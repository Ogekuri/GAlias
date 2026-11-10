import contextlib
import io
import re
import unittest
from unittest import mock

from git_alias import core


class AliasHelpTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.module = core
        cls.expected_help = cls.module.HELP_TEXTS.copy()

    @staticmethod
    def run_script(args):
        code, stdout, _ = AliasHelpTest.run_script_result(args, check=True)
        if code != 0:
            raise AssertionError(f"Expected exit code 0, got {code}")
        return stdout.strip()

    @staticmethod
    def run_script_result(args, check=True, *, check_updates=False):
        out = io.StringIO()
        err = io.StringIO()
        exit_code = 0
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            try:
                core.main(args, check_updates=check_updates)
            except SystemExit as exc:
                exit_code = int(exc.code) if isinstance(exc.code, int) else 1
        if check and exit_code != 0:
            raise AssertionError(f"Expected exit code 0, got {exit_code}: {err.getvalue()}")
        return exit_code, out.getvalue(), err.getvalue()

    def test_all_commands_have_help_text(self):
        missing = [
            name
            for name in self.module.COMMANDS
            if name not in self.module.HELP_TEXTS
        ]
        self.assertFalse(
            missing,
            msg=f"Help texts missing for commands: {', '.join(sorted(missing))}",
        )

    def test_hlal_matches_help_dictionary(self):
        for alias, desc in self.expected_help.items():
            self.assertIn(
                alias,
                self.module.HELP_TEXTS,
                msg=f"{alias} missing from HELP_TEXTS",
            )
            self.assertEqual(
                self.module.HELP_TEXTS[alias],
                desc,
                msg=f"{alias} description does not match hlal",
            )

    def test_global_help_contains_hlal_entries(self):
        output = self.run_script(["--help"])
        for alias, desc in self.expected_help.items():
            pattern = re.compile(
                rf"^\s*{re.escape(alias)}\s+-\s+{re.escape(desc)}\s*$",
                re.MULTILINE,
            )
            self.assertRegex(
                output,
                pattern,
                msg=f"{alias} help missing from global --help",
            )

    def test_management_help_order(self):
        output = self.run_script(["--help"])
        lines = output.splitlines()
        self.assertIn("Management Commands:", lines)
        start = lines.index("Management Commands:")
        entries = []
        for line in lines[start + 1 :]:
            if not line.strip():
                break
            entries.append(line.strip())
        flags = [line.split()[0] for line in entries if line.strip()]
        self.assertGreaterEqual(len(flags), 3)
        self.assertEqual(flags[:3], ["--write-config", "--upgrade", "--uninstall"])
        self.assertIn("--help", flags)

    def test_individual_help_matches_hlal(self):
        reset_aliases = getattr(self.module, "RESET_HELP_COMMANDS", set())
        for alias, desc in self.expected_help.items():
            output = self.run_script([alias, "--help"])
            if alias in reset_aliases:
                self.assertEqual(
                    output,
                    self.module.RESET_HELP.strip(),
                    msg=f"{alias} should print RESET_HELP when invoked with --help",
                )
            else:
                self.assertEqual(
                    output,
                    f"{alias} - {desc}",
                    msg=f"{alias} help output unexpected",
                )

    def test_reset_commands_show_reset_help(self):
        expected = self.module.RESET_HELP.strip()
        for alias in sorted(self.module.RESET_HELP_COMMANDS):
            output = self.run_script([alias, "--help"])
            self.assertEqual(
                output,
                expected,
                msg=f"{alias} did not emit RESET_HELP on --help",
            )

    def test_help_lists_command_options_when_present(self):
        expected_flags = {
            "changelog": ["--include-patch", "--force-write", "--print-only", "--disable-history"],
            "patch": ["--include-patch"],
            "ver": ["--verbose", "--debug"],
        }
        for alias, flags in expected_flags.items():
            output = self.run_script([alias, "--help"])
            for flag in flags:
                self.assertIn(
                    flag,
                    output,
                    msg=f"{alias} help missing option {flag}",
                )

    def test_conventional_alias_help_documents_module_prefix(self):
        aliases = ["new", "fix", "change", "implement", "refactor", "docs", "style", "revert", "misc", "cover"]
        for alias in aliases:
            output = self.run_script([alias, "--help"])
            self.assertIn("<module>: <description>", output, msg=f"{alias} help missing module prefix syntax")
            self.assertIn("default_commit_module", output, msg=f"{alias} help missing default module fallback")

    def test_usage_includes_version_when_no_args(self):
        code, stdout, _ = self.run_script_result([], check=False)
        self.assertNotEqual(code, 0)
        version = self.module.get_cli_version()
        expected = f"Usage: g <command> [options] ({version})"
        self.assertIn(expected, stdout.splitlines())

    def test_global_version_flags(self):
        version = self.module.get_cli_version()
        for flag in ("--ver", "--version"):
            with self.subTest(flag=flag):
                with mock.patch.object(
                    core, "check_for_newer_version", return_value="9.9.9"
                ) as check_update, mock.patch.object(
                    core, "_fetch_github_latest_version", return_value=("9.9.8", None)
                ) as fetch_github:
                    _, stdout, _ = self.run_script_result([flag], check=True)
                check_update.assert_called_once()
                fetch_github.assert_called_once()
                self.assertEqual(
                    stdout.strip(),
                    f"Current Installed : {version}\n"
                    f"Latest @ PyPI     : 9.9.9\n"
                    f"Latest @ GitHub   : 9.9.8",
                )

    ## @brief Verify unavailable remote sources render as unavailable (REQ-202, REQ-230, REQ-231).
    # @details Mock the PyPI fetcher returning None and the GitHub fetcher
    #          returning no version plus the intercepted failure reason; the
    #          installed version line stays first, the PyPI line degrades
    #          deterministically, and the GitHub line renders the REQ-241-aligned
    #          `Latest @ GitHub   : unknown (<reason>)` degradation.
    # @param self {AliasHelpTest} Isolated test instance.
    # @return {None} Assert REQ-202/REQ-230/REQ-231 degraded output.
    def test_global_version_flags_report_unavailable_sources(self):
        version = self.module.get_cli_version()
        github_failure_reason = (
            "HTTP 404: Not Found: API rate limit exceeded for 203.0.113.7."
        )
        with mock.patch.object(core, "check_for_newer_version", return_value=None), \
                mock.patch.object(
                    core,
                    "_fetch_github_latest_version",
                    return_value=(None, github_failure_reason),
                ):
            _, stdout, _ = self.run_script_result(["--ver"], check=True)
        self.assertEqual(
            stdout.strip(),
            f"Current Installed : {version}\n"
            f"Latest @ PyPI     : unavailable"
            f"\nLatest @ GitHub   : unknown ({github_failure_reason})",
        )

    def test_global_version_flags_force_online_update_check(self):
        for flag in ("--ver", "--version"):
            with self.subTest(flag=flag):
                with mock.patch.object(core, "check_for_newer_version") as check_update:
                    self.run_script_result([flag], check=True, check_updates=False)
                check_update.assert_called_once()
                kwargs = check_update.call_args.kwargs
                self.assertEqual(
                    kwargs.get("timeout_seconds"),
                    core.VERSION_CHECK_TIMEOUT_SECONDS,
                )
                self.assertIsNotNone(kwargs.get("repo_root"))
                self.assertTrue(kwargs.get("ignore_idle_cache"))

    def test_upgrade_flag_invokes_upgrade_self(self):
        with mock.patch.object(core, "upgrade_self") as upgrade_self:
            self.run_script_result(["--upgrade"], check=True)
        upgrade_self.assert_called_once()
        args, _ = upgrade_self.call_args
        self.assertEqual(len(args), 1)
        self.assertTrue(str(args[0]))

    ## @brief Verify --develop outside allowed commands is rejected (REQ-203).
    # @details The modifier is valid only with --upgrade, major, minor, or
    #          patch; any other first token exits non-zero with explicit
    #          English stderr guidance listing the allowed commands.
    # @param self {AliasHelpTest} Isolated test instance.
    # @return {None} Assert REQ-203 rejection.
    def test_develop_flag_without_upgrade_is_rejected(self):
        code, _, err = self.run_script_result(["--develop"], check=False)
        self.assertNotEqual(code, 0)
        self.assertIn(
            "supported only with '--upgrade', 'major', 'minor', and 'patch'",
            err,
        )
        code, _, err = self.run_script_result(["co", "--dev"], check=False)
        self.assertNotEqual(code, 0)
        self.assertIn(
            "supported only with '--upgrade', 'major', 'minor', and 'patch'",
            err,
        )

    ## @brief Verify --upgrade --develop (and equivalent --dev) route the GitHub source (REQ-201).
    # @details Mock the upgrade boundary; assert the github selector is True
    #          for both equivalent flags.
    # @param self {AliasHelpTest} Isolated test instance.
    # @return {None} Assert REQ-201 dispatch for each equivalent flag.
    def test_upgrade_develop_flags_select_github_source(self):
        for flag in ("--develop", "--dev"):
            with self.subTest(flag=flag):
                with mock.patch.object(core, "upgrade_self") as upgrade_self:
                    self.run_script_result(["--upgrade", flag], check=True)
                upgrade_self.assert_called_once()
                self.assertTrue(upgrade_self.call_args.kwargs.get("github"))

    ## @brief Verify `--upgrade --force` routes the forced install selector (REQ-238).
    # @details Mock the upgrade boundary; assert `force=True` for the forced
    #          PyPI and GitHub paths (with and without `--develop`/`--dev`)
    #          and `force=False` for the standard unforced path.
    # @param self {AliasHelpTest} Isolated test instance.
    # @return {None} Assert REQ-238 main-routing force selector (REQ-236, REQ-237).
    def test_upgrade_force_flag_selects_forced_install(self):
        for extra, expected_github, expected_force in (
            ((), False, False),
            (("--force",), False, True),
            (("--develop", "--force"), True, True),
            (("--force", "--dev"), True, True),
        ):
            with self.subTest(extra=extra):
                argv = ["--upgrade", *extra]
                with mock.patch.object(core, "upgrade_self") as upgrade_self:
                    self.run_script_result(argv, check=True)
                upgrade_self.assert_called_once()
                self.assertIs(upgrade_self.call_args.kwargs.get("force"), expected_force)
                self.assertIs(upgrade_self.call_args.kwargs.get("github"), expected_github)

    ## @brief Verify a first-token `--force` outside `--upgrade` is rejected (REQ-238).
    # @details The modifier is valid only with `--upgrade`; any other first
    #          token exits non-zero with explicit English stderr guidance.
    # @param self {AliasHelpTest} Isolated test instance.
    # @return {None} Assert REQ-238 rejection.
    def test_force_flag_without_upgrade_is_rejected(self):
        code, _, err = self.run_script_result(["--force"], check=False)
        self.assertNotEqual(code, 0)
        self.assertIn("supported only with '--upgrade'", err)
        code, _, err = self.run_script_result(["--ver", "--force"], check=False)
        self.assertNotEqual(code, 0)
        self.assertIn("supported only with '--upgrade'", err)

    ## @brief Verify release commands accept --dev/--develop through main (REQ-200, REQ-203).
    # @details The dispatcher must not reject the release-scope flags; mock
    #          the release boundary and assert each level dispatches with
    #          dev_release=True. The parse-level call carries no changelog
    #          flags: patch auto-adds --include-patch downstream inside
    #          _execute_release_flow per REQ-026.
    # @param self {AliasHelpTest} Isolated test instance.
    # @return {None} Assert REQ-200 main-routing acceptance.
    def test_release_commands_accept_dev_flag_through_main(self):
        expected_changelog = {
            "major": [],
            "minor": [],
            "patch": [],
        }
        for level in ("major", "minor", "patch"):
            for flag in ("--dev", "--develop"):
                with self.subTest(level=level, flag=flag):
                    with mock.patch.object(
                        core, "_run_release_command"
                    ) as run_release:
                        self.run_script_result([level, flag], check=True)
                    run_release.assert_called_once_with(
                        level,
                        changelog_args=expected_changelog[level],
                        exec_args=[],
                        dev_release=True,
                    )

    def test_uninstall_flag_invokes_uninstall_self(self):
        with mock.patch.object(core, "uninstall_self") as uninstall_self:
            self.run_script_result(["--uninstall"], check=True)
        uninstall_self.assert_called_once_with()

    def test_update_check_runs_before_empty_args_validation(self):
        events = []

        def _record_update(
            *,
            repo_root=None,
            timeout_seconds: float = 1.0,
            ignore_idle_cache: bool = False,
        ):
            del repo_root, timeout_seconds, ignore_idle_cache
            events.append("update")

        def _record_help():
            events.append("help")

        with mock.patch.object(core, "check_for_newer_version", side_effect=_record_update):
            with mock.patch.object(core, "print_all_help", side_effect=_record_help):
                code, _, _ = self.run_script_result([], check=False, check_updates=True)

        self.assertNotEqual(code, 0)
        self.assertEqual(events, ["update", "help"])

    def test_update_check_runs_before_unknown_help_target_validation(self):
        with mock.patch.object(core, "check_for_newer_version") as check_update:
            code, _, _ = self.run_script_result(
                ["--help", "not-a-command"],
                check=False,
                check_updates=True,
            )

        self.assertNotEqual(code, 0)
        check_update.assert_called_once()
        kwargs = check_update.call_args.kwargs
        self.assertEqual(
            kwargs.get("timeout_seconds"),
            core.VERSION_CHECK_TIMEOUT_SECONDS,
        )
        self.assertIsNotNone(kwargs.get("repo_root"))

    ## @brief Verify corrected help entries match the implemented alias behavior.
    # @details Keyword-level accuracy contract for HELP_TEXTS entries corrected
    #          against the delegated git commands: each corrected entry MUST
    #          name the wrapped command or configuration key, and MUST NOT
    #          retain removed misinformation ("zip" archive for the tar.gz
    #          `ar` flow, "Git K" for the configured `gp_command`/`gr_command`
    #          viewers, "latest full commit hash" for the full-history `ll`
    #          log, current-branch wording for the local+origin `rmtg` delete,
    #          origin-scoped wording for the all-remotes `feall` fetch).
    #          Level 0 UUT: HELP_TEXTS data contract; deterministic and fully
    #          isolated (no network, filesystem, clock, or process access).
    # @param self {AliasHelpTest} Isolated test instance.
    # @return {None} Assert required keywords present and stale keywords absent.
    def test_corrected_help_entries_match_implemented_behavior(self):
        # Arrange: explicit expected keyword outcomes per corrected alias.
        required_keywords = {
            "aa": ("stage area",),
            "ar": ("tar.gz",),
            "br": ("git branch",),
            "ck": ("git diff --check",),
            "de": ("git describe",),
            "feall": ("all remotes",),
            "gp": ("gp_command",),
            "gr": ("gr_command",),
            "ll": ("full commit hashes",),
            "me": ("--ff-only",),
            "rf": ("git reflog",),
            "rmtg": ("origin", "<tag>"),
            "tg": ("annotated",),
        }
        forbidden_keywords = {
            "aa": ("changes/added",),
            "ar": ("zip",),
            "br": ("Create a new branch.",),
            "de": ("last tagged commit details",),
            "feall": ("from origin for all branch",),
            "gp": ("Git K",),
            "gr": ("Git K",),
            "ll": ("latest full commit hash",),
            "rf": ("changes on HEAD reference",),
            "rmtg": ("current branch",),
            "tg": ("annotate tag",),
        }
        # Act: read the help dictionary under test.
        help_texts = self.module.HELP_TEXTS
        # Assert: every corrected entry keeps required keywords and drops stale ones.
        for alias, keywords in required_keywords.items():
            for keyword in keywords:
                with self.subTest(alias=alias, kind="required"):
                    self.assertIn(
                        keyword,
                        help_texts[alias],
                        msg=f"{alias} help missing required keyword: {keyword}",
                    )
        for alias, keywords in forbidden_keywords.items():
            for keyword in keywords:
                with self.subTest(alias=alias, kind="forbidden"):
                    self.assertNotIn(
                        keyword,
                        help_texts[alias],
                        msg=f"{alias} help retains stale keyword: {keyword}",
                    )
