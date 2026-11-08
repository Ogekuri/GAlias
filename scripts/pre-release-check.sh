#!/usr/bin/env bash
## @file pre-release-check.sh
# @brief Repository-local official-release pre-validation script.
# @details Executes, in strict order: prerequisite availability checks for
#          `git` and Astral `uv` (REQ-219), dependency-lock synchronization
#          verification via `uv lock --check` (REQ-220), the complete pytest
#          suite via `uv run pytest` (REQ-221), and a distribution build via
#          `uv build` into a temporary output directory (REQ-222). The script
#          resolves the repository root from its own location so it can be
#          invoked from any working directory (REQ-218), prints one canonical
#          English progress line per step plus a final success line (REQ-224),
#          aborts fail-fast with non-zero exit at the first failing step
#          (REQ-225), and removes the temporary build directory at exit
#          without modifying tracked repository files (REQ-223).
# @satisfies REQ-217, REQ-218, REQ-219, REQ-220, REQ-221, REQ-222, REQ-223, REQ-224, REQ-225

set -euo pipefail

## @brief Absolute path of this script, used to derive the repository root.
SCRIPT_PATH="${BASH_SOURCE[0]}"
## @brief Resolved repository root; every validation step executes from here (REQ-218).
REPO_ROOT="$(cd "$(dirname "$SCRIPT_PATH")/.." && pwd)"
## @brief Temporary output directory receiving `uv build` artifacts (REQ-222).
BUILD_DIR="$(mktemp -d)"

## @brief Remove the temporary build directory when the script exits.
# @details Registered as an EXIT trap so artifacts are cleaned on success,
#          failure, and interruption alike; no tracked repository file is
#          ever modified (REQ-223).
# @return None; side-effect: filesystem removal of "$BUILD_DIR".
cleanup_build_dir() {
  rm -rf "$BUILD_DIR"
}
trap cleanup_build_dir EXIT

## @brief Print one canonical pre-release-check progress line.
# @param message {str} English step description or outcome rendered in the line.
# @return None; side-effect: one stdout line formatted per REQ-224.
log_step() {
  printf -- "--- [pre-release-check] %s ---\n" "$1"
}

## @brief Execute one validation step with fail-fast semantics.
# @details Prints the canonical progress line, runs the command argv from the
#          repository root, and aborts the whole script with exit status 1 on
#          the first failure so subsequent steps never execute (REQ-225).
# @param message {str} English step description printed before execution.
# @param ... Command argv executed from "$REPO_ROOT".
# @return Never returns when the step fails; returns otherwise.
run_step() {
  local message="$1"
  shift
  log_step "$message"
  if ! (cd "$REPO_ROOT" && "$@"); then
    printf -- "--- [pre-release-check] Step failed: %s ---\n" "$message" >&2
    exit 1
  fi
}

run_step "Check git availability" git --version
run_step "Check uv availability" uv --version
run_step "Check dependency lock synchronization" uv lock --check
run_step "Run the full test suite" uv run pytest
run_step "Build distributions into a temporary directory" uv build --out-dir "$BUILD_DIR"
log_step "All pre-release checks passed"
