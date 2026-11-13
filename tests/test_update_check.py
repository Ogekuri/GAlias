import contextlib
import io
import json
import tempfile
import unittest
from email.message import Message
from pathlib import Path
from uuid import uuid4
from unittest import mock
from urllib.error import HTTPError

from git_alias import core


class _FakeResponse:
    def __init__(self, payload: dict):
        self._payload = payload

    def read(self):
        return json.dumps(self._payload).encode("utf-8")

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


class _RawResponse:
    def __init__(self, payload_bytes: bytes):
        self._payload_bytes = payload_bytes

    def read(self):
        return self._payload_bytes

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


class UpdateCheckTest(unittest.TestCase):
    def _isolated_cache(self):
        return mock.patch.object(
            core,
            "VERSION_CHECK_CACHE_FILE",
            Path(tempfile.gettempdir())
            / f"{core.UV_TOOL_NAME}.cache.test.{uuid4().hex}"
            / "check_version_idle-time.json",
        )

    @staticmethod
    def _http_error(
        *,
        code: int,
        payload: dict,
        headers: dict | None = None,
    ) -> HTTPError:
        response_headers = Message()
        for key, value in (headers or {}).items():
            response_headers[key] = value
        return HTTPError(
            url=core.PYPI_LATEST_VERSION_API,
            code=code,
            msg="HTTP Error",
            hdrs=response_headers,
            fp=io.BytesIO(json.dumps(payload).encode("utf-8")),
        )

    def test_check_prints_red_error_on_network_failure_and_writes_error_idle_time(self):
        err = io.StringIO()
        before_unix = int(core.datetime.now().timestamp())
        with self._isolated_cache():
            with contextlib.redirect_stderr(err):
                with mock.patch.object(
                    core,
                    "urlopen",
                    side_effect=OSError("network down"),
                ):
                    core.check_for_newer_version(timeout_seconds=0.01)
            data = json.loads(core.VERSION_CHECK_CACHE_FILE.read_text(encoding="utf-8"))
        after_unix = int(core.datetime.now().timestamp())
        self.assertIn("\033[31;1m", err.getvalue())
        self.assertIn("Version check failed: network down", err.getvalue())
        self.assertGreaterEqual(
            data["idle_until_unix"],
            before_unix + core.VERSION_CHECK_ERROR_IDLE_DELAY_SECONDS,
        )
        self.assertLessEqual(
            data["idle_until_unix"],
            after_unix + core.VERSION_CHECK_ERROR_IDLE_DELAY_SECONDS,
        )
        self.assertEqual(data["last_check_unix"], 0)

    def test_check_warns_when_newer_version_available(self):
        err = io.StringIO()
        with self._isolated_cache():
            with contextlib.redirect_stderr(err):
                with mock.patch.object(core, "get_cli_version", return_value="0.0.1"):
                    with mock.patch.object(
                        core,
                        "urlopen",
                        return_value=_FakeResponse({"info": {"version": "0.0.2"}}),
                    ):
                        core.check_for_newer_version(timeout_seconds=0.01)
        text = err.getvalue()
        self.assertIn("\033[92;1m", text)
        self.assertIn("Update available: 0.0.2 (installed: 0.0.1)", text)
        self.assertIn("\033[0m", text)

    def test_check_does_not_warn_when_latest_is_not_newer(self):
        err = io.StringIO()
        with self._isolated_cache():
            with contextlib.redirect_stderr(err):
                with mock.patch.object(core, "get_cli_version", return_value="0.0.2"):
                    with mock.patch.object(
                        core,
                        "urlopen",
                        return_value=_FakeResponse({"info": {"version": "0.0.2"}}),
                    ):
                        core.check_for_newer_version(timeout_seconds=0.01)
        self.assertEqual(err.getvalue(), "")

    def test_check_skips_network_when_idle_time_is_not_expired(self):
        with self._isolated_cache():
            cache_data = {
                "last_check_unix": 1,
                "last_check_human": "1970-01-01 00:00:01",
                "idle_until_unix": 4_000_000_000,
                "idle_until_human": "2096-10-02 07:06:40",
            }
            core.VERSION_CHECK_CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
            core.VERSION_CHECK_CACHE_FILE.write_text(
                json.dumps(cache_data),
                encoding="utf-8",
            )
            with mock.patch.object(core, "urlopen") as urlopen_mock:
                core.check_for_newer_version(timeout_seconds=0.01)
            urlopen_mock.assert_not_called()

    def test_check_forces_network_when_idle_time_is_not_expired_and_ignore_idle_cache_true(self):
        with self._isolated_cache():
            cache_data = {
                "last_check_unix": 1,
                "last_check_human": "1970-01-01 00:00:01",
                "idle_until_unix": 4_000_000_000,
                "idle_until_human": "2096-10-02 07:06:40",
            }
            core.VERSION_CHECK_CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
            core.VERSION_CHECK_CACHE_FILE.write_text(
                json.dumps(cache_data),
                encoding="utf-8",
            )
            with mock.patch.object(
                core,
                "urlopen",
                return_value=_FakeResponse({"info": {"version": "0.0.1"}}),
            ) as urlopen_mock:
                core.check_for_newer_version(
                    timeout_seconds=0.01,
                    ignore_idle_cache=True,
                )
            urlopen_mock.assert_called_once()

    def test_check_writes_idle_time_state_on_success(self):
        before_unix = int(core.datetime.now().timestamp())
        with self._isolated_cache():
            with mock.patch.object(
                core,
                "urlopen",
                return_value=_FakeResponse({"info": {"version": "0.0.2"}}),
            ):
                core.check_for_newer_version(timeout_seconds=0.01)
            data = json.loads(core.VERSION_CHECK_CACHE_FILE.read_text(encoding="utf-8"))
        after_unix = int(core.datetime.now().timestamp())
        self.assertEqual(
            sorted(data.keys()),
            [
                "idle_until_human",
                "idle_until_unix",
                "last_check_human",
                "last_check_unix",
            ],
        )
        self.assertIsInstance(data["last_check_unix"], int)
        self.assertIsInstance(data["idle_until_unix"], int)
        self.assertGreaterEqual(data["last_check_unix"], before_unix)
        self.assertLessEqual(data["last_check_unix"], after_unix)
        self.assertEqual(
            data["idle_until_unix"] - data["last_check_unix"],
            core.VERSION_CHECK_IDLE_DELAY_SECONDS,
        )

    def test_check_prints_http_403_rate_limit_error_details_and_writes_error_idle_time(self):
        err = io.StringIO()
        before_unix = int(core.datetime.now().timestamp())
        rate_limit_error = self._http_error(
            code=403,
            payload={"message": "rate limit exceeded"},
        )
        with self._isolated_cache():
            with contextlib.redirect_stderr(err):
                with mock.patch.object(
                    core,
                    "urlopen",
                    side_effect=rate_limit_error,
                ):
                    core.check_for_newer_version(timeout_seconds=0.01)
            data = json.loads(core.VERSION_CHECK_CACHE_FILE.read_text(encoding="utf-8"))
        after_unix = int(core.datetime.now().timestamp())
        text = err.getvalue()
        self.assertIn("\033[31;1m", text)
        self.assertIn("Version check failed: HTTP 403: rate limit exceeded", text)
        self.assertGreaterEqual(
            data["idle_until_unix"],
            before_unix + core.VERSION_CHECK_ERROR_IDLE_DELAY_SECONDS,
        )
        self.assertLessEqual(
            data["idle_until_unix"],
            after_unix + core.VERSION_CHECK_ERROR_IDLE_DELAY_SECONDS,
        )
        self.assertEqual(data["last_check_unix"], 0)

    def test_resolve_release_api_url_uses_fixed_pypi_constant(self):
        # REQ-124: the release check resolves exactly the PyPI JSON API URL.
        api_url = core._resolve_release_api_url(Path("/repo"))
        self.assertEqual(api_url, core.PYPI_LATEST_VERSION_API)
        self.assertEqual(api_url, "https://pypi.org/pypi/galias/json")

    def test_idle_time_uses_hardcoded_idle_delays(self):
        self.assertEqual(core.VERSION_CHECK_IDLE_DELAY_SECONDS, 3600)
        self.assertEqual(core.VERSION_CHECK_ERROR_IDLE_DELAY_SECONDS, 86400)

    def test_http_429_uses_fixed_error_idle_delay(self):
        err = io.StringIO()
        before_unix = int(core.datetime.now().timestamp())
        rate_limit_error = self._http_error(
            code=429,
            payload={"message": "rate limit exceeded"},
            headers={"Retry-After": "600"},
        )
        with self._isolated_cache():
            with contextlib.redirect_stderr(err):
                with mock.patch.object(core, "urlopen", side_effect=rate_limit_error):
                    core.check_for_newer_version(timeout_seconds=0.01)
            data = json.loads(core.VERSION_CHECK_CACHE_FILE.read_text(encoding="utf-8"))
        after_unix = int(core.datetime.now().timestamp())
        self.assertIn("Version check failed: HTTP 429: rate limit exceeded", err.getvalue())
        self.assertGreaterEqual(
            data["idle_until_unix"],
            before_unix + core.VERSION_CHECK_ERROR_IDLE_DELAY_SECONDS,
        )
        self.assertLessEqual(
            data["idle_until_unix"],
            after_unix + core.VERSION_CHECK_ERROR_IDLE_DELAY_SECONDS,
        )
        self.assertEqual(data["last_check_unix"], 0)

    def test_invalid_json_payload_writes_error_idle_delay(self):
        err = io.StringIO()
        before_unix = int(core.datetime.now().timestamp())
        with self._isolated_cache():
            with contextlib.redirect_stderr(err):
                with mock.patch.object(
                    core,
                    "urlopen",
                    return_value=_RawResponse(b"not-json"),
                ):
                    core.check_for_newer_version(timeout_seconds=0.01)
            data = json.loads(core.VERSION_CHECK_CACHE_FILE.read_text(encoding="utf-8"))
        after_unix = int(core.datetime.now().timestamp())
        self.assertIn("Version check failed: invalid JSON payload:", err.getvalue())
        self.assertGreaterEqual(
            data["idle_until_unix"],
            before_unix + core.VERSION_CHECK_ERROR_IDLE_DELAY_SECONDS,
        )
        self.assertLessEqual(
            data["idle_until_unix"],
            after_unix + core.VERSION_CHECK_ERROR_IDLE_DELAY_SECONDS,
        )
        self.assertEqual(data["last_check_unix"], 0)

    def test_invalid_installed_version_writes_error_idle_delay(self):
        err = io.StringIO()
        before_unix = int(core.datetime.now().timestamp())
        with self._isolated_cache():
            with contextlib.redirect_stderr(err):
                with mock.patch.object(core, "get_cli_version", return_value="unknown"):
                    core.check_for_newer_version(timeout_seconds=0.01)
            data = json.loads(core.VERSION_CHECK_CACHE_FILE.read_text(encoding="utf-8"))
        after_unix = int(core.datetime.now().timestamp())
        self.assertIn(
            "Version check failed: installed version is not semantic version.",
            err.getvalue(),
        )
        self.assertGreaterEqual(
            data["idle_until_unix"],
            before_unix + core.VERSION_CHECK_ERROR_IDLE_DELAY_SECONDS,
        )
        self.assertLessEqual(
            data["idle_until_unix"],
            after_unix + core.VERSION_CHECK_ERROR_IDLE_DELAY_SECONDS,
        )
        self.assertEqual(data["last_check_unix"], 0)

    def test_check_reports_error_when_info_version_is_not_semantic(self):
        # REQ-124: payload lacking a semantic `info.version` is a terminal error.
        err = io.StringIO()
        before_unix = int(core.datetime.now().timestamp())
        with self._isolated_cache():
            with contextlib.redirect_stderr(err):
                with mock.patch.object(
                    core,
                    "urlopen",
                    return_value=_FakeResponse({"info": {"version": "not-semver"}}),
                ):
                    core.check_for_newer_version(timeout_seconds=0.01)
            data = json.loads(core.VERSION_CHECK_CACHE_FILE.read_text(encoding="utf-8"))
        after_unix = int(core.datetime.now().timestamp())
        self.assertIn(
            "Version check failed: invalid API payload: `info.version` is not semantic version.",
            err.getvalue(),
        )
        self.assertGreaterEqual(
            data["idle_until_unix"],
            before_unix + core.VERSION_CHECK_ERROR_IDLE_DELAY_SECONDS,
        )
        self.assertLessEqual(
            data["idle_until_unix"],
            after_unix + core.VERSION_CHECK_ERROR_IDLE_DELAY_SECONDS,
        )
        self.assertEqual(data["last_check_unix"], 0)

    ## @brief Verify the default PyPI self-upgrade pins the latest release (REQ-001).
    # @details Defect reproducer: an installed release whose source is not PyPI
    #          (for example a GitHub tag install) survives `uv tool install galias
    #          --upgrade` because the recorded requirement stays satisfied, so the
    #          PyPI publication is never installed even when it is older than the
    #          installed release. The default argv therefore MUST pin the resolved
    #          latest PyPI version while still carrying no REQ-236 forcing option
    #          and no GitHub `--from` override.
    # @param self {UpdateCheckTest} Isolated test instance.
    # @return {None} Assert the REQ-001 pinned latest-release install argv.
    def test_upgrade_self_pypi_argv_pins_latest_release(self):
        # REQ-001: default --upgrade installs the latest PyPI release.
        with mock.patch.object(
            core, "_fetch_pypi_latest_version", return_value="0.52.3"
        ) as fetch_latest:
            with mock.patch.object(core, "_is_linux_platform", return_value=True):
                with mock.patch.object(core, "_run_checked") as run_checked:
                    core.upgrade_self(Path("/repo"))
        fetch_latest.assert_called_once()
        run_checked.assert_called_once_with(
            [
                "uv",
                "tool",
                "install",
                f"{core.UV_TOOL_NAME}==0.52.3",
                "--upgrade",
            ]
        )
        argv = run_checked.call_args.args[0]
        self.assertNotIn("--from", argv)
        for forcing_option in core.UV_TOOL_FORCE_UPGRADE_OPTIONS:
            self.assertNotIn(forcing_option, argv)

    ## @brief Verify the unpinned fallback when latest PyPI resolution fails (REQ-001).
    # @details A failed PyPI metadata resolution keeps the previous unpinned
    #          resolver argv so the self-upgrade still installs the latest release
    #          resolved by uv instead of aborting the management command.
    # @param self {UpdateCheckTest} Isolated test instance.
    # @return {None} Assert the REQ-001 unpinned fallback install argv.
    def test_upgrade_self_pypi_argv_falls_back_when_latest_resolution_fails(self):
        # REQ-001: unresolved latest version keeps the unpinned requirement.
        with mock.patch.object(
            core, "_fetch_pypi_latest_version", return_value=None
        ):
            with mock.patch.object(core, "_is_linux_platform", return_value=True):
                with mock.patch.object(core, "_run_checked") as run_checked:
                    core.upgrade_self(Path("/repo"))
        run_checked.assert_called_once_with(
            [
                "uv",
                "tool",
                "install",
                core.UV_TOOL_NAME,
                "--upgrade",
            ]
        )

    ## @brief Verify `--upgrade --force` appends the uv forcing options (REQ-236).
    # @details Mock the platform and subprocess boundaries; assert the PyPI
    #          install argv carries `--force --reinstall --refresh` for the
    #          forced download plus complete reinstallation.
    # @param self {UpdateCheckTest} Isolated test instance.
    # @return {None} Assert REQ-236 forced PyPI upgrade argv.
    def test_upgrade_self_force_installs_with_forcing_options(self):
        # REQ-236: --upgrade --force executes uv tool install with forcing options.
        with mock.patch.object(core, "_is_linux_platform", return_value=True):
            with mock.patch.object(core, "_run_checked") as run_checked:
                core.upgrade_self(Path("/repo"), force=True)
        run_checked.assert_called_once_with(
            [
                "uv",
                "tool",
                "install",
                core.UV_TOOL_NAME,
                *core.UV_TOOL_FORCE_UPGRADE_OPTIONS,
            ]
        )

    ## @brief Verify the GitHub-sourced self-upgrade installs the newest release tag (REQ-201, REQ-208, REQ-209).
    # @details Mock the tag-resolution, platform-gate, and subprocess boundaries;
    #          assert the resolved `tag_name` is appended to the git `--from`
    #          override as `@<tag>` verbatim.
    # @param self {UpdateCheckTest} Isolated test instance.
    # @return {None} Assert REQ-201/REQ-208/REQ-209 upgrade argv.
    def test_upgrade_self_github_installs_latest_release_tag(self):
        # REQ-201: --upgrade --develop installs the newest GitHub release tag.
        with mock.patch.object(
            core, "_fetch_github_latest_release_tag", return_value="v1.2.3"
        ) as fetch_tag:
            with mock.patch.object(core, "_is_linux_platform", return_value=True):
                with mock.patch.object(core, "_run_checked") as run_checked:
                    core.upgrade_self(Path("/repo"), github=True)
        fetch_tag.assert_called_once()
        run_checked.assert_called_once_with(
            [
                "uv",
                "tool",
                "install",
                "--from",
                f"{core.GITHUB_UPGRADE_SOURCE}@v1.2.3",
                core.UV_TOOL_NAME,
            ]
        )

    ## @brief Verify the forced GitHub-sourced self-upgrade appends the forcing options (REQ-237).
    # @details Mock the tag-resolution, platform-gate, and subprocess boundaries;
    #          assert the forced install argv carries `--force --reinstall
    #          --refresh` before the `--from` override.
    # @param self {UpdateCheckTest} Isolated test instance.
    # @return {None} Assert REQ-237 forced GitHub upgrade argv.
    def test_upgrade_self_github_force_installs_with_forcing_options(self):
        # REQ-237: --upgrade --develop --force executes uv tool install with forcing options.
        with mock.patch.object(
            core, "_fetch_github_latest_release_tag", return_value="v1.2.3"
        ):
            with mock.patch.object(core, "_is_linux_platform", return_value=True):
                with mock.patch.object(core, "_run_checked") as run_checked:
                    core.upgrade_self(Path("/repo"), github=True, force=True)
        run_checked.assert_called_once_with(
            [
                "uv",
                "tool",
                "install",
                *core.UV_TOOL_FORCE_UPGRADE_OPTIONS,
                "--from",
                f"{core.GITHUB_UPGRADE_SOURCE}@v1.2.3",
                core.UV_TOOL_NAME,
            ]
        )

    ## @brief Verify upgrade aborts when GitHub tag resolution fails (REQ-210).
    # @details Mock a failed tag resolution; assert the English abort diagnostic,
    #          the non-zero exit status, and that no install subprocess runs.
    # @param self {UpdateCheckTest} Isolated test instance.
    # @return {None} Assert REQ-210 abort contract.
    def test_upgrade_self_github_aborts_when_tag_resolution_fails(self):
        # REQ-210: failed tag resolution aborts before any install.
        err = io.StringIO()
        with mock.patch.object(
            core, "_fetch_github_latest_release_tag", return_value=None
        ):
            with mock.patch.object(core, "_run_checked") as run_checked:
                with contextlib.redirect_stderr(err):
                    with self.assertRaises(SystemExit) as ctx:
                        core.upgrade_self(Path("/repo"), github=True)
        self.assertEqual(ctx.exception.code, 1)
        self.assertIn(
            "Unable to resolve the latest GitHub release tag",
            err.getvalue(),
        )
        run_checked.assert_not_called()

    ## @brief Verify raw tag_name retrieval for the upgrade ref (REQ-208).
    # @details Mock the HTTP boundary with a synthetic release payload; the
    #          upgrade ref keeps the `tag_name` verbatim including the `v`.
    # @param self {UpdateCheckTest} Isolated test instance.
    # @return {None} Assert REQ-208 raw tag text.
    def test_fetch_github_latest_release_tag_returns_raw_tag_name(self):
        # REQ-208: tag_name is returned verbatim (leading `v` preserved).
        with mock.patch.object(
            core, "urlopen", return_value=_FakeResponse({"tag_name": "v9.9.9"})
        ):
            self.assertEqual(
                core._fetch_github_latest_release_tag(timeout_seconds=0.01),
                "v9.9.9",
            )

    ## @brief Verify the default-vs-GitHub source isolation contract (REQ-199).
    # @details Assert the default check/upgrade constants stay PyPI-only while
    #          GitHub constants exist only for REQ-201/REQ-202 flows.
    # @param self {UpdateCheckTest} Isolated test instance.
    # @return {None} Assert REQ-199 constant isolation.
    def test_default_flows_use_pypi_and_github_constants_are_isolated(self):
        # REQ-199: default check/upgrade paths are PyPI-only.
        upgrade_text = " ".join(core.UV_TOOL_UPGRADE_COMMAND)
        self.assertNotIn("--from", upgrade_text)
        self.assertNotIn("git+", upgrade_text)
        self.assertNotIn("github.com", upgrade_text)
        self.assertTrue(
            core.PYPI_LATEST_VERSION_API.startswith("https://pypi.org/pypi/")
        )
        self.assertNotIn("github.com", core.PYPI_LATEST_VERSION_API)
        # REQ-204: fixed GitHub reporting endpoint; REQ-201: fixed git source.
        self.assertEqual(
            core.GITHUB_LATEST_RELEASE_API,
            "https://api.github.com/repos/Ogekuri/GAlias/releases/latest",
        )
        self.assertEqual(
            core.GITHUB_UPGRADE_SOURCE,
            "git+https://github.com/Ogekuri/GAlias",
        )

    ## @brief Verify GitHub tag_name parsing and v-prefix stripping (REQ-204, REQ-230).
    # @details Mock the HTTP boundary with a synthetic release payload.
    # @param self {UpdateCheckTest} Isolated test instance.
    # @return {None} Assert REQ-204 normalized version text with no reason.
    def test_fetch_github_latest_version_parses_tag_name(self):
        with mock.patch.object(
            core, "urlopen", return_value=_FakeResponse({"tag_name": "v1.2.3"})
        ):
            version, failure_reason = core._fetch_github_latest_version(
                timeout_seconds=0.01
            )
        self.assertEqual(version, "1.2.3")
        self.assertIsNone(failure_reason)

    ## @brief Verify GitHub fetch failure diagnostics and reason (REQ-127, REQ-202, REQ-230, REQ-231).
    # @details Network failure and missing tag_name both return no version
    #          plus a non-empty English reason with the standardized
    #          bright-red update-check diagnostic on stderr.
    # @param self {UpdateCheckTest} Isolated test instance.
    # @return {None} Assert None version, reason text, and error output.
    def test_fetch_github_latest_version_reports_errors_and_returns_none(self):
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            with mock.patch.object(core, "urlopen", side_effect=OSError("network down")):
                version, failure_reason = core._fetch_github_latest_version(
                    timeout_seconds=0.01
                )
            self.assertIsNone(version)
            self.assertEqual(failure_reason, "network down")
            with mock.patch.object(
                core, "urlopen", return_value=_FakeResponse({"unexpected": "x"})
            ):
                version, failure_reason = core._fetch_github_latest_version(
                    timeout_seconds=0.01
                )
            self.assertIsNone(version)
            self.assertEqual(
                failure_reason,
                "invalid API payload: `tag_name` is not semantic version.",
            )
        self.assertIn("Version check failed: network down", err.getvalue())
        self.assertIn("`tag_name` is not semantic version.", err.getvalue())

    ## @brief Verify HTTP 404 rate-limit interception carries the API reason (REQ-230, REQ-231).
    # @details Mock the HTTP boundary with a 404 `HTTPError` whose body
    #          carries the GitHub API rate-limit message; the fetcher returns
    #          no version plus a reason containing the HTTP status code and
    #          the API message, and the standardized REQ-127 diagnostic
    #          repeats the reason on stderr.
    # @param self {UpdateCheckTest} Isolated test instance.
    # @return {None} Assert REQ-230/REQ-231 reason composition.
    def test_fetch_github_latest_version_intercepts_http_404_rate_limit(self):
        rate_limit_headers = Message()
        rate_limit_error = HTTPError(
            url=core.GITHUB_LATEST_RELEASE_API,
            code=404,
            msg="Not Found",
            hdrs=rate_limit_headers,
            fp=io.BytesIO(
                b'{"message": "API rate limit exceeded for 203.0.113.7.",'
                b' "documentation_url": "https://docs.github.com/rest"}'
            ),
        )
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            with mock.patch.object(core, "urlopen", side_effect=rate_limit_error):
                version, failure_reason = core._fetch_github_latest_version(
                    timeout_seconds=0.01
                )
        self.assertIsNone(version)
        assert isinstance(failure_reason, str)
        self.assertIn("HTTP 404", failure_reason)
        self.assertIn("API rate limit exceeded", failure_reason)
        self.assertIn(failure_reason, err.getvalue())

    ## @brief Verify check_for_newer_version returns the PyPI latest text.
    # @details Mock the HTTP boundary and isolated cache; REQ-202 consumers use
    #          this return value for the PyPI report line.
    # @param self {UpdateCheckTest} Isolated test instance.
    # @return {None} Assert returned version text.
    def test_check_returns_latest_pypi_version_text(self):
        with self._isolated_cache():
            with mock.patch.object(core, "get_cli_version", return_value="0.0.1"):
                with mock.patch.object(
                    core,
                    "urlopen",
                    return_value=_FakeResponse({"info": {"version": "0.0.2"}}),
                ):
                    result = core.check_for_newer_version(timeout_seconds=0.01)
        self.assertEqual(result, "0.0.2")

    def test_uninstall_self_uses_uv_tool_uninstall(self):
        with self._isolated_cache():
            with mock.patch.object(core, "_is_linux_platform", return_value=True):
                with mock.patch.object(core, "_run_checked") as run_checked:
                    core.uninstall_self()
        run_checked.assert_called_once_with(
            ["uv", "tool", "uninstall", core.UV_TOOL_NAME]
        )

    def test_uninstall_self_removes_idle_time_cache_file_and_directory(self):
        with self._isolated_cache():
            core.VERSION_CHECK_CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
            core.VERSION_CHECK_CACHE_FILE.write_text("{}", encoding="utf-8")
            with mock.patch.object(core, "_is_linux_platform", return_value=True):
                with mock.patch.object(core, "_run_checked"):
                    core.uninstall_self()
            self.assertFalse(core.VERSION_CHECK_CACHE_FILE.exists())
            self.assertFalse(core.VERSION_CHECK_CACHE_FILE.parent.exists())
