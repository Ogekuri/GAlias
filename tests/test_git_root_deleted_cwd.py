"""Regression tests for repository-root resolution from a deleted working directory.

HDT static analysis:
- UUTs: `core.get_git_root` (Level 1: depends on `_run_checked` + `Path.cwd`),
  `core.main` (composed CLI entrypoint).
- External dependencies isolated: OS working-directory state (temporary directory,
  deleted in-test, restored in `finally`); PyPI update check stubbed to guarantee
  no network I/O.
- Scenario matrix: error case only (unreadable/deleted CWD) for both UUTs;
  expected outcome is a `SystemExit(1)` with an explicit English stderr
  diagnostic (DES-002), never an escaping `FileNotFoundError` traceback.
"""
import contextlib
import io
import os
import shutil
import tempfile
import unittest
from unittest import mock

from git_alias import core


class GetGitRootDeletedCwdTest(unittest.TestCase):
    """@brief Regression guard for explicit errors when the OS CWD no longer exists.

    @details Reproduces the reported defect: running any command (e.g. `dcc`)
    from a directory deleted after `cd` crashed with an escaping
    `FileNotFoundError` from `Path.cwd()` instead of an explicit English
    error with non-zero exit (DES-002, PRJ-001).
    """

    def setUp(self):
        core.CONFIG.update(core.DEFAULT_CONFIG)

    def _chdir_into_deleted_directory(self, prefix):
        """@brief Change the process CWD into a temporary directory then delete it.

        @param prefix {str} Unique `tempfile.mkdtemp` prefix for diagnostics.
        @return {tuple[str, str]} Deleted directory path and the previous CWD
        that the caller MUST restore in its `finally` block.
        """
        deleted_dir = tempfile.mkdtemp(prefix=prefix)
        previous_cwd = os.getcwd()
        os.chdir(deleted_dir)
        shutil.rmtree(deleted_dir)
        return deleted_dir, previous_cwd

    def test_get_git_root_exits_with_explicit_error_when_cwd_is_deleted(self):
        """@brief `get_git_root` exits 1 with an English error on unreadable CWD.

        @details Expected: `SystemExit` code 1; forbidden: any escaping
        `OSError` (regression evidence: raw `FileNotFoundError` traceback).
        """
        deleted_dir, previous_cwd = self._chdir_into_deleted_directory(
            "galias-deleted-cwd-root-"
        )
        stderr = io.StringIO()
        try:
            with contextlib.redirect_stderr(stderr):
                with self.assertRaises(SystemExit) as exit_context:
                    core.get_git_root()
            self.assertEqual(exit_context.exception.code, 1)
            self.assertIn(
                "Unable to read the current working directory", stderr.getvalue()
            )
        finally:
            os.chdir(previous_cwd)
            shutil.rmtree(deleted_dir, ignore_errors=True)

    def test_main_dcc_exits_with_explicit_error_without_traceback(self):
        """@brief `main(["dcc"])` reports the deleted-CWD defect explicitly.

        @details Mirrors the user-reported invocation: the composed entrypoint
        MUST terminate via `SystemExit(1)` with an English stderr diagnostic,
        MUST NOT escape a `FileNotFoundError`, and MUST exit before any
        update-check network activity (stubbed and asserted not called).
        """
        deleted_dir, previous_cwd = self._chdir_into_deleted_directory(
            "galias-deleted-cwd-main-"
        )
        stderr = io.StringIO()
        try:
            with mock.patch.object(core, "check_for_newer_version") as check:
                with contextlib.redirect_stderr(stderr):
                    with self.assertRaises(SystemExit) as exit_context:
                        core.main(["dcc"])
                check.assert_not_called()
            self.assertEqual(exit_context.exception.code, 1)
            self.assertIn(
                "Unable to read the current working directory", stderr.getvalue()
            )
        finally:
            os.chdir(previous_cwd)
            shutil.rmtree(deleted_dir, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
