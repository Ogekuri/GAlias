"""HDT unit tests for gitignore(5) compatibility of `ver_rules.pattern`.

HDT artifacts (Generator mode):

- UUT list:
  - `core._normalize_version_rule_pattern` (Level 0)
  - `core._split_negation_pattern` (Level 0)
  - `core._load_config_rules` (Level 0, reads `core.CONFIG`)
  - `core._build_version_negation_specs` (Level 1, depends on `_split_negation_pattern`
    and `_normalize_version_rule_pattern`)
  - `core._collect_version_files` (Level 1, depends on inventory + pathspec)
  - `core._prepare_version_rule_contexts` (Level 2, depends on `_collect_version_files`)
- Call graph: `_prepare_version_rule_contexts` -> `_build_version_negation_specs`,
  `_split_negation_pattern`, `_collect_version_files` -> `_normalize_version_rule_pattern`,
  `_version_path_is_negated`, `_version_pathspec_matches`.
- External dependencies to isolate: `git ls-files` via `core.run_git_text` (mocked),
  filesystem (temp directories).
- Test matrix: escaping happy/boundary (REQ-160), negation exclusion happy/boundary
  (REQ-161, REQ-163), config loading of negation entries (REQ-162), anchoring
  regression (REQ-164).
"""

import tempfile
import unittest
import warnings
from pathlib import Path
from unittest import mock

from git_alias import core


class VerRulePatternTest(unittest.TestCase):
    def setUp(self):
        core.CONFIG.update(core.DEFAULT_CONFIG)
        core.CONFIG["ver_rules"] = core.DEFAULT_CONFIG["ver_rules"]

    def _make_root(self, files):
        """Create a temp repo root containing the given relative tracked files."""
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        root = Path(tmp.name)
        for relative in files:
            path = root / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text('__version__ = "1.2.3"\n', encoding="utf-8")
        return tmp, root

    @staticmethod
    def _mock_ls_files(root, tracked_files):
        payload = "\n".join(tracked_files)

        def _fake_run_git_text(args, cwd=None, check=True):
            if args != ["ls-files"]:
                raise AssertionError(f"Unexpected git args: {args}")
            return payload

        return mock.patch.object(core, "run_git_text", side_effect=_fake_run_git_text)

    def test_normalize_pattern_preserves_backslash_escape(self):
        # Arrange
        raw = "\\!important.txt"
        expected_output = "\\!important.txt"
        # Act
        actual = core._normalize_version_rule_pattern(raw)
        # Assert
        self.assertEqual(actual, expected_output)

    def test_normalize_pattern_anchors_slash_patterns(self):
        # Arrange
        raw = "src/**/*.py"
        expected_output = "/src/**/*.py"
        # Act
        actual = core._normalize_version_rule_pattern(raw)
        # Assert
        self.assertEqual(actual, expected_output)

    def test_split_negation_pattern_detects_prefix(self):
        # Arrange
        raw = "!docs/README.md"
        expected_output = (True, "docs/README.md")
        # Act
        actual = core._split_negation_pattern(raw)
        # Assert
        self.assertEqual(actual, expected_output)

    def test_split_negation_pattern_plain(self):
        # Arrange
        raw = "README.md"
        expected_output = (False, "README.md")
        # Act
        actual = core._split_negation_pattern(raw)
        # Assert
        self.assertEqual(actual, expected_output)

    def test_load_config_rules_accepts_negation_without_regex(self):
        # Arrange
        core.CONFIG["ver_rules"] = [{"pattern": "!docs/README.md"}]
        expected_output = [("!docs/README.md", None)]
        # Act
        actual = core._load_config_rules("ver_rules", core.DEFAULT_VER_RULES)
        # Assert
        self.assertEqual(actual, expected_output)

    def test_load_config_rules_keeps_regex_for_plain_entries(self):
        # Arrange
        core.CONFIG["ver_rules"] = [
            {"pattern": "README.md", "regex": r"(\d+\.\d+\.\d+)"}
        ]
        expected_output = [("README.md", r"(\d+\.\d+\.\d+)")]
        # Act
        actual = core._load_config_rules("ver_rules", core.DEFAULT_VER_RULES)
        # Assert
        self.assertEqual(actual, expected_output)

    def test_escaped_pattern_matches_exclamation_file(self):
        # Arrange
        tmp, root = self._make_root(["!important.txt", "module.py"])
        with self._mock_ls_files(root, ["!important.txt", "module.py"]):
            expected_files = [root / "!important.txt"]
            # Act
            actual_files = core._collect_version_files(root, "\\!important.txt")
            # Assert
            self.assertEqual(actual_files, expected_files)

    def test_escaped_pattern_does_not_match_plain_name(self):
        # Arrange
        tmp, root = self._make_root(["important.txt"])
        with self._mock_ls_files(root, ["important.txt"]):
            expected_files = []
            # Act
            actual_files = core._collect_version_files(root, "\\!important.txt")
            # Assert
            self.assertEqual(actual_files, expected_files)

    def test_negation_specs_compile_without_deprecation_warning(self):
        # Arrange
        rules = [("!docs/README.md", None)]
        expected_specs = 1
        # Act
        with warnings.catch_warnings():
            warnings.simplefilter("error", DeprecationWarning)
            actual_specs = core._build_version_negation_specs(rules)
        # Assert
        self.assertEqual(len(actual_specs), expected_specs)

    def test_negation_excludes_file_from_other_rule(self):
        # Arrange
        tmp, root = self._make_root(["README.md", "docs/README.md"])
        rules = [
            ("**/README.md", r'(\d+\.\d+\.\d+)'),
            ("!docs/README.md", None),
        ]
        with self._mock_ls_files(root, ["README.md", "docs/README.md"]):
            expected_files = [root / "README.md"]
            # Act
            contexts = core._prepare_version_rule_contexts(root, rules)
            actual_files = contexts[0].files
            # Assert
            self.assertEqual(actual_files, expected_files)
            self.assertEqual(len(contexts), 1)

    def test_negation_only_match_triggers_zero_match_abort(self):
        # Arrange
        tmp, root = self._make_root(["docs/README.md"])
        rules = [
            ("**/README.md", r'(\d+\.\d+\.\d+)'),
            ("!docs/README.md", None),
        ]
        with self._mock_ls_files(root, ["docs/README.md"]):
            expected_exception = core.VersionDetectionError
            # Act + Assert
            with self.assertRaises(expected_exception):
                core._prepare_version_rule_contexts(root, rules)

    def test_anchored_inclusion_still_matches_root_only(self):
        # Arrange
        tmp, root = self._make_root(["README.md", "docs/README.md"])
        with self._mock_ls_files(root, ["README.md", "docs/README.md"]):
            expected_files = [root / "README.md"]
            # Act
            actual_files = core._collect_version_files(root, "/README.md")
            # Assert
            self.assertEqual(actual_files, expected_files)


if __name__ == "__main__":
    unittest.main()
