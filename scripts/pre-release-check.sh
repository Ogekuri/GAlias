#!/usr/bin/env bash
## @file pre-release-check.sh
# @brief Repository-local release-readiness check with guaranteed cleanup.
# @details Executes, in strict fail-fast order (REQ-225): `git` and Astral
#          `uv` availability (REQ-219), repository structure validation
#          (REQ-289), Bash syntax of `scripts/*.sh` (REQ-291), repository-state
#          baseline capture, `uv lock --check` (REQ-220), Python source and
#          `pyproject.toml` validity (REQ-292), version consistency through
#          the `ver` alias (REQ-293), the complete pytest suite (REQ-221), the
#          release build through `scripts/build.sh --output-dir` into a
#          run-scoped temporary directory (REQ-222, REQ-324), artifact
#          validation in that directory (REQ-294), and an isolated wheel
#          installation check (REQ-296). The repository `dist/` directory is
#          never created, listed, cleaned, or verified (REQ-323), so results
#          are independent of its content (REQ-325). The `on_exit` trap runs
#          on success, failure, and interruption (REQ-297): it removes every
#          generated artifact (REQ-226, REQ-227), verifies repository
#          integrity against the baseline (REQ-298), preserves the original
#          failure status (REQ-299), and prints the final result line
#          (REQ-300). Tracked files are never modified (REQ-223) and
#          git-tracked content is never deleted (REQ-288). The repository
#          root derives from the script location (REQ-218). Project scope
#          note: the project configures no formatter, linter, type checker,
#          or dependency-audit tool, so no such step exists.
# @satisfies REQ-217, REQ-218, REQ-219, REQ-220, REQ-221, REQ-222, REQ-223, REQ-224, REQ-225, REQ-226, REQ-227, REQ-288, REQ-289, REQ-291, REQ-292, REQ-293, REQ-294, REQ-296, REQ-297, REQ-298, REQ-299, REQ-300, REQ-308, REQ-323, REQ-324, REQ-325

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
## @brief Physical absolute repository root; every step executes from here (REQ-218).
REPO_ROOT="$(cd -- "$SCRIPT_DIR/.." && pwd -P)"
## @brief Release-artifact build script owning generated-output knowledge and cleanup (REQ-222, REQ-226).
BUILD_SCRIPT="$SCRIPT_DIR/build.sh"
## @brief Temporary directory holding repository-state snapshots; outside the repository.
WORK_DIR=""
## @brief Temporary directory receiving the validation build artifacts; outside the repository.
# @details Created for the run and removed at exit, so the validation build never
#          reads, cleans, or writes the repository `dist/` directory (REQ-323, REQ-324).
BUILD_DIR=""
## @brief Description of the step currently executing, used by failure diagnostics.
CURRENT_STEP="initialization"
## @brief Description of the failed step or interruption; empty while every step passes.
FAILED_STEP=""
## @brief Flag set to 1 once the baseline exists; gates every cleanup removal (REQ-290).
BASELINE_READY=0
## @brief Flag set to 1 when `.venv` existed before the run (REQ-227).
VENV_PREEXISTED=0
## @brief Built sdist path resolved by `validate_release_artifacts`.
SDIST_PATH=""
## @brief Built wheel path resolved by `validate_release_artifacts`.
WHEEL_PATH=""

## @brief Print one canonical pre-release-check progress line.
# @details O(1); writes `--- [pre-release-check] <message> ---` to stdout (REQ-224).
# @param message {str} English step description or outcome.
# @return None; side-effect: one stdout line.
# @satisfies REQ-224
log_step() {
  printf -- '--- [pre-release-check] %s ---\n' "$1"
}

## @brief Print one diagnostic detail line.
# @details O(1); writes `[pre-release-check] <message>` to stderr.
# @param message {str} English diagnostic detail.
# @return None; side-effect: one stderr line.
log_detail() {
  printf -- '[pre-release-check] %s\n' "$1" >&2
}

## @brief Execute one validation step with fail-fast semantics.
# @details Records the step as current, prints the progress line, and runs
#          the command argv from the repository root. The first failure
#          records `FAILED_STEP`, prints the step-failed diagnostic, and
#          exits with status 1 so later steps never execute (REQ-225); the
#          `on_exit` trap then performs cleanup (REQ-297).
# @param message {str} English step description printed before execution.
# @param ... Command argv or function name with arguments.
# @return None; never returns when the step fails.
# @satisfies REQ-224, REQ-225
run_step() {
  local message="$1"
  shift
  CURRENT_STEP="$message"
  log_step "$message"
  if ! "$@"; then
    FAILED_STEP="$message"
    printf -- '--- [pre-release-check] Step failed: %s ---\n' "$message" >&2
    exit 1
  fi
}

## @brief Verify a prerequisite executable is in PATH, then run its version probe.
# @details O(1); resolves the executable name with `command -v` before any
#          invocation, so a missing tool never reaches Bash's own lookup
#          message. A missing executable prints the explicit English
#          diagnostic `Required tool '<tool>' was not found in PATH` and
#          returns 1, which makes the enclosing `run_step` report the failed
#          step and exit non-zero (REQ-219, REQ-225). A present executable
#          runs `<tool> --version` and returns its exit status.
# @param tool {str} Executable name resolved through PATH (`git` or `uv`).
# @return {int} 0 when the executable exists and `--version` succeeds; 1 when
#         it is missing or its version probe fails.
# @satisfies REQ-219, REQ-225
check_tool_version() {
  local tool="$1"
  if ! command -v "$tool" >/dev/null 2>&1; then
    log_detail "Required tool '$tool' was not found in PATH"
    return 1
  fi
  "$tool" --version
}

## @brief Validate the repository layout required by the release process.
# @details O(1); requires `REPO_ROOT` to be the root of a git work tree and
#          to contain the packaging manifests, documentation, package entry
#          module, test directory, and the executable build script (REQ-289).
# @return {int} 0 when the structure is valid; 1 otherwise with diagnostics.
# @satisfies REQ-289
validate_repository_structure() {
  local inside toplevel required
  if ! inside="$(git -C "$REPO_ROOT" rev-parse --is-inside-work-tree)" || [ "$inside" != "true" ]; then
    log_detail "'$REPO_ROOT' is not inside a git work tree"
    return 1
  fi
  if ! toplevel="$(git -C "$REPO_ROOT" rev-parse --show-toplevel)"; then
    log_detail "Unable to resolve the git work-tree root"
    return 1
  fi
  if [ ! "$toplevel" -ef "$REPO_ROOT" ]; then
    log_detail "Script location root '$REPO_ROOT' differs from the git work-tree root '$toplevel'"
    return 1
  fi
  for required in pyproject.toml uv.lock README.md LICENSE src/git_alias/__init__.py scripts/build.sh; do
    if [ ! -f "$REPO_ROOT/$required" ]; then
      log_detail "Required file '$required' is missing"
      return 1
    fi
  done
  if [ ! -d "$REPO_ROOT/tests" ]; then
    log_detail "Required directory 'tests' is missing"
    return 1
  fi
  if [ ! -x "$BUILD_SCRIPT" ]; then
    log_detail "Build script '$BUILD_SCRIPT' is not executable"
    return 1
  fi
  return 0
}

## @brief Verify Bash syntax of every repository script.
# @details O(N) over `scripts/*.sh`; runs `bash -n` on each file and stops
#          at the first syntax error (REQ-291).
# @return {int} 0 when every script parses; 1 otherwise.
# @satisfies REQ-291
check_shell_syntax() {
  local script
  for script in "$REPO_ROOT"/scripts/*.sh; do
    if [ ! -f "$script" ]; then
      continue
    fi
    if ! bash -n "$script"; then
      log_detail "Bash syntax check failed for '$script'"
      return 1
    fi
  done
  return 0
}

## @brief Print the fingerprint of the tracked-file state.
# @details O(tracked changes); emits `git status --porcelain` for tracked
#          files followed by the object hash of the unstaged binary diff, so
#          both the change set and the content of modified tracked files are
#          covered. Uses `--no-optional-locks` to leave the index untouched.
# @return {int} 0 on success with the fingerprint on stdout; 1 on git failure.
# @satisfies REQ-223, REQ-298
snapshot_tracked_state() {
  git -C "$REPO_ROOT" --no-optional-locks status --porcelain=v1 --untracked-files=no || return 1
  git -C "$REPO_ROOT" --no-optional-locks diff --binary | git hash-object --stdin || return 1
  return 0
}

## @brief Print the sorted inventory of untracked and ignored files.
# @details O(N log N) over non-tracked files; lists every untracked file,
#          ignored files included, excluding `.venv`, in C-locale order with
#          git path quoting so each line names exactly one path.
# @return {int} 0 on success with the inventory on stdout; 1 on failure.
# @satisfies REQ-298
snapshot_untracked_files() {
  git -C "$REPO_ROOT" --no-optional-locks ls-files --others -- . ':(exclude).venv' \
    | LC_ALL=C sort || return 1
  return 0
}

## @brief Capture the pre-run repository state used by cleanup verification.
# @details O(N); records `.venv` pre-existence, creates the temporary snapshot
#          directory, and stores the tracked-state fingerprint and the
#          untracked-file inventory. Sets `BASELINE_READY`, which enables
#          cleanup in `on_exit` (REQ-298). `dist/` is never probed (REQ-323).
# @return {int} 0 when the baseline is stored; 1 otherwise.
# @satisfies REQ-227, REQ-298, REQ-323
record_baseline() {
  if [ -e "$REPO_ROOT/.venv" ]; then
    VENV_PREEXISTED=1
  fi
  if ! WORK_DIR="$(mktemp -d "${TMPDIR:-/tmp}/galias-pre-release.XXXXXX")"; then
    log_detail "Unable to create the temporary snapshot directory"
    return 1
  fi
  if ! snapshot_tracked_state > "$WORK_DIR/tracked.before"; then
    log_detail "Unable to record the tracked-file state"
    return 1
  fi
  if ! snapshot_untracked_files > "$WORK_DIR/untracked.before"; then
    log_detail "Unable to record the untracked-file inventory"
    return 1
  fi
  BASELINE_READY=1
  return 0
}

## @brief Verify Python source validity and `pyproject.toml` parsing.
# @details O(total source size); compiles every `src/` and `tests/` Python
#          file in memory without writing bytecode and parses
#          `pyproject.toml` with `tomllib` through `uv run python` (REQ-292).
# @return {int} 0 when every file is valid; 1 otherwise.
# @satisfies REQ-292
check_python_sources() {
  uv run python - "$REPO_ROOT" <<'PY'
import pathlib
import sys
import tomllib

root = pathlib.Path(sys.argv[1])
errors = []
checked = 0
for folder in ("src", "tests"):
    for path in sorted((root / folder).rglob("*.py")):
        checked += 1
        try:
            compile(path.read_bytes(), str(path), "exec", dont_inherit=True)
        except (SyntaxError, ValueError) as exc:
            errors.append(f"{path}: {exc}")
try:
    with open(root / "pyproject.toml", "rb") as handle:
        tomllib.load(handle)
except (OSError, tomllib.TOMLDecodeError) as exc:
    errors.append(f"pyproject.toml: {exc}")
for error in errors:
    print(f"[pre-release-check] {error}", file=sys.stderr)
if errors:
    sys.exit(1)
print(f"Compiled {checked} Python files; pyproject.toml parses as TOML.")
PY
}

## @brief Verify version consistency across version-managed files.
# @details Executes the project `ver` alias in-process with update checks
#          disabled, so no network request and no update-check cache write
#          occurs; a version mismatch exits non-zero (REQ-293).
# @return {int} 0 when every version-managed file agrees; non-zero otherwise.
# @satisfies REQ-293
check_version_consistency() {
  uv run python -c 'from git_alias.core import main; main(["ver"], check_updates=False)'
}

## @brief Build the validation artifacts in a run-scoped temporary directory.
# @details O(1); creates the `BUILD_DIR` temporary directory outside the
#          repository and delegates the sdist and wheel build to
#          `scripts/build.sh --output-dir "$BUILD_DIR"` (REQ-222, REQ-324).
#          The repository `dist/` directory is neither read nor written
#          (REQ-323).
# @return {int} 0 when the build succeeded; non-zero otherwise.
# @satisfies REQ-222, REQ-323, REQ-324
build_release_artifacts() {
  if ! BUILD_DIR="$(mktemp -d "${TMPDIR:-/tmp}/galias-pre-release-build.XXXXXX")"; then
    log_detail "Unable to create the temporary build directory"
    return 1
  fi
  "$BUILD_SCRIPT" --output-dir "$BUILD_DIR"
}

## @brief Validate existence, naming, integrity, and content of built artifacts.
# @details Requires exactly one sdist and one wheel in the run-scoped `BUILD_DIR`
#          temporary directory, then validates through `uv run python`:
#          filenames against the `pyproject.toml` name and version, full archive
#          readability, presence of every `src/git_alias/*.py` module, license
#          and readme files, metadata name/version/`Requires-Python`, and wheel
#          console scripts (REQ-294). Sets `SDIST_PATH` and `WHEEL_PATH`.
#          Never inspects `dist/` (REQ-323).
# @return {int} 0 when both artifacts are valid; 1 otherwise.
# @satisfies REQ-294, REQ-308, REQ-323, REQ-324
validate_release_artifacts() {
  local artifact
  local count=0
  SDIST_PATH=""
  WHEEL_PATH=""
  if [ -z "$BUILD_DIR" ] || [ ! -d "$BUILD_DIR" ]; then
    log_detail "Temporary build directory is missing"
    return 1
  fi
  for artifact in "$BUILD_DIR"/*.tar.gz "$BUILD_DIR"/*.whl; do
    if [ ! -f "$artifact" ]; then
      continue
    fi
    count=$((count + 1))
    case "$artifact" in
      *.tar.gz) SDIST_PATH="$artifact" ;;
      *.whl) WHEEL_PATH="$artifact" ;;
    esac
  done
  if [ "$count" -ne 2 ] || [ -z "$SDIST_PATH" ] || [ -z "$WHEEL_PATH" ]; then
    log_detail "Expected exactly one sdist and one wheel in the temporary build directory, found $count artifact(s)"
    return 1
  fi
  uv run python - "$REPO_ROOT" "$SDIST_PATH" "$WHEEL_PATH" <<'PY'
import configparser
import email.parser
import pathlib
import re
import sys
import tarfile
import tomllib
import zipfile
import zlib

root, sdist, wheel = (pathlib.Path(argument) for argument in sys.argv[1:4])
project = tomllib.loads((root / "pyproject.toml").read_text(encoding="utf-8"))["project"]
name = re.sub(r"[-_.]+", "_", project["name"]).lower()
version = project["version"]
modules = sorted(path.name for path in (root / "src" / "git_alias").glob("*.py"))
documents = [project["readme"]] if isinstance(project.get("readme"), str) else []
licenses = [entry for entry in project.get("license-files", []) if not set("*?[") & set(entry)]
errors = []


def check(condition, message):
    if not condition:
        errors.append(message)


def check_metadata(text, label):
    metadata = email.parser.Parser().parsestr(text)
    actual_name = re.sub(r"[-_.]+", "_", metadata.get("Name", "")).lower()
    check(actual_name == name, f"{label}: Name is {metadata.get('Name')!r}, expected {project['name']!r}")
    check(metadata.get("Version") == version, f"{label}: Version is {metadata.get('Version')!r}, expected {version!r}")
    check(
        metadata.get("Requires-Python") == project.get("requires-python"),
        f"{label}: Requires-Python is {metadata.get('Requires-Python')!r}",
    )


check(sdist.name == f"{name}-{version}.tar.gz", f"unexpected sdist filename {sdist.name!r}")
check(wheel.name == f"{name}-{version}-py3-none-any.whl", f"unexpected wheel filename {wheel.name!r}")

try:
    with tarfile.open(sdist, "r:gz") as archive:
        members = {}
        for member in archive:
            members[member.name] = member
            if member.isfile():
                archive.extractfile(member).read()
        base = f"{name}-{version}/"
        required = ["PKG-INFO", "pyproject.toml", "uv.lock", *documents, *licenses]
        required += [f"src/git_alias/{module}" for module in modules]
        for entry in required:
            check(base + entry in members, f"sdist lacks {entry}")
        excluded_roots = {"tests", "scripts", "usereq"}
        for member_name, member in members.items():
            if not member.isfile() or not member_name.startswith(base):
                continue
            relative_name = member_name[len(base):]
            top_level = relative_name.split("/", 1)[0]
            is_egg_info = (
                relative_name.startswith("src/")
                and ".egg-info/" in relative_name
                and not relative_name.endswith("/SOURCES.txt")
            )
            if top_level in excluded_roots or relative_name == "MANIFEST.in" or is_egg_info:
                errors.append(f"sdist contains excluded member {member_name}")
        if base + "PKG-INFO" in members:
            payload = archive.extractfile(members[base + "PKG-INFO"]).read()
            check_metadata(payload.decode("utf-8"), "sdist PKG-INFO")
except (tarfile.TarError, OSError, EOFError, zlib.error) as exc:
    errors.append(f"sdist is not a readable tar.gz archive: {exc}")

try:
    with zipfile.ZipFile(wheel) as archive:
        check(archive.testzip() is None, "wheel contains a corrupt member")
        names = set(archive.namelist())
        info = f"{name}-{version}.dist-info/"
        required = [f"git_alias/{module}" for module in modules]
        required += [info + entry for entry in ("METADATA", "WHEEL", "RECORD", "entry_points.txt")]
        required += [f"{info}licenses/{entry}" for entry in licenses]
        for entry in required:
            check(entry in names, f"wheel lacks {entry}")
        if info + "METADATA" in names:
            check_metadata(archive.read(info + "METADATA").decode("utf-8"), "wheel METADATA")
        if info + "entry_points.txt" in names:
            parser = configparser.ConfigParser(delimiters=("=",))
            parser.optionxform = str
            parser.read_string(archive.read(info + "entry_points.txt").decode("utf-8"))
            scripts = dict(parser["console_scripts"]) if parser.has_section("console_scripts") else {}
            check(scripts == project.get("scripts", {}), f"wheel console scripts are {scripts!r}")
except (zipfile.BadZipFile, OSError, zlib.error, configparser.Error) as exc:
    errors.append(f"wheel is not a readable zip archive: {exc}")

for error in errors:
    print(f"[pre-release-check] {error}", file=sys.stderr)
if errors:
    sys.exit(1)
print(f"Validated {sdist.name} and {wheel.name} ({len(modules)} package modules, version {version}).")
PY
}

## @brief Verify the built wheel installs and loads in an isolated environment.
# @details Installs the wheel into an ephemeral uv environment detached from
#          the project (`--isolated --no-project`), imports every package
#          module from the installed distribution, and loads every console
#          script declared in `pyproject.toml` (REQ-296). Writes nothing
#          into the repository.
# @return {int} 0 when installation, imports, and entry points succeed; 1 otherwise.
# @satisfies REQ-296
check_wheel_installation() {
  uv run --isolated --no-project --with "$WHEEL_PATH" python - "$REPO_ROOT" <<'PY'
import importlib
import importlib.metadata
import pathlib
import sys
import tomllib

root = pathlib.Path(sys.argv[1]).resolve()
project = tomllib.loads((root / "pyproject.toml").read_text(encoding="utf-8"))["project"]
errors = []
distribution = importlib.metadata.distribution(project["name"])
if distribution.version != project["version"]:
    errors.append(f"installed version {distribution.version!r} differs from {project['version']!r}")
stems = sorted(path.stem for path in (root / "src" / "git_alias").glob("*.py"))
modules = ["git_alias"] + [f"git_alias.{stem}" for stem in stems if not stem.startswith("__")]
for module_name in modules:
    module = importlib.import_module(module_name)
    if root in pathlib.Path(module.__file__).resolve().parents:
        errors.append(f"{module_name} was imported from the source tree instead of the wheel")
entry_points = {entry.name: entry for entry in distribution.entry_points if entry.group == "console_scripts"}
for script, target in project.get("scripts", {}).items():
    entry = entry_points.get(script)
    if entry is None or entry.value != target:
        errors.append(f"console script {script!r} is missing or does not target {target!r}")
    elif not callable(entry.load()):
        errors.append(f"console script {script!r} does not load a callable")
for error in errors:
    print(f"[pre-release-check] {error}", file=sys.stderr)
if errors:
    sys.exit(1)
print(f"Installed wheel exposes {len(modules)} modules and {len(entry_points)} console scripts.")
PY
}

## @brief Report whether a path is or contains git-tracked content.
# @details O(tracked entries under path); queries `git ls-files` with
#          literal pathspecs relative to `REPO_ROOT`. A failing query is
#          treated as tracked so deletion fails closed (REQ-288).
# @param path {str} Absolute path below `REPO_ROOT`.
# @return {int} 0 when tracked content exists or the query failed; 1 otherwise.
# @satisfies REQ-288
has_tracked_content() {
  local relative="${1#"$REPO_ROOT"/}"
  local tracked
  if ! tracked="$(git -C "$REPO_ROOT" --literal-pathspecs ls-files -- "$relative")"; then
    return 0
  fi
  [ -n "$tracked" ]
}

## @brief Remove one generated path unless it holds git-tracked content.
# @details O(size of path); absent paths succeed. Tracked content makes the
#          function refuse deletion and report a diagnostic (REQ-288).
# @param path {str} Absolute file or directory path below `REPO_ROOT`.
# @return {int} 0 when the path is absent after the call; 1 otherwise.
# @satisfies REQ-226, REQ-288
remove_generated_path() {
  local target="$1"
  if [ ! -e "$target" ] && [ ! -L "$target" ]; then
    return 0
  fi
  if has_tracked_content "$target"; then
    log_detail "Refusing to remove '$target': it contains git-tracked files"
    return 1
  fi
  if ! rm -rf -- "$target"; then
    log_detail "Unable to remove '$target'"
    return 1
  fi
  return 0
}

## @brief Remove every artifact generated by the validation run.
# @details O(size of artifacts); removes the `build/` and `src/*.egg-info`
#          build intermediates through the tracked-content guard (REQ-288), then
#          removes `.pytest_cache`, `__pycache__` directories under `src/` and
#          `tests/`, and a `.venv` created during the run. A pre-existing
#          `.venv` is preserved (REQ-226, REQ-227). The repository `dist/`
#          directory is never touched (REQ-323).
# @return {int} 0 on complete cleanup; 1 on any failure.
# @satisfies REQ-226, REQ-227, REQ-288, REQ-323
cleanup_generated_artifacts() {
  local failed=0
  local cache_dir search_root intermediate
  local search_roots=()
  for intermediate in "$REPO_ROOT/build" "$REPO_ROOT"/src/*.egg-info; do
    remove_generated_path "$intermediate" || failed=1
  done
  remove_generated_path "$REPO_ROOT/.pytest_cache" || failed=1
  for search_root in "$REPO_ROOT/src" "$REPO_ROOT/tests"; do
    if [ -d "$search_root" ]; then
      search_roots+=("$search_root")
    fi
  done
  if [ "${#search_roots[@]}" -gt 0 ]; then
    if find "${search_roots[@]}" -type d -name __pycache__ -prune -print0 > "$WORK_DIR/pycache.list"; then
      while IFS= read -r -d '' cache_dir; do
        remove_generated_path "$cache_dir" || failed=1
      done < "$WORK_DIR/pycache.list"
    else
      log_detail "Unable to enumerate __pycache__ directories"
      failed=1
    fi
  fi
  if [ "$VENV_PREEXISTED" -ne 1 ]; then
    remove_generated_path "$REPO_ROOT/.venv" || failed=1
  fi
  return "$failed"
}

## @brief Verify the repository equals its pre-run state after cleanup.
# @details O(N log N); fails when a generated build intermediate remains, when
#          the tracked-file fingerprint differs from the baseline, or when any
#          untracked or ignored file absent from the baseline exists outside
#          `.venv` (REQ-298). Every violation is reported with its paths. The
#          repository `dist/` directory is never probed (REQ-323).
# @return {int} 0 when the repository is intact; 1 otherwise.
# @satisfies REQ-223, REQ-298, REQ-323
verify_repository_integrity() {
  local failed=0
  local residue leftovers
  for residue in "$REPO_ROOT/build" "$REPO_ROOT/.pytest_cache" "$REPO_ROOT"/src/*.egg-info; do
    if [ -e "$residue" ]; then
      log_detail "Generated path remains after cleanup: $residue"
      failed=1
    fi
  done
  if [ "$VENV_PREEXISTED" -ne 1 ] && [ -e "$REPO_ROOT/.venv" ]; then
    log_detail "Generated environment remains after cleanup: $REPO_ROOT/.venv"
    failed=1
  fi
  if ! snapshot_tracked_state > "$WORK_DIR/tracked.after"; then
    log_detail "Unable to read the tracked-file state after cleanup"
    failed=1
  elif ! cmp -s "$WORK_DIR/tracked.before" "$WORK_DIR/tracked.after"; then
    log_detail "Tracked files changed during the run (current git status follows):"
    git -C "$REPO_ROOT" --no-optional-locks status --porcelain=v1 --untracked-files=no >&2
    failed=1
  fi
  if ! snapshot_untracked_files > "$WORK_DIR/untracked.after"; then
    log_detail "Unable to read the untracked-file inventory after cleanup"
    failed=1
  elif ! leftovers="$(LC_ALL=C comm -13 "$WORK_DIR/untracked.before" "$WORK_DIR/untracked.after")"; then
    log_detail "Unable to compare the untracked-file inventories"
    failed=1
  elif [ -n "$leftovers" ]; then
    log_detail "Files created during the run remain in the repository:"
    printf '%s\n' "$leftovers" >&2
    failed=1
  fi
  return "$failed"
}

## @brief Convert a termination signal into a recorded failing exit.
# @details O(1); records the interruption and exits with `128+<signal>`,
#          which triggers the `on_exit` cleanup trap (REQ-297). Bash
#          dispatches the trap after the foreground step command ends; when
#          that command handles the signal itself and exits non-zero (pytest
#          on SIGINT), Bash skips the trap and `run_step` reports the step
#          failure with status 1, still followed by cleanup.
# @param signal_name {str} Signal name without the `SIG` prefix.
# @param exit_status {int} Exit status `128+<signal number>`.
# @return Never returns.
# @satisfies REQ-297
on_signal() {
  FAILED_STEP="interrupted by SIG$1 during: $CURRENT_STEP"
  exit "$2"
}

## @brief Report an unexpected command failure outside `run_step`.
# @details O(1); records the current step as failed and prints the failing
#          line number. Subshell invocations are ignored.
# @param line {int} Line number of the failing command.
# @return None; side-effect: diagnostics on stderr.
on_error() {
  if [ "$BASHPID" != "$$" ]; then
    return 0
  fi
  if [ -z "$FAILED_STEP" ]; then
    FAILED_STEP="$CURRENT_STEP"
  fi
  log_detail "Unexpected error at line $1 during: $CURRENT_STEP"
}

## @brief Exit trap: clean up, verify integrity, and print the final result.
# @details Runs on every exit path with termination signals ignored so
#          cleanup completes (REQ-297). When the baseline exists it removes
#          generated artifacts and verifies repository integrity (REQ-226,
#          REQ-298), then removes the snapshot directory. Exit status: the
#          original non-zero status when a step failed or the run was
#          interrupted, 1 when all steps passed but cleanup or verification
#          failed, 0 otherwise (REQ-299). Prints the result line (REQ-300).
# @return Never returns; exits with the resolved status.
# @satisfies REQ-226, REQ-297, REQ-298, REQ-299, REQ-300
on_exit() {
  local status=$?
  local cleanup_failed=0
  trap - EXIT ERR
  trap '' INT TERM HUP
  set +e
  if [ "$BASELINE_READY" -eq 1 ]; then
    log_step "Clean up generated artifacts"
    cleanup_generated_artifacts || cleanup_failed=1
    log_step "Verify repository integrity"
    verify_repository_integrity || cleanup_failed=1
  fi
  if [ -n "$BUILD_DIR" ] && [ -e "$BUILD_DIR" ]; then
    if ! rm -rf -- "$BUILD_DIR"; then
      log_detail "Unable to remove the temporary build directory '$BUILD_DIR'"
      cleanup_failed=1
    fi
  fi
  if [ -n "$WORK_DIR" ] && [ -e "$WORK_DIR" ]; then
    if ! rm -rf -- "$WORK_DIR"; then
      log_detail "Unable to remove the temporary directory '$WORK_DIR'"
      cleanup_failed=1
    fi
  fi
  if [ "$status" -ne 0 ]; then
    if [ "$cleanup_failed" -ne 0 ]; then
      log_detail "Cleanup or repository integrity verification also failed"
    fi
    printf -- '--- [pre-release-check] Result: FAILED (%s) ---\n' "${FAILED_STEP:-$CURRENT_STEP}" >&2
    exit "$status"
  fi
  if [ "$cleanup_failed" -ne 0 ]; then
    printf -- '--- [pre-release-check] Result: FAILED (%s) ---\n' "cleanup and repository integrity verification" >&2
    exit 1
  fi
  log_step "Result: PASSED"
  exit 0
}

trap on_exit EXIT
trap 'on_error "$LINENO"' ERR
trap 'on_signal INT 130' INT
trap 'on_signal TERM 143' TERM
trap 'on_signal HUP 129' HUP

cd -- "$REPO_ROOT"

run_step "Check git availability" check_tool_version git
run_step "Check uv availability" check_tool_version uv
run_step "Validate repository structure" validate_repository_structure
run_step "Check shell script syntax" check_shell_syntax
run_step "Record repository state" record_baseline
run_step "Check dependency lock synchronization" uv lock --check
run_step "Check Python sources and project metadata" check_python_sources
run_step "Check version consistency" check_version_consistency
run_step "Run the full test suite" uv run pytest
run_step "Build release artifacts" build_release_artifacts
run_step "Validate release artifacts" validate_release_artifacts
run_step "Verify wheel installation in an isolated environment" check_wheel_installation
CURRENT_STEP="completion"
log_step "All pre-release checks passed"
