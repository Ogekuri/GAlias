import contextlib
import io
import subprocess
import unittest
from pathlib import Path
from unittest import mock

from git_alias import core


class ReleaseFlowTest(unittest.TestCase):
    def setUp(self):
        core.CONFIG.update(core.DEFAULT_CONFIG)

    ## @brief Verify default patch publication selects the unified master flow.
    # @details Record orchestration only; Git operations remain mocked.
    # @param self {ReleaseFlowTest} Isolated test instance.
    # @return {None} Assert REQ-072 publication steps.
    def test_patch_release_pushes_master_with_release_tag(self):
        steps = []

        def record_step(level, step_name, action):
            steps.append(step_name)

        with mock.patch.object(
            core,
            "_ensure_release_prerequisites",
            return_value={"master": "master", "develop": "develop", "work": "work"},
        ), mock.patch.object(core, "get_version_rules", return_value=[("README.md", "x")]), mock.patch.object(
            core, "_determine_canonical_version", return_value="1.2.3"
        ), mock.patch.object(core, "_bump_semver_version", return_value="1.2.4"), mock.patch.object(
            core, "_run_release_step", side_effect=record_step
        ):
            core._execute_release_flow("patch")

        self.assertTrue(steps)
        self.assertIn("checkout master", steps)
        self.assertIn("merge develop into master", steps)
        self.assertIn("tag release on master", steps)
        self.assertIn("push develop branch", steps)
        self.assertIn("push master with release tag atomically", steps)
        self.assertNotIn("push develop with release tag atomically", steps)

    ## @brief Verify develop-scoped publication selects the atomic develop/tag step.
    # @details Record orchestration only; Git operations remain mocked.
    # @param self {ReleaseFlowTest} Isolated test instance.
    # @return {None} Assert REQ-045 publication step.
    def test_dev_release_pushes_develop_with_release_tag(self):
        steps = []

        def record_step(level, step_name, action):
            steps.append(step_name)

        with mock.patch.object(
            core,
            "_ensure_release_prerequisites",
            return_value={"master": "master", "develop": "develop", "work": "work"},
        ), mock.patch.object(core, "get_version_rules", return_value=[("README.md", "x")]), mock.patch.object(
            core, "_determine_canonical_version", return_value="1.2.3"
        ), mock.patch.object(core, "_bump_semver_version", return_value="1.2.4"), mock.patch.object(
            core, "_run_release_step", side_effect=record_step
        ):
            core._execute_release_flow("patch", dev_release=True)

        self.assertTrue(steps)
        self.assertIn("push develop with release tag atomically", steps)
        self.assertNotIn("push develop branch", steps)
        self.assertNotIn("push master with release tag atomically", steps)

    def test_release_step_formats_output_with_level(self):
        buffer = io.StringIO()
        with contextlib.redirect_stdout(buffer):
            core._run_release_step("major", "stage files", lambda: None)
        self.assertEqual(
            buffer.getvalue().strip(),
            "--- [release:major] Step 'stage files' completed successfully. ---",
        )

    def test_release_flow_emits_blank_line_before_steps(self):
        with mock.patch.object(
            core,
            "_ensure_release_prerequisites",
            return_value={"master": "master", "develop": "develop", "work": "work"},
        ), mock.patch.object(core, "get_version_rules", return_value=[("README.md", "x")]), mock.patch.object(
            core, "_determine_canonical_version", return_value="1.2.3"
        ), mock.patch.object(core, "_bump_semver_version", return_value="1.2.4"), mock.patch.object(
            core, "_run_release_step", return_value=None
        ):
            buffer = io.StringIO()
            with contextlib.redirect_stdout(buffer):
                core._execute_release_flow("minor")
        self.assertTrue(buffer.getvalue().startswith("\n"))

    def test_patch_release_auto_includes_patch_flag(self):
        # patch level must automatically add --include-patch to changelog flags
        def run_step(_level, step_name, action):
            if step_name == "regenerate changelog":
                action()
            return None

        with mock.patch.object(
            core,
            "_ensure_release_prerequisites",
            return_value={"master": "master", "develop": "develop", "work": "work"},
        ), mock.patch.object(core, "get_version_rules", return_value=[("README.md", "x")]), mock.patch.object(
            core, "_determine_canonical_version", return_value="1.2.3"
        ), mock.patch.object(core, "_bump_semver_version", return_value="1.2.4"), mock.patch.object(
            core, "_run_release_step", side_effect=run_step
        ), mock.patch.object(core, "cmd_changelog") as changelog:
            core._execute_release_flow("patch")
        changelog.assert_called_once_with(["--force-write", "--include-patch"])

    def test_release_flow_passes_explicit_include_patch_flag(self):
        # user-supplied --include-patch is forwarded without duplication
        def run_step(_level, step_name, action):
            if step_name == "regenerate changelog":
                action()
            return None

        with mock.patch.object(
            core,
            "_ensure_release_prerequisites",
            return_value={"master": "master", "develop": "develop", "work": "work"},
        ), mock.patch.object(core, "get_version_rules", return_value=[("README.md", "x")]), mock.patch.object(
            core, "_determine_canonical_version", return_value="1.2.3"
        ), mock.patch.object(core, "_bump_semver_version", return_value="1.2.4"), mock.patch.object(
            core, "_run_release_step", side_effect=run_step
        ), mock.patch.object(core, "cmd_changelog") as changelog:
            core._execute_release_flow("patch", changelog_args=["--include-patch"])
        changelog.assert_called_once_with(["--force-write", "--include-patch"])

    def test_minor_release_does_not_auto_include_patch_flag(self):
        # minor level must NOT automatically add --include-patch
        def run_step(_level, step_name, action):
            if step_name == "regenerate changelog":
                action()
            return None

        with mock.patch.object(
            core,
            "_ensure_release_prerequisites",
            return_value={"master": "master", "develop": "develop", "work": "work"},
        ), mock.patch.object(core, "get_version_rules", return_value=[("README.md", "x")]), mock.patch.object(
            core, "_determine_canonical_version", return_value="1.2.0"
        ), mock.patch.object(core, "_bump_semver_version", return_value="1.3.0"), mock.patch.object(
            core, "_run_release_step", side_effect=run_step
        ), mock.patch.object(core, "cmd_changelog") as changelog:
            core._execute_release_flow("minor")
        changelog.assert_called_once_with(["--force-write"])

    def test_release_commands_accept_include_patch_flag(self):
        with mock.patch.object(core, "_run_release_command") as run_release:
            core.cmd_patch(["--include-patch"])
        run_release.assert_called_once_with(
            "patch", changelog_args=["--include-patch"], dev_release=False
        )

    ## @brief Verify develop-scope flag parsing and dispatch on every level.
    # @details Equivalent --dev/--develop flags select dev_release=True and are
    #          never forwarded to the changelog step (REQ-200).
    # @param self {ReleaseFlowTest} Isolated test instance.
    # @return {None} Assert REQ-200 flag dispatch.
    def test_release_commands_accept_dev_flags(self):
        with mock.patch.object(core, "_run_release_command") as run_release:
            core.cmd_minor(["--dev", "--include-patch"])
        run_release.assert_called_once_with(
            "minor", changelog_args=["--include-patch"], dev_release=True
        )
        with mock.patch.object(core, "_run_release_command") as run_release:
            core.cmd_major(["--develop"])
        run_release.assert_called_once_with(
            "major", changelog_args=[], dev_release=True
        )

    def test_release_commands_reject_unknown_flags(self):
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            with self.assertRaises(SystemExit):
                core.cmd_patch(["--unexpected"])
        self.assertIn("accepts only --include-patch", err.getvalue())

    def test_dev_release_skips_master_steps(self):
        # develop-scoped releases MUST NOT execute checkout master / merge develop into master / tag/push master
        steps = []

        def record_step(level, step_name, action):
            steps.append(step_name)

        with mock.patch.object(
            core,
            "_ensure_release_prerequisites",
            return_value={"master": "master", "develop": "develop", "work": "work"},
        ), mock.patch.object(core, "get_version_rules", return_value=[("README.md", "x")]), mock.patch.object(
            core, "_determine_canonical_version", return_value="1.2.3"
        ), mock.patch.object(core, "_bump_semver_version", return_value="1.2.4"), mock.patch.object(
            core, "_run_release_step", side_effect=record_step
        ):
            core._execute_release_flow("patch", dev_release=True)

        self.assertNotIn("checkout master", steps)
        self.assertNotIn("merge develop into master", steps)
        self.assertNotIn("tag release on master", steps)
        self.assertNotIn("push master with release tag atomically", steps)

    def test_major_release_includes_master_steps(self):
        # major level MUST execute checkout master / merge develop into master / tag/push master
        steps = []

        def record_step(level, step_name, action):
            steps.append(step_name)

        with mock.patch.object(
            core,
            "_ensure_release_prerequisites",
            return_value={"master": "master", "develop": "develop", "work": "work"},
        ), mock.patch.object(core, "get_version_rules", return_value=[("README.md", "x")]), mock.patch.object(
            core, "_determine_canonical_version", return_value="1.2.0"
        ), mock.patch.object(core, "_bump_semver_version", return_value="2.0.0"), mock.patch.object(
            core, "_run_release_step", side_effect=record_step
        ):
            core._execute_release_flow("major")

        self.assertIn("checkout master", steps)
        self.assertIn("merge develop into master", steps)
        self.assertIn("tag release on master", steps)
        self.assertIn("push master with release tag atomically", steps)
        self.assertLess(steps.index("tag release on master"), steps.index("push develop branch"))

    def test_minor_release_includes_master_steps(self):
        # minor level MUST execute checkout master / merge develop into master / tag/push master
        steps = []

        def record_step(level, step_name, action):
            steps.append(step_name)

        with mock.patch.object(
            core,
            "_ensure_release_prerequisites",
            return_value={"master": "master", "develop": "develop", "work": "work"},
        ), mock.patch.object(core, "get_version_rules", return_value=[("README.md", "x")]), mock.patch.object(
            core, "_determine_canonical_version", return_value="1.2.0"
        ), mock.patch.object(core, "_bump_semver_version", return_value="1.3.0"), mock.patch.object(
            core, "_run_release_step", side_effect=record_step
        ):
            core._execute_release_flow("minor")

        self.assertIn("checkout master", steps)
        self.assertIn("merge develop into master", steps)
        self.assertIn("tag release on master", steps)
        self.assertIn("push master with release tag atomically", steps)
        self.assertLess(steps.index("tag release on master"), steps.index("push develop branch"))

    def test_release_flow_uses_temporary_tag_for_changelog_then_deletes_it(self):
        steps = []

        def run_step(_level, step_name, action):
            steps.append(step_name)
            if step_name in {
                "create temporary changelog tag",
                "delete temporary changelog tag",
                "tag release on develop",
            }:
                action()
            return None

        with mock.patch.object(
            core,
            "_ensure_release_prerequisites",
            return_value={"master": "master", "develop": "develop", "work": "work"},
        ), mock.patch.object(core, "get_version_rules", return_value=[("README.md", "x")]), mock.patch.object(
            core, "_determine_canonical_version", return_value="1.2.3"
        ), mock.patch.object(core, "_bump_semver_version", return_value="1.2.4"), mock.patch.object(
            core, "_run_release_step", side_effect=run_step
        ), mock.patch.object(core, "cmd_tg") as cmd_tg, mock.patch.object(core, "run_git_cmd") as run_git:
            core._execute_release_flow("patch", dev_release=True)

        cmd_tg.assert_has_calls(
            [
                mock.call(["release: Release version 1.2.4", "v1.2.4"]),
                mock.call(["release: Release version 1.2.4", "v1.2.4"]),
            ]
        )
        run_git.assert_called_once_with(["tag", "--delete", "v1.2.4"])
        self.assertLess(steps.index("create temporary changelog tag"), steps.index("regenerate changelog"))
        self.assertLess(steps.index("regenerate changelog"), steps.index("delete temporary changelog tag"))

    ## @brief Verify exact unified patch publication argv via inherited stdio.
    # @details Isolate Git; assert ordered explicit refspecs for REQ-072 and
    #          delegation through the shared inherited-stdio wrapper
    #          (`run_git_cmd`) so push output and interactive SSH
    #          authentication reach the user terminal.
    # @param self {ReleaseFlowTest} Isolated test instance.
    # @return {None} Assert REQ-072 push contract.
    def test_patch_push_uses_exact_release_tag(self):
        def run_step(_level, step_name, action):
            if step_name in {"push develop branch", "push master with release tag atomically"}:
                action()
            return None

        with mock.patch.object(
            core,
            "_ensure_release_prerequisites",
            return_value={"master": "master", "develop": "develop", "work": "work"},
        ), mock.patch.object(core, "get_version_rules", return_value=[("README.md", "x")]), mock.patch.object(
            core, "_determine_canonical_version", return_value="1.2.3"
        ), mock.patch.object(core, "_bump_semver_version", return_value="1.2.4"), mock.patch.object(
            core, "_run_release_step", side_effect=run_step
        ), mock.patch.object(core, "run_git_cmd") as run_git:
            core._execute_release_flow("patch")
        expected_output = [
            mock.call(["push", "--no-follow-tags", "origin", "refs/heads/develop:refs/heads/develop"]),
            mock.call(["push", "--no-follow-tags", "--atomic", "origin",
                       "refs/heads/master:refs/heads/master", "refs/tags/v1.2.4:refs/tags/v1.2.4"]),
        ]
        self.assertEqual(run_git.call_args_list, expected_output)

    ## @brief Verify exact atomic develop-scoped publication argv via inherited stdio.
    # @details Isolate Git; assert explicit refspecs, disabled implicit tag
    #          following, and delegation through the shared inherited-stdio
    #          wrapper (`run_git_cmd`) so push output and interactive SSH
    #          authentication reach the user terminal.
    # @param self {ReleaseFlowTest} Isolated test instance.
    # @return {None} Assert REQ-045 push contract.
    def test_dev_patch_push_uses_exact_release_tag(self):
        def run_step(_level, step_name, action):
            if step_name == "push develop with release tag atomically":
                action()
            return None

        with mock.patch.object(
            core,
            "_ensure_release_prerequisites",
            return_value={"master": "master", "develop": "develop", "work": "work"},
        ), mock.patch.object(core, "get_version_rules", return_value=[("README.md", "x")]), mock.patch.object(
            core, "_determine_canonical_version", return_value="1.2.3"
        ), mock.patch.object(core, "_bump_semver_version", return_value="1.2.4"), mock.patch.object(
            core, "_run_release_step", side_effect=run_step
        ), mock.patch.object(core, "run_git_cmd") as run_git:
            core._execute_release_flow("patch", dev_release=True)
        expected_output = ["push", "--no-follow-tags", "--atomic", "origin",
                           "refs/heads/develop:refs/heads/develop", "refs/tags/v1.2.4:refs/tags/v1.2.4"]
        run_git.assert_called_once_with(expected_output)

    ## @brief Verify branch-only preliminary push and atomic final publication.
    # @details Isolate Git; assert ordered explicit refspecs for REQ-072 and
    #          delegation through the shared inherited-stdio wrapper
    #          (`run_git_cmd`) for both publication pushes.
    # @param self {ReleaseFlowTest} Isolated test instance.
    # @return {None} Assert publication argv without unrelated tags.
    def test_minor_pushes_develop_then_master_and_release_tag(self):
        def run_step(_level, step_name, action):
            if step_name in {"push develop branch", "push master with release tag atomically"}:
                action()
            return None

        with mock.patch.object(
            core,
            "_ensure_release_prerequisites",
            return_value={"master": "master", "develop": "develop", "work": "work"},
        ), mock.patch.object(core, "get_version_rules", return_value=[("README.md", "x")]), mock.patch.object(
            core, "_determine_canonical_version", return_value="1.2.0"
        ), mock.patch.object(core, "_bump_semver_version", return_value="1.3.0"), mock.patch.object(
            core, "_run_release_step", side_effect=run_step
        ), mock.patch.object(core, "run_git_cmd") as run_git:
            core._execute_release_flow("minor")
        expected_output = [
            mock.call(["push", "--no-follow-tags", "origin", "refs/heads/develop:refs/heads/develop"]),
            mock.call(["push", "--no-follow-tags", "--atomic", "origin",
                       "refs/heads/master:refs/heads/master", "refs/tags/v1.3.0:refs/tags/v1.3.0"]),
        ]
        self.assertEqual(run_git.call_args_list, expected_output)

    def test_create_release_commit_for_flow_uses_release_amend_strategy(self):
        with mock.patch.object(core, "_ensure_commit_ready"), mock.patch.object(core, "_execute_commit") as execute_commit:
            core._create_release_commit_for_flow("2.0.0")
        execute_commit.assert_called_once_with("release: Release version 2.0.0", "release")

    def test_release_flow_uses_internal_release_commit_builder(self):
        def run_step(_level, step_name, action):
            if step_name == "create release commit":
                action()
            return None

        with mock.patch.object(
            core,
            "_ensure_release_prerequisites",
            return_value={"master": "master", "develop": "develop", "work": "work"},
        ), mock.patch.object(core, "get_version_rules", return_value=[("README.md", "x")]), mock.patch.object(
            core, "_determine_canonical_version", return_value="1.2.3"
        ), mock.patch.object(core, "_bump_semver_version", return_value="1.2.4"), mock.patch.object(
            core, "_run_release_step", side_effect=run_step
        ), mock.patch.object(core, "_create_release_commit_for_flow") as create_release_commit:
            core._execute_release_flow("patch")

        create_release_commit.assert_called_once_with("1.2.4")

    ## @brief Verify the configuration-driven release script hooks and their ordering.
    # @details Empty keys MUST skip both steps; configured keys MUST tokenize the
    #          command line into argv and run from the repository root, with the
    #          readiness gate first and the build hook after the version update.
    # @param self {ReleaseFlowTest} Isolated test instance.
    # @return {None} Assert REQ-166, REQ-167, REQ-318, and REQ-319 ordering.
    def test_release_script_hooks_follow_configuration(self):
        cases = (
            ("", "", False),
            ("scripts/build.sh --fast", "scripts/pre-release-check.sh", True),
        )
        for build_script, pre_release_check, expected in cases:
            with self.subTest(build_script=build_script, pre_release_check=pre_release_check):
                steps = []
                executed = []

                def record_step(_level, step_name, action):
                    steps.append(step_name)
                    if step_name in ("run build script", "run pre-release check script"):
                        action()
                    return None

                def record_command(cmd, cwd=None):
                    executed.append((list(cmd), str(cwd)))
                    return None

                core.CONFIG["build_script"] = build_script
                core.CONFIG["pre_release_check"] = pre_release_check
                with mock.patch.object(
                    core,
                    "_ensure_release_prerequisites",
                    return_value={"master": "master", "develop": "develop", "work": "work"},
                ), mock.patch.object(core, "get_version_rules", return_value=[("README.md", "x")]), mock.patch.object(
                    core, "get_git_root", return_value=Path("/synthetic")
                ), mock.patch.object(
                    core, "_determine_canonical_version", return_value="1.2.3"
                ), mock.patch.object(core, "_bump_semver_version", return_value="1.2.4"), mock.patch.object(
                    core, "_run_release_step", side_effect=record_step
                ), mock.patch.object(core, "run_command", side_effect=record_command):
                    core._execute_release_flow("patch")

                self.assertEqual("run pre-release check script" in steps, expected)
                self.assertEqual("run build script" in steps, expected)
                if expected:
                    self.assertLess(
                        steps.index("run pre-release check script"),
                        steps.index("update versions"),
                    )
                    self.assertLess(
                        steps.index("update versions"), steps.index("run build script")
                    )
                    self.assertLess(
                        steps.index("run build script"), steps.index("stage files")
                    )
                    self.assertEqual(
                        executed,
                        [
                            (["scripts/pre-release-check.sh"], "/synthetic"),
                            (["scripts/build.sh", "--fast"], "/synthetic"),
                        ],
                    )
                else:
                    self.assertEqual(executed, [])

    ## @brief Verify a failing pre-release check aborts the release before the version update.
    # @details Uses the real step wrapper so the failure conversion is asserted;
    #          the version update and all Git mutations remain unmocked negations.
    # @param self {ReleaseFlowTest} Isolated test instance.
    # @return {None} Assert REQ-320 fail-fast semantics.
    def test_failing_pre_release_check_aborts_release(self):
        failure = subprocess.CalledProcessError(
            1, ["scripts/pre-release-check.sh"], stderr=b"readiness failed"
        )
        core.CONFIG["pre_release_check"] = "scripts/pre-release-check.sh"
        core.CONFIG["build_script"] = ""
        with mock.patch.object(
            core,
            "_ensure_release_prerequisites",
            return_value={"master": "master", "develop": "develop", "work": "work"},
        ), mock.patch.object(core, "get_version_rules", return_value=[("README.md", "x")]), mock.patch.object(
            core, "get_git_root", return_value=Path("/synthetic")
        ), mock.patch.object(
            core, "_determine_canonical_version", return_value="1.2.3"
        ), mock.patch.object(core, "_bump_semver_version", return_value="1.2.4"), mock.patch.object(
            core, "run_command", side_effect=core.CommandExecutionError(failure)
        ), mock.patch.object(core, "cmd_chver") as chver, mock.patch.object(
            core, "run_git_cmd"
        ) as run_git:
            with self.assertRaises(core.ReleaseError) as raised:
                core._execute_release_flow("patch")
        self.assertIn("run pre-release check script", str(raised.exception))
        self.assertIn("readiness failed", str(raised.exception))
        chver.assert_not_called()
        run_git.assert_not_called()
