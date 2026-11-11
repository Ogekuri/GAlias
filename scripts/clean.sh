#!/usr/bin/env bash
## @file clean.sh
# @brief Cleanup script removing every artifact created by `scripts/build.sh`.
# @details Removes, in strict fail-fast order: untracked generated
#          `dist/galias-*.tar.gz` and `dist/galias-*.whl` release artifacts,
#          the `build/` intermediates, and `src/*.egg-info` directories
#          (REQ-310), then removes the `dist/` directory when it became
#          empty. Git-tracked files and non-generated `dist/` files are never
#          deleted (REQ-310, REQ-288). The repository root derives from the
#          script location, so invocation works from any working directory
#          (REQ-309). Every step prints one canonical progress line
#          (REQ-312). Complexity: O(N) over `dist/` entries.
# @satisfies REQ-309, REQ-310, REQ-311, REQ-312, REQ-288

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
## @brief Physical absolute repository root; every cleanup step runs from here (REQ-309).
REPO_ROOT="$(cd -- "$SCRIPT_DIR/.." && pwd -P)"
## @brief Canonical destination directory of the release artifacts (REQ-310).
DIST_DIR="$REPO_ROOT/dist"
## @brief Normalized distribution name prefixing every generated artifact filename.
# @details Equals the `pyproject.toml` `[project].name` value mandated by REQ-196.
DIST_NAME="galias"
## @brief Flag set to 1 when `REPO_ROOT` lies inside a git work tree.
IN_GIT_WORK_TREE=0
## @brief Result array of `collect_release_artifacts`: untracked generated `dist/` artifacts.
RELEASE_ARTIFACTS=()

## @brief Print one canonical cleanup progress line.
# @details O(1); writes `--- [clean] <message> ---` to stdout.
# @param message {str} English step description or outcome.
# @return None; side-effect: one stdout line.
# @satisfies REQ-312
log_step() {
  printf -- '--- [clean] %s ---\n' "$1"
}

## @brief Print one canonical cleanup error line.
# @details O(1); writes `--- [clean] ERROR: <message> ---` to stderr.
# @param message {str} English failure description.
# @return None; side-effect: one stderr line.
log_error() {
  printf -- '--- [clean] ERROR: %s ---\n' "$1" >&2
}

## @brief Abort the script with an explicit English error.
# @details O(1); prints the error line and exits with status 1.
# @param message {str} English failure description.
# @return Never returns.
# @satisfies REQ-311
fail() {
  log_error "$1"
  exit 1
}

## @brief Print command usage.
# @details O(1); documents the default cleanup mode and the `--help` option.
# @return None; side-effect: usage text on stdout.
# @satisfies REQ-311
print_usage() {
  cat <<'USAGE'
Usage: scripts/clean.sh [--help]

  (no option)       Remove every artifact created by scripts/build.sh.
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
# @satisfies REQ-310, REQ-288
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
# @satisfies REQ-311, REQ-288
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
#          generated output (REQ-310).
# @return None; side-effect: overwrites global array `RELEASE_ARTIFACTS`.
# @satisfies REQ-310
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
#          preserving tracked and non-generated `dist/` files (REQ-310).
# @return {int} 0 when every artifact was removed; 1 on any removal failure.
# @satisfies REQ-310
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
# @satisfies REQ-310
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
# @satisfies REQ-310
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

## @brief Execute the complete cleanup of `scripts/build.sh` artifacts.
# @details O(N); removes generated release artifacts, build intermediates,
#          and an emptied `dist/` directory (REQ-310). Tracked and
#          non-generated files are preserved. Any removal failure or an
#          unknown option exits non-zero with an explicit English error
#          (REQ-311). Each step emits one progress line (REQ-312).
# @return {int} 0 on complete cleanup; 1 on any removal failure.
# @satisfies REQ-309, REQ-310, REQ-311, REQ-312
run_clean() {
  local failed=0
  log_step "Remove generated release artifacts and build intermediates"
  remove_release_artifacts || failed=1
  remove_build_intermediates || failed=1
  remove_empty_dist_dir || failed=1
  if [ "$failed" -ne 0 ]; then
    fail "Cleanup incomplete"
  fi
  log_step "Cleanup completed"
  return 0
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
    run_clean
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
