#!/usr/bin/env bash
## @file build.sh
# @brief Release-artifact build script producing the sdist and wheel in `dist/`.
# @details Default mode executes, in strict fail-fast order: prerequisite
#          checks (REQ-281), targeted removal of stale generated outputs
#          (REQ-282), `uv build` into a temporary staging directory, staged
#          artifact verification, and installation of exactly one sdist and
#          one wheel into `dist/` (REQ-283), followed by a summary (REQ-285).
#          The `on_exit` trap removes the staging directory and build
#          intermediates and, when the build failed, every generated `dist/`
#          artifact so a failed build never exposes partial output (REQ-284).
#          `--clean` removes generated outputs without building (REQ-286);
#          `--list-artifacts` prints generated `dist/` artifacts (REQ-287).
#          Git-tracked files and non-generated `dist/` files are never deleted
#          (REQ-282, REQ-288). The repository root derives from the script
#          location, so invocation works from any working directory (REQ-280).
#          Complexity: O(N) over `dist/` entries plus the delegated build.
# @satisfies REQ-280, REQ-281, REQ-282, REQ-283, REQ-284, REQ-285, REQ-286, REQ-287, REQ-288, REQ-307

set -Eeuo pipefail

## @brief Invocation path of this script, used to derive the repository root.
SCRIPT_PATH="${BASH_SOURCE[0]}"
## @brief Directory component of `SCRIPT_PATH`; `.` when the path has no slash.
case "$SCRIPT_PATH" in
  */*) SCRIPT_DIR="${SCRIPT_PATH%/*}" ;;
  *) SCRIPT_DIR="." ;;
esac
## @brief Physical absolute path of the `scripts/` directory.
SCRIPT_DIR="$(cd -- "${SCRIPT_DIR:-/}" && pwd -P)"
## @brief Physical absolute repository root; every build step runs from here (REQ-280).
REPO_ROOT="$(cd -- "$SCRIPT_DIR/.." && pwd -P)"
## @brief Canonical destination directory of the final release artifacts (REQ-280).
DIST_DIR="$REPO_ROOT/dist"
## @brief Normalized distribution name prefixing every generated artifact filename.
# @details Equals the `pyproject.toml` `[project].name` value mandated by REQ-196.
DIST_NAME="galias"
## @brief Temporary staging directory receiving raw `uv build` output (REQ-283).
STAGING_DIR=""
## @brief Flag set to 1 once the build started mutating the repository tree.
# @details Gates every `on_exit` removal so aborted prerequisite checks delete nothing.
BUILD_STARTED=0
## @brief Flag set to 1 when this run created the `dist/` directory.
DIST_CREATED=0
## @brief Flag set to 1 when `REPO_ROOT` lies inside a git work tree.
IN_GIT_WORK_TREE=0
## @brief Result array of `collect_release_artifacts`: untracked generated `dist/` artifacts.
RELEASE_ARTIFACTS=()
## @brief Staged sdist path resolved by `verify_staged_artifacts`.
STAGED_SDIST=""
## @brief Staged wheel path resolved by `verify_staged_artifacts`.
STAGED_WHEEL=""

## @brief Print one canonical build progress line.
# @details O(1); writes `--- [build] <message> ---` to stdout.
# @param message {str} English step description or outcome.
# @return None; side-effect: one stdout line.
log_step() {
  printf -- '--- [build] %s ---\n' "$1"
}

## @brief Print one canonical build error line.
# @details O(1); writes `--- [build] ERROR: <message> ---` to stderr.
# @param message {str} English failure description.
# @return None; side-effect: one stderr line.
log_error() {
  printf -- '--- [build] ERROR: %s ---\n' "$1" >&2
}

## @brief Abort the script with an explicit English error.
# @details O(1); prints the error line and exits with status 1, triggering
#          the `on_exit` trap in build mode (REQ-285).
# @param message {str} English failure description.
# @return Never returns.
# @satisfies REQ-285
fail() {
  log_error "$1"
  exit 1
}

## @brief Print command usage.
# @details O(1); documents the default build mode and the `--clean`,
#          `--list-artifacts`, and `--help` options.
# @return None; side-effect: usage text on stdout.
# @satisfies REQ-287
print_usage() {
  cat <<'USAGE'
Usage: scripts/build.sh [--clean | --list-artifacts | --help]

  (no option)       Build the sdist and wheel release artifacts into dist/.
  --clean           Remove generated release artifacts and build intermediates.
  --list-artifacts  Print generated release artifacts currently in dist/.
  --help            Print this usage text.
USAGE
}

## @brief Report whether a path is or contains git-tracked content.
# @details O(tracked entries under path); queries `git ls-files` with
#          literal pathspecs relative to `REPO_ROOT`. Outside a git work tree
#          nothing is tracked. A failing git query inside a work tree is
#          treated as tracked so deletion fails closed (REQ-288).
# @param path {str} Absolute path below `REPO_ROOT`.
# @return {int} 0 when tracked content exists or the query failed inside a
#         work tree; 1 otherwise.
# @satisfies REQ-282, REQ-288
has_tracked_content() {
  local relative="${1#"$REPO_ROOT"/}"
  local tracked
  if [ "$IN_GIT_WORK_TREE" -ne 1 ]; then
    return 1
  fi
  if ! tracked="$(git -C "$REPO_ROOT" --literal-pathspecs ls-files -- "$relative")"; then
    return 0
  fi
  [ -n "$tracked" ]
}

## @brief Remove one generated path unless it holds git-tracked content.
# @details O(size of path); absent paths succeed. Tracked content makes the
#          function refuse deletion and report an error (REQ-288).
# @param path {str} Absolute file or directory path below `REPO_ROOT`.
# @return {int} 0 when the path is absent after the call; 1 on refusal or
#         removal failure.
# @satisfies REQ-288
remove_generated_path() {
  local target="$1"
  if [ ! -e "$target" ] && [ ! -L "$target" ]; then
    return 0
  fi
  if has_tracked_content "$target"; then
    log_error "Refusing to remove '$target': it contains git-tracked files"
    return 1
  fi
  if ! rm -rf -- "$target"; then
    log_error "Unable to remove '$target'"
    return 1
  fi
  return 0
}

## @brief Collect untracked generated release artifacts present in `dist/`.
# @details O(N) over matching `dist/` entries; selects regular files named
#          `<DIST_NAME>-*.tar.gz` or `<DIST_NAME>-*.whl` and skips git-tracked
#          files so version-controlled `dist/` content is never treated as
#          generated output (REQ-282).
# @return None; side-effect: overwrites global array `RELEASE_ARTIFACTS`.
# @satisfies REQ-282, REQ-287
collect_release_artifacts() {
  local candidate
  RELEASE_ARTIFACTS=()
  for candidate in "$DIST_DIR/$DIST_NAME"-*.tar.gz "$DIST_DIR/$DIST_NAME"-*.whl; do
    if [ ! -f "$candidate" ]; then
      continue
    fi
    if has_tracked_content "$candidate"; then
      continue
    fi
    RELEASE_ARTIFACTS+=("$candidate")
  done
}

## @brief Remove every untracked generated release artifact from `dist/`.
# @details O(N); deletes only paths returned by `collect_release_artifacts`,
#          preserving tracked and non-generated `dist/` files (REQ-282).
# @return {int} 0 when every artifact was removed; 1 on any removal failure.
# @satisfies REQ-282, REQ-284, REQ-286
remove_release_artifacts() {
  local artifact
  local failed=0
  collect_release_artifacts
  if [ "${#RELEASE_ARTIFACTS[@]}" -gt 0 ]; then
    for artifact in "${RELEASE_ARTIFACTS[@]}"; do
      remove_generated_path "$artifact" || failed=1
    done
  fi
  return "$failed"
}

## @brief Remove setuptools build intermediates from the repository tree.
# @details O(size of intermediates); targets `build/` and `src/*.egg-info`
#          only, through the tracked-content guard (REQ-288).
# @return {int} 0 when every intermediate was removed; 1 on any failure.
# @satisfies REQ-282, REQ-284, REQ-286
remove_build_intermediates() {
  local intermediate
  local failed=0
  for intermediate in "$REPO_ROOT/build" "$REPO_ROOT"/src/*.egg-info; do
    remove_generated_path "$intermediate" || failed=1
  done
  return "$failed"
}

## @brief Remove the `dist/` directory when it is empty.
# @details O(1); a non-empty or absent directory is left untouched.
# @return {int} 0 when `dist/` is absent, non-empty, or removed; 1 when the
#         empty directory cannot be removed.
# @satisfies REQ-286
remove_empty_dist_dir() {
  local entry
  if [ ! -d "$DIST_DIR" ]; then
    return 0
  fi
  for entry in "$DIST_DIR"/* "$DIST_DIR"/.[!.]* "$DIST_DIR"/..?*; do
    if [ -e "$entry" ] || [ -L "$entry" ]; then
      return 0
    fi
  done
  if ! rmdir -- "$DIST_DIR"; then
    log_error "Unable to remove empty directory '$DIST_DIR'"
    return 1
  fi
  return 0
}

## @brief Implement `--clean`: remove generated outputs without building.
# @details O(1); delegates to `scripts/clean.sh`, the canonical cleanup entry
#          point for every artifact created by this script (REQ-286, REQ-309).
# @return {int} 0 on complete cleanup; 1 on any removal failure.
# @satisfies REQ-286
clean_generated_outputs() {
  "$SCRIPT_DIR/clean.sh"
}

## @brief Implement `--list-artifacts`: print generated `dist/` artifacts.
# @details O(N); prints one absolute path per line and nothing when no
#          untracked generated artifact exists (REQ-287).
# @return None; side-effect: artifact paths on stdout.
# @satisfies REQ-287
list_release_artifacts() {
  local artifact
  collect_release_artifacts
  if [ "${#RELEASE_ARTIFACTS[@]}" -gt 0 ]; then
    for artifact in "${RELEASE_ARTIFACTS[@]}"; do
      printf '%s\n' "$artifact"
    done
  fi
}

## @brief Validate build tools and required project inputs.
# @details O(1); requires `uv` in PATH plus `pyproject.toml` and the
#          `src/git_alias/` package directory, aborting with an explicit
#          English error otherwise (REQ-281).
# @return None; never returns when a prerequisite is missing.
# @satisfies REQ-281
check_build_prerequisites() {
  if ! command -v uv >/dev/null 2>&1; then
    fail "Required tool 'uv' (Astral uv) was not found in PATH"
  fi
  if [ ! -f "$REPO_ROOT/pyproject.toml" ]; then
    fail "Required file '$REPO_ROOT/pyproject.toml' is missing"
  fi
  if [ ! -d "$REPO_ROOT/src/git_alias" ]; then
    fail "Required package directory '$REPO_ROOT/src/git_alias' is missing"
  fi
}

## @brief Verify the staged sdist member list against the sdist content policy.
# @details O(M) over archive members. Writes the `tar -tzf` listing into the
#          staging directory so a listing failure aborts the build instead of
#          being masked by a pipeline (REQ-307). Requires the metadata, license,
#          readme, lock file, and package entry module members. Rejects members
#          of the `tests/`, `scripts/`, and `usereq/` trees, `MANIFEST.in`, and
#          generated `src/*.egg-info/` files other than `SOURCES.txt` (REQ-305).
# @param archive {str} Absolute path of the staged sdist archive.
# @return None; never returns when the listing fails or a member violates REQ-304 or REQ-305.
# @satisfies REQ-304, REQ-305, REQ-307
verify_sdist_content() {
  local archive="$1"
  local listing="$STAGING_DIR/sdist-members.txt"
  local member relative required seen=" "
  local -a excluded=()
  tar -tzf "$archive" > "$listing" || fail "Unable to list the members of '${archive##*/}'"
  while IFS= read -r member; do
    relative="${member#*/}"
    case "$relative" in
      tests|tests/*|scripts|scripts/*|usereq|usereq/*|MANIFEST.in)
        excluded+=("$member") ;;
      src/*.egg-info/SOURCES.txt|src/*.egg-info/) ;;
      src/*.egg-info/*)
        excluded+=("$member") ;;
    esac
    seen+="$relative "
  done < "$listing"
  for required in PKG-INFO pyproject.toml README.md LICENSE uv.lock src/git_alias/__init__.py; do
    case "$seen" in
      *" $required "*) ;;
      *) fail "Sdist '${archive##*/}' lacks required member '$required'" ;;
    esac
  done
  if [ "${#excluded[@]}" -gt 0 ]; then
    fail "Sdist '${archive##*/}' contains excluded members: ${excluded[*]}"
  fi
}

## @brief Verify the staging directory holds exactly the expected artifacts.
# @details O(N) over staging entries; requires exactly one non-empty sdist
#          and one non-empty wheel named after `DIST_NAME`, tolerates the
#          uv-generated `.gitignore` marker, and rejects any other entry so
#          no build output is silently dropped (REQ-283).
# @return None; side-effect: sets `STAGED_SDIST` and `STAGED_WHEEL`; never
#         returns when verification fails.
# @satisfies REQ-283
verify_staged_artifacts() {
  local entry name
  local sdists=()
  local wheels=()
  local unexpected=()
  for entry in "$STAGING_DIR"/* "$STAGING_DIR"/.[!.]* "$STAGING_DIR"/..?*; do
    if [ ! -e "$entry" ] && [ ! -L "$entry" ]; then
      continue
    fi
    name="${entry##*/}"
    case "$name" in
      .gitignore) ;;
      "$DIST_NAME"-*.tar.gz) sdists+=("$entry") ;;
      "$DIST_NAME"-*.whl) wheels+=("$entry") ;;
      *) unexpected+=("$name") ;;
    esac
  done
  if [ "${#sdists[@]}" -ne 1 ]; then
    fail "Expected exactly one sdist '$DIST_NAME-*.tar.gz' from the build, found ${#sdists[@]}"
  fi
  if [ "${#wheels[@]}" -ne 1 ]; then
    fail "Expected exactly one wheel '$DIST_NAME-*.whl' from the build, found ${#wheels[@]}"
  fi
  if [ "${#unexpected[@]}" -gt 0 ]; then
    fail "Unexpected build output: ${unexpected[*]}"
  fi
  STAGED_SDIST="${sdists[0]}"
  STAGED_WHEEL="${wheels[0]}"
  if [ ! -f "$STAGED_SDIST" ] || [ ! -s "$STAGED_SDIST" ]; then
    fail "Built sdist '${STAGED_SDIST##*/}' is not a non-empty regular file"
  fi
  if [ ! -f "$STAGED_WHEEL" ] || [ ! -s "$STAGED_WHEEL" ]; then
    fail "Built wheel '${STAGED_WHEEL##*/}' is not a non-empty regular file"
  fi
  verify_sdist_content "$STAGED_SDIST"
}

## @brief Move verified staged artifacts into `dist/`.
# @details O(1) moves; creates `dist/` when absent and refuses to overwrite
#          an existing destination, which after stale removal can only be a
#          git-tracked file (REQ-282, REQ-283).
# @return None; never returns when installation fails.
# @satisfies REQ-280, REQ-283
install_staged_artifacts() {
  local staged destination
  if [ ! -d "$DIST_DIR" ]; then
    mkdir -p -- "$DIST_DIR" || fail "Unable to create '$DIST_DIR'"
    DIST_CREATED=1
  fi
  for staged in "$STAGED_SDIST" "$STAGED_WHEEL"; do
    destination="$DIST_DIR/${staged##*/}"
    if [ -e "$destination" ] || [ -L "$destination" ]; then
      fail "Refusing to overwrite existing version-controlled file '$destination'"
    fi
    mv -- "$staged" "$destination" || fail "Unable to move '${staged##*/}' into '$DIST_DIR'"
  done
}

## @brief Print the summary of produced release artifacts.
# @details O(N) over artifacts; prints path, byte size, and the SHA-256
#          digest when `sha256sum` is available (REQ-285). Requires exactly
#          two generated artifacts in `dist/`.
# @return None; never returns when the artifact count differs from two.
# @satisfies REQ-285
print_build_summary() {
  local artifact size digest
  collect_release_artifacts
  if [ "${#RELEASE_ARTIFACTS[@]}" -ne 2 ]; then
    fail "Expected exactly two release artifacts in '$DIST_DIR', found ${#RELEASE_ARTIFACTS[@]}"
  fi
  log_step "Build completed: ${#RELEASE_ARTIFACTS[@]} release artifacts in $DIST_DIR"
  for artifact in "${RELEASE_ARTIFACTS[@]}"; do
    size="$(wc -c < "$artifact")" || fail "Unable to read the size of '$artifact'"
    size="$((size))"
    if command -v sha256sum >/dev/null 2>&1; then
      digest="$(sha256sum -- "$artifact")" || fail "Unable to hash '$artifact'"
      printf '  %s (%s bytes, sha256 %s)\n' "$artifact" "$size" "${digest%% *}"
    else
      printf '  %s (%s bytes)\n' "$artifact" "$size"
    fi
  done
}

## @brief Build-mode exit trap removing temporary and partial outputs.
# @details Runs on every build-mode exit path. Removes the staging directory
#          and, once the build started, the build intermediates; a failed
#          build or a failed cleanup additionally removes generated `dist/`
#          artifacts and a `dist/` directory created by this run (REQ-284).
#          The original non-zero status is preserved; a cleanup failure
#          after a successful build yields status 1 (REQ-285).
# @return Never returns; exits with the resolved status.
# @satisfies REQ-284, REQ-285
on_exit() {
  local status=$?
  local cleanup_failed=0
  trap - EXIT
  trap '' INT TERM HUP
  set +e
  if [ -n "$STAGING_DIR" ] && [ -e "$STAGING_DIR" ]; then
    if ! rm -rf -- "$STAGING_DIR"; then
      log_error "Unable to remove staging directory '$STAGING_DIR'"
      cleanup_failed=1
    fi
  fi
  if [ "$BUILD_STARTED" -eq 1 ]; then
    remove_build_intermediates || cleanup_failed=1
  fi
  if [ "$status" -eq 0 ] && [ "$cleanup_failed" -ne 0 ]; then
    log_error "Build intermediates cleanup failed"
    status=1
  fi
  if [ "$status" -ne 0 ] && [ "$BUILD_STARTED" -eq 1 ]; then
    remove_release_artifacts || log_error "Unable to remove partial release artifacts"
    if [ "$DIST_CREATED" -eq 1 ]; then
      remove_empty_dist_dir
    fi
  fi
  if [ "$status" -ne 0 ]; then
    log_error "Build failed with exit status $status; no release artifact was produced"
  fi
  exit "$status"
}

## @brief Execute the complete release-artifact build.
# @details Registers the exit and signal traps, validates prerequisites,
#          removes stale generated outputs, runs `uv build` into the staging
#          directory, verifies and installs the artifacts, and prints the
#          summary. Every step aborts the script on failure (REQ-285).
# @return None; exits non-zero on the first failing step.
# @satisfies REQ-280, REQ-281, REQ-282, REQ-283, REQ-284, REQ-285
run_build() {
  trap on_exit EXIT
  trap 'exit 130' INT
  trap 'exit 143' TERM
  trap 'exit 129' HUP

  log_step "Check build prerequisites"
  check_build_prerequisites

  log_step "Remove stale build outputs"
  BUILD_STARTED=1
  remove_release_artifacts || fail "Unable to remove stale release artifacts"
  remove_build_intermediates || fail "Unable to remove stale build intermediates"

  log_step "Build sdist and wheel"
  STAGING_DIR="$(mktemp -d "${TMPDIR:-/tmp}/galias-build.XXXXXX")" \
    || fail "Unable to create the temporary staging directory"
  uv build --out-dir "$STAGING_DIR" || fail "'uv build' failed"

  log_step "Verify built artifacts"
  verify_staged_artifacts

  log_step "Install release artifacts into dist/"
  install_staged_artifacts

  print_build_summary
}

cd -- "$REPO_ROOT"

if command -v git >/dev/null 2>&1 \
  && [ "$(git -C "$REPO_ROOT" rev-parse --is-inside-work-tree 2>/dev/null)" = "true" ]; then
  IN_GIT_WORK_TREE=1
fi

if [ "$#" -gt 1 ]; then
  log_error "Expected at most one option, got $#"
  print_usage >&2
  exit 2
fi

case "${1:-}" in
  "")
    run_build
    ;;
  --clean)
    clean_generated_outputs
    ;;
  --list-artifacts)
    list_release_artifacts
    ;;
  --help | -h)
    print_usage
    ;;
  *)
    log_error "Unknown option: $1"
    print_usage >&2
    exit 2
    ;;
esac
