#!/usr/bin/env python3
## @file core.py
# @brief Core command dispatch and galias runtime orchestration.
# @details Provides command routing, repository diagnostics, changelog/version workflows, and process wrappers.

import argparse
import importlib
import json
import os
import re
import shlex
import shutil
import subprocess
import sys
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from git_alias import configuration

pathspec = importlib.import_module("pathspec")

## @brief Repository-local configuration filename resolved from repository root.
## @details Value `.galias.conf` per DES-006/REQ-014; loaded by `load_cli_config`
##          and managed by `configuration.execute` for the five DES-006 local
##          keys (`master`, `develop`, `work`, `default_commit_module`, `ver_rules`).
##          No `.g.conf` fallback exists: backward compatibility is not implemented.
## @satisfies DES-006, DES-009, REQ-014, REQ-017

CONFIG_FILENAME = ".galias.conf"
## @brief Global configuration directory under `$HOME`.
## @details Value `.config/galias` after the `galias` distribution rename from
##          `git-alias`; combined with `$HOME` by `get_global_config_path` to
##          locate `config.json` (CTN-003, DES-006, REQ-186).
## @satisfies CTN-003, DES-006, REQ-186
GLOBAL_CONFIG_DIRECTORY = ".config/galias"
## @brief Constant `GLOBAL_CONFIG_FILENAME` used by CLI runtime paths and policies.
GLOBAL_CONFIG_FILENAME = "config.json"

## @brief Astral uv tool and distribution name for self-management flows.
## @details Value `galias` after the distribution rename from `git-alias`;
##          drives `uv tool install` (REQ-001), `uv tool uninstall` (REQ-002),
##          and the `~/.cache/<tool>` update-check cache directory (REQ-136).
## @satisfies REQ-001, REQ-002, REQ-136
UV_TOOL_NAME = "galias"
## @brief PyPI project name sourcing update checks and self-upgrade installs.
## @details Canonical PyPI distribution identifier equal to `UV_TOOL_NAME`;
##          composes the PyPI JSON API endpoint (REQ-124) and names the
##          `uv tool install` self-upgrade target (REQ-001). PyPI is the only
##          remote source used by default version verification and upgrades
##          (REQ-199).
## @satisfies REQ-001, REQ-124, REQ-199
PYPI_PROJECT_NAME = UV_TOOL_NAME
## @brief PyPI JSON API endpoint resolving the latest published version.
## @details Fixed endpoint `https://pypi.org/pypi/galias/json`; the update check
##          parses the latest version from its `info.version` JSON field
##          (REQ-124) and default checks query no other remote source (REQ-199).
## @satisfies REQ-124, REQ-199
PYPI_LATEST_VERSION_API = f"https://pypi.org/pypi/{PYPI_PROJECT_NAME}/json"
## @brief Upstream GitHub repository hosting intermediate and test releases.
## @details Value `Ogekuri/GAlias`; composes the GitHub latest-release API
##          endpoint (REQ-204) and the git upgrade source (REQ-201). GitHub is
##          queried only by REQ-201 upgrades and REQ-202 version reporting.
## @satisfies REQ-201, REQ-202, REQ-204
GITHUB_REPOSITORY = "Ogekuri/GAlias"
## @brief GitHub latest-release API endpoint for version reporting and upgrade tag resolution.
## @details Fixed endpoint `https://api.github.com/repos/Ogekuri/GAlias/releases/latest`;
##          `_fetch_github_latest_version` parses the release `tag_name` JSON
##          field stripping one leading `v` (REQ-204), and
##          `_fetch_github_latest_release_tag` returns the same `tag_name`
##          verbatim to select the REQ-209 upgrade ref (REQ-208). This endpoint
##          never participates in default update checks (REQ-199).
## @satisfies REQ-202, REQ-204, REQ-208, REQ-199
GITHUB_LATEST_RELEASE_API = (
    f"https://api.github.com/repos/{GITHUB_REPOSITORY}/releases/latest"
)
## @brief Git source specifier base for GitHub-sourced self-upgrades.
## @details Value `git+https://github.com/Ogekuri/GAlias`; consumed only by the
##          REQ-201 `--upgrade --develop` (equivalent `--dev`) flow, where
##          `_build_github_upgrade_command` appends the REQ-208-resolved
##          release tag as `@<tag>` to form the uv `--from` override (REQ-209).
## @satisfies REQ-201, REQ-209
GITHUB_UPGRADE_SOURCE = f"git+https://github.com/{GITHUB_REPOSITORY}"
## @brief Self-upgrade command installing the latest PyPI release.
## @details Executes `uv tool install galias` with no forcing options so the
##          standard install/update process applies (REQ-001); the default
##          path carries no `--from` override, keeping PyPI the only default
##          upgrade source (REQ-199, REQ-201). Forced upgrades append
##          `UV_TOOL_FORCE_UPGRADE_OPTIONS` (REQ-236).
## @satisfies REQ-001, REQ-199, REQ-236
UV_TOOL_UPGRADE_COMMAND = (
    "uv",
    "tool",
    "install",
    UV_TOOL_NAME,
)

## @brief Forcing options appended to `uv tool install` for forced self-upgrades.
## @details Tuple `("--force", "--reinstall", "--refresh")` appended to the
##          selected upgrade argv when `--upgrade --force` (optionally with
##          `--develop`/`--dev`) requests a forced download plus complete
##          reinstallation (REQ-236, REQ-237); never appended on the standard
##          unforced install path (REQ-001, REQ-209).
## @satisfies REQ-236, REQ-237
UV_TOOL_FORCE_UPGRADE_OPTIONS = ("--force", "--reinstall", "--refresh")
## @brief Constant `UV_TOOL_UNINSTALL_COMMAND` used by CLI runtime paths and policies.
UV_TOOL_UNINSTALL_COMMAND = ("uv", "tool", "uninstall", UV_TOOL_NAME)

## @brief Constant `VERSION_CHECK_CACHE_FILE` used by CLI runtime paths and policies.
VERSION_CHECK_CACHE_FILE = (
    Path.home()
    / ".cache"
    / UV_TOOL_NAME
    / "check_version_idle-time.json"
)
## @brief Constant `VERSION_CHECK_IDLE_DELAY_SECONDS` used by CLI runtime paths and policies.
VERSION_CHECK_IDLE_DELAY_SECONDS = 3600
## @brief Constant `VERSION_CHECK_ERROR_IDLE_DELAY_SECONDS` used by CLI runtime paths and policies.
VERSION_CHECK_ERROR_IDLE_DELAY_SECONDS = 86400
## @brief Constant `VERSION_CHECK_TIMEOUT_SECONDS` used by CLI runtime paths and policies.
VERSION_CHECK_TIMEOUT_SECONDS = 2.0
## @brief Constant `VERSION_AVAILABLE_COLOR` used by CLI runtime paths and policies.
VERSION_AVAILABLE_COLOR = "\033[92;1m"
## @brief Constant `VERSION_ERROR_COLOR` used by CLI runtime paths and policies.
VERSION_ERROR_COLOR = "\033[31;1m"
## @brief Constant `ANSI_COLOR_RESET` used by CLI runtime paths and policies.
ANSI_COLOR_RESET = "\033[0m"

## @brief Label field width aligning the `--ver`/`--version` report colon separator.
# @details Every `--ver`/`--version` report line left-justifies its label in this
#          many characters before appending `: <version>` (REQ-241); 18 characters
#          fit the longest label `Current Installed` (17 characters) plus one
#          separating blank so every `: ` separator aligns at column 20.
# @satisfies REQ-241
VERSION_REPORT_LABEL_WIDTH = 18

## @brief Constant `DEFAULT_VER_RULES` used by CLI runtime paths and policies.

DEFAULT_VER_RULES = [
    ("README.md", r'\s*"(\d+\.\d+\.\d+)"\s*'),
    ("src/**/*.py", r'__version__\s*=\s*["\']?(\d+\.\d+\.\d+)["\']?'),
    ("pyproject.toml", r'\bversion\s*=\s*"(\d+\.\d+\.\d+)"'),
]
## @brief Constant `VERSION_CLEANUP_REGEXES` used by CLI runtime paths and policies.

VERSION_CLEANUP_REGEXES = [
    r"(^|/)\.git(/|$)",
    r"(^|/)\.vscode(/|$)",
    r"(^|/)tmp(/|$)",
    r"(^|/)temp(/|$)",
    r"(^|/)\.cache(/|$)",
    r"(^|/)\.pytest_cache(/|$)",
    r"(^|/)node_modules/\.cache(/|$)",
]
## @brief Constant `VERSION_CLEANUP_PATTERNS` used by CLI runtime paths and policies.

VERSION_CLEANUP_PATTERNS = [re.compile(pattern) for pattern in VERSION_CLEANUP_REGEXES]
ANSI_ESCAPE_RE = re.compile(r"\x1b\[[0-9;]*m")

## @brief Constant `DEFAULT_GP_COMMAND` used by CLI runtime paths and policies.
# @details Default terminal commit-graph launcher for the `gp` command pair
#          (REQ-186); imposed default value `gitui` per REQ-191.
# @satisfies REQ-191
DEFAULT_GP_COMMAND = configuration.SCHEMA["Global"].fields["gp_command"].default
## @brief Constant `DEFAULT_GR_COMMAND` used by CLI runtime paths and policies.
# @details Default terminal tag/decoration-graph launcher for the `gr`
#          command pair (REQ-186); imposed default value `tig` per REQ-191.
# @satisfies REQ-191
DEFAULT_GR_COMMAND = configuration.SCHEMA["Global"].fields["gr_command"].default
## @brief Constant `GIT_DIFFTOOL_COMMAND` used by CLI runtime paths and policies.
# @details Base argv executed by visual diff aliases (REQ-189); the
#          environment-selected diff tool is injected as `--extcmd` override
#          (REQ-190) when configured.
GIT_DIFFTOOL_COMMAND = ("git", "difftool", "-d")

## @brief Constant `DEFAULT_CONFIG` used by CLI runtime paths and policies.
# @details O(N) deep copies from the shared schema; flat consumer interface
# preserves existing alias algorithms and imposed command defaults.
# @satisfies REQ-191, REQ-192, REQ-242, REQ-253
DEFAULT_CONFIG = configuration.defaults("Global") | configuration.defaults("Local")

## @brief Constant `CONFIG` used by CLI runtime paths and policies.

CONFIG = DEFAULT_CONFIG.copy()
## @brief Constant `BRANCH_KEYS` used by CLI runtime paths and policies.

BRANCH_KEYS = ("master", "develop", "work")
## @brief Constant `LOCAL_CONFIG_KEYS` used by CLI runtime paths and policies.
LOCAL_CONFIG_KEYS = tuple(configuration.SCHEMA["Local"].fields)
## @brief Constant `GLOBAL_CONFIG_KEYS` used by CLI runtime paths and policies.
# @details Ordered key inventory derived from the canonical shared schema.
# @satisfies REQ-186, REQ-192, REQ-242
GLOBAL_CONFIG_KEYS = tuple(configuration.SCHEMA["Global"].fields)
## @brief Constant `MANAGEMENT_HELP` used by CLI runtime paths and policies.

MANAGEMENT_HELP = list(configuration.COMMAND_HELP.items()) + [
    ("--upgrade", "Reinstall galias on Linux; print manual command elsewhere. Combine with --develop or --dev to install the newest tagged release from GitHub. Add --force to force the download and a complete reinstallation. Note: --dev/--develop mean something different on major/minor/patch, where they limit the release to the configured develop branch."),
    ("--uninstall", "Uninstall galias on Linux; print manual command elsewhere."),
    ("--ver", "Print the CLI version with the latest PyPI and GitHub release versions."),
    ("--version", "Print the CLI version with the latest PyPI and GitHub release versions."),
    ("--help", "Print the full help screen or the help text of a specific alias."),
]


## @brief Execute `get_config_value` runtime logic for Git-Alias CLI.
# @details Executes `get_config_value` using deterministic CLI control-flow and explicit error propagation.
# @param name Input parameter consumed by `get_config_value`.
# @return Result emitted by `get_config_value` according to command contract.
def get_config_value(name):
    return CONFIG.get(name, DEFAULT_CONFIG[name])


## @brief Execute `get_branch` runtime logic for Git-Alias CLI.
# @details Executes `get_branch` using deterministic CLI control-flow and explicit error propagation.
# @param name Input parameter consumed by `get_branch`.
# @return Result emitted by `get_branch` according to command contract.
def get_branch(name):
    if name not in BRANCH_KEYS:
        raise KeyError(f"Unknown branch key {name}")
    return get_config_value(name)


## @brief Execute `get_editor` runtime logic for Git-Alias CLI.
# @details Executes `get_editor` using deterministic CLI control-flow and explicit error propagation.
# @return Result emitted by `get_editor` according to command contract.
def get_editor():
    return get_config_value("edit_command")


## @brief Load rule pairs from the active configuration for a rule-bearing config key.
# @details O(N) object traversal; strips fields and drops invalid entries.
# Negation patterns accept absent regex. Internal fallback pairs remain
# unchanged; configured sequence entries are ignored. Only diagnostics use I/O.
# @param key {str} Configuration key to read from `CONFIG`.
# @param fallback {List[Tuple[str, str]]} Default rule list used when no valid entry remains.
# @return {List[Tuple[str, Optional[str]]]} Parsed `(pattern, regex)` rule pairs; negation entries carry `None` regex.
# @satisfies REQ-162, REQ-207
def _load_config_rules(key, fallback):
    raw_value = CONFIG.get(key, DEFAULT_CONFIG[key])
    if not isinstance(raw_value, list):
        print(f"Ignoring non-list value for {key}", file=sys.stderr)
        return list(fallback)
    rules = []
    for entry in raw_value:
        pattern = regex = None
        if isinstance(entry, dict):
            pattern = entry.get("pattern")
            regex = entry.get("regex")
        if isinstance(pattern, str):
            pattern = pattern.strip()
        else:
            pattern = None
        if isinstance(regex, str):
            regex = regex.strip()
        else:
            regex = None
        if pattern and regex:
            rules.append((pattern, regex))
        elif pattern and pattern.startswith("!"):
            rules.append((pattern, None))
    return rules if rules else list(fallback)


## @brief Execute `get_version_rules` runtime logic for Git-Alias CLI.
# @details Executes `get_version_rules` using deterministic CLI control-flow and explicit error propagation.
# @return Result emitted by `get_version_rules` according to command contract.
def get_version_rules():
    return _load_config_rules("ver_rules", DEFAULT_VER_RULES)


## @brief Execute `get_cli_version` runtime logic for Git-Alias CLI.
# @details Executes `get_cli_version` using deterministic CLI control-flow and explicit error propagation.
# @return Result emitted by `get_cli_version` according to command contract.
def get_cli_version():
    init_path = Path(__file__).resolve().with_name("__init__.py")
    try:
        content = init_path.read_text(encoding="utf-8")
    except OSError:
        return "unknown"
    match = re.search(r'__version__\s*=\s*["\']([^"\']+)["\']', content)
    if match:
        return match.group(1)
    return "unknown"


## @brief Execute `_normalize_semver_text` runtime logic for Git-Alias CLI.
# @details Executes `_normalize_semver_text` using deterministic CLI control-flow and explicit error propagation.
# @param text Input parameter consumed by `_normalize_semver_text`.
# @return Result emitted by `_normalize_semver_text` according to command contract.
def _normalize_semver_text(text: str) -> str:
    value = (text or "").strip()
    if value.lower().startswith("v"):
        value = value[1:]
    return value


## @brief Format one `--ver`/`--version` report line with an aligned label column.
# @details Left-justifies `label` in a `VERSION_REPORT_LABEL_WIDTH`-character field
#          and appends `: ` plus `version_text`, implementing the REQ-241 contract
#          `<label>: <version>` with every `: ` separator aligned across the three
#          `--ver`/`--version` report lines. Pure function: performs no I/O,
#          mutates no state, and never raises for string inputs.
# @param label {str} Report label: `Current Installed`, `Latest @ PyPI`, or `Latest @ GitHub`.
# @param version_text {str} Version text or degraded value (`unavailable`, `unknown (<reason>)`).
# @return {str} REQ-241-aligned report line `<label padded to 18>: <version_text>`.
# @note Complexity: O(len(label) + len(version_text)).
# @see check_for_newer_version, _fetch_github_latest_version
# @satisfies REQ-241
def _format_version_report_line(label: str, version_text: str) -> str:
    return f"{label:<{VERSION_REPORT_LABEL_WIDTH}}: {version_text}"


## @brief Emit the standardized bright-green update warning for newer available versions.
# @details Formats the warning using the REQ-123 contract
#          `Update available: <latest> (installed: <current>)`,
#          applies ANSI bright-green color, and writes to stderr without altering process
#          control-flow.
# @param current Parsed current semantic version tuple `(major, minor, patch)`.
# @param latest_text Latest available semantic version text.
# @return None.
def _print_update_available_warning(
    current: Tuple[int, int, int],
    latest_text: str,
) -> None:
    current_text = "{}.{}.{}".format(*current)
    print(
        (
            f"{VERSION_AVAILABLE_COLOR}"
            f"Update available: {latest_text} (installed: {current_text})"
            f"{ANSI_COLOR_RESET}"
        ),
        file=sys.stderr,
    )


## @brief Emit a standardized bright-red update-check error message.
# @details Prefixes diagnostic payload with `Version check failed:` and applies ANSI
#          bright-red color formatting while preserving caller control-flow.
# @param detail Human-readable diagnostic detail.
# @return None.
def _print_update_check_error(detail: str) -> None:
    print(
        f"{VERSION_ERROR_COLOR}Version check failed: {detail}{ANSI_COLOR_RESET}",
        file=sys.stderr,
    )


## @brief Resolve the fixed PyPI JSON API URL for update checks.
# @details Returns the constant PyPI endpoint configured for the program package.
#          The `repo_root` parameter is intentionally ignored to keep call sites stable.
# @param repo_root Repository root placeholder parameter.
# @return Full PyPI JSON API URL string.
# @satisfies REQ-124
def _resolve_release_api_url(repo_root: Path) -> str:
    del repo_root
    return PYPI_LATEST_VERSION_API


## @brief Coerce candidate JSON timestamp values into unix-second integers.
# @details Accepts numeric values (`int`/`float`) and converts them to integer unix
#          seconds; all non-numeric values are rejected.
# @param value Candidate timestamp value loaded from JSON cache payload.
# @return Parsed unix timestamp integer when numeric; otherwise `None`.
def _coerce_unix_timestamp(value: object) -> Optional[int]:
    if isinstance(value, (int, float)):
        return int(value)
    return None


## @brief Persist update-check idle-time cache state to JSON file.
# @details Writes canonical fields `last_check_unix`, `last_check_human`,
#          `idle_until_unix`, and `idle_until_human` using second-precision
#          timestamps and emits standardized error diagnostics on I/O or timestamp failures.
# @param last_check_unix Unix timestamp of last successful version check.
# @param idle_until_unix Unix timestamp until next remote check is disabled.
# @return None.
# @satisfies REQ-126 REQ-131 REQ-136 REQ-137
def _write_version_check_state(
    *,
    last_check_unix: int,
    idle_until_unix: int,
) -> None:
    try:
        last_check_time = datetime.fromtimestamp(last_check_unix)
        idle_until_time = datetime.fromtimestamp(idle_until_unix)
        VERSION_CHECK_CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(VERSION_CHECK_CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump(
                {
                    "last_check_unix": int(last_check_unix),
                    "last_check_human": last_check_time.isoformat(
                        sep=" ",
                        timespec="seconds",
                    ),
                    "idle_until_unix": int(idle_until_unix),
                    "idle_until_human": idle_until_time.isoformat(
                        sep=" ",
                        timespec="seconds",
                    ),
                },
                f,
            )
    except (OSError, OverflowError, ValueError) as exc:
        _print_update_check_error(f"idle-time state write failed: {exc}")


## @brief Persist the canonical extended idle-time state for version-check errors.
# @details Reuses cached `last_check_unix` when available, normalizes missing or
#          invalid cached values to `0`, and writes `idle_until_unix = now_unix +
#          VERSION_CHECK_ERROR_IDLE_DELAY_SECONDS` to suppress repeated failing
#          version checks across all terminal error branches.
# @param cache_data Parsed idle-time JSON object from prior state.
# @param now_unix Current unix timestamp captured by the active release-check attempt.
# @return None.
# @satisfies REQ-130 REQ-131 REQ-137
def _write_version_check_error_state(
    cache_data: Dict[str, object],
    now_unix: int,
) -> None:
    last_check_unix = _coerce_unix_timestamp(cache_data.get("last_check_unix"))
    if last_check_unix is None:
        last_check_unix = 0
    _write_version_check_state(
        last_check_unix=last_check_unix,
        idle_until_unix=now_unix + VERSION_CHECK_ERROR_IDLE_DELAY_SECONDS,
    )


## @brief Execute `check_for_newer_version` runtime logic for Git-Alias CLI.
# @details Executes `check_for_newer_version` using deterministic CLI control-flow,
#          explicit error propagation, a fixed 3600-second idle window after
#          successful release checks, and a fixed 86400-second idle window after
#          terminal version-check errors while rewriting the idle-time JSON before
#          returning control on every error path. The remote source is exclusively
#          the PyPI JSON API `info.version` field (REQ-124, REQ-199).
# @param repo_root Input parameter consumed by `check_for_newer_version`.
# @param timeout_seconds Input parameter consumed by `check_for_newer_version`.
# @param ignore_idle_cache When `True`, bypasses `idle_until_unix` gating and forces an online check.
# @return {Optional[str]} Latest PyPI version text on success; None when the
#         check is skipped, unavailable, or failed.
# @satisfies REQ-123 REQ-124 REQ-126 REQ-127 REQ-129 REQ-130 REQ-131 REQ-137 REQ-199
def check_for_newer_version(
    *,
    repo_root: Optional[Path] = None,
    timeout_seconds: float = VERSION_CHECK_TIMEOUT_SECONDS,
    ignore_idle_cache: bool = False,
) -> Optional[str]:
    now = datetime.now()
    now_unix = int(now.timestamp())
    cache_data: Dict[str, object] = {}
    if VERSION_CHECK_CACHE_FILE.exists():
        try:
            with open(VERSION_CHECK_CACHE_FILE, "r", encoding="utf-8") as f:
                loaded_cache_data = json.load(f)
        except (OSError, json.JSONDecodeError) as exc:
            _print_update_check_error(f"idle-time state read failed: {exc}")
        else:
            if isinstance(loaded_cache_data, dict):
                cache_data = loaded_cache_data
                idle_until_unix = _coerce_unix_timestamp(cache_data.get("idle_until_unix"))
                if (
                    not ignore_idle_cache
                    and idle_until_unix is not None
                    and now_unix < idle_until_unix
                ):
                    return
                if (
                    cache_data.get("idle_until_unix") is not None
                    and idle_until_unix is None
                ):
                    _print_update_check_error(
                        "idle-time state is invalid: `idle_until_unix` must be numeric."
                    )
            else:
                _print_update_check_error(
                    "idle-time state is invalid: JSON root must be an object."
                )

    current = _parse_semver_tuple(get_cli_version())
    if current is None:
        _write_version_check_error_state(cache_data, now_unix)
        _print_update_check_error("installed version is not semantic version.")
        return

    root = Path(repo_root) if repo_root is not None else get_git_root()
    release_api_url = _resolve_release_api_url(root)

    request = Request(
        release_api_url,
        headers={
            "Accept": "application/json",
            "User-Agent": PYPI_PROJECT_NAME,
        },
        method="GET",
    )
    try:
        with urlopen(request, timeout=timeout_seconds) as response:
            payload_bytes = response.read()
    except HTTPError as exc:
        details = ""
        try:
            details_text = exc.read().decode("utf-8")
            details_payload = json.loads(details_text)
            if isinstance(details_payload, dict):
                details = str(details_payload.get("message", "")).strip()
        except (OSError, UnicodeDecodeError, json.JSONDecodeError):
            details = ""
        _write_version_check_error_state(cache_data, now_unix)
        if details:
            _print_update_check_error(f"HTTP {exc.code}: {details}")
        else:
            _print_update_check_error(f"HTTP {exc.code}")
        return
    except URLError as exc:
        _write_version_check_error_state(cache_data, now_unix)
        _print_update_check_error(str(exc.reason))
        return
    except TimeoutError:
        _write_version_check_error_state(cache_data, now_unix)
        _print_update_check_error("request timeout exceeded.")
        return
    except OSError as exc:
        _write_version_check_error_state(cache_data, now_unix)
        _print_update_check_error(str(exc))
        return
    try:
        payload_text = (
            payload_bytes.decode("utf-8")
            if isinstance(payload_bytes, (bytes, bytearray))
            else str(payload_bytes)
        )
        data = json.loads(payload_text)
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
        _write_version_check_error_state(cache_data, now_unix)
        _print_update_check_error(f"invalid JSON payload: {exc}")
        return
    if not isinstance(data, dict):
        _write_version_check_error_state(cache_data, now_unix)
        _print_update_check_error("invalid API payload: JSON root must be an object.")
        return
    info = data.get("info")
    version_text = str(info.get("version") or "") if isinstance(info, dict) else ""
    latest_text = _normalize_semver_text(version_text)
    latest = _parse_semver_tuple(latest_text)
    if latest is None:
        _write_version_check_error_state(cache_data, now_unix)
        _print_update_check_error(
            "invalid API payload: `info.version` is not semantic version."
        )
        return

    idle_seconds = VERSION_CHECK_IDLE_DELAY_SECONDS
    _write_version_check_state(
        last_check_unix=now_unix,
        idle_until_unix=now_unix + idle_seconds,
    )

    if latest > current:
        _print_update_available_warning(current, latest_text)
    return latest_text


## @brief Build the uv argv installing the newest GitHub release tag.
# @details Composes the REQ-209 self-upgrade command by appending the
#          REQ-208-resolved release tag to `GITHUB_UPGRADE_SOURCE` as the
#          pip/uv direct-URL reference `git+https://github.com/Ogekuri/GAlias@<tag>`,
#          so Astral uv installs the tool from the newest tagged release
#          regardless of the branch containing it (REQ-201). With `force`
#          enabled, `UV_TOOL_FORCE_UPGRADE_OPTIONS` is inserted before the
#          `--from` override so the install becomes a forced download plus
#          complete reinstallation (REQ-237); the unforced path carries no
#          forcing options (REQ-209).
# @param tag {str} Raw GitHub release tag name (REQ-208), including any leading `v`.
# @param force {bool} When True, prepend the uv forcing options (REQ-237).
# @return {Tuple[str, ...]} `uv tool install [--force --reinstall --refresh] --from <source>@<tag> galias` argv.
# @satisfies REQ-209, REQ-237, REQ-201
def _build_github_upgrade_command(tag: str, force: bool = False) -> Tuple[str, ...]:
    command: List[str] = ["uv", "tool", "install"]
    if force:
        command.extend(UV_TOOL_FORCE_UPGRADE_OPTIONS)
    command.extend(
        (
            "--from",
            f"{GITHUB_UPGRADE_SOURCE}@{tag}",
            UV_TOOL_NAME,
        )
    )
    return tuple(command)


## @brief Compose a non-empty English failure reason for an intercepted GitHub fetch exception.
# @details Intercepts transport and payload failures raised by the GitHub
#          latest-release fetch and derives a deterministic diagnostic:
#          `HTTPError` instances render `HTTP <code>: <reason phrase>:
#          <api message>`, appending the API-provided JSON `message` field
#          when the error body decodes to a JSON object containing a
#          non-empty `message` string; `URLError` instances render the
#          bare socket reason; every other exception renders its text,
#          falling back to the exception class name when the text is blank.
#          Never mutates state and never raises: the error-body read is
#          guarded so reason derivation stays total.
# @param exc {BaseException} Exception intercepted by the GitHub fetch guard.
# @return {str} Non-empty English failure reason (REQ-231).
# @note Complexity: O(1) excluding the single error-body read.
# @satisfies REQ-231
def _github_failure_reason(exc: BaseException) -> str:
    if isinstance(exc, HTTPError):
        reason_text = str(exc.reason or "").strip()
        api_message = ""
        try:
            body = json.loads(exc.read().decode("utf-8", "ignore"))
        except Exception:
            body = None
        if isinstance(body, dict):
            candidate = body.get("message")
            if isinstance(candidate, str):
                api_message = candidate.strip()
        detail = ": ".join(part for part in (reason_text, api_message) if part)
        return f"HTTP {exc.code}" + (f": {detail}" if detail else "")
    if isinstance(exc, URLError):
        reason_text = str(getattr(exc, "reason", "") or "").strip()
        if reason_text:
            return reason_text
    text = str(exc).strip()
    return text or exc.__class__.__name__


## @brief Fetch the raw latest GitHub release tag together with its failure reason.
# @details Performs exactly one HTTP GET against `GITHUB_LATEST_RELEASE_API`
#          (REQ-208), decodes the JSON payload, and returns the `tag_name`
#          field verbatim including any leading `v`, so the value can be
#          appended to `GITHUB_UPGRADE_SOURCE` as a git ref (REQ-209).
#          Every transport or payload failure is intercepted and converted
#          by `_github_failure_reason` into a non-empty English reason
#          (REQ-231); no diagnostic is emitted and no exception is raised,
#          keeping REQ-127 reporting at the caller boundary. Never mutates
#          the PyPI idle-time cache.
# @param timeout_seconds {float} Request timeout in seconds (REQ-125).
# @return {Tuple[Optional[str], Optional[str]]} `(tag_name, failure_reason)`;
#         `failure_reason` is None on success; `tag_name` is None on transport
#         or decode failure and empty string when the payload lacks a
#         `tag_name` field.
# @note Complexity: O(payload) for one HTTP GET plus one JSON decode.
# @satisfies REQ-208, REQ-231
def _fetch_github_release_tag_with_reason(
    timeout_seconds: float = VERSION_CHECK_TIMEOUT_SECONDS,
) -> Tuple[Optional[str], Optional[str]]:
    request = Request(
        GITHUB_LATEST_RELEASE_API,
        headers={
            "Accept": "application/json",
            "User-Agent": PYPI_PROJECT_NAME,
        },
        method="GET",
    )
    try:
        with urlopen(request, timeout=timeout_seconds) as response:
            payload_bytes = response.read()
    except HTTPError as exc:
        return None, _github_failure_reason(exc)
    except URLError as exc:
        return None, _github_failure_reason(exc)
    except TimeoutError:
        return None, "request timeout exceeded."
    except OSError as exc:
        return None, _github_failure_reason(exc)
    try:
        payload_text = (
            payload_bytes.decode("utf-8")
            if isinstance(payload_bytes, (bytes, bytearray))
            else str(payload_bytes)
        )
        data = json.loads(payload_text)
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
        return None, _github_failure_reason(exc)
    if not isinstance(data, dict):
        return "", None
    return str(data.get("tag_name") or ""), None


## @brief Fetch the raw latest GitHub release tag name for upgrade ref selection.
# @details Delegates transport, decoding, and reason derivation to
#          `_fetch_github_release_tag_with_reason` (REQ-208). On transport or
#          decode failure it prints the standardized bright-red update-check
#          diagnostic (REQ-127) carrying the REQ-231 failure reason and
#          returns None without raising; the fetch never mutates the PyPI
#          idle-time cache.
# @param timeout_seconds {float} Request timeout in seconds (REQ-125).
# @return {Optional[str]} Raw `tag_name` text; None on transport or decode
#         failure; empty string when the payload lacks a `tag_name` field.
# @see _fetch_github_release_tag_with_reason, _github_failure_reason
# @satisfies REQ-208, REQ-127, REQ-231
def _fetch_github_latest_release_tag(
    timeout_seconds: float = VERSION_CHECK_TIMEOUT_SECONDS,
) -> Optional[str]:
    tag_name, failure_reason = _fetch_github_release_tag_with_reason(
        timeout_seconds=timeout_seconds
    )
    if tag_name is None:
        _print_update_check_error(failure_reason or "request failed.")
        return None
    return tag_name


## @brief Fetch the latest GitHub release version together with its failure reason.
# @details Delegates transport and payload decoding to
#          `_fetch_github_release_tag_with_reason` (REQ-204), strips one
#          leading `v` from the raw `tag_name`, and normalizes the result as
#          a semantic version. Failure paths print the standardized
#          bright-red update-check diagnostic (REQ-127) and return a
#          non-empty REQ-231 failure reason so `main` renders
#          `GitHub latest: unknown (<reason>)` (REQ-230); the fetch is
#          report-only (REQ-202) and never mutates the PyPI idle-time cache.
# @param timeout_seconds {float} Request timeout in seconds (REQ-125).
# @return {Tuple[Optional[str], Optional[str]]} `(version, failure_reason)`;
#         normalized latest GitHub release version with None reason on
#         success; None version with non-empty reason on any request,
#         payload, or semver failure.
# @note Complexity: O(payload) for one HTTP GET plus one JSON decode.
# @satisfies REQ-202, REQ-204, REQ-230, REQ-231
def _fetch_github_latest_version(
    timeout_seconds: float = VERSION_CHECK_TIMEOUT_SECONDS,
) -> Tuple[Optional[str], Optional[str]]:
    tag_name, failure_reason = _fetch_github_release_tag_with_reason(
        timeout_seconds=timeout_seconds
    )
    if tag_name is None:
        _print_update_check_error(failure_reason or "request failed.")
        return None, failure_reason
    if tag_name.startswith("v"):
        tag_name = tag_name[1:]
    latest_text = _normalize_semver_text(tag_name)
    if _parse_semver_tuple(latest_text) is None:
        reason = "invalid API payload: `tag_name` is not semantic version."
        _print_update_check_error(reason)
        return None, reason
    return latest_text, None


## @brief Execute `get_git_root` runtime logic for Git-Alias CLI.
# @details Executes `get_git_root` using deterministic CLI control-flow and explicit error propagation.
# @return Result emitted by `get_git_root` according to command contract.
def get_git_root():
    try:
        result = _run_checked(
            ["git", "rev-parse", "--show-toplevel"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        location = result.stdout.strip()
        if location:
            return Path(location)
    except CommandExecutionError:
        pass
    return Path.cwd()


## @brief Execute `get_config_path` runtime logic for Git-Alias CLI.
# @details Executes `get_config_path` using deterministic CLI control-flow and explicit error propagation.
# @param root Input parameter consumed by `get_config_path`.
# @return Result emitted by `get_config_path` according to command contract.
def get_config_path(root=None):
    base = Path(root) if root is not None else get_git_root()
    return base / CONFIG_FILENAME


## @brief Execute `get_global_config_path` runtime logic for Git-Alias CLI.
# @details Executes `get_global_config_path` using deterministic CLI control-flow and explicit error propagation.
# @param home Input parameter consumed by `get_global_config_path`.
# @return Result emitted by `get_global_config_path` according to command contract.
def get_global_config_path(home=None):
    base = Path(home).expanduser() if home is not None else Path.home()
    return base / GLOBAL_CONFIG_DIRECTORY / GLOBAL_CONFIG_FILENAME


## @brief Execute `_read_config_object` runtime logic for Git-Alias CLI.
# @details Executes `_read_config_object` using deterministic CLI control-flow and explicit error propagation.
# @param config_path Input parameter consumed by `_read_config_object`.
# @return Result emitted by `_read_config_object` according to command contract.
def _read_config_object(config_path):
    if not config_path.exists():
        return {}
    try:
        raw_text = config_path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        print(f"Unable to read {config_path}: {exc}", file=sys.stderr)
        return None
    try:
        data = json.loads(raw_text)
    except json.JSONDecodeError as exc:
        print(f"Unable to parse {config_path} as JSON: {exc}", file=sys.stderr)
        return None
    if not isinstance(data, dict):
        print(f"Ignoring {config_path}: expected a JSON object.", file=sys.stderr)
        return None
    return data


## @brief Apply schema-validated values to the flat alias configuration.
# @details O(N) validation; invalid values leave defaults active and emit
# diagnostics. Version-rule entry filtering remains in _load_config_rules.
# @param data {dict[str, Any]} Decoded configuration object.
# @param keys {tuple[str, ...]} Allowed scope key inventory.
# @return {None} Mutates CONFIG; never writes files.
# @satisfies DES-006, REQ-097, REQ-188, REQ-190, REQ-242
def _apply_config_values(data, keys):
    fields = configuration.SCHEMA["Global"].fields | configuration.SCHEMA["Local"].fields
    for key in keys:
        if key not in data:
            continue
        value = data[key]
        if key == "ver_rules" and isinstance(value, list):
            CONFIG[key] = value
            continue
        try:
            CONFIG[key] = configuration.validate(value, fields[key], key)
        except ValueError as exc:
            print(f"Ignoring {key}: {exc}", file=sys.stderr)


## @brief Execute `load_cli_config` runtime logic for Git-Alias CLI.
# @details Executes `load_cli_config` using deterministic CLI control-flow and explicit error propagation.
# @param root Input parameter consumed by `load_cli_config`.
# @param home Input parameter consumed by `load_cli_config`.
# @return Result emitted by `load_cli_config` according to command contract.
def load_cli_config(root=None, home=None):
    CONFIG.update(DEFAULT_CONFIG)
    global_config_path = get_global_config_path(home)
    global_data = _read_config_object(global_config_path)
    if global_data is not None:
        _apply_config_values(global_data, GLOBAL_CONFIG_KEYS)
    config_path = get_config_path(root)
    local_data = _read_config_object(config_path)
    if local_data is not None:
        _apply_config_values(local_data, LOCAL_CONFIG_KEYS)
    return config_path


## @brief Parse one configured launcher command line into argv tokens.
# @details Applies shell-like tokenization to the configured command line,
# rejects malformed quoting, and rejects empty argv sequences before process
# execution dispatch.
# @param command_line `str` — configured launcher command line.
# @param config_key `str` — configuration key used in error messages.
# @return `List[str]` — parsed argv tokens.
# @exception RuntimeError Raised when the configured command line is invalid or empty.
# @satisfies REQ-156, REQ-159
def _parse_config_command_parts(command_line: str, config_key: str) -> List[str]:
    try:
        parts = shlex.split(command_line)
    except ValueError as exc:
        raise RuntimeError(
            f"Configured {config_key} command is invalid: {exc}"
        ) from None
    if not parts:
        raise RuntimeError(f"Configured {config_key} command is empty.")
    return parts


## @brief Resolve non-PATHEXT Windows shell-script launcher paths.
# @details Searches the configured `PATH` for an exact filename match when the
# launcher is a Git Bash style script such as `gitk` with no executable
# extension. This bypasses `shutil.which(...)` limitations on Windows for
# shell-script launchers not covered by `PATHEXT`.
# @param executable `str` — configured launcher token before argument parsing.
# @return `Optional[str]` — POSIX-normalized script path when found; otherwise `None`.
# @satisfies CTN-002
def _find_windows_shell_script_path(executable: str) -> Optional[str]:
    if os.name != "nt":
        return None
    separators = tuple(
        separator
        for separator in (os.sep, os.altsep, "/", "\\")
        if separator
    )
    if any(separator in executable for separator in separators):
        candidates = [executable]
    else:
        path_value = os.getenv("PATH", "")
        candidates = [
            os.path.join(directory, executable)
            for directory in path_value.split(os.pathsep)
            if directory
        ]
    for candidate in candidates:
        normalized_candidate = os.path.normpath(candidate)
        if os.path.isfile(normalized_candidate):
            return Path(normalized_candidate).as_posix()
    return None


## @brief Resolve a runnable Windows shell-script launcher prefix.
# @details Converts Git Bash style PATH entries such as `gitk` into a subprocess
# argv prefix executable by Python on Windows. When a shell-script launcher is
# detected, the command is executed through `sh` or `bash` so `subprocess.run`
# does not fail with native Win32 executable lookup errors.
# @param executable `str` — configured launcher token before argument parsing.
# @return `Optional[List[str]]` — argv prefix `[shell_path, script_path]` when a
# Windows shell-script launcher is available; otherwise `None`.
# @satisfies CTN-002
def _resolve_windows_shell_command_prefix(executable: str) -> Optional[List[str]]:
    script_path = _find_windows_shell_script_path(executable)
    if script_path is None:
        return None
    shell_path = shutil.which("sh") or shutil.which("bash")
    if shell_path is None:
        return None
    return [shell_path, script_path]


## @brief Validate configured launcher executable availability.
# @details Resolves the first argv token against the current-platform PATH
# lookup rules and aborts command execution when the executable is unavailable.
# On Windows, Git Bash shell-script launchers without executable extensions are
# executed through `sh`/`bash` when present in `PATH`.
# @param key `str` — configuration key containing the launcher command line.
# @param default_command `str` — fallback command line when config is empty.
# @return `List[str]` — validated argv tokens ready for subprocess execution.
# @exception RuntimeError Raised when the configured command is invalid or the executable is unavailable.
# @satisfies CTN-002, REQ-157, REQ-159
def _validated_config_command_parts(key: str, default_command: str) -> List[str]:
    raw_value = get_config_value(key) or default_command
    parts = _parse_config_command_parts(raw_value, key)
    executable = parts[0]
    if shutil.which(executable) is not None:
        return parts
    shell_prefix = _resolve_windows_shell_command_prefix(executable)
    if shell_prefix is not None:
        return shell_prefix + parts[1:]
    raise RuntimeError(
        f"Configured {key} executable '{executable}' is not available on this system."
    )


## @brief Detect whether the current execution environment is graphical.
# @details Implements the REQ-187 environment classification: non-POSIX
#          platforms are graphical desktop sessions; POSIX platforms are
#          graphical only when `DISPLAY` or `WAYLAND_DISPLAY` is set non-empty.
# @return `bool` True for graphical environments; False for terminal environments.
# @note Complexity: O(1) environment inspection; no subprocess execution.
# @satisfies REQ-187
def _is_graphical_environment() -> bool:
    if os.name != "posix":
        return True
    return bool(os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY"))


## @brief Resolve the environment-selected variant of a paired external command.
# @details Implements REQ-186/REQ-187/REQ-188 dual-command resolution:
#          graphical environments select `<command_key>_gfx` when its configured
#          value is non-empty; every other case uses `<command_key`; empty or
#          absent `_gfx` values fall back to the terminal command. The selected
#          command line is validated through `_validated_config_command_parts`.
# @param command_key {str} Terminal command configuration key (e.g. `gp_command`).
# @param default_command {str} Fallback command line when the key value is empty.
# @return {List[str]} Validated argv tokens of the environment-selected command.
# @exception RuntimeError Raised when the selected command is invalid or unavailable.
# @note Complexity: O(1) excluding PATH lookup inside validation.
# @satisfies REQ-186, REQ-187, REQ-188
def _environment_config_command_parts(
    command_key: str, default_command: str
) -> List[str]:
    if _is_graphical_environment():
        gfx_value = get_config_value(f"{command_key}_gfx")
        if gfx_value:
            return _validated_config_command_parts(
                f"{command_key}_gfx", gfx_value
            )
    return _validated_config_command_parts(command_key, default_command)


## @brief Resolve the editor launcher command after executable validation.
# @details Returns the environment-selected validated editor argv sequence used
#          by the `ed` alias, choosing `edit_command_gfx` in graphical
#          environments per REQ-187/REQ-188.
# @return `List[str] — validated editor argv tokens.
# @exception RuntimeError Raised when the selected editor command is invalid or unavailable.
# @satisfies REQ-156, REQ-157, REQ-159, REQ-187
def _editor_base_command() -> List[str]:
    return _environment_config_command_parts(
        "edit_command", DEFAULT_CONFIG["edit_command"]
    )


## @brief Execute `run_editor_command` runtime logic for Git-Alias CLI.
# @details Executes `run_editor_command` using deterministic CLI control-flow and explicit error propagation.
# @param args Input parameter consumed by `run_editor_command`.
# @return Result emitted by `run_editor_command` according to command contract.
# @exception RuntimeError Raised when the configured editor launcher is invalid or unavailable.
# @satisfies REQ-158, REQ-159
def run_editor_command(args):
    return run_command(_editor_base_command() + list(args))


## @brief Resolve configured graph launcher command parts after validation.
# @details Normalizes the configured command line, selects the environment
#          variant (`<key>_gfx` in graphical environments per REQ-187/REQ-188),
#          validates the executable on the current platform, and returns argv
#          tokens without fallback execution.
# @param key Input parameter consumed by `_config_command_parts`.
# @param default_command Input parameter consumed by `_config_command_parts`.
# @return Result emitted by `_config_command_parts` according to command contract.
# @exception RuntimeError Raised when the configured launcher is invalid or unavailable.
# @satisfies REQ-156, REQ-157, REQ-159, REQ-187
def _config_command_parts(key: str, default_command: str) -> List[str]:
    return _environment_config_command_parts(key, default_command)


## @brief Constant `HELP_TEXTS` used by CLI runtime paths and policies.

HELP_TEXTS = {
    "aa": "Add all file changes to the stage area for commit.",
    "ar": "Archive the configured master branch as tar.gz file named after the latest tag.",
    "bd": "Delete a local branch, or the associated worktree plus branch when paired. Syntax: git bd [--force] <branch>.",
    "br": "Print or create branches (native git branch).",
    "backup": "Merge configured work into develop and push develop to origin (shared release preflight checks).",
    "chver": "Change the project version to the provided semantic version.",
    "changelog": "Generate CHANGELOG.md grouped by minor releases. Options: --include-patch, --force-write, --print-only, --disable-history.",
    "ck": "Check for conflict markers and whitespace errors (git diff --check).",
    "cm": "Standard commit with staging/worktree validation: git cm '<message>'.",
    "co": "Checkout a specific branch: git co '<branch>'.",
    "dc": "Run git difftool -d from <ref_prev> to <ref>, overriding the diff tool with the configured diff_command/diff_command_gfx. Syntax: git dc <ref> [<ref_prev>]; <ref_prev> defaults to the commit preceding <ref> (<ref>~1).",
    "dcc": "Run git difftool -d between HEAD~1 and HEAD with the configured diff tool override (--extcmd).",
    "dccc": "Run git difftool -d between HEAD~2 and HEAD with the configured diff tool override (--extcmd).",
    "de": "Print the nearest tag reachable from a ref (git describe).",
    "di": "Discard current changes on file: git di '<filename>'",
    "dime": "Discard merge changes in favor of their files.",
    "diyou": "Discard merge changes in favor of your files.",
    "dw": "Run git difftool -d between working tree and a specific ref with the configured diff tool override. Syntax: git dw <ref>.",
    "dwc": "Run git difftool -d between working tree and HEAD with the configured diff tool override (--extcmd).",
    "dwcc": "Run git difftool -d between working tree and HEAD~1 with the configured diff tool override (--extcmd).",
    "dcd": "Run git difftool -d between configured develop and work branches with the configured diff tool override.",
    "dcm": "Run git difftool -d between configured master and work branches with the configured diff tool override.",
    "ddm": "Run git difftool -d between configured master and develop branches with the configured diff tool override.",
    "ed": "Edit a file. Syntax: git ed <filename>.",
    "fe": "Fetch new data of current branch from origin.",
    "feall": "Fetch from all remotes with tags and prune stale references (git fetch --all --tags --prune).",
    "get": "Fast-forward local master and develop from origin (with tags) and fast-forward merge develop into the current work branch after preflight checks.",
    "gp": "Open git commits graph using the configured gp_command.",
    "gr": "Open git tags graph using the configured gr_command.",
    "l": "Print commit history as a text-based tree. Options: --all, --no-color, --no-status, --reverse, --wrap, --abbrev=<n>, --svdepth=<n>, --style=<n>, --graph-margin-left=<n>, --graph-margin-right=<n>, --graph-symbol-commit=<s>, --graph-symbol-merge=<s>, --graph-symbol-overpass=<s>, --graph-symbol-root=<s>, --graph-symbol-tip=<s>.",
    "lb": "Print all branches.",
    "lg": "Print commit history.",
    "lh": "Print last commit details.",
    "ll": "Print commit history graph with full commit hashes.",
    "lm": "Print all merges.",
    "ls": "List tracked files using git ls-files.",
    "lsi": "List ignored files using git ls-files. Options: --include-all (show all, skip default directory filter).",
    "lsa": "List untracked files using git ls-files.",
    "lt": "Print tags with containing branches.",
    "major": "Release a new major version from the work branch. Options: --include-patch, --dev/--develop (limit the release to the configured develop branch: merge work into develop, tag there, and atomically push develop with the release tag only; master stays unchanged), build_script and pre_release_check (local .galias.conf keys: build_script runs after the version update and before the release commit; pre_release_check runs first; both abort the release on a non-zero exit and are skipped when empty). Alternatively use --resume alone or with --dev/--develop to validate and publish an already prepared local release without bumping, amending, or recreating its tag; completed publication is a no-op. Note: here --dev/--develop mean develop-scoped release, not the --upgrade GitHub-install option.",
    "minor": "Release a new minor version from the work branch. Options: --include-patch, --dev/--develop (limit the release to the configured develop branch: merge work into develop, tag there, and atomically push develop with the release tag only; master stays unchanged), build_script and pre_release_check (local .galias.conf keys: build_script runs after the version update and before the release commit; pre_release_check runs first; both abort the release on a non-zero exit and are skipped when empty). Alternatively use --resume alone or with --dev/--develop to validate and publish an already prepared local release without bumping, amending, or recreating its tag; completed publication is a no-op. Note: here --dev/--develop mean develop-scoped release, not the --upgrade GitHub-install option.",
    "new": "Conventional commit new(<module>): <description>. Input: '<module>: <description>' or '<description>' (uses default_commit_module).",
    "o": "Print a verbose overview with status, branch distances, active worktrees, and a qualitative ASCII topology tree.",
    "implement": "Conventional commit implement(<module>): <description>. Input: '<module>: <description>' or '<description>' (uses default_commit_module).",
    "refactor": "Conventional commit refactor(<module>): <description>. Input: '<module>: <description>' or '<description>' (uses default_commit_module).",
    "fix": "Conventional commit fix(<module>): <description>. Input: '<module>: <description>' or '<description>' (uses default_commit_module).",
    "change": "Conventional commit change(<module>): <description>. Input: '<module>: <description>' or '<description>' (uses default_commit_module).",
    "docs": "Conventional commit docs(<module>): <description>. Input: '<module>: <description>' or '<description>' (uses default_commit_module).",
    "style": "Conventional commit style(<module>): <description>. Input: '<module>: <description>' or '<description>' (uses default_commit_module).",
    "revert": "Conventional commit revert(<module>): <description>. Input: '<module>: <description>' or '<description>' (uses default_commit_module).",
    "rollback": "Create rollback commit to a target commit or tag on current branch, preserving the current application version (runs a version pre-check and restores the version via chver before committing). Syntax: git rollback <commit-hash|tag>.",
    "misc": "Conventional commit misc(<module>): <description>. Input: '<module>: <description>' or '<description>' (uses default_commit_module).",
    "cover": "Conventional commit cover(<module>): <description>. Input: '<module>: <description>' or '<description>' (uses default_commit_module).",
    "me": "Merge with fast-forward only (git merge --ff-only).",
    "pl": "Pull (fetch + merge FETCH_HEAD) from origin on current branch.",
    "pt": "Push all new tags to origin.",
    "pu": "Push current branch to origin (add upstream (tracking) reference for pull).",
    "patch": "Release a new patch version from the work branch with the same master integration used by major/minor. Options: --include-patch (auto-included), --dev/--develop (limit the release to the configured develop branch: merge work into develop, tag there, and atomically push develop with the release tag only; master stays unchanged), build_script and pre_release_check (local .galias.conf keys: build_script runs after the version update and before the release commit; pre_release_check runs first; both abort the release on a non-zero exit and are skipped when empty). Alternatively use --resume alone or with --dev/--develop to validate and publish an already prepared local release without bumping, amending, or recreating its tag; completed publication is a no-op. Note: here --dev/--develop mean develop-scoped release, not the --upgrade GitHub-install option.",
    "ra": "Remove all staged files and return them to the working tree (inverse of aa).",
    "rf": "Print the HEAD reference log (git reflog).",
    "rmloc": "Remove changed files from the working tree.",
    "rmstg": "Remove staged files from index tree.",
    "rmtg": "Delete a tag locally and from origin. Syntax: git rmtg <tag>.",
    "rmunt": "Remove untracked files from the working tree.",
    "rs": "Reset current branch to HEAD (--hard).",
    "rshrd": "Hard reset alias (--hard).",
    "rskep": "Keep reset alias (--keep).",
    "rsmix": "Mixed reset alias (--mixed).",
    "rsmrg": "Merge reset alias (--merge).",
    "rssft": "Soft reset alias (--soft).",
    "st": "Print current GIT status.",
    "tg": "Create a new annotated tag. Syntax: git tg <description> <tag>.",
    "unstg": "Un-stage a file from commit: git unstg '<filename>'. Unstage all files with: git unstg *.",
    "wt": "Run native git worktree subcommands. Syntax: git wt [<git worktree args>].",
    "wtl": "List worktrees with optional verbosity/porcelain flags. Syntax: git wtl [-v|--porcelain [-z]] [args].",
    "wtp": "Prune stale worktree metadata. Syntax: git wtp [-n] [-v] [--expire <expire>] [args].",
    "wtd": "Delete a worktree, or the associated worktree plus branch when paired. Syntax: git wtd [--force] <worktree>.",
    "wip": "Commit work in progress with an automatic message and the same checks as cm.",
    "ver": "Verify version consistency across configured files. Options: --verbose, --debug.",
    "str": "Display all unique remotes and show detailed status for each.",
}

## @brief Constant `RESET_HELP` used by CLI runtime paths and policies.

RESET_HELP = """

 Reset commands help screen

 default mode = '--mixed'

 working - working tree
 index   - staging area ready to commit
 HEAD    - latest commit
 target  - example: origin/master

 working index HEAD target         working index HEAD
 ----------------------------------------------------
  A       B     C    D     --soft   A       B     D
                           --mixed  A       D     D
                           --hard   D       D     D
                           --merge  (disallowed)
                           --keep   (disallowed)

 working index HEAD target         working index HEAD
 ----------------------------------------------------
  A       B     C    C     --soft   A       B     C
                           --mixed  A       C     C
                           --hard   C       C     C
                           --merge  (disallowed)
                           --keep   A       C     C

 working index HEAD target         working index HEAD
 ----------------------------------------------------
  B       B     C    D     --soft   B       B     D
                           --mixed  B       D     D
                           --hard   D       D     D
                           --merge  D       D     D
                           --keep   (disallowed)

 working index HEAD target         working index HEAD
 ----------------------------------------------------
  B       B     C    C     --soft   B       B     C
                           --mixed  B       C     C
                           --hard   C       C     C
                           --merge  C       C     C
                           --keep   B       C     C

 working index HEAD target         working index HEAD
 ----------------------------------------------------
  B       C     C    D     --soft   B       C     D
                           --mixed  B       D     D
                           --hard   D       D     D
                           --merge  (disallowed)
                           --keep   (disallowed)

 working index HEAD target         working index HEAD
 ----------------------------------------------------
  B       C     C    C     --soft   B       C     C
                           --mixed  B       C     C
                           --hard   C       C     C
                           --merge  B       C     C
                           --keep   B       C     C

 The following tables show what happens when there are unmerged entries:
 X means any state and U means an unmerged index.

 working index HEAD target         working index HEAD
 ----------------------------------------------------
  X       U     A    B     --soft   (disallowed)
                           --mixed  X       B     B
                           --hard   B       B     B
                           --merge  B       B     B
                           --keep   (disallowed)

 working index HEAD target         working index HEAD
 ----------------------------------------------------
  X       U     A    A     --soft   (disallowed)
                           --mixed  X       A     A
                           --hard   A       A     A
                           --merge  A       A     A
                           --keep   (disallowed)

"""

## @brief Constant `RESET_HELP_COMMANDS` used by CLI runtime paths and policies.

RESET_HELP_COMMANDS = {"rs", "rshrd", "rskep", "rsmix", "rsmrg", "rssft"}

## @brief Default directory/file names excluded from `lsi` output.
# @details Immutable set of path-component names that `cmd_lsi` filters out
# by default via exact-match. Filtering is bypassed when `--include-all` is passed.
# @satisfies REQ-120
LSI_DEFAULT_EXCLUDED_DIRS = frozenset(
    {
        ".cache",
        ".claude",
        ".codex",
        ".eslintcache",
        ".gemini",
        ".git",
        ".github",
        ".kiro",
        ".mypy_cache",
        ".npm",
        ".opencode",
        ".parcel-cache",
        ".pytest_cache",
        ".ruff_cache",
        ".sass-cache",
        ".terragrunt-cache",
        ".tox",
        ".venv",
        ".vscode",
        "__pycache__",
        "build",
        "dist",
        "htmlcov",
        "node_modules",
        "temp",
        "tmp",
        "venv",
    }
)

## @brief Default directory-name suffixes excluded from `lsi` output.
# @details Tuple of suffix strings that `cmd_lsi` uses for suffix-match filtering
# on each path component. A path component ending with any suffix in this tuple
# is excluded. Filtering is bypassed when `--include-all` is passed.
# @satisfies REQ-122
LSI_DEFAULT_EXCLUDED_DIR_SUFFIXES = (".egg-info",)


## @brief Execute `_to_args` runtime logic for Git-Alias CLI.
# @details Executes `_to_args` using deterministic CLI control-flow and explicit error propagation.
# @param extra Input parameter consumed by `_to_args`.
# @return Result emitted by `_to_args` according to command contract.
def _to_args(extra):
    return list(extra) if extra else []


## @brief Class `CommandExecutionError` models a typed runtime container/error boundary.
# @details Captures subprocess execution metadata and exposes normalized human-readable failure text.
class CommandExecutionError(RuntimeError):
    ## @brief Execute `__init__` runtime logic for Git-Alias CLI.
    # @param self Input parameter consumed by `__init__`.
    # @param exc Input parameter consumed by `__init__`.
    # @return Result emitted by `__init__` according to command contract.
    def __init__(self, exc: subprocess.CalledProcessError):
        self.cmd = exc.cmd
        self.returncode = exc.returncode
        self.stdout = exc.stdout
        self.stderr = exc.stderr
        message = self._format_message()
        super().__init__(message)

    ## @brief Execute `_format_message` runtime logic for Git-Alias CLI.
    # @param self Input parameter consumed by `_format_message`.
    # @return Result emitted by `_format_message` according to command contract.
    def _format_message(self) -> str:
        text = self._decode_stream(self.stderr).strip()
        if text:
            return text
        cmd_display = ""
        if isinstance(self.cmd, (list, tuple)):
            cmd_display = " ".join(str(part) for part in self.cmd)
        elif self.cmd:
            cmd_display = str(self.cmd)
        return f"Command '{cmd_display}' failed with exit code {self.returncode}"

    @staticmethod
    ## @brief Execute `_decode_stream` runtime logic for Git-Alias CLI.
    # @param data Input parameter consumed by `_decode_stream`.
    # @return Result emitted by `_decode_stream` according to command contract.
    def _decode_stream(data) -> str:
        if data is None:
            return ""
        if isinstance(data, bytes):
            try:
                return data.decode("utf-8")
            except UnicodeDecodeError:
                return data.decode("utf-8", errors="replace")
        return str(data)


## @brief Execute `_run_checked` runtime logic for Git-Alias CLI.
# @details Single external-command interception point (REQ-185): every external
#          process spawned by `core.py` executes through this wrapper. Default
#          mode runs `subprocess.run` with `check=True` and converts
#          `CalledProcessError` into `CommandExecutionError`; `stream=True` mode
#          returns a `subprocess.Popen` handle for streaming pipelines and
#          converts launch `OSError` into an explicit English `RuntimeError`.
# @param *popenargs Positional subprocess arguments (argv list plus extras).
# @param stream {bool} When True, spawn via `subprocess.Popen` for streaming use.
# @param **kwargs Forwarded subprocess keyword arguments (cwd, check, stdio).
# @return {Any} `CompletedProcess` in default mode; `Popen` handle in stream mode.
# @exception CommandExecutionError Raised in default mode on non-zero exit with check enabled.
# @exception RuntimeError Raised in stream mode when the process cannot launch.
# @satisfies REQ-185
def _run_checked(*popenargs, stream=False, **kwargs) -> Any:
    if stream:
        try:
            return subprocess.Popen(*popenargs, **kwargs)
        except OSError as exc:
            argv = popenargs[0] if popenargs else []
            raise RuntimeError(
                f"Unable to launch command: {' '.join(map(str, argv))}: {exc}"
            ) from None
    kwargs.setdefault("check", True)
    try:
        return subprocess.run(*popenargs, **kwargs)
    except subprocess.CalledProcessError as exc:
        raise CommandExecutionError(exc) from None


## @brief Class `VersionDetectionError` models a typed runtime container/error boundary.
# @details Represents deterministic failures encountered while resolving semantic versions from repository files.
class VersionDetectionError(RuntimeError):
    pass


## @brief Class `ReleaseError` models a typed runtime container/error boundary.
# @details Represents release-flow precondition or orchestration failures.
class ReleaseError(RuntimeError):
    pass


## @brief Execute `run_git_cmd` runtime logic for Git-Alias CLI.
# @details Executes `run_git_cmd` using deterministic CLI control-flow and explicit error propagation.
# @param base_args Input parameter consumed by `run_git_cmd`.
# @param extra Input parameter consumed by `run_git_cmd`.
# @param cwd Input parameter consumed by `run_git_cmd`.
# @param **kwargs Input parameter consumed by `run_git_cmd`.
# @return Result emitted by `run_git_cmd` according to command contract.
def run_git_cmd(base_args, extra=None, cwd=None, **kwargs):
    full = ["git"] + list(base_args) + _to_args(extra)
    return _run_checked(full, cwd=cwd, **kwargs)


## @brief Execute `capture_git_output` runtime logic for Git-Alias CLI.
# @details Executes `capture_git_output` using deterministic CLI control-flow and explicit error propagation.
# @param base_args Input parameter consumed by `capture_git_output`.
# @param cwd Input parameter consumed by `capture_git_output`.
# @return Result emitted by `capture_git_output` according to command contract.
def capture_git_output(base_args, cwd=None):
    result = _run_checked(
        ["git"] + list(base_args), cwd=cwd, stdout=subprocess.PIPE, text=True
    )
    return result.stdout.strip()


## @brief Execute `run_command` runtime logic for Git-Alias CLI.
# @details Executes `run_command` using deterministic CLI control-flow and explicit error propagation.
# @param cmd Input parameter consumed by `run_command`.
# @param cwd Input parameter consumed by `run_command`.
# @return Result emitted by `run_command` according to command contract.
def run_command(cmd, cwd=None):
    return _run_checked(cmd, cwd=cwd)


## @brief Execute `run_git_text` runtime logic for Git-Alias CLI.
# @details Executes `run_git_text` using deterministic CLI control-flow and explicit error propagation.
# @param args Input parameter consumed by `run_git_text`.
# @param cwd Input parameter consumed by `run_git_text`.
# @param check Input parameter consumed by `run_git_text`.
# @return Result emitted by `run_git_text` according to command contract.
def run_git_text(args, cwd=None, check=True):
    try:
        proc = _run_checked(
            ["git", *args],
            cwd=cwd,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=check,
        )
    except CommandExecutionError as exc:
        message = CommandExecutionError._decode_stream(exc.stderr).strip()
        if not message:
            message = f"git {' '.join(args)} failed"
        raise RuntimeError(message) from None
    return proc.stdout.strip()


## @brief Execute `run_shell` runtime logic for Git-Alias CLI.
# @details Executes `run_shell` using deterministic CLI control-flow and explicit error propagation.
# @param command Input parameter consumed by `run_shell`.
# @param cwd Input parameter consumed by `run_shell`.
# @return Result emitted by `run_shell` according to command contract.
def run_shell(command, cwd=None):
    return _run_checked(command, shell=True, cwd=cwd)


## @brief Execute `_git_status_lines` runtime logic for Git-Alias CLI.
# @details Executes `_git_status_lines` using deterministic CLI control-flow and explicit error propagation.
# @return Result emitted by `_git_status_lines` according to command contract.
def _git_status_lines():
    proc = _run_checked(
        ["git", "status", "--porcelain"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=False,
    )
    if proc.returncode != 0:
        return []
    return proc.stdout.splitlines()


## @brief Execute `has_unstaged_changes` runtime logic for Git-Alias CLI.
# @details Executes `has_unstaged_changes` using deterministic CLI control-flow and explicit error propagation.
# @param status_lines Input parameter consumed by `has_unstaged_changes`.
# @return Result emitted by `has_unstaged_changes` according to command contract.
def has_unstaged_changes(status_lines=None):
    lines = status_lines if status_lines is not None else _git_status_lines()
    for line in lines:
        if not line:
            continue
        if line.startswith("??"):
            return True
        if len(line) > 1 and line[1] != " ":
            return True
    return False


## @brief Execute `has_staged_changes` runtime logic for Git-Alias CLI.
# @details Executes `has_staged_changes` using deterministic CLI control-flow and explicit error propagation.
# @param status_lines Input parameter consumed by `has_staged_changes`.
# @return Result emitted by `has_staged_changes` according to command contract.
def has_staged_changes(status_lines=None):
    lines = status_lines if status_lines is not None else _git_status_lines()
    for line in lines:
        if not line or line.startswith("??"):
            continue
        if line[0] != " ":
            return True
    return False


## @brief Constant `_REMOTE_REFS_UPDATED` used by CLI runtime paths and policies.

_REMOTE_REFS_UPDATED = False
## @brief Constant `WIP_MESSAGE_RE` used by CLI runtime paths and policies.

WIP_MESSAGE_RE = re.compile(r"^wip: work in progress\.$")


## @brief Refresh remote-tracking references for the configured `origin` remote.
# @details Executes `git remote update origin` scoped to the single configured
#          remote instead of updating every configured remote (`git remote -v update`
#          updated all remotes and failed whenever any unrelated remote was
#          unreachable). Success is cached in `_REMOTE_REFS_UPDATED` so the fetch
#          runs at most once per CLI invocation; failure prints a non-fatal English
#          warning and leaves the cache unset so tolerant callers may retry.
# @return {bool} True when `origin` references were refreshed; False when the
#         update command failed (callers enforcing remote-state prerequisites
#         MUST treat False as fatal).
# @exception None; failures are reported via the boolean result and a stderr warning.
# @satisfies REQ-020
def _refresh_remote_refs():
    global _REMOTE_REFS_UPDATED
    if _REMOTE_REFS_UPDATED:
        return True
    try:
        run_git_cmd(["remote", "update", "origin"])
    except CommandExecutionError as exc:
        print(f"Unable to update remote references: {exc}", file=sys.stderr)
        return False
    _REMOTE_REFS_UPDATED = True
    return True


## @brief Execute `_branch_remote_divergence` runtime logic for Git-Alias CLI.
# @details Executes `_branch_remote_divergence` using deterministic CLI control-flow and explicit error propagation.
# @param branch_key Input parameter consumed by `_branch_remote_divergence`.
# @param remote Input parameter consumed by `_branch_remote_divergence`.
# @return Result emitted by `_branch_remote_divergence` according to command contract.
def _branch_remote_divergence(branch_key, remote="origin"):
    _refresh_remote_refs()
    branch = get_branch(branch_key)
    upstream = f"{remote}/{branch}"
    try:
        counts = run_git_text(
            ["rev-list", "--left-right", "--count", f"{branch}...{upstream}"]
        )
    except RuntimeError:
        return (0, 0)
    parts = counts.strip().split()
    if len(parts) < 2:
        return (0, 0)
    try:
        local_ahead = int(parts[0])
        remote_ahead = int(parts[1])
    except ValueError:
        return (0, 0)
    return (local_ahead, remote_ahead)


## @brief Execute `has_remote_branch_updates` runtime logic for Git-Alias CLI.
# @details Executes `has_remote_branch_updates` using deterministic CLI control-flow and explicit error propagation.
# @param branch_key Input parameter consumed by `has_remote_branch_updates`.
# @param remote Input parameter consumed by `has_remote_branch_updates`.
# @return Result emitted by `has_remote_branch_updates` according to command contract.
def has_remote_branch_updates(branch_key, remote="origin"):
    _, remote_ahead = _branch_remote_divergence(branch_key, remote=remote)
    return remote_ahead > 0


## @brief Execute `has_remote_develop_updates` runtime logic for Git-Alias CLI.
# @details Executes `has_remote_develop_updates` using deterministic CLI control-flow and explicit error propagation.
# @return Result emitted by `has_remote_develop_updates` according to command contract.
def has_remote_develop_updates():
    return has_remote_branch_updates("develop")


## @brief Execute `has_remote_master_updates` runtime logic for Git-Alias CLI.
# @details Executes `has_remote_master_updates` using deterministic CLI control-flow and explicit error propagation.
# @return Result emitted by `has_remote_master_updates` according to command contract.
def has_remote_master_updates():
    return has_remote_branch_updates("master")


## @brief Execute `_head_commit_message` runtime logic for Git-Alias CLI.
# @details Executes `_head_commit_message` using deterministic CLI control-flow and explicit error propagation.
# @return Result emitted by `_head_commit_message` according to command contract.
def _head_commit_message():
    try:
        return run_git_text(["log", "-1", "--pretty=%s"]).strip()
    except RuntimeError:
        return ""


## @brief Execute `_head_commit_hash` runtime logic for Git-Alias CLI.
# @details Executes `_head_commit_hash` using deterministic CLI control-flow and explicit error propagation.
# @return Result emitted by `_head_commit_hash` according to command contract.
def _head_commit_hash():
    try:
        return run_git_text(["rev-parse", "HEAD"]).strip()
    except RuntimeError:
        return ""


## @brief Execute `_commit_exists_in_branch` runtime logic for Git-Alias CLI.
# @details Executes `_commit_exists_in_branch` using deterministic CLI control-flow and explicit error propagation.
# @param commit_hash Input parameter consumed by `_commit_exists_in_branch`.
# @param branch_name Input parameter consumed by `_commit_exists_in_branch`.
# @return Result emitted by `_commit_exists_in_branch` according to command contract.
def _commit_exists_in_branch(commit_hash, branch_name):
    if not commit_hash or not branch_name:
        return False
    proc = _run_checked(
        ["git", "merge-base", "--is-ancestor", commit_hash, branch_name],
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    return proc.returncode == 0


## @brief Execute `_should_amend_existing_commit` runtime logic for Git-Alias CLI.
# @details Executes `_should_amend_existing_commit` using deterministic CLI control-flow and explicit error propagation.
# @return Result emitted by `_should_amend_existing_commit` according to command contract.
def _should_amend_existing_commit():
    message = _head_commit_message()
    if not (message and WIP_MESSAGE_RE.match(message)):
        return (False, "HEAD is not a WIP commit.")
    commit_hash = _head_commit_hash()
    if not commit_hash:
        return (False, "Unable to determine the HEAD commit hash.")
    develop_branch = get_branch("develop")
    master_branch = get_branch("master")
    if _commit_exists_in_branch(commit_hash, develop_branch):
        return (False, f"The last WIP commit is already contained in {develop_branch}.")
    if _commit_exists_in_branch(commit_hash, master_branch):
        return (False, f"The last WIP commit is already contained in {master_branch}.")
    return (True, "HEAD WIP commit is still pending locally.")


## @brief Execute `is_inside_git_repo` runtime logic for Git-Alias CLI.
# @details Executes `is_inside_git_repo` using deterministic CLI control-flow and explicit error propagation.
# @return Result emitted by `is_inside_git_repo` according to command contract.
def is_inside_git_repo():
    try:
        output = run_git_text(["rev-parse", "--is-inside-work-tree"])
    except RuntimeError:
        return False
    return output.strip().lower() == "true"


@dataclass
## @brief Class `TagInfo` models a typed runtime container/error boundary.
# @details Encapsulates tag identity, tag date, and resolved Git object identifier for changelog assembly.

class TagInfo:
    ## @brief Store raw tag name including `v` prefix when present.
    name: str
    ## @brief Store ISO date string used for changelog section headers.
    iso_date: str
    ## @brief Store object hash associated with the tag reference.
    object_name: str


@dataclass(frozen=True)
## @brief Class `WorktreeInfo` models parsed worktree-to-branch association data.
# @details Encapsulates a normalized absolute worktree path and its optional local branch binding
#          as derived from `git worktree list --porcelain` output.
class WorktreeInfo:
    ## @brief Store normalized absolute worktree path.
    path: Path
    ## @brief Store associated local branch name or `None` for detached worktrees.
    branch_name: Optional[str]


## @brief Constant `DELIM` used by CLI runtime paths and policies.

DELIM = "\x1f"
## @brief Constant `RECORD` used by CLI runtime paths and policies.

RECORD = "\x1e"
## @brief Constant `_CONVENTIONAL_RE` used by CLI runtime paths and policies.

_CONVENTIONAL_RE = re.compile(
    r"^(?P<type>new|fix|change|implement|refactor|docs|style|revert|misc|cover)"
    r"(?:\((?P<scope>[^)\r\n]+)\))?(?P<breaking>!)?:\s+(?P<desc>.+)$",
    re.IGNORECASE | re.DOTALL,
)
## @brief Constant `_MODULE_PREFIX_RE` used by CLI runtime paths and policies.

_MODULE_PREFIX_RE = re.compile(r"^(?P<module>[A-Za-z0-9_]+):\s*(?P<body>.*)$")
## @brief Constant `_SEMVER_TAG_RE` used by CLI runtime paths and policies.

_SEMVER_TAG_RE = re.compile(r"^v(\d+)\.(\d+)\.(\d+)$")
## @brief Constant `SEMVER_RE` used by CLI runtime paths and policies.

SEMVER_RE = re.compile(r"^(\d+)\.(\d+)\.(\d+)$")
## @brief Constant `SECTION_EMOJI` used by CLI runtime paths and policies.

SECTION_EMOJI = {
    "Features": "⛰️",
    "Implementations": "🏗️",
    "Bug Fixes": "🐛",
    "Changes": "🚜",
    "Refactor": "✨",
    "Documentation": "📚",
    "Styling": "🎨",
    "Miscellaneous Tasks": "⚙️",
    "Revert": "◀️",
    "Cover Requirements": "🎯",
}


## @brief Execute `_tag_semver_tuple` runtime logic for Git-Alias CLI.
# @details Executes `_tag_semver_tuple` using deterministic CLI control-flow and explicit error propagation.
# @param tag_name Input parameter consumed by `_tag_semver_tuple`.
# @return Result emitted by `_tag_semver_tuple` according to command contract.
def _tag_semver_tuple(tag_name: str) -> Optional[Tuple[int, int, int]]:
    return _parse_semver_tuple(tag_name.lstrip("v"))


## @brief Execute `_latest_supported_tag_name` runtime logic for Git-Alias CLI.
# @details Executes `_latest_supported_tag_name` using deterministic CLI control-flow and explicit error propagation.
# @param tags Input parameter consumed by `_latest_supported_tag_name`.
# @return Result emitted by `_latest_supported_tag_name` according to command contract.
def _latest_supported_tag_name(tags: List[TagInfo]) -> Optional[str]:
    return tags[-1].name if tags else None


## @brief Predicate: tag is a minor release.
# @details Returns `True` when `tag_name` is a semver tag where `patch==0` AND `(major>=1 OR minor>=1)`,
#          i.e. version `>=0.1.0` with no patch component.
#          Patch releases (`patch>0`) and pre-0.1.0 tags (`0.0.x`) return `False`.
# @param tag_name Semver tag string, optionally prefixed with `v` (e.g. `v0.1.0`, `0.2.0`).
# @return `True` iff tag represents a minor release; `False` otherwise.
# @satisfies REQ-018, REQ-040
def _is_minor_release_tag(tag_name: str) -> bool:
    parts = _tag_semver_tuple(tag_name)
    if parts is None:
        return False
    major, minor, patch = parts
    return patch == 0 and (major >= 1 or minor >= 1)


## @brief Locate the chronologically latest patch tag after a given minor release.
# @details Scans `all_tags` (sorted chronologically, ascending) for tags that are NOT minor releases
#          and appear after `last_minor` in the list.  When `last_minor` is `None`, scans all tags.
#          Returns the last qualifying `TagInfo` (most recent), or `None` if no patch exists.
# @param all_tags  Full list of `TagInfo` sorted by date ascending (from `list_tags_sorted_by_date`).
# @param last_minor The last minor-release `TagInfo` to anchor the search; `None` means no minor exists.
# @return Most recent `TagInfo` that is not a minor release and appears after `last_minor`, or `None`.
# @satisfies REQ-040
def _latest_patch_tag_after(
    all_tags: List[TagInfo], last_minor: Optional[TagInfo]
) -> Optional[TagInfo]:
    if last_minor is None:
        candidates = all_tags
    else:
        idx = next(
            (i for i, t in enumerate(all_tags) if t.name == last_minor.name), None
        )
        candidates = all_tags[idx + 1 :] if idx is not None else []
    patch_tags = [t for t in candidates if not _is_minor_release_tag(t.name)]
    return patch_tags[-1] if patch_tags else None


## @brief Execute `list_tags_sorted_by_date` runtime logic for Git-Alias CLI.
# @details Executes `list_tags_sorted_by_date` using deterministic CLI control-flow and explicit error propagation.
# @param repo_root Input parameter consumed by `list_tags_sorted_by_date`.
# @param merged_ref Input parameter consumed by `list_tags_sorted_by_date`.
# @return Result emitted by `list_tags_sorted_by_date` according to command contract.
def list_tags_sorted_by_date(
    repo_root: Path, merged_ref: Optional[str] = None
) -> List[TagInfo]:
    fmt = f"%(refname:strip=2){DELIM}%(creatordate:short){DELIM}%(objectname)"
    args = ["for-each-ref", "--sort=creatordate", f"--format={fmt}"]
    if merged_ref:
        args.extend(["--merged", merged_ref])
    args.append("refs/tags")
    output = run_git_text(args, cwd=repo_root, check=False)
    if not output:
        return []
    tags: List[TagInfo] = []
    for line in output.splitlines():
        parts = line.split(DELIM)
        if len(parts) != 3:
            continue
        name, date_s, obj = parts
        if not _SEMVER_TAG_RE.match(name):
            continue
        tags.append(
            TagInfo(name=name, iso_date=date_s or "unknown-date", object_name=obj)
        )
    return tags


## @brief Execute `git_log_subjects` runtime logic for Git-Alias CLI.
# @details Executes `git_log_subjects` using deterministic CLI control-flow and explicit error propagation.
#          Reads full commit messages (subject + body) to preserve multiline conventional descriptions.
# @param repo_root Input parameter consumed by `git_log_subjects`.
# @param rev_range Input parameter consumed by `git_log_subjects`.
# @return Result emitted by `git_log_subjects` according to command contract.
def git_log_subjects(repo_root: Path, rev_range: str) -> List[str]:
    fmt = f"%B{RECORD}"
    out = run_git_text(
        ["log", "--no-merges", f"--pretty=format:{fmt}", rev_range],
        cwd=repo_root,
        check=False,
    )
    if not out:
        return []
    return [x.strip() for x in out.split(RECORD) if x.strip()]


## @brief Execute `parse_conventional_commit` runtime logic for Git-Alias CLI.
# @details Parses a conventional-commit header with optional scope and optional breaking marker (`!`),
#          then returns extracted type/scope/breaking/description fields for changelog rendering.
# @param message Raw commit message text (subject and optional body).
# @return Tuple `(type, scope, breaking, description)` when message is parseable; otherwise `None`.
def parse_conventional_commit(
    message: str,
) -> Optional[Tuple[str, Optional[str], bool, str]]:
    match = _CONVENTIONAL_RE.match(message.strip())
    if not match:
        return None
    ctype = match.group("type").lower()
    scope = match.group("scope")
    breaking = bool(match.group("breaking"))
    desc = match.group("desc").strip()
    if not desc:
        return None
    return (ctype, scope, breaking, desc)


## @brief Normalize a commit description for readable changelog entry rendering.
# @details Removes `Co-authored-by:` trailer lines (REQ-044), drops empty lines (REQ-044),
#          and trims surrounding whitespace on every line. The first line is kept verbatim.
#          From the second line on, non-bullet lines are preserved verbatim (REQ-232); every
#          line starting with a markdown bullet marker (`-`, `*`, `+`, `1.`, `1)` plus
#          whitespace) has its marker stripped (REQ-234), and each maximal run of
#          consecutive bullet items is collapsed into one line whose item texts are
#          joined by `'; '` (REQ-235) so multiline commit text stays readable inside
#          the changelog top-level bullet.
# @param desc {str} Parsed commit description text (subject remainder plus body).
# @return {List[str]} Ordered non-empty rendered description lines; no continuation
#         line carries a leading markdown bullet marker.
# @note Complexity: O(L) where L is the number of description lines.
# @note A lone bullet marker without trailing whitespace does not match the marker
#       regex and is treated as non-bullet text.
# @see categorize_commit
# @satisfies REQ-044, REQ-232, REQ-234, REQ-235
def _format_changelog_description(desc: str) -> List[str]:
    lines = [line.strip() for line in desc.strip().splitlines()]
    filtered_lines = [
        line for line in lines if not re.match(r"^Co-authored-by:.*$", line)
    ]
    cleaned_lines = [line for line in filtered_lines if line]
    if not cleaned_lines:
        return []
    rendered_lines = [cleaned_lines[0]]
    bullet_items = []
    for line in cleaned_lines[1:]:
        marker = re.match(r"^(?:[-*+]|\d+[.)])\s+", line)
        if marker:
            bullet_items.append(line[marker.end():].strip())
            continue
        if bullet_items:
            rendered_lines.append("; ".join(bullet_items))
            bullet_items = []
        rendered_lines.append(line)
    if bullet_items:
        rendered_lines.append("; ".join(bullet_items))
    return rendered_lines


## @brief Map a conventional commit message to a changelog section and formatted entry.
# @details Parses the conventional header and renders one top-level bullet:
#          `- <description> *(<scope>)*` when scope is present, `- <description>`
#          otherwise (REQ-078). Cleaned description lines after the first are
#          indented by two spaces to align with the bullet text (REQ-232); markdown
#          bullet-marker runs are flattened into `'; '`-joined lines
#          (REQ-234, REQ-235); entry blocks
#          never carry blank separator lines because `generate_section_for_range`
#          appends entries contiguously (REQ-233). When the breaking marker is
#          present, the first description line is prefixed with `BREAKING CHANGE: `.
# @param subject {str} Conventional commit message string (subject plus optional body).
# @return {Tuple[Optional[str], str]} `(section, line)`: `section` is the changelog
#         section name or `None` if type is unmapped or ignored; `line` is the
#         formatted entry string or `""` when section is `None`.
# @note Complexity: O(L) where L is the number of description lines.
# @see _format_changelog_description, generate_section_for_range
# @satisfies REQ-078, REQ-232, REQ-233, REQ-234, REQ-235
def categorize_commit(subject: str) -> Tuple[Optional[str], str]:
    parsed = parse_conventional_commit(subject)
    if not parsed:
        return (None, "")
    ctype, scope, breaking, desc = parsed
    desc_lines = _format_changelog_description(desc)
    if not desc_lines:
        return (None, "")
    if breaking:
        desc_lines[0] = f"BREAKING CHANGE: {desc_lines[0]}"
    scope_text = f" *({scope})*" if scope else ""
    line = f"- {desc_lines[0]}{scope_text}"
    if len(desc_lines) > 1:
        line = "\n".join([line, *(f"  {detail}" for detail in desc_lines[1:])])
    mapping = {
        "new": "Features",
        "implement": "Implementations",
        "fix": "Bug Fixes",
        "change": "Changes",
        "cover": "Cover Requirements",
        "refactor": "Refactor",
        "docs": "Documentation",
        "style": "Styling",
        "revert": "Revert",
        "misc": "Miscellaneous Tasks",
    }
    section = mapping.get(ctype)
    return (section, line) if section else (None, "")


## @brief Execute `_extract_release_version` runtime logic for Git-Alias CLI.
# @details Executes `_extract_release_version` using deterministic CLI control-flow and explicit error propagation.
# @param subject Input parameter consumed by `_extract_release_version`.
# @return Result emitted by `_extract_release_version` according to command contract.
def _extract_release_version(subject: str) -> Optional[str]:
    match = re.match(
        r"\s*(?:release version:\s+|release:\s+release version\s+)(\d+\.\d+\.\d+)\s*$",
        subject,
        re.IGNORECASE,
    )
    if not match:
        return None
    return match.group(1)


## @brief Execute `_is_release_marker_commit` runtime logic for Git-Alias CLI.
# @details Executes `_is_release_marker_commit` using deterministic CLI control-flow and explicit error propagation.
# @param subject Input parameter consumed by `_is_release_marker_commit`.
# @return Result emitted by `_is_release_marker_commit` according to command contract.
def _is_release_marker_commit(subject: str) -> bool:
    return _extract_release_version(subject) is not None


## @brief Execute `generate_section_for_range` runtime logic for Git-Alias CLI.
# @details Executes `generate_section_for_range` using deterministic CLI control-flow and explicit error propagation.
# @param repo_root Input parameter consumed by `generate_section_for_range`.
# @param title Input parameter consumed by `generate_section_for_range`.
# @param date_s Input parameter consumed by `generate_section_for_range`.
# @param rev_range Input parameter consumed by `generate_section_for_range`.
# @param expected_version Input parameter consumed by `generate_section_for_range`.
# @return Result emitted by `generate_section_for_range` according to command contract.
def generate_section_for_range(
    repo_root: Path,
    title: str,
    date_s: str,
    rev_range: str,
    expected_version: Optional[str] = None,
) -> Optional[str]:
    subjects = git_log_subjects(repo_root, rev_range)
    buckets: Dict[str, List[str]] = defaultdict(list)
    for subj in subjects:
        if _is_release_marker_commit(subj):
            continue
        release_version = _extract_release_version(subj)
        if expected_version and release_version and release_version != expected_version:
            continue
        section, line = categorize_commit(subj)
        if section and line:
            buckets[section].append(line)
    if not any(buckets.values()):
        return None
    lines: List[str] = []
    lines.append(f"## {title} - {date_s}")
    order = [
        "Features",
        "Implementations",
        "Bug Fixes",
        "Changes",
        "Cover Requirements",
        "Refactor",
        "Documentation",
        "Styling",
        "Miscellaneous Tasks",
        "Revert",
    ]
    for sec in order:
        entries = buckets.get(sec, [])
        if entries:
            emoji = SECTION_EMOJI.get(sec, "")
            header = f"### {emoji}  {sec}".rstrip()
            lines.append(header)
            lines.extend(entries)
            lines.append("")
    return "\n".join(lines).rstrip() + "\n"


## @brief Resolve the git remote name configured for a given branch.
# @details Queries `git config branch.<branch_name>.remote` via a local git command.
#          Returns `origin` as fallback when the config key is absent or the command fails.
#          No network operations are performed.
# @param branch_name Local branch name whose configured remote is requested (e.g. `"master"`).
# @param repo_root Absolute path used as CWD for the git config query.
# @return Remote name string; never empty (falls back to `"origin"`).
# @satisfies REQ-046
def _get_remote_name_for_branch(branch_name: str, repo_root: Path) -> str:
    remote = run_git_text(
        ["config", "--get", f"branch.{branch_name}.remote"],
        cwd=repo_root,
        check=False,
    ).strip()
    return remote if remote else "origin"


## @brief Resolve the normalized HTTPS base URL from the master branch's configured remote.
# @details Parses both SSH (`git@<host>:<owner>/<repo>[.git]`) and HTTPS
#          (`https://<host>/<owner>/<repo>[.git]`) formats, plus URI-style SSH forms
#          (`ssh://git@<host>/<owner>/<repo>[.git]`, `git+ssh://...`), and extracts
#          `<owner>` and `<repo>` through deterministic string parsing.
# @param remote_url Raw git remote URL string.
# @return Tuple `(owner, repo)` when parsing succeeds; otherwise `None`.
def _extract_owner_repo(remote_url: str) -> Optional[Tuple[str, str]]:
    value = (remote_url or "").strip()
    if not value:
        return None
    if value.startswith("git@"):
        if ":" not in value:
            return None
        path_part = value.split(":", 1)[1]
    else:
        parsed = urlparse(value)
        if parsed.scheme not in {"http", "https", "ssh", "git+ssh"} or not parsed.netloc:
            return None
        path_part = parsed.path.lstrip("/")
    path_part = path_part.rstrip("/")
    if path_part.endswith(".git"):
        path_part = path_part[:-4]
    parts = [segment for segment in path_part.split("/") if segment]
    if len(parts) != 2:
        return None
    owner, repo = parts
    if not owner or not repo:
        return None
    return owner, repo


## @brief Resolve normalized GitHub URL base from the master-branch configured remote.
# @details Determines remote name using `_get_remote_name_for_branch` with the configured
#          master branch, then executes local `git remote get-url <remote>` command.
#          If command execution fails or URL parsing fails, returns `None`.
#          On success, always emits `https://github.com/<owner>/<repo>` for changelog templates.
#          No network operation is performed; all data is derived from local git metadata.
# @param repo_root Absolute path to the repository root used as CWD for all git commands.
# @return Normalized HTTPS base URL string (no trailing `.git`), or `None` on failure.
# @satisfies REQ-043, REQ-046
def _canonical_origin_base(repo_root: Path) -> Optional[str]:
    master_branch = get_branch("master")
    remote = _get_remote_name_for_branch(master_branch, repo_root)
    try:
        url = run_git_text(
            ["remote", "get-url", remote], cwd=repo_root, check=True
        ).strip()
    except RuntimeError:
        return None
    owner_repo = _extract_owner_repo(url)
    if owner_repo is None:
        return None
    owner, repo = owner_repo
    return f"https://github.com/{owner}/{repo}"


## @brief Execute `get_origin_compare_url` runtime logic for Git-Alias CLI.
# @details Executes `get_origin_compare_url` using deterministic CLI control-flow and explicit error propagation.
# @param base_url Input parameter consumed by `get_origin_compare_url`.
# @param prev_tag Input parameter consumed by `get_origin_compare_url`.
# @param tag Input parameter consumed by `get_origin_compare_url`.
# @return Result emitted by `get_origin_compare_url` according to command contract.
def get_origin_compare_url(
    base_url: Optional[str], prev_tag: Optional[str], tag: str
) -> Optional[str]:
    if not base_url:
        return None
    if prev_tag:
        return f"{base_url}/compare/{prev_tag}..{tag}"
    return f"{base_url}/releases/tag/{tag}"


## @brief Execute `get_release_page_url` runtime logic for Git-Alias CLI.
# @details Executes `get_release_page_url` using deterministic CLI control-flow and explicit error propagation.
# @param base_url Input parameter consumed by `get_release_page_url`.
# @param tag Input parameter consumed by `get_release_page_url`.
# @return Result emitted by `get_release_page_url` according to command contract.
def get_release_page_url(base_url: Optional[str], tag: str) -> Optional[str]:
    if not base_url:
        return None
    return f"{base_url}/releases/tag/{tag}"


## @brief Execute `build_history_section` runtime logic for Git-Alias CLI.
# @details Executes `build_history_section` using deterministic CLI control-flow and explicit error propagation.
# @param repo_root Input parameter consumed by `build_history_section`.
# @param tags Input parameter consumed by `build_history_section`.
# @param include_unreleased Input parameter consumed by `build_history_section`.
# @param include_unreleased_link Input parameter consumed by `build_history_section`.
# @return Result emitted by `build_history_section` according to command contract.
def build_history_section(
    repo_root: Path,
    tags: List[TagInfo],
    include_unreleased: bool,
    include_unreleased_link: bool = True,
) -> Optional[str]:
    base = _canonical_origin_base(repo_root)
    if not base:
        return None
    lines = ["# History"]
    visible_tags = tags
    if visible_tags:
        lines.append("")
        for tag in visible_tags:
            release_url = get_release_page_url(base, tag.name)
            if release_url:
                lines.append(f"- \\[{tag.name.lstrip('v')}\\]: {release_url}")
        lines.append("")
    prev: Optional[str] = None
    for tag in visible_tags:
        compare = get_origin_compare_url(base, prev, tag.name)
        if compare:
            lines.append(f"[{tag.name.lstrip('v')}]: {compare}")
        prev = tag.name
    if include_unreleased and include_unreleased_link:
        baseline = _latest_supported_tag_name(tags)
        if baseline:
            compare = get_origin_compare_url(base, baseline, "HEAD")
            if compare:
                lines.append(f"[unreleased]: {compare}")
    return "\n".join(lines).rstrip() + "\n"


## @brief Generate the full CHANGELOG.md document from repository tags and commits.
# @details Groups commits by minor release (semver where `patch=0` AND version `>=0.1.0`).
#          By default only minor releases appear; the document body is empty when none exist.
#          With `include_patch=True`, prepends the latest patch release after the last minor
#          (or the latest patch overall when no minor exists) including all commits in that range.
#          Releases are ordered reverse-chronologically in the output.
#          `# History` contains only the version tags present in the changelog body:
#          minor tags when `include_patch=False`; minor tags plus the latest patch when
#          `include_patch=True`. Diff links in `# History` use the same ranges as the
#          corresponding changelog sections. History generation can be disabled by flag.
# @param repo_root Absolute path to the repository root used as CWD for all git commands.
# @param include_patch When `True`, prepend the latest patch release section to the document.
# @param disable_history When `True`, omit `# History` section from output.
# @return Complete `CHANGELOG.md` string content, terminated with a newline.
# @satisfies REQ-018, REQ-040, REQ-041, REQ-043, REQ-068, REQ-069, REQ-070
## @brief Execute `generate_changelog_document` runtime logic for Git-Alias CLI.
# @details Executes `generate_changelog_document` using deterministic CLI control-flow and explicit error propagation.
# @param repo_root Input parameter consumed by `generate_changelog_document`.
# @param include_patch Input parameter consumed by `generate_changelog_document`.
# @param disable_history Input parameter consumed by `generate_changelog_document`.
# @return Result emitted by `generate_changelog_document` according to command contract.
def generate_changelog_document(
    repo_root: Path, include_patch: bool, disable_history: bool = False
) -> str:
    all_tags = list_tags_sorted_by_date(repo_root)
    origin_base = _canonical_origin_base(repo_root)
    lines: List[str] = ["# Changelog", ""]
    release_sections: List[str] = []
    minor_tags = [t for t in all_tags if _is_minor_release_tag(t.name)]
    last_minor: Optional[TagInfo] = minor_tags[-1] if minor_tags else None
    latest_patch: Optional[TagInfo] = None
    if include_patch:
        latest_patch = _latest_patch_tag_after(all_tags, last_minor)
        if latest_patch:
            rev_range = (
                f"{last_minor.name}..{latest_patch.name}"
                if last_minor
                else latest_patch.name
            )
            display = latest_patch.name.lstrip("v")
            compare_url = get_origin_compare_url(
                origin_base, last_minor.name if last_minor else None, latest_patch.name
            )
            title = f"[{display}]({compare_url})" if compare_url else display
            section = generate_section_for_range(
                repo_root,
                title,
                latest_patch.iso_date,
                rev_range,
                expected_version=display,
            )
            if section:
                lines.append(section)
    prev_included: Optional[str] = None
    for tag in minor_tags:
        rev_range = (
            tag.name if prev_included is None else f"{prev_included}..{tag.name}"
        )
        display = tag.name.lstrip("v")
        compare_url = get_origin_compare_url(origin_base, prev_included, tag.name)
        title = f"[{display}]({compare_url})" if compare_url else display
        section = generate_section_for_range(
            repo_root,
            title,
            tag.iso_date,
            rev_range,
            expected_version=display,
        )
        if section:
            release_sections.append(section)
        prev_included = tag.name
    if release_sections:
        lines.extend(reversed(release_sections))
    if not disable_history:
        history_tags: List[TagInfo] = list(minor_tags)
        if latest_patch is not None:
            history_tags = history_tags + [latest_patch]
        history = build_history_section(
            repo_root,
            history_tags,
            False,
            include_unreleased_link=False,
        )
        if history:
            lines.append("")
            lines.append(history)
    return "\n".join(lines).rstrip() + "\n"


## @brief Store resolved per-rule context for version discovery and matching.
# @details Encapsulates immutable artifacts required across detect/update/verify phases:
#          compiled regex, resolved file list, and pre-rendered relative-path map for stable debug output.
# @note Complexity: O(1) storage per field; aggregate complexity scales with matched file count per rule.
@dataclass(frozen=True)
class VersionRuleContext:
    pattern: str
    expression: str
    compiled_regex: re.Pattern
    files: List[Path]
    relative_map: Dict[Path, str]


## @brief Normalize a `ver_rules` pattern to the internal pathspec matching form.
# @details Strips surrounding blanks, strips a leading `./`, and anchors patterns containing `/`
#          to repository root by prefixing `/` when missing. Backslash sequences are preserved
#          verbatim so pathspec gitignore-style matching applies gitignore(5) escape semantics.
# @param pattern {str} Input pattern string from configuration.
# @return {str} Normalized pathspec-compatible pattern string; empty string when input is blank.
# @satisfies REQ-160, REQ-164
def _normalize_version_rule_pattern(pattern: str) -> str:
    trimmed = (pattern or "").strip()
    if not trimmed:
        return ""
    normalized_pattern = trimmed
    if normalized_pattern.startswith("./"):
        normalized_pattern = normalized_pattern[2:]
    if "/" in normalized_pattern and not normalized_pattern.startswith("/"):
        normalized_pattern = f"/{normalized_pattern}"
    return normalized_pattern


## @brief Split a `ver_rules` pattern into its negation flag and matching base pattern.
# @details Detects the gitignore(5)-style negation prefix `!` in the raw pattern text and
#          returns the remainder used for exclusion matching.
# @param pattern {str} Raw pattern string from configuration.
# @return {Tuple[bool, str]} `(True, remainder)` when the pattern starts with `!`; `(False, pattern)` otherwise.
# @satisfies REQ-161
def _split_negation_pattern(pattern: str) -> Tuple[bool, str]:
    text = pattern or ""
    if text.startswith("!"):
        return True, text[1:]
    return False, text


## @brief Evaluate pathspec membership for one repository-relative path.
# @details Applies the spec match and retries with a leading `/` for root-anchored patterns,
#          mirroring the anchored-pattern matching contract of the inventory walker.
# @param spec {pathspec.PathSpec} Compiled pathspec used for matching.
# @param normalized_pattern {str} Normalized pattern that produced `spec`.
# @param relative {str} Repository-relative POSIX path under evaluation.
# @return {bool} True when the path matches the spec.
def _version_pathspec_matches(spec, normalized_pattern: str, relative: str) -> bool:
    matches = spec.match_file(relative)
    if (
        not matches
        and normalized_pattern.startswith("/")
        and not relative.startswith("/")
    ):
        matches = spec.match_file(f"/{relative}")
    return bool(matches)


## @brief Compile exclusion pathspecs from negation `ver_rules` patterns.
# @details Collects every rule pattern starting with `!`, strips the prefix, normalizes the
#          remainder with the shared normalization contract, and compiles each base pattern
#          as a positive gitignore-style spec via the supported pathspec `gitignore`
#          registered style (the legacy `gitwildmatch` name is deprecated by pathspec).
# @param rules {List[Tuple[str, Optional[str]]]} Parsed `(pattern, regex)` rule pairs.
# @return {List[pathspec.PathSpec]} Compiled exclusion pathspecs; empty when no negation pattern is configured.
# @satisfies REQ-161
def _build_version_negation_specs(rules) -> List:
    specs = []
    for pattern, _regex in rules:
        negated, base_text = _split_negation_pattern(
            pattern if isinstance(pattern, str) else ""
        )
        if not negated:
            continue
        base = _normalize_version_rule_pattern(base_text)
        if not base:
            continue
        specs.append(pathspec.PathSpec.from_lines("gitignore", [base]))
    return specs


## @brief Report whether a repository-relative path is excluded by a negation pattern.
# @details Evaluates each compiled negation spec directly and with a leading `/` prefix so
#          root-anchored exclusion bases match repository-relative paths.
# @param relative {str} Repository-relative POSIX path under evaluation.
# @param negation_specs {List[pathspec.PathSpec]} Compiled exclusion pathspecs.
# @return {bool} True when any negation spec matches the path.
# @satisfies REQ-161, REQ-163
def _version_path_is_negated(relative: str, negation_specs) -> bool:
    for spec in negation_specs:
        if spec.match_file(relative) or spec.match_file(f"/{relative}"):
            return True
    return False


## @brief Build a deduplicated repository file inventory for version rule evaluation.
# @details Executes a single `git ls-files` query from repository root, filters to existing files only,
#          applies hardcoded exclusion regexes, normalizes relative paths, and deduplicates by resolved path.
# @param root Repository root path used as traversal anchor.
# @return List of tuples `(absolute_path, normalized_relative_path)` used by downstream matchers.
def _build_version_file_inventory(root: Path) -> List[Tuple[Path, str]]:
    inventory: List[Tuple[Path, str]] = []
    seen = set()
    try:
        tracked_files = run_git_text(["ls-files"], cwd=root)
    except RuntimeError as exc:
        raise VersionDetectionError(
            f"Unable to list repository files with git ls-files: {exc}"
        ) from None
    for relative in tracked_files.splitlines():
        normalized_relative = (relative or "").replace("\\", "/").strip()
        if not normalized_relative:
            continue
        if normalized_relative.startswith("./"):
            normalized_relative = normalized_relative[2:]
        if _is_version_path_excluded(normalized_relative):
            continue
        path = root / Path(normalized_relative)
        if not path.is_file():
            continue
        resolved = path.resolve()
        if resolved in seen:
            continue
        seen.add(resolved)
        inventory.append((path, normalized_relative))
    return inventory


## @brief Collect repository files matched by one `ver_rules` pattern.
# @details Normalizes the pattern, applies pathspec gitignore-style matching over the tracked-file
#          inventory, and drops candidates excluded by any compiled negation spec. Uses the
#          precomputed inventory when provided to avoid repeated repository traversals.
# @param root {Path} Repository root path used as traversal anchor.
# @param pattern {str} Inclusion pattern string from configuration (never starting with `!`).
# @param inventory {Optional[List[Tuple[Path, str]]]} Precomputed `(path, normalized_relative_path)` list.
# @param negation_specs {List[pathspec.PathSpec]} Compiled exclusion pathspecs applied before matching.
# @return {List[Path]} Matched, non-excluded file paths in inventory order.
# @satisfies REQ-161, REQ-163, REQ-164
def _collect_version_files(root, pattern, *, inventory=None, negation_specs=()):
    files = []
    normalized_pattern = _normalize_version_rule_pattern(pattern)
    if not normalized_pattern:
        return files
    # @details Apply pathspec matcher to preserve configured GitIgnore-like semantics.
    spec = pathspec.PathSpec.from_lines("gitignore", [normalized_pattern])
    candidates = (
        inventory if inventory is not None else _build_version_file_inventory(root)
    )
    for path, normalized_relative in candidates:
        if _version_path_is_negated(normalized_relative, negation_specs):
            continue
        if _version_pathspec_matches(spec, normalized_pattern, normalized_relative):
            files.append(path)

    return files


## @brief Execute `_is_version_path_excluded` runtime logic for Git-Alias CLI.
# @details Executes `_is_version_path_excluded` using deterministic CLI control-flow and explicit error propagation.
# @param relative_path Input parameter consumed by `_is_version_path_excluded`.
# @return Result emitted by `_is_version_path_excluded` according to command contract.
def _is_version_path_excluded(relative_path: str) -> bool:
    return any(regex.search(relative_path) for regex in VERSION_CLEANUP_PATTERNS)


## @brief Execute `_iter_versions_in_text` runtime logic for Git-Alias CLI.
# @details Executes `_iter_versions_in_text` using deterministic CLI control-flow and explicit error propagation.
# @param text Input parameter consumed by `_iter_versions_in_text`.
# @param compiled_regexes Input parameter consumed by `_iter_versions_in_text`.
# @return Result emitted by `_iter_versions_in_text` according to command contract.
def _iter_versions_in_text(text, compiled_regexes):
    for regex in compiled_regexes:
        for match in regex.finditer(text):
            if match.groups():
                for group in match.groups():
                    if group:
                        yield group
                        break
            else:
                yield match.group(0)


## @brief Read and cache UTF-8 text content for a version-managed file.
# @details Loads file content with UTF-8 decoding; falls back to `errors="ignore"` on decode failures.
#          Emits deterministic stderr diagnostics on I/O failure and returns `None` for caller-managed skip logic.
# @param file_path Absolute path of the file to read.
# @param text_cache Optional mutable cache keyed by `Path` to avoid duplicate reads across phases.
# @return File text payload or `None` when file cannot be read.
def _read_version_file_text(
    file_path: Path, text_cache: Optional[Dict[Path, str]] = None
) -> Optional[str]:
    if text_cache is not None and file_path in text_cache:
        return text_cache[file_path]
    try:
        text = file_path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        text = file_path.read_text(encoding="utf-8", errors="ignore")
    except OSError as exc:
        print(f"Unable to read {file_path}: {exc}", file=sys.stderr)
        return None
    if text_cache is not None:
        text_cache[file_path] = text
    return text


## @brief Build reusable per-rule contexts for canonical version evaluation workflows.
# @details Compiles exclusion pathspecs from negation rules, skips negation rules from context
#          generation, and resolves matched files plus compiled regex for each inclusion rule.
#          Preserves error contracts for unmatched patterns and invalid regex declarations.
# @param root {Path} Repository root path used for relative-path rendering.
# @param rules {List[Tuple[str, Optional[str]]]} Sequence of `(pattern, regex)` tuples; negation
#        patterns (`!` prefix) contribute exclusions and never produce contexts.
# @param inventory {Optional[List[Tuple[Path, str]]]} Precomputed inventory to avoid repeated filesystem traversal.
# @return {List[VersionRuleContext]} Ordered list of `VersionRuleContext` objects aligned to inclusion rule order.
# @throws VersionDetectionError when a rule matches no files or contains an invalid regex.
# @satisfies REQ-161, REQ-162, REQ-163
def _prepare_version_rule_contexts(
    root: Path, rules, *, inventory: Optional[List[Tuple[Path, str]]] = None
) -> List[VersionRuleContext]:
    contexts: List[VersionRuleContext] = []
    negation_specs = _build_version_negation_specs(rules)
    for pattern, expression in rules:
        negated, _base_text = _split_negation_pattern(
            pattern if isinstance(pattern, str) else ""
        )
        if negated:
            continue
        files = _collect_version_files(
            root, pattern, inventory=inventory, negation_specs=negation_specs
        )
        relative_map: Dict[Path, str] = {}
        for file_path in files:
            try:
                relative_map[file_path] = file_path.relative_to(root).as_posix()
            except ValueError:
                relative_map[file_path] = str(file_path)
        if not files:
            raise VersionDetectionError(
                f"No files matched the version rule pattern '{pattern}'. Only repository files "
                "reported by git ls-files can be configured in ver_rules.pattern."
            )
        try:
            compiled = re.compile(expression)
        except re.error as exc:
            raise VersionDetectionError(
                f"Invalid regex '{expression}' for pattern '{pattern}': {exc}"
            )
        contexts.append(
            VersionRuleContext(
                pattern=pattern,
                expression=expression,
                compiled_regex=compiled,
                files=files,
                relative_map=relative_map,
            )
        )
    return contexts


## @brief Execute `_determine_canonical_version` runtime logic for Git-Alias CLI.
# @details Executes `_determine_canonical_version` using deterministic CLI control-flow and explicit error propagation.
# @param root Input parameter consumed by `_determine_canonical_version`.
# @param rules Input parameter consumed by `_determine_canonical_version`.
# @param verbose Input parameter consumed by `_determine_canonical_version`.
# @param debug Input parameter consumed by `_determine_canonical_version`.
# @param contexts Optional precomputed `VersionRuleContext` list for reuse across phases.
# @param text_cache Optional mutable cache keyed by file path to avoid duplicate reads.
# @return Result emitted by `_determine_canonical_version` according to command contract.
def _determine_canonical_version(
    root: Path,
    rules,
    *,
    verbose: bool = False,
    debug: bool = False,
    contexts: Optional[List[VersionRuleContext]] = None,
    text_cache: Optional[Dict[Path, str]] = None,
):
    active_contexts = (
        contexts
        if contexts is not None
        else _prepare_version_rule_contexts(root, rules)
    )
    canonical = None
    canonical_file = None
    for context in active_contexts:
        if debug:
            print(f"Pattern '{context.pattern}' matched files:")
            if context.files:
                for file_path in context.files:
                    print(f"  {context.relative_map[file_path]}")
            else:
                print("  (none)")
        matched_in_rule = False
        for file_path in context.files:
            text = _read_version_file_text(file_path, text_cache=text_cache)
            if text is None:
                continue
            versions = list(_iter_versions_in_text(text, [context.compiled_regex]))
            if verbose:
                match_state = "yes" if versions else "no"
                print(
                    f"Regex match for {context.relative_map[file_path]}: {match_state}."
                )
            if versions:
                matched_in_rule = True
            for version in versions:
                if canonical is None:
                    canonical = version
                    canonical_file = file_path
                elif version != canonical:
                    raise VersionDetectionError(
                        f"Version mismatch between {canonical_file} ({canonical}) and {file_path} ({version})"
                    )
        if not matched_in_rule:
            raise VersionDetectionError(
                f"No version matches found for rule pattern '{context.pattern}' with regex '{context.expression}'."
            )
    if canonical is None:
        raise VersionDetectionError(
            "No version string matched the configured rule list."
        )
    return canonical


## @brief Execute `_parse_semver_tuple` runtime logic for Git-Alias CLI.
# @details Executes `_parse_semver_tuple` using deterministic CLI control-flow and explicit error propagation.
# @param text Input parameter consumed by `_parse_semver_tuple`.
# @return Result emitted by `_parse_semver_tuple` according to command contract.
def _parse_semver_tuple(text: str) -> Optional[Tuple[int, int, int]]:
    match = SEMVER_RE.match((text or "").strip())
    if not match:
        return None
    return (int(match.group(1)), int(match.group(2)), int(match.group(3)))


## @brief Execute `_replace_versions_in_text` runtime logic for Git-Alias CLI.
# @details Executes `_replace_versions_in_text` using deterministic CLI control-flow and explicit error propagation.
# @param text Input parameter consumed by `_replace_versions_in_text`.
# @param compiled_regex Input parameter consumed by `_replace_versions_in_text`.
# @param replacement Input parameter consumed by `_replace_versions_in_text`.
# @return Result emitted by `_replace_versions_in_text` according to command contract.
def _replace_versions_in_text(text, compiled_regex, replacement):
    last_index = 0
    pieces = []
    count = 0
    for match in compiled_regex.finditer(text):
        span = match.span(1) if match.groups() else match.span(0)
        pieces.append(text[last_index : span[0]])
        pieces.append(replacement)
        last_index = span[1]
        count += 1
    if count == 0:
        return text, 0
    pieces.append(text[last_index:])
    return "".join(pieces), count


## @brief Execute `_current_branch_name` runtime logic for Git-Alias CLI.
# @details Executes `_current_branch_name` using deterministic CLI control-flow and explicit error propagation.
# @return Result emitted by `_current_branch_name` according to command contract.
def _current_branch_name():
    proc = _run_checked(
        ["git", "rev-parse", "--abbrev-ref", "HEAD"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    branch = proc.stdout.strip()
    if not branch or branch == "HEAD":
        raise ReleaseError("Release commands require an active branch head.")
    return branch


## @brief Execute `_ref_exists` runtime logic for Git-Alias CLI.
# @details Executes `_ref_exists` using deterministic CLI control-flow and explicit error propagation.
# @param ref_name Input parameter consumed by `_ref_exists`.
# @return Result emitted by `_ref_exists` according to command contract.
def _ref_exists(ref_name):
    proc = _run_checked(
        ["git", "show-ref", "--verify", "--quiet", ref_name],
        check=False,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    return proc.returncode == 0


## @brief Execute `_local_branch_exists` runtime logic for Git-Alias CLI.
# @details Executes `_local_branch_exists` using deterministic CLI control-flow and explicit error propagation.
# @param branch_name Input parameter consumed by `_local_branch_exists`.
# @return Result emitted by `_local_branch_exists` according to command contract.
def _local_branch_exists(branch_name):
    return _ref_exists(f"refs/heads/{branch_name}")


## @brief Execute `_remote_branch_exists` runtime logic for Git-Alias CLI.
# @details Executes `_remote_branch_exists` using deterministic CLI control-flow and explicit error propagation.
# @param branch_name Input parameter consumed by `_remote_branch_exists`.
# @return Result emitted by `_remote_branch_exists` according to command contract.
def _remote_branch_exists(branch_name):
    return _ref_exists(f"refs/remotes/origin/{branch_name}")


## @brief Parse worktree porcelain output into deterministic association records.
# @details Executes `git worktree list --porcelain`, extracts `worktree <path>` and optional
#          `branch refs/heads/<name>` fields, normalizes paths via `Path.resolve()`, and preserves
#          entry order for deterministic downstream matching and diagnostics.
# @return `List[WorktreeInfo]` parsed from repository worktree metadata.
# @exception RuntimeError Propagates git query failures from `run_git_text`.
# @satisfies REQ-139
def _list_worktree_associations() -> List[WorktreeInfo]:
    text = run_git_text(["worktree", "list", "--porcelain"])
    entries: List[WorktreeInfo] = []
    current_path: Optional[Path] = None
    current_branch: Optional[str] = None
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            if current_path is not None:
                entries.append(WorktreeInfo(path=current_path, branch_name=current_branch))
            current_path = None
            current_branch = None
            continue
        if line.startswith("worktree "):
            if current_path is not None:
                entries.append(WorktreeInfo(path=current_path, branch_name=current_branch))
            current_path = Path(line[len("worktree ") :]).expanduser().resolve()
            current_branch = None
            continue
        if line.startswith("branch refs/heads/"):
            current_branch = line[len("branch refs/heads/") :]
    if current_path is not None:
        entries.append(WorktreeInfo(path=current_path, branch_name=current_branch))
    return entries


## @brief Resolve the association record bound to a local branch name.
# @details Scans parsed worktree metadata and returns the first worktree whose `branch_name`
#          equals the requested local branch.
# @param branch_name `str` — local branch name to resolve.
# @param associations `List[WorktreeInfo]` — parsed worktree metadata snapshot.
# @return `Optional[WorktreeInfo]` matching association or `None`.
# @satisfies REQ-139
def _find_worktree_for_branch(
    branch_name: str, associations: List[WorktreeInfo]
) -> Optional[WorktreeInfo]:
    for info in associations:
        if info.branch_name == branch_name:
            return info
    return None


## @brief Resolve the association record bound to a target worktree path.
# @details Normalizes the user-provided path via `Path.resolve()` and returns the matching parsed
#          worktree record when present.
# @param worktree_arg `str` — CLI worktree operand.
# @param associations `List[WorktreeInfo]` — parsed worktree metadata snapshot.
# @return `Optional[WorktreeInfo]` matching association or `None`.
# @satisfies REQ-139
def _find_association_for_worktree(
    worktree_arg: str, associations: List[WorktreeInfo]
) -> Optional[WorktreeInfo]:
    target = Path(worktree_arg).expanduser().resolve()
    for info in associations:
        if info.path == target:
            return info
    return None


## @brief Validate branch-delete CLI operands and optional force mode.
# @details Accepts exactly one branch operand with an optional leading `--force`, rejects all other
#          flags and extra operands, and emits deterministic English diagnostics on invalid input.
# @param args `List[str]` — CLI operands after `bd`.
# @return `Tuple[str, bool]` normalized branch target and force-mode flag.
# @exception SystemExit Exit code 1 on invalid operands.
# @satisfies REQ-019
def _parse_bd_target(args: List[str]) -> Tuple[str, bool]:
    force_delete = False
    if args and args[0] == "--force":
        force_delete = True
        args = args[1:]
    if len(args) != 1:
        print("git bd requires exactly one branch: git bd [--force] <branch>.", file=sys.stderr)
        sys.exit(1)
    branch_name = args[0].strip()
    if not branch_name or branch_name.startswith("-"):
        print("git bd accepts one branch name and an optional leading --force flag.", file=sys.stderr)
        sys.exit(1)
    return branch_name, force_delete


## @brief Validate worktree-delete CLI operands and optional force mode.
# @details Accepts exactly one worktree operand with an optional leading `--force`, rejects all
#          other flags and extra operands, and emits deterministic English diagnostics on invalid input.
# @param args `List[str]` — CLI operands after `wtd`.
# @return `Tuple[str, bool]` normalized worktree target operand and force-mode flag.
# @exception SystemExit Exit code 1 on invalid operands.
# @satisfies REQ-077
def _parse_wtd_target(args: List[str]) -> Tuple[str, bool]:
    force_delete = False
    if args and args[0] == "--force":
        force_delete = True
        args = args[1:]
    if len(args) != 1:
        print("git wtd requires exactly one worktree: git wtd [--force] <worktree>.", file=sys.stderr)
        sys.exit(1)
    worktree_arg = args[0].strip()
    if not worktree_arg or worktree_arg.startswith("-"):
        print("git wtd accepts one worktree path and an optional leading --force flag.", file=sys.stderr)
        sys.exit(1)
    return worktree_arg, force_delete


## @brief Preflight branch deletion without mutating repository state.
# @details Resolves the branch tip commit, verifies that an upstream branch exists and contains the
#          tip or that the tip is reachable from `HEAD`, and converts any git failure into deterministic
#          English diagnostics suitable for the all-or-nothing coordinated deletion flow.
# @param branch_name `str` — local branch target.
# @param alias `str` — user-facing alias token used in diagnostics.
# @return `None` when branch deletion is safe without force.
# @exception SystemExit Exit code 1 when the branch cannot be deleted without force.
# @satisfies REQ-138, REQ-140
def _preflight_branch_delete(branch_name: str, alias: str) -> None:
    try:
        branch_commit = run_git_text(["rev-parse", "--verify", branch_name]).strip()
    except RuntimeError as exc:
        print(
            f"Unable to run git {alias}: branch '{branch_name}' cannot be deleted without force: {exc}",
            file=sys.stderr,
        )
        sys.exit(1)
    try:
        upstream_ref = run_git_text(
            ["for-each-ref", "--format=%(upstream:short)", f"refs/heads/{branch_name}"]
        ).strip()
    except RuntimeError:
        upstream_ref = ""
    if upstream_ref:
        if _is_commit_ancestor(branch_commit, upstream_ref):
            return
        print(
            f"Unable to run git {alias}: branch '{branch_name}' cannot be deleted without force because it is not merged into upstream '{upstream_ref}'.",
            file=sys.stderr,
        )
        sys.exit(1)
    if _is_commit_ancestor(branch_commit, "HEAD"):
        return
    print(
        f"Unable to run git {alias}: branch '{branch_name}' cannot be deleted without force because it is not merged into HEAD.",
        file=sys.stderr,
    )
    sys.exit(1)


## @brief Preflight worktree removal without mutating repository state.
# @details Rejects deletion of the main repository worktree, ensures the target path is a registered
#          linked worktree, and verifies that `git status --porcelain` executed inside the worktree
#          is empty so `git worktree remove` can proceed without force.
# @param worktree_path `Path` — normalized absolute worktree target.
# @param alias `str` — user-facing alias token used in diagnostics.
# @return `None` when worktree removal is safe without force.
# @exception SystemExit Exit code 1 when the worktree cannot be deleted without force.
# @satisfies REQ-140, REQ-143
def _preflight_worktree_delete(worktree_path: Path, alias: str) -> None:
    if worktree_path == get_git_root().resolve():
        print(
            f"Unable to run git {alias}: worktree '{worktree_path}' is the main repository worktree.",
            file=sys.stderr,
        )
        sys.exit(1)
    if not worktree_path.exists():
        print(
            f"Unable to run git {alias}: worktree '{worktree_path}' does not exist.",
            file=sys.stderr,
        )
        sys.exit(1)
    try:
        status_output = run_git_text(["status", "--porcelain"], cwd=worktree_path)
    except RuntimeError as exc:
        print(
            f"Unable to run git {alias}: worktree '{worktree_path}' cannot be deleted without force: {exc}",
            file=sys.stderr,
        )
        sys.exit(1)
    if status_output.strip():
        print(
            f"Unable to run git {alias}: worktree '{worktree_path}' cannot be deleted without force because it is not clean.",
            file=sys.stderr,
        )
        sys.exit(1)


## @brief Print paired branch/worktree deletion evidence.
# @details Emits deterministic English stdout lines identifying both deleted resources after the
#          coordinated deletion path completes successfully.
# @param worktree_path `Path` — deleted worktree path.
# @param branch_name `str` — deleted local branch name.
# @return `None`; side-effect: stdout output.
# @satisfies REQ-142
def _print_paired_delete_success(worktree_path: Path, branch_name: str) -> None:
    print(f"Deleted worktree: {worktree_path}")
    print(f"Deleted branch: {branch_name}")


## @brief Execute coordinated deletion for an associated worktree/branch pair.
# @details When `force_delete` is disabled, preflights both deletion operations before mutating
#          repository state. Always removes the worktree first and the branch second because the
#          branch cannot be deleted while an associated worktree still exists.
# @param worktree_info `WorktreeInfo` — resolved association record with branch binding.
# @param alias `str` — user-facing alias token used in diagnostics.
# @param force_delete `bool` — when `True`, bypass non-force preflight checks and execute forced git deletion flags.
# @return `None`; side-effects: git delete commands and stdout evidence.
# @exception RuntimeError Raised when the association lacks a branch binding.
# @satisfies REQ-140, REQ-141, REQ-142, REQ-145
def _delete_associated_branch_and_worktree(
    worktree_info: WorktreeInfo, alias: str, force_delete: bool = False
) -> None:
    if not worktree_info.branch_name:
        raise RuntimeError("Associated branch name is required for paired deletion.")
    if not force_delete:
        _preflight_worktree_delete(worktree_info.path, alias)
        _preflight_branch_delete(worktree_info.branch_name, alias)
    worktree_cmd = ["worktree", "remove"]
    branch_cmd = ["branch", "-d"]
    if force_delete:
        worktree_cmd.append("--force")
        branch_cmd = ["branch", "-D"]
    run_git_cmd(worktree_cmd + [str(worktree_info.path)])
    run_git_cmd(branch_cmd + [worktree_info.branch_name])
    _print_paired_delete_success(worktree_info.path, worktree_info.branch_name)


## @brief Enforce release preflight prerequisites with fail-closed remote verification.
# @details Validates configured local branches, then requires a successful
#          `origin` remote-reference refresh before evaluating any remote state;
#          when `_refresh_remote_refs()` reports failure the preflight raises
#          immediately so no local release mutation can proceed against
#          unverifiable remote data. Subsequent checks enforce remote-branch
#          existence, remote update status for master and develop, current branch
#          equal to configured work, and a clean working tree and index.
# @return {Dict[str, str]} Branch map with keys `master`, `develop`, `work`.
# @throws ReleaseError Missing local/remote branches, failed remote refresh,
#         pending remote updates, non-work checkout, or dirty state.
# @satisfies REQ-026, REQ-047
def _ensure_release_prerequisites():
    master_branch = get_branch("master")
    develop_branch = get_branch("develop")
    work_branch = get_branch("work")
    missing_local = [
        name
        for name in (master_branch, develop_branch, work_branch)
        if not _local_branch_exists(name)
    ]
    if missing_local:
        joined = ", ".join(missing_local)
        raise ReleaseError(
            f"Unable to run release command: missing local branches {joined}."
        )
    if not _refresh_remote_refs():
        raise ReleaseError(
            "Unable to update remote references from origin. "
            "Resolve remote access and retry the release command."
        )
    missing_remote = [
        name
        for name in (master_branch, develop_branch)
        if not _remote_branch_exists(name)
    ]
    if missing_remote:
        joined = ", ".join(missing_remote)
        raise ReleaseError(
            f"Unable to run release command: missing remote branches {joined}."
        )
    if has_remote_branch_updates("master"):
        raise ReleaseError(
            f"Remote branch {master_branch} has pending updates. Please pull them first."
        )
    if has_remote_branch_updates("develop"):
        raise ReleaseError(
            f"Remote branch {develop_branch} has pending updates. Please pull them first."
        )
    current_branch = _current_branch_name()
    if current_branch != work_branch:
        raise ReleaseError(
            f"Release commands must be executed from the {work_branch} branch (current: {current_branch})."
        )
    status = _git_status_lines()
    if has_unstaged_changes(status):
        raise ReleaseError(
            "Working tree changes detected. Clean or stage them before running a release."
        )
    if has_staged_changes(status):
        raise ReleaseError(
            "Staging area is not empty. Complete or reset pending commits before running a release."
        )
    return {"master": master_branch, "develop": develop_branch, "work": work_branch}


## @brief Execute `_bump_semver_version` runtime logic for Git-Alias CLI.
# @details Executes `_bump_semver_version` using deterministic CLI control-flow and explicit error propagation.
# @param current_version Input parameter consumed by `_bump_semver_version`.
# @param level Input parameter consumed by `_bump_semver_version`.
# @return Result emitted by `_bump_semver_version` according to command contract.
def _bump_semver_version(current_version, level):
    parts = _parse_semver_tuple(current_version)
    if parts is None:
        raise ReleaseError(
            f"The current version '{current_version}' is not a valid semantic version."
        )
    major, minor, patch = parts
    if level == "major":
        major += 1
        minor = 0
        patch = 0
    elif level == "minor":
        minor += 1
        patch = 0
    elif level == "patch":
        patch += 1
    else:
        raise ReleaseError(f"Unsupported release level '{level}'.")
    return f"{major}.{minor}.{patch}"


## @brief Execute `_run_release_step` runtime logic for Git-Alias CLI.
# @details Executes `_run_release_step` using deterministic CLI control-flow and explicit error propagation.
# @param level Input parameter consumed by `_run_release_step`.
# @param step_name Input parameter consumed by `_run_release_step`.
# @param action Input parameter consumed by `_run_release_step`.
# @return Result emitted by `_run_release_step` according to command contract.
def _run_release_step(level, step_name, action):
    label = f"[release:{level}]"
    try:
        result = action()
        print(f"\n--- {label} Step '{step_name}' completed successfully. ---")
        return result
    except ReleaseError:
        raise
    except VersionDetectionError:
        raise
    except CommandExecutionError as exc:
        err_text = CommandExecutionError._decode_stream(exc.stderr).strip()
        message = err_text if err_text else str(exc)
        raise ReleaseError(
            f"\n--- {label} Step '{step_name}' failed: {message} ---"
        ) from None
    except SystemExit as exc:
        code = exc.code if isinstance(exc.code, int) else 1
        raise ReleaseError(
            f"\n--- {label} Step '{step_name}' failed: command exited with status {code} ---"
        ) from None
    except Exception as exc:
        raise ReleaseError(
            f"\n--- {label} Step '{step_name}' failed: {exc} ---"
        ) from None


## @brief Execute `_create_release_commit_for_flow` runtime logic for Git-Alias CLI.
# @details Executes release-flow first-commit creation with WIP amend semantics reused from `_execute_commit`.
# @param target_version Input parameter consumed by `_create_release_commit_for_flow`.
# @return Result emitted by `_create_release_commit_for_flow` according to command contract.
def _create_release_commit_for_flow(target_version):
    _ensure_commit_ready("release")
    message = f"release: Release version {target_version}"
    return _execute_commit(message, "release")


## @brief Publish selected release references once with recovery diagnostics.
# @details O(1) refspec construction; one Git push; no automatic retries. The push
#          executes through the shared inherited-stdio git wrapper (`run_git_cmd`) so
#          push output and transport errors reach the user terminal and interactive
#          SSH/credential authentication remains possible (restores the pre-8e4abd26
#          publication transport; piped stdio caused `Permission denied (publickey)`
#          rejections in sessions whose interactive fetch succeeded). Tag publication
#          requires atomic support; --no-follow-tags excludes unrelated tags. Failure
#          preserves local objects and reports Git's rejection live on stderr.
# @param level {str} Release command: major, minor, or patch.
# @param version {str} Prepared semantic version.
# @param branch {str} Configured destination branch name.
# @param include_branch {bool} Publish branch when True.
# @param include_tag {bool} Publish exact release tag atomically when True.
# @param dev_release {bool} Develop-scoped release (REQ-045, REQ-200); selects the
#        `g <level> --dev --resume` recovery command and develop-only tips.
# @return {None} No operation when both selectors are False.
# @throws ReleaseError Push failed; includes rejection and recovery references.
# @satisfies REQ-045, REQ-072, REQ-179, REQ-180, REQ-181, REQ-200
def _push_release_refs(level, version, branch, include_branch=True, include_tag=False,
                       dev_release=False):
    ## @brief Exact reference names for publication and diagnostics.
    branch_ref = f"refs/heads/{branch}"
    tag_ref = f"refs/tags/v{version}"
    ## @brief Non-force refspecs; empty selection requires no network mutation.
    refspecs = []
    if include_branch:
        refspecs.append(f"{branch_ref}:{branch_ref}")
    if include_tag:
        refspecs.append(f"{tag_ref}:{tag_ref}")
    if not refspecs:
        return
    ## @brief Explicitly disable configured implicit annotated-tag following.
    command = ["push", "--no-follow-tags"]
    if include_tag:
        command.append("--atomic")
    scope_tips = "work/develop" if dev_release else "work/develop/master"
    resume_command = f"g {level} --dev --resume" if dev_release else f"g {level} --resume"
    try:
        run_git_cmd([*command, "origin", *refspecs])
    except CommandExecutionError:
        raise ReleaseError(
            f"Release {version} is already prepared locally. Push failed.\n"
            f"Verify local and origin refs: {branch_ref}, {tag_ref}; "
            f"configured {scope_tips} tips.\n"
            f"Resume safely after resolving the rejection: {resume_command}"
        ) from None


## @brief Validate and resume publication of an immutable prepared local release.
# @details O(1) Git queries excluding ancestry traversal. Require clean checkout,
#          matching work/integration tips, release subject/version, and annotated tag identity.
#          Query the single origin push URL before any push; reject missing remote branches,
#          conflicting tags, and non-ancestor remote tips. Publish missing refs only, then
#          checkout work. Preserve version files, commits, tags, and external build outputs.
# @param level {str} Release command: major, minor, or patch.
# @param dev_release {bool} Develop-scoped release (REQ-045, REQ-200); excludes
#        master from integration and publication validation.
# @return {None} Completes missing publication and restores work checkout.
# @throws ReleaseError Invalid release state or publication rejection.
# @throws RuntimeError Git inspection failed.
# @throws VersionDetectionError Version-managed files disagree.
# @satisfies REQ-045, REQ-176, REQ-177, REQ-178, REQ-179, REQ-200
def _resume_release_flow(level, dev_release=False):
    ## @brief Configured branch map; develop-scoped releases exclude master.
    branches = {key: get_branch(key) for key in BRANCH_KEYS}
    integrated = [branches["develop"]]
    if not dev_release:
        integrated.append(branches["master"])
    if run_git_text(["status", "--porcelain"]):
        raise ReleaseError("Cannot resume: working tree and index must be clean.")
    if _current_branch_name() not in [branches["work"], *integrated]:
        raise ReleaseError("Cannot resume: checkout a configured release branch first.")
    ## @brief Immutable release commit and version derived from configured work.
    commit = run_git_text([
        "rev-parse", "--verify", f"refs/heads/{branches['work']}^{{commit}}"
    ])
    subject = run_git_text(["show", "-s", "--format=%s", commit])
    version = _extract_release_version(subject)
    parts = _parse_semver_tuple(version or "")
    if parts is None or subject != f"release: Release version {version}":
        raise ReleaseError("Cannot resume: work tip is not a release commit.")
    ## @brief Semver shape identifies releases produced by each bump level.
    expected_level = "patch" if parts[2] else "minor" if parts[1] else "major"
    if level != expected_level or parts == (0, 0, 0):
        raise ReleaseError("Cannot resume: release version does not match requested level.")
    for branch in integrated:
        if run_git_text([
            "rev-parse", "--verify", f"refs/heads/{branch}^{{commit}}"
        ]) != commit:
            raise ReleaseError(
                f"Cannot resume: refs/heads/{branch} differs from work release {commit}."
            )
    if _determine_canonical_version(get_git_root(), get_version_rules()) != version:
        raise ReleaseError("Cannot resume: version files differ from the release commit.")
    ## @brief Preserve annotated tag object identity and peeled commit identity.
    tag_ref = f"refs/tags/v{version}"
    tag_object = run_git_text(["rev-parse", "--verify", tag_ref])
    if (run_git_text(["cat-file", "-t", tag_object]) != "tag"
            or run_git_text(["rev-parse", "--verify", f"{tag_ref}^{{commit}}"]) != commit):
        raise ReleaseError(
            f"Cannot resume: {tag_ref} is not the prepared annotated release tag."
        )
    ## @brief Inspect publication endpoint rather than a potentially different fetch URL.
    urls = run_git_text(["remote", "get-url", "--push", "--all", "origin"]).splitlines()
    if len(urls) != 1:
        raise ReleaseError("Cannot resume: origin must have exactly one push URL.")
    ## @brief Remote snapshot of branch tips, annotated tag object, and peeled target.
    refs = [f"refs/heads/{branch}" for branch in integrated]
    remote = dict(
        (ref, oid) for oid, ref in (
            line.split() for line in run_git_text(
                ["ls-remote", "--", urls[0], *refs, tag_ref, f"{tag_ref}^{{}}"]
            ).splitlines()
        )
    )
    if tag_ref in remote and (
        remote[tag_ref] != tag_object or remote.get(f"{tag_ref}^{{}}") != commit
    ):
        raise ReleaseError(f"Cannot resume: remote {tag_ref} conflicts with the local tag.")
    for ref in refs:
        if ref not in remote or not _is_commit_ancestor(remote[ref], commit):
            raise ReleaseError(
                f"Cannot resume: remote {ref} is missing or diverges from {commit}."
            )
    if not dev_release and remote[refs[0]] != commit:
        _run_release_step(level, "push develop branch", lambda: _push_release_refs(
            level, version, integrated[0]
        ))
    if remote[refs[-1]] != commit or tag_ref not in remote:
        _run_release_step(level, "push release atomically", lambda: _push_release_refs(
            level, version, integrated[-1],
            include_branch=remote[refs[-1]] != commit,
            include_tag=tag_ref not in remote,
            dev_release=dev_release,
        ))
    _run_release_step(level, "return to work", lambda: cmd_co([branches["work"]]))
    print(f"Release {version} publication completed successfully.")


## @brief Execute `_execute_release_flow` runtime logic for Git-Alias CLI.
# @details Orchestrates the full release pipeline for `major`, `minor`, and `patch` levels.
#          Branch integration is scope-dependent (REQ-045, REQ-072, REQ-200):
#          - `dev_release=True`: merges `work` into `develop` and pushes `develop`
#            with the exact release tag atomically; skips `master` entirely.
#          - default: integrates work/develop/master and prepares the tag,
#            pushes develop alone, then atomically publishes master and the exact tag.
#          Changelog flags always include `--force-write`; `patch` auto-adds `--include-patch`.
#          Release script hooks come from the local configuration (REQ-166, REQ-318):
#          a non-empty `pre_release_check` runs as the first release step before the
#          version update, and a non-empty `build_script` runs after the version update
#          and before the release-version commit so build artifacts are staged by
#          `git add --all` and included in that commit. Both execute through
#          `run_command(...)` without shell, with repository root as CWD and
#          inherited stdio; a non-zero exit aborts the release before any commit,
#          tag, or push (REQ-168, REQ-320).
#          The temporary changelog tag is deleted before integration. The definitive
#          tag is prepared before any push; final publication is atomic and tag-scoped.
#          Complexity: O(F + C) version-file and changelog traversal plus Git operations.
# @param level {str} Release level string: `"major"`, `"minor"`, or `"patch"`.
# @param changelog_args {List[str] | None} Optional extra changelog flags forwarded alongside `--force-write`.
# @param dev_release {bool} Develop-scoped release (REQ-045, REQ-200); integrates and
#          publishes configured `develop` only, leaving `master` unchanged.
# @return None; raises `ReleaseError` or `VersionDetectionError` on failure.
# @satisfies REQ-026, REQ-045, REQ-072, REQ-166, REQ-167, REQ-168, REQ-200, REQ-318, REQ-319, REQ-320
# @return Result emitted by `_execute_release_flow` according to command contract.
def _execute_release_flow(level, changelog_args=None, dev_release=False):
    branches = _ensure_release_prerequisites()
    rules = get_version_rules()
    if not rules:
        raise ReleaseError(
            "No version rules configured. Cannot compute the next version."
        )
    root = get_git_root()
    pre_release_check = _release_script_argv("pre_release_check")
    build_script = _release_script_argv("build_script")
    current_version = _determine_canonical_version(root, rules)
    target_version = _bump_semver_version(current_version, level)
    release_message = f"release: Release version {target_version}"
    release_tag = f"v{target_version}"
    changelog_flags = ["--force-write"]
    if level == "patch" and "--include-patch" not in changelog_flags:
        changelog_flags.append("--include-patch")
    if changelog_args:
        for arg in changelog_args:
            if arg not in changelog_flags:
                changelog_flags.append(arg)

    print()
    if pre_release_check:
        _run_release_step(
            level,
            "run pre-release check script",
            lambda: run_command(list(pre_release_check), cwd=root),
        )
    _run_release_step(level, "update versions", lambda: cmd_chver([target_version]))
    if build_script:
        _run_release_step(
            level,
            "run build script",
            lambda: run_command(list(build_script), cwd=root),
        )
    _run_release_step(level, "stage files", lambda: run_git_cmd(["add", "--all"]))
    _run_release_step(
        level,
        "create release commit",
        lambda: _create_release_commit_for_flow(target_version),
    )
    _run_release_step(
        level,
        "create temporary changelog tag",
        lambda: cmd_tg([release_message, release_tag]),
    )
    _run_release_step(
        level, "regenerate changelog", lambda: cmd_changelog(changelog_flags)
    )
    _run_release_step(
        level,
        "delete temporary changelog tag",
        lambda: run_git_cmd(["tag", "--delete", release_tag]),
    )
    _run_release_step(
        level, "stage changelog", lambda: run_git_cmd(["add", "CHANGELOG.md"])
    )
    _run_release_step(
        level,
        "amend release commit",
        lambda: run_git_cmd(["commit", "--amend", "--no-edit"]),
    )

    work_branch = branches["work"]
    develop_branch = branches["develop"]
    master_branch = branches["master"]

    _run_release_step(level, "checkout develop", lambda: cmd_co([develop_branch]))
    _run_release_step(level, "merge work into develop", lambda: cmd_me([work_branch]))
    if dev_release:
        _run_release_step(
            level,
            "tag release on develop",
            lambda: cmd_tg([release_message, release_tag]),
        )
        _run_release_step(
            level,
            "push develop with release tag atomically",
            lambda: _push_release_refs(
                level, target_version, develop_branch, include_tag=True, dev_release=True
            ),
        )
    else:
        _run_release_step(level, "checkout master", lambda: cmd_co([master_branch]))
        _run_release_step(
            level, "merge develop into master", lambda: cmd_me([develop_branch])
        )
        _run_release_step(
            level,
            "tag release on master",
            lambda: cmd_tg([release_message, release_tag]),
        )
        _run_release_step(
            level,
            "push develop branch",
            lambda: _push_release_refs(level, target_version, develop_branch),
        )
        _run_release_step(
            level,
            "push master with release tag atomically",
            lambda: _push_release_refs(level, target_version, master_branch, include_tag=True),
        )
    _run_release_step(level, "return to work", lambda: cmd_co([work_branch]))
    _run_release_step(level, "show release details", lambda: cmd_de([]))
    print(f"Release {target_version} completed successfully.")


## @brief Execute `_execute_backup_flow` runtime logic for Git-Alias CLI.
# @details Executes the `backup` workflow by reusing the release preflight checks, then
#          fast-forward merges configured `work` into configured `develop`, pushes `develop`
#          to its configured remote tracking branch, checks out back to `work`, and prints
#          an explicit success confirmation.
# @return None; raises `ReleaseError` on preflight or workflow failure.
# @satisfies REQ-047, REQ-048, REQ-049
def _execute_backup_flow():
    branches = _ensure_release_prerequisites()
    work_branch = branches["work"]
    develop_branch = branches["develop"]

    level = "backup"
    print()
    _run_release_step(level, "checkout develop", lambda: cmd_co([develop_branch]))
    _run_release_step(level, "merge work into develop", lambda: cmd_me([work_branch]))
    _run_release_step(
        level, "push develop", lambda: run_git_cmd(["push", "origin", develop_branch])
    )
    _run_release_step(level, "return to work", lambda: cmd_co([work_branch]))
    print(
        f"Backup completed successfully: all local '{work_branch}' changes were merged and pushed to remote '{develop_branch}'."
    )


## @brief Execute one release workflow command with unified error propagation to CLI exit codes.
# @details Routes standalone --resume to immutable publication recovery; otherwise
#          delegates to `_execute_release_flow`. O(1) dispatch; converts `ReleaseError`,
#          `VersionDetectionError`, and `CommandExecutionError` into English stderr
#          diagnostics plus non-zero exit status.
# @param level {str} Release level string: `"major"`, `"minor"`, or `"patch"`.
# @param changelog_args {List[str] | None} Optional extra changelog flags forwarded alongside `--force-write`.
# @param dev_release {bool} Develop-scoped release (REQ-045, REQ-200); forwarded to both
#          `_resume_release_flow` and `_execute_release_flow`.
# @return None; side-effects: release workflow execution and stderr diagnostics on failure.
# @exception SystemExit Exit code 1 (or the failing command return code) on workflow failure.
# @satisfies REQ-026, REQ-045, REQ-166, REQ-168, REQ-176, REQ-200, REQ-318, REQ-319, REQ-320
# @return Result emitted by `_run_release_command` according to command contract.
def _run_release_command(level, changelog_args=None, dev_release=False):
    try:
        if changelog_args == ["--resume"]:
            _resume_release_flow(level, dev_release=dev_release)
        else:
            _execute_release_flow(
                level, changelog_args=changelog_args, dev_release=dev_release
            )
    except ReleaseError as exc:
        print(str(exc), file=sys.stderr)
        sys.exit(1)
    except VersionDetectionError as exc:
        print(str(exc), file=sys.stderr)
        sys.exit(1)
    except CommandExecutionError as exc:
        err_text = CommandExecutionError._decode_stream(exc.stderr).strip()
        if err_text:
            print(err_text, file=sys.stderr)
        sys.exit(exc.returncode or 1)
    except RuntimeError as exc:
        print(str(exc), file=sys.stderr)
        sys.exit(1)


## @brief Execute `_run_backup_command` runtime logic for Git-Alias CLI.
# @details Runs the `backup` workflow with the same error propagation strategy used by release commands.
# @return None; exits with status 1 on `ReleaseError`.
# @satisfies REQ-047, REQ-048, REQ-049
def _run_backup_command():
    try:
        _execute_backup_flow()
    except ReleaseError as exc:
        print(str(exc), file=sys.stderr)
        sys.exit(1)


## @brief Execute `_run_reset_with_help` runtime logic for Git-Alias CLI.
# @details Executes `_run_reset_with_help` using deterministic CLI control-flow and explicit error propagation.
# @param base_args Input parameter consumed by `_run_reset_with_help`.
# @param extra Input parameter consumed by `_run_reset_with_help`.
# @return Result emitted by `_run_reset_with_help` according to command contract.
def _run_reset_with_help(base_args, extra):
    args = _to_args(extra)
    if "--help" in args:
        print(RESET_HELP.strip("\n"))
        return
    return run_git_cmd(base_args, args)


## @brief Execute `_reject_extra_arguments` runtime logic for Git-Alias CLI.
# @details Executes `_reject_extra_arguments` using deterministic CLI control-flow and explicit error propagation.
# @param extra Input parameter consumed by `_reject_extra_arguments`.
# @param alias Input parameter consumed by `_reject_extra_arguments`.
# @return Result emitted by `_reject_extra_arguments` according to command contract.
def _reject_extra_arguments(extra, alias):
    args = _to_args(extra)
    if args:
        print(f"git {alias} does not accept positional arguments.", file=sys.stderr)
        sys.exit(1)


## @brief Resolve one release script configuration key into an executable argv list.
# @details Implements REQ-166 and REQ-318: reads the local configuration key,
#          treats blank values as unconfigured, and tokenizes the remaining
#          command line with shell-like quoting into an argv list never
#          evaluated by a shell. Resolution is pure: no subprocess, no file I/O.
# @param config_key {str} Local configuration key holding the script command line.
# @return {Optional[List[str]]} Tokenized argv, or None when the key value is empty.
# @exception RuntimeError Raised when the configured command line is malformed or empty.
# @note Complexity: O(len(value)) tokenization.
# @satisfies REQ-166, REQ-318
# @return Result emitted by `_release_script_argv` according to command contract.
def _release_script_argv(config_key: str) -> Optional[List[str]]:
    value = get_config_value(config_key)
    command_line = value.strip() if isinstance(value, str) else ""
    if not command_line:
        return None
    return _parse_config_command_parts(command_line, config_key)


## @brief Parse release flags and resolve the develop scope or standalone resume.
# @note Standalone --resume, optionally combined with --dev/--develop, returns
#          (["--resume"], True/False); any other resume combination fails.
# @note Complexity: O(N) argv traversal; release step commands come from configuration.
# @details Operands are validated against the whitelist
#          `{"--include-patch", "--dev", "--develop"}` and deduplicated preserving
#          first-occurrence order. Equivalent flags `--dev` and `--develop`
#          (REQ-200) select the develop-scoped workflow (REQ-045) and are never
#          forwarded to the `changelog` step. The removed `--exec` option is
#          rejected by the same whitelist (REQ-322) because the release build and
#          readiness commands come from the local `build_script` and
#          `pre_release_check` keys (REQ-166, REQ-318).
# @param extra {List[str] | None} Raw CLI operands following the release alias token.
# @param alias {str} Release alias name used in English diagnostics (`major`, `minor`, `patch`).
# @return {Tuple[List[str], bool]} `(changelog_args, dev_release)`; the develop scope
#          is True when `--dev`/`--develop` was supplied.
# @exception SystemExit Exit code 1 on unknown or removed options and on an invalid
#          `--resume` combination.
# @satisfies REQ-166, REQ-176, REQ-200, REQ-318, REQ-322
# @return Result emitted by `_parse_release_flags` according to command contract.
def _parse_release_flags(extra, alias):
    args = _to_args(extra)
    if not args:
        return [], False
    dev_flags = ("--dev", "--develop")
    if "--resume" in args:
        remaining = [arg for arg in args if arg != "--resume"]
        resume_is_valid = len(remaining) + 1 == len(args) and all(
            arg in dev_flags for arg in remaining
        )
        if not resume_is_valid:
            joined = ", ".join(args)
            print(
                f"git {alias} accepts --resume only alone or with --dev/--develop (got {joined}).",
                file=sys.stderr,
            )
            sys.exit(1)
        return ["--resume"], any(arg in dev_flags for arg in remaining)
    allowed = {"--include-patch", "--dev", "--develop"}
    unknown = [arg for arg in args if arg not in allowed]
    if unknown:
        joined = ", ".join(unknown)
        print(
            f"git {alias} accepts only --include-patch, --dev/--develop, or standalone --resume (got {joined}).",
            file=sys.stderr,
        )
        sys.exit(1)
    changelog_args: List[str] = []
    seen = set()
    for arg in args:
        if arg not in seen:
            seen.add(arg)
            if arg not in dev_flags:
                changelog_args.append(arg)
    return changelog_args, any(arg in dev_flags for arg in args)


## @brief Execute `_prepare_commit_message` runtime logic for Git-Alias CLI.
# @details Executes `_prepare_commit_message` using deterministic CLI control-flow and explicit error propagation.
# @param extra Input parameter consumed by `_prepare_commit_message`.
# @param alias Input parameter consumed by `_prepare_commit_message`.
# @return Result emitted by `_prepare_commit_message` according to command contract.
def _prepare_commit_message(extra, alias):
    args = _to_args(extra)
    if not args:
        print(f"git {alias} requires a message after the command.", file=sys.stderr)
        sys.exit(1)
    if args[0] == "--help":
        print_command_help(alias)
        sys.exit(0)
    return " ".join(args)


## @brief Normalize conventional commit description formatting.
# @details Applies canonical description normalization for conventional aliases:
# uppercases the first character unless it is numeric and appends a trailing
# period when missing.
# @param description Input parameter consumed by `_normalize_conventional_description`.
# @return Result emitted by `_normalize_conventional_description` according to command contract.
def _normalize_conventional_description(description: str) -> str:
    text = description.strip()
    if not text:
        return text
    if not text[0].isdigit():
        text = text[0].upper() + text[1:]
    if not text.endswith("."):
        text = f"{text}."
    return text


## @brief Execute `_build_conventional_message` runtime logic for Git-Alias CLI.
# @details Executes `_build_conventional_message` using deterministic CLI control-flow and explicit error propagation.
#          The output format is `<type>: <description>` when the effective module is empty,
#          otherwise `<type>(<module>): <description>`.
# @param kind Input parameter consumed by `_build_conventional_message`.
# @param extra Input parameter consumed by `_build_conventional_message`.
# @param alias Input parameter consumed by `_build_conventional_message`.
# @return Result emitted by `_build_conventional_message` according to command contract.
def _build_conventional_message(kind: str, extra, alias: str) -> str:
    text = _prepare_commit_message(extra, alias).strip()
    match = _MODULE_PREFIX_RE.match(text)
    if match:
        scope = match.group("module")
        body = match.group("body").strip()
    else:
        scope = get_config_value("default_commit_module")
        body = text
    scope = scope.strip() if isinstance(scope, str) else ""
    if not body:
        print(
            f"git {alias} requires text after the '<module>:' prefix to complete the message.",
            file=sys.stderr,
        )
        sys.exit(1)
    body = _normalize_conventional_description(body)
    if scope:
        return f"{kind}({scope}): {body}"
    return f"{kind}: {body}"


## @brief Execute `_run_conventional_commit` runtime logic for Git-Alias CLI.
# @details Builds the conventional commit message via `_build_conventional_message`, then validates
#          commitability via `_ensure_commit_ready_with_stage` (auto-stages working-tree changes when
#          staging is empty), then delegates to `_execute_commit` with WIP-amend semantics.
# @param kind `str` — commit type token (e.g., `"fix"`, `"new"`, `"refactor"`).
# @param alias `str` — alias name used in error messages and dispatch.
# @param extra `list | None` — raw CLI extra arguments forwarded to `_build_conventional_message`.
# @return Return value of `_execute_commit`.
# @exception SystemExit Exit code 1 on message validation failure or no-data failure.
# @satisfies REQ-022, DES-007
# @see _build_conventional_message, _ensure_commit_ready_with_stage, _execute_commit, cmd_aa
## @brief Execute `_run_conventional_commit` runtime logic for Git-Alias CLI.
# @details Executes `_run_conventional_commit` using deterministic CLI control-flow and explicit error propagation.
# @param kind Input parameter consumed by `_run_conventional_commit`.
# @param alias Input parameter consumed by `_run_conventional_commit`.
# @param extra Input parameter consumed by `_run_conventional_commit`.
# @return Result emitted by `_run_conventional_commit` according to command contract.
def _run_conventional_commit(kind: str, alias: str, extra):
    message = _build_conventional_message(kind, extra, alias)
    _ensure_commit_ready_with_stage(alias)
    return _execute_commit(message, alias)


## @brief Execute `_execute_commit` runtime logic for Git-Alias CLI.
# @details Executes `_execute_commit` using deterministic CLI control-flow and explicit error propagation.
# @param message Input parameter consumed by `_execute_commit`.
# @param alias Input parameter consumed by `_execute_commit`.
# @param allow_amend Input parameter consumed by `_execute_commit`.
# @return Result emitted by `_execute_commit` according to command contract.
def _execute_commit(message, alias, allow_amend=True):
    if allow_amend:
        amend, reason = _should_amend_existing_commit()
    else:
        amend = False
        reason = "Amend is disabled for this alias."
    if amend:
        print(f"Updating the existing WIP commit (--amend). Reason: {reason}")
    else:
        print(f"Creating a new commit. Reason: {reason}")
    base = ["commit"]
    if amend:
        base.append("--amend")
    base.extend(["-F", "-"])
    try:
        return run_git_cmd(base, input=message, text=True)
    except CommandExecutionError as exc:
        status_lines = _git_status_lines()
        if has_unstaged_changes(status_lines):
            print(
                f"Unable to run git {alias}: unstaged changes are still present.",
                file=sys.stderr,
            )
            sys.exit(exc.returncode or 1)
        if not has_staged_changes(status_lines):
            print(
                f"Unable to run git {alias}: the staging area is empty.",
                file=sys.stderr,
            )
            sys.exit(exc.returncode or 1)
        raise


## @brief Validate clean working tree and empty staging before rollback operations.
# @details Evaluates porcelain status and rejects command execution when unstaged,
#          untracked, or staged entries are present in repository state.
# @param alias `str` — alias name used in user-facing diagnostics.
# @return `True` when both working tree and index are clean.
# @exception SystemExit Exit code 1 when repository is not fully clean.
# @satisfies REQ-133
def _ensure_clean_worktree_and_index(alias: str) -> bool:
    status_lines = _git_status_lines()
    if has_unstaged_changes(status_lines):
        print(
            f"Unable to run git {alias}: working tree is not clean.",
            file=sys.stderr,
        )
        sys.exit(1)
    if has_staged_changes(status_lines):
        print(
            f"Unable to run git {alias}: staging area is not empty.",
            file=sys.stderr,
        )
        sys.exit(1)
    return True


## @brief Resolve rollback target to an existing commit object.
# @details Runs `git rev-parse --verify <target>^{commit}` to support both commit
#          hashes and tag names while normalizing to a full commit hash.
# @param target `str` — user-provided rollback target token.
# @return `str` normalized full commit hash.
# @exception SystemExit Exit code 1 when target does not resolve to a commit.
# @satisfies REQ-134
def _resolve_rollback_target_commit(target: str) -> str:
    try:
        return run_git_text(["rev-parse", "--verify", f"{target}^{{commit}}"]).strip()
    except RuntimeError:
        print(
            f"Unable to run git rollback: target '{target}' is not a valid commit hash or tag.",
            file=sys.stderr,
        )
        sys.exit(1)


## @brief Evaluate commit reachability relation via merge-base ancestry check.
# @details Executes `git merge-base --is-ancestor <ancestor> <descendant>` and
#          returns boolean reachability without raising on non-zero status.
# @param ancestor_commit `str` — commit expected to be ancestor.
# @param descendant_ref `str` — descendant git reference.
# @return `True` when `ancestor_commit` is reachable from `descendant_ref`.
def _is_commit_ancestor(ancestor_commit: str, descendant_ref: str) -> bool:
    proc = _run_checked(
        ["git", "merge-base", "--is-ancestor", ancestor_commit, descendant_ref],
        check=False,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    return proc.returncode == 0


## @brief Validate whether a token matches git hexadecimal commit-hash syntax.
# @details Accepts abbreviated/full hexadecimal hashes with length 4..40.
# @param token `str` — CLI token to validate.
# @return `True` when token is a hexadecimal commit-hash candidate.
def _is_commit_hash_token(token: str) -> bool:
    return bool(re.fullmatch(r"[0-9a-fA-F]{4,40}", token))


## @brief Check whether a tag exists in local repository references.
# @details Verifies `refs/tags/<tag_name>` presence using internal ref lookup.
# @param tag_name `str` — tag name token.
# @return `True` when local tag reference exists.
def _tag_exists(tag_name: str) -> bool:
    return _ref_exists(f"refs/tags/{tag_name}")


## @brief Abort a rollback after a failed version restore and restore pre-rollback state.
# @details Executes `git revert --abort` to discard already applied inverse revert
#          changes, prints an explicit English diagnostic prefixed with
#          `Unable to run git rollback: the version restore failed`, and terminates
#          with exit code 1 before the revert commit is created. Prefers
#          `CommandExecutionError` stderr payload as diagnostic detail when present.
# @param failure `BaseException` — `SystemExit` or `RuntimeError` raised by the
#             version restore pipeline (`cmd_chver` or the staging step).
# @return None; side-effects: `git revert --abort` subprocess and stderr output.
# @exception SystemExit Always exits with status 1.
# @satisfies REQ-174
def _abort_rollback_version_restore(failure):
    _run_checked(
        ["git", "revert", "--abort"],
        check=False,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    detail = ""
    stderr_text = getattr(failure, "stderr", None)
    if stderr_text is not None:
        detail = CommandExecutionError._decode_stream(stderr_text).strip()
    message = (
        "Unable to run git rollback: the version restore failed and the revert was aborted."
    )
    if detail:
        print(f"{message} {detail}", file=sys.stderr)
    else:
        print(message, file=sys.stderr)
    sys.exit(1)


## @brief Determine whether local self-management commands are supported on current host.
# @details Evaluates the current Python platform token and accepts only Linux hosts.
# @return `True` when runtime platform is Linux; otherwise `False`.
# @satisfies REQ-001 REQ-002 REQ-129 REQ-130
def _is_linux_platform() -> bool:
    return sys.platform.startswith("linux")


## @brief Print manual self-management command for non-Linux runtimes.
# @details Emits deterministic guidance without executing local `uv tool` commands.
# @param action `str` — management action token (`upgrade` or `uninstall`).
# @param command_tokens `Tuple[str, ...]` — command token sequence to print verbatim.
# @return None.
# @satisfies REQ-129 REQ-130
def _print_non_linux_management_command(
    action: str,
    command_tokens: Tuple[str, ...],
) -> None:
    print(
        f"Command '--{action}' is supported only on Linux for local execution.",
        file=sys.stderr,
    )
    print(f"Run manually: {' '.join(command_tokens)}", file=sys.stderr)


## @brief Execute `upgrade_self` runtime logic for Git-Alias CLI.
# @details Selects the GitHub tagged-release source (REQ-201) when `github` is
#          True and the PyPI default release (REQ-001) otherwise. The GitHub
#          path resolves the newest release tag via
#          `_fetch_github_latest_release_tag` (REQ-208) and installs through
#          `_build_github_upgrade_command` (REQ-209); resolution failure
#          aborts with an explicit English error and non-zero exit before any
#          install (REQ-210). When `force` is True the executed argv appends
#          `UV_TOOL_FORCE_UPGRADE_OPTIONS` (`--force --reinstall --refresh`)
#          so uv performs a forced download plus complete reinstallation
#          (REQ-236, REQ-237); when `force` is False the standard unforced
#          install/update process runs (REQ-001, REQ-209). Non-Linux hosts
#          receive the exact manual command matching the selected source and
#          force mode without local execution (REQ-129).
# @param repo_root Input parameter consumed by `upgrade_self`.
# @param github {bool} When True, upgrade from the newest GitHub release tag
#        (REQ-201, REQ-208, REQ-209) instead of the default PyPI release
#        (REQ-001).
# @param force {bool} When True, append the uv forcing options
#        `--force --reinstall --refresh` to the selected install argv
#        (REQ-236, REQ-237); when False, run the standard install with no
#        forcing options (REQ-001, REQ-209).
# @return None; side-effect: uv tool install subprocess, manual-command
#         guidance, or English abort diagnostic with non-zero exit.
# @exception SystemExit Exit code 1 when REQ-208 tag resolution fails (REQ-210).
# @satisfies REQ-001, REQ-129, REQ-201, REQ-208, REQ-209, REQ-210, REQ-236, REQ-237
def upgrade_self(
    repo_root: Optional[Path] = None,
    github: bool = False,
    force: bool = False,
):
    del repo_root
    if not github:
        command = UV_TOOL_UPGRADE_COMMAND
        if force:
            command = UV_TOOL_UPGRADE_COMMAND + UV_TOOL_FORCE_UPGRADE_OPTIONS
        if not _is_linux_platform():
            _print_non_linux_management_command("upgrade", command)
            return
        _run_checked(list(command))
        return
    latest_tag = _fetch_github_latest_release_tag(
        timeout_seconds=VERSION_CHECK_TIMEOUT_SECONDS
    )
    if not latest_tag:
        print(
            "Unable to resolve the latest GitHub release tag: upgrade aborted.",
            file=sys.stderr,
        )
        sys.exit(1)
    command = _build_github_upgrade_command(latest_tag, force=force)
    if not _is_linux_platform():
        _print_non_linux_management_command("upgrade", command)
        return
    _run_checked(list(command))


## @brief Remove update-check idle-time cache artifacts before Linux uninstall.
# @details Deletes `VERSION_CHECK_CACHE_FILE` when present and then removes the
#          parent directory, enforcing deterministic failure on invalid path types
#          or non-empty cache directory state.
# @return None.
# @satisfies REQ-002
def _remove_version_check_cache_artifacts() -> None:
    cache_file = VERSION_CHECK_CACHE_FILE
    cache_directory = cache_file.parent
    if cache_file.exists():
        if not cache_file.is_file():
            raise RuntimeError(
                f"Uninstall failed: cache path is not a file: {cache_file}"
            )
        cache_file.unlink()
    if cache_directory.exists():
        if not cache_directory.is_dir():
            raise RuntimeError(
                f"Uninstall failed: cache directory path is invalid: {cache_directory}"
            )
        try:
            cache_directory.rmdir()
        except OSError as exc:
            raise RuntimeError(
                f"Uninstall failed: unable to remove cache directory {cache_directory}: {exc}"
            ) from exc


## @brief Execute `uninstall_self` runtime logic for Git-Alias CLI.
# @details Executes `uninstall_self` using deterministic CLI control-flow and explicit error propagation.
# @return Result emitted by `uninstall_self` according to command contract.
# @satisfies REQ-002 REQ-130
def uninstall_self():
    if not _is_linux_platform():
        _print_non_linux_management_command("uninstall", UV_TOOL_UNINSTALL_COMMAND)
        return
    _remove_version_check_cache_artifacts()
    _run_checked(list(UV_TOOL_UNINSTALL_COMMAND))


## @brief Execute `cmd_aa` runtime logic for Git-Alias CLI.
# @details Executes `cmd_aa` using deterministic CLI control-flow and explicit error propagation.
# @param extra Input parameter consumed by `cmd_aa`.
# @return Result emitted by `cmd_aa` according to command contract.
def cmd_aa(extra):
    status_lines = _git_status_lines()
    if not has_unstaged_changes(status_lines):
        print("No changes are available to add to the staging area.", file=sys.stderr)
        sys.exit(1)
    return run_git_cmd(["add", "--all"], extra)


## @brief Execute `cmd_ra` runtime logic for Git-Alias CLI.
# @details Executes `cmd_ra` using deterministic CLI control-flow and explicit error propagation.
# @param extra Input parameter consumed by `cmd_ra`.
# @return Result emitted by `cmd_ra` according to command contract.
def cmd_ra(extra):
    if extra:
        args = _to_args(extra)
        if args == ["--help"]:
            print_command_help("ra")
            return
        print("git ra does not accept positional arguments.", file=sys.stderr)
        sys.exit(1)
    work_branch = get_branch("work")
    try:
        current_branch = _current_branch_name()
    except ReleaseError:
        print("git ra requires an active branch head.", file=sys.stderr)
        sys.exit(1)
    if current_branch != work_branch:
        print(
            f"git ra must be executed from the {work_branch} branch (current: {current_branch}).",
            file=sys.stderr,
        )
        sys.exit(1)
    _ensure_commit_ready("ra")
    return run_git_cmd(["reset", "--mixed"], [])


## @brief Execute `cmd_ar` runtime logic for Git-Alias CLI.
# @details Executes `cmd_ar` using deterministic CLI control-flow and explicit error propagation.
# @param extra Input parameter consumed by `cmd_ar`.
# @return Result emitted by `cmd_ar` according to command contract.
def cmd_ar(extra):
    args = _to_args(extra)
    master_branch = get_branch("master")
    tag = capture_git_output(["describe", master_branch])
    filename = f"{tag}.tar.gz"
    archive_cmd = ["git", "archive", master_branch, "--prefix=/"] + args
    with _run_checked(
        archive_cmd, stdout=subprocess.PIPE, stream=True
    ) as archive_proc:
        with open(filename, "wb") as output_io:
            gzip_proc = _run_checked(
                ["gzip"], stdin=archive_proc.stdout, stdout=output_io
            )
        if archive_proc.stdout is not None:
            archive_proc.stdout.close()
        archive_proc.wait()
    return gzip_proc


## @brief Execute `cmd_br` runtime logic for Git-Alias CLI.
# @details Executes `cmd_br` using deterministic CLI control-flow and explicit error propagation.
# @param extra Input parameter consumed by `cmd_br`.
# @return Result emitted by `cmd_br` according to command contract.
def cmd_br(extra):
    return run_git_cmd(["branch"], extra)


## @brief Execute `cmd_bd` runtime logic for Git-Alias CLI.
# @details Accepts one branch target with optional `--force`, resolves worktree associations,
#          deletes an associated worktree before deleting the branch, and uses forced git delete
#          flags only when explicitly requested.
# @param extra `list | None` — requires exactly one branch target or `--help`.
# @return Return value from `run_git_cmd` when only the branch is deleted; otherwise `None`.
# @exception SystemExit Exit code 1 on invalid operands or preflight failure.
# @satisfies REQ-019, REQ-138, REQ-139, REQ-140, REQ-141, REQ-142, REQ-144, REQ-145
def cmd_bd(extra):
    args = _to_args(extra)
    if args == ["--help"]:
        print_command_help("bd")
        return
    branch_name, force_delete = _parse_bd_target(args)
    associations = _list_worktree_associations()
    worktree_info = _find_worktree_for_branch(branch_name, associations)
    if worktree_info is not None:
        _delete_associated_branch_and_worktree(worktree_info, "bd", force_delete)
        return
    branch_cmd = ["branch", "-d", branch_name]
    if force_delete:
        branch_cmd = ["branch", "-D", branch_name]
    else:
        _preflight_branch_delete(branch_name, "bd")
    return run_git_cmd(branch_cmd)


## @brief Execute `cmd_ck` runtime logic for Git-Alias CLI.
# @details Executes `cmd_ck` using deterministic CLI control-flow and explicit error propagation.
# @param extra Input parameter consumed by `cmd_ck`.
# @return Result emitted by `cmd_ck` according to command contract.
def cmd_ck(extra):
    return run_git_cmd(["diff", "--check"], extra)


## @brief Execute `_ensure_commit_ready` runtime logic for Git-Alias CLI.
# @details Executes `_ensure_commit_ready` using deterministic CLI control-flow and explicit error propagation.
# @param alias Input parameter consumed by `_ensure_commit_ready`.
# @return Result emitted by `_ensure_commit_ready` according to command contract.
def _ensure_commit_ready(alias):
    status_lines = _git_status_lines()
    if has_unstaged_changes(status_lines):
        print(
            f"Unable to run git {alias}: unstaged changes are still present.",
            file=sys.stderr,
        )
        sys.exit(1)
    if not has_staged_changes(status_lines):
        print(f"Unable to run git {alias}: the staging area is empty.", file=sys.stderr)
        sys.exit(1)
    return True


## @brief Commit-readiness guard with automatic working-tree staging for Git-Alias CLI.
# @details Evaluates working-tree and staging state via `_git_status_lines()`.
#          Control flow:
#          1. Both staging and working-tree empty → print error and `sys.exit(1)`.
#          2. Staging empty AND working-tree dirty → invoke `cmd_aa([])` to stage all changes.
#          3. Staging non-empty → return `True` immediately.
#          Satisfies REQ-021, REQ-022, DES-007: auto-stage path for `wip` and conventional commit aliases.
#          Does NOT enforce "no unstaged changes" constraint; that constraint belongs to `_ensure_commit_ready`.
# @param alias `str` — alias name used in error messages.
# @return `True` when staging is confirmed non-empty after optional `cmd_aa` execution.
# @exception SystemExit Exit code 1 when both working-tree and staging have no committable data.
# @satisfies REQ-021, REQ-022, DES-007
# @see _ensure_commit_ready, cmd_aa, has_staged_changes, has_unstaged_changes
## @brief Execute `_ensure_commit_ready_with_stage` runtime logic for Git-Alias CLI.
# @details Executes `_ensure_commit_ready_with_stage` using deterministic CLI control-flow and explicit error propagation.
# @param alias Input parameter consumed by `_ensure_commit_ready_with_stage`.
# @return Result emitted by `_ensure_commit_ready_with_stage` according to command contract.
def _ensure_commit_ready_with_stage(alias):
    status_lines = _git_status_lines()
    staged = has_staged_changes(status_lines)
    unstaged = has_unstaged_changes(status_lines)
    if not staged and not unstaged:
        print(
            f"Unable to run git {alias}: no changes to commit (working tree and staging area are both empty).",
            file=sys.stderr,
        )
        sys.exit(1)
    if not staged:
        cmd_aa([])
    return True


## @brief Execute `cmd_cm` runtime logic for Git-Alias CLI.
# @details Executes `cmd_cm` using deterministic CLI control-flow and explicit error propagation.
# @param extra Input parameter consumed by `cmd_cm`.
# @return Result emitted by `cmd_cm` according to command contract.
def cmd_cm(extra):
    message = _prepare_commit_message(extra, "cm")
    _ensure_commit_ready("cm")
    return _execute_commit(message, "cm")


## @brief Execute `cmd_wip` runtime logic for Git-Alias CLI.
# @details Validates commitability via `_ensure_commit_ready_with_stage` (auto-stages working-tree changes
#          when staging is empty); rejects positional arguments except `--help`; emits fixed message
#          `wip: work in progress.` and delegates to `_execute_commit` with WIP-amend semantics.
# @param extra `list | None` — CLI extra arguments; only `["--help"]` is accepted.
# @return Return value of `_execute_commit`, or `None` on `--help`.
# @exception SystemExit Exit code 1 on positional argument or no-data failure; exit code 0 on `--help`.
# @satisfies REQ-021, DES-007
# @see _ensure_commit_ready_with_stage, _execute_commit, cmd_aa
def cmd_wip(extra):
    if extra:
        args = _to_args(extra)
        if args == ["--help"]:
            print_command_help("wip")
            return
        print("git wip does not accept positional arguments.", file=sys.stderr)
        sys.exit(1)
    _ensure_commit_ready_with_stage("wip")
    message = "wip: work in progress."
    return _execute_commit(message, "wip")


## @brief Execute `cmd_release` runtime logic for Git-Alias CLI.
# @details Executes `cmd_release` using deterministic CLI control-flow and explicit error propagation.
# @param extra Input parameter consumed by `cmd_release`.
# @return Result emitted by `cmd_release` according to command contract.
def cmd_release(extra):
    args = _to_args(extra)
    if args:
        if args == ["--help"]:
            print_command_help("release")
            return
        print("git release does not accept positional arguments.", file=sys.stderr)
        sys.exit(1)
    _ensure_commit_ready("release")
    rules = get_version_rules()
    if not rules:
        print("No version rules configured.", file=sys.stderr)
        sys.exit(1)
    root = get_git_root()
    try:
        version = _determine_canonical_version(root, rules)
    except VersionDetectionError as exc:
        print(str(exc), file=sys.stderr)
        sys.exit(1)
    message = f"release: Release version {version}"
    return _execute_commit(message, "release")


## @brief Execute `cmd_new` runtime logic for Git-Alias CLI.
# @details Executes `cmd_new` using deterministic CLI control-flow and explicit error propagation.
# @param extra Input parameter consumed by `cmd_new`.
# @return Result emitted by `cmd_new` according to command contract.
def cmd_new(extra):
    return _run_conventional_commit("new", "new", extra)


## @brief Execute `cmd_refactor` runtime logic for Git-Alias CLI.
# @details Executes `cmd_refactor` using deterministic CLI control-flow and explicit error propagation.
# @param extra Input parameter consumed by `cmd_refactor`.
# @return Result emitted by `cmd_refactor` according to command contract.
def cmd_refactor(extra):
    return _run_conventional_commit("refactor", "refactor", extra)


## @brief Execute `cmd_fix` runtime logic for Git-Alias CLI.
# @details Executes `cmd_fix` using deterministic CLI control-flow and explicit error propagation.
# @param extra Input parameter consumed by `cmd_fix`.
# @return Result emitted by `cmd_fix` according to command contract.
def cmd_fix(extra):
    return _run_conventional_commit("fix", "fix", extra)


## @brief Execute `cmd_change` runtime logic for Git-Alias CLI.
# @details Executes `cmd_change` using deterministic CLI control-flow and explicit error propagation.
# @param extra Input parameter consumed by `cmd_change`.
# @return Result emitted by `cmd_change` according to command contract.
def cmd_change(extra):
    return _run_conventional_commit("change", "change", extra)


## @brief Execute `cmd_implement` runtime logic for Git-Alias CLI.
# @details Executes `cmd_implement` using deterministic CLI control-flow and explicit error propagation.
# @param extra Input parameter consumed by `cmd_implement`.
# @return Result emitted by `cmd_implement` according to command contract.
def cmd_implement(extra):
    return _run_conventional_commit("implement", "implement", extra)


## @brief Execute `cmd_docs` runtime logic for Git-Alias CLI.
# @details Executes `cmd_docs` using deterministic CLI control-flow and explicit error propagation.
# @param extra Input parameter consumed by `cmd_docs`.
# @return Result emitted by `cmd_docs` according to command contract.
def cmd_docs(extra):
    return _run_conventional_commit("docs", "docs", extra)


## @brief Execute `cmd_style` runtime logic for Git-Alias CLI.
# @details Executes `cmd_style` using deterministic CLI control-flow and explicit error propagation.
# @param extra Input parameter consumed by `cmd_style`.
# @return Result emitted by `cmd_style` according to command contract.
def cmd_style(extra):
    return _run_conventional_commit("style", "style", extra)


## @brief Execute `cmd_revert` runtime logic for Git-Alias CLI.
# @details Executes `cmd_revert` using deterministic CLI control-flow and explicit error propagation.
# @param extra Input parameter consumed by `cmd_revert`.
# @return Result emitted by `cmd_revert` according to command contract.
def cmd_revert(extra):
    return _run_conventional_commit("revert", "revert", extra)


## @brief Execute `cmd_rollback` runtime logic for Git-Alias CLI.
# @details Validates clean preconditions, resolves a reachable commit target from
#          current branch, runs the release-style canonical version detection as
#          pre-flight check, applies inverse changes with `git revert --no-commit
#          <target>..HEAD`, restores the pre-rollback application version through
#          the `chver` flow, stages restored files with `git add --all`, and creates
#          one non-amend conventional `revert` commit preserving the pre-rollback
#          version. A failed version restore aborts via `git revert --abort`.
# @param extra `list | None` — requires exactly one rollback target or `--help`.
# @return Return value emitted by `_execute_commit`.
# @exception SystemExit Exit code 1 on argument, precondition, resolution, ancestry,
#             version-check, revert, or version-restore failures.
# @satisfies REQ-132, REQ-133, REQ-134, REQ-135, REQ-169, REQ-170, REQ-171, REQ-172, REQ-173, REQ-174
def cmd_rollback(extra):
    args = _to_args(extra)
    if args == ["--help"]:
        print_command_help("rollback")
        return
    if len(args) != 1:
        print(
            "git rollback requires exactly one target: git rollback <commit-hash|tag>.",
            file=sys.stderr,
        )
        sys.exit(1)
    target = args[0]
    if not _is_commit_hash_token(target) and not _tag_exists(target):
        print(
            f"Unable to run git rollback: target '{target}' must be an existing tag or a commit hash.",
            file=sys.stderr,
        )
        sys.exit(1)
    _ensure_clean_worktree_and_index("rollback")
    resolved_target = _resolve_rollback_target_commit(target)
    if not _is_commit_ancestor(resolved_target, "HEAD"):
        print(
            f"Unable to run git rollback: target '{target}' is not reachable from the current branch HEAD.",
            file=sys.stderr,
        )
        sys.exit(1)
    current_head = run_git_text(["rev-parse", "--verify", "HEAD"]).strip()
    if resolved_target == current_head:
        print(
            "Unable to run git rollback: target matches HEAD and produces no rollback commit.",
            file=sys.stderr,
        )
        sys.exit(1)
    rules = get_version_rules()
    if not rules:
        print(
            "Unable to run git rollback: no version rules configured. "
            "Cannot preserve the application version.",
            file=sys.stderr,
        )
        sys.exit(1)
    root = get_git_root()
    try:
        current_version = _determine_canonical_version(root, rules)
    except VersionDetectionError as exc:
        print(
            f"Unable to run git rollback: the version check failed. {exc}",
            file=sys.stderr,
        )
        sys.exit(1)
    try:
        run_git_cmd(["revert", "--no-commit", f"{resolved_target}..HEAD"])
    except CommandExecutionError as exc:
        _run_checked(
            ["git", "revert", "--abort"],
            check=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        message = CommandExecutionError._decode_stream(exc.stderr).strip()
        if message:
            print(message, file=sys.stderr)
        else:
            print("Unable to run git rollback: revert operation failed.", file=sys.stderr)
        sys.exit(exc.returncode or 1)
    try:
        cmd_chver([current_version])
        run_git_cmd(["add", "--all"])
    except (SystemExit, RuntimeError) as exc:
        _abort_rollback_version_restore(exc)
    commit_message = f"revert: Roll back branch to {target} ({resolved_target})."
    result = _execute_commit(commit_message, "rollback", allow_amend=False)
    _ensure_clean_worktree_and_index("rollback")
    return result


## @brief Execute `cmd_misc` runtime logic for Git-Alias CLI.
# @details Executes `cmd_misc` using deterministic CLI control-flow and explicit error propagation.
# @param extra Input parameter consumed by `cmd_misc`.
# @return Result emitted by `cmd_misc` according to command contract.
def cmd_misc(extra):
    return _run_conventional_commit("misc", "misc", extra)


## @brief Execute `cmd_cover` runtime logic for Git-Alias CLI.
# @details Executes `cmd_cover` using deterministic CLI control-flow and explicit error propagation.
# @param extra Input parameter consumed by `cmd_cover`.
# @return Result emitted by `cmd_cover` according to command contract.
def cmd_cover(extra):
    return _run_conventional_commit("cover", "cover", extra)


## @brief Execute `cmd_co` runtime logic for Git-Alias CLI.
# @details Executes `cmd_co` using deterministic CLI control-flow and explicit error propagation.
# @param extra Input parameter consumed by `cmd_co`.
# @return Result emitted by `cmd_co` according to command contract.
def cmd_co(extra):
    return run_git_cmd(["checkout"], extra)


## @brief Resolve the environment-selected diff tool argv for extcmd injection.
# @details Applies the REQ-186/REQ-187/REQ-188 selection to the
#          `diff_command`/`diff_command_gfx` pair: graphical environments
#          select `diff_command_gfx` when non-empty, otherwise the terminal
#          `diff_command` applies. Unlike `_environment_config_command_parts`,
#          an empty effective value returns `[]` per REQ-190 so the caller runs
#          plain `git difftool -d` without overriding git's configured tool.
#          Non-empty values are tokenized and validated through
#          `_validated_config_command_parts`.
# @return {List[str]} Validated argv tokens of the selected diff tool; `[]` when unconfigured.
# @exception RuntimeError Raised when the selected non-empty command is invalid or unavailable.
# @note Complexity: O(1) excluding PATH lookup inside validation.
# @satisfies REQ-187, REQ-188, REQ-190
def _selected_diff_command_parts() -> List[str]:
    if _is_graphical_environment():
        gfx_value = get_config_value("diff_command_gfx")
        if gfx_value:
            return _validated_config_command_parts("diff_command_gfx", gfx_value)
    terminal_value = get_config_value("diff_command")
    if not terminal_value:
        return []
    return _validated_config_command_parts("diff_command", terminal_value)


## @brief Execute `git difftool -d` with the configured tool injected as extcmd.
# @details Implements REQ-189/REQ-190: builds the `git difftool -d` base argv,
#          appends `--extcmd=<selected command>` when
#          `_selected_diff_command_parts` returns a non-empty tool so the
#          environment-selected galias tool overrides git's configured diff
#          tool, then appends the ordered ref operands and forwarded extras.
#          An empty tool runs plain `git difftool -d` (REQ-190). Execution goes
#          through `run_command` so every visual diff alias passes the same
#          environment-detection and subprocess-interception path (REQ-185).
# @param refs {List[str]} Ordered git ref operands appended after the difftool argv.
# @param extra {Optional[List[str]]} Additional CLI operands forwarded unchanged.
# @return Result of `run_command` for the delegated `git difftool` subprocess.
# @exception RuntimeError Raised when the selected diff command is invalid or unavailable.
# @note `--extcmd` tokens are joined with single spaces; embedded whitespace
#       inside tokens is not re-quoted.
# @note Complexity: O(1) excluding PATH lookup and subprocess runtime.
# @satisfies REQ-189, REQ-190, REQ-185, REQ-187
def _run_configured_diff(refs, extra=None):
    argv: List[str] = list(GIT_DIFFTOOL_COMMAND)
    tool_parts = _selected_diff_command_parts()
    if tool_parts:
        argv.append("--extcmd=" + " ".join(tool_parts))
    return run_command(argv + list(refs) + _to_args(extra))


## @brief Execute `cmd_dc` runtime logic for Git-Alias CLI.
# @details Validates the REQ-182 arity contract (exactly one required `<ref>`
# plus at most one optional `<ref_prev>`), resolves an omitted `<ref_prev>` to
# the commit preceding `<ref>` via the git revision expression `<ref>~1` per
# REQ-184, and delegates to `_run_configured_diff([<ref_prev>, <ref>])` so the
# rendered diff direction is always `<ref_prev>` -> `<ref>` and never inverted
# per REQ-183, using the environment-resolved diff command per REQ-189.
# @param extra {Optional[List[str]]} CLI operands after `dc`; accepted arity is
# 1 or 2 positional git refs (`--help` is intercepted by `main` before dispatch).
# @return Result of `_run_configured_diff` for the delegated diff subprocess.
# @exception SystemExit Exit code 1 on zero or more than two positional refs.
# @note Complexity: O(1); no CLI-side ref resolution or transformation.
# @satisfies REQ-182, REQ-183, REQ-184, REQ-189
def cmd_dc(extra):
    args = _to_args(extra)
    if len(args) == 0 or len(args) > 2:
        print(
            "git dc requires one ref and an optional previous ref:"
            " git dc <ref> [<ref_prev>]",
            file=sys.stderr,
        )
        sys.exit(1)
    ref = args[0]
    ref_prev = args[1] if len(args) == 2 else f"{ref}~1"
    return _run_configured_diff([ref_prev, ref])


## @brief Execute `cmd_dcc` runtime logic for Git-Alias CLI.
# @details Delegates refs `HEAD~1 HEAD` to `_run_configured_diff` so the diff
# runs through the environment-resolved configured diff command per REQ-189.
# @param extra Input parameter consumed by `cmd_dcc`.
# @return Result emitted by `_run_configured_diff` according to command contract.
# @satisfies REQ-037, REQ-189
def cmd_dcc(extra):
    return _run_configured_diff(["HEAD~1", "HEAD"], extra)


## @brief Execute `cmd_dccc` runtime logic for Git-Alias CLI.
# @details Delegates refs `HEAD~2 HEAD` to `_run_configured_diff` so the diff
# runs through the environment-resolved configured diff command per REQ-189.
# @param extra Input parameter consumed by `cmd_dccc`.
# @return Result emitted by `_run_configured_diff` according to command contract.
# @satisfies REQ-038, REQ-189
def cmd_dccc(extra):
    return _run_configured_diff(["HEAD~2", "HEAD"], extra)


## @brief Execute `cmd_de` runtime logic for Git-Alias CLI.
# @details Executes `cmd_de` using deterministic CLI control-flow and explicit error propagation.
# @param extra Input parameter consumed by `cmd_de`.
# @return Result emitted by `cmd_de` according to command contract.
def cmd_de(extra):
    return run_git_cmd(["describe"], extra)


## @brief Execute `cmd_di` runtime logic for Git-Alias CLI.
# @details Executes `cmd_di` using deterministic CLI control-flow and explicit error propagation.
# @param extra Input parameter consumed by `cmd_di`.
# @return Result emitted by `cmd_di` according to command contract.
def cmd_di(extra):
    return run_git_cmd(["checkout", "--"], extra)


## @brief Execute `cmd_diyou` runtime logic for Git-Alias CLI.
# @details Executes `cmd_diyou` using deterministic CLI control-flow and explicit error propagation.
# @param extra Input parameter consumed by `cmd_diyou`.
# @return Result emitted by `cmd_diyou` according to command contract.
def cmd_diyou(extra):
    return run_git_cmd(["checkout", "--ours", "--"], extra)


## @brief Execute `cmd_dime` runtime logic for Git-Alias CLI.
# @details Executes `cmd_dime` using deterministic CLI control-flow and explicit error propagation.
# @param extra Input parameter consumed by `cmd_dime`.
# @return Result emitted by `cmd_dime` according to command contract.
def cmd_dime(extra):
    return run_git_cmd(["checkout", "--theirs", "--"], extra)


## @brief Execute `cmd_dwc` runtime logic for Git-Alias CLI.
# @details Delegates ref `HEAD` to `_run_configured_diff` so the working-tree
# vs HEAD diff runs through the environment-resolved diff command per REQ-189.
# @param extra Input parameter consumed by `cmd_dwc`.
# @return Result emitted by `_run_configured_diff` according to command contract.
# @satisfies REQ-037, REQ-189
def cmd_dwc(extra):
    return _run_configured_diff(["HEAD"], extra)


## @brief Execute `cmd_dw` runtime logic for Git-Alias CLI.
# @details Validates exactly one positional git ref, then delegates `<ref>` to
# `_run_configured_diff` for the working-tree vs ref diff through the
# environment-resolved diff command per REQ-189.
# @param extra Input parameter consumed by `cmd_dw`.
# @return Result emitted by `_run_configured_diff` according to command contract.
# @exception SystemExit Exit code 1 on zero or multiple positional refs.
# @satisfies REQ-037, REQ-189
def cmd_dw(extra):
    args = _to_args(extra)
    if len(args) != 1:
        print("git dw requires exactly one ref: git dw <ref>", file=sys.stderr)
        sys.exit(1)
    return _run_configured_diff([args[0]])


## @brief Execute `cmd_dwcc` runtime logic for Git-Alias CLI.
# @details Delegates ref `HEAD~1` to `_run_configured_diff` so the working-tree
# vs penultimate-commit diff runs through the environment-resolved diff
# command per REQ-189.
# @param extra Input parameter consumed by `cmd_dwcc`.
# @return Result emitted by `_run_configured_diff` according to command contract.
# @satisfies REQ-038, REQ-189
def cmd_dwcc(extra):
    return _run_configured_diff(["HEAD~1"], extra)


## @brief Execute `cmd_dcd` runtime logic for Git-Alias CLI.
# @details Resolves configured `develop` and `work` branch names, then delegates
# refs `<develop> <work>` to `_run_configured_diff` per REQ-119/REQ-189.
# @param extra Input parameter consumed by `cmd_dcd`.
# @return Result emitted by `_run_configured_diff` according to command contract.
# @satisfies REQ-119, REQ-189
def cmd_dcd(extra):
    develop_branch = get_branch("develop")
    work_branch = get_branch("work")
    return _run_configured_diff([develop_branch, work_branch], extra)


## @brief Execute `cmd_dcm` runtime logic for Git-Alias CLI.
# @details Resolves configured `master` and `work` branch names, then delegates
# refs `<master> <work>` to `_run_configured_diff` per REQ-119/REQ-189.
# @param extra Input parameter consumed by `cmd_dcm`.
# @return Result emitted by `_run_configured_diff` according to command contract.
# @satisfies REQ-119, REQ-189
def cmd_dcm(extra):
    master_branch = get_branch("master")
    work_branch = get_branch("work")
    return _run_configured_diff([master_branch, work_branch], extra)


## @brief Execute `cmd_ddm` runtime logic for Git-Alias CLI.
# @details Resolves configured `master` and `develop` branch names, then
# delegates refs `<master> <develop>` to `_run_configured_diff` per
# REQ-119/REQ-189.
# @param extra Input parameter consumed by `cmd_ddm`.
# @return Result emitted by `_run_configured_diff` according to command contract.
# @satisfies REQ-119, REQ-189
def cmd_ddm(extra):
    master_branch = get_branch("master")
    develop_branch = get_branch("develop")
    return _run_configured_diff([master_branch, develop_branch], extra)


## @brief Execute `cmd_ed` runtime logic for Git-Alias CLI.
# @details Executes `cmd_ed` using deterministic CLI control-flow and explicit error propagation.
# @param extra Input parameter consumed by `cmd_ed`.
# @return Result emitted by `cmd_ed` according to command contract.
def cmd_ed(extra):
    paths = _to_args(extra)
    if not paths:
        print("git ed requires at least one file path", file=sys.stderr)
        sys.exit(1)
    for path in paths:
        expanded = os.path.expanduser(path)
        run_editor_command([expanded])


## @brief Execute `cmd_fe` runtime logic for Git-Alias CLI.
# @details Executes `cmd_fe` using deterministic CLI control-flow and explicit error propagation.
# @param extra Input parameter consumed by `cmd_fe`.
# @return Result emitted by `cmd_fe` according to command contract.
def cmd_fe(extra):
    return run_git_cmd(["fetch"], extra)


## @brief Execute `cmd_feall` runtime logic for Git-Alias CLI.
# @details Executes `cmd_feall` using deterministic CLI control-flow and explicit error propagation.
# @param extra Input parameter consumed by `cmd_feall`.
# @return Result emitted by `cmd_feall` according to command contract.
def cmd_feall(extra):
    return cmd_fe(["--all", "--tags", "--prune"] + _to_args(extra))


## @brief Execute preflight verifications and fast-forward synchronization flow for `get`.
# @details Validates clean index/worktree, current-branch=work, develop contains work HEAD,
#          local develop and master aligned on same commit, local develop/master HEADs already
#          present on their origin counterparts, and origin/develop strictly ahead of local
#          develop. Then fetches origin master into local master fast-forward (with tags),
#          fetches origin develop into local develop fast-forward (with tags), and finally
#          fast-forward merges local develop into the currently checked out work branch.
#          Any verification failure or git step error raises `ReleaseError` with an explicit
#          English diagnostic.
# @return None; raises `ReleaseError` on any verification or execution failure.
# @satisfies REQ-146, REQ-148, REQ-149, REQ-150, REQ-151, REQ-152, REQ-153, REQ-154, REQ-155
def _execute_get_flow():
    master_branch = get_branch("master")
    develop_branch = get_branch("develop")
    work_branch = get_branch("work")
    for name in (master_branch, develop_branch, work_branch):
        if not _local_branch_exists(name):
            raise ReleaseError(f"Unable to run get: missing local branch '{name}'.")
    status = _git_status_lines()
    if has_staged_changes(status):
        raise ReleaseError(
            "Staging area is not empty. Clean the index before running 'get'."
        )
    if has_unstaged_changes(status):
        raise ReleaseError(
            "Working tree has pending changes. Commit or discard them before running 'get'."
        )
    current_branch = _current_branch_name()
    if current_branch != work_branch:
        raise ReleaseError(
            f"'get' must be executed from the '{work_branch}' branch (current: {current_branch})."
        )
    work_hash = capture_git_output(["rev-parse", work_branch])
    develop_hash = capture_git_output(["rev-parse", develop_branch])
    master_hash = capture_git_output(["rev-parse", master_branch])
    if not _commit_exists_in_branch(work_hash, develop_branch):
        raise ReleaseError(
            f"Local '{work_branch}' HEAD is not contained in local '{develop_branch}'. Merge it first."
        )
    if develop_hash != master_hash:
        raise ReleaseError(
            f"Local '{develop_branch}' and '{master_branch}' are not aligned on the same commit."
        )
    _refresh_remote_refs()
    for name in (master_branch, develop_branch):
        if not _remote_branch_exists(name):
            raise ReleaseError(f"Missing remote branch 'origin/{name}'.")
    if not _commit_exists_in_branch(develop_hash, f"origin/{develop_branch}"):
        raise ReleaseError(
            f"Local '{develop_branch}' HEAD is not present on 'origin/{develop_branch}'."
        )
    if not _commit_exists_in_branch(master_hash, f"origin/{master_branch}"):
        raise ReleaseError(
            f"Local '{master_branch}' HEAD is not present on 'origin/{master_branch}'."
        )
    _, remote_ahead = _branch_remote_divergence("develop")
    if remote_ahead <= 0:
        raise ReleaseError(
            f"Remote 'origin/{develop_branch}' has no new commits relative to local '{develop_branch}'."
        )
    level = "get"
    print()
    _run_release_step(
        level,
        "fast-forward local master from origin",
        lambda: run_git_cmd(
            ["fetch", "origin", f"{master_branch}:{master_branch}", "--tags"]
        ),
    )
    _run_release_step(
        level,
        "fast-forward local develop from origin",
        lambda: run_git_cmd(
            ["fetch", "origin", f"{develop_branch}:{develop_branch}", "--tags"]
        ),
    )
    _run_release_step(
        level,
        "fast-forward merge develop into work",
        lambda: run_git_cmd(["merge", "--ff-only", develop_branch]),
    )
    print(
        f"Get completed successfully: local '{master_branch}' and '{develop_branch}' aligned with origin; '{work_branch}' fast-forwarded from '{develop_branch}'."
    )


## @brief CLI entry-point for the `get` subcommand.
# @details Rejects positional arguments, supports `--help`, and delegates to `_execute_get_flow`.
#          Converts `ReleaseError` into stderr output plus non-zero exit.
# @param extra Iterable of CLI argument strings following the `get` subcommand token.
# @return None; side-effects: fast-forwards local branches and tags from origin.
# @satisfies REQ-146, REQ-147, REQ-155
def cmd_get(extra):
    args = _to_args(extra)
    if args == ["--help"]:
        print_command_help("get")
        return
    if args:
        print("git get does not accept positional arguments.", file=sys.stderr)
        sys.exit(1)
    try:
        _execute_get_flow()
    except ReleaseError as exc:
        print(str(exc), file=sys.stderr)
        sys.exit(1)


## @brief Execute `cmd_gp` runtime logic for Git-Alias CLI.
# @details Executes `cmd_gp` using deterministic CLI control-flow and explicit error propagation.
# @param extra Input parameter consumed by `cmd_gp`.
# @return Result emitted by `cmd_gp` according to command contract.
def cmd_gp(extra):
    return run_command(
        _config_command_parts("gp_command", DEFAULT_GP_COMMAND) + _to_args(extra)
    )


## @brief Execute `cmd_gr` runtime logic for Git-Alias CLI.
# @details Executes `cmd_gr` using deterministic CLI control-flow and explicit error propagation.
# @param extra Input parameter consumed by `cmd_gr`.
# @return Result emitted by `cmd_gr` according to command contract.
def cmd_gr(extra):
    return run_command(
        _config_command_parts("gr_command", DEFAULT_GR_COMMAND) + _to_args(extra)
    )


## @brief Constant `OVERVIEW_COLOR_RESET` used by CLI runtime paths and policies.
OVERVIEW_COLOR_RESET = "\033[0m"
## @brief Constant `OVERVIEW_COLOR_SECTION_PURPLE` used by CLI runtime paths and policies.
OVERVIEW_COLOR_SECTION_PURPLE = "\033[35;1m"
## @brief Constant `OVERVIEW_COLOR_AHEAD` used by CLI runtime paths and policies.
OVERVIEW_COLOR_AHEAD = "\033[92m"
## @brief Constant `OVERVIEW_COLOR_BEHIND` used by CLI runtime paths and policies.
OVERVIEW_COLOR_BEHIND = "\033[31;1m"
## @brief Constant `OVERVIEW_COLOR_LABEL` used by CLI runtime paths and policies.
OVERVIEW_COLOR_LABEL = "\033[38;5;226m"
## @brief Constant `OVERVIEW_COLOR_WHITE` used by CLI runtime paths and policies.
OVERVIEW_COLOR_WHITE = "\033[97m"
## @brief Constant `OVERVIEW_COLOR_WHITE_BOLD` used by CLI runtime paths and policies.
OVERVIEW_COLOR_WHITE_BOLD = "\033[97;1m"
## @brief Constant `OVERVIEW_SECTION_TEMPLATE` used by CLI runtime paths and policies.
OVERVIEW_SECTION_TEMPLATE = "{color}=== {title} ==={reset}"
## @brief Constant `OVERVIEW_SUBSECTION_TEMPLATE` used by CLI runtime paths and policies.
OVERVIEW_SUBSECTION_TEMPLATE = "{color}--- {title} ---{reset}"
## @brief Constant `OVERVIEW_DISTANCE_TEMPLATE` used by CLI runtime paths and policies.
OVERVIEW_DISTANCE_TEMPLATE = "{text_color}{label}{reset} | {ahead} | {behind}"


## @brief Execute `_overview_branch_identifier` runtime logic for Git-Alias CLI.
# @details Executes `_overview_branch_identifier` using deterministic CLI control-flow and explicit error propagation.
# @param logical_name Input parameter consumed by `_overview_branch_identifier`.
# @param ref_name Input parameter consumed by `_overview_branch_identifier`.
# @param prefix_color Input parameter consumed by `_overview_branch_identifier`.
# @return Result emitted by `_overview_branch_identifier` according to command contract.
def _overview_branch_identifier(
    logical_name: str,
    ref_name: str,
    prefix_color: str = OVERVIEW_COLOR_WHITE,
) -> str:
    return (
        f"{prefix_color}{logical_name}"
        f"{OVERVIEW_COLOR_WHITE}"
        f"({OVERVIEW_COLOR_LABEL}⎇ {ref_name}{OVERVIEW_COLOR_RESET}{OVERVIEW_COLOR_WHITE})"
        f"{OVERVIEW_COLOR_RESET}"
    )


## @brief Execute `_overview_work_prefix_color` runtime logic for Git-Alias CLI.
# @details Executes `_overview_work_prefix_color` using deterministic CLI control-flow and explicit error propagation.
# @param worktree_state Input parameter consumed by `_overview_work_prefix_color`.
# @return Result emitted by `_overview_work_prefix_color` according to command contract.
def _overview_work_prefix_color(worktree_state: str) -> str:
    if worktree_state == "clean":
        return OVERVIEW_COLOR_AHEAD
    if worktree_state == "unstaged":
        return OVERVIEW_COLOR_BEHIND
    return OVERVIEW_COLOR_WHITE


## @brief Execute `_overview_logical_branch_name` runtime logic for Git-Alias CLI.
# @details Executes `_overview_logical_branch_name` using deterministic CLI control-flow and explicit error propagation.
# @param current_branch Input parameter consumed by `_overview_logical_branch_name`.
# @param work_branch Input parameter consumed by `_overview_logical_branch_name`.
# @param develop_branch Input parameter consumed by `_overview_logical_branch_name`.
# @param master_branch Input parameter consumed by `_overview_logical_branch_name`.
# @return Result emitted by `_overview_logical_branch_name` according to command contract.
def _overview_logical_branch_name(
    current_branch: str,
    work_branch: str,
    develop_branch: str,
    master_branch: str,
) -> str:
    if current_branch == work_branch:
        return "Work"
    if current_branch == develop_branch:
        return "Develop"
    if current_branch == master_branch:
        return "Master"
    return "Current"


## @brief Execute `_overview_current_branch_display` runtime logic for Git-Alias CLI.
# @details Executes `_overview_current_branch_display` using deterministic CLI control-flow and explicit error propagation.
# @param current_branch Input parameter consumed by `_overview_current_branch_display`.
# @param work_branch Input parameter consumed by `_overview_current_branch_display`.
# @param develop_branch Input parameter consumed by `_overview_current_branch_display`.
# @param master_branch Input parameter consumed by `_overview_current_branch_display`.
# @param worktree_state Input parameter consumed by `_overview_current_branch_display`.
# @return Result emitted by `_overview_current_branch_display` according to command contract.
def _overview_current_branch_display(
    current_branch: str,
    work_branch: str,
    develop_branch: str,
    master_branch: str,
    worktree_state: str,
) -> str:
    logical_name = _overview_logical_branch_name(
        current_branch=current_branch,
        work_branch=work_branch,
        develop_branch=develop_branch,
        master_branch=master_branch,
    )
    prefix_color = OVERVIEW_COLOR_BEHIND
    if logical_name == "Work":
        prefix_color = _overview_work_prefix_color(worktree_state)
    return _overview_branch_identifier(
        logical_name=logical_name,
        ref_name=current_branch,
        prefix_color=prefix_color,
    )


## @brief Execute `_overview_ref_is_available` runtime logic for Git-Alias CLI.
# @details Executes `_overview_ref_is_available` using deterministic CLI control-flow and explicit error propagation.
# @param ref_name Input parameter consumed by `_overview_ref_is_available`.
# @return Result emitted by `_overview_ref_is_available` according to command contract.
def _overview_ref_is_available(ref_name: str) -> bool:
    proc = _run_checked(
        ["git", "rev-parse", "--verify", "--quiet", ref_name],
        check=False,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    return proc.returncode == 0


## @brief Resolve latest commit subject for an overview ref.
# @details Returns the `%s` subject of `git log -1` for the input ref, or `n/a`
# when the ref is unavailable or the lookup fails.
# @param ref_name Input parameter consumed by `_overview_ref_latest_subject`.
# @return Result emitted by `_overview_ref_latest_subject` according to command contract.
def _overview_ref_latest_subject(ref_name: str) -> str:
    if not _overview_ref_is_available(ref_name):
        return "n/a"
    try:
        subject = run_git_text(["log", "-1", "--pretty=%s", ref_name]).strip()
    except RuntimeError:
        return "n/a"
    subject = ANSI_ESCAPE_RE.sub("", subject)
    return subject if subject else "n/a"


## @brief Collect normalized branch refs from `git branch -a` for overview rendering.
# @details Returns ordered unique branch refs, stripping current-branch marker and
# `remotes/` prefix and excluding symbolic-ref redirect rows.
# @return Result emitted by `_overview_discovered_branch_refs` according to command contract.
def _overview_discovered_branch_refs() -> List[str]:
    try:
        branches_text = run_git_text(["branch", "-a"])
    except RuntimeError:
        return []
    refs: List[str] = []
    seen = set()
    for branch_line in branches_text.splitlines():
        ref_name = branch_line.strip()
        if not ref_name:
            continue
        if ref_name.startswith("*"):
            ref_name = ref_name.lstrip("*").strip()
        if ref_name.startswith("remotes/"):
            ref_name = ref_name[len("remotes/") :]
        if " -> " in ref_name or ref_name.startswith("("):
            continue
        if ref_name in seen:
            continue
        seen.add(ref_name)
        refs.append(ref_name)
    return refs


## @brief Build section-5 aligned branch summary lines for overview output.
# @details Produces one row for each configured branch/ref identifier using
# `<Identifier> | <latest commit subject>` formatting, aligned by visible
# identifier width and with commit subject in bright white bold; appends rows
# for additional branch refs after configured rows.
# @param work_ref Input parameter consumed by `_overview_branch_summary_lines`.
# @param develop_ref Input parameter consumed by `_overview_branch_summary_lines`.
# @param master_ref Input parameter consumed by `_overview_branch_summary_lines`.
# @param remote_develop_ref Input parameter consumed by `_overview_branch_summary_lines`.
# @param remote_master_ref Input parameter consumed by `_overview_branch_summary_lines`.
# @param work_display Input parameter consumed by `_overview_branch_summary_lines`.
# @param develop_display Input parameter consumed by `_overview_branch_summary_lines`.
# @param master_display Input parameter consumed by `_overview_branch_summary_lines`.
# @param remote_develop_display Input parameter consumed by `_overview_branch_summary_lines`.
# @param remote_master_display Input parameter consumed by `_overview_branch_summary_lines`.
# @param additional_refs Input parameter consumed by `_overview_branch_summary_lines`.
# @return Result emitted by `_overview_branch_summary_lines` according to command contract.
# @satisfies REQ-094, REQ-096, REQ-115
## @brief Execute `_overview_branch_summary_lines` runtime logic for Git-Alias CLI.
# @details Executes `_overview_branch_summary_lines` using deterministic CLI control-flow and explicit error propagation.
# @param work_ref Input parameter consumed by `_overview_branch_summary_lines`.
# @param develop_ref Input parameter consumed by `_overview_branch_summary_lines`.
# @param master_ref Input parameter consumed by `_overview_branch_summary_lines`.
# @param remote_develop_ref Input parameter consumed by `_overview_branch_summary_lines`.
# @param remote_master_ref Input parameter consumed by `_overview_branch_summary_lines`.
# @param work_display Input parameter consumed by `_overview_branch_summary_lines`.
# @param develop_display Input parameter consumed by `_overview_branch_summary_lines`.
# @param master_display Input parameter consumed by `_overview_branch_summary_lines`.
# @param remote_develop_display Input parameter consumed by `_overview_branch_summary_lines`.
# @param remote_master_display Input parameter consumed by `_overview_branch_summary_lines`.
# @param additional_refs Input parameter consumed by `_overview_branch_summary_lines`.
# @return Result emitted by `_overview_branch_summary_lines` according to command contract.
def _overview_branch_summary_lines(
    work_ref: str,
    develop_ref: str,
    master_ref: str,
    remote_develop_ref: str,
    remote_master_ref: str,
    work_display: str,
    develop_display: str,
    master_display: str,
    remote_develop_display: str,
    remote_master_display: str,
    additional_refs: Optional[List[str]] = None,
) -> List[str]:
    rows = [
        ("Work", work_ref, work_display),
        ("Develop", develop_ref, develop_display),
        ("Master", master_ref, master_display),
        ("RemoteDevelop", remote_develop_ref, remote_develop_display),
        ("RemoteMaster", remote_master_ref, remote_master_display),
    ]
    configured_refs = {
        work_ref,
        develop_ref,
        master_ref,
        remote_develop_ref,
        remote_master_ref,
    }
    for ref_name in additional_refs or []:
        if ref_name in configured_refs:
            continue
        rows.append(
            (ref_name, ref_name, _overview_branch_identifier(ref_name, ref_name))
        )
    label_width = max(
        len(f"{logical_name}(⎇ {ref_name})") for logical_name, ref_name, _ in rows
    )
    lines: List[str] = []
    for logical_name, ref_name, display in rows:
        label_text = f"{logical_name}(⎇ {ref_name})"
        padding = " " * (label_width - len(label_text))
        subject = _overview_ref_latest_subject(ref_name)
        lines.append(
            f"{display}"
            f"{OVERVIEW_COLOR_WHITE}{padding} | {OVERVIEW_COLOR_RESET}"
            f"{subject}"
        )
    return lines


## @brief Execute `_overview_relation_state` runtime logic for Git-Alias CLI.
# @details Executes `_overview_relation_state` using deterministic CLI control-flow and explicit error propagation.
# @param ahead Input parameter consumed by `_overview_relation_state`.
# @param behind Input parameter consumed by `_overview_relation_state`.
# @return Result emitted by `_overview_relation_state` according to command contract.
def _overview_relation_state(ahead: int, behind: int) -> str:
    if ahead > 0 and behind > 0:
        return "diverged"
    if ahead > 0:
        return "ahead"
    if behind > 0:
        return "behind"
    return "in_sync"


## @brief Execute `_overview_worktree_state` runtime logic for Git-Alias CLI.
# @details Executes `_overview_worktree_state` using deterministic CLI control-flow and explicit error propagation.
# @param status_lines Input parameter consumed by `_overview_worktree_state`.
# @return Result emitted by `_overview_worktree_state` according to command contract.
def _overview_worktree_state(status_lines=None) -> str:
    lines = status_lines if status_lines is not None else _git_status_lines()
    has_unstaged = has_unstaged_changes(lines)
    has_staged = has_staged_changes(lines)
    if has_unstaged and has_staged:
        return "mixed"
    if has_staged:
        return "staged"
    if has_unstaged:
        return "unstaged"
    return "clean"


## @brief Execute `_overview_distance_text` runtime logic for Git-Alias CLI.
# @details Executes `_overview_distance_text` using deterministic CLI control-flow and explicit error propagation.
# @param is_ahead Input parameter consumed by `_overview_distance_text`.
# @param count Input parameter consumed by `_overview_distance_text`.
# @return Result emitted by `_overview_distance_text` according to command contract.
def _overview_distance_text(is_ahead: bool, count: int) -> str:
    label = "ahead" if is_ahead else "behind"
    if count == 0:
        return f"{OVERVIEW_COLOR_WHITE}{label} 0{OVERVIEW_COLOR_RESET}"
    arrow = "↑" if is_ahead else "↓"
    color = OVERVIEW_COLOR_AHEAD if is_ahead else OVERVIEW_COLOR_BEHIND
    return f"{color}{arrow} {label} {count}{OVERVIEW_COLOR_RESET}"


## @brief Execute `_overview_compare_refs` runtime logic for Git-Alias CLI.
# @details Executes `_overview_compare_refs` using deterministic CLI control-flow and explicit error propagation.
# @param base_ref Input parameter consumed by `_overview_compare_refs`.
# @param target_ref Input parameter consumed by `_overview_compare_refs`.
# @param label Input parameter consumed by `_overview_compare_refs`.
# @return Result emitted by `_overview_compare_refs` according to command contract.
def _overview_compare_refs(base_ref: str, target_ref: str, label: str) -> str:
    if not _overview_ref_is_available(base_ref) or not _overview_ref_is_available(
        target_ref
    ):
        unavailable = f"{OVERVIEW_COLOR_WHITE}n/a{OVERVIEW_COLOR_RESET}"
        print(
            OVERVIEW_DISTANCE_TEMPLATE.format(
                text_color=OVERVIEW_COLOR_WHITE,
                label=label,
                reset=OVERVIEW_COLOR_RESET,
                ahead=f"{OVERVIEW_COLOR_WHITE}ahead {unavailable}{OVERVIEW_COLOR_RESET}",
                behind=f"{OVERVIEW_COLOR_WHITE}behind {unavailable}{OVERVIEW_COLOR_RESET}",
            )
        )
        return "unknown"
    try:
        ahead = int(run_git_text(["rev-list", "--count", f"{target_ref}..{base_ref}"]))
        behind = int(run_git_text(["rev-list", "--count", f"{base_ref}..{target_ref}"]))
    except (RuntimeError, ValueError):
        unavailable = f"{OVERVIEW_COLOR_WHITE}n/a{OVERVIEW_COLOR_RESET}"
        print(
            OVERVIEW_DISTANCE_TEMPLATE.format(
                text_color=OVERVIEW_COLOR_WHITE,
                label=label,
                reset=OVERVIEW_COLOR_RESET,
                ahead=f"{OVERVIEW_COLOR_WHITE}ahead {unavailable}{OVERVIEW_COLOR_RESET}",
                behind=f"{OVERVIEW_COLOR_WHITE}behind {unavailable}{OVERVIEW_COLOR_RESET}",
            )
        )
        return "unknown"
    state = _overview_relation_state(ahead, behind)
    print(
        OVERVIEW_DISTANCE_TEMPLATE.format(
            text_color=OVERVIEW_COLOR_WHITE,
            label=label,
            reset=OVERVIEW_COLOR_RESET,
            ahead=_overview_distance_text(True, ahead),
            behind=_overview_distance_text(False, behind),
        )
    )
    return state


## @brief Build chronological-position topology tree from actual commit positions.
# @details Resolves commit hashes for each ref, computes commit counts from
# octopus merge-base, groups refs sharing the same hash on one output line,
# and orders nodes from most-ahead (root) to most-behind (deepest child).
# WorkingTree always occupies a dedicated line above the line that contains
# Work when tied or dirty. Complexity O(R) git
# subprocess calls where R is the number of available refs.
# @param work_ref {str} Git ref name for work branch.
# @param develop_ref {str} Git ref name for develop branch.
# @param master_ref {str} Git ref name for master branch.
# @param remote_develop_ref {str} Git ref name for remote develop (e.g., origin/develop).
# @param remote_master_ref {str} Git ref name for remote master (e.g., origin/master).
# @param work_display {str} Rendered display string for Work identifier.
# @param develop_display {str} Rendered display string for Develop identifier.
# @param master_display {str} Rendered display string for Master identifier.
# @param remote_develop_display {str} Rendered display string for RemoteDevelop identifier.
# @param remote_master_display {str} Rendered display string for RemoteMaster identifier.
# @param worktree_state {str} Working tree state (clean/unstaged/staged/mixed).
# @return {List[str]} Rendered topology lines with ANSI color codes.
# @satisfies REQ-089, REQ-090, REQ-091, REQ-092, REQ-093, REQ-095
## @brief Execute `_overview_ascii_topology_lines` runtime logic for Git-Alias CLI.
# @details Executes `_overview_ascii_topology_lines` using deterministic CLI control-flow and explicit error propagation.
# @param work_ref Input parameter consumed by `_overview_ascii_topology_lines`.
# @param develop_ref Input parameter consumed by `_overview_ascii_topology_lines`.
# @param master_ref Input parameter consumed by `_overview_ascii_topology_lines`.
# @param remote_develop_ref Input parameter consumed by `_overview_ascii_topology_lines`.
# @param remote_master_ref Input parameter consumed by `_overview_ascii_topology_lines`.
# @param work_display Input parameter consumed by `_overview_ascii_topology_lines`.
# @param develop_display Input parameter consumed by `_overview_ascii_topology_lines`.
# @param master_display Input parameter consumed by `_overview_ascii_topology_lines`.
# @param remote_develop_display Input parameter consumed by `_overview_ascii_topology_lines`.
# @param remote_master_display Input parameter consumed by `_overview_ascii_topology_lines`.
# @param worktree_state Input parameter consumed by `_overview_ascii_topology_lines`.
# @return Result emitted by `_overview_ascii_topology_lines` according to command contract.
def _overview_ascii_topology_lines(
    work_ref: str,
    develop_ref: str,
    master_ref: str,
    remote_develop_ref: str,
    remote_master_ref: str,
    work_display: str,
    develop_display: str,
    master_display: str,
    remote_develop_display: str,
    remote_master_display: str,
    worktree_state: str,
) -> List[str]:
    branch_nodes = [
        ("Work", work_ref, work_display),
        ("Develop", develop_ref, develop_display),
        ("Master", master_ref, master_display),
        ("RemoteDevelop", remote_develop_ref, remote_develop_display),
        ("RemoteMaster", remote_master_ref, remote_master_display),
    ]
    ref_hashes: Dict[str, Optional[str]] = {}
    available_refs: List[str] = []
    for name, ref, _ in branch_nodes:
        if _overview_ref_is_available(ref):
            try:
                h = run_git_text(["rev-parse", ref]).strip()
                ref_hashes[name] = h
                available_refs.append(ref)
            except RuntimeError:
                ref_hashes[name] = None
        else:
            ref_hashes[name] = None
    merge_base: Optional[str] = None
    if len(available_refs) >= 2:
        try:
            merge_base = run_git_text(
                ["merge-base", "--octopus"] + available_refs,
            ).strip()
        except RuntimeError:
            merge_base = None
    positions: Dict[str, int] = {}
    for name, ref, _ in branch_nodes:
        if ref_hashes.get(name) is None:
            positions[name] = 0
            continue
        if merge_base:
            try:
                count = int(
                    run_git_text(["rev-list", "--count", f"{merge_base}..{ref}"]),
                )
                positions[name] = count
            except (RuntimeError, ValueError):
                positions[name] = 0
        else:
            positions[name] = 0
    work_pos = positions.get("Work", 0)
    wt_sort_key = (
        float(work_pos) + 0.5 if worktree_state != "clean" else float(work_pos)
    )
    wt_text = (
        f"{OVERVIEW_COLOR_WHITE}WorkingTree [{worktree_state}]{OVERVIEW_COLOR_RESET}"
    )
    entries: List[Tuple[float, int, str]] = [(wt_sort_key, 2, wt_text)]
    work_hash = ref_hashes.get("Work")
    hash_groups: Dict[str, List[str]] = {}
    hash_positions: Dict[str, int] = {}
    for name, ref, display in branch_nodes:
        h = ref_hashes.get(name)
        if h is None:
            continue
        if h not in hash_groups:
            hash_groups[h] = []
            hash_positions[h] = positions[name]
        hash_groups[h].append(display)
    for h, members in hash_groups.items():
        pos = hash_positions[h]
        if h == work_hash:
            sort_key = float(work_pos) - 0.1
        else:
            sort_key = float(pos)
        members_text = ", ".join(members)
        entries.append((sort_key, 0, members_text))
    entries.sort(key=lambda e: (e[0], e[1]), reverse=True)
    if not entries:
        return []
    root_text = entries[0][2]
    lines = [
        root_text,
        f"{OVERVIEW_COLOR_WHITE}|{OVERVIEW_COLOR_RESET}",
    ]
    for _, _, text in entries[1:]:
        lines.append(f"{OVERVIEW_COLOR_WHITE}|-- {OVERVIEW_COLOR_RESET}{text}")
    lines.append(f"{OVERVIEW_COLOR_WHITE}|{OVERVIEW_COLOR_RESET}")
    return lines


## @brief Build normalized section-6 status lines for overview output.
# @details Executes `git status -sb`, rewrites the header line from
# `## <branch>` to `## <Logical>(⎇ <branch>)` with the same color formatting
# used by section-1 current-branch output, and preserves all other lines.
# @param current_branch_display Input parameter consumed by `_overview_current_branch_state_lines`.
# @return {List[str]} Result emitted by `_overview_current_branch_state_lines` according to command contract.
# @satisfies REQ-094
def _overview_current_branch_state_lines(current_branch_display: str) -> List[str]:
    lines = run_git_text(["status", "-sb"]).splitlines()
    normalized_lines: List[str] = []
    header_replaced = False
    for line in lines:
        if line.startswith("## ") and not header_replaced:
            normalized_lines.append(
                f"{OVERVIEW_COLOR_WHITE}## {current_branch_display}{OVERVIEW_COLOR_RESET}"
            )
            header_replaced = True
            continue
        if line:
            normalized_lines.append(
                f"{OVERVIEW_COLOR_BEHIND}{line[:2]}{OVERVIEW_COLOR_RESET}{line[2:]}"
            )
            continue
        normalized_lines.append(line)
    return normalized_lines


## @brief Execute `cmd_o` runtime logic for Git-Alias CLI.
# @details Executes `cmd_o` using deterministic CLI control-flow and explicit error propagation.
# @param extra Input parameter consumed by `cmd_o`.
# @return Result emitted by `cmd_o` according to command contract.
# @satisfies REQ-082, REQ-083, REQ-084, REQ-085, REQ-086, REQ-087, REQ-088, REQ-089, REQ-090, REQ-091, REQ-092, REQ-093, REQ-094, REQ-095, REQ-096, REQ-115
def cmd_o(extra):
    del extra
    if not is_inside_git_repo():
        print(
            "Error: The overview command must be executed inside a Git repository.",
            file=sys.stderr,
        )
        sys.exit(2)
    work_branch = get_branch("work")
    develop_branch = get_branch("develop")
    master_branch = get_branch("master")
    remote_develop = f"origin/{develop_branch}"
    remote_master = f"origin/{master_branch}"
    current_branch = run_git_text(["branch", "--show-current"]).strip() or "HEAD"
    status_lines = _git_status_lines()
    worktree_state = _overview_worktree_state(status_lines)
    work_display = _overview_branch_identifier(
        "Work",
        work_branch,
        prefix_color=_overview_work_prefix_color(worktree_state),
    )
    develop_display = _overview_branch_identifier("Develop", develop_branch)
    master_display = _overview_branch_identifier("Master", master_branch)
    remote_develop_display = _overview_branch_identifier(
        "RemoteDevelop", remote_develop
    )
    remote_master_display = _overview_branch_identifier("RemoteMaster", remote_master)
    current_branch_display = _overview_current_branch_display(
        current_branch=current_branch,
        work_branch=work_branch,
        develop_branch=develop_branch,
        master_branch=master_branch,
        worktree_state=worktree_state,
    )
    print(
        OVERVIEW_SECTION_TEMPLATE.format(
            color=OVERVIEW_COLOR_SECTION_PURPLE,
            title="1. WORKING AREA, STAGE & CURRENT BRANCH",
            reset=OVERVIEW_COLOR_RESET,
        )
    )
    print(
        f"{OVERVIEW_COLOR_WHITE}Configured branches: {work_display}, {develop_display}, {master_display}{OVERVIEW_COLOR_RESET}"
    )
    print(
        f"{OVERVIEW_COLOR_WHITE}Configured remotes: {remote_develop_display}, {remote_master_display}{OVERVIEW_COLOR_RESET}"
    )
    print(
        f"{OVERVIEW_COLOR_WHITE}Current Branch: {current_branch_display}{OVERVIEW_COLOR_RESET}"
    )
    print()
    print(
        OVERVIEW_SECTION_TEMPLATE.format(
            color=OVERVIEW_COLOR_SECTION_PURPLE,
            title="2. BRANCH DISTANCES (COMMITS)",
            reset=OVERVIEW_COLOR_RESET,
        )
    )
    _overview_compare_refs(
        work_branch,
        develop_branch,
        f"{work_display} vs {develop_display}",
    )
    _overview_compare_refs(
        work_branch,
        master_branch,
        f"{work_display} vs {master_display}",
    )
    print(
        OVERVIEW_SUBSECTION_TEMPLATE.format(
            color=OVERVIEW_COLOR_WHITE_BOLD,
            title="Server Alignment",
            reset=OVERVIEW_COLOR_RESET,
        )
    )
    _overview_compare_refs(
        develop_branch,
        remote_develop,
        f"{develop_display} vs {remote_develop_display}",
    )
    _overview_compare_refs(
        master_branch,
        remote_master,
        f"{master_display} vs {remote_master_display}",
    )
    print()
    print(
        OVERVIEW_SECTION_TEMPLATE.format(
            color=OVERVIEW_COLOR_SECTION_PURPLE,
            title="3. ACTIVE WORKTREES",
            reset=OVERVIEW_COLOR_RESET,
        )
    )
    run_git_cmd(["worktree", "list", "--verbose"])
    print()
    print(
        OVERVIEW_SECTION_TEMPLATE.format(
            color=OVERVIEW_COLOR_SECTION_PURPLE,
            title="4. QUALITATIVE TOPOLOGY",
            reset=OVERVIEW_COLOR_RESET,
        )
    )
    topology_lines = _overview_ascii_topology_lines(
        work_ref=work_branch,
        develop_ref=develop_branch,
        master_ref=master_branch,
        remote_develop_ref=remote_develop,
        remote_master_ref=remote_master,
        work_display=work_display,
        develop_display=develop_display,
        master_display=master_display,
        remote_develop_display=remote_develop_display,
        remote_master_display=remote_master_display,
        worktree_state=worktree_state,
    )
    for line in topology_lines:
        print(line)
    print()
    print(
        OVERVIEW_SECTION_TEMPLATE.format(
            color=OVERVIEW_COLOR_SECTION_PURPLE,
            title="5. BRANCHES",
            reset=OVERVIEW_COLOR_RESET,
        )
    )
    additional_branch_refs = _overview_discovered_branch_refs()
    branch_rows = _overview_branch_summary_lines(
        work_ref=work_branch,
        develop_ref=develop_branch,
        master_ref=master_branch,
        remote_develop_ref=remote_develop,
        remote_master_ref=remote_master,
        work_display=work_display,
        develop_display=develop_display,
        master_display=master_display,
        remote_develop_display=remote_develop_display,
        remote_master_display=remote_master_display,
        additional_refs=additional_branch_refs,
    )
    for row in branch_rows:
        print(f"{OVERVIEW_COLOR_WHITE}{row}{OVERVIEW_COLOR_RESET}")
    print()
    if worktree_state != "clean":
        print(
            OVERVIEW_SECTION_TEMPLATE.format(
                color=OVERVIEW_COLOR_SECTION_PURPLE,
                title="6. CURRENT BRANCH STATE",
                reset=OVERVIEW_COLOR_RESET,
            )
        )
        for line in _overview_current_branch_state_lines(current_branch_display):
            print(line)
        print()


## @brief Execute `cmd_str` runtime logic for Git-Alias CLI.
# @details Executes `cmd_str` using deterministic CLI control-flow and explicit error propagation.
# @param extra Input parameter consumed by `cmd_str`.
# @return Result emitted by `cmd_str` according to command contract.
def cmd_str(extra):
    # @details Query git remotes with transport metadata.
    result = run_git_text(["remote", "-v"])
    lines = result.strip().split("\n")

    # @details Deduplicate remote names from `git remote -v` rows.
    remotes = set()
    for line in lines:
        if line.strip():
            parts = line.split()
            if parts:
                remote_name = parts[0]
                remotes.add(remote_name)

    # @details Print normalized remote name inventory.
    print("Remotes found:")
    for remote in sorted(remotes):
        print(f"  {remote}")
    print()

    # @details Print detailed status for each unique remote.
    for remote in sorted(remotes):
        print(f"--- Status for '{remote}' ---")
        try:
            run_git_cmd(["remote", "show", remote])
        except CommandExecutionError:
            print(f"Error showing status for '{remote}'", file=sys.stderr)
            raise


## @brief Execute `cmd_l` runtime logic for Git-Alias CLI.
# @details Delegates to `forest.run()` which renders a text-based tree visualization
# of git commit history using a vine-based graph algorithm with configurable styles,
# symbols, colors, and margins. Injects `-n 25` only when invoked without
# user arguments; otherwise forwards provided arguments unchanged.
# @satisfies REQ-098, REQ-099, REQ-111
# @param extra {list} Additional CLI arguments forwarded to the forest engine.
# @return None.
def cmd_l(extra):
    from git_alias import forest

    args = list(extra) if extra else ["-n", "25"]
    forest.run(args)


## @brief Execute `cmd_lb` runtime logic for Git-Alias CLI.
# @details Executes `cmd_lb` using deterministic CLI control-flow and explicit error propagation.
# @param extra Input parameter consumed by `cmd_lb`.
# @return Result emitted by `cmd_lb` according to command contract.
def cmd_lb(extra):
    return run_git_cmd(["branch", "-v", "-a"], extra)


## @brief Execute `cmd_lg` runtime logic for Git-Alias CLI.
# @details Executes `cmd_lg` using deterministic CLI control-flow and explicit error propagation.
# @param extra Input parameter consumed by `cmd_lg`.
# @return Result emitted by `cmd_lg` according to command contract.
def cmd_lg(extra):
    return run_git_cmd(
        [
            "log",
            "--graph",
            "--abbrev-commit",
            "--decorate",
            "--format=format:%C(bold blue)%h%C(reset) - %C(bold green)(%ar)%C(reset) %C(white)%s%C(reset) %C(dim white)- %an%C(reset)%C(bold yellow)%d%C(reset)",
            "--all",
        ],
        extra,
    )


## @brief Execute `cmd_lh` runtime logic for Git-Alias CLI.
# @details Executes `cmd_lh` using deterministic CLI control-flow and explicit error propagation.
# @param extra Input parameter consumed by `cmd_lh`.
# @return Result emitted by `cmd_lh` according to command contract.
def cmd_lh(extra):
    return run_git_cmd(["log", "-1", "HEAD"], extra)


## @brief Execute `cmd_ll` runtime logic for Git-Alias CLI.
# @details Executes `cmd_ll` using deterministic CLI control-flow and explicit error propagation.
# @param extra Input parameter consumed by `cmd_ll`.
# @return Result emitted by `cmd_ll` according to command contract.
def cmd_ll(extra):
    return run_git_cmd(
        [
            "log",
            "--graph",
            "--decorate",
            "--format=format:%C(bold blue)%H%C(reset) - %C(bold cyan)%aD%C(reset) %C(bold green)(%ar)%C(reset)%C(bold yellow)%d%C(reset)%n %C(white)%s%C(reset) %C(dim white)- %an%C(reset)",
            "--all",
        ],
        extra,
    )


## @brief Execute `cmd_lm` runtime logic for Git-Alias CLI.
# @details Executes `cmd_lm` using deterministic CLI control-flow and explicit error propagation.
# @param extra Input parameter consumed by `cmd_lm`.
# @return Result emitted by `cmd_lm` according to command contract.
def cmd_lm(extra):
    return run_git_cmd(["log", "--merges"], extra)


## @brief Execute `cmd_ls` runtime logic for Git-Alias CLI.
# @details Executes `cmd_ls` using deterministic CLI control-flow and explicit error propagation.
# @param extra Input parameter consumed by `cmd_ls`.
# @return Result emitted by `cmd_ls` according to command contract.
# @satisfies REQ-079
def cmd_ls(extra):
    return run_git_cmd(["ls-files", "--exclude-standard"], extra)


## @brief Execute `cmd_lsi` runtime logic for Git-Alias CLI.
# @details Runs `git ls-files --others --ignored --exclude-standard` and filters
# output by excluding paths where any path component matches any entry in
# `LSI_DEFAULT_EXCLUDED_DIRS` (exact match) or ends with any suffix in
# `LSI_DEFAULT_EXCLUDED_DIR_SUFFIXES` (suffix match). When `--include-all`
# is present in @p extra, both filtering mechanisms are bypassed and all
# output is printed. Additional arguments are forwarded to the underlying
# git command unchanged. Exact-match uses `frozenset.intersection` for
# O(min(n,m)) lookup per line; suffix-match iterates path components
# against the suffix tuple via `str.endswith`.
# @param extra List[str] CLI arguments passed after the alias name.
# @return None. Filtered output is printed to stdout.
# @satisfies REQ-080, REQ-121
## @brief Execute `cmd_lsi` runtime logic for Git-Alias CLI.
# @details Executes `cmd_lsi` using deterministic CLI control-flow and explicit error propagation.
# @param extra Input parameter consumed by `cmd_lsi`.
# @return Result emitted by `cmd_lsi` according to command contract.
def cmd_lsi(extra):
    args = _to_args(extra)
    include_all = "--include-all" in args
    if include_all:
        args = [a for a in args if a != "--include-all"]
    git_args = ["ls-files", "--others", "--ignored", "--exclude-standard", *args]
    if include_all:
        return run_git_cmd(git_args, [])
    output = run_git_text(git_args)
    if not output:
        return None
    for line in output.splitlines():
        parts = line.split("/")
        if LSI_DEFAULT_EXCLUDED_DIRS.intersection(parts):
            continue
        if any(p.endswith(s) for p in parts for s in LSI_DEFAULT_EXCLUDED_DIR_SUFFIXES):
            continue
        print(line)
    return None


## @brief Execute `cmd_lsa` runtime logic for Git-Alias CLI.
# @details Executes `cmd_lsa` using deterministic CLI control-flow and explicit error propagation.
# @param extra Input parameter consumed by `cmd_lsa`.
# @return Result emitted by `cmd_lsa` according to command contract.
# @satisfies REQ-081
def cmd_lsa(extra):
    return run_git_cmd(["ls-files", "--others", "--exclude-standard"], extra)


## @brief Execute `cmd_lt` runtime logic for Git-Alias CLI.
# @details Enumerates tags via `git tag -l`, resolves containing refs via `git branch -a --contains <tag>`,
#          trims branch markers/prefixes from git output, and prints deterministic `<tag>: <branch_1>, <branch_2>, ...` lines.
# @param extra Input parameter consumed by `cmd_lt`.
# @return Result emitted by `cmd_lt` according to command contract.
def cmd_lt(extra):
    tags_text = capture_git_output(["tag", "-l", *_to_args(extra)])
    tags = [tag.strip() for tag in tags_text.splitlines() if tag.strip()]
    for tag in tags:
        branches_text = capture_git_output(["branch", "-a", "--contains", tag])
        branches = []
        for branch_line in branches_text.splitlines():
            branch = branch_line.strip()
            if not branch:
                continue
            if branch.startswith("*"):
                branch = branch.lstrip("*").strip()
            if branch.startswith("remotes/"):
                branch = branch[len("remotes/") :]
            if " -> " in branch:
                continue
            branches.append(branch)
        print(f"{tag}: {', '.join(branches)}" if branches else f"{tag}:")


## @brief Execute `cmd_me` runtime logic for Git-Alias CLI.
# @details Executes `cmd_me` using deterministic CLI control-flow and explicit error propagation.
# @param extra Input parameter consumed by `cmd_me`.
# @return Result emitted by `cmd_me` according to command contract.
def cmd_me(extra):
    return run_git_cmd(["merge", "--ff-only"], extra)


## @brief Execute `cmd_pl` runtime logic for Git-Alias CLI.
# @details Executes `cmd_pl` using deterministic CLI control-flow and explicit error propagation.
# @param extra Input parameter consumed by `cmd_pl`.
# @return Result emitted by `cmd_pl` according to command contract.
def cmd_pl(extra):
    return run_git_cmd(["pull", "--ff-only"], extra)


## @brief Execute `cmd_pt` runtime logic for Git-Alias CLI.
# @details Executes `cmd_pt` using deterministic CLI control-flow and explicit error propagation.
# @param extra Input parameter consumed by `cmd_pt`.
# @return Result emitted by `cmd_pt` according to command contract.
def cmd_pt(extra):
    return run_git_cmd(["push", "--tags"], extra)


## @brief Execute `cmd_pu` runtime logic for Git-Alias CLI.
# @details Executes `cmd_pu` using deterministic CLI control-flow and explicit error propagation.
# @param extra Input parameter consumed by `cmd_pu`.
# @return Result emitted by `cmd_pu` according to command contract.
def cmd_pu(extra):
    return run_git_cmd(["push", "-u"], extra)


## @brief Execute `cmd_rf` runtime logic for Git-Alias CLI.
# @details Executes `cmd_rf` using deterministic CLI control-flow and explicit error propagation.
# @param extra Input parameter consumed by `cmd_rf`.
# @return Result emitted by `cmd_rf` according to command contract.
def cmd_rf(extra):
    return run_git_cmd(["reflog"], extra)


## @brief Execute `cmd_rmtg` runtime logic for Git-Alias CLI.
# @details Executes `cmd_rmtg` using deterministic CLI control-flow and explicit error propagation.
# @param extra Input parameter consumed by `cmd_rmtg`.
# @return Result emitted by `cmd_rmtg` according to command contract.
def cmd_rmtg(extra):
    args = _to_args(extra)
    if not args:
        print('usage: git rmtg "<tag>"', file=sys.stderr)
        sys.exit(1)
    tag = args[0]
    tail = args[1:]
    run_git_cmd(["tag", "--delete", tag])
    return run_git_cmd(["push", "--delete", "origin", tag], tail)


## @brief Execute `cmd_rmloc` runtime logic for Git-Alias CLI.
# @details Executes `cmd_rmloc` using deterministic CLI control-flow and explicit error propagation.
# @param extra Input parameter consumed by `cmd_rmloc`.
# @return Result emitted by `cmd_rmloc` according to command contract.
def cmd_rmloc(extra):
    return run_git_cmd(["reset", "--hard", "--"], extra)


## @brief Execute `cmd_rmstg` runtime logic for Git-Alias CLI.
# @details Executes `cmd_rmstg` using deterministic CLI control-flow and explicit error propagation.
# @param extra Input parameter consumed by `cmd_rmstg`.
# @return Result emitted by `cmd_rmstg` according to command contract.
def cmd_rmstg(extra):
    return run_git_cmd(["rm", "--cached", "--"], extra)


## @brief Execute `cmd_rmunt` runtime logic for Git-Alias CLI.
# @details Executes `cmd_rmunt` using deterministic CLI control-flow and explicit error propagation.
# @param extra Input parameter consumed by `cmd_rmunt`.
# @return Result emitted by `cmd_rmunt` according to command contract.
def cmd_rmunt(extra):
    return run_git_cmd(["clean", "-d", "-f", "--"], extra)


## @brief Execute `cmd_rs` runtime logic for Git-Alias CLI.
# @details Executes `cmd_rs` using deterministic CLI control-flow and explicit error propagation.
# @param extra Input parameter consumed by `cmd_rs`.
# @return Result emitted by `cmd_rs` according to command contract.
def cmd_rs(extra):
    return _run_reset_with_help(["reset", "--hard", "HEAD"], extra)


## @brief Execute `cmd_rssft` runtime logic for Git-Alias CLI.
# @details Executes `cmd_rssft` using deterministic CLI control-flow and explicit error propagation.
# @param extra Input parameter consumed by `cmd_rssft`.
# @return Result emitted by `cmd_rssft` according to command contract.
def cmd_rssft(extra):
    return _run_reset_with_help(["reset", "--soft", "--"], extra)


## @brief Execute `cmd_rsmix` runtime logic for Git-Alias CLI.
# @details Executes `cmd_rsmix` using deterministic CLI control-flow and explicit error propagation.
# @param extra Input parameter consumed by `cmd_rsmix`.
# @return Result emitted by `cmd_rsmix` according to command contract.
def cmd_rsmix(extra):
    return _run_reset_with_help(["reset", "--mixed", "--"], extra)


## @brief Execute `cmd_rshrd` runtime logic for Git-Alias CLI.
# @details Executes `cmd_rshrd` using deterministic CLI control-flow and explicit error propagation.
# @param extra Input parameter consumed by `cmd_rshrd`.
# @return Result emitted by `cmd_rshrd` according to command contract.
def cmd_rshrd(extra):
    return _run_reset_with_help(["reset", "--hard", "--"], extra)


## @brief Execute `cmd_rsmrg` runtime logic for Git-Alias CLI.
# @details Executes `cmd_rsmrg` using deterministic CLI control-flow and explicit error propagation.
# @param extra Input parameter consumed by `cmd_rsmrg`.
# @return Result emitted by `cmd_rsmrg` according to command contract.
def cmd_rsmrg(extra):
    return _run_reset_with_help(["reset", "--merge", "--"], extra)


## @brief Execute `cmd_rskep` runtime logic for Git-Alias CLI.
# @details Executes `cmd_rskep` using deterministic CLI control-flow and explicit error propagation.
# @param extra Input parameter consumed by `cmd_rskep`.
# @return Result emitted by `cmd_rskep` according to command contract.
def cmd_rskep(extra):
    return _run_reset_with_help(["reset", "--keep", "--"], extra)


## @brief Execute `cmd_st` runtime logic for Git-Alias CLI.
# @details Executes `cmd_st` using deterministic CLI control-flow and explicit error propagation.
# @param extra Input parameter consumed by `cmd_st`.
# @return Result emitted by `cmd_st` according to command contract.
def cmd_st(extra):
    return run_git_cmd(["status"], extra)


## @brief Execute `cmd_tg` runtime logic for Git-Alias CLI.
# @details Executes `cmd_tg` using deterministic CLI control-flow and explicit error propagation.
# @param extra Input parameter consumed by `cmd_tg`.
# @return Result emitted by `cmd_tg` according to command contract.
def cmd_tg(extra):
    return run_git_cmd(["tag", "-a", "-m"], extra)


## @brief Execute `cmd_unstg` runtime logic for Git-Alias CLI.
# @details Executes `cmd_unstg` using deterministic CLI control-flow and explicit error propagation.
# @param extra Input parameter consumed by `cmd_unstg`.
# @return Result emitted by `cmd_unstg` according to command contract.
def cmd_unstg(extra):
    return run_git_cmd(["reset", "--mixed", "--"], extra)


## @brief Dispatch raw `git worktree` subcommands through alias `wt`.
# @details Delegates to native `git worktree` so subcommands such as `list`,
# `add`, and `prune` remain reachable through the alias. Forwards every
# operand unchanged and performs no CLI-side interpretation before subprocess
# execution.
# @param extra {List[str] | None} CLI operands appended after `git worktree`.
# @return Result emitted by `run_git_cmd` for the delegated git subprocess.
# @satisfies REQ-074
# @note Complexity: O(1) excluding delegated git process runtime.
def cmd_wt(extra):
    return run_git_cmd(["worktree"], extra)


## @brief Dispatch dedicated `git worktree list` behavior through alias `wtl`.
# @details Delegates to native `git worktree list` while preserving every user
# operand unchanged, including verbosity and porcelain flags handled by git
# itself.
# @param extra {List[str] | None} CLI operands appended after
# `git worktree list`.
# @return Result emitted by `run_git_cmd` for the delegated git subprocess.
# @satisfies REQ-074, REQ-075
# @note Complexity: O(1) excluding delegated git process runtime.
def cmd_wtl(extra):
    return run_git_cmd(["worktree", "list"], extra)


## @brief Execute `cmd_wtp` runtime logic for Git-Alias CLI.
# @details Executes `cmd_wtp` using deterministic CLI control-flow and explicit error propagation.
# @param extra Input parameter consumed by `cmd_wtp`.
# @return Result emitted by `cmd_wtp` according to command contract.
def cmd_wtp(extra):
    return run_git_cmd(["worktree", "prune"], extra)


## @brief Execute `cmd_wtd` runtime logic for Git-Alias CLI.
# @details Accepts one worktree target with optional `--force`, resolves worktree associations,
#          deletes an associated worktree before deleting the branch, and uses forced git delete
#          flags only when explicitly requested.
# @param extra `list | None` — requires exactly one worktree target or `--help`.
# @return Return value from `run_git_cmd` when only the worktree is deleted; otherwise `None`.
# @exception SystemExit Exit code 1 on invalid operands or preflight failure.
# @satisfies REQ-077, REQ-139, REQ-140, REQ-141, REQ-142, REQ-143, REQ-144, REQ-145
def cmd_wtd(extra):
    args = _to_args(extra)
    if args == ["--help"]:
        print_command_help("wtd")
        return
    worktree_arg, force_delete = _parse_wtd_target(args)
    associations = _list_worktree_associations()
    worktree_info = _find_association_for_worktree(worktree_arg, associations)
    if worktree_info is None:
        target_path = Path(worktree_arg).expanduser().resolve()
        worktree_cmd = ["worktree", "remove", str(target_path)]
        if force_delete:
            worktree_cmd = ["worktree", "remove", "--force", str(target_path)]
        else:
            _preflight_worktree_delete(target_path, "wtd")
        return run_git_cmd(worktree_cmd)
    if worktree_info.branch_name:
        _delete_associated_branch_and_worktree(worktree_info, "wtd", force_delete)
        return
    worktree_cmd = ["worktree", "remove", str(worktree_info.path)]
    if force_delete:
        worktree_cmd = ["worktree", "remove", "--force", str(worktree_info.path)]
    else:
        _preflight_worktree_delete(worktree_info.path, "wtd")
    return run_git_cmd(worktree_cmd)


## @brief Execute `cmd_ver` runtime logic for Git-Alias CLI.
# @details Executes `cmd_ver` using deterministic CLI control-flow and explicit error propagation.
# @param extra Input parameter consumed by `cmd_ver`.
# @return Result emitted by `cmd_ver` according to command contract.
def cmd_ver(extra):
    args = _to_args(extra)
    verbose = "--verbose" in args
    debug = "--debug" in args
    if debug:
        verbose = True
    root = get_git_root()
    rules = get_version_rules()
    if not rules:
        print("No version rules configured.", file=sys.stderr)
        sys.exit(1)
    try:
        inventory = _build_version_file_inventory(root)
        contexts = _prepare_version_rule_contexts(root, rules, inventory=inventory)
        canonical = _determine_canonical_version(
            root,
            rules,
            verbose=verbose,
            debug=debug,
            contexts=contexts,
        )
    except VersionDetectionError as exc:
        print(str(exc), file=sys.stderr)
        sys.exit(1)
    print(canonical)


## @brief Execute `cmd_chver` runtime logic for Git-Alias CLI.
# @details Executes `cmd_chver` using deterministic CLI control-flow and explicit error propagation.
# @param extra Input parameter consumed by `cmd_chver`.
# @return Result emitted by `cmd_chver` according to command contract.
def cmd_chver(extra):
    args = _to_args(extra)
    if len(args) != 1:
        print("usage: git chver <major.minor.patch>", file=sys.stderr)
        sys.exit(1)
    requested = args[0].strip()
    target_tuple = _parse_semver_tuple(requested)
    if not target_tuple:
        print(
            "Please provide the version in the format <major>.<minor>.<patch> (e.g. 1.2.3).",
            file=sys.stderr,
        )
        sys.exit(1)
    root = get_git_root()
    rules = get_version_rules()
    if not rules:
        print("No version rules configured.", file=sys.stderr)
        sys.exit(1)
    text_cache: Dict[Path, str] = {}
    try:
        inventory = _build_version_file_inventory(root)
        contexts = _prepare_version_rule_contexts(root, rules, inventory=inventory)
        current = _determine_canonical_version(
            root,
            rules,
            contexts=contexts,
            text_cache=text_cache,
        )
    except VersionDetectionError as exc:
        print(f"Unable to determine the current version: {exc}", file=sys.stderr)
        sys.exit(1)
    current_tuple = _parse_semver_tuple(current)
    if current_tuple is None:
        print(
            f"The current version '{current}' is not a valid semantic version.",
            file=sys.stderr,
        )
        sys.exit(1)
    if requested == current:
        print(f"The project version is already {current}.")
        return
    action = "Upgrade" if target_tuple > current_tuple else "Downgrade"
    replacements = 0
    for context in contexts:
        for file_path in context.files:
            text = _read_version_file_text(file_path, text_cache=text_cache)
            if text is None:
                continue
            new_text, count = _replace_versions_in_text(
                text, context.compiled_regex, requested
            )
            if count:
                try:
                    file_path.write_text(new_text, encoding="utf-8")
                except OSError as exc:
                    print(f"Unable to write {file_path}: {exc}", file=sys.stderr)
                    sys.exit(1)
                text_cache[file_path] = new_text
                replacements += count
    if replacements == 0:
        print(
            "No version entries were updated. Ensure ver_rules match the desired files.",
            file=sys.stderr,
        )
        sys.exit(1)
    try:
        confirmed = _determine_canonical_version(
            root,
            rules,
            contexts=contexts,
            text_cache=text_cache,
        )
    except VersionDetectionError as exc:
        print(f"Fatal error after updating versions: {exc}", file=sys.stderr)
        sys.exit(1)
    if confirmed != requested:
        print(
            f"Fatal error: the updated files report version {confirmed} instead of {requested}.",
            file=sys.stderr,
        )
        sys.exit(1)
    print(f"{action} completed: version is now {confirmed}.")


## @brief CLI entry-point for the `major` release subcommand.
# @details Increments the major semver index (resets minor and patch to 0), merges and pushes
#          to both configured `develop` and `master` branches, regenerates changelog via a
#          temporary local tag on `work`, and creates the definitive release tag on `master`
#          before publication; pushes develop alone, then master and the exact tag atomically.
#          `--dev`/`--develop` limits the workflow to configured `develop` (REQ-045, REQ-200).
#          Standalone --resume, optionally with --dev/--develop, validates and publishes
#          existing release objects unchanged.
# @param extra {List[str] | None} CLI argument strings; accepted flags: `--include-patch`,
#        `--dev`/`--develop` (REQ-200); release scripts come from the local
#        `build_script` and `pre_release_check` keys (REQ-166, REQ-318).
# @return None; delegates to `_run_release_command("major", ...)`.
# @exception SystemExit Exit code 1 on invalid operands or release-flow failure.
# @satisfies REQ-026, REQ-045, REQ-072, REQ-166, REQ-167, REQ-168, REQ-200
def cmd_major(extra):
    changelog_args, dev_release = _parse_release_flags(extra, "major")
    _run_release_command(
        "major", changelog_args=changelog_args, dev_release=dev_release
    )


## @brief CLI entry-point for the `minor` release subcommand.
# @details Increments the minor semver index (resets patch to 0), merges and pushes to both
#          configured `develop` and `master` branches, regenerates changelog via a temporary local
#          tag on `work`, and creates the definitive release tag on `master` immediately before
#          publication; pushes develop alone, then master and the exact tag atomically.
#          `--dev`/`--develop` limits the workflow to configured `develop` (REQ-045, REQ-200).
#          Standalone --resume, optionally with --dev/--develop, validates and publishes
#          existing release objects unchanged.
# @param extra {List[str] | None} CLI argument strings; accepted flags: `--include-patch`,
#        `--dev`/`--develop` (REQ-200); release scripts come from the local
#        `build_script` and `pre_release_check` keys (REQ-166, REQ-318).
# @return None; delegates to `_run_release_command("minor", ...)`.
# @exception SystemExit Exit code 1 on invalid operands or release-flow failure.
# @satisfies REQ-026, REQ-045, REQ-072, REQ-166, REQ-167, REQ-168, REQ-200
def cmd_minor(extra):
    changelog_args, dev_release = _parse_release_flags(extra, "minor")
    _run_release_command(
        "minor", changelog_args=changelog_args, dev_release=dev_release
    )


## @brief CLI entry-point for the `patch` release subcommand.
# @details Increments the patch semver index and runs the same default workflow as `major`
#          and `minor`: integrates work/develop/master, tags configured `master`, pushes
#          develop alone, then master and the exact tag atomically (REQ-072).
#          `--dev`/`--develop` limits the workflow to configured `develop` (REQ-045, REQ-200);
#          --include-patch is auto-included in the changelog regeneration step.
#          Standalone --resume, optionally with --dev/--develop, validates and publishes
#          existing release objects unchanged.
# @param extra {List[str] | None} CLI argument strings; accepted flags: `--include-patch`,
#        `--dev`/`--develop` (REQ-200); release scripts come from the local
#        `build_script` and `pre_release_check` keys (REQ-166, REQ-318).
# @return None; delegates to `_run_release_command("patch", ...)`.
# @exception SystemExit Exit code 1 on invalid operands or release-flow failure.
# @satisfies REQ-026, REQ-045, REQ-072, REQ-166, REQ-167, REQ-168, REQ-200
def cmd_patch(extra):
    changelog_args, dev_release = _parse_release_flags(extra, "patch")
    _run_release_command(
        "patch", changelog_args=changelog_args, dev_release=dev_release
    )


## @brief CLI entry-point for the `backup` workflow subcommand.
# @details Runs the same preflight checks used by `major`/`minor`/`patch`, then integrates the
#          configured `work` branch into the configured `develop` branch and pushes `develop`
#          to its remote tracking branch before returning to `work`.
# @param extra Iterable of CLI argument strings; accepted token: `--help` only.
# @return None; delegates to `_run_backup_command()`.
# @satisfies REQ-047, REQ-048, REQ-049
def cmd_backup(extra):
    args = _to_args(extra)
    if args == ["--help"]:
        print_command_help("backup")
        return
    if args:
        print("git backup does not accept positional arguments.", file=sys.stderr)
        sys.exit(1)
    _run_backup_command()


## @brief CLI entry-point for the `changelog` subcommand.
# @details Parses flags, delegates to `generate_changelog_document`, and writes or prints the result.
#          Accepted flags: `--include-patch`, `--force-write`, `--print-only`,
#          `--disable-history`, `--help`.
#          Exits with status 2 on argument errors or when not inside a git repository.
#          Exits with status 1 when `CHANGELOG.md` already exists and `--force-write` was not supplied.
# @param extra Iterable of CLI argument strings following the `changelog` subcommand token.
# @return None; side-effects: writes `CHANGELOG.md` to disk or prints to stdout.
# @satisfies REQ-018, REQ-040, REQ-041, REQ-043
def cmd_changelog(extra):
    parser = argparse.ArgumentParser(prog="g changelog", add_help=False)
    parser.add_argument("--force-write", dest="force_write", action="store_true")
    parser.add_argument("--include-patch", dest="include_patch", action="store_true")
    parser.add_argument("--print-only", action="store_true")
    parser.add_argument(
        "--disable-history", dest="disable_history", action="store_true"
    )
    parser.add_argument("--help", action="store_true")
    try:
        args = parser.parse_args(list(extra))
    except SystemExit:
        print("Invalid arguments for g changelog.", file=sys.stderr)
        sys.exit(2)
    if args.help:
        print_command_help("changelog")
        return
    if not is_inside_git_repo():
        print("Error: run g changelog inside a Git repository.", file=sys.stderr)
        sys.exit(2)
    repo_root = get_git_root()
    content = generate_changelog_document(
        repo_root, args.include_patch, args.disable_history
    )
    if args.print_only:
        print(content, end="")
        return
    destination = Path(repo_root) / "CHANGELOG.md"
    if destination.exists() and not args.force_write:
        print(
            "CHANGELOG.md already exists. Use --force-write to overwrite it or --print-only to show the new content.",
            file=sys.stderr,
        )
        sys.exit(1)
    destination.write_text(content, encoding="utf-8")
    print(f"\nGenerated file: {destination}")


## @brief Constant `COMMANDS` used by CLI runtime paths and policies.

COMMANDS = {
    "aa": cmd_aa,
    "ar": cmd_ar,
    "backup": cmd_backup,
    "bd": cmd_bd,
    "br": cmd_br,
    "chver": cmd_chver,
    "changelog": cmd_changelog,
    "change": cmd_change,
    "implement": cmd_implement,
    "ck": cmd_ck,
    "cm": cmd_cm,
    "co": cmd_co,
    "dc": cmd_dc,
    "dcc": cmd_dcc,
    "dccc": cmd_dccc,
    "dcd": cmd_dcd,
    "dcm": cmd_dcm,
    "ddm": cmd_ddm,
    "de": cmd_de,
    "di": cmd_di,
    "dime": cmd_dime,
    "diyou": cmd_diyou,
    "docs": cmd_docs,
    "dw": cmd_dw,
    "dwc": cmd_dwc,
    "dwcc": cmd_dwcc,
    "ed": cmd_ed,
    "fix": cmd_fix,
    "fe": cmd_fe,
    "feall": cmd_feall,
    "get": cmd_get,
    "gp": cmd_gp,
    "gr": cmd_gr,
    "l": cmd_l,
    "lb": cmd_lb,
    "lg": cmd_lg,
    "lh": cmd_lh,
    "ll": cmd_ll,
    "lm": cmd_lm,
    "ls": cmd_ls,
    "lsi": cmd_lsi,
    "lsa": cmd_lsa,
    "lt": cmd_lt,
    "major": cmd_major,
    "misc": cmd_misc,
    "me": cmd_me,
    "minor": cmd_minor,
    "new": cmd_new,
    "o": cmd_o,
    "cover": cmd_cover,
    "str": cmd_str,
    "refactor": cmd_refactor,
    "patch": cmd_patch,
    "ra": cmd_ra,
    "pl": cmd_pl,
    "pt": cmd_pt,
    "pu": cmd_pu,
    "revert": cmd_revert,
    "rollback": cmd_rollback,
    "rf": cmd_rf,
    "rmloc": cmd_rmloc,
    "rmstg": cmd_rmstg,
    "rmtg": cmd_rmtg,
    "rmunt": cmd_rmunt,
    "rs": cmd_rs,
    "rshrd": cmd_rshrd,
    "rskep": cmd_rskep,
    "rsmix": cmd_rsmix,
    "rsmrg": cmd_rsmrg,
    "rssft": cmd_rssft,
    "st": cmd_st,
    "tg": cmd_tg,
    "unstg": cmd_unstg,
    "wt": cmd_wt,
    "wtl": cmd_wtl,
    "wtp": cmd_wtp,
    "wtd": cmd_wtd,
    "wip": cmd_wip,
    "ver": cmd_ver,
    "style": cmd_style,
}


## @brief Execute `print_command_help` runtime logic for Git-Alias CLI.
# @details Executes `print_command_help` using deterministic CLI control-flow and explicit error propagation.
# @param name Input parameter consumed by `print_command_help`.
# @param width Input parameter consumed by `print_command_help`.
# @return Result emitted by `print_command_help` according to command contract.
def print_command_help(name, width=None):
    description = HELP_TEXTS.get(name, "No help text is available for this command.")
    if width is None:
        print(f"{name} - {description}")
    else:
        print(f"{name.ljust(width)} - {description}")


## @brief Render management help, schema-derived values, and sorted aliases.
# @details O(N) output; retains section order and delegates the configuration
# tree to the annotated values renderer. Reads CONFIG without changing files
# or state.
# @return {None} Writes English help to stdout.
# @satisfies DES-009, REQ-016, REQ-192, REQ-243, REQ-250
def print_all_help():
    print(f"Usage: g <command> [options] ({get_cli_version()})")
    print()
    print("Management Commands:")
    for flag, description in MANAGEMENT_HELP:
        print(f"  {flag} - {description}")
    print()
    print("Configuration Parameters:")
    values = {
        scope: {key: CONFIG.get(key, spec.default) for key, spec in schema.fields.items()}
        for scope, schema in configuration.SCHEMA.items()
    }
    print(configuration.render_values_tree(values))
    print()
    print("Commands:")
    help_width = max(len(name) for name in HELP_TEXTS)
    for name in sorted(COMMANDS.keys()):
        print("  ", end="")
        print_command_help(name, width=help_width)


## @brief Execute `main` runtime logic for Git-Alias CLI.
# @details Executes `main` using deterministic CLI control-flow and explicit error propagation.
#          Management dispatch: `--ver`/`--version` prints the installed version
#          plus the latest PyPI and GitHub versions as three REQ-241-aligned
#          `Current Installed`/`Latest @ PyPI`/`Latest @ GitHub` lines (REQ-202);
#          the GitHub failure path renders the REQ-241 `Latest @ GitHub` line
#          with `unknown (<reason>)` value (REQ-230); `--upgrade`
#          selects the PyPI default source or the GitHub source via
#          `--develop` (equivalent `--dev`) (REQ-001, REQ-201) and rejects
#          `--develop`/`--dev` outside `--upgrade`/`major`/`minor`/`patch`
#          (REQ-203); rejects a first-token `--force` outside `--upgrade`
#          (REQ-238) and forwards the `--force` selector so the install argv
#          carries the uv forcing options when requested (REQ-236, REQ-237).
#          Configuration commands route before alias flag validation so values
#          remain opaque arguments. O(N) dispatch plus delegated I/O; no migration.
# @param argv {list[str] | None} Explicit argv or process arguments.
# @param check_updates {bool} Enable ordinary startup checks.
# @return {None} Delegated output or command completion.
# @throws SystemExit Invalid operands, configuration failure, or command failure.
# @satisfies REQ-001, REQ-030, REQ-201, REQ-202, REQ-203, REQ-230, REQ-238, REQ-241, REQ-243, REQ-248, REQ-253, REQ-255
def main(argv=None, *, check_updates: bool = True):
    args = list(argv) if argv is not None else sys.argv[1:]
    force_online_update_check = bool(args) and args[0] in ("--ver", "--version")
    git_root = get_git_root()
    config_args = args
    if len(args) == 2 and args[0] == "--help" and args[1] in configuration.COMMAND_HELP:
        config_args = [args[1], "--help"]
    is_config_command = bool(config_args) and config_args[0] in configuration.COMMAND_HELP
    if not is_config_command:
        load_cli_config(git_root)
    pypi_latest_version: Optional[str] = None
    if check_updates or force_online_update_check:
        pypi_latest_version = check_for_newer_version(
            repo_root=git_root,
            timeout_seconds=VERSION_CHECK_TIMEOUT_SECONDS,
            ignore_idle_cache=force_online_update_check,
        )
    if is_config_command:
        try:
            configuration.execute(config_args, {
                "Global": get_global_config_path(),
                "Local": get_config_path(git_root),
            })
        except (ValueError, OSError) as exc:
            print(f"Configuration error: {exc}", file=sys.stderr)
            sys.exit(1)
        return
    if not args:
        print("Please provide a command or --help", file=sys.stderr)
        print_all_help()
        sys.exit(1)
    if args[0] == "--help" and len(args) > 1 and args[1] not in COMMANDS:
        print(f"Unknown command: {args[1]}", file=sys.stderr)
        sys.exit(1)
    if ("--develop" in args or "--dev" in args) and args[0] not in (
        "--upgrade",
        "major",
        "minor",
        "patch",
    ):
        print(
            "Options '--develop' and '--dev' are supported only with '--upgrade', 'major', 'minor', and 'patch'.",
            file=sys.stderr,
        )
        sys.exit(1)
    if "--force" in args and args[0] != "--upgrade":
        print(
            "Option '--force' is supported only with '--upgrade'.",
            file=sys.stderr,
        )
        sys.exit(1)
    if args[0] in ("--ver", "--version"):
        github_latest_version, github_failure_reason = _fetch_github_latest_version(
            timeout_seconds=VERSION_CHECK_TIMEOUT_SECONDS
        )
        installed_version = get_cli_version()
        pypi_report_value = pypi_latest_version or "unavailable"
        print(_format_version_report_line("Current Installed", installed_version))
        print(_format_version_report_line("Latest @ PyPI", pypi_report_value))
        if github_latest_version:
            print(_format_version_report_line("Latest @ GitHub", github_latest_version))
        else:
            github_report_value = f"unknown ({github_failure_reason or 'unavailable'})"
            print(_format_version_report_line("Latest @ GitHub", github_report_value))
        return
    if args[0] == "--upgrade":
        upgrade_self(
            git_root,
            github=("--develop" in args or "--dev" in args),
            force=("--force" in args),
        )
        return
    if args[0] == "--uninstall":
        uninstall_self()
        return
    if args[0] == "--help":
        if len(args) == 1:
            print_all_help()
            return
        name = args[1]
        if name in COMMANDS:
            print_command_help(name)
        return
    name = args[0]
    extras = args[1:]
    try:
        if name not in COMMANDS:
            run_git_cmd([name], extras)
            return
        if "--help" in extras:
            if name in RESET_HELP_COMMANDS:
                COMMANDS[name](extras)
            else:
                print_command_help(name)
            return
        COMMANDS[name](extras)
    except CommandExecutionError as exc:
        err_text = CommandExecutionError._decode_stream(exc.stderr).strip()
        if err_text:
            print(err_text, file=sys.stderr)
        sys.exit(exc.returncode or 1)
    except RuntimeError as exc:
        print(str(exc), file=sys.stderr)
        sys.exit(1)
