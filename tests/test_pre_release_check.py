"""HDT unit tests for the `scripts/pre-release-check.sh` release-readiness script.

HDT artifacts (Refactorer mode):

- Audit: the previous suite executed the script against the real repository
  root with fake `git`/`uv` shims, so script side effects (cache and artifact
  removal) reached real user paths and coupled the suite to repository
  state. The suite now runs script copies inside a throwaway git sandbox.
- UUT list:
  - `scripts/pre-release-check.sh` script contract (Level 0, static:
    presence, executable permission, Bash syntax)
  - `scripts/pre-release-check.sh` prerequisite and guard steps (Level 1,
    subprocess in a sandbox repository)
  - `scripts/pre-release-check.sh` full step flow, cleanup, and integrity
    verification (Level 2, subprocess composing `scripts/build.sh`)
- Call graph: `pre-release-check.sh` -> `git --version`, `uv --version`,
  `validate_repository_structure`, `check_shell_syntax`,
  `remove_preexisting_artifacts` -> `build.sh --clean`,
  `check_preexisting_artifacts` -> `build.sh --list-artifacts`,
  `record_baseline`, `uv lock --check`, `uv run python` checks,
  `uv run pytest`, `build.sh`, artifact validation steps, `on_exit` ->
  `cleanup_generated_artifacts` -> `build.sh --clean`,
  `verify_repository_integrity`.
- External dependencies to isolate: `uv` replaced by a deterministic fake;
  repository replaced by a temporary git sandbox; `HOME`, `TMPDIR`, and git
  configuration redirected to temporary paths; process interruption
  synchronized through a FIFO instead of timing.
- Test matrix: script contract (REQ-217); full step sequence, progress
  output, and zero residue from a foreign working directory (REQ-218,
  REQ-220, REQ-221, REQ-222, REQ-224, REQ-226, REQ-227, REQ-300);
  preservation of pre-existing content (REQ-223, REQ-227, REQ-298);
  fail-fast on the first failing step (REQ-219, REQ-225); missing `git`
  and missing `uv` (REQ-219); pre-existing artifact removal through
  `build.sh --clean` and its effective-removal verification (REQ-290,
  REQ-323);
  failing tests, failing build, and missing artifact with cleanup
  (REQ-225, REQ-226, REQ-299); leftover file, modified tracked file, and
  tracked cleanup target (REQ-288, REQ-298, REQ-299); signal interruption
  (REQ-297).
- Execution plan: CI runs the suite through `uv run pytest`; developers
  run `uv run pytest tests/test_pre_release_check.py`.
"""

import os
import select
import shutil
import signal
import stat
import subprocess
import tempfile
import unittest
from pathlib import Path

from release_scripts_support import REPO_ROOT, create_sandbox, write_executable


## @brief Test suite for the pre-release validation Bash script.
# @details Validates the script contract, step ordering, cwd-independent
#          root resolution, fail-fast semantics, guaranteed cleanup,
#          repository-integrity verification, and signal handling inside
#          hermetic sandbox repositories.
# @satisfies REQ-217, REQ-218, REQ-219, REQ-220, REQ-221, REQ-222, REQ-223, REQ-224, REQ-225, REQ-226, REQ-227, REQ-288, REQ-290, REQ-297, REQ-298, REQ-299, REQ-300, REQ-323
class PreReleaseCheckScriptTest(unittest.TestCase):
    ## @brief Absolute path of the real pre-release-check script under test.
    SCRIPT_PATH = REPO_ROOT / "scripts" / "pre-release-check.sh"
    ## @brief Script filename inside sandbox repositories.
    SCRIPT_NAME = "pre-release-check.sh"

    ## @brief Assert a failed run left the sandbox without generated residue.
    # @param sandbox {ReleaseSandbox} Sandbox inspected after the run.
    # @return None.
    def _assert_sandbox_clean(self, sandbox) -> None:
        self.assertEqual(sandbox.untracked_files(), [])
        self.assertEqual(sandbox.git("status", "--porcelain"), "")
        self.assertFalse((sandbox.repo / "dist").exists())
        self.assertFalse((sandbox.repo / ".venv").exists())
        self.assertEqual(sandbox.temp_entries(), [])

    ## @brief Run the script with a failing fake `uv` step and assert cleanup.
    # @param overrides {dict[str, str]} Fake `uv` behavior switches.
    # @param failed_step {str} Expected failed step description.
    # @return {ReleaseSandbox-bound list} Fake `uv` invocations of the run.
    def _assert_step_failure_with_cleanup(self, overrides: dict, failed_step: str) -> list:
        with tempfile.TemporaryDirectory() as tmp_dir:
            # Arrange
            sandbox = create_sandbox(Path(tmp_dir))
            env = dict(sandbox.env, **overrides)
            # Act
            completed = sandbox.run(self.SCRIPT_NAME, env=env)
            # Assert
            self.assertEqual(completed.returncode, 1, msg=completed.stderr)
            self.assertIn(f"--- [pre-release-check] Step failed: {failed_step} ---", completed.stderr)
            self.assertIn(f"--- [pre-release-check] Result: FAILED ({failed_step}) ---", completed.stderr)
            self.assertNotIn("All pre-release checks passed", completed.stdout)
            self.assertNotIn("Result: PASSED", completed.stdout)
            self.assertIn("--- [pre-release-check] Clean up generated artifacts ---", completed.stdout)
            self._assert_sandbox_clean(sandbox)
            return sandbox.uv_invocations()

    ## @brief Verify the script exists with the executable permission bit.
    # @return None.
    # @satisfies REQ-217
    def test_script_exists_and_is_executable(self):
        # Arrange
        expected_exists = True
        # Act
        actual_exists = self.SCRIPT_PATH.is_file()
        actual_executable = os.access(self.SCRIPT_PATH, os.X_OK)
        # Assert
        self.assertEqual(actual_exists, expected_exists)
        self.assertTrue(actual_executable)
        mode = self.SCRIPT_PATH.stat().st_mode
        self.assertTrue(mode & stat.S_IXUSR)

    ## @brief Verify the script parses as valid Bash with no syntax errors.
    # @return None.
    # @satisfies REQ-217
    def test_script_passes_bash_syntax_check(self):
        # Arrange
        expected_returncode = 0
        # Act
        completed = subprocess.run(
            ["bash", "-n", str(self.SCRIPT_PATH)],
            capture_output=True,
            text=True,
            check=False,
        )
        # Assert
        self.assertEqual(completed.returncode, expected_returncode, msg=completed.stderr)

    ## @brief Verify fail-fast abort when the first `uv` step fails.
    # @details The failing `uv --version` prerequisite precedes the baseline,
    #          so no cleanup runs and `uv` is never invoked again.
    # @return None.
    # @satisfies REQ-219, REQ-225, REQ-300
    def test_script_aborts_at_first_failing_step(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            # Arrange
            sandbox = create_sandbox(Path(tmp_dir))
            env = dict(sandbox.env, UV_FAIL_MATCH=" --version ")
            expected_invocations = [["--version"]]
            # Act
            completed = sandbox.run(self.SCRIPT_NAME, env=env)
            # Assert
            self.assertNotEqual(completed.returncode, 0)
            self.assertIn("--- [pre-release-check] Step failed: Check uv availability ---", completed.stderr)
            self.assertIn("--- [pre-release-check] Result: FAILED (Check uv availability) ---", completed.stderr)
            self.assertNotIn("All pre-release checks passed", completed.stdout)
            self.assertNotIn("Clean up generated artifacts", completed.stdout)
            self.assertEqual(sandbox.uv_invocations(), expected_invocations)

    ## @brief Verify abort with an explicit error when `git` is missing.
    # @details PATH holds only the fake `uv`, so the `git` prerequisite step
    #          fails before any `uv` invocation.
    # @return None.
    # @satisfies REQ-219, REQ-225
    def test_script_aborts_when_git_is_missing(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            # Arrange
            sandbox = create_sandbox(Path(tmp_dir))
            env = dict(sandbox.env, PATH=sandbox.fake_bin.as_posix())
            bash_exe = shutil.which("bash")
            self.assertIsNotNone(bash_exe)
            assert bash_exe is not None  # Type narrowing for static analysis.
            # Act
            completed = subprocess.run(
                [bash_exe, str(sandbox.script(self.SCRIPT_NAME))],
                cwd=str(sandbox.repo),
                env=env,
                capture_output=True,
                text=True,
                check=False,
            )
            # Assert
            self.assertNotEqual(completed.returncode, 0)
            self.assertIn("--- [pre-release-check] Step failed: Check git availability ---", completed.stderr)
            self.assertIn("[pre-release-check] Required tool 'git' was not found in PATH", completed.stderr)
            self.assertIn("--- [pre-release-check] Result: FAILED (Check git availability) ---", completed.stderr)
            self.assertNotIn("command not found", completed.stderr)
            self.assertEqual(sandbox.uv_invocations(), [])

    ## @brief Verify abort with an explicit error when `uv` is missing.
    # @details PATH holds only a `git` shim, so the `uv` prerequisite step
    #          fails immediately after the `git` step.
    # @return None.
    # @satisfies REQ-219, REQ-225
    def test_script_aborts_when_uv_is_missing(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            # Arrange
            sandbox = create_sandbox(Path(tmp_dir))
            git_only_bin = Path(tmp_dir) / "git-only-bin"
            git_only_bin.mkdir()
            write_executable(git_only_bin / "git", "#!/bin/sh\nexit 0\n")
            env = dict(sandbox.env, PATH=git_only_bin.as_posix())
            bash_exe = shutil.which("bash")
            self.assertIsNotNone(bash_exe)
            assert bash_exe is not None  # Type narrowing for static analysis.
            # Act
            completed = subprocess.run(
                [bash_exe, str(sandbox.script(self.SCRIPT_NAME))],
                cwd=str(sandbox.repo),
                env=env,
                capture_output=True,
                text=True,
                check=False,
            )
            # Assert
            self.assertNotEqual(completed.returncode, 0)
            self.assertIn("--- [pre-release-check] Step failed: Check uv availability ---", completed.stderr)
            self.assertIn("[pre-release-check] Required tool 'uv' was not found in PATH", completed.stderr)
            self.assertIn("--- [pre-release-check] Result: FAILED (Check uv availability) ---", completed.stderr)
            self.assertNotIn("command not found", completed.stderr)
            self.assertEqual(sandbox.uv_invocations(), [])

    ## @brief Verify pre-existing release artifacts are removed before the baseline.
    # @details Untracked and git-tracked release artifacts of any version are
    #          removed through `build.sh --clean` before the baseline, the
    #          removal is verified through `build.sh --list-artifacts`, the
    #          non-generated `dist/` file survives, and the run passes.
    # @return None.
    # @satisfies REQ-290, REQ-323
    def test_script_removes_preexisting_release_artifacts(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            # Arrange
            sandbox = create_sandbox(Path(tmp_dir))
            dist = sandbox.repo / "dist"
            dist.mkdir()
            stale_sdist = dist / "galias-0.0.1.tar.gz"
            stale_wheel = dist / "galias-0.0.2-py3-none-any.whl"
            stale_sdist.write_text("stale", encoding="utf-8")
            stale_wheel.write_text("tracked", encoding="utf-8")
            notes = dist / "NOTES.md"
            notes.write_text("notes", encoding="utf-8")
            sandbox.git("add", "--force", "dist/galias-0.0.2-py3-none-any.whl")
            sandbox.git("commit", "-q", "-m", "track stale wheel")
            expected_dist_entries = ["NOTES.md"]
            # Act
            completed = sandbox.run(self.SCRIPT_NAME)
            # Assert
            self.assertEqual(completed.returncode, 0, msg=completed.stderr)
            self.assertIn("--- [pre-release-check] Remove pre-existing release artifacts ---", completed.stdout)
            self.assertIn("--- [pre-release-check] Check for pre-existing release artifacts ---", completed.stdout)
            self.assertIn("--- [pre-release-check] Result: PASSED ---", completed.stdout)
            self.assertFalse(stale_sdist.exists())
            self.assertFalse(stale_wheel.exists())
            self.assertEqual(sorted(entry.name for entry in dist.iterdir()), expected_dist_entries)
            self.assertEqual(notes.read_text(encoding="utf-8"), "notes")
            self.assertEqual(sandbox.temp_entries(), [])

    ## @brief Verify a failing artifact removal aborts the run.
    # @details The sandbox build script fails on `--clean`, so the removal
    #          step reports the failure before the baseline and no `uv` step
    #          beyond the version probe executes.
    # @return None.
    # @satisfies REQ-225, REQ-290
    def test_script_aborts_when_artifact_removal_fails(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            # Arrange
            sandbox = create_sandbox(Path(tmp_dir))
            write_executable(sandbox.script("build.sh"), "#!/bin/sh\nexit 1\n")
            expected_invocations = [["--version"]]
            # Act
            completed = sandbox.run(self.SCRIPT_NAME)
            # Assert
            self.assertEqual(completed.returncode, 1)
            self.assertIn(
                "--- [pre-release-check] Step failed: Remove pre-existing release artifacts ---",
                completed.stderr,
            )
            self.assertIn(
                "--- [pre-release-check] Result: FAILED (Remove pre-existing release artifacts) ---",
                completed.stderr,
            )
            self.assertEqual(sandbox.uv_invocations(), expected_invocations)

    ## @brief Verify surviving artifacts fail the effective-removal check.
    # @details The sandbox build script succeeds on `--clean` but still lists
    #          a release artifact, so the verification step reports every
    #          surviving path and aborts before the baseline.
    # @return None.
    # @satisfies REQ-225, REQ-323
    def test_script_aborts_when_artifacts_survive_removal(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            # Arrange
            sandbox = create_sandbox(Path(tmp_dir))
            stub = "\n".join(
                (
                    "#!/bin/sh",
                    'case "${1:-}" in',
                    "  --list-artifacts)",
                    "    printf '%s\\n' 'dist/galias-0.0.1.tar.gz'",
                    "    ;;",
                    "esac",
                    "exit 0",
                    "",
                )
            )
            write_executable(sandbox.script("build.sh"), stub)
            expected_invocations = [["--version"]]
            # Act
            completed = sandbox.run(self.SCRIPT_NAME)
            # Assert
            self.assertEqual(completed.returncode, 1)
            self.assertIn(
                "--- [pre-release-check] Step failed: Check for pre-existing release artifacts ---",
                completed.stderr,
            )
            self.assertIn("Pre-existing release artifacts remain after removal", completed.stderr)
            self.assertIn("dist/galias-0.0.1.tar.gz", completed.stderr)
            self.assertEqual(sandbox.uv_invocations(), expected_invocations)

    ## @brief Verify the full step sequence, output, and zero residue.
    # @details Executes from a foreign working directory against a sandbox
    #          path containing a space; asserts the exact `uv` invocation
    #          order, canonical progress and result lines, and a sandbox
    #          free of artifacts, caches, `.venv`, and temporary directories.
    # @return None.
    # @satisfies REQ-218, REQ-219, REQ-220, REQ-221, REQ-222, REQ-224, REQ-226, REQ-227, REQ-300
    def test_script_executes_full_step_sequence_from_any_working_directory(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            # Arrange
            sandbox = create_sandbox(Path(tmp_dir))
            outside_cwd = Path(tmp_dir) / "elsewhere"
            outside_cwd.mkdir()
            dist = sandbox.repo / "dist"
            expected_sdist = str(dist / "galias-1.2.3.tar.gz")
            expected_wheel = str(dist / "galias-1.2.3-py3-none-any.whl")
            expected_progress = [
                "Check git availability",
                "Check uv availability",
                "Validate repository structure",
                "Check shell script syntax",
                "Remove pre-existing release artifacts",
                "Check for pre-existing release artifacts",
                "Record repository state",
                "Check dependency lock synchronization",
                "Check Python sources and project metadata",
                "Check version consistency",
                "Run the full test suite",
                "Build release artifacts",
                "Validate release artifacts",
                "Verify release artifacts are not ignored by git",
                "Verify wheel installation in an isolated environment",
                "All pre-release checks passed",
                "Clean up generated artifacts",
                "Verify repository integrity",
                "Result: PASSED",
            ]
            # Act
            completed = sandbox.run(self.SCRIPT_NAME, cwd=outside_cwd)
            # Assert
            self.assertEqual(completed.returncode, 0, msg=completed.stderr)
            invocations = sandbox.uv_invocations()
            self.assertEqual(len(invocations), 8)
            self.assertEqual(invocations[0], ["--version"])
            self.assertEqual(invocations[1], ["lock", "--check"])
            self.assertEqual(invocations[2], ["run", "python", "-", str(sandbox.repo)])
            self.assertEqual(invocations[3][:3], ["run", "python", "-c"])
            self.assertIn('main(["ver"], check_updates=False)', invocations[3][3])
            self.assertEqual(invocations[4], ["run", "pytest"])
            self.assertEqual(invocations[5][:2], ["build", "--out-dir"])
            self.assertEqual(
                invocations[6],
                ["run", "python", "-", str(sandbox.repo), expected_sdist, expected_wheel],
            )
            self.assertEqual(
                invocations[7],
                ["run", "--isolated", "--no-project", "--with", expected_wheel, "python", "-", str(sandbox.repo)],
            )
            progress = [
                line[len("--- [pre-release-check] "):-len(" ---")]
                for line in completed.stdout.splitlines()
                if line.startswith("--- [pre-release-check] ")
            ]
            self.assertEqual(progress, expected_progress)
            self._assert_sandbox_clean(sandbox)

    ## @brief Verify pre-existing repository content survives a passing run.
    # @details A dirty tracked file, a pre-existing `.venv`, and a
    #          non-generated `dist/` file keep their exact content while
    #          generated artifacts are removed.
    # @return None.
    # @satisfies REQ-223, REQ-227, REQ-298
    def test_script_preserves_preexisting_repository_content(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            # Arrange
            sandbox = create_sandbox(Path(tmp_dir))
            readme = sandbox.repo / "README.md"
            readme.write_text("locally modified\n", encoding="utf-8")
            venv_marker = sandbox.repo / ".venv" / "keep.txt"
            venv_marker.parent.mkdir()
            venv_marker.write_text("environment", encoding="utf-8")
            notes = sandbox.repo / "dist" / "NOTES.md"
            notes.parent.mkdir()
            notes.write_text("notes", encoding="utf-8")
            expected_status = " M README.md\n?? dist/NOTES.md\n"
            # Act
            completed = sandbox.run(self.SCRIPT_NAME)
            # Assert
            self.assertEqual(completed.returncode, 0, msg=completed.stderr)
            self.assertIn("--- [pre-release-check] Result: PASSED ---", completed.stdout)
            self.assertEqual(sandbox.git("status", "--porcelain", "--untracked-files=all"), expected_status)
            self.assertEqual(readme.read_text(encoding="utf-8"), "locally modified\n")
            self.assertEqual(venv_marker.read_text(encoding="utf-8"), "environment")
            self.assertEqual(notes.read_text(encoding="utf-8"), "notes")
            self.assertEqual(sorted(entry.name for entry in notes.parent.iterdir()), ["NOTES.md"])
            self.assertEqual(sandbox.temp_entries(), [])

    ## @brief Verify a failing test suite aborts before the build and cleans up.
    # @return None.
    # @satisfies REQ-221, REQ-225, REQ-226, REQ-299
    def test_script_cleans_up_when_test_suite_fails(self):
        # Arrange
        overrides = {"UV_FAIL_MATCH": " pytest "}
        # Act
        invocations = self._assert_step_failure_with_cleanup(overrides, "Run the full test suite")
        # Assert
        self.assertEqual(invocations[-1], ["run", "pytest"])
        self.assertNotIn("build", [invocation[0] for invocation in invocations])

    ## @brief Verify a failing build aborts the run and cleans up.
    # @return None.
    # @satisfies REQ-222, REQ-225, REQ-226, REQ-299
    def test_script_cleans_up_when_build_fails(self):
        # Arrange
        overrides = {"UV_FAIL_MATCH": " build "}
        # Act
        invocations = self._assert_step_failure_with_cleanup(overrides, "Build release artifacts")
        # Assert
        self.assertEqual(invocations[-1][0], "build")

    ## @brief Verify a missing expected artifact aborts the run and cleans up.
    # @return None.
    # @satisfies REQ-222, REQ-225, REQ-226, REQ-299
    def test_script_cleans_up_when_expected_artifact_is_missing(self):
        # Arrange
        overrides = {"UV_BUILD_OMIT": "wheel"}
        # Act
        invocations = self._assert_step_failure_with_cleanup(overrides, "Build release artifacts")
        # Assert
        self.assertEqual(invocations[-1][0], "build")

    ## @brief Verify a file left behind by a step fails the run after cleanup.
    # @details Every step passes; the integrity verification reports the
    #          stray ignored file and converts the result into a failure.
    # @return None.
    # @satisfies REQ-298, REQ-299, REQ-300
    def test_script_fails_when_a_generated_file_remains_after_cleanup(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            # Arrange
            sandbox = create_sandbox(Path(tmp_dir))
            env = dict(sandbox.env, UV_STRAY_FILE="stray-output.bin")
            expected_returncode = 1
            # Act
            completed = sandbox.run(self.SCRIPT_NAME, env=env)
            # Assert
            self.assertEqual(completed.returncode, expected_returncode)
            self.assertIn("All pre-release checks passed", completed.stdout)
            self.assertNotIn("Result: PASSED", completed.stdout)
            self.assertIn("stray-output.bin", completed.stderr)
            self.assertIn(
                "--- [pre-release-check] Result: FAILED (cleanup and repository integrity verification) ---",
                completed.stderr,
            )

    ## @brief Verify an ignored release artifact fails the release check.
    # @details Appends a root `/dist/` rule to the sandbox `.gitignore` so git
    #          ignores the built artifacts; the run fails at the not-ignored step
    #          and reports that step as the failed result.
    # @return None.
    # @satisfies REQ-295, REQ-299, REQ-300
    def test_script_fails_when_release_artifacts_are_ignored(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            # Arrange
            sandbox = create_sandbox(Path(tmp_dir))
            gitignore = sandbox.repo / ".gitignore"
            gitignore.write_text(gitignore.read_text(encoding="utf-8") + "\n/dist/\n", encoding="utf-8")
            expected_returncode = 1
            # Act
            completed = sandbox.run(self.SCRIPT_NAME)
            # Assert
            self.assertEqual(completed.returncode, expected_returncode)
            self.assertIn("is ignored by git", completed.stderr)
            self.assertIn(
                "--- [pre-release-check] Result: FAILED (Verify release artifacts are not ignored by git) ---",
                completed.stderr,
            )
            self.assertNotIn("Result: PASSED", completed.stdout)

    ## @brief Verify a tracked file modified by a step fails the run.
    # @return None.
    # @satisfies REQ-223, REQ-298, REQ-299
    def test_script_fails_when_a_tracked_file_is_modified(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            # Arrange
            sandbox = create_sandbox(Path(tmp_dir))
            env = dict(sandbox.env, UV_TOUCH_TRACKED="README.md")
            expected_returncode = 1
            # Act
            completed = sandbox.run(self.SCRIPT_NAME, env=env)
            # Assert
            self.assertEqual(completed.returncode, expected_returncode)
            self.assertIn("Tracked files changed during the run", completed.stderr)
            self.assertIn(" M README.md", completed.stderr)
            self.assertNotIn("Result: PASSED", completed.stdout)

    ## @brief Verify cleanup refuses to delete git-tracked content.
    # @details A tracked file inside a `__pycache__` cleanup target survives
    #          and the refusal converts the passing run into a failure.
    # @return None.
    # @satisfies REQ-288, REQ-299
    def test_script_fails_when_cleanup_target_holds_tracked_files(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            # Arrange
            sandbox = create_sandbox(Path(tmp_dir))
            tracked = sandbox.repo / "src" / "git_alias" / "__pycache__" / "tracked.pyc"
            tracked.parent.mkdir()
            tracked.write_text("tracked", encoding="utf-8")
            sandbox.git("add", "--force", "src/git_alias/__pycache__/tracked.pyc")
            sandbox.git("commit", "-q", "-m", "track cache file")
            expected_returncode = 1
            # Act
            completed = sandbox.run(self.SCRIPT_NAME)
            # Assert
            self.assertEqual(completed.returncode, expected_returncode)
            self.assertIn("Refusing to remove", completed.stderr)
            self.assertEqual(tracked.read_text(encoding="utf-8"), "tracked")
            self.assertNotIn("Result: PASSED", completed.stdout)

    ## @brief Verify termination signals trigger cleanup and `128+N` exit.
    # @details The fake `uv` blocks inside the pytest step after signalling
    #          readiness through a FIFO (bounded wait, no polling); the
    #          signal targets the whole process group, mirroring a terminal
    #          interrupt.
    # @return None.
    # @satisfies REQ-226, REQ-297, REQ-300
    @unittest.skipIf(os.name == "nt", "POSIX process groups and FIFOs are required")
    def test_script_cleans_up_when_interrupted_by_signal(self):
        for signal_number, expected_returncode, signal_name in (
            (signal.SIGINT, 130, "SIGINT"),
            (signal.SIGTERM, 143, "SIGTERM"),
        ):
            with self.subTest(signal=signal_name), tempfile.TemporaryDirectory() as tmp_dir:
                # Arrange
                sandbox = create_sandbox(Path(tmp_dir))
                fifo_path = Path(tmp_dir) / "ready.fifo"
                os.mkfifo(fifo_path)
                # O_RDWR keeps the FIFO open so neither side blocks on open.
                ready_fd = os.open(fifo_path, os.O_RDWR)
                self.addCleanup(os.close, ready_fd)
                env = dict(sandbox.env, UV_BLOCK_FIFO=str(fifo_path))
                process = subprocess.Popen(
                    ["bash", str(sandbox.script(self.SCRIPT_NAME))],
                    cwd=str(sandbox.repo),
                    env=env,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    start_new_session=True,
                )
                readable, _, _ = select.select([ready_fd], [], [], 120)
                self.assertEqual(readable, [ready_fd], msg="pytest step was never reached")
                # Act
                os.killpg(process.pid, signal_number)
                stdout, stderr = process.communicate(timeout=120)
                # Assert
                self.assertEqual(process.returncode, expected_returncode, msg=stderr)
                self.assertIn(
                    f"--- [pre-release-check] Result: FAILED (interrupted by {signal_name} "
                    "during: Run the full test suite) ---",
                    stderr,
                )
                self.assertIn("--- [pre-release-check] Clean up generated artifacts ---", stdout)
                self._assert_sandbox_clean(sandbox)


if __name__ == "__main__":
    unittest.main()
