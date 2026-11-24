import contextlib
import io
import subprocess
import unittest
from contextlib import contextmanager
from pathlib import Path
from unittest import mock

from git_alias import core


RESOLVED_HASH = "0123456789abcdef0123456789abcdef01234567"
HEAD_HASH = "fedcba9876543210fedcba9876543210fedcba98"
VERSION_RULES = [("pyproject.toml", r"version")]


class CmdRollbackTest(unittest.TestCase):
    def setUp(self):
        core.CONFIG.update(core.DEFAULT_CONFIG)

    @contextmanager
    def _patch_target_pipeline(self):
        with (
            mock.patch.object(core, "_git_status_lines", return_value=[]),
            mock.patch.object(core, "_tag_exists", return_value=True),
            mock.patch.object(
                core, "_resolve_rollback_target_commit", return_value=RESOLVED_HASH
            ),
            mock.patch.object(core, "_is_commit_ancestor", return_value=True),
            mock.patch.object(core, "run_git_text", return_value=HEAD_HASH),
        ):
            yield

    def test_help_argument_prints_help(self):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            core.cmd_rollback(["--help"])
        self.assertIn("rollback -", out.getvalue())

    def test_rejects_missing_target_argument(self):
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            with self.assertRaises(SystemExit) as ctx:
                core.cmd_rollback([])
        self.assertEqual(ctx.exception.code, 1)
        self.assertIn("requires exactly one target", err.getvalue())

    def test_fails_when_working_tree_is_not_clean(self):
        with mock.patch.object(core, "_git_status_lines", return_value=[" M file.txt"]):
            err = io.StringIO()
            with contextlib.redirect_stderr(err):
                with self.assertRaises(SystemExit) as ctx:
                    core.cmd_rollback(["abc123"])
        self.assertEqual(ctx.exception.code, 1)
        self.assertIn("working tree is not clean", err.getvalue())

    def test_fails_when_staging_area_is_not_empty(self):
        with mock.patch.object(core, "_git_status_lines", return_value=["M  file.txt"]):
            err = io.StringIO()
            with contextlib.redirect_stderr(err):
                with self.assertRaises(SystemExit) as ctx:
                    core.cmd_rollback(["abc123"])
        self.assertEqual(ctx.exception.code, 1)
        self.assertIn("staging area is not empty", err.getvalue())

    def test_fails_when_target_is_not_resolvable(self):
        with (
            mock.patch.object(core, "_git_status_lines", return_value=[]),
            mock.patch.object(core, "_tag_exists", return_value=True),
            mock.patch.object(
                core, "run_git_text", side_effect=RuntimeError("invalid target")
            ),
        ):
            err = io.StringIO()
            with contextlib.redirect_stderr(err):
                with self.assertRaises(SystemExit) as ctx:
                    core.cmd_rollback(["missing-tag"])
        self.assertEqual(ctx.exception.code, 1)
        self.assertIn("not a valid commit hash or tag", err.getvalue())

    def test_fails_when_target_is_neither_hash_nor_existing_tag(self):
        with mock.patch.object(core, "_tag_exists", return_value=False):
            err = io.StringIO()
            with contextlib.redirect_stderr(err):
                with self.assertRaises(SystemExit) as ctx:
                    core.cmd_rollback(["not-a-hash"])
        self.assertEqual(ctx.exception.code, 1)
        self.assertIn("must be an existing tag or a commit hash", err.getvalue())

    def test_fails_when_target_is_not_in_current_branch(self):
        with (
            mock.patch.object(core, "_git_status_lines", return_value=[]),
            mock.patch.object(core, "_tag_exists", return_value=True),
            mock.patch.object(core, "run_git_text", return_value=RESOLVED_HASH),
            mock.patch.object(core, "_is_commit_ancestor", return_value=False),
        ):
            err = io.StringIO()
            with contextlib.redirect_stderr(err):
                with self.assertRaises(SystemExit) as ctx:
                    core.cmd_rollback(["v1.2.3"])
        self.assertEqual(ctx.exception.code, 1)
        self.assertIn("not reachable from the current branch HEAD", err.getvalue())

    def test_fails_when_target_matches_head(self):
        with (
            mock.patch.object(core, "_git_status_lines", return_value=[]),
            mock.patch.object(core, "_tag_exists", return_value=True),
            mock.patch.object(
                core, "_resolve_rollback_target_commit", return_value=RESOLVED_HASH
            ),
            mock.patch.object(core, "_is_commit_ancestor", return_value=True),
            mock.patch.object(core, "run_git_text", return_value=RESOLVED_HASH),
        ):
            err = io.StringIO()
            with contextlib.redirect_stderr(err):
                with self.assertRaises(SystemExit) as ctx:
                    core.cmd_rollback(["v1.2.3"])
        self.assertEqual(ctx.exception.code, 1)
        self.assertIn("target matches HEAD", err.getvalue())

    def test_continues_without_version_restore_when_rules_are_missing(self):
        manager = mock.Mock()
        with (
            self._patch_target_pipeline(),
            mock.patch.object(core, "get_version_rules", return_value=[]),
            mock.patch.object(core, "cmd_chver", new=manager.chver),
            mock.patch.object(core, "run_git_cmd", new=manager.run_git),
            mock.patch.object(core, "_execute_commit", new=manager.execute_commit),
        ):
            err = io.StringIO()
            with contextlib.redirect_stderr(err):
                core.cmd_rollback(["v1.2.3"])
        self.assertIn("Version check failed", err.getvalue())
        self.assertIn("without version restoration", err.getvalue())
        expected_calls = [
            mock.call.run_git(["revert", "--no-commit", f"{RESOLVED_HASH}..HEAD"]),
            mock.call.execute_commit(
                f"revert: Roll back branch to v1.2.3 ({RESOLVED_HASH}).",
                "rollback",
                allow_amend=False,
            ),
        ]
        self.assertEqual(manager.mock_calls, expected_calls)

    def test_continues_without_version_restore_when_detection_fails(self):
        manager = mock.Mock()
        with (
            self._patch_target_pipeline(),
            mock.patch.object(core, "get_version_rules", return_value=VERSION_RULES),
            mock.patch.object(
                core, "get_git_root", return_value=Path("/tmp/fake-repo")
            ),
            mock.patch.object(
                core,
                "_determine_canonical_version",
                side_effect=core.VersionDetectionError("no version found"),
            ),
            mock.patch.object(core, "cmd_chver", new=manager.chver),
            mock.patch.object(core, "run_git_cmd", new=manager.run_git),
            mock.patch.object(core, "_execute_commit", new=manager.execute_commit),
        ):
            err = io.StringIO()
            with contextlib.redirect_stderr(err):
                core.cmd_rollback(["v1.2.3"])
        self.assertIn("no version found", err.getvalue())
        self.assertIn("without version restoration", err.getvalue())
        expected_calls = [
            mock.call.run_git(["revert", "--no-commit", f"{RESOLVED_HASH}..HEAD"]),
            mock.call.execute_commit(
                f"revert: Roll back branch to v1.2.3 ({RESOLVED_HASH}).",
                "rollback",
                allow_amend=False,
            ),
        ]
        self.assertEqual(manager.mock_calls, expected_calls)

    def test_executes_revert_restores_version_and_creates_non_amend_commit(self):
        manager = mock.Mock()
        with (
            self._patch_target_pipeline(),
            mock.patch.object(core, "get_version_rules", return_value=VERSION_RULES),
            mock.patch.object(
                core, "get_git_root", return_value=Path("/tmp/fake-repo")
            ),
            mock.patch.object(
                core, "_determine_canonical_version", return_value="1.2.3"
            ),
            mock.patch.object(core, "cmd_chver", new=manager.chver),
            mock.patch.object(core, "run_git_cmd", new=manager.run_git),
            mock.patch.object(core, "_execute_commit", new=manager.execute_commit),
        ):
            core.cmd_rollback(["v1.2.3"])
        expected_calls = [
            mock.call.run_git(["revert", "--no-commit", f"{RESOLVED_HASH}..HEAD"]),
            mock.call.chver(["1.2.3"]),
            mock.call.run_git(["add", "--all"]),
            mock.call.execute_commit(
                f"revert: Roll back branch to v1.2.3 ({RESOLVED_HASH}).",
                "rollback",
                allow_amend=False,
            ),
        ]
        self.assertEqual(manager.mock_calls, expected_calls)

    def test_aborts_and_discards_revert_when_version_restore_fails(self):
        with (
            self._patch_target_pipeline(),
            mock.patch.object(core, "get_version_rules", return_value=VERSION_RULES),
            mock.patch.object(
                core, "get_git_root", return_value=Path("/tmp/fake-repo")
            ),
            mock.patch.object(
                core, "_determine_canonical_version", return_value="1.2.3"
            ),
            mock.patch.object(core, "cmd_chver", side_effect=SystemExit(1)),
            mock.patch.object(core, "run_git_cmd", return_value=None) as run_git,
            mock.patch.object(
                core, "_execute_commit", return_value=None
            ) as execute_commit,
            mock.patch.object(
                core.subprocess, "run", return_value=None
            ) as subprocess_run,
        ):
            err = io.StringIO()
            with contextlib.redirect_stderr(err):
                with self.assertRaises(SystemExit) as ctx:
                    core.cmd_rollback(["v1.2.3"])
        self.assertEqual(ctx.exception.code, 1)
        self.assertIn("version restore failed", err.getvalue())
        run_git.assert_called_once_with(
            ["revert", "--no-commit", f"{RESOLVED_HASH}..HEAD"]
        )
        subprocess_run.assert_called_once_with(
            ["git", "revert", "--abort"],
            check=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        execute_commit.assert_not_called()

    def test_aborts_when_staging_fails_after_version_restore(self):
        failed_add = subprocess.CalledProcessError(
            1, ["git", "add", "--all"], stderr=b"fatal: unable to stage"
        )
        with (
            self._patch_target_pipeline(),
            mock.patch.object(core, "get_version_rules", return_value=VERSION_RULES),
            mock.patch.object(
                core, "get_git_root", return_value=Path("/tmp/fake-repo")
            ),
            mock.patch.object(
                core, "_determine_canonical_version", return_value="1.2.3"
            ),
            mock.patch.object(core, "cmd_chver", return_value=None),
            mock.patch.object(
                core,
                "run_git_cmd",
                side_effect=[None, core.CommandExecutionError(failed_add)],
            ),
            mock.patch.object(
                core, "_execute_commit", return_value=None
            ) as execute_commit,
            mock.patch.object(
                core.subprocess, "run", return_value=None
            ) as subprocess_run,
        ):
            err = io.StringIO()
            with contextlib.redirect_stderr(err):
                with self.assertRaises(SystemExit) as ctx:
                    core.cmd_rollback(["v1.2.3"])
        self.assertEqual(ctx.exception.code, 1)
        self.assertIn("version restore failed", err.getvalue())
        self.assertIn("fatal: unable to stage", err.getvalue())
        subprocess_run.assert_called_once()
        execute_commit.assert_not_called()


if __name__ == "__main__":
    unittest.main()
