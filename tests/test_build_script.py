"""HDT unit tests for the `scripts/build.sh` release-artifact build script.

HDT artifacts (Generator mode):

- UUT list:
  - `scripts/build.sh` script contract (Level 0, static: presence,
    executable permission, Bash syntax)
  - `scripts/build.sh` option modes `--list-artifacts`, `--clean`, and
    unknown-option rejection (Level 1, subprocess in a sandbox repository)
  - `scripts/build.sh` default build flow (Level 2, subprocess in a sandbox
    repository with a fake `uv` executable)
- Call graph: `build.sh` -> `check_build_prerequisites`,
  `run_cleanup`, `remove_release_artifacts`, `remove_build_intermediates`,
  `uv build --out-dir <staging>`, `verify_staged_artifacts`,
  `install_staged_artifacts`, `print_build_summary`, `on_exit`.
- External dependencies to isolate: `uv` replaced by a deterministic fake;
  repository replaced by a temporary git sandbox; `HOME`, `TMPDIR`, and git
  configuration redirected to temporary paths.
- Test matrix: script contract (REQ-280); happy-path build from a foreign
  working directory (REQ-280, REQ-283, REQ-284, REQ-285, REQ-317);
  pre-build removal of every release-artifact version including tracked
  artifacts and non-generated preservation (REQ-282, REQ-316); repeated
  builds (REQ-282); failed `uv build` (REQ-284, REQ-285); missing
  wheel (REQ-283, REQ-284); missing `uv` (REQ-281); `--clean` (REQ-286);
  `--list-artifacts` and unknown options (REQ-287).
- Execution plan: CI runs the suite through `uv run pytest`; developers
  run `uv run pytest tests/test_build_script.py`.
"""

import os
import shutil
import stat
import subprocess
import tempfile
import unittest
from pathlib import Path

from release_scripts_support import REPO_ROOT, create_sandbox


## @brief Test suite for the release-artifact build Bash script.
# @details Validates the script contract, the staged build flow, automatic
#          pre-build cleanup of every artifact version, post-build residue
#          removal, failure cleanup, and the auxiliary option modes inside
#          hermetic sandbox repositories.
# @satisfies REQ-280, REQ-281, REQ-282, REQ-283, REQ-284, REQ-285, REQ-286, REQ-287, REQ-288, REQ-316, REQ-317
class BuildScriptTest(unittest.TestCase):
    ## @brief Absolute path of the real build script under test.
    SCRIPT_PATH = REPO_ROOT / "scripts" / "build.sh"
    ## @brief Artifact filenames produced by the fake `uv build`.
    EXPECTED_ARTIFACTS = ["galias-1.2.3-py3-none-any.whl", "galias-1.2.3.tar.gz"]

    ## @brief Verify the script exists with the executable permission bit.
    # @return None.
    # @satisfies REQ-280
    def test_script_exists_and_is_executable(self):
        # Arrange
        expected_exists = True
        # Act
        actual_exists = self.SCRIPT_PATH.is_file()
        actual_mode = self.SCRIPT_PATH.stat().st_mode
        # Assert
        self.assertEqual(actual_exists, expected_exists)
        self.assertTrue(actual_mode & stat.S_IXUSR)
        self.assertTrue(os.access(self.SCRIPT_PATH, os.X_OK))

    ## @brief Verify the script parses as valid Bash.
    # @return None.
    # @satisfies REQ-280
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

    ## @brief Verify `--list-artifacts` prints every existing artifact.
    # @details Tracked and untracked release artifacts of every version are
    #          listed; non-generated `dist/` files are excluded.
    # @return None.
    # @satisfies REQ-287
    def test_list_artifacts_prints_every_existing_release_artifact(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            # Arrange
            sandbox = create_sandbox(Path(tmp_dir))
            dist = sandbox.repo / "dist"
            dist.mkdir()
            (dist / "galias-0.0.1.tar.gz").write_text("stale", encoding="utf-8")
            (dist / "galias-9.9.9-py3-none-any.whl").write_text("tracked", encoding="utf-8")
            (dist / "NOTES.md").write_text("notes", encoding="utf-8")
            sandbox.git("add", "--force", "dist/galias-9.9.9-py3-none-any.whl")
            expected_output = [
                str(dist / "galias-0.0.1.tar.gz"),
                str(dist / "galias-9.9.9-py3-none-any.whl"),
            ]
            # Act
            completed = sandbox.run("build.sh", "--list-artifacts")
            # Assert
            self.assertEqual(completed.returncode, 0, msg=completed.stderr)
            self.assertEqual(completed.stdout.splitlines(), expected_output)

    ## @brief Verify unknown options fail with usage text.
    # @return None.
    # @satisfies REQ-287
    def test_unknown_option_is_rejected_with_usage(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            # Arrange
            sandbox = create_sandbox(Path(tmp_dir))
            expected_returncode = 2
            # Act
            completed = sandbox.run("build.sh", "--unknown")
            # Assert
            self.assertEqual(completed.returncode, expected_returncode)
            self.assertIn("Unknown option: --unknown", completed.stderr)
            self.assertIn("Usage: scripts/build.sh", completed.stderr)
            self.assertEqual(sandbox.uv_invocations(), [])

    ## @brief Verify `--clean` removes generated outputs and nothing else.
    # @details Generated artifacts, `build/`, and `src/*.egg-info` are
    #          removed; tracked and non-generated `dist/` files survive.
    # @return None.
    # @satisfies REQ-286, REQ-288
    def test_clean_removes_generated_outputs_and_preserves_other_files(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            # Arrange
            sandbox = create_sandbox(Path(tmp_dir))
            dist = sandbox.repo / "dist"
            dist.mkdir()
            (dist / "galias-0.0.1.tar.gz").write_text("stale", encoding="utf-8")
            (dist / "galias-0.0.1-py3-none-any.whl").write_text("stale", encoding="utf-8")
            (dist / "NOTES.md").write_text("notes", encoding="utf-8")
            (sandbox.repo / "build" / "lib").mkdir(parents=True)
            (sandbox.repo / "src" / "galias.egg-info").mkdir()
            expected_dist_entries = ["NOTES.md"]
            # Act
            completed = sandbox.run("build.sh", "--clean")
            # Assert
            self.assertEqual(completed.returncode, 0, msg=completed.stderr)
            self.assertEqual(sorted(entry.name for entry in dist.iterdir()), expected_dist_entries)
            self.assertFalse((sandbox.repo / "build").exists())
            self.assertFalse((sandbox.repo / "src" / "galias.egg-info").exists())
            self.assertEqual(sandbox.uv_invocations(), [])

    ## @brief Verify `--clean` removes a `dist/` directory left empty.
    # @return None.
    # @satisfies REQ-286
    def test_clean_removes_emptied_dist_directory(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            # Arrange
            sandbox = create_sandbox(Path(tmp_dir))
            dist = sandbox.repo / "dist"
            dist.mkdir()
            (dist / "galias-0.0.1.tar.gz").write_text("stale", encoding="utf-8")
            expected_dist_exists = False
            # Act
            completed = sandbox.run("build.sh", "--clean")
            # Assert
            self.assertEqual(completed.returncode, 0, msg=completed.stderr)
            self.assertEqual(dist.exists(), expected_dist_exists)

    ## @brief Verify the build installs exactly one sdist and one wheel.
    # @details Runs from a foreign working directory against a sandbox path
    #          containing a space; asserts the staged `uv build` invocation,
    #          final `dist/` content without the uv `.gitignore` marker,
    #          removal of intermediates and staging, the summary, and that the
    #          built artifacts are git-visible untracked files (REQ-302).
    # @return None.
    # @satisfies REQ-280, REQ-283, REQ-284, REQ-285, REQ-302
    def test_build_installs_artifacts_into_dist_from_any_working_directory(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            # Arrange
            sandbox = create_sandbox(Path(tmp_dir))
            outside_cwd = Path(tmp_dir) / "elsewhere"
            outside_cwd.mkdir()
            dist = sandbox.repo / "dist"
            # Act
            completed = sandbox.run("build.sh", cwd=outside_cwd)
            # Assert
            self.assertEqual(completed.returncode, 0, msg=completed.stderr)
            invocations = sandbox.uv_invocations()
            self.assertEqual(len(invocations), 1)
            self.assertEqual(invocations[0][:2], ["build", "--out-dir"])
            self.assertFalse(Path(invocations[0][2]).exists())
            self.assertEqual(sorted(entry.name for entry in dist.iterdir()), self.EXPECTED_ARTIFACTS)
            self.assertFalse((sandbox.repo / "build").exists())
            self.assertFalse((sandbox.repo / "src" / "galias.egg-info").exists())
            self.assertEqual(sandbox.temp_entries(), [])
            self.assertEqual(sandbox.git("status", "--porcelain"), "?? dist/\n")
            self.assertIn("--- [build] Build completed: 2 release artifacts", completed.stdout)
            for artifact in self.EXPECTED_ARTIFACTS:
                self.assertIn(f"{dist / artifact} (", completed.stdout)

    ## @brief Verify stale artifacts of every version are replaced.
    # @details Untracked and git-tracked release artifacts of any version are
    #          removed before building; a non-generated file remains untouched.
    # @return None.
    # @satisfies REQ-282, REQ-317
    def test_build_removes_stale_artifacts_of_any_version(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            # Arrange
            sandbox = create_sandbox(Path(tmp_dir))
            dist = sandbox.repo / "dist"
            dist.mkdir()
            (dist / "galias-0.0.1.tar.gz").write_text("stale", encoding="utf-8")
            (dist / "galias-9.9.9-py3-none-any.whl").write_text("tracked", encoding="utf-8")
            (dist / "NOTES.md").write_text("notes", encoding="utf-8")
            sandbox.git("add", "--force", "dist/galias-9.9.9-py3-none-any.whl")
            expected_entries = sorted(self.EXPECTED_ARTIFACTS + ["NOTES.md"])
            # Act
            completed = sandbox.run("build.sh")
            # Assert
            self.assertEqual(completed.returncode, 0, msg=completed.stderr)
            self.assertEqual(sorted(entry.name for entry in dist.iterdir()), expected_entries)
            self.assertFalse((dist / "galias-9.9.9-py3-none-any.whl").exists())
            self.assertEqual((dist / "NOTES.md").read_text(encoding="utf-8"), "notes")

    ## @brief Verify consecutive builds never accumulate artifacts.
    # @return None.
    # @satisfies REQ-282
    def test_repeated_builds_leave_exactly_one_artifact_pair(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            # Arrange
            sandbox = create_sandbox(Path(tmp_dir))
            dist = sandbox.repo / "dist"
            # Act
            first = sandbox.run("build.sh")
            second = sandbox.run("build.sh")
            # Assert
            self.assertEqual(first.returncode, 0, msg=first.stderr)
            self.assertEqual(second.returncode, 0, msg=second.stderr)
            self.assertEqual(sorted(entry.name for entry in dist.iterdir()), self.EXPECTED_ARTIFACTS)
            self.assertEqual(sandbox.temp_entries(), [])

    ## @brief Verify a failing `uv build` leaves no generated output.
    # @details Stale artifacts are already removed and no partial artifact,
    #          intermediate, staging directory, or empty `dist/` remains.
    # @return None.
    # @satisfies REQ-284, REQ-285
    def test_build_failure_exits_non_zero_without_artifacts(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            # Arrange
            sandbox = create_sandbox(Path(tmp_dir))
            env = dict(sandbox.env, UV_FAIL_MATCH=" build ")
            # Act
            completed = sandbox.run("build.sh", env=env)
            # Assert
            self.assertNotEqual(completed.returncode, 0)
            self.assertIn("--- [build] ERROR: 'uv build' failed ---", completed.stderr)
            self.assertNotIn("Build completed", completed.stdout)
            self.assertFalse((sandbox.repo / "dist").exists())
            self.assertEqual(sandbox.untracked_files(), [])
            self.assertEqual(sandbox.temp_entries(), [])

    ## @brief Verify a missing wheel fails the build without partial output.
    # @return None.
    # @satisfies REQ-283, REQ-284
    def test_build_fails_when_expected_wheel_is_missing(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            # Arrange
            sandbox = create_sandbox(Path(tmp_dir))
            env = dict(sandbox.env, UV_BUILD_OMIT="wheel")
            # Act
            completed = sandbox.run("build.sh", env=env)
            # Assert
            self.assertNotEqual(completed.returncode, 0)
            self.assertIn("Expected exactly one wheel", completed.stderr)
            self.assertFalse((sandbox.repo / "dist").exists())
            self.assertEqual(sandbox.untracked_files(), [])
            self.assertEqual(sandbox.temp_entries(), [])

    ## @brief Verify the build aborts with an explicit error without `uv`.
    # @details PATH holds no executable, so only Bash builtins run before
    #          the prerequisite failure and nothing is deleted.
    # @return None.
    # @satisfies REQ-281
    def test_build_aborts_when_uv_is_missing(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            # Arrange
            sandbox = create_sandbox(Path(tmp_dir))
            stale = sandbox.repo / "dist" / "galias-0.0.1.tar.gz"
            stale.parent.mkdir()
            stale.write_text("stale", encoding="utf-8")
            empty_bin = Path(tmp_dir) / "empty-bin"
            empty_bin.mkdir()
            env = dict(sandbox.env, PATH=empty_bin.as_posix())
            bash_exe = shutil.which("bash")
            self.assertIsNotNone(bash_exe)
            assert bash_exe is not None  # Type narrowing for static analysis.
            # Act
            completed = subprocess.run(
                [bash_exe, str(sandbox.script("build.sh"))],
                cwd=str(sandbox.repo),
                env=env,
                capture_output=True,
                text=True,
                check=False,
            )
            # Assert
            self.assertNotEqual(completed.returncode, 0)
            self.assertIn("Required tool 'uv'", completed.stderr)
            self.assertTrue(stale.exists())


if __name__ == "__main__":
    unittest.main()
