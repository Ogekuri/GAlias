import contextlib
import io
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from git_alias import core


class VerCommandTest(unittest.TestCase):
    def setUp(self):
        core.CONFIG.update(core.DEFAULT_CONFIG)
        core.CONFIG["ver_rules"] = core.DEFAULT_CONFIG["ver_rules"]

    @staticmethod
    def _set_rules(rules):
        core.CONFIG["ver_rules"] = rules

    @staticmethod
    def _mock_ls_files(root: Path, tracked_files=None):
        files = tracked_files
        if files is None:
            files = sorted(
                path.relative_to(root).as_posix()
                for path in root.rglob("*")
                if path.is_file()
            )
        payload = "\n".join(files)

        def _fake_run_git_text(args, cwd=None, check=True):
            if args != ["ls-files"]:
                raise AssertionError(f"Unexpected git args: {args}")
            if cwd != root:
                raise AssertionError(f"Unexpected cwd: {cwd}")
            return payload

        return mock.patch.object(core, "run_git_text", side_effect=_fake_run_git_text)

    def test_cmd_ver_prints_shared_version(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / "module.py").write_text('__version__ = "1.2.3"\n', encoding="utf-8")
            (root / "README.md").write_text('Current version "1.2.3"\n', encoding="utf-8")
            self._set_rules(
                [
                    {"pattern": "module.py", "regex": r'__version__\s*=\s*"(\d+\.\d+\.\d+)"'},
                    {"pattern": "README.md", "regex": r'"(\d+\.\d+\.\d+)"'},
                ]
            )
            with mock.patch.object(core, "get_git_root", return_value=root):
                with self._mock_ls_files(root):
                    buffer = io.StringIO()
                    with contextlib.redirect_stdout(buffer):
                        core.cmd_ver([])
                    self.assertEqual(buffer.getvalue().strip(), "1.2.3")

    def test_cmd_ver_anchors_src_glob_at_root(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / "src" / "git_alias").mkdir(parents=True)
            (root / "src" / "git_alias" / "__init__.py").write_text(
                '__version__ = "1.2.3"\n', encoding="utf-8"
            )
            (root / "prova" / "src").mkdir(parents=True)
            (root / "prova" / "src" / "__init__.py").write_text(
                '__version__ = "2.0.0"\n', encoding="utf-8"
            )
            self._set_rules(
                [
                    {"pattern": "src/**/*.py", "regex": r'__version__\s*=\s*["\']?(\d+\.\d+\.\d+)["\']?'},
                ]
            )
            with mock.patch.object(core, "get_git_root", return_value=root):
                with self._mock_ls_files(root):
                    buffer = io.StringIO()
                    with contextlib.redirect_stdout(buffer):
                        core.cmd_ver([])
                    self.assertEqual(buffer.getvalue().strip(), "1.2.3")

    def test_cmd_ver_uses_git_ls_files_for_nested_paths(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / "src" / "debriddo").mkdir(parents=True)
            (root / "src" / "debriddo" / "main.py").write_text(
                '__version__ = "1.2.3"\n', encoding="utf-8"
            )
            self._set_rules(
                [
                    {"pattern": "src/**/*.py", "regex": r'__version__\s*=\s*["\']?(\d+\.\d+\.\d+)["\']?'},
                ]
            )
            with mock.patch.object(core, "get_git_root", return_value=root):
                with self._mock_ls_files(root):
                    buffer = io.StringIO()
                    with contextlib.redirect_stdout(buffer):
                        core.cmd_ver([])
                    self.assertEqual(buffer.getvalue().strip(), "1.2.3")

    def test_cmd_ver_uses_git_ls_files_inventory(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / "src" / "debriddo").mkdir(parents=True)
            file_path = root / "src" / "debriddo" / "main.py"
            file_path.write_text('__version__ = "1.2.3"\n', encoding="utf-8")
            self._set_rules(
                [
                    {"pattern": "src/**/*.py", "regex": r'__version__\s*=\s*["\']?(\d+\.\d+\.\d+)["\']?'},
                ]
            )
            with mock.patch.object(core, "get_git_root", return_value=root):
                with self._mock_ls_files(root) as ls_files:
                    buffer = io.StringIO()
                    with contextlib.redirect_stdout(buffer):
                        core.cmd_ver([])
                    self.assertEqual(buffer.getvalue().strip(), "1.2.3")
                self.assertEqual(ls_files.call_count, 1)

    def test_cmd_ver_detects_conflict(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / "module.py").write_text("__version__ =  '1.2.3'\n", encoding="utf-8")
            (root / "second.py").write_text('__version__ = "2.0.0"\n', encoding="utf-8")
            self._set_rules(
                [
                    {"pattern": "*.py", "regex": r'__version__\s*=\s*["\']?(\d+\.\d+\.\d+)["\']?'},
                ]
            )
            with mock.patch.object(core, "get_git_root", return_value=root):
                with self._mock_ls_files(root):
                    err = io.StringIO()
                    with contextlib.redirect_stderr(err):
                        with self.assertRaises(SystemExit) as ctx:
                            core.cmd_ver([])
                    self.assertNotEqual(ctx.exception.code, 0)
                    message = err.getvalue()
                    self.assertIn("Version mismatch", message)
                    self.assertIn("module.py", message)
                    self.assertIn("second.py", message)

    def test_cmd_ver_errors_on_rule_without_matches(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / "module.py").write_text('__version__ = "1.2.3"\n', encoding="utf-8")
            regex = r'version\s*=\s*"(\d+\.\d+\.\d+)"'
            self._set_rules(
                [
                    {"pattern": "module.py", "regex": regex},
                ]
            )
            with mock.patch.object(core, "get_git_root", return_value=root):
                with self._mock_ls_files(root):
                    err = io.StringIO()
                    with contextlib.redirect_stderr(err):
                        with self.assertRaises(SystemExit) as ctx:
                            core.cmd_ver([])
                    self.assertNotEqual(ctx.exception.code, 0)
                    message = err.getvalue()
                    self.assertIn("No version matches found", message)
                    self.assertIn("module.py", message)
                    self.assertIn(regex, message)

    def test_cmd_ver_errors_when_pattern_matches_no_repository_files(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / "module.py").write_text('__version__ = "1.2.3"\n', encoding="utf-8")
            self._set_rules(
                [
                    {"pattern": "missing.py", "regex": r'__version__\s*=\s*["\']?(\d+\.\d+\.\d+)["\']?'},
                ]
            )
            with mock.patch.object(core, "get_git_root", return_value=root):
                with self._mock_ls_files(root, tracked_files=["module.py"]):
                    err = io.StringIO()
                    with contextlib.redirect_stderr(err):
                        with self.assertRaises(SystemExit) as ctx:
                            core.cmd_ver([])
                    self.assertNotEqual(ctx.exception.code, 0)
                    message = err.getvalue()
                    self.assertIn("No files matched the version rule pattern 'missing.py'.", message)
                    self.assertIn(
                        "Only repository files reported by git ls-files can be configured in ver_rules.pattern.",
                        message,
                    )

    def test_cmd_ver_ignores_cached_and_temp_paths(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / "module.py").write_text('__version__ = "1.2.3"\n', encoding="utf-8")
            ignored_paths = [
                root / ".git" / "ignored.py",
                root / ".vscode" / "ignored.py",
                root / "tmp" / "ignored.py",
                root / "temp" / "ignored.py",
                root / ".cache" / "ignored.py",
                root / ".pytest_cache" / "ignored.py",
                root / "node_modules" / ".cache" / "ignored.py",
            ]
            for path in ignored_paths:
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text('__version__ = "9.9.9"\n', encoding="utf-8")
            self._set_rules(
                [
                    {"pattern": "**/*.py", "regex": r'__version__\s*=\s*["\']?(\d+\.\d+\.\d+)["\']?'},
                ]
            )
            with mock.patch.object(core, "get_git_root", return_value=root):
                with self._mock_ls_files(root):
                    buffer = io.StringIO()
                    with contextlib.redirect_stdout(buffer):
                        core.cmd_ver([])
                    self.assertEqual(buffer.getvalue().strip(), "1.2.3")

    def test_cmd_ver_verbose_reports_regex_matches(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / "module.py").write_text('__version__ = "1.2.3"\n', encoding="utf-8")
            (root / "notes.py").write_text("no version here\n", encoding="utf-8")
            self._set_rules(
                [
                    {"pattern": "*.py", "regex": r'__version__\s*=\s*["\']?(\d+\.\d+\.\d+)["\']?'},
                ]
            )
            with mock.patch.object(core, "get_git_root", return_value=root):
                with self._mock_ls_files(root):
                    buffer = io.StringIO()
                    with contextlib.redirect_stdout(buffer):
                        core.cmd_ver(["--verbose"])
                    output = buffer.getvalue()
                    self.assertIn("Regex match for module.py: yes.", output)
                    self.assertIn("Regex match for notes.py: no.", output)
                    self.assertEqual(output.strip().splitlines()[-1], "1.2.3")

    def test_cmd_ver_debug_reports_globbing_matches(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / "module.py").write_text('__version__ = "1.2.3"\n', encoding="utf-8")
            self._set_rules(
                [
                    {"pattern": "*.py", "regex": r'__version__\s*=\s*["\']?(\d+\.\d+\.\d+)["\']?'},
                ]
            )
            with mock.patch.object(core, "get_git_root", return_value=root):
                with self._mock_ls_files(root):
                    buffer = io.StringIO()
                    with contextlib.redirect_stdout(buffer):
                        core.cmd_ver(["--debug"])
                    output = buffer.getvalue()
                    self.assertIn("Pattern '*.py' matched files:", output)
                    self.assertIn("  module.py", output)
                    self.assertIn("Regex match for module.py: yes.", output)

    def test_cmd_chver_updates_versions_and_reports_success(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            module_path = root / "module.py"
            readme_path = root / "README.md"
            module_path.write_text('__version__ = "1.2.3"\n', encoding="utf-8")
            readme_path.write_text('Current version "1.2.3"\n', encoding="utf-8")
            self._set_rules(
                [
                    {"pattern": "module.py", "regex": r'__version__\s*=\s*"(\d+\.\d+\.\d+)"'},
                    {"pattern": "README.md", "regex": r'"(\d+\.\d+\.\d+)"'},
                ]
            )
            with mock.patch.object(core, "get_git_root", return_value=root):
                with self._mock_ls_files(root):
                    buffer = io.StringIO()
                    with contextlib.redirect_stdout(buffer):
                        core.cmd_chver(["1.2.4"])
                    self.assertIn("Upgrade completed: version is now 1.2.4.", buffer.getvalue())
            self.assertIn('1.2.4', module_path.read_text(encoding="utf-8"))
            self.assertIn('1.2.4', readme_path.read_text(encoding="utf-8"))

    def test_cmd_chver_errors_when_pattern_matches_no_repository_files(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / "module.py").write_text('__version__ = "1.2.3"\n', encoding="utf-8")
            self._set_rules(
                [
                    {"pattern": "missing.py", "regex": r'__version__\s*=\s*"(\d+\.\d+\.\d+)"'},
                ]
            )
            with mock.patch.object(core, "get_git_root", return_value=root):
                with self._mock_ls_files(root, tracked_files=["module.py"]):
                    err = io.StringIO()
                    with contextlib.redirect_stderr(err):
                        with self.assertRaises(SystemExit) as ctx:
                            core.cmd_chver(["1.2.4"])
                    self.assertNotEqual(ctx.exception.code, 0)
                    message = err.getvalue()
                    self.assertIn("Unable to determine the current version:", message)
                    self.assertIn("No files matched the version rule pattern 'missing.py'.", message)
                    self.assertIn(
                        "Only repository files reported by git ls-files can be configured in ver_rules.pattern.",
                        message,
                    )

    def test_cmd_chver_builds_version_inventory_once(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / "module.py").write_text('__version__ = "1.2.3"\n', encoding="utf-8")
            self._set_rules(
                [
                    {"pattern": "*.py", "regex": r'__version__\s*=\s*"(\d+\.\d+\.\d+)"'},
                ]
            )
            with mock.patch.object(core, "get_git_root", return_value=root):
                with self._mock_ls_files(root):
                    with mock.patch.object(
                        core,
                        "_build_version_file_inventory",
                        wraps=core._build_version_file_inventory,
                    ) as build_inventory:
                        core.cmd_chver(["1.2.4"])
                    self.assertEqual(build_inventory.call_count, 1)

    ## @brief Verify the REQ-337 updated-file report after a successful version update.
    # @details Updates two version-managed files in a temporary repository and asserts
    #          the completion line is followed by the `Updated files:` list containing
    #          one repository-relative line per rewritten file.
    # @param self {VersionCommandTest} Isolated test instance.
    # @return {None} Assert REQ-337 list content and ordering after the completion line.
    def test_cmd_chver_prints_updated_files_list(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            module_path = root / "module.py"
            readme_path = root / "README.md"
            module_path.write_text('__version__ = "1.2.3"\n', encoding="utf-8")
            readme_path.write_text('Current version "1.2.3"\n', encoding="utf-8")
            self._set_rules(
                [
                    {"pattern": "module.py", "regex": r'__version__\s*=\s*"(\d+\.\d+\.\d+)"'},
                    {"pattern": "README.md", "regex": r'"(\d+\.\d+\.\d+)"'},
                ]
            )
            with mock.patch.object(core, "get_git_root", return_value=root):
                with self._mock_ls_files(root):
                    buffer = io.StringIO()
                    with contextlib.redirect_stdout(buffer):
                        core.cmd_chver(["1.2.4"])
            output = buffer.getvalue()
            self.assertIn("Upgrade completed: version is now 1.2.4.", output)
            self.assertIn("Updated files:", output)
            self.assertIn("- module.py", output)
            self.assertIn("- README.md", output)
            self.assertLess(
                output.index("Upgrade completed: version is now 1.2.4."),
                output.index("Updated files:"),
            )

    ## @brief Verify the updated-file report lists only files with rewritten occurrences.
    # @details One rule rewrites its file while a second matched rule finds no occurrence;
    #          asserts the `Updated files:` list contains only the rewritten file.
    # @param self {VersionCommandTest} Isolated test instance.
    # @return {None} Assert REQ-337 per-file membership semantics.
    def test_cmd_chver_lists_only_files_with_rewritten_occurrences(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / "module.py").write_text('__version__ = "1.2.3"\n', encoding="utf-8")
            (root / "notes.py").write_text("notes: 1.2.3\n", encoding="utf-8")
            self._set_rules(
                [
                    {"pattern": "*.py", "regex": r'__version__\s*=\s*"(\d+\.\d+\.\d+)"'},
                ]
            )
            with mock.patch.object(core, "get_git_root", return_value=root):
                with self._mock_ls_files(root):
                    buffer = io.StringIO()
                    with contextlib.redirect_stdout(buffer):
                        core.cmd_chver(["1.2.4"])
            output = buffer.getvalue()
            self.assertIn("Updated files:", output)
            self.assertIn("- module.py", output)
            self.assertNotIn("- notes.py", output)

    ## @brief Verify the updated-file report is omitted when the version is unchanged.
    # @details Requests the current version so the command returns early; asserts the
    #          informational line is printed and no `Updated files:` list appears.
    # @param self {VersionCommandTest} Isolated test instance.
    # @return {None} Assert REQ-337 no-op boundary without the file list.
    def test_cmd_chver_omits_file_list_when_version_already_current(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / "module.py").write_text('__version__ = "1.2.3"\n', encoding="utf-8")
            self._set_rules(
                [
                    {"pattern": "module.py", "regex": r'__version__\s*=\s*"(\d+\.\d+\.\d+)"'},
                ]
            )
            with mock.patch.object(core, "get_git_root", return_value=root):
                with self._mock_ls_files(root):
                    buffer = io.StringIO()
                    with contextlib.redirect_stdout(buffer):
                        core.cmd_chver(["1.2.3"])
            output = buffer.getvalue()
            self.assertIn("The project version is already 1.2.3.", output)
            self.assertNotIn("Updated files:", output)
