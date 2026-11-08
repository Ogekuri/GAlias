"""HDT unit tests for the `scripts/pre-release-check.sh` release pre-validation script.

HDT artifacts (Generator mode):

- UUT list:
  - `scripts/pre-release-check.sh` script contract (Level 0, static:
    presence, executable permission, Bash syntax)
  - `scripts/pre-release-check.sh` end-to-end step flow (Level 1, subprocess
    with fake `git` and `uv` executables)
- Call graph: `pre-release-check.sh` -> `git --version`, `uv --version`,
  `uv lock --check`, `uv run pytest`, `uv build --out-dir <temporary dir>`.
- External dependencies to isolate: `git` and `uv` executables replaced by
  deterministic fake shims capturing argv payloads; execution working
  directory moved outside the repository.
- Test matrix: script presence/permission (REQ-217), Bash syntax validity
  (REQ-217), cwd-independent repository-root resolution (REQ-218),
  prerequisite and step invocation sequence (REQ-219, REQ-220, REQ-221,
  REQ-222), temporary build directory cleanup (REQ-223), progress and
  success output format (REQ-224), fail-fast abort on the first failing
  step (REQ-225), abort when `git` is missing from PATH (REQ-219).
"""

import os
import shutil
import stat
import subprocess
import tempfile
import unittest
from pathlib import Path


## @brief Test suite for the pre-release validation Bash script.
# @details Validates script contract, step ordering, cwd-independent root
#          resolution, temporary-build cleanup, progress output format, and
#          fail-fast abort semantics via deterministic executable shims.
# @satisfies REQ-217, REQ-218, REQ-219, REQ-220, REQ-221, REQ-222, REQ-223, REQ-224, REQ-225
class PreReleaseCheckScriptTest(unittest.TestCase):
    ## @brief Repository root path used to locate the script under test.
    REPO_ROOT = Path(__file__).resolve().parents[1]
    ## @brief Absolute path of the pre-release-check script under test.
    SCRIPT_PATH = REPO_ROOT / "scripts" / "pre-release-check.sh"

    ## @brief Write an executable shell helper file.
    # @param path {Path} Destination executable path.
    # @param content {str} Script body text encoded as UTF-8.
    # @return None.
    @staticmethod
    def _write_executable(path: Path, content: str) -> None:
        path.write_text(content, encoding="utf-8")
        path.chmod(path.stat().st_mode | stat.S_IXUSR)

    ## @brief Build fake `git` and `uv` executables plus an isolated PATH env.
    # @details The fake `uv` appends one argv block per invocation to
    #          `$UV_CAPTURE_FILE` separated by `--STEP--` markers and fails
    #          its first invocation only when `$UV_FAIL_FIRST` is set.
    # @param temp_root {Path} Directory receiving `bin/` and capture files.
    # @param include_git {bool} When True, a fake `git` shim is provided.
    # @param minimal_path {bool} When True, PATH contains only `fake_bin` and
    #        coreutil shims (`dirname`, `mktemp`, `rm`) are provided so the
    #        script reaches the `git` prerequisite step.
    # @return Tuple `(env, capture_path)` with the isolated environment and
    #         the uv argv capture file path.
    def _make_fake_environment(self, temp_root: Path, include_git: bool = True, minimal_path: bool = False):
        fake_bin = temp_root / "bin"
        fake_bin.mkdir()
        capture_path = temp_root / "uv-args.txt"
        fake_uv = fake_bin / "uv"
        self._write_executable(
            fake_uv,
            "#!/bin/sh\n"
            "{\n"
            "  printf '%s\\n' \"$@\"\n"
            "  printf '%s\\n' '--STEP--'\n"
            "} >> \"$UV_CAPTURE_FILE\"\n"
            "if [ -n \"${UV_FAIL_FIRST:-}\" ] && [ ! -e \"$UV_FAIL_MARKER\" ]; then\n"
            "  : > \"$UV_FAIL_MARKER\"\n"
            "  exit 1\n"
            "fi\n"
            "exit 0\n",
        )
        if include_git:
            fake_git = fake_bin / "git"
            self._write_executable(fake_git, "#!/bin/sh\nexit 0\n")
        if minimal_path:
            self._write_executable(
                fake_bin / "dirname",
                "#!/bin/sh\nprintf '%s\\n' \"${1%/*}\"\nexit 0\n",
            )
            self._write_executable(
                fake_bin / "mktemp",
                "#!/bin/sh\nprintf '%s\\n' \"$MKTEMP_DIR\"\nexit 0\n",
            )
            self._write_executable(fake_bin / "rm", "#!/bin/sh\nexit 0\n")

        env = os.environ.copy()
        # Isolation: BASH_ENV would re-source a user rc file inside the
        # non-interactive script bash, defeating fake-bin PATH injection.
        env.pop("BASH_ENV", None)
        if minimal_path:
            env["PATH"] = fake_bin.as_posix()
            env["MKTEMP_DIR"] = str(temp_root / "build-out")
        else:
            env["PATH"] = f"{fake_bin.as_posix()}:{env.get('PATH', '')}"
        env["UV_CAPTURE_FILE"] = str(capture_path)
        env["UV_FAIL_MARKER"] = str(temp_root / "uv-fail-marker")
        return env, capture_path

    ## @brief Split captured uv argv blocks into per-invocation lists.
    # @param capture_path {Path} Capture file written by the fake `uv` shim.
    # @return {list[list[str]]} One argv list per `uv` invocation.
    @staticmethod
    def _split_uv_invocations(capture_path: Path) -> list:
        lines = capture_path.read_text(encoding="utf-8").splitlines()
        invocations = []
        current = []
        for line in lines:
            if line == "--STEP--":
                invocations.append(current)
                current = []
            else:
                current.append(line)
        return invocations

    ## @brief Run the script with the given environment and working directory.
    # @param env {dict} Environment mapping passed to the subprocess.
    # @param cwd {Path} Working directory for the script invocation.
    # @return CompletedProcess with captured stdout/stderr as text.
    def _run_script(self, env, cwd: Path):
        return subprocess.run(
            ["bash", str(self.SCRIPT_PATH)],
            cwd=str(cwd),
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )

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

    ## @brief Verify full step sequence, cleanup, and output from any cwd.
    # @details Executes the script from a temporary working directory with
    #          fake `git`/`uv` shims, asserting the exact invocation order
    #          (`uv --version`, `uv lock --check`, `uv run pytest`,
    #          `uv build --out-dir`), removal of the temporary build
    #          directory at exit, and canonical progress plus success lines.
    # @return None.
    # @satisfies REQ-218, REQ-219, REQ-220, REQ-221, REQ-222, REQ-223, REQ-224
    def test_script_executes_full_step_sequence_from_any_working_directory(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            # Arrange
            temp_root = Path(tmp_dir)
            env, capture_path = self._make_fake_environment(temp_root)
            outside_cwd = temp_root / "elsewhere"
            outside_cwd.mkdir()
            # Act
            completed = self._run_script(env, outside_cwd)
            # Assert
            self.assertEqual(completed.returncode, 0, msg=completed.stderr)
            invocations = self._split_uv_invocations(capture_path)
            self.assertEqual(len(invocations), 4)
            self.assertEqual(invocations[0], ["--version"])
            self.assertEqual(invocations[1], ["lock", "--check"])
            self.assertEqual(invocations[2], ["run", "pytest"])
            self.assertEqual(invocations[3][0], "build")
            self.assertEqual(invocations[3][1], "--out-dir")
            build_dir = Path(invocations[3][2])
            self.assertTrue(build_dir.name.startswith("tmp"))
            self.assertFalse(build_dir.exists())
            self.assertIn("--- [pre-release-check] Check git availability ---", completed.stdout)
            self.assertIn("--- [pre-release-check] Check uv availability ---", completed.stdout)
            self.assertIn(
                "--- [pre-release-check] Check dependency lock synchronization ---",
                completed.stdout,
            )
            self.assertIn("--- [pre-release-check] Run the full test suite ---", completed.stdout)
            self.assertIn(
                "--- [pre-release-check] Build distributions into a temporary directory ---",
                completed.stdout,
            )
            self.assertIn(
                "--- [pre-release-check] All pre-release checks passed ---",
                completed.stdout,
            )

    ## @brief Verify fail-fast abort when the first `uv` step fails.
    # @details Forces the fake `uv` to fail its first invocation (`--version`
    #          prerequisite step) so the script must exit non-zero, print a
    #          step-failed diagnostic, skip the success line, and never
    #          invoke `uv` again.
    # @return None.
    # @satisfies REQ-219, REQ-225
    def test_script_aborts_at_first_failing_step(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            # Arrange
            temp_root = Path(tmp_dir)
            env, capture_path = self._make_fake_environment(temp_root)
            env["UV_FAIL_FIRST"] = "1"
            # Act
            completed = self._run_script(env, self.REPO_ROOT)
            # Assert
            self.assertNotEqual(completed.returncode, 0)
            self.assertIn(
                "--- [pre-release-check] Step failed: Check uv availability ---",
                completed.stderr,
            )
            self.assertNotIn("All pre-release checks passed", completed.stdout)
            invocations = self._split_uv_invocations(capture_path)
            self.assertEqual(invocations, [["--version"]])

    ## @brief Verify abort with explicit English error when git is missing.
    # @details Restricts PATH to a fake bin directory containing no `git`
    #          shim so the prerequisite step must fail before any `uv`
    #          invocation.
    # @return None.
    # @satisfies REQ-219, REQ-225
    def test_script_aborts_when_git_is_missing(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            # Arrange
            temp_root = Path(tmp_dir)
            env, capture_path = self._make_fake_environment(temp_root, include_git=False, minimal_path=True)
            env["PATH"] = (temp_root / "bin").as_posix()
            bash_exe = shutil.which("bash")
            self.assertIsNotNone(bash_exe)
            assert bash_exe is not None  # Type narrowing for static analysis.
            # Act
            completed = subprocess.run(
                [bash_exe, str(self.SCRIPT_PATH)],
                cwd=str(self.REPO_ROOT),
                env=env,
                capture_output=True,
                text=True,
                check=False,
            )
            # Assert
            self.assertNotEqual(completed.returncode, 0)
            self.assertIn(
                "--- [pre-release-check] Step failed: Check git availability ---",
                completed.stderr,
            )
            self.assertFalse(capture_path.exists())


if __name__ == "__main__":
    unittest.main()
