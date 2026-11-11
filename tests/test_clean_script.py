"""HDT unit tests for the `scripts/clean.sh` cleanup script.

HDT artifacts (Generator mode):

- UUT list:
  - `scripts/clean.sh` script contract (Level 0, static: presence,
    executable permission, Bash syntax)
  - `scripts/clean.sh` option modes and unknown-option rejection (Level 1,
    subprocess in a sandbox repository)
  - `scripts/clean.sh` cleanup flow removing every `scripts/build.sh`
    artifact (Level 2, subprocess in a sandbox repository)
- Call graph: `clean.sh` -> `has_tracked_content`, `remove_generated_path`,
  `collect_release_artifacts`, `remove_release_artifacts`,
  `remove_build_intermediates`, `remove_empty_dist_dir`, `run_clean`.
- External dependencies to isolate: repository replaced by a temporary git
  sandbox; `HOME`, `TMPDIR`, and git configuration redirected to temporary
  paths; no network or real `uv` is required because cleanup never builds.
- Test matrix: script contract and root resolution (REQ-309); generated
  artifact, intermediate, and emptied `dist/` removal with tracked and
  non-generated preservation (REQ-310); tracked-content refusal,
  unknown-option rejection, and multi-option rejection (REQ-311); canonical
  progress and completion lines (REQ-312).
- Execution plan: CI runs the suite through `uv run pytest`; developers
  run `uv run pytest tests/test_clean_script.py`.
"""

import os
import stat
import subprocess
import tempfile
import unittest
from pathlib import Path

from release_scripts_support import REPO_ROOT, create_sandbox


## @brief Test suite for the `scripts/clean.sh` cleanup Bash script.
# @details Validates the script contract, the cleanup of every
#          `scripts/build.sh` artifact, tracked-content preservation, option
#          handling, and canonical progress output inside hermetic sandbox
#          repositories.
# @satisfies REQ-309, REQ-310, REQ-311, REQ-312
class CleanScriptTest(unittest.TestCase):
    ## @brief Absolute path of the real cleanup script under test.
    SCRIPT_PATH = REPO_ROOT / "scripts" / "clean.sh"

    ## @brief Verify the script exists with the executable permission bit.
    # @return None.
    # @satisfies REQ-309
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
    # @satisfies REQ-309
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

    ## @brief Verify cleanup removes generated outputs and preserves others.
    # @details Generated artifacts, `build/`, and `src/*.egg-info` are
    #          removed; tracked and non-generated `dist/` files survive.
    # @return None.
    # @satisfies REQ-310, REQ-288
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
            completed = sandbox.run("clean.sh")
            # Assert
            self.assertEqual(completed.returncode, 0, msg=completed.stderr)
            self.assertEqual(sorted(entry.name for entry in dist.iterdir()), expected_dist_entries)
            self.assertFalse((sandbox.repo / "build").exists())
            self.assertFalse((sandbox.repo / "src" / "galias.egg-info").exists())

    ## @brief Verify cleanup removes a `dist/` directory left empty.
    # @return None.
    # @satisfies REQ-310
    def test_clean_removes_emptied_dist_directory(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            # Arrange
            sandbox = create_sandbox(Path(tmp_dir))
            dist = sandbox.repo / "dist"
            dist.mkdir()
            (dist / "galias-0.0.1.tar.gz").write_text("stale", encoding="utf-8")
            expected_dist_exists = False
            # Act
            completed = sandbox.run("clean.sh")
            # Assert
            self.assertEqual(completed.returncode, 0, msg=completed.stderr)
            self.assertEqual(dist.exists(), expected_dist_exists)

    ## @brief Verify cleanup preserves git-tracked generated artifacts.
    # @return None.
    # @satisfies REQ-310, REQ-288
    def test_clean_preserves_tracked_release_artifacts(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            # Arrange
            sandbox = create_sandbox(Path(tmp_dir))
            dist = sandbox.repo / "dist"
            dist.mkdir()
            tracked = dist / "galias-9.9.9-py3-none-any.whl"
            tracked.write_text("tracked", encoding="utf-8")
            (dist / "galias-0.0.1.tar.gz").write_text("stale", encoding="utf-8")
            sandbox.git("add", "--force", "dist/galias-9.9.9-py3-none-any.whl")
            expected_entries = [tracked.name]
            # Act
            completed = sandbox.run("clean.sh")
            # Assert
            self.assertEqual(completed.returncode, 0, msg=completed.stderr)
            self.assertEqual(sorted(entry.name for entry in dist.iterdir()), expected_entries)
            self.assertEqual(tracked.read_text(encoding="utf-8"), "tracked")

    ## @brief Verify cleanup refuses to delete a target holding tracked content.
    # @return None.
    # @satisfies REQ-311, REQ-288
    def test_clean_refuses_tracked_cleanup_target(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            # Arrange
            sandbox = create_sandbox(Path(tmp_dir))
            target = sandbox.repo / "build" / "lib"
            target.mkdir(parents=True)
            (target / "kept.py").write_text("tracked", encoding="utf-8")
            sandbox.git("add", "--force", "build/lib/kept.py")
            expected_returncode = 1
            # Act
            completed = sandbox.run("clean.sh")
            # Assert
            self.assertEqual(completed.returncode, expected_returncode)
            self.assertIn("Refusing to remove", completed.stderr)
            self.assertTrue((target / "kept.py").exists())

    ## @brief Verify unknown options fail with usage text.
    # @return None.
    # @satisfies REQ-311
    def test_unknown_option_is_rejected_with_usage(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            # Arrange
            sandbox = create_sandbox(Path(tmp_dir))
            expected_returncode = 2
            # Act
            completed = sandbox.run("clean.sh", "--unknown")
            # Assert
            self.assertEqual(completed.returncode, expected_returncode)
            self.assertIn("Unknown option: --unknown", completed.stderr)
            self.assertIn("Usage: scripts/clean.sh", completed.stderr)

    ## @brief Verify the canonical progress and completion lines are printed.
    # @return None.
    # @satisfies REQ-312
    def test_clean_prints_progress_and_completion_lines(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            # Arrange
            sandbox = create_sandbox(Path(tmp_dir))
            expected_lines = [
                "--- [clean] Remove generated release artifacts and build intermediates ---",
                "--- [clean] Cleanup completed ---",
            ]
            # Act
            completed = sandbox.run("clean.sh")
            # Assert
            self.assertEqual(completed.returncode, 0, msg=completed.stderr)
            self.assertEqual(completed.stdout.splitlines(), expected_lines)

    ## @brief Verify cleanup succeeds from a foreign working directory.
    # @return None.
    # @satisfies REQ-309
    def test_clean_resolves_root_from_any_working_directory(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            # Arrange
            sandbox = create_sandbox(Path(tmp_dir))
            outside_cwd = Path(tmp_dir) / "elsewhere"
            outside_cwd.mkdir()
            dist = sandbox.repo / "dist"
            dist.mkdir()
            (dist / "galias-0.0.1.tar.gz").write_text("stale", encoding="utf-8")
            expected_dist_exists = False
            # Act
            completed = sandbox.run("clean.sh", cwd=outside_cwd)
            # Assert
            self.assertEqual(completed.returncode, 0, msg=completed.stderr)
            self.assertEqual(dist.exists(), expected_dist_exists)


if __name__ == "__main__":
    unittest.main()
