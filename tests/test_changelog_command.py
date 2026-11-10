import contextlib
import io
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from git_alias import core


class ChangelogCommandTest(unittest.TestCase):
    def setUp(self):
        core.CONFIG.update(core.DEFAULT_CONFIG)

    def test_creates_file_when_missing(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_root = Path(tmpdir)
            with mock.patch.object(core, "is_inside_git_repo", return_value=True), mock.patch.object(
                core, "get_git_root", return_value=repo_root
            ), mock.patch.object(core, "generate_changelog_document", return_value="# Changelog\n"):
                core.cmd_changelog([])
            content = (repo_root / "CHANGELOG.md").read_text(encoding="utf-8")
            self.assertEqual(content, "# Changelog\n")

    def test_refuses_overwrite_without_force(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_root = Path(tmpdir)
            (repo_root / "CHANGELOG.md").write_text("old", encoding="utf-8")
            with mock.patch.object(core, "is_inside_git_repo", return_value=True), mock.patch.object(
                core, "get_git_root", return_value=repo_root
            ), mock.patch.object(core, "generate_changelog_document", return_value="new"):
                with self.assertRaises(SystemExit):
                    core.cmd_changelog([])

    def test_print_only_outputs_content(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_root = Path(tmpdir)
            with mock.patch.object(core, "is_inside_git_repo", return_value=True), mock.patch.object(
                core, "get_git_root", return_value=repo_root
            ), mock.patch.object(core, "generate_changelog_document", return_value="markdown"):
                buffer = io.StringIO()
                with contextlib.redirect_stdout(buffer):
                    core.cmd_changelog(["--print-only"])
                self.assertEqual(buffer.getvalue(), "markdown")
            self.assertFalse((repo_root / "CHANGELOG.md").exists())

    def test_include_patch_flag_propagates(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_root = Path(tmpdir)
            with mock.patch.object(core, "is_inside_git_repo", return_value=True), mock.patch.object(
                core, "get_git_root", return_value=repo_root
            ), mock.patch.object(core, "generate_changelog_document", return_value="data") as gen:
                buffer = io.StringIO()
                with contextlib.redirect_stdout(buffer):
                    core.cmd_changelog(["--include-patch", "--print-only"])
                gen.assert_called_once_with(repo_root, True, False)

    def test_disable_history_flag_propagates(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_root = Path(tmpdir)
            with mock.patch.object(core, "is_inside_git_repo", return_value=True), mock.patch.object(
                core, "get_git_root", return_value=repo_root
            ), mock.patch.object(core, "generate_changelog_document", return_value="data") as gen:
                buffer = io.StringIO()
                with contextlib.redirect_stdout(buffer):
                    core.cmd_changelog(["--disable-history", "--print-only"])
                gen.assert_called_once_with(repo_root, False, True)

    def test_unknown_flag_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_root = Path(tmpdir)
            with mock.patch.object(core, "is_inside_git_repo", return_value=True), mock.patch.object(
                core, "get_git_root", return_value=repo_root
            ):
                buffer = io.StringIO()
                with contextlib.redirect_stderr(buffer):
                    with self.assertRaises(SystemExit):
                        core.cmd_changelog(["--include-unreleased", "--print-only"])
                self.assertIn("Invalid arguments for g changelog.", buffer.getvalue())

    def test_generate_document_orders_releases_descending(self):
        tags = [
            core.TagInfo(name="v1.0.0", iso_date="2024-01-01", object_name="a"),
            core.TagInfo(name="v1.1.0", iso_date="2024-02-01", object_name="b"),
            core.TagInfo(name="v1.2.0", iso_date="2024-03-01", object_name="c"),
        ]
        with mock.patch.object(core, "list_tags_sorted_by_date", return_value=tags), mock.patch.object(
            core, "_canonical_origin_base", return_value=None
        ), mock.patch.object(
            core,
            "generate_section_for_range",
            side_effect=["sec-old", "sec-mid", "sec-new"],
        ), mock.patch.object(core, "build_history_section", return_value="# History\nchrono"):
                document = core.generate_changelog_document(Path("/tmp"), include_patch=False)
        sections = [line for line in document.splitlines() if line.startswith("sec-")]
        self.assertEqual(sections, ["sec-new", "sec-mid", "sec-old"])
        self.assertIn("# History\nchrono", document)

    def test_generate_document_only_includes_minor_tags_by_default(self):
        repo_root = Path("/tmp")
        release_tags = [
            core.TagInfo(name="v0.0.9", iso_date="2024-02-01", object_name="b"),
            core.TagInfo(name="v0.1.0", iso_date="2024-03-01", object_name="c"),
        ]

        def list_tags(root, merged_ref=None):
            self.assertEqual(root, repo_root)
            return release_tags

        with mock.patch.object(core, "list_tags_sorted_by_date", side_effect=lambda root, merged_ref=None: list_tags(root, merged_ref)), mock.patch.object(
            core, "_canonical_origin_base", return_value=None
        ), mock.patch.object(core, "build_history_section", return_value="# History\n"), mock.patch.object(
            core, "generate_section_for_range", return_value="sec"
        ) as generate_section:
            core.generate_changelog_document(repo_root, include_patch=False)
        # v0.0.9 is not a minor release; only v0.1.0 produces a section
        self.assertEqual(generate_section.call_count, 1)

    def test_generate_document_uses_minor_tag_ranges_only(self):
        tags = [
            core.TagInfo(name="v0.0.5", iso_date="2024-01-01", object_name="a"),
            core.TagInfo(name="v0.1.0", iso_date="2024-02-01", object_name="b"),
            core.TagInfo(name="v0.2.0", iso_date="2024-03-01", object_name="c"),
        ]
        calls = []

        def record_range(_root, _title, _date, rev_range, expected_version=None):
            calls.append(rev_range)
            return f"sec-{rev_range}"

        with mock.patch.object(core, "list_tags_sorted_by_date", return_value=tags), mock.patch.object(
            core, "_canonical_origin_base", return_value=None
        ), mock.patch.object(
            core, "generate_section_for_range", side_effect=record_range
        ), mock.patch.object(core, "build_history_section", return_value=None):
            core.generate_changelog_document(Path("/tmp"), include_patch=False)
        # v0.0.5 is not a minor release; only v0.1.0 and v0.2.0 produce sections
        self.assertEqual(calls, ["v0.1.0", "v0.1.0..v0.2.0"])

    def test_generate_document_empty_without_minor_releases(self):
        # All tags are pre-0.1.0; without --include-patch the body is empty
        tags = [core.TagInfo(name="v0.0.5", iso_date="2024-01-01", object_name="a")]

        with mock.patch.object(core, "list_tags_sorted_by_date", return_value=tags), mock.patch.object(
            core, "_canonical_origin_base", return_value=None
        ), mock.patch.object(
            core, "generate_section_for_range", return_value="sec"
        ) as generate_section, mock.patch.object(core, "build_history_section", return_value=None):
            document = core.generate_changelog_document(Path("/tmp"), include_patch=False)
        generate_section.assert_not_called()
        self.assertNotIn("sec", document)

    def test_generate_document_includes_patch_when_no_minor(self):
        # All tags are pre-0.1.0; with --include-patch the latest patch appears
        tags = [
            core.TagInfo(name="v0.0.5", iso_date="2024-01-01", object_name="a"),
            core.TagInfo(name="v0.0.9", iso_date="2024-02-01", object_name="b"),
        ]
        calls = []

        def record_range(_root, _title, _date, rev_range, expected_version=None):
            calls.append(rev_range)
            return "sec"

        with mock.patch.object(core, "list_tags_sorted_by_date", return_value=tags), mock.patch.object(
            core, "_canonical_origin_base", return_value=None
        ), mock.patch.object(
            core, "generate_section_for_range", side_effect=record_range
        ), mock.patch.object(core, "build_history_section", return_value=None):
            document = core.generate_changelog_document(Path("/tmp"), include_patch=True)
        # Only v0.0.9 (latest patch) appears; range is the tag itself (from beginning)
        self.assertEqual(calls, ["v0.0.9"])
        self.assertIn("sec", document)

    def test_generate_document_includes_patch_after_minor(self):
        # With --include-patch the latest patch after the last minor is prepended
        tags = [
            core.TagInfo(name="v0.1.0", iso_date="2024-01-01", object_name="a"),
            core.TagInfo(name="v0.1.1", iso_date="2024-02-01", object_name="b"),
            core.TagInfo(name="v0.1.2", iso_date="2024-03-01", object_name="c"),
        ]
        calls = []

        def record_range(_root, _title, _date, rev_range, expected_version=None):
            calls.append(rev_range)
            return f"sec-{rev_range}"

        with mock.patch.object(core, "list_tags_sorted_by_date", return_value=tags), mock.patch.object(
            core, "_canonical_origin_base", return_value=None
        ), mock.patch.object(
            core, "generate_section_for_range", side_effect=record_range
        ), mock.patch.object(core, "build_history_section", return_value=None):
            document = core.generate_changelog_document(Path("/tmp"), include_patch=True)
        # v0.1.2 is the latest patch after last minor v0.1.0; v0.1.1 is not the latest
        self.assertIn("v0.1.0..v0.1.2", calls)
        # v0.1.0 minor section also present (from beginning)
        self.assertIn("v0.1.0", calls)
        # v0.1.2 patch section appears first in document (newest); split by newline to avoid substring overlap
        sections = [line for line in document.splitlines() if line.startswith("sec-")]
        self.assertEqual(sections[0], "sec-v0.1.0..v0.1.2", "patch section must be first")
        self.assertIn("sec-v0.1.0", sections, "minor section must also appear")

    def test_history_section_contains_only_minor_tags_without_include_patch(self):
        repo_root = Path("/tmp")
        all_tags = [
            core.TagInfo(name="v0.0.1", iso_date="2024-01-01", object_name="a"),
            core.TagInfo(name="v0.1.0", iso_date="2024-02-01", object_name="b"),
            core.TagInfo(name="v0.2.0", iso_date="2024-03-01", object_name="c"),
        ]
        expected_history = [
            core.TagInfo(name="v0.1.0", iso_date="2024-02-01", object_name="b"),
            core.TagInfo(name="v0.2.0", iso_date="2024-03-01", object_name="c"),
        ]
        with mock.patch.object(core, "list_tags_sorted_by_date", return_value=all_tags) as list_tags_mock, mock.patch.object(
            core, "_canonical_origin_base", return_value="https://example.com/repo"
        ), mock.patch.object(
            core, "generate_section_for_range", return_value=None
        ), mock.patch.object(core, "build_history_section", return_value="# History\n") as build_history:
            core.generate_changelog_document(repo_root, include_patch=False)
        list_tags_mock.assert_called_once_with(repo_root)
        build_history.assert_called_once_with(repo_root, expected_history, False, include_unreleased_link=False)

    def test_history_section_includes_patch_tag_when_include_patch(self):
        repo_root = Path("/tmp")
        all_tags = [
            core.TagInfo(name="v0.1.0", iso_date="2024-01-01", object_name="a"),
            core.TagInfo(name="v0.1.1", iso_date="2024-02-01", object_name="b"),
        ]
        expected_history = [
            core.TagInfo(name="v0.1.0", iso_date="2024-01-01", object_name="a"),
            core.TagInfo(name="v0.1.1", iso_date="2024-02-01", object_name="b"),
        ]
        with mock.patch.object(core, "list_tags_sorted_by_date", return_value=all_tags) as list_tags_mock, mock.patch.object(
            core, "_canonical_origin_base", return_value="https://example.com/repo"
        ), mock.patch.object(
            core, "generate_section_for_range", return_value=None
        ), mock.patch.object(core, "build_history_section", return_value="# History\n") as build_history:
            core.generate_changelog_document(repo_root, include_patch=True)
        list_tags_mock.assert_called_once_with(repo_root)
        build_history.assert_called_once_with(repo_root, expected_history, False, include_unreleased_link=False)

    def test_history_section_is_omitted_when_disable_history_true(self):
        repo_root = Path("/tmp")
        tags = [core.TagInfo(name="v0.1.0", iso_date="2024-01-01", object_name="a")]
        with mock.patch.object(core, "list_tags_sorted_by_date", return_value=tags), mock.patch.object(
            core, "_canonical_origin_base", return_value="https://example.com/repo"
        ), mock.patch.object(
            core, "generate_section_for_range", return_value=None
        ), mock.patch.object(core, "build_history_section", return_value="# History\n") as build_history:
            core.generate_changelog_document(repo_root, include_patch=False, disable_history=True)
        build_history.assert_not_called()

    def test_history_includes_release_list(self):
        repo_root = Path("/tmp")
        tags = [
            core.TagInfo(name="v0.1.0", iso_date="2024-03-01", object_name="c"),
            core.TagInfo(name="v0.1.1", iso_date="2024-04-01", object_name="d"),
        ]
        with mock.patch.object(core, "_canonical_origin_base", return_value="https://github.com/Ogekuri/G"):
            history = core.build_history_section(repo_root, tags, include_unreleased=False)
        self.assertIsNotNone(history)
        assert history is not None
        lines = history.splitlines()
        self.assertEqual(lines[0], "# History")
        self.assertIn("- \\[0.1.0\\]: https://github.com/Ogekuri/G/releases/tag/v0.1.0", lines)
        self.assertIn("- \\[0.1.1\\]: https://github.com/Ogekuri/G/releases/tag/v0.1.1", lines)

    def test_history_omits_unreleased_link_without_section(self):
        repo_root = Path("/tmp")
        tags = [core.TagInfo(name="v0.1.0", iso_date="2024-03-01", object_name="c")]
        with mock.patch.object(core, "_canonical_origin_base", return_value="https://github.com/Ogekuri/G"):
            history = core.build_history_section(repo_root, tags, include_unreleased=True, include_unreleased_link=False)
        assert history is not None
        self.assertNotIn("[unreleased]:", history)

    def test_history_includes_unreleased_link_when_requested(self):
        repo_root = Path("/tmp")
        tags = [core.TagInfo(name="v0.1.0", iso_date="2024-03-01", object_name="c")]
        with mock.patch.object(core, "_canonical_origin_base", return_value="https://github.com/Ogekuri/G"):
            history = core.build_history_section(repo_root, tags, include_unreleased=True, include_unreleased_link=True)
        assert history is not None
        self.assertIn("[unreleased]: https://github.com/Ogekuri/G/compare/v0.1.0..HEAD", history)

    def test_history_includes_draft_releases_by_default(self):
        repo_root = Path("/tmp")
        tags = [
            core.TagInfo(name="v0.0.9", iso_date="2024-02-01", object_name="b"),
            core.TagInfo(name="v0.1.0", iso_date="2024-03-01", object_name="c"),
        ]
        with mock.patch.object(core, "_canonical_origin_base", return_value="https://github.com/Ogekuri/G"):
            history = core.build_history_section(repo_root, tags, include_unreleased=False)
        assert history is not None
        lines = history.splitlines()
        self.assertIn("- \\[0.0.9\\]: https://github.com/Ogekuri/G/releases/tag/v0.0.9", lines)
        self.assertIn("- \\[0.1.0\\]: https://github.com/Ogekuri/G/releases/tag/v0.1.0", lines)

    def test_categorize_commit_maps_implement_type(self):
        section, line = core.categorize_commit("implement(core): Add implementation command")
        self.assertEqual(section, "Implementations")
        self.assertEqual(line, "- Add implementation command *(core)*")

    def test_parse_conventional_commit_accepts_all_requested_prefix_variants(self):
        types = ["change", "cover", "docs", "fix", "implement", "misc", "new", "refactor", "revert", "style"]
        for ctype in types:
            for module in [None, "core"]:
                for breaking in [False, True]:
                    header = ctype
                    if module:
                        header += f"({module})"
                    if breaking:
                        header += "!"
                    parsed = core.parse_conventional_commit(f"{header}: description")
                    with self.subTest(header=header):
                        self.assertIsNotNone(parsed)
                        assert parsed is not None
                        parsed_type, parsed_module, parsed_breaking, parsed_desc = parsed
                        self.assertEqual(parsed_type, ctype)
                        self.assertEqual(parsed_module, module)
                        self.assertEqual(parsed_breaking, breaking)
                        self.assertEqual(parsed_desc, "description")

    def test_parse_conventional_commit_extracts_multiline_description(self):
        parsed = core.parse_conventional_commit("fix(core)!: first line\nsecond line")
        self.assertEqual(parsed, ("fix", "core", True, "first line\nsecond line"))

    def test_categorize_commit_formats_breaking_change_with_scope(self):
        section, line = core.categorize_commit("fix(core)!: first line")
        self.assertEqual(section, "Bug Fixes")
        self.assertEqual(line, "- BREAKING CHANGE: first line *(core)*")

    def test_categorize_commit_formats_multiline_description(self):
        section, line = core.categorize_commit("change(core)!: first line\nsecond line")
        self.assertEqual(section, "Changes")
        self.assertEqual(line, "- BREAKING CHANGE: first line *(core)*\n  second line")

    def test_categorize_commit_formats_multiline_with_blank_line(self):
        section, line = core.categorize_commit("change(core): first line\n\nCo-authored-by: Copilot <x@y.z>")
        self.assertEqual(section, "Changes")
        self.assertEqual(line, "- first line *(core)*")

    def test_categorize_commit_preserves_crlf_lines_verbatim_after_cleanup(self):
        section, line = core.categorize_commit(
            "change(core): first line\r\n\r\nCo-authored-by: Copilot <x@y.z>\r\nthird line"
        )
        self.assertEqual(section, "Changes")
        self.assertEqual(line, "- first line *(core)*\n  third line")

    def test_categorize_commit_flattens_markdown_list_body_to_semicolon_list(self):
        section, line = core.categorize_commit(
            "change(changelog): headline\n\n- first detail\n- second detail"
        )
        self.assertEqual(section, "Changes")
        self.assertEqual(line, "- headline *(changelog)*\n  first detail; second detail")

    def test_generate_section_keeps_commit_bullets_consecutive(self):
        with mock.patch.object(
            core,
            "git_log_subjects",
            return_value=[
                "change(core): first line\nsecond line",
                "change(core): third line",
            ],
        ):
            section = core.generate_section_for_range(Path("/tmp"), "v1.2.3", "2026-02-18", "v1.2.2..v1.2.3")
        self.assertIsNotNone(section)
        assert section is not None
        self.assertIn("- first line *(core)*\n  second line\n- third line *(core)*", section)

    def test_generate_section_indents_all_continuations_before_next_commit(self):
        with mock.patch.object(
            core,
            "git_log_subjects",
            return_value=[
                "fix(core): first\n# heading\n> quote\n- one\n- two\ntail",
                "fix: second\nsecond detail",
            ],
        ):
            section = core.generate_section_for_range(
                Path("/tmp"), "v1.2.3", "2026-02-18", "v1.2.2..v1.2.3"
            )
        self.assertIn(
            "- first *(core)*\n  # heading\n  > quote\n  one; two\n  tail"
            "\n- second\n  second detail",
            section,
        )

    def test_git_log_subjects_reads_full_commit_messages(self):
        payload = "fix(core)!: first line\n\nsecond line" + core.RECORD
        with mock.patch.object(core, "run_git_text", return_value=payload) as run_git_text:
            messages = core.git_log_subjects(Path("/tmp"), "v1.0.0..v1.1.0")
        self.assertEqual(messages, ["fix(core)!: first line\n\nsecond line"])
        run_git_text.assert_called_once_with(
            ["log", "--no-merges", f"--pretty=format:%B{core.RECORD}", "v1.0.0..v1.1.0"],
            cwd=Path("/tmp"),
            check=False,
        )

    def test_generate_section_renders_implementations_header_with_icon(self):
        with mock.patch.object(
            core,
            "git_log_subjects",
            return_value=["implement(core): Build command pipeline"],
        ):
            section = core.generate_section_for_range(Path("/tmp"), "v1.2.3", "2026-02-18", "v1.2.2..v1.2.3")
        self.assertIsNotNone(section)
        assert section is not None
        self.assertIn("### 🏗️  Implementations", section)

    def test_extract_release_version_accepts_new_release_marker(self):
        self.assertEqual(core._extract_release_version("release: Release version 1.2.3"), "1.2.3")

    def test_extract_release_version_keeps_legacy_release_marker(self):
        self.assertEqual(core._extract_release_version("release version: 1.2.3"), "1.2.3")

    def test_generate_section_ignores_release_marker_commits(self):
        with mock.patch.object(
            core,
            "git_log_subjects",
            return_value=["release: Release version 1.2.3"],
        ):
            section = core.generate_section_for_range(Path("/tmp"), "v1.2.3", "2026-02-18", "v1.2.2..v1.2.3")
        self.assertIsNone(section)


class MinorReleaseTagPredicateTest(unittest.TestCase):
    def test_minor_release_tags(self):
        for tag in ("v0.1.0", "0.1.0", "v0.2.0", "v1.0.0", "v1.1.0", "v2.3.0"):
            with self.subTest(tag=tag):
                self.assertTrue(core._is_minor_release_tag(tag), f"{tag} should be minor")

    def test_non_minor_release_tags(self):
        for tag in ("v0.0.1", "v0.0.42", "v0.1.1", "v1.0.1", "v1.2.3", "notasemver"):
            with self.subTest(tag=tag):
                self.assertFalse(core._is_minor_release_tag(tag), f"{tag} should not be minor")


class LatestPatchTagAfterTest(unittest.TestCase):
    def _make(self, name, date="2024-01-01"):
        return core.TagInfo(name=name, iso_date=date, object_name="x")

    def test_returns_latest_patch_after_last_minor(self):
        tags = [
            self._make("v0.1.0", "2024-01-01"),
            self._make("v0.1.1", "2024-02-01"),
            self._make("v0.1.2", "2024-03-01"),
        ]
        last_minor = tags[0]
        result = core._latest_patch_tag_after(tags, last_minor)
        self.assertIsNotNone(result)
        assert result is not None
        self.assertEqual(result.name, "v0.1.2")

    def test_returns_none_when_no_patch_after_minor(self):
        tags = [
            self._make("v0.1.0", "2024-01-01"),
            self._make("v0.2.0", "2024-02-01"),
        ]
        last_minor = tags[1]
        self.assertIsNone(core._latest_patch_tag_after(tags, last_minor))

    def test_returns_latest_patch_when_no_minor(self):
        tags = [
            self._make("v0.0.1", "2024-01-01"),
            self._make("v0.0.9", "2024-02-01"),
            self._make("v0.0.42", "2024-03-01"),
        ]
        result = core._latest_patch_tag_after(tags, None)
        self.assertIsNotNone(result)
        assert result is not None
        self.assertEqual(result.name, "v0.0.42")

    def test_returns_none_when_all_tags_empty(self):
        self.assertIsNone(core._latest_patch_tag_after([], None))


class GetRemoteNameForBranchTest(unittest.TestCase):
    """Tests for _get_remote_name_for_branch (REQ-046)."""

    def setUp(self):
        core.CONFIG.update(core.DEFAULT_CONFIG)

    def test_returns_configured_remote_when_present(self):
        # Arrange: git config returns a non-empty remote name
        with mock.patch.object(core, "run_git_text", return_value="upstream\n"):
            result = core._get_remote_name_for_branch("master", Path("/tmp/repo"))
        # Assert: configured name is returned verbatim
        self.assertEqual(result, "upstream")

    def test_falls_back_to_origin_when_config_empty(self):
        # Arrange: git config returns empty string (key not set)
        with mock.patch.object(core, "run_git_text", return_value=""):
            result = core._get_remote_name_for_branch("master", Path("/tmp/repo"))
        # Assert: fallback is "origin"
        self.assertEqual(result, "origin")

    def test_falls_back_to_origin_when_config_whitespace_only(self):
        # Arrange: git config returns whitespace only
        with mock.patch.object(core, "run_git_text", return_value="   \n"):
            result = core._get_remote_name_for_branch("master", Path("/tmp/repo"))
        # Assert: stripped whitespace treated as empty → fallback
        self.assertEqual(result, "origin")

    def test_passes_correct_git_config_key(self):
        # Arrange: capture the args passed to run_git_text
        calls = []
        def capture(args, **kwargs):
            calls.append(args)
            return "origin"
        with mock.patch.object(core, "run_git_text", side_effect=capture):
            core._get_remote_name_for_branch("develop", Path("/tmp/repo"))
        # Assert: correct branch-scoped config key is queried
        self.assertEqual(calls[0], ["config", "--get", "branch.develop.remote"])


class CanonicalOriginBaseTest(unittest.TestCase):
    """Tests for _canonical_origin_base using master-branch remote (REQ-043, REQ-046)."""

    def setUp(self):
        core.CONFIG.update(core.DEFAULT_CONFIG)

    def _make_run_git_text(self, config_remote, remote_url):
        """Return a side_effect function that returns config_remote on first call and remote_url on second."""
        responses = [config_remote, remote_url]
        call_count = {"n": 0}

        def fake(args, **kwargs):
            idx = call_count["n"]
            call_count["n"] += 1
            return responses[idx] if idx < len(responses) else ""

        return fake

    def test_resolves_ssh_url_using_master_remote(self):
        # Arrange: master remote is "upstream", URL is SSH
        side_effect = self._make_run_git_text("upstream", "git@github.com:Ogekuri/html2tree.git")
        with mock.patch.object(core, "run_git_text", side_effect=side_effect):
            result = core._canonical_origin_base(Path("/tmp/repo"))
        # Assert: normalized HTTPS URL without .git
        self.assertEqual(result, "https://github.com/Ogekuri/html2tree")

    def test_resolves_https_url_using_master_remote(self):
        # Arrange: git config returns empty → falls back to "origin"; URL is HTTPS with .git
        side_effect = self._make_run_git_text("", "https://github.com/Ogekuri/G.git")
        with mock.patch.object(core, "run_git_text", side_effect=side_effect):
            result = core._canonical_origin_base(Path("/tmp/repo"))
        # Assert: .git stripped, HTTPS base returned
        self.assertEqual(result, "https://github.com/Ogekuri/G")

    def test_returns_none_when_remote_url_empty(self):
        # Arrange: config returns a remote but get-url returns empty
        side_effect = self._make_run_git_text("origin", "")
        with mock.patch.object(core, "run_git_text", side_effect=side_effect):
            result = core._canonical_origin_base(Path("/tmp/repo"))
        # Assert: None when URL cannot be resolved
        self.assertIsNone(result)

    def test_uses_master_branch_from_config(self):
        # Arrange: CONFIG has a custom master branch name
        core.CONFIG["master"] = "main"
        captured_args = []

        def capture(args, **kwargs):
            captured_args.append(list(args))
            return ""

        with mock.patch.object(core, "run_git_text", side_effect=capture):
            core._canonical_origin_base(Path("/tmp/repo"))
        # Assert: git config query uses the configured master branch name
        self.assertIn(["config", "--get", "branch.main.remote"], captured_args)

    def test_returns_none_for_invalid_url_structure(self):
        # Arrange: URL passes basic checks but lacks valid scheme/netloc after parsing
        side_effect = self._make_run_git_text("origin", "not-a-valid-url")
        with mock.patch.object(core, "run_git_text", side_effect=side_effect):
            result = core._canonical_origin_base(Path("/tmp/repo"))
        # Assert: None when urlparse cannot produce a valid base
        self.assertIsNone(result)

    def test_returns_none_when_remote_get_url_command_fails(self):
        calls = {"n": 0}

        def side_effect(args, **kwargs):
            if calls["n"] == 0:
                calls["n"] += 1
                return "origin"
            raise RuntimeError("fatal: no such remote")

        with mock.patch.object(core, "run_git_text", side_effect=side_effect):
            result = core._canonical_origin_base(Path("/tmp/repo"))
        self.assertIsNone(result)
