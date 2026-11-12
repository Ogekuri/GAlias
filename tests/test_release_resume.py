## @brief Isolated release-publication recovery contract tests.
# @details HDT levels: parsing/push helper -> resume orchestration -> CLI dispatch.
# All Git, filesystem discovery, version detection, and checkout dependencies are mocked.

import subprocess
import unittest
from pathlib import Path
from unittest import mock

from git_alias import core


## @brief Verify release-publication recovery contracts with isolated Git boundaries.
# @details Every Git query, version detection, publication, and checkout dependency is
#          replaced by deterministic mocks; no subprocess, filesystem, or network access.
#          SubTest iterations reset observable mocks to keep expectations independent.
class ReleaseResumeTest(unittest.TestCase):
    ## @brief Build a deterministic prepared release and remote snapshot.
    # @details O(1) fixture setup; all module patches are restored after each test.
    #          `push_impl` captures the real publication helper before mocking so
    #          helper-contract tests execute production logic with a mocked Git boundary.
    # @param self {ReleaseResumeTest} Isolated test instance.
    # @return {None} Populates response map and observable mock attributes.
    def setUp(self):
        ## @brief Real `_push_release_refs` captured before module-level mocking.
        self.push_impl = core._push_release_refs
        ## @brief Synthetic object identities and Git query results; string values only.
        self.responses = {
            ("status", "--porcelain"): "",
            ("rev-parse", "--verify", "refs/heads/work^{commit}"): "commit",
            ("rev-parse", "--verify", "refs/heads/develop^{commit}"): "commit",
            ("rev-parse", "--verify", "refs/heads/master^{commit}"): "commit",
            ("show", "-s", "--format=%s", "commit"): "release: Release version 1.3.0",
            ("rev-parse", "--verify", "refs/tags/v1.3.0"): "tag-object",
            ("cat-file", "-t", "tag-object"): "tag",
            ("rev-parse", "--verify", "refs/tags/v1.3.0^{commit}"): "commit",
            ("remote", "get-url", "--push", "--all", "origin"): "/synthetic/publish.git",
            "remote": "old refs/heads/develop\nold refs/heads/master",
        }

        ## @brief Serve explicit Git queries and fail on unexpected commands.
        # @details O(1) lookup; publication is separately mocked; no subprocess execution.
        # @param args {list[str]} Git argv excluding executable.
        # @return {str} Synthetic command stdout.
        # @throws KeyError Unplanned Git command.
        def query(args):
            if args[0] == "ls-remote":
                assert args[1:3] == ["--", "/synthetic/publish.git"]
                return self.responses["remote"]
            return self.responses[tuple(args)]

        self.enterContext(mock.patch.object(core, "get_branch", side_effect=lambda key: key))
        self.git_mock = self.enterContext(
            mock.patch.object(core, "run_git_text", side_effect=query)
        )
        self.enterContext(mock.patch.object(core, "get_git_root", return_value=Path("/synthetic")))
        self.enterContext(
            mock.patch.object(core, "get_version_rules", return_value=[("version", "x")])
        )
        self.version_mock = self.enterContext(
            mock.patch.object(core, "_determine_canonical_version", return_value="1.3.0")
        )
        self.branch_mock = self.enterContext(
            mock.patch.object(core, "_current_branch_name", return_value="master")
        )
        self.ancestor_mock = self.enterContext(
            mock.patch.object(core, "_is_commit_ancestor", return_value=True)
        )
        self.push_mock = self.enterContext(mock.patch.object(core, "_push_release_refs"))
        self.checkout_mock = self.enterContext(mock.patch.object(core, "cmd_co"))
        for symbol in ("cmd_chver", "cmd_tg", "cmd_changelog", "_execute_commit", "run_command", "cmd_me"):
            self.enterContext(mock.patch.object(core, symbol, side_effect=AssertionError(symbol)))

    ## @brief Verify standalone recovery and develop-scope parsing.
    # @details O(1) parser checks; no runtime side effects. The removed `--exec`
    #          option is rejected through the release-flag whitelist (REQ-322).
    # @param self {ReleaseResumeTest} Isolated test instance.
    # @return {None} Assert REQ-176, REQ-200, and REQ-322 rejection.
    def test_resume_parser(self):
        expected_output = (["--resume"], False)
        self.assertEqual(core._parse_release_flags(["--resume"], "minor"), expected_output)
        self.assertEqual(
            core._parse_release_flags(["--dev", "--resume"], "minor"),
            (["--resume"], True),
        )
        self.assertEqual(
            core._parse_release_flags(["--resume", "--develop"], "minor"),
            (["--resume"], True),
        )
        self.assertEqual(core._parse_release_flags(["--dev"], "minor"), ([], True))
        with self.assertRaises(SystemExit):
            core._parse_release_flags(["--exec", "build", "--resume"], "minor")

    ## @brief Reject combined recovery and creation options.
    # @details SubTest per invalid argv; parser exits before side effects.
    # @param self {ReleaseResumeTest} Isolated test instance.
    # @return {None} Assert REQ-176 standalone-only mode.
    def test_resume_rejects_combined_options(self):
        cases = [
            ["--resume", "--include-patch"], ["--include-patch", "--resume"],
            ["--resume", "--exec", "build"], ["--resume", "--resume"],
        ]
        for args in cases:
            with self.subTest(args=args):
                with self.assertRaises(SystemExit):
                    core._parse_release_flags(args, "minor")

    ## @brief Verify creation handlers dispatch resume without running creation.
    # @details Mock both flow boundaries; O(1) dispatch for each supported level;
    #          develop-scoped recovery forwards dev_release=True (REQ-200).
    # @param self {ReleaseResumeTest} Isolated test instance.
    # @return {None} Assert REQ-176 recovery path and help visibility.
    def test_resume_cli_dispatch(self):
        for level in ("patch", "minor", "major"):
            with self.subTest(level=level):
                with mock.patch.object(core, "_resume_release_flow") as resume, mock.patch.object(
                    core, "_execute_release_flow"
                ) as create:
                    core.COMMANDS[level](["--resume"])
                    self.assertEqual(resume.call_args, mock.call(level, dev_release=False))
                    create.assert_not_called()
                    resume.reset_mock()
                    core.COMMANDS[level](["--dev", "--resume"])
                    self.assertEqual(resume.call_args, mock.call(level, dev_release=True))
                    create.assert_not_called()
                self.assertIn("--resume", core.HELP_TEXTS[level])
                self.assertIn("--dev", core.HELP_TEXTS[level])

    ## @brief Verify missing publication operations are selected independently.
    # @details Exercise preliminary failure, final failure, lost acknowledgement,
    #          tag-only recovery, and branch-only recovery; observable mocks reset per
    #          SubTest iteration; no real Git commands.
    # @param self {ReleaseResumeTest} Isolated test instance.
    # @return {None} Assert REQ-178 and REQ-179 idempotence.
    def test_resume_only_missing_operations(self):
        cases = [
            ("old refs/heads/develop\nold refs/heads/master", [
                mock.call("minor", "1.3.0", "develop"),
                mock.call("minor", "1.3.0", "master", include_branch=True, include_tag=True,
                          dev_release=False),
            ]),
            ("commit refs/heads/develop\nold refs/heads/master", [
                mock.call("minor", "1.3.0", "master", include_branch=True, include_tag=True,
                          dev_release=False),
            ]),
            ("commit refs/heads/develop\ncommit refs/heads/master", [
                mock.call("minor", "1.3.0", "master", include_branch=False, include_tag=True,
                          dev_release=False),
            ]),
            ("commit refs/heads/develop\ncommit refs/heads/master\n"
             "tag-object refs/tags/v1.3.0\ncommit refs/tags/v1.3.0^{}", []),
            ("commit refs/heads/develop\nold refs/heads/master\n"
             "tag-object refs/tags/v1.3.0\ncommit refs/tags/v1.3.0^{}", [
                mock.call("minor", "1.3.0", "master", include_branch=True, include_tag=False,
                          dev_release=False),
            ]),
        ]
        for remote, expected_output in cases:
            with self.subTest(remote=remote):
                self.push_mock.reset_mock()
                self.checkout_mock.reset_mock()
                self.responses["remote"] = remote
                core._resume_release_flow("minor")
                self.assertEqual(self.push_mock.call_args_list, expected_output)
                self.checkout_mock.assert_called_once_with(["work"])

    ## @brief Resume major and patch publication using existing tag objects.
    # @details Adapt synthetic semver; default patch publishes master like
    #          major/minor (REQ-072); develop-scoped patch never inspects or
    #          publishes master (REQ-045); observable mocks reset per SubTest.
    # @param self {ReleaseResumeTest} Isolated test instance.
    # @return {None} Assert REQ-045, REQ-072, REQ-177, and REQ-179.
    def test_resume_major_and_patch(self):
        def prepare(version):
            self.push_mock.reset_mock()
            self.git_mock.reset_mock()
            for key in list(self.responses):
                if isinstance(key, tuple) and any("v1.3.0" in arg for arg in key):
                    replaced = tuple(arg.replace("v1.3.0", f"v{version}") for arg in key)
                    self.responses[replaced] = self.responses[key]
            self.responses[("show", "-s", "--format=%s", "commit")] = (
                f"release: Release version {version}"
            )
            self.version_mock.return_value = version

        cases = [("major", "2.0.0"), ("patch", "1.2.4")]
        for level, version in cases:
            with self.subTest(level=level):
                prepare(version)
                self.branch_mock.return_value = "develop"
                core._resume_release_flow(level)
                expected_output = [
                    mock.call(level, version, "develop"),
                    mock.call(
                        level, version, "master",
                        include_branch=True, include_tag=True, dev_release=False,
                    ),
                ]
                self.assertEqual(self.push_mock.call_args_list, expected_output)
        with self.subTest(level="patch", dev_release=True):
            prepare("1.2.4")
            self.branch_mock.return_value = "develop"
            core._resume_release_flow("patch", dev_release=True)
            self.assertEqual(self.push_mock.call_args_list, [mock.call(
                "patch", "1.2.4", "develop",
                include_branch=True, include_tag=True, dev_release=True,
            )])
            git_calls = self.git_mock.call_args_list
            self.assertTrue(all("master" not in str(call) for call in git_calls))

    ## @brief Validate local release state before publication.
    # @details Inject one dirty, moved, unannotated, mismatched, or ambiguous input.
    # @param self {ReleaseResumeTest} Isolated test instance.
    # @return {None} Assert REQ-177 rejects before push or checkout.
    def test_resume_rejects_invalid_local_state(self):
        cases = [
            (("status", "--porcelain"), " M version"),
            (("status", "--porcelain"), "M  version"),
            (("status", "--porcelain"), "?? unrelated"),
            (("show", "-s", "--format=%s", "commit"), "fix: unrelated"),
            (("rev-parse", "--verify", "refs/heads/develop^{commit}"), "moved"),
            (("rev-parse", "--verify", "refs/heads/master^{commit}"), "moved"),
            (("cat-file", "-t", "tag-object"), "commit"),
            (("rev-parse", "--verify", "refs/tags/v1.3.0^{commit}"), "wrong-commit"),
            (("remote", "get-url", "--push", "--all", "origin"), "/one\n/two"),
        ]
        for key, value in cases:
            with self.subTest(key=key):
                self.push_mock.reset_mock()
                self.checkout_mock.reset_mock()
                self.responses[key] = value
                with self.assertRaises(core.ReleaseError):
                    core._resume_release_flow("minor")
                self.push_mock.assert_not_called()
                self.checkout_mock.assert_not_called()

    ## @brief Reject unsafe remote snapshots before any publication.
    # @details Validate missing branches, conflicting tag objects, and peeled targets.
    # @param self {ReleaseResumeTest} Isolated test instance.
    # @return {None} Assert REQ-178 fail-closed publication.
    def test_resume_rejects_remote_conflicts(self):
        cases = [
            "", "old refs/heads/develop",
            "old refs/heads/develop\nold refs/heads/master\nother refs/tags/v1.3.0",
            "old refs/heads/develop\nold refs/heads/master\ntag-object refs/tags/v1.3.0",
            "old refs/heads/develop\nold refs/heads/master\n"
            "tag-object refs/tags/v1.3.0\nwrong refs/tags/v1.3.0^{}",
        ]
        for remote in cases:
            with self.subTest(remote=remote):
                self.push_mock.reset_mock()
                self.responses["remote"] = remote
                with self.assertRaises(core.ReleaseError):
                    core._resume_release_flow("minor")
                self.push_mock.assert_not_called()

    ## @brief Reject divergent remote history, version drift, and unrelated checkout.
    # @details Mock each validation boundary independently; no mutation expected.
    # @param self {ReleaseResumeTest} Isolated test instance.
    # @return {None} Assert REQ-177 and REQ-178 rejection.
    def test_resume_rejects_drift(self):
        cases = [("ancestor", False), ("version", "9.0.0"), ("branch", "unrelated")]
        mocks = {"ancestor": self.ancestor_mock, "version": self.version_mock,
                 "branch": self.branch_mock}
        for dependency, value in cases:
            with self.subTest(dependency=dependency):
                self.push_mock.reset_mock()
                mocks[dependency].return_value = value
                with self.assertRaises(core.ReleaseError):
                    core._resume_release_flow("minor")
                self.push_mock.assert_not_called()

    ## @brief Reject a recovery level incompatible with the prepared semver.
    # @details A prepared minor cannot be resumed as major or patch.
    # @param self {ReleaseResumeTest} Isolated test instance.
    # @return {None} Assert REQ-177 level validation.
    def test_resume_rejects_wrong_level(self):
        self.branch_mock.return_value = "work"
        for level in ("major", "patch"):
            with self.subTest(level=level):
                self.push_mock.reset_mock()
                with self.assertRaises(core.ReleaseError):
                    core._resume_release_flow(level)
                self.push_mock.assert_not_called()

    ## @brief Verify publication diagnostics and bounded attempts for every rejection.
    # @details Execute the real helper with mocked Git failures through the inherited-
    #          stdio wrapper; transient errors also remain single-attempt, and Git's
    #          own rejection reaches the user terminal live while REQ-180 fields
    #          (version, refs, resume command) are preserved in the ReleaseError.
    # @param self {ReleaseResumeTest} Isolated test instance.
    # @return {None} Assert REQ-180 and REQ-181 recovery instructions and no retries.
    def test_push_failure_preserves_diagnostic_without_retry(self):
        cases = [
            "protected branch hook declined", "non-fast-forward", "connection timed out",
            "remote does not support --atomic push", "tag already exists",
        ]
        for message in cases:
            with self.subTest(message=message):
                failure = core.CommandExecutionError(
                    subprocess.CalledProcessError(
                        128, ["git", "push", "origin"], stderr=message.encode()
                    )
                )
                with mock.patch.object(core, "run_git_cmd", side_effect=failure) as git:
                    with self.assertRaises(core.ReleaseError) as error:
                        self.push_impl("minor", "1.3.0", "master", include_tag=True)
                git.assert_called_once()
                details = str(error.exception)
                for expected_output in ("Push failed", "1.3.0", "refs/heads/master",
                                        "refs/tags/v1.3.0", "g minor --resume"):
                    self.assertIn(expected_output, details)

    ## @brief Verify develop-scoped publication diagnostics.
    # @details Execute the real helper with a mocked Git rejection; the REQ-180
    #          recovery command must include --dev for develop-scoped releases.
    # @param self {ReleaseResumeTest} Isolated test instance.
    # @return {None} Assert REQ-180 scope-aware recovery guidance.
    def test_push_failure_dev_scope_reports_dev_resume(self):
        failure = core.CommandExecutionError(
            subprocess.CalledProcessError(
                128, ["git", "push", "origin"], stderr=b"protected branch hook declined"
            )
        )
        with mock.patch.object(core, "run_git_cmd", side_effect=failure):
            with self.assertRaises(core.ReleaseError) as error:
                self.push_impl(
                    "patch", "1.2.4", "develop", include_tag=True, dev_release=True
                )
        details = str(error.exception)
        self.assertIn("g patch --dev --resume", details)
        self.assertIn("work/develop tips", details)

    ## @brief Verify empty and tag-only publication selections.
    # @details Execute the real helper against a mocked Git boundary through the
    #          inherited-stdio wrapper; no implicit branch or unrelated tag publication.
    # @param self {ReleaseResumeTest} Isolated test instance.
    # @return {None} Assert REQ-179 exact missing-reference selection.
    def test_push_empty_and_tag_only(self):
        with mock.patch.object(core, "run_git_cmd") as git:
            self.push_impl("patch", "1.2.4", "develop", False, False)
            git.assert_not_called()
            self.push_impl("patch", "1.2.4", "develop", False, True)
            expected_output = ["push", "--no-follow-tags", "--atomic", "origin",
                               "refs/tags/v1.2.4:refs/tags/v1.2.4"]
            git.assert_called_once_with(expected_output)

    ## @brief Convert inspection failures to CLI errors without raw tracebacks.
    # @details Mock failed remote inspection; no release recreation.
    # @param self {ReleaseResumeTest} Isolated test instance.
    # @return {None} Assert nonzero recovery exit under DES-002.
    def test_resume_query_failure_exits(self):
        with mock.patch.object(core, "_resume_release_flow", side_effect=RuntimeError("offline")):
            with self.assertRaises(SystemExit) as error:
                core.cmd_minor(["--resume"])
        self.assertEqual(error.exception.code, 1)


if __name__ == "__main__":
    unittest.main()
