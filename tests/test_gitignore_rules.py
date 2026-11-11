"""HDT unit tests for the repository `.gitignore` release-artifact rules.

HDT artifacts (Generator mode):

- UUT list: `.gitignore` rule set (Level 0, evaluated by `git check-ignore`
  inside a sandbox repository holding a copy of the real file).
- Call graph: `git check-ignore` -> `.gitignore` rules (exclude-all block,
  re-inclusion block, targeted exclusion block).
- External dependencies to isolate: repository replaced by a temporary git
  sandbox; user and system git configuration disabled.
- Test matrix: generated `dist/` artifacts versionable (REQ-302); non-generated
  `dist/` files visible (REQ-301); nested `dist` directories ignored
  (REQ-303); pre-existing inclusions and exclusions unchanged (REQ-301).
- Execution plan: CI runs the suite through `uv run pytest`; developers
  run `uv run pytest tests/test_gitignore_rules.py`.
"""

import subprocess
import tempfile
import unittest
from pathlib import Path

from release_scripts_support import create_sandbox


## @brief Test suite for `.gitignore` inverse-strategy and `dist/` rules.
# @details Creates real files in a sandbox repository and classifies each
#          path through `git check-ignore`, so rule order and parent
#          directory semantics are evaluated by git itself.
# @satisfies REQ-301, REQ-302, REQ-303
class GitignoreRulesTest(unittest.TestCase):
    ## @brief Classify sandbox paths as ignored or visible.
    # @details Creates every path as a file, then queries
    #          `git check-ignore -q` once per path.
    # @param paths {list[str]} Repository-relative file paths.
    # @return {dict[str, bool]} Path mapped to True when git ignores it.
    def _classify(self, paths: list) -> dict:
        with tempfile.TemporaryDirectory() as tmp_dir:
            sandbox = create_sandbox(Path(tmp_dir))
            ignored = {}
            for relative in paths:
                target = sandbox.repo / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text("content", encoding="utf-8")
            for relative in paths:
                completed = subprocess.run(
                    ["git", "-C", str(sandbox.repo), "check-ignore", "-q", "--", relative],
                    env=sandbox.env,
                    capture_output=True,
                    text=True,
                    check=False,
                )
                self.assertIn(completed.returncode, (0, 1), msg=completed.stderr)
                ignored[relative] = completed.returncode == 0
            return ignored

    ## @brief Verify generated release artifacts in `dist/` stay visible to git.
    # @return None.
    # @satisfies REQ-302
    def test_generated_dist_artifacts_are_versionable(self):
        # Arrange
        paths = [
            "dist/galias-1.2.3.tar.gz",
            "dist/galias-1.2.3-py3-none-any.whl",
            "dist/nested/galias-1.2.3-py3-none-any.whl",
        ]
        expected_output = {path: False for path in paths}
        # Act
        actual_output = self._classify(paths)
        # Assert
        self.assertEqual(actual_output, expected_output)

    ## @brief Verify non-generated `dist/` files stay visible to git.
    # @return None.
    # @satisfies REQ-301
    def test_non_generated_dist_files_are_versionable(self):
        # Arrange
        paths = ["dist/NOTES.md", "dist/.gitkeep", "dist/nested/manifest.json"]
        expected_output = {path: False for path in paths}
        # Act
        actual_output = self._classify(paths)
        # Assert
        self.assertEqual(actual_output, expected_output)

    ## @brief Verify generic exclusions still apply inside `dist/`.
    # @return None.
    # @satisfies REQ-301
    def test_generic_exclusions_still_apply_inside_dist(self):
        # Arrange
        paths = ["dist/debug.log", "dist/__pycache__/module.pyc", "dist/galias.egg-info/PKG-INFO"]
        expected_output = {path: True for path in paths}
        # Act
        actual_output = self._classify(paths)
        # Assert
        self.assertEqual(actual_output, expected_output)

    ## @brief Verify nested directories named `dist` remain ignored.
    # @return None.
    # @satisfies REQ-303
    def test_nested_dist_directories_are_ignored(self):
        # Arrange
        paths = ["src/dist/module.py", "tests/deep/dist/data.py", "dist/dist/NOTES.md"]
        expected_output = {path: True for path in paths}
        # Act
        actual_output = self._classify(paths)
        # Assert
        self.assertEqual(actual_output, expected_output)

    ## @brief Verify the inverse strategy keeps prior inclusions and exclusions.
    # @details Whitelisted sources stay visible; root-level strays, build
    #          intermediates, caches, and non-whitelisted script types stay
    #          ignored.
    # @return None.
    # @satisfies REQ-301
    def test_inverse_strategy_behavior_is_unchanged_outside_dist(self):
        # Arrange
        expected_output = {
            "src/git_alias/extra.py": False,
            "tests/test_extra.py": False,
            "scripts/extra.sh": False,
            "usereq/docs/EXTRA.md": False,
            "stray.txt": True,
            "notes": True,
            "build/lib/module.py": True,
            "src/galias.egg-info/PKG-INFO": True,
            "src/git_alias/__pycache__/module.pyc": True,
            ".pytest_cache/cache.db": True,
            ".venv/pyvenv.cfg": True,
            "scripts/tool.py": True,
        }
        # Act
        actual_output = self._classify(list(expected_output))
        # Assert
        self.assertEqual(actual_output, expected_output)


if __name__ == "__main__":
    unittest.main()
