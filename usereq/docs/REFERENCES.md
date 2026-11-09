# Files Structure
```
.
└── src
    └── git_alias
        ├── __init__.py
        ├── __main__.py
        ├── core.py
        └── foresta.py
```

# __init__.py | Python | 13L | 0 symbols | 1 imports | 7 comments
> Path: `src/git_alias/__init__.py`

## Imports
```
from .core import main  # noqa: F401
```


---

# __main__.py | Python | 11L | 0 symbols | 2 imports | 5 comments
> Path: `src/git_alias/__main__.py`

## Imports
```
from .core import main
import sys
```


---

# core.py | Python | 6093L | 294 symbols | 18 imports | 1799 comments
> Path: `src/git_alias/core.py`

## Imports
```
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
from git_alias import foresta
```

## Definitions

- var `CONFIG_FILENAME = ".galias.conf"` (L33)
- @brief Repository-local configuration filename resolved from repository root.
- @details Value `.galias.conf` per DES-006/REQ-014; loaded by `load_cli_config`
and normalized by `write_default_config` for the five DES-006 local
keys (`master`, `develop`, `work`, `default_commit_module`, `ver_rules`).
No `.g.conf` fallback exists: backward compatibility is not implemented.
- @satisfies DES-006, DES-009, REQ-014, REQ-017
- var `GLOBAL_CONFIG_DIRECTORY = ".config/galias"` (L39)
- @brief Global configuration directory under `$HOME`.
- @details Value `.config/galias` after the `galias` distribution rename from
`git-alias`; combined with `$HOME` by `get_global_config_path` to
locate `config.json` (CTN-003, DES-006, REQ-186).
- @satisfies CTN-003, DES-006, REQ-186
- var `GLOBAL_CONFIG_FILENAME = "config.json"` (L41)
- @brief Constant `GLOBAL_CONFIG_FILENAME` used by CLI runtime paths and policies.
- var `UV_TOOL_NAME = "galias"` (L48)
- @brief Astral uv tool and distribution name for self-management flows.
- @details Value `galias` after the distribution rename from `git-alias`;
drives `uv tool install` (REQ-001), `uv tool uninstall` (REQ-002),
and the `~/.cache/<tool>` update-check cache directory (REQ-136).
- @satisfies REQ-001, REQ-002, REQ-136
- var `PYPI_PROJECT_NAME = UV_TOOL_NAME` (L56)
- @brief PyPI project name sourcing update checks and self-upgrade installs.
- @details Canonical PyPI distribution identifier equal to `UV_TOOL_NAME`;
composes the PyPI JSON API endpoint (REQ-124) and names the
`uv tool install` self-upgrade target (REQ-001). PyPI is the only
remote source used by default version verification and upgrades
(REQ-199).
- @satisfies REQ-001, REQ-124, REQ-199
- var `PYPI_LATEST_VERSION_API = f"https://pypi.org/pypi/{PYPI_PROJECT_NAME}/json"` (L62)
- @brief PyPI JSON API endpoint resolving the latest published version.
- @details Fixed endpoint `https://pypi.org/pypi/galias/json`; the update check
parses the latest version from its `info.version` JSON field
(REQ-124) and default checks query no other remote source (REQ-199).
- @satisfies REQ-124, REQ-199
- var `GITHUB_REPOSITORY = "Ogekuri/GAlias"` (L68)
- @brief Upstream GitHub repository hosting intermediate and test releases.
- @details Value `Ogekuri/GAlias`; composes the GitHub latest-release API
endpoint (REQ-204) and the git upgrade source (REQ-201). GitHub is
queried only by REQ-201 upgrades and REQ-202 version reporting.
- @satisfies REQ-201, REQ-202, REQ-204
- var `GITHUB_LATEST_RELEASE_API = (` (L77)
- @brief GitHub latest-release API endpoint for version reporting and upgrade tag resolution.
- @details Fixed endpoint `https://api.github.com/repos/Ogekuri/GAlias/releases/latest`;
`_fetch_github_latest_version` parses the release `tag_name` JSON
field stripping one leading `v` (REQ-204), and
`_fetch_github_latest_release_tag` returns the same `tag_name`
verbatim to select the REQ-209 upgrade ref (REQ-208). This endpoint
never participates in default update checks (REQ-199).
- @satisfies REQ-202, REQ-204, REQ-208, REQ-199
- var `GITHUB_UPGRADE_SOURCE = f"git+https://github.com/{GITHUB_REPOSITORY}"` (L86)
- @brief Git source specifier base for GitHub-sourced self-upgrades.
- @details Value `git+https://github.com/Ogekuri/GAlias`; consumed only by the
REQ-201 `--upgrade --develop` (equivalent `--dev`) flow, where
`_build_github_upgrade_command` appends the REQ-208-resolved
release tag as `@<tag>` to form the uv `--from` override (REQ-209).
- @satisfies REQ-201, REQ-209
- var `UV_TOOL_UPGRADE_COMMAND = (` (L93)
- @brief Self-upgrade command installing the latest PyPI release.
- @details Executes `uv tool install galias --force` so Astral uv reinstalls
the tool from the PyPI default source (REQ-001); the default path
carries no `--from` override, keeping PyPI the only default upgrade
source (REQ-199, REQ-201).
- @satisfies REQ-001, REQ-199
- var `UV_TOOL_UNINSTALL_COMMAND = ("uv", "tool", "uninstall", UV_TOOL_NAME)` (L101)
- @brief Constant `UV_TOOL_UNINSTALL_COMMAND` used by CLI runtime paths and policies.
- var `VERSION_CHECK_CACHE_FILE = (` (L104)
- @brief Constant `VERSION_CHECK_CACHE_FILE` used by CLI runtime paths and policies.
- var `VERSION_CHECK_IDLE_DELAY_SECONDS = 3600` (L111)
- @brief Constant `VERSION_CHECK_IDLE_DELAY_SECONDS` used by CLI runtime paths and policies.
- var `VERSION_CHECK_ERROR_IDLE_DELAY_SECONDS = 86400` (L113)
- @brief Constant `VERSION_CHECK_ERROR_IDLE_DELAY_SECONDS` used by CLI runtime paths and policies.
- var `VERSION_CHECK_TIMEOUT_SECONDS = 2.0` (L115)
- @brief Constant `VERSION_CHECK_TIMEOUT_SECONDS` used by CLI runtime paths and policies.
- var `VERSION_AVAILABLE_COLOR = "\033[92;1m"` (L117)
- @brief Constant `VERSION_AVAILABLE_COLOR` used by CLI runtime paths and policies.
- var `VERSION_ERROR_COLOR = "\033[31;1m"` (L119)
- @brief Constant `VERSION_ERROR_COLOR` used by CLI runtime paths and policies.
- var `ANSI_COLOR_RESET = "\033[0m"` (L121)
- @brief Constant `ANSI_COLOR_RESET` used by CLI runtime paths and policies.
- var `DEFAULT_VER_RULES = [` (L125)
- @brief Constant `DEFAULT_VER_RULES` used by CLI runtime paths and policies.
- var `VERSION_CLEANUP_REGEXES = [` (L132)
- @brief Constant `VERSION_CLEANUP_REGEXES` used by CLI runtime paths and policies.
- var `VERSION_CLEANUP_PATTERNS = [re.compile(pattern) for pattern in VERSION_CLEANUP_REGEXES]` (L143)
- @brief Constant `VERSION_CLEANUP_PATTERNS` used by CLI runtime paths and policies.
- var `ANSI_ESCAPE_RE = re.compile(r"\x1b\[[0-9;]*m")` (L144)
- var `DEFAULT_GP_COMMAND = "gitui"` (L150)
- @brief Constant `DEFAULT_GP_COMMAND` used by CLI runtime paths and policies.
- @details Default terminal commit-graph launcher for the `gp` command pair
(REQ-186); imposed default value `gitui` per REQ-191.
- @satisfies REQ-191
- var `DEFAULT_GR_COMMAND = "tig"` (L155)
- @brief Constant `DEFAULT_GR_COMMAND` used by CLI runtime paths and policies.
- @details Default terminal tag/decoration-graph launcher for the `gr`
command pair (REQ-186); imposed default value `tig` per REQ-191.
- @satisfies REQ-191
- var `GIT_DIFFTOOL_COMMAND = ("git", "difftool", "-d")` (L160)
- var `DEFAULT_CONFIG = {` (L171)
- @brief Constant `DEFAULT_CONFIG` used by CLI runtime paths and policies.
- @details Canonical default configuration. The eight REQ-186 global command
keys hold the imposed REQ-191 default values and are declared
contiguously in the REQ-192 canonical order
(`edit_command`, `edit_command_gfx`, `diff_command`,
`diff_command_gfx`, `gr_command`, `gr_command_gfx`, `gp_command`,
`gp_command_gfx`) because `print_all_help` renders Configuration
Parameters in dict insertion order.
- @satisfies REQ-191, REQ-192
- var `CONFIG = DEFAULT_CONFIG.copy()` (L196)
- @brief Constant `CONFIG` used by CLI runtime paths and policies.
- var `BRANCH_KEYS = ("master", "develop", "work")` (L199)
- @brief Constant `BRANCH_KEYS` used by CLI runtime paths and policies.
- var `LOCAL_CONFIG_KEYS = ("master", "develop", "work", "default_commit_module", "ver_rules")` (L201)
- @brief Constant `LOCAL_CONFIG_KEYS` used by CLI runtime paths and policies.
- var `GLOBAL_CONFIG_KEYS = (` (L209)
- @brief Constant `GLOBAL_CONFIG_KEYS` used by CLI runtime paths and policies.
- @details Ordered inventory of the eight REQ-186 global command keys in the
REQ-192 canonical order; drives global config loading,
`--write-config` normalization (REQ-014), and persisted JSON key
insertion order. Out-of-scope keys are ignored and never persisted
(REQ-015); no legacy-key migration exists.
- @satisfies REQ-014, REQ-015, REQ-192
- var `MANAGEMENT_HELP = [` (L221)
- @brief Constant `MANAGEMENT_HELP` used by CLI runtime paths and policies.
### fn `def get_config_value(name)` (L238-241)
- @brief Execute `get_config_value` runtime logic for Git-Alias CLI.
- @details Executes `get_config_value` using deterministic CLI control-flow and explicit error propagation.
- @param name Input parameter consumed by `get_config_value`.
- @return Result emitted by `get_config_value` according to command contract.

### fn `def get_branch(name)` (L246-251)
- @brief Execute `get_branch` runtime logic for Git-Alias CLI.
- @details Executes `get_branch` using deterministic CLI control-flow and explicit error propagation.
- @param name Input parameter consumed by `get_branch`.
- @return Result emitted by `get_branch` according to command contract.

### fn `def get_editor()` (L255-258)
- @brief Execute `get_editor` runtime logic for Git-Alias CLI.
- @details Executes `get_editor` using deterministic CLI control-flow and explicit error propagation.
- @return Result emitted by `get_editor` according to command contract.

### fn `def _load_config_rules(key, fallback)` `priv` (L267-294)
- @brief Load rule pairs from the active configuration for a rule-bearing config key.
- @details Accepts dict entries `{"pattern", "regex"}` and `(pattern, regex)` sequence
entries, strips both fields, and drops invalid entries. Negation patterns starting
with `!` are accepted without a `regex` field and stored with `None` regex.
- @param key {str} Configuration key to read from `CONFIG`.
- @param fallback {List[Tuple[str, str]]} Default rule list used when no valid entry remains.
- @return {List[Tuple[str, Optional[str]]]} Parsed `(pattern, regex)` rule pairs; negation entries carry `None` regex.
- @satisfies REQ-162, REQ-207

### fn `def get_version_rules()` (L298-301)
- @brief Execute `get_version_rules` runtime logic for Git-Alias CLI.
- @details Executes `get_version_rules` using deterministic CLI control-flow and explicit error propagation.
- @return Result emitted by `get_version_rules` according to command contract.

### fn `def get_cli_version()` (L305-316)
- @brief Execute `get_cli_version` runtime logic for Git-Alias CLI.
- @details Executes `get_cli_version` using deterministic CLI control-flow and explicit error propagation.
- @return Result emitted by `get_cli_version` according to command contract.

### fn `def _normalize_semver_text(text: str) -> str` `priv` (L321-327)
- @brief Execute `_normalize_semver_text` runtime logic for Git-Alias CLI.
- @details Executes `_normalize_semver_text` using deterministic CLI control-flow and explicit error propagation.
- @param text Input parameter consumed by `_normalize_semver_text`.
- @return Result emitted by `_normalize_semver_text` according to command contract.

### fn `def _print_update_available_warning(` `priv` (L336-338)
- @brief Emit the standardized bright-green update warning for newer available versions.
- @details Formats the warning using the REQ-123 contract
`Update available: <latest> (installed: <current>)`,
applies ANSI bright-green color, and writes to stderr without altering process
control-flow.
- @param current Parsed current semantic version tuple `(major, minor, patch)`.
- @param latest_text Latest available semantic version text.
- @return None.

### fn `def _print_update_check_error(detail: str) -> None` `priv` (L356-362)
- @brief Emit a standardized bright-red update-check error message.
- @details Prefixes diagnostic payload with `Version check failed:` and applies ANSI
bright-red color formatting while preserving caller control-flow.
- @param detail Human-readable diagnostic detail.
- @return None.

### fn `def _resolve_release_api_url(repo_root: Path) -> str` `priv` (L369-373)
- @brief Resolve the fixed PyPI JSON API URL for update checks.
- @details Returns the constant PyPI endpoint configured for the program package.
The `repo_root` parameter is intentionally ignored to keep call sites stable.
- @param repo_root Repository root placeholder parameter.
- @return Full PyPI JSON API URL string.
- @satisfies REQ-124

### fn `def _coerce_unix_timestamp(value: object) -> Optional[int]` `priv` (L379-384)
- @brief Coerce candidate JSON timestamp values into unix-second integers.
- @details Accepts numeric values (`int`/`float`) and converts them to integer unix
seconds; all non-numeric values are rejected.
- @param value Candidate timestamp value loaded from JSON cache payload.
- @return Parsed unix timestamp integer when numeric; otherwise `None`.

### fn `def _write_version_check_state(` `priv` (L393-396)
- @brief Persist update-check idle-time cache state to JSON file.
- @details Writes canonical fields `last_check_unix`, `last_check_human`,
`idle_until_unix`, and `idle_until_human` using second-precision
timestamps and emits standardized error diagnostics on I/O or timestamp failures.
- @param last_check_unix Unix timestamp of last successful version check.
- @param idle_until_unix Unix timestamp until next remote check is disabled.
- @return None.
- @satisfies REQ-126 REQ-131 REQ-136 REQ-137

### fn `def _write_version_check_error_state(` `priv` (L431-433)
- @brief Persist the canonical extended idle-time state for version-check errors.
- @details Reuses cached `last_check_unix` when available, normalizes missing or
invalid cached values to `0`, and writes `idle_until_unix = now_unix +
VERSION_CHECK_ERROR_IDLE_DELAY_SECONDS` to suppress repeated failing
version checks across all terminal error branches.
- @param cache_data Parsed idle-time JSON object from prior state.
- @param now_unix Current unix timestamp captured by the active release-check attempt.
- @return None.
- @satisfies REQ-130 REQ-131 REQ-137

### fn `def check_for_newer_version(` (L457-461)
- @brief Execute `check_for_newer_version` runtime logic for Git-Alias CLI.
- @details Executes `check_for_newer_version` using deterministic CLI control-flow,
explicit error propagation, a fixed 3600-second idle window after
successful release checks, and a fixed 86400-second idle window after
terminal version-check errors while rewriting the idle-time JSON before
returning control on every error path. The remote source is exclusively
the PyPI JSON API `info.version` field (REQ-124, REQ-199).
- @param repo_root Input parameter consumed by `check_for_newer_version`.
- @param timeout_seconds Input parameter consumed by `check_for_newer_version`.
- @param ignore_idle_cache When `True`, bypasses `idle_until_unix` gating and forces an online check.
- @return {Optional[str]} Latest PyPI version text on success; None when the
check is skipped, unavailable, or failed.
- @satisfies REQ-123 REQ-124 REQ-126 REQ-127 REQ-129 REQ-130 REQ-131 REQ-137 REQ-199

### fn `def _build_github_upgrade_command(tag: str) -> Tuple[str, ...]` `priv` (L587-598)
- @brief Build the uv argv installing the newest GitHub release tag.
- @details Composes the REQ-209 self-upgrade command by appending the
REQ-208-resolved release tag to `GITHUB_UPGRADE_SOURCE` as the
pip/uv direct-URL reference `git+https://github.com/Ogekuri/GAlias@<tag>`,
so Astral uv reinstalls the tool from the newest tagged release
regardless of the branch containing it (REQ-201).
- @param tag {str} Raw GitHub release tag name (REQ-208), including any leading `v`.
- @return {Tuple[str, ...]} `uv tool install --force --from <source>@<tag> galias` argv.
- @satisfies REQ-209, REQ-201

### fn `def _github_failure_reason(exc: BaseException) -> str` `priv` (L614-635)
- @brief Compose a non-empty English failure reason for an intercepted GitHub fetch exception.
- @details Intercepts transport and payload failures raised by the GitHub
latest-release fetch and derives a deterministic diagnostic:
`HTTPError` instances render `HTTP <code>: <reason phrase>:
<api message>`, appending the API-provided JSON `message` field
when the error body decodes to a JSON object containing a
non-empty `message` string; `URLError` instances render the
bare socket reason; every other exception renders its text,
falling back to the exception class name when the text is blank.
Never mutates state and never raises: the error-body read is
guarded so reason derivation stays total.
- @param exc {BaseException} Exception intercepted by the GitHub fetch guard.
- @return {str} Non-empty English failure reason (REQ-231).
- @note Complexity: O(1) excluding the single error-body read.
- @satisfies REQ-231

### fn `def _fetch_github_release_tag_with_reason(` `priv` (L653-654)
- @brief Fetch the raw latest GitHub release tag together with its failure reason.
- @details Performs exactly one HTTP GET against `GITHUB_LATEST_RELEASE_API`
(REQ-208), decodes the JSON payload, and returns the `tag_name`
field verbatim including any leading `v`, so the value can be
appended to `GITHUB_UPGRADE_SOURCE` as a git ref (REQ-209).
Every transport or payload failure is intercepted and converted
by `_github_failure_reason` into a non-empty English reason
(REQ-231); no diagnostic is emitted and no exception is raised,
keeping REQ-127 reporting at the caller boundary. Never mutates
the PyPI idle-time cache.
- @param timeout_seconds {float} Request timeout in seconds (REQ-125).
- @return {Tuple[Optional[str], Optional[str]]} `(tag_name, failure_reason)`;
`failure_reason` is None on success; `tag_name` is None on transport
or decode failure and empty string when the payload lacks a
`tag_name` field.
- @note Complexity: O(payload) for one HTTP GET plus one JSON decode.
- @satisfies REQ-208, REQ-231

### fn `def _fetch_github_latest_release_tag(` `priv` (L701-702)
- @brief Fetch the raw latest GitHub release tag name for upgrade ref selection.
- @details Delegates transport, decoding, and reason derivation to
`_fetch_github_release_tag_with_reason` (REQ-208). On transport or
decode failure it prints the standardized bright-red update-check
diagnostic (REQ-127) carrying the REQ-231 failure reason and
returns None without raising; the fetch never mutates the PyPI
idle-time cache.
- @param timeout_seconds {float} Request timeout in seconds (REQ-125).
- @return {Optional[str]} Raw `tag_name` text; None on transport or decode
failure; empty string when the payload lacks a `tag_name` field.
- @see _fetch_github_release_tag_with_reason, _github_failure_reason
- @satisfies REQ-208, REQ-127, REQ-231

### fn `def _fetch_github_latest_version(` `priv` (L729-730)
- @brief Fetch the latest GitHub release version together with its failure reason.
- @details Delegates transport and payload decoding to
`_fetch_github_release_tag_with_reason` (REQ-204), strips one
leading `v` from the raw `tag_name`, and normalizes the result as
a semantic version. Failure paths print the standardized
bright-red update-check diagnostic (REQ-127) and return a
non-empty REQ-231 failure reason so `main` renders
`GitHub latest: unknown (<reason>)` (REQ-230); the fetch is
report-only (REQ-202) and never mutates the PyPI idle-time cache.
- @param timeout_seconds {float} Request timeout in seconds (REQ-125).
- @return {Tuple[Optional[str], Optional[str]]} `(version, failure_reason)`;
normalized latest GitHub release version with None reason on
success; None version with non-empty reason on any request,
payload, or semver failure.
- @note Complexity: O(payload) for one HTTP GET plus one JSON decode.
- @satisfies REQ-202, REQ-204, REQ-230, REQ-231

### fn `def get_git_root()` (L751-766)
- @brief Execute `get_git_root` runtime logic for Git-Alias CLI.
- @details Executes `get_git_root` using deterministic CLI control-flow and explicit error propagation.
- @return Result emitted by `get_git_root` according to command contract.

### fn `def get_config_path(root=None)` (L771-775)
- @brief Execute `get_config_path` runtime logic for Git-Alias CLI.
- @details Executes `get_config_path` using deterministic CLI control-flow and explicit error propagation.
- @param root Input parameter consumed by `get_config_path`.
- @return Result emitted by `get_config_path` according to command contract.

### fn `def get_global_config_path(home=None)` (L780-784)
- @brief Execute `get_global_config_path` runtime logic for Git-Alias CLI.
- @details Executes `get_global_config_path` using deterministic CLI control-flow and explicit error propagation.
- @param home Input parameter consumed by `get_global_config_path`.
- @return Result emitted by `get_global_config_path` according to command contract.

### fn `def _read_config_object(config_path)` `priv` (L789-807)
- @brief Execute `_read_config_object` runtime logic for Git-Alias CLI.
- @details Executes `_read_config_object` using deterministic CLI control-flow and explicit error propagation.
- @param config_path Input parameter consumed by `_read_config_object`.
- @return Result emitted by `_read_config_object` according to command contract.

### fn `def _apply_config_values(data, keys)` `priv` (L813-835)
- @brief Execute `_apply_config_values` runtime logic for Git-Alias CLI.
- @details Executes `_apply_config_values` using deterministic CLI control-flow and explicit error propagation.
- @param data Input parameter consumed by `_apply_config_values`.
- @param keys Input parameter consumed by `_apply_config_values`.
- @return Result emitted by `_apply_config_values` according to command contract.

### fn `def load_cli_config(root=None, home=None)` (L841-853)
- @brief Execute `load_cli_config` runtime logic for Git-Alias CLI.
- @details Executes `load_cli_config` using deterministic CLI control-flow and explicit error propagation.
- @param root Input parameter consumed by `load_cli_config`.
- @param home Input parameter consumed by `load_cli_config`.
- @return Result emitted by `load_cli_config` according to command contract.

### fn `def _write_missing_config_values(config_path, keys, create_parent=False)` `priv` (L867-915)
- @brief Normalize one configuration file to its canonical key set without migrating legacy keys.
- @details Reads the existing JSON object (when present), rebuilds it containing
only `keys`, fills missing or invalid entries with `DEFAULT_CONFIG`
values, and writes the result only when normalization changes the
persisted content. Out-of-scope keys (for example the legacy global
`editor` key) are ignored and are never read, migrated, or preserved
in the output object. Runtime loading never calls this function; it
runs only from `write_default_config` (`--write-config`).
- @param config_path {Path} Target configuration file path.
- @param keys {Tuple[str, ...]} Canonical key sequence defining the output key set and order.
- @param create_parent {bool} When True, create the parent directory before writing.
- @return {Path} The input `config_path` after optional normalization.
- @satisfies REQ-014, REQ-015, DES-006, REQ-097

### fn `def write_default_config(root=None, home=None)` (L921-934)
- @brief Execute `write_default_config` runtime logic for Git-Alias CLI.
- @details Executes `write_default_config` using deterministic CLI control-flow and explicit error propagation.
- @param root Input parameter consumed by `write_default_config`.
- @param home Input parameter consumed by `write_default_config`.
- @return Result emitted by `write_default_config` according to command contract.

### fn `def _parse_config_command_parts(command_line: str, config_key: str) -> List[str]` `priv` (L944-955)
- @brief Parse one configured launcher command line into argv tokens.
- @details Applies shell-like tokenization to the configured command line,
rejects malformed quoting, and rejects empty argv sequences before process
execution dispatch.
- @param command_line `str` — configured launcher command line.
- @param config_key `str` — configuration key used in error messages.
- @return `List[str]` — parsed argv tokens.
- @exception RuntimeError Raised when the configured command line is invalid or empty.
- @satisfies REQ-156, REQ-159

### fn `def _find_windows_shell_script_path(executable: str) -> Optional[str]` `priv` (L964-987)
- @brief Resolve non-PATHEXT Windows shell-script launcher paths.
- @details Searches the configured `PATH` for an exact filename match when the
launcher is a Git Bash style script such as `gitk` with no executable
extension. This bypasses `shutil.which(...)` limitations on Windows for
shell-script launchers not covered by `PATHEXT`.
- @param executable `str` — configured launcher token before argument parsing.
- @return `Optional[str]` — POSIX-normalized script path when found; otherwise `None`.
- @satisfies CTN-002

### fn `def _resolve_windows_shell_command_prefix(executable: str) -> Optional[List[str]]` `priv` (L997-1006)
- @brief Resolve a runnable Windows shell-script launcher prefix.
- @details Converts Git Bash style PATH entries such as `gitk` into a subprocess
argv prefix executable by Python on Windows. When a shell-script launcher is
detected, the command is executed through `sh` or `bash` so `subprocess.run`
does not fail with native Win32 executable lookup errors.
- @param executable `str` — configured launcher token before argument parsing.
- @return `Optional[List[str]]` — argv prefix `[shell_path, script_path]` when a
Windows shell-script launcher is available; otherwise `None`.
- @satisfies CTN-002

### fn `def _validated_config_command_parts(key: str, default_command: str) -> List[str]` `priv` (L1017-1030)
- @brief Validate configured launcher executable availability.
- @details Resolves the first argv token against the current-platform PATH
lookup rules and aborts command execution when the executable is unavailable.
On Windows, Git Bash shell-script launchers without executable extensions are
executed through `sh`/`bash` when present in `PATH`.
- @param key `str` — configuration key containing the launcher command line.
- @param default_command `str` — fallback command line when config is empty.
- @return `List[str]` — validated argv tokens ready for subprocess execution.
- @exception RuntimeError Raised when the configured command is invalid or the executable is unavailable.
- @satisfies CTN-002, REQ-157, REQ-159

### fn `def _is_graphical_environment() -> bool` `priv` (L1038-1043)
- @brief Detect whether the current execution environment is graphical.
- @details Implements the REQ-187 environment classification: non-POSIX
platforms are graphical desktop sessions; POSIX platforms are
graphical only when `DISPLAY` or `WAYLAND_DISPLAY` is set non-empty.
- @return `bool` True for graphical environments; False for terminal environments.
- @note Complexity: O(1) environment inspection; no subprocess execution.
- @satisfies REQ-187

### fn `def _environment_config_command_parts(` `priv` (L1056-1057)
- @brief Resolve the environment-selected variant of a paired external command.
- @details Implements REQ-186/REQ-187/REQ-188 dual-command resolution:
graphical environments select `<command_key>_gfx` when its configured
value is non-empty; every other case uses `<command_key`; empty or
absent `_gfx` values fall back to the terminal command. The selected
command line is validated through `_validated_config_command_parts`.
- @param command_key {str} Terminal command configuration key (e.g. `gp_command`).
- @param default_command {str} Fallback command line when the key value is empty.
- @return {List[str]} Validated argv tokens of the environment-selected command.
- @exception RuntimeError Raised when the selected command is invalid or unavailable.
- @note Complexity: O(1) excluding PATH lookup inside validation.
- @satisfies REQ-186, REQ-187, REQ-188

### fn `def _editor_base_command() -> List[str]` `priv` (L1075-1080)
- @brief Resolve the editor launcher command after executable validation.
- @details Returns the environment-selected validated editor argv sequence used
by the `ed` alias, choosing `edit_command_gfx` in graphical
environments per REQ-187/REQ-188.
- @return `List[str] — validated editor argv tokens.
- @exception RuntimeError Raised when the selected editor command is invalid or unavailable.
- @satisfies REQ-156, REQ-157, REQ-159, REQ-187

### fn `def run_editor_command(args)` (L1087-1090)
- @brief Execute `run_editor_command` runtime logic for Git-Alias CLI.
- @details Executes `run_editor_command` using deterministic CLI control-flow and explicit error propagation.
- @param args Input parameter consumed by `run_editor_command`.
- @return Result emitted by `run_editor_command` according to command contract.
- @exception RuntimeError Raised when the configured editor launcher is invalid or unavailable.
- @satisfies REQ-158, REQ-159

### fn `def _config_command_parts(key: str, default_command: str) -> List[str]` `priv` (L1101-1104)
- @brief Resolve configured graph launcher command parts after validation.
- @details Normalizes the configured command line, selects the environment
variant (`<key>_gfx` in graphical environments per REQ-187/REQ-188),
validates the executable on the current platform, and returns argv
tokens without fallback execution.
- @param key Input parameter consumed by `_config_command_parts`.
- @param default_command Input parameter consumed by `_config_command_parts`.
- @return Result emitted by `_config_command_parts` according to command contract.
- @exception RuntimeError Raised when the configured launcher is invalid or unavailable.
- @satisfies REQ-156, REQ-157, REQ-159, REQ-187

- var `HELP_TEXTS = {` (L1107)
- @brief Constant `HELP_TEXTS` used by CLI runtime paths and policies.
- var `RESET_HELP_COMMANDS = {"rs", "rshrd", "rskep", "rsmix", "rsmrg", "rssft"}` (L1274)
- @brief Constant `RESET_HELP_COMMANDS` used by CLI runtime paths and policies.
- var `LSI_DEFAULT_EXCLUDED_DIRS = frozenset(` (L1280)
- @brief Default directory/file names excluded from `lsi` output.
- @details Immutable set of path-component names that `cmd_lsi` filters out
by default via exact-match. Filtering is bypassed when `--include-all` is passed.
- @satisfies REQ-120
- var `LSI_DEFAULT_EXCLUDED_DIR_SUFFIXES = (".egg-info",)` (L1317)
- @brief Default directory-name suffixes excluded from `lsi` output.
- @details Tuple of suffix strings that `cmd_lsi` uses for suffix-match filtering
on each path component. A path component ending with any suffix in this tuple
is excluded. Filtering is bypassed when `--include-all` is passed.
- @satisfies REQ-122
### fn `def _to_args(extra)` `priv` (L1324-1327)
- @brief Execute `_to_args` runtime logic for Git-Alias CLI.
- @details Executes `_to_args` using deterministic CLI control-flow and explicit error propagation.
- @param extra Input parameter consumed by `_to_args`.
- @return Result emitted by `_to_args` according to command contract.

### class `class CommandExecutionError(RuntimeError)` : RuntimeError (L1330-1371)
- @brief Class `CommandExecutionError` models a typed runtime container/error boundary.
- @brief Execute `__init__` runtime logic for Git-Alias CLI.
- @details Captures subprocess execution metadata and exposes normalized human-readable failure text.
- @param self Input parameter consumed by `__init__`.
- @param exc Input parameter consumed by `__init__`.
- fn `def __init__(self, exc: subprocess.CalledProcessError)` `priv` (L1335-1342)
  - @brief Execute `__init__` runtime logic for Git-Alias CLI.
  - @param self Input parameter consumed by `__init__`.
  - @param exc Input parameter consumed by `__init__`.
  - @return Result emitted by `__init__` according to command contract.
- fn `def _format_message(self) -> str` `priv` (L1346-1356)
  - @brief Execute `_format_message` runtime logic for Git-Alias CLI.
  - @param self Input parameter consumed by `_format_message`.
  - @return Result emitted by `_format_message` according to command contract.
- fn `def _decode_stream(data) -> str` `priv` (L1361-1371)
  - @brief Execute `_decode_stream` runtime logic for Git-Alias CLI.
  - @param data Input parameter consumed by `_decode_stream`.
  - @return Result emitted by `_decode_stream` according to command contract.

### fn `def _run_checked(*popenargs, stream=False, **kwargs) -> Any` `priv` (L1386-1401)
- @brief Execute `_run_checked` runtime logic for Git-Alias CLI.
- @details Single external-command interception point (REQ-185): every external
process spawned by `core.py` executes through this wrapper. Default
mode runs `subprocess.run` with `check=True` and converts
`CalledProcessError` into `CommandExecutionError`; `stream=True` mode
returns a `subprocess.Popen` handle for streaming pipelines and
converts launch `OSError` into an explicit English `RuntimeError`.
- @param *popenargs Positional subprocess arguments (argv list plus extras).
- @param stream {bool} When True, spawn via `subprocess.Popen` for streaming use.
- @param **kwargs Forwarded subprocess keyword arguments (cwd, check, stdio).
- @return {Any} `CompletedProcess` in default mode; `Popen` handle in stream mode.
- @exception CommandExecutionError Raised in default mode on non-zero exit with check enabled.
- @exception RuntimeError Raised in stream mode when the process cannot launch.
- @satisfies REQ-185

### class `class VersionDetectionError(RuntimeError)` : RuntimeError (L1404-1407)
- @brief Class `VersionDetectionError` models a typed runtime container/error boundary.
- @details Represents deterministic failures encountered while resolving semantic versions from repository files.

### class `class ReleaseError(RuntimeError)` : RuntimeError (L1410-1413)
- @brief Class `ReleaseError` models a typed runtime container/error boundary.
- @details Represents release-flow precondition or orchestration failures.

### fn `def run_git_cmd(base_args, extra=None, cwd=None, **kwargs)` (L1421-1425)
- @brief Execute `run_git_cmd` runtime logic for Git-Alias CLI.
- @details Executes `run_git_cmd` using deterministic CLI control-flow and explicit error propagation.
- @param base_args Input parameter consumed by `run_git_cmd`.
- @param extra Input parameter consumed by `run_git_cmd`.
- @param cwd Input parameter consumed by `run_git_cmd`.
- @param **kwargs Input parameter consumed by `run_git_cmd`.
- @return Result emitted by `run_git_cmd` according to command contract.

### fn `def capture_git_output(base_args, cwd=None)` (L1431-1437)
- @brief Execute `capture_git_output` runtime logic for Git-Alias CLI.
- @details Executes `capture_git_output` using deterministic CLI control-flow and explicit error propagation.
- @param base_args Input parameter consumed by `capture_git_output`.
- @param cwd Input parameter consumed by `capture_git_output`.
- @return Result emitted by `capture_git_output` according to command contract.

### fn `def run_command(cmd, cwd=None)` (L1443-1446)
- @brief Execute `run_command` runtime logic for Git-Alias CLI.
- @details Executes `run_command` using deterministic CLI control-flow and explicit error propagation.
- @param cmd Input parameter consumed by `run_command`.
- @param cwd Input parameter consumed by `run_command`.
- @return Result emitted by `run_command` according to command contract.

### fn `def run_git_text(args, cwd=None, check=True)` (L1453-1470)
- @brief Execute `run_git_text` runtime logic for Git-Alias CLI.
- @details Executes `run_git_text` using deterministic CLI control-flow and explicit error propagation.
- @param args Input parameter consumed by `run_git_text`.
- @param cwd Input parameter consumed by `run_git_text`.
- @param check Input parameter consumed by `run_git_text`.
- @return Result emitted by `run_git_text` according to command contract.

### fn `def run_shell(command, cwd=None)` (L1476-1479)
- @brief Execute `run_shell` runtime logic for Git-Alias CLI.
- @details Executes `run_shell` using deterministic CLI control-flow and explicit error propagation.
- @param command Input parameter consumed by `run_shell`.
- @param cwd Input parameter consumed by `run_shell`.
- @return Result emitted by `run_shell` according to command contract.

### fn `def _git_status_lines()` `priv` (L1483-1495)
- @brief Execute `_git_status_lines` runtime logic for Git-Alias CLI.
- @details Executes `_git_status_lines` using deterministic CLI control-flow and explicit error propagation.
- @return Result emitted by `_git_status_lines` according to command contract.

### fn `def has_unstaged_changes(status_lines=None)` (L1500-1511)
- @brief Execute `has_unstaged_changes` runtime logic for Git-Alias CLI.
- @details Executes `has_unstaged_changes` using deterministic CLI control-flow and explicit error propagation.
- @param status_lines Input parameter consumed by `has_unstaged_changes`.
- @return Result emitted by `has_unstaged_changes` according to command contract.

### fn `def has_staged_changes(status_lines=None)` (L1516-1525)
- @brief Execute `has_staged_changes` runtime logic for Git-Alias CLI.
- @details Executes `has_staged_changes` using deterministic CLI control-flow and explicit error propagation.
- @param status_lines Input parameter consumed by `has_staged_changes`.
- @return Result emitted by `has_staged_changes` according to command contract.

- var `WIP_MESSAGE_RE = re.compile(r"^wip: work in progress\.$")` (L1531)
- @brief Constant `WIP_MESSAGE_RE` used by CLI runtime paths and policies.
### fn `def _refresh_remote_refs()` `priv` (L1546-1558)
- @brief Refresh remote-tracking references for the configured `origin` remote.
- @details Executes `git remote update origin` scoped to the single configured
remote instead of updating every configured remote (`git remote -v update`
updated all remotes and failed whenever any unrelated remote was
unreachable). Success is cached in `_REMOTE_REFS_UPDATED` so the fetch
runs at most once per CLI invocation; failure prints a non-fatal English
warning and leaves the cache unset so tolerant callers may retry.
- @return {bool} True when `origin` references were refreshed; False when the
update command failed (callers enforcing remote-state prerequisites
MUST treat False as fatal).
- @exception None; failures are reported via the boolean result and a stderr warning.
- @satisfies REQ-020

### fn `def _branch_remote_divergence(branch_key, remote="origin")` `priv` (L1564-1584)
- @brief Execute `_branch_remote_divergence` runtime logic for Git-Alias CLI.
- @details Executes `_branch_remote_divergence` using deterministic CLI control-flow and explicit error propagation.
- @param branch_key Input parameter consumed by `_branch_remote_divergence`.
- @param remote Input parameter consumed by `_branch_remote_divergence`.
- @return Result emitted by `_branch_remote_divergence` according to command contract.

### fn `def has_remote_branch_updates(branch_key, remote="origin")` (L1590-1594)
- @brief Execute `has_remote_branch_updates` runtime logic for Git-Alias CLI.
- @details Executes `has_remote_branch_updates` using deterministic CLI control-flow and explicit error propagation.
- @param branch_key Input parameter consumed by `has_remote_branch_updates`.
- @param remote Input parameter consumed by `has_remote_branch_updates`.
- @return Result emitted by `has_remote_branch_updates` according to command contract.

### fn `def has_remote_develop_updates()` (L1598-1601)
- @brief Execute `has_remote_develop_updates` runtime logic for Git-Alias CLI.
- @details Executes `has_remote_develop_updates` using deterministic CLI control-flow and explicit error propagation.
- @return Result emitted by `has_remote_develop_updates` according to command contract.

### fn `def has_remote_master_updates()` (L1605-1608)
- @brief Execute `has_remote_master_updates` runtime logic for Git-Alias CLI.
- @details Executes `has_remote_master_updates` using deterministic CLI control-flow and explicit error propagation.
- @return Result emitted by `has_remote_master_updates` according to command contract.

### fn `def _head_commit_message()` `priv` (L1612-1618)
- @brief Execute `_head_commit_message` runtime logic for Git-Alias CLI.
- @details Executes `_head_commit_message` using deterministic CLI control-flow and explicit error propagation.
- @return Result emitted by `_head_commit_message` according to command contract.

### fn `def _head_commit_hash()` `priv` (L1622-1628)
- @brief Execute `_head_commit_hash` runtime logic for Git-Alias CLI.
- @details Executes `_head_commit_hash` using deterministic CLI control-flow and explicit error propagation.
- @return Result emitted by `_head_commit_hash` according to command contract.

### fn `def _commit_exists_in_branch(commit_hash, branch_name)` `priv` (L1634-1646)
- @brief Execute `_commit_exists_in_branch` runtime logic for Git-Alias CLI.
- @details Executes `_commit_exists_in_branch` using deterministic CLI control-flow and explicit error propagation.
- @param commit_hash Input parameter consumed by `_commit_exists_in_branch`.
- @param branch_name Input parameter consumed by `_commit_exists_in_branch`.
- @return Result emitted by `_commit_exists_in_branch` according to command contract.

### fn `def _should_amend_existing_commit()` `priv` (L1650-1665)
- @brief Execute `_should_amend_existing_commit` runtime logic for Git-Alias CLI.
- @details Executes `_should_amend_existing_commit` using deterministic CLI control-flow and explicit error propagation.
- @return Result emitted by `_should_amend_existing_commit` according to command contract.

### fn `def is_inside_git_repo()` (L1669-1676)
- @brief Execute `is_inside_git_repo` runtime logic for Git-Alias CLI.
- @details Executes `is_inside_git_repo` using deterministic CLI control-flow and explicit error propagation.
- @return Result emitted by `is_inside_git_repo` according to command contract.

### class `class TagInfo` (L1681-1689)
- @brief Class `TagInfo` models a typed runtime container/error boundary.
- @brief Store raw tag name including `v` prefix when present.
- @brief Store ISO date string used for changelog section headers.
- @details Encapsulates tag identity, tag date, and resolved Git object identifier for changelog assembly.

### class `class WorktreeInfo` (L1694-1700)
- @brief Store normalized absolute worktree path.
- @brief Store associated local branch name or `None` for detached worktrees.

- var `DELIM = "\x1f"` (L1703)
- @brief Constant `DELIM` used by CLI runtime paths and policies.
- var `RECORD = "\x1e"` (L1706)
- @brief Constant `RECORD` used by CLI runtime paths and policies.
- var `SEMVER_RE = re.compile(r"^(\d+)\.(\d+)\.(\d+)$")` (L1722)
- @brief Constant `SEMVER_RE` used by CLI runtime paths and policies.
- var `SECTION_EMOJI = {` (L1725)
- @brief Constant `SECTION_EMOJI` used by CLI runtime paths and policies.
### fn `def _tag_semver_tuple(tag_name: str) -> Optional[Tuple[int, int, int]]` `priv` (L1743-1746)
- @brief Execute `_tag_semver_tuple` runtime logic for Git-Alias CLI.
- @details Executes `_tag_semver_tuple` using deterministic CLI control-flow and explicit error propagation.
- @param tag_name Input parameter consumed by `_tag_semver_tuple`.
- @return Result emitted by `_tag_semver_tuple` according to command contract.

### fn `def _latest_supported_tag_name(tags: List[TagInfo]) -> Optional[str]` `priv` (L1751-1754)
- @brief Execute `_latest_supported_tag_name` runtime logic for Git-Alias CLI.
- @details Executes `_latest_supported_tag_name` using deterministic CLI control-flow and explicit error propagation.
- @param tags Input parameter consumed by `_latest_supported_tag_name`.
- @return Result emitted by `_latest_supported_tag_name` according to command contract.

### fn `def _is_minor_release_tag(tag_name: str) -> bool` `priv` (L1762-1769)
- @brief Predicate: tag is a minor release.
- @details Returns `True` when `tag_name` is a semver tag where `patch==0` AND `(major>=1 OR minor>=1)`,
i.e. version `>=0.1.0` with no patch component.
Patch releases (`patch>0`) and pre-0.1.0 tags (`0.0.x`) return `False`.
- @param tag_name Semver tag string, optionally prefixed with `v` (e.g. `v0.1.0`, `0.2.0`).
- @return `True` iff tag represents a minor release; `False` otherwise.
- @satisfies REQ-018, REQ-040

### fn `def _latest_patch_tag_after(` `priv` (L1778-1779)
- @brief Locate the chronologically latest patch tag after a given minor release.
- @details Scans `all_tags` (sorted chronologically, ascending) for tags that are NOT minor releases
and appear after `last_minor` in the list. When `last_minor` is `None`, scans all tags.
Returns the last qualifying `TagInfo` (most recent), or `None` if no patch exists.
- @param all_tags Full list of `TagInfo` sorted by date ascending (from `list_tags_sorted_by_date`).
- @param last_minor The last minor-release `TagInfo` to anchor the search; `None` means no minor exists.
- @return Most recent `TagInfo` that is not a minor release and appears after `last_minor`, or `None`.
- @satisfies REQ-040

### fn `def list_tags_sorted_by_date(` (L1797-1798)
- @brief Execute `list_tags_sorted_by_date` runtime logic for Git-Alias CLI.
- @details Executes `list_tags_sorted_by_date` using deterministic CLI control-flow and explicit error propagation.
- @param repo_root Input parameter consumed by `list_tags_sorted_by_date`.
- @param merged_ref Input parameter consumed by `list_tags_sorted_by_date`.
- @return Result emitted by `list_tags_sorted_by_date` according to command contract.

### fn `def git_log_subjects(repo_root: Path, rev_range: str) -> List[str]` (L1828-1839)
- @brief Execute `git_log_subjects` runtime logic for Git-Alias CLI.
- @details Executes `git_log_subjects` using deterministic CLI control-flow and explicit error propagation.
Reads full commit messages (subject + body) to preserve multiline conventional descriptions.
- @param repo_root Input parameter consumed by `git_log_subjects`.
- @param rev_range Input parameter consumed by `git_log_subjects`.
- @return Result emitted by `git_log_subjects` according to command contract.

### fn `def parse_conventional_commit(` (L1845-1846)
- @brief Execute `parse_conventional_commit` runtime logic for Git-Alias CLI.
- @details Parses a conventional-commit header with optional scope and optional breaking marker (`!`),
then returns extracted type/scope/breaking/description fields for changelog rendering.
- @param message Raw commit message text (subject and optional body).
- @return Tuple `(type, scope, breaking, description)` when message is parseable; otherwise `None`.

### fn `def _format_changelog_description(desc: str) -> List[str]` `priv` (L1877-1900)
- @brief Normalize a commit description for readable changelog entry rendering.
- @details Removes `Co-authored-by:` trailer lines (REQ-044), drops empty lines (REQ-044),
and trims surrounding whitespace on every line. The first line is kept verbatim.
From the second line on, non-bullet lines are preserved verbatim (REQ-232); every
line starting with a markdown bullet marker (`-`, `*`, `+`, `1.`, `1)` plus
whitespace) has its marker stripped (REQ-234), and each maximal run of
consecutive bullet items is collapsed into one line whose item texts are
joined by `'; '` (REQ-235) so multiline commit text stays readable inside
the changelog top-level bullet.
- @param desc {str} Parsed commit description text (subject remainder plus body).
- @return {List[str]} Ordered non-empty rendered description lines; no continuation
line carries a leading markdown bullet marker.
- @note Complexity: O(L) where L is the number of description lines.
- @note A lone bullet marker without trailing whitespace does not match the marker
regex and is treated as non-bullet text.
- @see categorize_commit
- @satisfies REQ-044, REQ-232, REQ-234, REQ-235

### fn `def categorize_commit(subject: str) -> Tuple[Optional[str], str]` (L1918-1947)
- @brief Map a conventional commit message to a changelog section and formatted entry.
- @details Parses the conventional header and renders one top-level bullet:
`- <description> *(<scope>)*` when scope is present, `- <description>`
otherwise (REQ-078). Cleaned description lines after the first are
emitted as plain lines with no indentation transformation: non-bullet
lines stay verbatim (REQ-232) while markdown bullet-marker runs are
flattened into `'; '`-joined lines (REQ-234, REQ-235); entry blocks
never carry blank separator lines because `generate_section_for_range`
appends entries contiguously (REQ-233). When the breaking marker is
present, the first description line is prefixed with `BREAKING CHANGE: `.
- @param subject {str} Conventional commit message string (subject plus optional body).
- @return {Tuple[Optional[str], str]} `(section, line)`: `section` is the changelog
section name or `None` if type is unmapped or ignored; `line` is the
formatted entry string or `""` when section is `None`.
- @note Complexity: O(L) where L is the number of description lines.
- @see _format_changelog_description, generate_section_for_range
- @satisfies REQ-078, REQ-232, REQ-233, REQ-234, REQ-235

### fn `def _extract_release_version(subject: str) -> Optional[str]` `priv` (L1952-1962)
- @brief Execute `_extract_release_version` runtime logic for Git-Alias CLI.
- @details Executes `_extract_release_version` using deterministic CLI control-flow and explicit error propagation.
- @param subject Input parameter consumed by `_extract_release_version`.
- @return Result emitted by `_extract_release_version` according to command contract.

### fn `def _is_release_marker_commit(subject: str) -> bool` `priv` (L1967-1970)
- @brief Execute `_is_release_marker_commit` runtime logic for Git-Alias CLI.
- @details Executes `_is_release_marker_commit` using deterministic CLI control-flow and explicit error propagation.
- @param subject Input parameter consumed by `_is_release_marker_commit`.
- @return Result emitted by `_is_release_marker_commit` according to command contract.

### fn `def generate_section_for_range(` (L1979-1984)
- @brief Execute `generate_section_for_range` runtime logic for Git-Alias CLI.
- @details Executes `generate_section_for_range` using deterministic CLI control-flow and explicit error propagation.
- @param repo_root Input parameter consumed by `generate_section_for_range`.
- @param title Input parameter consumed by `generate_section_for_range`.
- @param date_s Input parameter consumed by `generate_section_for_range`.
- @param rev_range Input parameter consumed by `generate_section_for_range`.
- @param expected_version Input parameter consumed by `generate_section_for_range`.
- @return Result emitted by `generate_section_for_range` according to command contract.

### fn `def _get_remote_name_for_branch(branch_name: str, repo_root: Path) -> str` `priv` (L2032-2040)
- @brief Resolve the git remote name configured for a given branch.
- @details Queries `git config branch.<branch_name>.remote` via a local git command.
Returns `origin` as fallback when the config key is absent or the command fails.
No network operations are performed.
- @param branch_name Local branch name whose configured remote is requested (e.g. `"master"`).
- @param repo_root Absolute path used as CWD for the git config query.
- @return Remote name string; never empty (falls back to `"origin"`).
- @satisfies REQ-046

### fn `def _extract_owner_repo(remote_url: str) -> Optional[Tuple[str, str]]` `priv` (L2048-2072)
- @brief Resolve the normalized HTTPS base URL from the master branch's configured remote.
- @details Parses both SSH (`git@<host>:<owner>/<repo>[.git]`) and HTTPS
(`https://<host>/<owner>/<repo>[.git]`) formats, plus URI-style SSH forms
(`ssh://git@<host>/<owner>/<repo>[.git]`, `git+ssh://...`), and extracts
`<owner>` and `<repo>` through deterministic string parsing.
- @param remote_url Raw git remote URL string.
- @return Tuple `(owner, repo)` when parsing succeeds; otherwise `None`.

### fn `def _canonical_origin_base(repo_root: Path) -> Optional[str]` `priv` (L2082-2097)
- @brief Resolve normalized GitHub URL base from the master-branch configured remote.
- @details Determines remote name using `_get_remote_name_for_branch` with the configured
master branch, then executes local `git remote get-url <remote>` command.
If command execution fails or URL parsing fails, returns `None`.
On success, always emits `https://github.com/<owner>/<repo>` for changelog templates.
No network operation is performed; all data is derived from local git metadata.
- @param repo_root Absolute path to the repository root used as CWD for all git commands.
- @return Normalized HTTPS base URL string (no trailing `.git`), or `None` on failure.
- @satisfies REQ-043, REQ-046

### fn `def get_origin_compare_url(` (L2104-2105)
- @brief Execute `get_origin_compare_url` runtime logic for Git-Alias CLI.
- @details Executes `get_origin_compare_url` using deterministic CLI control-flow and explicit error propagation.
- @param base_url Input parameter consumed by `get_origin_compare_url`.
- @param prev_tag Input parameter consumed by `get_origin_compare_url`.
- @param tag Input parameter consumed by `get_origin_compare_url`.
- @return Result emitted by `get_origin_compare_url` according to command contract.

### fn `def get_release_page_url(base_url: Optional[str], tag: str) -> Optional[str]` (L2119-2124)
- @brief Execute `get_release_page_url` runtime logic for Git-Alias CLI.
- @details Executes `get_release_page_url` using deterministic CLI control-flow and explicit error propagation.
- @param base_url Input parameter consumed by `get_release_page_url`.
- @param tag Input parameter consumed by `get_release_page_url`.
- @return Result emitted by `get_release_page_url` according to command contract.

### fn `def build_history_section(` (L2132-2136)
- @brief Execute `build_history_section` runtime logic for Git-Alias CLI.
- @details Executes `build_history_section` using deterministic CLI control-flow and explicit error propagation.
- @param repo_root Input parameter consumed by `build_history_section`.
- @param tags Input parameter consumed by `build_history_section`.
- @param include_unreleased Input parameter consumed by `build_history_section`.
- @param include_unreleased_link Input parameter consumed by `build_history_section`.
- @return Result emitted by `build_history_section` according to command contract.

### fn `def generate_changelog_document(` (L2186-2187)
- @brief Generate the full CHANGELOG.md document from repository tags and commits.
- @brief Execute `generate_changelog_document` runtime logic for Git-Alias CLI.
- @details Groups commits by minor release (semver where `patch=0` AND version `>=0.1.0`).
By default only minor releases appear; the document body is empty when none exist.
With `include_patch=True`, prepends the latest patch release after the last minor
(or the latest patch overall when no minor exists) including all commits in that range.
Releases are ordered reverse-chronologically in the output.
`# History` contains only the version tags present in the changelog body:
minor tags when `include_patch=False`; minor tags plus the latest patch when
`include_patch=True`. Diff links in `# History` use the same ranges as the
corresponding changelog sections. History generation can be disabled by flag.
- @details Executes `generate_changelog_document` using deterministic CLI control-flow and explicit error propagation.
- @param repo_root Absolute path to the repository root used as CWD for all git commands.
- @param include_patch When `True`, prepend the latest patch release section to the document.
- @param disable_history When `True`, omit `# History` section from output.
- @param repo_root Input parameter consumed by `generate_changelog_document`.
- @param include_patch Input parameter consumed by `generate_changelog_document`.
- @param disable_history Input parameter consumed by `generate_changelog_document`.
- @return Complete `CHANGELOG.md` string content, terminated with a newline.
- @return Result emitted by `generate_changelog_document` according to command contract.
- @satisfies REQ-018, REQ-040, REQ-041, REQ-043, REQ-068, REQ-069, REQ-070

### class `class VersionRuleContext` `@dataclass(frozen=True)` (L2259-2266)

### fn `def _normalize_version_rule_pattern(pattern: str) -> str` `priv` (L2274-2285)
- @brief Normalize a `ver_rules` pattern to the internal pathspec matching form.
- @details Strips surrounding blanks, strips a leading `./`, and anchors patterns containing `/`
to repository root by prefixing `/` when missing. Backslash sequences are preserved
verbatim so pathspec gitignore-style matching applies gitignore(5) escape semantics.
- @param pattern {str} Input pattern string from configuration.
- @return {str} Normalized pathspec-compatible pattern string; empty string when input is blank.
- @satisfies REQ-160, REQ-164

### fn `def _split_negation_pattern(pattern: str) -> Tuple[bool, str]` `priv` (L2292-2298)
- @brief Split a `ver_rules` pattern into its negation flag and matching base pattern.
- @details Detects the gitignore(5)-style negation prefix `!` in the raw pattern text and
returns the remainder used for exclusion matching.
- @param pattern {str} Raw pattern string from configuration.
- @return {Tuple[bool, str]} `(True, remainder)` when the pattern starts with `!`; `(False, pattern)` otherwise.
- @satisfies REQ-161

### fn `def _version_pathspec_matches(spec, normalized_pattern: str, relative: str) -> bool` `priv` (L2306-2316)
- @brief Evaluate pathspec membership for one repository-relative path.
- @details Applies the spec match and retries with a leading `/` for root-anchored patterns,
mirroring the anchored-pattern matching contract of the inventory walker.
- @param spec {pathspec.PathSpec} Compiled pathspec used for matching.
- @param normalized_pattern {str} Normalized pattern that produced `spec`.
- @param relative {str} Repository-relative POSIX path under evaluation.
- @return {bool} True when the path matches the spec.

### fn `def _build_version_negation_specs(rules) -> List` `priv` (L2325-2339)
- @brief Compile exclusion pathspecs from negation `ver_rules` patterns.
- @details Collects every rule pattern starting with `!`, strips the prefix, normalizes the
remainder with the shared normalization contract, and compiles each base pattern
as a positive gitignore-style spec via the supported pathspec `gitignore`
registered style (the legacy `gitwildmatch` name is deprecated by pathspec).
- @param rules {List[Tuple[str, Optional[str]]]} Parsed `(pattern, regex)` rule pairs.
- @return {List[pathspec.PathSpec]} Compiled exclusion pathspecs; empty when no negation pattern is configured.
- @satisfies REQ-161

### fn `def _version_path_is_negated(relative: str, negation_specs) -> bool` `priv` (L2347-2353)
- @brief Report whether a repository-relative path is excluded by a negation pattern.
- @details Evaluates each compiled negation spec directly and with a leading `/` prefix so
root-anchored exclusion bases match repository-relative paths.
- @param relative {str} Repository-relative POSIX path under evaluation.
- @param negation_specs {List[pathspec.PathSpec]} Compiled exclusion pathspecs.
- @return {bool} True when any negation spec matches the path.
- @satisfies REQ-161, REQ-163

### fn `def _build_version_file_inventory(root: Path) -> List[Tuple[Path, str]]` `priv` (L2359-2386)
- @brief Build a deduplicated repository file inventory for version rule evaluation.
- @details Executes a single `git ls-files` query from repository root, filters to existing files only,
applies hardcoded exclusion regexes, normalizes relative paths, and deduplicates by resolved path.
- @param root Repository root path used as traversal anchor.
- @return List of tuples `(absolute_path, normalized_relative_path)` used by downstream matchers.

### fn `def _collect_version_files(root, pattern, *, inventory=None, negation_specs=())` `priv` (L2397-2415)
- @brief Collect repository files matched by one `ver_rules` pattern.
- @details Normalizes the pattern, applies pathspec gitignore-style matching over the tracked-file
inventory, and drops candidates excluded by any compiled negation spec. Uses the
precomputed inventory when provided to avoid repeated repository traversals.
- @param root {Path} Repository root path used as traversal anchor.
- @param pattern {str} Inclusion pattern string from configuration (never starting with `!`).
- @param inventory {Optional[List[Tuple[Path, str]]]} Precomputed `(path, normalized_relative_path)` list.
- @param negation_specs {List[pathspec.PathSpec]} Compiled exclusion pathspecs applied before matching.
- @return {List[Path]} Matched, non-excluded file paths in inventory order.
- @satisfies REQ-161, REQ-163, REQ-164

### fn `def _is_version_path_excluded(relative_path: str) -> bool` `priv` (L2420-2423)
- @brief Execute `_is_version_path_excluded` runtime logic for Git-Alias CLI.
- @details Executes `_is_version_path_excluded` using deterministic CLI control-flow and explicit error propagation.
- @param relative_path Input parameter consumed by `_is_version_path_excluded`.
- @return Result emitted by `_is_version_path_excluded` according to command contract.

### fn `def _iter_versions_in_text(text, compiled_regexes)` `priv` (L2429-2440)
- @brief Execute `_iter_versions_in_text` runtime logic for Git-Alias CLI.
- @details Executes `_iter_versions_in_text` using deterministic CLI control-flow and explicit error propagation.
- @param text Input parameter consumed by `_iter_versions_in_text`.
- @param compiled_regexes Input parameter consumed by `_iter_versions_in_text`.
- @return Result emitted by `_iter_versions_in_text` according to command contract.

### fn `def _read_version_file_text(` `priv` (L2447-2448)
- @brief Read and cache UTF-8 text content for a version-managed file.
- @details Loads file content with UTF-8 decoding; falls back to `errors="ignore"` on decode failures.
Emits deterministic stderr diagnostics on I/O failure and returns `None` for caller-managed skip logic.
- @param file_path Absolute path of the file to read.
- @param text_cache Optional mutable cache keyed by `Path` to avoid duplicate reads across phases.
- @return File text payload or `None` when file cannot be read.

### fn `def _prepare_version_rule_contexts(` `priv` (L2475-2476)
- @brief Build reusable per-rule contexts for canonical version evaluation workflows.
- @details Compiles exclusion pathspecs from negation rules, skips negation rules from context
generation, and resolves matched files plus compiled regex for each inclusion rule.
Preserves error contracts for unmatched patterns and invalid regex declarations.
- @param root {Path} Repository root path used for relative-path rendering.
- @param rules {List[Tuple[str, Optional[str]]]} Sequence of `(pattern, regex)` tuples; negation
patterns (`!` prefix) contribute exclusions and never produce contexts.
- @param inventory {Optional[List[Tuple[Path, str]]]} Precomputed inventory to avoid repeated filesystem traversal.
- @return {List[VersionRuleContext]} Ordered list of `VersionRuleContext` objects aligned to inclusion rule order.
- @throws VersionDetectionError when a rule matches no files or contains an invalid regex.
- @satisfies REQ-161, REQ-162, REQ-163

### fn `def _determine_canonical_version(` `priv` (L2527-2534)
- @brief Execute `_determine_canonical_version` runtime logic for Git-Alias CLI.
- @details Executes `_determine_canonical_version` using deterministic CLI control-flow and explicit error propagation.
- @param root Input parameter consumed by `_determine_canonical_version`.
- @param rules Input parameter consumed by `_determine_canonical_version`.
- @param verbose Input parameter consumed by `_determine_canonical_version`.
- @param debug Input parameter consumed by `_determine_canonical_version`.
- @param contexts Optional precomputed `VersionRuleContext` list for reuse across phases.
- @param text_cache Optional mutable cache keyed by file path to avoid duplicate reads.
- @return Result emitted by `_determine_canonical_version` according to command contract.

### fn `def _parse_semver_tuple(text: str) -> Optional[Tuple[int, int, int]]` `priv` (L2587-2593)
- @brief Execute `_parse_semver_tuple` runtime logic for Git-Alias CLI.
- @details Executes `_parse_semver_tuple` using deterministic CLI control-flow and explicit error propagation.
- @param text Input parameter consumed by `_parse_semver_tuple`.
- @return Result emitted by `_parse_semver_tuple` according to command contract.

### fn `def _replace_versions_in_text(text, compiled_regex, replacement)` `priv` (L2600-2615)
- @brief Execute `_replace_versions_in_text` runtime logic for Git-Alias CLI.
- @details Executes `_replace_versions_in_text` using deterministic CLI control-flow and explicit error propagation.
- @param text Input parameter consumed by `_replace_versions_in_text`.
- @param compiled_regex Input parameter consumed by `_replace_versions_in_text`.
- @param replacement Input parameter consumed by `_replace_versions_in_text`.
- @return Result emitted by `_replace_versions_in_text` according to command contract.

### fn `def _current_branch_name()` `priv` (L2619-2631)
- @brief Execute `_current_branch_name` runtime logic for Git-Alias CLI.
- @details Executes `_current_branch_name` using deterministic CLI control-flow and explicit error propagation.
- @return Result emitted by `_current_branch_name` according to command contract.

### fn `def _ref_exists(ref_name)` `priv` (L2636-2645)
- @brief Execute `_ref_exists` runtime logic for Git-Alias CLI.
- @details Executes `_ref_exists` using deterministic CLI control-flow and explicit error propagation.
- @param ref_name Input parameter consumed by `_ref_exists`.
- @return Result emitted by `_ref_exists` according to command contract.

### fn `def _local_branch_exists(branch_name)` `priv` (L2650-2653)
- @brief Execute `_local_branch_exists` runtime logic for Git-Alias CLI.
- @details Executes `_local_branch_exists` using deterministic CLI control-flow and explicit error propagation.
- @param branch_name Input parameter consumed by `_local_branch_exists`.
- @return Result emitted by `_local_branch_exists` according to command contract.

### fn `def _remote_branch_exists(branch_name)` `priv` (L2658-2661)
- @brief Execute `_remote_branch_exists` runtime logic for Git-Alias CLI.
- @details Executes `_remote_branch_exists` using deterministic CLI control-flow and explicit error propagation.
- @param branch_name Input parameter consumed by `_remote_branch_exists`.
- @return Result emitted by `_remote_branch_exists` according to command contract.

### fn `def _list_worktree_associations() -> List[WorktreeInfo]` `priv` (L2669-2694)
- @brief Parse worktree porcelain output into deterministic association records.
- @details Executes `git worktree list --porcelain`, extracts `worktree <path>` and optional
`branch refs/heads/<name>` fields, normalizes paths via `Path.resolve()`, and preserves
entry order for deterministic downstream matching and diagnostics.
- @return `List[WorktreeInfo]` parsed from repository worktree metadata.
- @exception RuntimeError Propagates git query failures from `run_git_text`.
- @satisfies REQ-139

### fn `def _find_worktree_for_branch(` `priv` (L2702-2703)
- @brief Resolve the association record bound to a local branch name.
- @details Scans parsed worktree metadata and returns the first worktree whose `branch_name`
equals the requested local branch.
- @param branch_name `str` — local branch name to resolve.
- @param associations `List[WorktreeInfo]` — parsed worktree metadata snapshot.
- @return `Optional[WorktreeInfo]` matching association or `None`.
- @satisfies REQ-139

### fn `def _find_association_for_worktree(` `priv` (L2718-2719)
- @brief Resolve the association record bound to a target worktree path.
- @details Normalizes the user-provided path via `Path.resolve()` and returns the matching parsed
worktree record when present.
- @param worktree_arg `str` — CLI worktree operand.
- @param associations `List[WorktreeInfo]` — parsed worktree metadata snapshot.
- @return `Optional[WorktreeInfo]` matching association or `None`.
- @satisfies REQ-139

### fn `def _parse_bd_target(args: List[str]) -> Tuple[str, bool]` `priv` (L2735-2749)
- @brief Validate branch-delete CLI operands and optional force mode.
- @details Accepts exactly one branch operand with an optional leading `--force`, rejects all other
flags and extra operands, and emits deterministic English diagnostics on invalid input.
- @param args `List[str]` — CLI operands after `bd`.
- @return `Tuple[str, bool]` normalized branch target and force-mode flag.
- @exception SystemExit Exit code 1 on invalid operands.
- @satisfies REQ-019

### fn `def _parse_wtd_target(args: List[str]) -> Tuple[str, bool]` `priv` (L2757-2771)
- @brief Validate worktree-delete CLI operands and optional force mode.
- @details Accepts exactly one worktree operand with an optional leading `--force`, rejects all
other flags and extra operands, and emits deterministic English diagnostics on invalid input.
- @param args `List[str]` — CLI operands after `wtd`.
- @return `Tuple[str, bool]` normalized worktree target operand and force-mode flag.
- @exception SystemExit Exit code 1 on invalid operands.
- @satisfies REQ-077

### fn `def _preflight_branch_delete(branch_name: str, alias: str) -> None` `priv` (L2781-2812)
- @brief Preflight branch deletion without mutating repository state.
- @details Resolves the branch tip commit, verifies that an upstream branch exists and contains the
tip or that the tip is reachable from `HEAD`, and converts any git failure into deterministic
English diagnostics suitable for the all-or-nothing coordinated deletion flow.
- @param branch_name `str` — local branch target.
- @param alias `str` — user-facing alias token used in diagnostics.
- @return `None` when branch deletion is safe without force.
- @exception SystemExit Exit code 1 when the branch cannot be deleted without force.
- @satisfies REQ-138, REQ-140

### fn `def _preflight_worktree_delete(worktree_path: Path, alias: str) -> None` `priv` (L2822-2850)
- @brief Preflight worktree removal without mutating repository state.
- @details Rejects deletion of the main repository worktree, ensures the target path is a registered
linked worktree, and verifies that `git status --porcelain` executed inside the worktree
is empty so `git worktree remove` can proceed without force.
- @param worktree_path `Path` — normalized absolute worktree target.
- @param alias `str` — user-facing alias token used in diagnostics.
- @return `None` when worktree removal is safe without force.
- @exception SystemExit Exit code 1 when the worktree cannot be deleted without force.
- @satisfies REQ-140, REQ-143

### fn `def _print_paired_delete_success(worktree_path: Path, branch_name: str) -> None` `priv` (L2858-2862)
- @brief Print paired branch/worktree deletion evidence.
- @details Emits deterministic English stdout lines identifying both deleted resources after the
coordinated deletion path completes successfully.
- @param worktree_path `Path` — deleted worktree path.
- @param branch_name `str` — deleted local branch name.
- @return `None`; side-effect: stdout output.
- @satisfies REQ-142

### fn `def _delete_associated_branch_and_worktree(` `priv` (L2873-2874)
- @brief Execute coordinated deletion for an associated worktree/branch pair.
- @details When `force_delete` is disabled, preflights both deletion operations before mutating
repository state. Always removes the worktree first and the branch second because the
branch cannot be deleted while an associated worktree still exists.
- @param worktree_info `WorktreeInfo` — resolved association record with branch binding.
- @param alias `str` — user-facing alias token used in diagnostics.
- @param force_delete `bool` — when `True`, bypass non-force preflight checks and execute forced git deletion flags.
- @return `None`; side-effects: git delete commands and stdout evidence.
- @exception RuntimeError Raised when the association lacks a branch binding.
- @satisfies REQ-140, REQ-141, REQ-142, REQ-145

### fn `def _ensure_release_prerequisites()` `priv` (L2903-2956)
- @brief Enforce release preflight prerequisites with fail-closed remote verification.
- @details Validates configured local branches, then requires a successful
`origin` remote-reference refresh before evaluating any remote state;
when `_refresh_remote_refs()` reports failure the preflight raises
immediately so no local release mutation can proceed against
unverifiable remote data. Subsequent checks enforce remote-branch
existence, remote update status for master and develop, current branch
equal to configured work, and a clean working tree and index.
- @return {Dict[str, str]} Branch map with keys `master`, `develop`, `work`.
- @throws ReleaseError Missing local/remote branches, failed remote refresh,
pending remote updates, non-work checkout, or dirty state.
- @satisfies REQ-026, REQ-047

### fn `def _bump_semver_version(current_version, level)` `priv` (L2962-2982)
- @brief Execute `_bump_semver_version` runtime logic for Git-Alias CLI.
- @details Executes `_bump_semver_version` using deterministic CLI control-flow and explicit error propagation.
- @param current_version Input parameter consumed by `_bump_semver_version`.
- @param level Input parameter consumed by `_bump_semver_version`.
- @return Result emitted by `_bump_semver_version` according to command contract.

### fn `def _run_release_step(level, step_name, action)` `priv` (L2989-3015)
- @brief Execute `_run_release_step` runtime logic for Git-Alias CLI.
- @details Executes `_run_release_step` using deterministic CLI control-flow and explicit error propagation.
- @param level Input parameter consumed by `_run_release_step`.
- @param step_name Input parameter consumed by `_run_release_step`.
- @param action Input parameter consumed by `_run_release_step`.
- @return Result emitted by `_run_release_step` according to command contract.

### fn `def _create_release_commit_for_flow(target_version)` `priv` (L3020-3025)
- @brief Execute `_create_release_commit_for_flow` runtime logic for Git-Alias CLI.
- @details Executes release-flow first-commit creation with WIP amend semantics reused from `_execute_commit`.
- @param target_version Input parameter consumed by `_create_release_commit_for_flow`.
- @return Result emitted by `_create_release_commit_for_flow` according to command contract.

### fn `def _push_release_refs(level, version, branch, include_branch=True, include_tag=False,` `priv` (L3045-3074)
- @brief Publish selected release references once with recovery diagnostics.
- @brief Exact reference names for publication and diagnostics.
- @details O(1) refspec construction; one Git push; no automatic retries. The push
executes through the shared inherited-stdio git wrapper (`run_git_cmd`) so
push output and transport errors reach the user terminal and interactive
SSH/credential authentication remains possible (restores the pre-8e4abd26
publication transport; piped stdio caused `Permission denied (publickey)`
rejections in sessions whose interactive fetch succeeded). Tag publication
requires atomic support; --no-follow-tags excludes unrelated tags. Failure
preserves local objects and reports Git's rejection live on stderr.
- @param level {str} Release command: major, minor, or patch.
- @param version {str} Prepared semantic version.
- @param branch {str} Configured destination branch name.
- @param include_branch {bool} Publish branch when True.
- @param include_tag {bool} Publish exact release tag atomically when True.
- @param dev_release {bool} Develop-scoped release (REQ-045, REQ-200); selects the
`g <level> --dev --resume` recovery command and develop-only tips.
- @return {None} No operation when both selectors are False.
- @throws ReleaseError Push failed; includes rejection and recovery references.
- @satisfies REQ-045, REQ-072, REQ-179, REQ-180, REQ-181, REQ-200

### fn `def _resume_release_flow(level, dev_release=False)` `priv` (L3089-3165)
- @brief Validate and resume publication of an immutable prepared local release.
- @brief Configured branch map; develop-scoped releases exclude master.
- @details O(1) Git queries excluding ancestry traversal. Require clean checkout,
matching work/integration tips, release subject/version, and annotated tag identity.
Query the single origin push URL before any push; reject missing remote branches,
conflicting tags, and non-ancestor remote tips. Publish missing refs only, then
checkout work. Preserve version files, commits, tags, and external build outputs.
- @param level {str} Release command: major, minor, or patch.
- @param dev_release {bool} Develop-scoped release (REQ-045, REQ-200); excludes
master from integration and publication validation.
- @return {None} Completes missing publication and restores work checkout.
- @throws ReleaseError Invalid release state or publication rejection.
- @throws RuntimeError Git inspection failed.
- @throws VersionDetectionError Version-managed files disagree.
- @satisfies REQ-045, REQ-176, REQ-177, REQ-178, REQ-179, REQ-200

### fn `def _execute_release_flow(level, changelog_args=None, exec_args=None, dev_release=False)` `priv` (L3190-3289)
- @brief Execute `_execute_release_flow` runtime logic for Git-Alias CLI.
- @details Orchestrates the full release pipeline for `major`, `minor`, and `patch` levels.
Branch integration is scope-dependent (REQ-045, REQ-072, REQ-200):
- `dev_release=True`: merges `work` into `develop` and pushes `develop`
with the exact release tag atomically; skips `master` entirely.
- default: integrates work/develop/master and prepares the tag,
pushes develop alone, then atomically publishes master and the exact tag.
Changelog flags always include `--force-write`; `patch` auto-adds `--include-patch`.
When `exec_args` is non-empty, an additional `run external command` step executes
the argv list between `update versions` and `stage files` so build artifacts are
staged by `git add --all` and included in the first release commit.
The temporary changelog tag is deleted before integration. The definitive
tag is prepared before any push; final publication is atomic and tag-scoped.
Complexity: O(F + C) version-file and changelog traversal plus Git operations.
- @param level {str} Release level string: `"major"`, `"minor"`, or `"patch"`.
- @param changelog_args {List[str] | None} Optional extra changelog flags forwarded alongside `--force-write`.
- @param exec_args {List[str] | None} Optional external command argv executed without shell
with repository root as CWD and inherited stdio (REQ-166, REQ-167); a non-zero
exit is converted by `_run_release_step` into a `ReleaseError` that aborts the
release before staging, commit, tag, or push (REQ-168).
- @param dev_release {bool} Develop-scoped release (REQ-045, REQ-200); integrates and
publishes configured `develop` only, leaving `master` unchanged.
- @return None; raises `ReleaseError` or `VersionDetectionError` on failure.
- @satisfies REQ-026, REQ-045, REQ-072, REQ-166, REQ-167, REQ-168, REQ-200

### fn `def _execute_backup_flow()` `priv` (L3297-3314)
- @brief Execute `_execute_backup_flow` runtime logic for Git-Alias CLI.
- @details Executes the `backup` workflow by reusing the release preflight checks, then
fast-forward merges configured `work` into configured `develop`, pushes `develop`
to its configured remote tracking branch, checks out back to `work`, and prints
an explicit success confirmation.
- @return None; raises `ReleaseError` on preflight or workflow failure.
- @satisfies REQ-047, REQ-048, REQ-049

### fn `def _run_release_command(level, changelog_args=None, exec_args=None, dev_release=False)` `priv` (L3329-3353)
- @brief Execute one release workflow command with unified error propagation to CLI exit codes.
- @details Routes standalone --resume to immutable publication recovery; otherwise
delegates to `_execute_release_flow`. O(1) dispatch; converts `ReleaseError`,
`VersionDetectionError`, and `CommandExecutionError` into English stderr
diagnostics plus non-zero exit status.
- @param level {str} Release level string: `"major"`, `"minor"`, or `"patch"`.
- @param changelog_args {List[str] | None} Optional extra changelog flags forwarded alongside `--force-write`.
- @param exec_args {List[str] | None} Optional external command argv forwarded to
`_execute_release_flow` for the injected exec step (REQ-166, REQ-167).
- @param dev_release {bool} Develop-scoped release (REQ-045, REQ-200); forwarded to both
`_resume_release_flow` and `_execute_release_flow`.
- @return None; side-effects: release workflow execution and stderr diagnostics on failure.
- @exception SystemExit Exit code 1 (or the failing command return code) on workflow failure.
- @satisfies REQ-026, REQ-045, REQ-166, REQ-168, REQ-176, REQ-200

### fn `def _run_backup_command()` `priv` (L3358-3365)
- @brief Execute `_run_backup_command` runtime logic for Git-Alias CLI.
- @details Runs the `backup` workflow with the same error propagation strategy used by release commands.
- @return None; exits with status 1 on `ReleaseError`.
- @satisfies REQ-047, REQ-048, REQ-049

### fn `def _run_reset_with_help(base_args, extra)` `priv` (L3371-3378)
- @brief Execute `_run_reset_with_help` runtime logic for Git-Alias CLI.
- @details Executes `_run_reset_with_help` using deterministic CLI control-flow and explicit error propagation.
- @param base_args Input parameter consumed by `_run_reset_with_help`.
- @param extra Input parameter consumed by `_run_reset_with_help`.
- @return Result emitted by `_run_reset_with_help` according to command contract.

### fn `def _reject_extra_arguments(extra, alias)` `priv` (L3384-3390)
- @brief Execute `_reject_extra_arguments` runtime logic for Git-Alias CLI.
- @details Executes `_reject_extra_arguments` using deterministic CLI control-flow and explicit error propagation.
- @param extra Input parameter consumed by `_reject_extra_arguments`.
- @param alias Input parameter consumed by `_reject_extra_arguments`.
- @return Result emitted by `_reject_extra_arguments` according to command contract.

### fn `def _parse_release_flags(extra, alias)` `priv` (L3412-3464)
- @brief Parse release flags, develop scope, standalone resume, or an exec command tail.
- @details Applies rest-of-argv semantics: operand scanning stops at the first `--exec` token
and every following operand is returned verbatim as the external command argv
(command plus parameters) without flag validation. A `--resume` token before
`--exec` selects recovery mode and MUST NOT combine with any flag other than
`--dev`/`--develop` (REQ-176). Operands before `--exec` are validated against the
whitelist `{"--include-patch", "--dev", "--develop"}` and deduplicated preserving
first-occurrence order. Equivalent flags `--dev` and `--develop` (REQ-200) select
the develop-scoped workflow (REQ-045) and are never forwarded to the `changelog`
step. The `--exec` tail is never merged into `changelog_args` (REQ-166).
- @param extra {List[str] | None} Raw CLI operands following the release alias token.
- @param alias {str} Release alias name used in English diagnostics (`major`, `minor`, `patch`).
- @return {Tuple[List[str], List[str], bool]} `(changelog_args, exec_args, dev_release)`;
`exec_args` is empty when `--exec` is absent; `dev_release` is True when
`--dev`/`--develop` was supplied before `--exec`.
- @exception SystemExit Exit code 1 on unknown flags before `--exec`, on a parameterless
`--exec`, or on an invalid `--resume` combination.
- @note Standalone --resume, optionally combined with --dev/--develop, returns
(["--resume"], [], True/False); any other resume combination fails.
- @note Complexity: O(N) argv traversal; --exec tail remains opaque.
- @satisfies REQ-166, REQ-168, REQ-176, REQ-200

### fn `def _prepare_commit_message(extra, alias)` `priv` (L3470-3480)
- @brief Execute `_prepare_commit_message` runtime logic for Git-Alias CLI.
- @details Executes `_prepare_commit_message` using deterministic CLI control-flow and explicit error propagation.
- @param extra Input parameter consumed by `_prepare_commit_message`.
- @param alias Input parameter consumed by `_prepare_commit_message`.
- @return Result emitted by `_prepare_commit_message` according to command contract.

### fn `def _normalize_conventional_description(description: str) -> str` `priv` (L3487-3497)
- @brief Normalize conventional commit description formatting.
- @details Applies canonical description normalization for conventional aliases:
uppercases the first character unless it is numeric and appends a trailing
period when missing.
- @param description Input parameter consumed by `_normalize_conventional_description`.
- @return Result emitted by `_normalize_conventional_description` according to command contract.

### fn `def _build_conventional_message(kind: str, extra, alias: str) -> str` `priv` (L3506-3527)
- @brief Execute `_build_conventional_message` runtime logic for Git-Alias CLI.
- @details Executes `_build_conventional_message` using deterministic CLI control-flow and explicit error propagation.
The output format is `<type>: <description>` when the effective module is empty,
otherwise `<type>(<module>): <description>`.
- @param kind Input parameter consumed by `_build_conventional_message`.
- @param extra Input parameter consumed by `_build_conventional_message`.
- @param alias Input parameter consumed by `_build_conventional_message`.
- @return Result emitted by `_build_conventional_message` according to command contract.

### fn `def _run_conventional_commit(kind: str, alias: str, extra)` `priv` (L3545-3550)
- @brief Execute `_run_conventional_commit` runtime logic for Git-Alias CLI.
- @brief Execute `_run_conventional_commit` runtime logic for Git-Alias CLI.
- @details Builds the conventional commit message via `_build_conventional_message`, then validates
commitability via `_ensure_commit_ready_with_stage` (auto-stages working-tree changes when
staging is empty), then delegates to `_execute_commit` with WIP-amend semantics.
- @details Executes `_run_conventional_commit` using deterministic CLI control-flow and explicit error propagation.
- @param kind `str` — commit type token (e.g., `"fix"`, `"new"`, `"refactor"`).
- @param alias `str` — alias name used in error messages and dispatch.
- @param extra `list | None` — raw CLI extra arguments forwarded to `_build_conventional_message`.
- @param kind Input parameter consumed by `_run_conventional_commit`.
- @param alias Input parameter consumed by `_run_conventional_commit`.
- @param extra Input parameter consumed by `_run_conventional_commit`.
- @return Return value of `_execute_commit`.
- @return Result emitted by `_run_conventional_commit` according to command contract.
- @exception SystemExit Exit code 1 on message validation failure or no-data failure.
- @see _build_conventional_message, _ensure_commit_ready_with_stage, _execute_commit, cmd_aa
- @satisfies REQ-022, DES-007

### fn `def _execute_commit(message, alias, allow_amend=True)` `priv` (L3557-3589)
- @brief Execute `_execute_commit` runtime logic for Git-Alias CLI.
- @details Executes `_execute_commit` using deterministic CLI control-flow and explicit error propagation.
- @param message Input parameter consumed by `_execute_commit`.
- @param alias Input parameter consumed by `_execute_commit`.
- @param allow_amend Input parameter consumed by `_execute_commit`.
- @return Result emitted by `_execute_commit` according to command contract.

### fn `def _ensure_clean_worktree_and_index(alias: str) -> bool` `priv` (L3597-3613)
- @brief Validate clean working tree and empty staging before rollback operations.
- @details Evaluates porcelain status and rejects command execution when unstaged,
untracked, or staged entries are present in repository state.
- @param alias `str` — alias name used in user-facing diagnostics.
- @return `True` when both working tree and index are clean.
- @exception SystemExit Exit code 1 when repository is not fully clean.
- @satisfies REQ-133

### fn `def _resolve_rollback_target_commit(target: str) -> str` `priv` (L3621-3631)
- @brief Resolve rollback target to an existing commit object.
- @details Runs `git rev-parse --verify <target>^{commit}` to support both commit
hashes and tag names while normalizing to a full commit hash.
- @param target `str` — user-provided rollback target token.
- @return `str` normalized full commit hash.
- @exception SystemExit Exit code 1 when target does not resolve to a commit.
- @satisfies REQ-134

### fn `def _is_commit_ancestor(ancestor_commit: str, descendant_ref: str) -> bool` `priv` (L3638-3647)
- @brief Evaluate commit reachability relation via merge-base ancestry check.
- @details Executes `git merge-base --is-ancestor <ancestor> <descendant>` and
returns boolean reachability without raising on non-zero status.
- @param ancestor_commit `str` — commit expected to be ancestor.
- @param descendant_ref `str` — descendant git reference.
- @return `True` when `ancestor_commit` is reachable from `descendant_ref`.

### fn `def _is_commit_hash_token(token: str) -> bool` `priv` (L3652-3655)
- @brief Validate whether a token matches git hexadecimal commit-hash syntax.
- @details Accepts abbreviated/full hexadecimal hashes with length 4..40.
- @param token `str` — CLI token to validate.
- @return `True` when token is a hexadecimal commit-hash candidate.

### fn `def _tag_exists(tag_name: str) -> bool` `priv` (L3660-3663)
- @brief Check whether a tag exists in local repository references.
- @details Verifies `refs/tags/<tag_name>` presence using internal ref lookup.
- @param tag_name `str` — tag name token.
- @return `True` when local tag reference exists.

### fn `def _abort_rollback_version_restore(failure)` `priv` (L3675-3695)
- @brief Abort a rollback after a failed version restore and restore pre-rollback state.
- @details Executes `git revert --abort` to discard already applied inverse revert
changes, prints an explicit English diagnostic prefixed with
`Unable to run git rollback: the version restore failed`, and terminates
with exit code 1 before the revert commit is created. Prefers
`CommandExecutionError` stderr payload as diagnostic detail when present.
- @param failure `BaseException` — `SystemExit` or `RuntimeError` raised by the
version restore pipeline (`cmd_chver` or the staging step).
- @return None; side-effects: `git revert --abort` subprocess and stderr output.
- @exception SystemExit Always exits with status 1.
- @satisfies REQ-174

### fn `def _is_linux_platform() -> bool` `priv` (L3700-3703)
- @brief Determine whether local self-management commands are supported on current host.
- @details Evaluates the current Python platform token and accepts only Linux hosts.
- @return `True` when runtime platform is Linux; otherwise `False`.
- @satisfies REQ-001 REQ-002 REQ-129 REQ-130

### fn `def _print_non_linux_management_command(` `priv` (L3710-3712)
- @brief Print manual self-management command for non-Linux runtimes.
- @details Emits deterministic guidance without executing local `uv tool` commands.
- @param action `str` — management action token (`upgrade` or `uninstall`).
- @param command_tokens `Tuple[str, ...]` — command token sequence to print verbatim.
- @return None.
- @satisfies REQ-129 REQ-130

### fn `def upgrade_self(repo_root: Optional[Path] = None, github: bool = False)` (L3738-3761)
- @brief Execute `upgrade_self` runtime logic for Git-Alias CLI.
- @details Selects the GitHub tagged-release source (REQ-201) when `github` is
True and the PyPI default release (REQ-001) otherwise. The GitHub
path resolves the newest release tag via
`_fetch_github_latest_release_tag` (REQ-208) and installs through
`_build_github_upgrade_command` (REQ-209); resolution failure
aborts with an explicit English error and non-zero exit before any
install (REQ-210). Non-Linux hosts receive the exact manual command
matching the selected source without local execution (REQ-129).
- @param repo_root Input parameter consumed by `upgrade_self`.
- @param github {bool} When True, upgrade from the newest GitHub release tag
(REQ-201, REQ-208, REQ-209) instead of the default PyPI release
(REQ-001).
- @return None; side-effect: uv tool install subprocess, manual-command
guidance, or English abort diagnostic with non-zero exit.
- @exception SystemExit Exit code 1 when REQ-208 tag resolution fails (REQ-210).
- @satisfies REQ-001, REQ-129, REQ-201, REQ-208, REQ-209, REQ-210

### fn `def _remove_version_check_cache_artifacts() -> None` `priv` (L3768-3789)
- @brief Remove update-check idle-time cache artifacts before Linux uninstall.
- @details Deletes `VERSION_CHECK_CACHE_FILE` when present and then removes the
parent directory, enforcing deterministic failure on invalid path types
or non-empty cache directory state.
- @return None.
- @satisfies REQ-002

### fn `def uninstall_self()` (L3794-3801)
- @brief Execute `uninstall_self` runtime logic for Git-Alias CLI.
- @details Executes `uninstall_self` using deterministic CLI control-flow and explicit error propagation.
- @return Result emitted by `uninstall_self` according to command contract.
- @satisfies REQ-002 REQ-130

### fn `def cmd_aa(extra)` (L3806-3813)
- @brief Execute `cmd_aa` runtime logic for Git-Alias CLI.
- @details Executes `cmd_aa` using deterministic CLI control-flow and explicit error propagation.
- @param extra Input parameter consumed by `cmd_aa`.
- @return Result emitted by `cmd_aa` according to command contract.

### fn `def cmd_ra(extra)` (L3818-3841)
- @brief Execute `cmd_ra` runtime logic for Git-Alias CLI.
- @details Executes `cmd_ra` using deterministic CLI control-flow and explicit error propagation.
- @param extra Input parameter consumed by `cmd_ra`.
- @return Result emitted by `cmd_ra` according to command contract.

### fn `def cmd_ar(extra)` (L3846-3864)
- @brief Execute `cmd_ar` runtime logic for Git-Alias CLI.
- @details Executes `cmd_ar` using deterministic CLI control-flow and explicit error propagation.
- @param extra Input parameter consumed by `cmd_ar`.
- @return Result emitted by `cmd_ar` according to command contract.

### fn `def cmd_br(extra)` (L3869-3872)
- @brief Execute `cmd_br` runtime logic for Git-Alias CLI.
- @details Executes `cmd_br` using deterministic CLI control-flow and explicit error propagation.
- @param extra Input parameter consumed by `cmd_br`.
- @return Result emitted by `cmd_br` according to command contract.

### fn `def cmd_bd(extra)` (L3881-3899)
- @brief Execute `cmd_bd` runtime logic for Git-Alias CLI.
- @details Accepts one branch target with optional `--force`, resolves worktree associations,
deletes an associated worktree before deleting the branch, and uses forced git delete
flags only when explicitly requested.
- @param extra `list | None` — requires exactly one branch target or `--help`.
- @return Return value from `run_git_cmd` when only the branch is deleted; otherwise `None`.
- @exception SystemExit Exit code 1 on invalid operands or preflight failure.
- @satisfies REQ-019, REQ-138, REQ-139, REQ-140, REQ-141, REQ-142, REQ-144, REQ-145

### fn `def cmd_ck(extra)` (L3904-3907)
- @brief Execute `cmd_ck` runtime logic for Git-Alias CLI.
- @details Executes `cmd_ck` using deterministic CLI control-flow and explicit error propagation.
- @param extra Input parameter consumed by `cmd_ck`.
- @return Result emitted by `cmd_ck` according to command contract.

### fn `def _ensure_commit_ready(alias)` `priv` (L3912-3925)
- @brief Execute `_ensure_commit_ready` runtime logic for Git-Alias CLI.
- @details Executes `_ensure_commit_ready` using deterministic CLI control-flow and explicit error propagation.
- @param alias Input parameter consumed by `_ensure_commit_ready`.
- @return Result emitted by `_ensure_commit_ready` according to command contract.

### fn `def _ensure_commit_ready_with_stage(alias)` `priv` (L3943-3957)
- @brief Commit-readiness guard with automatic working-tree staging for Git-Alias CLI.
- @brief Execute `_ensure_commit_ready_with_stage` runtime logic for Git-Alias CLI.
- @details Evaluates working-tree and staging state via `_git_status_lines()`.
Control flow:
1. Both staging and working-tree empty → print error and `sys.exit(1)`.
2. Staging empty AND working-tree dirty → invoke `cmd_aa([])` to stage all changes.
3. Staging non-empty → return `True` immediately.
Satisfies REQ-021, REQ-022, DES-007: auto-stage path for `wip` and conventional commit aliases.
Does NOT enforce "no unstaged changes" constraint; that constraint belongs to `_ensure_commit_ready`.
- @details Executes `_ensure_commit_ready_with_stage` using deterministic CLI control-flow and explicit error propagation.
- @param alias `str` — alias name used in error messages.
- @param alias Input parameter consumed by `_ensure_commit_ready_with_stage`.
- @return `True` when staging is confirmed non-empty after optional `cmd_aa` execution.
- @return Result emitted by `_ensure_commit_ready_with_stage` according to command contract.
- @exception SystemExit Exit code 1 when both working-tree and staging have no committable data.
- @see _ensure_commit_ready, cmd_aa, has_staged_changes, has_unstaged_changes
- @satisfies REQ-021, REQ-022, DES-007

### fn `def cmd_cm(extra)` (L3962-3967)
- @brief Execute `cmd_cm` runtime logic for Git-Alias CLI.
- @details Executes `cmd_cm` using deterministic CLI control-flow and explicit error propagation.
- @param extra Input parameter consumed by `cmd_cm`.
- @return Result emitted by `cmd_cm` according to command contract.

### fn `def cmd_wip(extra)` (L3977-3989)
- @brief Execute `cmd_wip` runtime logic for Git-Alias CLI.
- @details Validates commitability via `_ensure_commit_ready_with_stage` (auto-stages working-tree changes
when staging is empty); rejects positional arguments except `--help`; emits fixed message
`wip: work in progress.` and delegates to `_execute_commit` with WIP-amend semantics.
- @param extra `list | None` — CLI extra arguments; only `["--help"]` is accepted.
- @return Return value of `_execute_commit`, or `None` on `--help`.
- @exception SystemExit Exit code 1 on positional argument or no-data failure; exit code 0 on `--help`.
- @see _ensure_commit_ready_with_stage, _execute_commit, cmd_aa
- @satisfies REQ-021, DES-007

### fn `def cmd_release(extra)` (L3994-4016)
- @brief Execute `cmd_release` runtime logic for Git-Alias CLI.
- @details Executes `cmd_release` using deterministic CLI control-flow and explicit error propagation.
- @param extra Input parameter consumed by `cmd_release`.
- @return Result emitted by `cmd_release` according to command contract.

### fn `def cmd_new(extra)` (L4021-4024)
- @brief Execute `cmd_new` runtime logic for Git-Alias CLI.
- @details Executes `cmd_new` using deterministic CLI control-flow and explicit error propagation.
- @param extra Input parameter consumed by `cmd_new`.
- @return Result emitted by `cmd_new` according to command contract.

### fn `def cmd_refactor(extra)` (L4029-4032)
- @brief Execute `cmd_refactor` runtime logic for Git-Alias CLI.
- @details Executes `cmd_refactor` using deterministic CLI control-flow and explicit error propagation.
- @param extra Input parameter consumed by `cmd_refactor`.
- @return Result emitted by `cmd_refactor` according to command contract.

### fn `def cmd_fix(extra)` (L4037-4040)
- @brief Execute `cmd_fix` runtime logic for Git-Alias CLI.
- @details Executes `cmd_fix` using deterministic CLI control-flow and explicit error propagation.
- @param extra Input parameter consumed by `cmd_fix`.
- @return Result emitted by `cmd_fix` according to command contract.

### fn `def cmd_change(extra)` (L4045-4048)
- @brief Execute `cmd_change` runtime logic for Git-Alias CLI.
- @details Executes `cmd_change` using deterministic CLI control-flow and explicit error propagation.
- @param extra Input parameter consumed by `cmd_change`.
- @return Result emitted by `cmd_change` according to command contract.

### fn `def cmd_implement(extra)` (L4053-4056)
- @brief Execute `cmd_implement` runtime logic for Git-Alias CLI.
- @details Executes `cmd_implement` using deterministic CLI control-flow and explicit error propagation.
- @param extra Input parameter consumed by `cmd_implement`.
- @return Result emitted by `cmd_implement` according to command contract.

### fn `def cmd_docs(extra)` (L4061-4064)
- @brief Execute `cmd_docs` runtime logic for Git-Alias CLI.
- @details Executes `cmd_docs` using deterministic CLI control-flow and explicit error propagation.
- @param extra Input parameter consumed by `cmd_docs`.
- @return Result emitted by `cmd_docs` according to command contract.

### fn `def cmd_style(extra)` (L4069-4072)
- @brief Execute `cmd_style` runtime logic for Git-Alias CLI.
- @details Executes `cmd_style` using deterministic CLI control-flow and explicit error propagation.
- @param extra Input parameter consumed by `cmd_style`.
- @return Result emitted by `cmd_style` according to command contract.

### fn `def cmd_revert(extra)` (L4077-4080)
- @brief Execute `cmd_revert` runtime logic for Git-Alias CLI.
- @details Executes `cmd_revert` using deterministic CLI control-flow and explicit error propagation.
- @param extra Input parameter consumed by `cmd_revert`.
- @return Result emitted by `cmd_revert` according to command contract.

### fn `def cmd_rollback(extra)` (L4094-4169)
- @brief Execute `cmd_rollback` runtime logic for Git-Alias CLI.
- @details Validates clean preconditions, resolves a reachable commit target from
current branch, runs the release-style canonical version detection as
pre-flight check, applies inverse changes with `git revert --no-commit
<target>..HEAD`, restores the pre-rollback application version through
the `chver` flow, stages restored files with `git add --all`, and creates
one non-amend conventional `revert` commit preserving the pre-rollback
version. A failed version restore aborts via `git revert --abort`.
- @param extra `list | None` — requires exactly one rollback target or `--help`.
- @return Return value emitted by `_execute_commit`.
- @exception SystemExit Exit code 1 on argument, precondition, resolution, ancestry,
version-check, revert, or version-restore failures.
- @satisfies REQ-132, REQ-133, REQ-134, REQ-135, REQ-169, REQ-170, REQ-171, REQ-172, REQ-173, REQ-174

### fn `def cmd_misc(extra)` (L4174-4177)
- @brief Execute `cmd_misc` runtime logic for Git-Alias CLI.
- @details Executes `cmd_misc` using deterministic CLI control-flow and explicit error propagation.
- @param extra Input parameter consumed by `cmd_misc`.
- @return Result emitted by `cmd_misc` according to command contract.

### fn `def cmd_cover(extra)` (L4182-4185)
- @brief Execute `cmd_cover` runtime logic for Git-Alias CLI.
- @details Executes `cmd_cover` using deterministic CLI control-flow and explicit error propagation.
- @param extra Input parameter consumed by `cmd_cover`.
- @return Result emitted by `cmd_cover` according to command contract.

### fn `def cmd_co(extra)` (L4190-4193)
- @brief Execute `cmd_co` runtime logic for Git-Alias CLI.
- @details Executes `cmd_co` using deterministic CLI control-flow and explicit error propagation.
- @param extra Input parameter consumed by `cmd_co`.
- @return Result emitted by `cmd_co` according to command contract.

### fn `def _selected_diff_command_parts() -> List[str]` `priv` (L4207-4217)
- @brief Resolve the environment-selected diff tool argv for extcmd injection.
- @details Applies the REQ-186/REQ-187/REQ-188 selection to the
`diff_command`/`diff_command_gfx` pair: graphical environments
select `diff_command_gfx` when non-empty, otherwise the terminal
`diff_command` applies. Unlike `_environment_config_command_parts`,
an empty effective value returns `[]` per REQ-190 so the caller runs
plain `git difftool -d` without overriding git's configured tool.
Non-empty values are tokenized and validated through
`_validated_config_command_parts`.
- @return {List[str]} Validated argv tokens of the selected diff tool; `[]` when unconfigured.
- @exception RuntimeError Raised when the selected non-empty command is invalid or unavailable.
- @note Complexity: O(1) excluding PATH lookup inside validation.
- @satisfies REQ-187, REQ-188, REQ-190

### fn `def _run_configured_diff(refs, extra=None)` `priv` (L4235-4242)
- @brief Execute `git difftool -d` with the configured tool injected as extcmd.
- @details Implements REQ-189/REQ-190: builds the `git difftool -d` base argv,
appends `--extcmd=<selected command>` when
`_selected_diff_command_parts` returns a non-empty tool so the
environment-selected galias tool overrides git's configured diff
tool, then appends the ordered ref operands and forwarded extras.
An empty tool runs plain `git difftool -d` (REQ-190). Execution goes
through `run_command` so every visual diff alias passes the same
environment-detection and subprocess-interception path (REQ-185).
- @param refs {List[str]} Ordered git ref operands appended after the difftool argv.
- @param extra {Optional[List[str]]} Additional CLI operands forwarded unchanged.
- @return Result of `run_command` for the delegated `git difftool` subprocess.
- @exception RuntimeError Raised when the selected diff command is invalid or unavailable.
- @note `--extcmd` tokens are joined with single spaces; embedded whitespace
inside tokens is not re-quoted.
- @note Complexity: O(1) excluding PATH lookup and subprocess runtime.
- @satisfies REQ-189, REQ-190, REQ-185, REQ-187

### fn `def cmd_dc(extra)` (L4256-4269)
- @brief Execute `cmd_dc` runtime logic for Git-Alias CLI.
- @details Validates the REQ-182 arity contract (exactly one required `<ref>`
plus at most one optional `<ref_prev>`), resolves an omitted `<ref_prev>` to
the commit preceding `<ref>` via the git revision expression `<ref>~1` per
REQ-184, and delegates to `_run_configured_diff([<ref_prev>, <ref>])` so the
rendered diff direction is always `<ref_prev>` -> `<ref>` and never inverted
per REQ-183, using the environment-resolved diff command per REQ-189.
- @param extra {Optional[List[str]]} CLI operands after `dc`; accepted arity is
1 or 2 positional git refs (`--help` is intercepted by `main` before dispatch).
- @return Result of `_run_configured_diff` for the delegated diff subprocess.
- @exception SystemExit Exit code 1 on zero or more than two positional refs.
- @note Complexity: O(1); no CLI-side ref resolution or transformation.
- @satisfies REQ-182, REQ-183, REQ-184, REQ-189

### fn `def cmd_dcc(extra)` (L4276-4279)
- @brief Execute `cmd_dcc` runtime logic for Git-Alias CLI.
- @details Delegates refs `HEAD~1 HEAD` to `_run_configured_diff` so the diff
runs through the environment-resolved configured diff command per REQ-189.
- @param extra Input parameter consumed by `cmd_dcc`.
- @return Result emitted by `_run_configured_diff` according to command contract.
- @satisfies REQ-037, REQ-189

### fn `def cmd_dccc(extra)` (L4286-4289)
- @brief Execute `cmd_dccc` runtime logic for Git-Alias CLI.
- @details Delegates refs `HEAD~2 HEAD` to `_run_configured_diff` so the diff
runs through the environment-resolved configured diff command per REQ-189.
- @param extra Input parameter consumed by `cmd_dccc`.
- @return Result emitted by `_run_configured_diff` according to command contract.
- @satisfies REQ-038, REQ-189

### fn `def cmd_de(extra)` (L4294-4297)
- @brief Execute `cmd_de` runtime logic for Git-Alias CLI.
- @details Executes `cmd_de` using deterministic CLI control-flow and explicit error propagation.
- @param extra Input parameter consumed by `cmd_de`.
- @return Result emitted by `cmd_de` according to command contract.

### fn `def cmd_di(extra)` (L4302-4305)
- @brief Execute `cmd_di` runtime logic for Git-Alias CLI.
- @details Executes `cmd_di` using deterministic CLI control-flow and explicit error propagation.
- @param extra Input parameter consumed by `cmd_di`.
- @return Result emitted by `cmd_di` according to command contract.

### fn `def cmd_diyou(extra)` (L4310-4313)
- @brief Execute `cmd_diyou` runtime logic for Git-Alias CLI.
- @details Executes `cmd_diyou` using deterministic CLI control-flow and explicit error propagation.
- @param extra Input parameter consumed by `cmd_diyou`.
- @return Result emitted by `cmd_diyou` according to command contract.

### fn `def cmd_dime(extra)` (L4318-4321)
- @brief Execute `cmd_dime` runtime logic for Git-Alias CLI.
- @details Executes `cmd_dime` using deterministic CLI control-flow and explicit error propagation.
- @param extra Input parameter consumed by `cmd_dime`.
- @return Result emitted by `cmd_dime` according to command contract.

### fn `def cmd_dwc(extra)` (L4328-4331)
- @brief Execute `cmd_dwc` runtime logic for Git-Alias CLI.
- @details Delegates ref `HEAD` to `_run_configured_diff` so the working-tree
vs HEAD diff runs through the environment-resolved diff command per REQ-189.
- @param extra Input parameter consumed by `cmd_dwc`.
- @return Result emitted by `_run_configured_diff` according to command contract.
- @satisfies REQ-037, REQ-189

### fn `def cmd_dw(extra)` (L4340-4347)
- @brief Execute `cmd_dw` runtime logic for Git-Alias CLI.
- @details Validates exactly one positional git ref, then delegates `<ref>` to
`_run_configured_diff` for the working-tree vs ref diff through the
environment-resolved diff command per REQ-189.
- @param extra Input parameter consumed by `cmd_dw`.
- @return Result emitted by `_run_configured_diff` according to command contract.
- @exception SystemExit Exit code 1 on zero or multiple positional refs.
- @satisfies REQ-037, REQ-189

### fn `def cmd_dwcc(extra)` (L4355-4358)
- @brief Execute `cmd_dwcc` runtime logic for Git-Alias CLI.
- @details Delegates ref `HEAD~1` to `_run_configured_diff` so the working-tree
vs penultimate-commit diff runs through the environment-resolved diff
command per REQ-189.
- @param extra Input parameter consumed by `cmd_dwcc`.
- @return Result emitted by `_run_configured_diff` according to command contract.
- @satisfies REQ-038, REQ-189

### fn `def cmd_dcd(extra)` (L4365-4370)
- @brief Execute `cmd_dcd` runtime logic for Git-Alias CLI.
- @details Resolves configured `develop` and `work` branch names, then delegates
refs `<develop> <work>` to `_run_configured_diff` per REQ-119/REQ-189.
- @param extra Input parameter consumed by `cmd_dcd`.
- @return Result emitted by `_run_configured_diff` according to command contract.
- @satisfies REQ-119, REQ-189

### fn `def cmd_dcm(extra)` (L4377-4382)
- @brief Execute `cmd_dcm` runtime logic for Git-Alias CLI.
- @details Resolves configured `master` and `work` branch names, then delegates
refs `<master> <work>` to `_run_configured_diff` per REQ-119/REQ-189.
- @param extra Input parameter consumed by `cmd_dcm`.
- @return Result emitted by `_run_configured_diff` according to command contract.
- @satisfies REQ-119, REQ-189

### fn `def cmd_ddm(extra)` (L4390-4395)
- @brief Execute `cmd_ddm` runtime logic for Git-Alias CLI.
- @details Resolves configured `master` and `develop` branch names, then
delegates refs `<master> <develop>` to `_run_configured_diff` per
REQ-119/REQ-189.
- @param extra Input parameter consumed by `cmd_ddm`.
- @return Result emitted by `_run_configured_diff` according to command contract.
- @satisfies REQ-119, REQ-189

### fn `def cmd_ed(extra)` (L4400-4409)
- @brief Execute `cmd_ed` runtime logic for Git-Alias CLI.
- @details Executes `cmd_ed` using deterministic CLI control-flow and explicit error propagation.
- @param extra Input parameter consumed by `cmd_ed`.
- @return Result emitted by `cmd_ed` according to command contract.

### fn `def cmd_fe(extra)` (L4414-4417)
- @brief Execute `cmd_fe` runtime logic for Git-Alias CLI.
- @details Executes `cmd_fe` using deterministic CLI control-flow and explicit error propagation.
- @param extra Input parameter consumed by `cmd_fe`.
- @return Result emitted by `cmd_fe` according to command contract.

### fn `def cmd_feall(extra)` (L4422-4425)
- @brief Execute `cmd_feall` runtime logic for Git-Alias CLI.
- @details Executes `cmd_feall` using deterministic CLI control-flow and explicit error propagation.
- @param extra Input parameter consumed by `cmd_feall`.
- @return Result emitted by `cmd_feall` according to command contract.

### fn `def _execute_get_flow()` `priv` (L4437-4511)
- @brief Execute preflight verifications and fast-forward synchronization flow for `get`.
- @details Validates clean index/worktree, current-branch=work, develop contains work HEAD,
local develop and master aligned on same commit, local develop/master HEADs already
present on their origin counterparts, and origin/develop strictly ahead of local
develop. Then fetches origin master into local master fast-forward (with tags),
fetches origin develop into local develop fast-forward (with tags), and finally
fast-forward merges local develop into the currently checked out work branch.
Any verification failure or git step error raises `ReleaseError` with an explicit
English diagnostic.
- @return None; raises `ReleaseError` on any verification or execution failure.
- @satisfies REQ-146, REQ-148, REQ-149, REQ-150, REQ-151, REQ-152, REQ-153, REQ-154, REQ-155

### fn `def cmd_get(extra)` (L4518-4532)
- @brief CLI entry-point for the `get` subcommand.
- @details Rejects positional arguments, supports `--help`, and delegates to `_execute_get_flow`.
Converts `ReleaseError` into stderr output plus non-zero exit.
- @param extra Iterable of CLI argument strings following the `get` subcommand token.
- @return None; side-effects: fast-forwards local branches and tags from origin.
- @satisfies REQ-146, REQ-147, REQ-155

### fn `def cmd_gp(extra)` (L4537-4542)
- @brief Execute `cmd_gp` runtime logic for Git-Alias CLI.
- @details Executes `cmd_gp` using deterministic CLI control-flow and explicit error propagation.
- @param extra Input parameter consumed by `cmd_gp`.
- @return Result emitted by `cmd_gp` according to command contract.

### fn `def cmd_gr(extra)` (L4547-4552)
- @brief Execute `cmd_gr` runtime logic for Git-Alias CLI.
- @details Executes `cmd_gr` using deterministic CLI control-flow and explicit error propagation.
- @param extra Input parameter consumed by `cmd_gr`.
- @return Result emitted by `cmd_gr` according to command contract.

- var `OVERVIEW_COLOR_RESET = "\033[0m"` (L4554)
- @brief Constant `OVERVIEW_COLOR_RESET` used by CLI runtime paths and policies.
- var `OVERVIEW_COLOR_SECTION_PURPLE = "\033[35;1m"` (L4556)
- @brief Constant `OVERVIEW_COLOR_SECTION_PURPLE` used by CLI runtime paths and policies.
- var `OVERVIEW_COLOR_AHEAD = "\033[92m"` (L4558)
- @brief Constant `OVERVIEW_COLOR_AHEAD` used by CLI runtime paths and policies.
- var `OVERVIEW_COLOR_BEHIND = "\033[31;1m"` (L4560)
- @brief Constant `OVERVIEW_COLOR_BEHIND` used by CLI runtime paths and policies.
- var `OVERVIEW_COLOR_LABEL = "\033[38;5;226m"` (L4562)
- @brief Constant `OVERVIEW_COLOR_LABEL` used by CLI runtime paths and policies.
- var `OVERVIEW_COLOR_WHITE = "\033[97m"` (L4564)
- @brief Constant `OVERVIEW_COLOR_WHITE` used by CLI runtime paths and policies.
- var `OVERVIEW_COLOR_WHITE_BOLD = "\033[97;1m"` (L4566)
- @brief Constant `OVERVIEW_COLOR_WHITE_BOLD` used by CLI runtime paths and policies.
- var `OVERVIEW_SECTION_TEMPLATE = "{color}=== {title} ==={reset}"` (L4568)
- @brief Constant `OVERVIEW_SECTION_TEMPLATE` used by CLI runtime paths and policies.
- var `OVERVIEW_SUBSECTION_TEMPLATE = "{color}--- {title} ---{reset}"` (L4570)
- @brief Constant `OVERVIEW_SUBSECTION_TEMPLATE` used by CLI runtime paths and policies.
- var `OVERVIEW_DISTANCE_TEMPLATE = "{text_color}{label}{reset} | {ahead} | {behind}"` (L4572)
- @brief Constant `OVERVIEW_DISTANCE_TEMPLATE` used by CLI runtime paths and policies.
### fn `def _overview_branch_identifier(` `priv` (L4581-4584)
- @brief Execute `_overview_branch_identifier` runtime logic for Git-Alias CLI.
- @details Executes `_overview_branch_identifier` using deterministic CLI control-flow and explicit error propagation.
- @param logical_name Input parameter consumed by `_overview_branch_identifier`.
- @param ref_name Input parameter consumed by `_overview_branch_identifier`.
- @param prefix_color Input parameter consumed by `_overview_branch_identifier`.
- @return Result emitted by `_overview_branch_identifier` according to command contract.

### fn `def _overview_work_prefix_color(worktree_state: str) -> str` `priv` (L4598-4605)
- @brief Execute `_overview_work_prefix_color` runtime logic for Git-Alias CLI.
- @details Executes `_overview_work_prefix_color` using deterministic CLI control-flow and explicit error propagation.
- @param worktree_state Input parameter consumed by `_overview_work_prefix_color`.
- @return Result emitted by `_overview_work_prefix_color` according to command contract.

### fn `def _overview_logical_branch_name(` `priv` (L4613-4617)
- @brief Execute `_overview_logical_branch_name` runtime logic for Git-Alias CLI.
- @details Executes `_overview_logical_branch_name` using deterministic CLI control-flow and explicit error propagation.
- @param current_branch Input parameter consumed by `_overview_logical_branch_name`.
- @param work_branch Input parameter consumed by `_overview_logical_branch_name`.
- @param develop_branch Input parameter consumed by `_overview_logical_branch_name`.
- @param master_branch Input parameter consumed by `_overview_logical_branch_name`.
- @return Result emitted by `_overview_logical_branch_name` according to command contract.

### fn `def _overview_current_branch_display(` `priv` (L4636-4641)
- @brief Execute `_overview_current_branch_display` runtime logic for Git-Alias CLI.
- @details Executes `_overview_current_branch_display` using deterministic CLI control-flow and explicit error propagation.
- @param current_branch Input parameter consumed by `_overview_current_branch_display`.
- @param work_branch Input parameter consumed by `_overview_current_branch_display`.
- @param develop_branch Input parameter consumed by `_overview_current_branch_display`.
- @param master_branch Input parameter consumed by `_overview_current_branch_display`.
- @param worktree_state Input parameter consumed by `_overview_current_branch_display`.
- @return Result emitted by `_overview_current_branch_display` according to command contract.

### fn `def _overview_ref_is_available(ref_name: str) -> bool` `priv` (L4663-4672)
- @brief Execute `_overview_ref_is_available` runtime logic for Git-Alias CLI.
- @details Executes `_overview_ref_is_available` using deterministic CLI control-flow and explicit error propagation.
- @param ref_name Input parameter consumed by `_overview_ref_is_available`.
- @return Result emitted by `_overview_ref_is_available` according to command contract.

### fn `def _overview_ref_latest_subject(ref_name: str) -> str` `priv` (L4678-4688)
- @brief Resolve latest commit subject for an overview ref.
- @details Returns the `%s` subject of `git log -1` for the input ref, or `n/a`
when the ref is unavailable or the lookup fails.
- @param ref_name Input parameter consumed by `_overview_ref_latest_subject`.
- @return Result emitted by `_overview_ref_latest_subject` according to command contract.

### fn `def _overview_discovered_branch_refs() -> List[str]` `priv` (L4693-4716)
- @brief Collect normalized branch refs from `git branch -a` for overview rendering.
- @details Returns ordered unique branch refs, stripping current-branch marker and
`remotes/` prefix and excluding symbolic-ref redirect rows.
- @return Result emitted by `_overview_discovered_branch_refs` according to command contract.

### fn `def _overview_branch_summary_lines(` `priv` (L4749-4760)
- @brief Build section-5 aligned branch summary lines for overview output.
- @brief Execute `_overview_branch_summary_lines` runtime logic for Git-Alias CLI.
- @details Produces one row for each configured branch/ref identifier using
`<Identifier> | <latest commit subject>` formatting, aligned by visible
identifier width and with commit subject in bright white bold; appends rows
for additional branch refs after configured rows.
- @details Executes `_overview_branch_summary_lines` using deterministic CLI control-flow and explicit error propagation.
- @param work_ref Input parameter consumed by `_overview_branch_summary_lines`.
- @param develop_ref Input parameter consumed by `_overview_branch_summary_lines`.
- @param master_ref Input parameter consumed by `_overview_branch_summary_lines`.
- @param remote_develop_ref Input parameter consumed by `_overview_branch_summary_lines`.
- @param remote_master_ref Input parameter consumed by `_overview_branch_summary_lines`.
- @param work_display Input parameter consumed by `_overview_branch_summary_lines`.
- @param develop_display Input parameter consumed by `_overview_branch_summary_lines`.
- @param master_display Input parameter consumed by `_overview_branch_summary_lines`.
- @param remote_develop_display Input parameter consumed by `_overview_branch_summary_lines`.
- @param remote_master_display Input parameter consumed by `_overview_branch_summary_lines`.
- @param additional_refs Input parameter consumed by `_overview_branch_summary_lines`.
- @param work_ref Input parameter consumed by `_overview_branch_summary_lines`.
- @param develop_ref Input parameter consumed by `_overview_branch_summary_lines`.
- @param master_ref Input parameter consumed by `_overview_branch_summary_lines`.
- @param remote_develop_ref Input parameter consumed by `_overview_branch_summary_lines`.
- @param remote_master_ref Input parameter consumed by `_overview_branch_summary_lines`.
- @param work_display Input parameter consumed by `_overview_branch_summary_lines`.
- @param develop_display Input parameter consumed by `_overview_branch_summary_lines`.
- @param master_display Input parameter consumed by `_overview_branch_summary_lines`.
- @param remote_develop_display Input parameter consumed by `_overview_branch_summary_lines`.
- @param remote_master_display Input parameter consumed by `_overview_branch_summary_lines`.
- @param additional_refs Input parameter consumed by `_overview_branch_summary_lines`.
- @return Result emitted by `_overview_branch_summary_lines` according to command contract.
- @return Result emitted by `_overview_branch_summary_lines` according to command contract.
- @satisfies REQ-094, REQ-096, REQ-115

### fn `def _overview_relation_state(ahead: int, behind: int) -> str` `priv` (L4803-4812)
- @brief Execute `_overview_relation_state` runtime logic for Git-Alias CLI.
- @details Executes `_overview_relation_state` using deterministic CLI control-flow and explicit error propagation.
- @param ahead Input parameter consumed by `_overview_relation_state`.
- @param behind Input parameter consumed by `_overview_relation_state`.
- @return Result emitted by `_overview_relation_state` according to command contract.

### fn `def _overview_worktree_state(status_lines=None) -> str` `priv` (L4817-4829)
- @brief Execute `_overview_worktree_state` runtime logic for Git-Alias CLI.
- @details Executes `_overview_worktree_state` using deterministic CLI control-flow and explicit error propagation.
- @param status_lines Input parameter consumed by `_overview_worktree_state`.
- @return Result emitted by `_overview_worktree_state` according to command contract.

### fn `def _overview_distance_text(is_ahead: bool, count: int) -> str` `priv` (L4835-4843)
- @brief Execute `_overview_distance_text` runtime logic for Git-Alias CLI.
- @details Executes `_overview_distance_text` using deterministic CLI control-flow and explicit error propagation.
- @param is_ahead Input parameter consumed by `_overview_distance_text`.
- @param count Input parameter consumed by `_overview_distance_text`.
- @return Result emitted by `_overview_distance_text` according to command contract.

### fn `def _overview_compare_refs(base_ref: str, target_ref: str, label: str) -> str` `priv` (L4850-4892)
- @brief Execute `_overview_compare_refs` runtime logic for Git-Alias CLI.
- @details Executes `_overview_compare_refs` using deterministic CLI control-flow and explicit error propagation.
- @param base_ref Input parameter consumed by `_overview_compare_refs`.
- @param target_ref Input parameter consumed by `_overview_compare_refs`.
- @param label Input parameter consumed by `_overview_compare_refs`.
- @return Result emitted by `_overview_compare_refs` according to command contract.

### fn `def _overview_ascii_topology_lines(` `priv` (L4927-4938)
- @brief Build chronological-position topology tree from actual commit positions.
- @brief Execute `_overview_ascii_topology_lines` runtime logic for Git-Alias CLI.
- @details Resolves commit hashes for each ref, computes commit counts from
octopus merge-base, groups refs sharing the same hash on one output line,
and orders nodes from most-ahead (root) to most-behind (deepest child).
WorkingTree always occupies a dedicated line above the line that contains
Work when tied or dirty. Complexity O(R) git
subprocess calls where R is the number of available refs.
- @details Executes `_overview_ascii_topology_lines` using deterministic CLI control-flow and explicit error propagation.
- @param work_ref {str} Git ref name for work branch.
- @param develop_ref {str} Git ref name for develop branch.
- @param master_ref {str} Git ref name for master branch.
- @param remote_develop_ref {str} Git ref name for remote develop (e.g., origin/develop).
- @param remote_master_ref {str} Git ref name for remote master (e.g., origin/master).
- @param work_display {str} Rendered display string for Work identifier.
- @param develop_display {str} Rendered display string for Develop identifier.
- @param master_display {str} Rendered display string for Master identifier.
- @param remote_develop_display {str} Rendered display string for RemoteDevelop identifier.
- @param remote_master_display {str} Rendered display string for RemoteMaster identifier.
- @param worktree_state {str} Working tree state (clean/unstaged/staged/mixed).
- @param work_ref Input parameter consumed by `_overview_ascii_topology_lines`.
- @param develop_ref Input parameter consumed by `_overview_ascii_topology_lines`.
- @param master_ref Input parameter consumed by `_overview_ascii_topology_lines`.
- @param remote_develop_ref Input parameter consumed by `_overview_ascii_topology_lines`.
- @param remote_master_ref Input parameter consumed by `_overview_ascii_topology_lines`.
- @param work_display Input parameter consumed by `_overview_ascii_topology_lines`.
- @param develop_display Input parameter consumed by `_overview_ascii_topology_lines`.
- @param master_display Input parameter consumed by `_overview_ascii_topology_lines`.
- @param remote_develop_display Input parameter consumed by `_overview_ascii_topology_lines`.
- @param remote_master_display Input parameter consumed by `_overview_ascii_topology_lines`.
- @param worktree_state Input parameter consumed by `_overview_ascii_topology_lines`.
- @return {List[str]} Rendered topology lines with ANSI color codes.
- @return Result emitted by `_overview_ascii_topology_lines` according to command contract.
- @satisfies REQ-089, REQ-090, REQ-091, REQ-092, REQ-093, REQ-095

### fn `def _overview_current_branch_state_lines(current_branch_display: str) -> List[str]` `priv` (L5030-5049)
- @brief Build normalized section-6 status lines for overview output.
- @details Executes `git status -sb`, rewrites the header line from
`## <branch>` to `## <Logical>(⎇ <branch>)` with the same color formatting
used by section-1 current-branch output, and preserves all other lines.
- @param current_branch_display Input parameter consumed by `_overview_current_branch_state_lines`.
- @return {List[str]} Result emitted by `_overview_current_branch_state_lines` according to command contract.
- @satisfies REQ-094

### fn `def cmd_o(extra)` (L5055-5209)
- @brief Execute `cmd_o` runtime logic for Git-Alias CLI.
- @details Executes `cmd_o` using deterministic CLI control-flow and explicit error propagation.
- @param extra Input parameter consumed by `cmd_o`.
- @return Result emitted by `cmd_o` according to command contract.
- @satisfies REQ-082, REQ-083, REQ-084, REQ-085, REQ-086, REQ-087, REQ-088, REQ-089, REQ-090, REQ-091, REQ-092, REQ-093, REQ-094, REQ-095, REQ-096, REQ-115

### fn `def cmd_str(extra)` (L5214-5243)
- @brief Execute `cmd_str` runtime logic for Git-Alias CLI.
- @details Executes `cmd_str` using deterministic CLI control-flow and explicit error propagation.
- @details Query git remotes with transport metadata.
- @param extra Input parameter consumed by `cmd_str`.
- @return Result emitted by `cmd_str` according to command contract.

### fn `def cmd_l(extra)` (L5252-5258)
- @brief Execute `cmd_l` runtime logic for Git-Alias CLI.
- @details Delegates to `foresta.run()` which renders a text-based tree visualization
of git commit history using a vine-based graph algorithm with configurable styles,
symbols, colors, and margins. Injects `-n 25` only when invoked without
user arguments; otherwise forwards provided arguments unchanged.
- @param extra {list} Additional CLI arguments forwarded to the foresta engine.
- @return None.
- @satisfies REQ-098, REQ-099, REQ-111

### fn `def cmd_lb(extra)` (L5263-5266)
- @brief Execute `cmd_lb` runtime logic for Git-Alias CLI.
- @details Executes `cmd_lb` using deterministic CLI control-flow and explicit error propagation.
- @param extra Input parameter consumed by `cmd_lb`.
- @return Result emitted by `cmd_lb` according to command contract.

### fn `def cmd_lg(extra)` (L5271-5284)
- @brief Execute `cmd_lg` runtime logic for Git-Alias CLI.
- @details Executes `cmd_lg` using deterministic CLI control-flow and explicit error propagation.
- @param extra Input parameter consumed by `cmd_lg`.
- @return Result emitted by `cmd_lg` according to command contract.

### fn `def cmd_lh(extra)` (L5289-5292)
- @brief Execute `cmd_lh` runtime logic for Git-Alias CLI.
- @details Executes `cmd_lh` using deterministic CLI control-flow and explicit error propagation.
- @param extra Input parameter consumed by `cmd_lh`.
- @return Result emitted by `cmd_lh` according to command contract.

### fn `def cmd_ll(extra)` (L5297-5309)
- @brief Execute `cmd_ll` runtime logic for Git-Alias CLI.
- @details Executes `cmd_ll` using deterministic CLI control-flow and explicit error propagation.
- @param extra Input parameter consumed by `cmd_ll`.
- @return Result emitted by `cmd_ll` according to command contract.

### fn `def cmd_lm(extra)` (L5314-5317)
- @brief Execute `cmd_lm` runtime logic for Git-Alias CLI.
- @details Executes `cmd_lm` using deterministic CLI control-flow and explicit error propagation.
- @param extra Input parameter consumed by `cmd_lm`.
- @return Result emitted by `cmd_lm` according to command contract.

### fn `def cmd_ls(extra)` (L5323-5326)
- @brief Execute `cmd_ls` runtime logic for Git-Alias CLI.
- @details Executes `cmd_ls` using deterministic CLI control-flow and explicit error propagation.
- @param extra Input parameter consumed by `cmd_ls`.
- @return Result emitted by `cmd_ls` according to command contract.
- @satisfies REQ-079

### fn `def cmd_lsi(extra)` (L5344-5364)
- @brief Execute `cmd_lsi` runtime logic for Git-Alias CLI.
- @brief Execute `cmd_lsi` runtime logic for Git-Alias CLI.
- @details Runs `git ls-files --others --ignored --exclude-standard` and filters
output by excluding paths where any path component matches any entry in
`LSI_DEFAULT_EXCLUDED_DIRS` (exact match) or ends with any suffix in
`LSI_DEFAULT_EXCLUDED_DIR_SUFFIXES` (suffix match). When `--include-all`
is present in @p extra, both filtering mechanisms are bypassed and all
output is printed. Additional arguments are forwarded to the underlying
git command unchanged. Exact-match uses `frozenset.intersection` for
O(min(n,m)) lookup per line; suffix-match iterates path components
against the suffix tuple via `str.endswith`.
- @details Executes `cmd_lsi` using deterministic CLI control-flow and explicit error propagation.
- @param extra List[str] CLI arguments passed after the alias name.
- @param extra Input parameter consumed by `cmd_lsi`.
- @return None. Filtered output is printed to stdout.
- @return Result emitted by `cmd_lsi` according to command contract.
- @satisfies REQ-080, REQ-121

### fn `def cmd_lsa(extra)` (L5370-5373)
- @brief Execute `cmd_lsa` runtime logic for Git-Alias CLI.
- @details Executes `cmd_lsa` using deterministic CLI control-flow and explicit error propagation.
- @param extra Input parameter consumed by `cmd_lsa`.
- @return Result emitted by `cmd_lsa` according to command contract.
- @satisfies REQ-081

### fn `def cmd_lt(extra)` (L5379-5398)
- @brief Execute `cmd_lt` runtime logic for Git-Alias CLI.
- @details Enumerates tags via `git tag -l`, resolves containing refs via `git branch -a --contains <tag>`,
trims branch markers/prefixes from git output, and prints deterministic `<tag>: <branch_1>, <branch_2>, ...` lines.
- @param extra Input parameter consumed by `cmd_lt`.
- @return Result emitted by `cmd_lt` according to command contract.

### fn `def cmd_me(extra)` (L5403-5406)
- @brief Execute `cmd_me` runtime logic for Git-Alias CLI.
- @details Executes `cmd_me` using deterministic CLI control-flow and explicit error propagation.
- @param extra Input parameter consumed by `cmd_me`.
- @return Result emitted by `cmd_me` according to command contract.

### fn `def cmd_pl(extra)` (L5411-5414)
- @brief Execute `cmd_pl` runtime logic for Git-Alias CLI.
- @details Executes `cmd_pl` using deterministic CLI control-flow and explicit error propagation.
- @param extra Input parameter consumed by `cmd_pl`.
- @return Result emitted by `cmd_pl` according to command contract.

### fn `def cmd_pt(extra)` (L5419-5422)
- @brief Execute `cmd_pt` runtime logic for Git-Alias CLI.
- @details Executes `cmd_pt` using deterministic CLI control-flow and explicit error propagation.
- @param extra Input parameter consumed by `cmd_pt`.
- @return Result emitted by `cmd_pt` according to command contract.

### fn `def cmd_pu(extra)` (L5427-5430)
- @brief Execute `cmd_pu` runtime logic for Git-Alias CLI.
- @details Executes `cmd_pu` using deterministic CLI control-flow and explicit error propagation.
- @param extra Input parameter consumed by `cmd_pu`.
- @return Result emitted by `cmd_pu` according to command contract.

### fn `def cmd_rf(extra)` (L5435-5438)
- @brief Execute `cmd_rf` runtime logic for Git-Alias CLI.
- @details Executes `cmd_rf` using deterministic CLI control-flow and explicit error propagation.
- @param extra Input parameter consumed by `cmd_rf`.
- @return Result emitted by `cmd_rf` according to command contract.

### fn `def cmd_rmtg(extra)` (L5443-5453)
- @brief Execute `cmd_rmtg` runtime logic for Git-Alias CLI.
- @details Executes `cmd_rmtg` using deterministic CLI control-flow and explicit error propagation.
- @param extra Input parameter consumed by `cmd_rmtg`.
- @return Result emitted by `cmd_rmtg` according to command contract.

### fn `def cmd_rmloc(extra)` (L5458-5461)
- @brief Execute `cmd_rmloc` runtime logic for Git-Alias CLI.
- @details Executes `cmd_rmloc` using deterministic CLI control-flow and explicit error propagation.
- @param extra Input parameter consumed by `cmd_rmloc`.
- @return Result emitted by `cmd_rmloc` according to command contract.

### fn `def cmd_rmstg(extra)` (L5466-5469)
- @brief Execute `cmd_rmstg` runtime logic for Git-Alias CLI.
- @details Executes `cmd_rmstg` using deterministic CLI control-flow and explicit error propagation.
- @param extra Input parameter consumed by `cmd_rmstg`.
- @return Result emitted by `cmd_rmstg` according to command contract.

### fn `def cmd_rmunt(extra)` (L5474-5477)
- @brief Execute `cmd_rmunt` runtime logic for Git-Alias CLI.
- @details Executes `cmd_rmunt` using deterministic CLI control-flow and explicit error propagation.
- @param extra Input parameter consumed by `cmd_rmunt`.
- @return Result emitted by `cmd_rmunt` according to command contract.

### fn `def cmd_rs(extra)` (L5482-5485)
- @brief Execute `cmd_rs` runtime logic for Git-Alias CLI.
- @details Executes `cmd_rs` using deterministic CLI control-flow and explicit error propagation.
- @param extra Input parameter consumed by `cmd_rs`.
- @return Result emitted by `cmd_rs` according to command contract.

### fn `def cmd_rssft(extra)` (L5490-5493)
- @brief Execute `cmd_rssft` runtime logic for Git-Alias CLI.
- @details Executes `cmd_rssft` using deterministic CLI control-flow and explicit error propagation.
- @param extra Input parameter consumed by `cmd_rssft`.
- @return Result emitted by `cmd_rssft` according to command contract.

### fn `def cmd_rsmix(extra)` (L5498-5501)
- @brief Execute `cmd_rsmix` runtime logic for Git-Alias CLI.
- @details Executes `cmd_rsmix` using deterministic CLI control-flow and explicit error propagation.
- @param extra Input parameter consumed by `cmd_rsmix`.
- @return Result emitted by `cmd_rsmix` according to command contract.

### fn `def cmd_rshrd(extra)` (L5506-5509)
- @brief Execute `cmd_rshrd` runtime logic for Git-Alias CLI.
- @details Executes `cmd_rshrd` using deterministic CLI control-flow and explicit error propagation.
- @param extra Input parameter consumed by `cmd_rshrd`.
- @return Result emitted by `cmd_rshrd` according to command contract.

### fn `def cmd_rsmrg(extra)` (L5514-5517)
- @brief Execute `cmd_rsmrg` runtime logic for Git-Alias CLI.
- @details Executes `cmd_rsmrg` using deterministic CLI control-flow and explicit error propagation.
- @param extra Input parameter consumed by `cmd_rsmrg`.
- @return Result emitted by `cmd_rsmrg` according to command contract.

### fn `def cmd_rskep(extra)` (L5522-5525)
- @brief Execute `cmd_rskep` runtime logic for Git-Alias CLI.
- @details Executes `cmd_rskep` using deterministic CLI control-flow and explicit error propagation.
- @param extra Input parameter consumed by `cmd_rskep`.
- @return Result emitted by `cmd_rskep` according to command contract.

### fn `def cmd_st(extra)` (L5530-5533)
- @brief Execute `cmd_st` runtime logic for Git-Alias CLI.
- @details Executes `cmd_st` using deterministic CLI control-flow and explicit error propagation.
- @param extra Input parameter consumed by `cmd_st`.
- @return Result emitted by `cmd_st` according to command contract.

### fn `def cmd_tg(extra)` (L5538-5541)
- @brief Execute `cmd_tg` runtime logic for Git-Alias CLI.
- @details Executes `cmd_tg` using deterministic CLI control-flow and explicit error propagation.
- @param extra Input parameter consumed by `cmd_tg`.
- @return Result emitted by `cmd_tg` according to command contract.

### fn `def cmd_unstg(extra)` (L5546-5549)
- @brief Execute `cmd_unstg` runtime logic for Git-Alias CLI.
- @details Executes `cmd_unstg` using deterministic CLI control-flow and explicit error propagation.
- @param extra Input parameter consumed by `cmd_unstg`.
- @return Result emitted by `cmd_unstg` according to command contract.

### fn `def cmd_wt(extra)` (L5559-5562)
- @brief Dispatch raw `git worktree` subcommands through alias `wt`.
- @details Delegates to native `git worktree` so subcommands such as `list`,
`add`, and `prune` remain reachable through the alias. Forwards every
operand unchanged and performs no CLI-side interpretation before subprocess
execution.
- @param extra {List[str] | None} CLI operands appended after `git worktree`.
- @return Result emitted by `run_git_cmd` for the delegated git subprocess.
- @note Complexity: O(1) excluding delegated git process runtime.
- @satisfies REQ-074

### fn `def cmd_wtl(extra)` (L5572-5575)
- @brief Dispatch dedicated `git worktree list` behavior through alias `wtl`.
- @details Delegates to native `git worktree list` while preserving every user
operand unchanged, including verbosity and porcelain flags handled by git
itself.
- @param extra {List[str] | None} CLI operands appended after
`git worktree list`.
- @return Result emitted by `run_git_cmd` for the delegated git subprocess.
- @note Complexity: O(1) excluding delegated git process runtime.
- @satisfies REQ-074, REQ-075

### fn `def cmd_wtp(extra)` (L5580-5583)
- @brief Execute `cmd_wtp` runtime logic for Git-Alias CLI.
- @details Executes `cmd_wtp` using deterministic CLI control-flow and explicit error propagation.
- @param extra Input parameter consumed by `cmd_wtp`.
- @return Result emitted by `cmd_wtp` according to command contract.

### fn `def cmd_wtd(extra)` (L5592-5618)
- @brief Execute `cmd_wtd` runtime logic for Git-Alias CLI.
- @details Accepts one worktree target with optional `--force`, resolves worktree associations,
deletes an associated worktree before deleting the branch, and uses forced git delete
flags only when explicitly requested.
- @param extra `list | None` — requires exactly one worktree target or `--help`.
- @return Return value from `run_git_cmd` when only the worktree is deleted; otherwise `None`.
- @exception SystemExit Exit code 1 on invalid operands or preflight failure.
- @satisfies REQ-077, REQ-139, REQ-140, REQ-141, REQ-142, REQ-143, REQ-144, REQ-145

### fn `def cmd_ver(extra)` (L5623-5649)
- @brief Execute `cmd_ver` runtime logic for Git-Alias CLI.
- @details Executes `cmd_ver` using deterministic CLI control-flow and explicit error propagation.
- @param extra Input parameter consumed by `cmd_ver`.
- @return Result emitted by `cmd_ver` according to command contract.

### fn `def cmd_chver(extra)` (L5654-5737)
- @brief Execute `cmd_chver` runtime logic for Git-Alias CLI.
- @details Executes `cmd_chver` using deterministic CLI control-flow and explicit error propagation.
- @param extra Input parameter consumed by `cmd_chver`.
- @return Result emitted by `cmd_chver` according to command contract.

### fn `def cmd_major(extra)` (L5751-5758)
- @brief CLI entry-point for the `major` release subcommand.
- @details Increments the major semver index (resets minor and patch to 0), merges and pushes
to both configured `develop` and `master` branches, regenerates changelog via a
temporary local tag on `work`, and creates the definitive release tag on `master`
before publication; pushes develop alone, then master and the exact tag atomically.
`--dev`/`--develop` limits the workflow to configured `develop` (REQ-045, REQ-200).
Standalone --resume, optionally with --dev/--develop, validates and publishes
existing release objects unchanged.
- @param extra {List[str] | None} CLI argument strings; accepted flags: `--include-patch`,
`--dev`/`--develop` (REQ-200), `--exec <command> [params...]` (REQ-166).
- @return None; delegates to `_run_release_command("major", ...)`.
- @exception SystemExit Exit code 1 on invalid operands or release-flow failure.
- @satisfies REQ-026, REQ-045, REQ-072, REQ-166, REQ-167, REQ-168, REQ-200

### fn `def cmd_minor(extra)` (L5772-5779)
- @brief CLI entry-point for the `minor` release subcommand.
- @details Increments the minor semver index (resets patch to 0), merges and pushes to both
configured `develop` and `master` branches, regenerates changelog via a temporary local
tag on `work`, and creates the definitive release tag on `master` immediately before
publication; pushes develop alone, then master and the exact tag atomically.
`--dev`/`--develop` limits the workflow to configured `develop` (REQ-045, REQ-200).
Standalone --resume, optionally with --dev/--develop, validates and publishes
existing release objects unchanged.
- @param extra {List[str] | None} CLI argument strings; accepted flags: `--include-patch`,
`--dev`/`--develop` (REQ-200), `--exec <command> [params...]` (REQ-166).
- @return None; delegates to `_run_release_command("minor", ...)`.
- @exception SystemExit Exit code 1 on invalid operands or release-flow failure.
- @satisfies REQ-026, REQ-045, REQ-072, REQ-166, REQ-167, REQ-168, REQ-200

### fn `def cmd_patch(extra)` (L5793-5800)
- @brief CLI entry-point for the `patch` release subcommand.
- @details Increments the patch semver index and runs the same default workflow as `major`
and `minor`: integrates work/develop/master, tags configured `master`, pushes
develop alone, then master and the exact tag atomically (REQ-072).
`--dev`/`--develop` limits the workflow to configured `develop` (REQ-045, REQ-200);
--include-patch is auto-included in the changelog regeneration step.
Standalone --resume, optionally with --dev/--develop, validates and publishes
existing release objects unchanged.
- @param extra {List[str] | None} CLI argument strings; accepted flags: `--include-patch`,
`--dev`/`--develop` (REQ-200), `--exec <command> [params...]` (REQ-166).
- @return None; delegates to `_run_release_command("patch", ...)`.
- @exception SystemExit Exit code 1 on invalid operands or release-flow failure.
- @satisfies REQ-026, REQ-045, REQ-072, REQ-166, REQ-167, REQ-168, REQ-200

### fn `def cmd_backup(extra)` (L5808-5818)
- @brief CLI entry-point for the `backup` workflow subcommand.
- @details Runs the same preflight checks used by `major`/`minor`/`patch`, then integrates the
configured `work` branch into the configured `develop` branch and pushes `develop`
to its remote tracking branch before returning to `work`.
- @param extra Iterable of CLI argument strings; accepted token: `--help` only.
- @return None; delegates to `_run_backup_command()`.
- @satisfies REQ-047, REQ-048, REQ-049

### fn `def cmd_changelog(extra)` (L5828-5865)
- @brief CLI entry-point for the `changelog` subcommand.
- @details Parses flags, delegates to `generate_changelog_document`, and writes or prints the result.
Accepted flags: `--include-patch`, `--force-write`, `--print-only`,
`--disable-history`, `--help`.
Exits with status 2 on argument errors or when not inside a git repository.
Exits with status 1 when `CHANGELOG.md` already exists and `--force-write` was not supplied.
- @param extra Iterable of CLI argument strings following the `changelog` subcommand token.
- @return None; side-effects: writes `CHANGELOG.md` to disk or prints to stdout.
- @satisfies REQ-018, REQ-040, REQ-041, REQ-043

- var `COMMANDS = {` (L5868)
- @brief Constant `COMMANDS` used by CLI runtime paths and policies.
### fn `def print_command_help(name, width=None)` (L5957-5964)
- @brief Execute `print_command_help` runtime logic for Git-Alias CLI.
- @details Executes `print_command_help` using deterministic CLI control-flow and explicit error propagation.
- @param name Input parameter consumed by `print_command_help`.
- @param width Input parameter consumed by `print_command_help`.
- @return Result emitted by `print_command_help` according to command contract.

### fn `def print_all_help()` (L5968-6002)
- @brief Execute `print_all_help` runtime logic for Git-Alias CLI.
- @details Executes `print_all_help` using deterministic CLI control-flow and explicit error propagation.
- @return Result emitted by `print_all_help` according to command contract.

### fn `def main(argv=None, *, check_updates: bool = True)` (L6015-6094)
- @brief Execute `main` runtime logic for Git-Alias CLI.
- @details Executes `main` using deterministic CLI control-flow and explicit error propagation.
Management dispatch: `--ver`/`--version` prints the installed version
plus the latest PyPI and GitHub versions (REQ-202); `--upgrade`
selects the PyPI default source or the GitHub source via
`--develop` (equivalent `--dev`) (REQ-001, REQ-201) and rejects
`--develop`/`--dev` outside `--upgrade`/`major`/`minor`/`patch`
(REQ-203).
- @param argv Input parameter consumed by `main`.
- @param check_updates Input parameter consumed by `main`.
- @return Result emitted by `main` according to command contract.
- @satisfies REQ-001, REQ-030, REQ-201, REQ-202, REQ-203, REQ-230

## Symbol Index
|Symbol|Kind|Vis|Lines|Sig|
|---|---|---|---|---|
|`CONFIG_FILENAME`|var|pub|33||
|`GLOBAL_CONFIG_DIRECTORY`|var|pub|39||
|`GLOBAL_CONFIG_FILENAME`|var|pub|41||
|`UV_TOOL_NAME`|var|pub|48||
|`PYPI_PROJECT_NAME`|var|pub|56||
|`PYPI_LATEST_VERSION_API`|var|pub|62||
|`GITHUB_REPOSITORY`|var|pub|68||
|`GITHUB_LATEST_RELEASE_API`|var|pub|77||
|`GITHUB_UPGRADE_SOURCE`|var|pub|86||
|`UV_TOOL_UPGRADE_COMMAND`|var|pub|93||
|`UV_TOOL_UNINSTALL_COMMAND`|var|pub|101||
|`VERSION_CHECK_CACHE_FILE`|var|pub|104||
|`VERSION_CHECK_IDLE_DELAY_SECONDS`|var|pub|111||
|`VERSION_CHECK_ERROR_IDLE_DELAY_SECONDS`|var|pub|113||
|`VERSION_CHECK_TIMEOUT_SECONDS`|var|pub|115||
|`VERSION_AVAILABLE_COLOR`|var|pub|117||
|`VERSION_ERROR_COLOR`|var|pub|119||
|`ANSI_COLOR_RESET`|var|pub|121||
|`DEFAULT_VER_RULES`|var|pub|125||
|`VERSION_CLEANUP_REGEXES`|var|pub|132||
|`VERSION_CLEANUP_PATTERNS`|var|pub|143||
|`ANSI_ESCAPE_RE`|var|pub|144||
|`DEFAULT_GP_COMMAND`|var|pub|150||
|`DEFAULT_GR_COMMAND`|var|pub|155||
|`GIT_DIFFTOOL_COMMAND`|var|pub|160||
|`DEFAULT_CONFIG`|var|pub|171||
|`CONFIG`|var|pub|196||
|`BRANCH_KEYS`|var|pub|199||
|`LOCAL_CONFIG_KEYS`|var|pub|201||
|`GLOBAL_CONFIG_KEYS`|var|pub|209||
|`MANAGEMENT_HELP`|var|pub|221||
|`get_config_value`|fn|pub|238-241|def get_config_value(name)|
|`get_branch`|fn|pub|246-251|def get_branch(name)|
|`get_editor`|fn|pub|255-258|def get_editor()|
|`_load_config_rules`|fn|priv|267-294|def _load_config_rules(key, fallback)|
|`get_version_rules`|fn|pub|298-301|def get_version_rules()|
|`get_cli_version`|fn|pub|305-316|def get_cli_version()|
|`_normalize_semver_text`|fn|priv|321-327|def _normalize_semver_text(text: str) -> str|
|`_print_update_available_warning`|fn|priv|336-338|def _print_update_available_warning(|
|`_print_update_check_error`|fn|priv|356-362|def _print_update_check_error(detail: str) -> None|
|`_resolve_release_api_url`|fn|priv|369-373|def _resolve_release_api_url(repo_root: Path) -> str|
|`_coerce_unix_timestamp`|fn|priv|379-384|def _coerce_unix_timestamp(value: object) -> Optional[int]|
|`_write_version_check_state`|fn|priv|393-396|def _write_version_check_state(|
|`_write_version_check_error_state`|fn|priv|431-433|def _write_version_check_error_state(|
|`check_for_newer_version`|fn|pub|457-461|def check_for_newer_version(|
|`_build_github_upgrade_command`|fn|priv|587-598|def _build_github_upgrade_command(tag: str) -> Tuple[str,...|
|`_github_failure_reason`|fn|priv|614-635|def _github_failure_reason(exc: BaseException) -> str|
|`_fetch_github_release_tag_with_reason`|fn|priv|653-654|def _fetch_github_release_tag_with_reason(|
|`_fetch_github_latest_release_tag`|fn|priv|701-702|def _fetch_github_latest_release_tag(|
|`_fetch_github_latest_version`|fn|priv|729-730|def _fetch_github_latest_version(|
|`get_git_root`|fn|pub|751-766|def get_git_root()|
|`get_config_path`|fn|pub|771-775|def get_config_path(root=None)|
|`get_global_config_path`|fn|pub|780-784|def get_global_config_path(home=None)|
|`_read_config_object`|fn|priv|789-807|def _read_config_object(config_path)|
|`_apply_config_values`|fn|priv|813-835|def _apply_config_values(data, keys)|
|`load_cli_config`|fn|pub|841-853|def load_cli_config(root=None, home=None)|
|`_write_missing_config_values`|fn|priv|867-915|def _write_missing_config_values(config_path, keys, creat...|
|`write_default_config`|fn|pub|921-934|def write_default_config(root=None, home=None)|
|`_parse_config_command_parts`|fn|priv|944-955|def _parse_config_command_parts(command_line: str, config...|
|`_find_windows_shell_script_path`|fn|priv|964-987|def _find_windows_shell_script_path(executable: str) -> O...|
|`_resolve_windows_shell_command_prefix`|fn|priv|997-1006|def _resolve_windows_shell_command_prefix(executable: str...|
|`_validated_config_command_parts`|fn|priv|1017-1030|def _validated_config_command_parts(key: str, default_com...|
|`_is_graphical_environment`|fn|priv|1038-1043|def _is_graphical_environment() -> bool|
|`_environment_config_command_parts`|fn|priv|1056-1057|def _environment_config_command_parts(|
|`_editor_base_command`|fn|priv|1075-1080|def _editor_base_command() -> List[str]|
|`run_editor_command`|fn|pub|1087-1090|def run_editor_command(args)|
|`_config_command_parts`|fn|priv|1101-1104|def _config_command_parts(key: str, default_command: str)...|
|`HELP_TEXTS`|var|pub|1107||
|`RESET_HELP_COMMANDS`|var|pub|1274||
|`LSI_DEFAULT_EXCLUDED_DIRS`|var|pub|1280||
|`LSI_DEFAULT_EXCLUDED_DIR_SUFFIXES`|var|pub|1317||
|`_to_args`|fn|priv|1324-1327|def _to_args(extra)|
|`CommandExecutionError`|class|pub|1330-1371|class CommandExecutionError(RuntimeError)|
|`CommandExecutionError.__init__`|fn|priv|1335-1342|def __init__(self, exc: subprocess.CalledProcessError)|
|`CommandExecutionError._format_message`|fn|priv|1346-1356|def _format_message(self) -> str|
|`CommandExecutionError._decode_stream`|fn|priv|1361-1371|def _decode_stream(data) -> str|
|`_run_checked`|fn|priv|1386-1401|def _run_checked(*popenargs, stream=False, **kwargs) -> Any|
|`VersionDetectionError`|class|pub|1404-1407|class VersionDetectionError(RuntimeError)|
|`ReleaseError`|class|pub|1410-1413|class ReleaseError(RuntimeError)|
|`run_git_cmd`|fn|pub|1421-1425|def run_git_cmd(base_args, extra=None, cwd=None, **kwargs)|
|`capture_git_output`|fn|pub|1431-1437|def capture_git_output(base_args, cwd=None)|
|`run_command`|fn|pub|1443-1446|def run_command(cmd, cwd=None)|
|`run_git_text`|fn|pub|1453-1470|def run_git_text(args, cwd=None, check=True)|
|`run_shell`|fn|pub|1476-1479|def run_shell(command, cwd=None)|
|`_git_status_lines`|fn|priv|1483-1495|def _git_status_lines()|
|`has_unstaged_changes`|fn|pub|1500-1511|def has_unstaged_changes(status_lines=None)|
|`has_staged_changes`|fn|pub|1516-1525|def has_staged_changes(status_lines=None)|
|`WIP_MESSAGE_RE`|var|pub|1531||
|`_refresh_remote_refs`|fn|priv|1546-1558|def _refresh_remote_refs()|
|`_branch_remote_divergence`|fn|priv|1564-1584|def _branch_remote_divergence(branch_key, remote="origin")|
|`has_remote_branch_updates`|fn|pub|1590-1594|def has_remote_branch_updates(branch_key, remote="origin")|
|`has_remote_develop_updates`|fn|pub|1598-1601|def has_remote_develop_updates()|
|`has_remote_master_updates`|fn|pub|1605-1608|def has_remote_master_updates()|
|`_head_commit_message`|fn|priv|1612-1618|def _head_commit_message()|
|`_head_commit_hash`|fn|priv|1622-1628|def _head_commit_hash()|
|`_commit_exists_in_branch`|fn|priv|1634-1646|def _commit_exists_in_branch(commit_hash, branch_name)|
|`_should_amend_existing_commit`|fn|priv|1650-1665|def _should_amend_existing_commit()|
|`is_inside_git_repo`|fn|pub|1669-1676|def is_inside_git_repo()|
|`TagInfo`|class|pub|1681-1689|class TagInfo|
|`WorktreeInfo`|class|pub|1694-1700|class WorktreeInfo|
|`DELIM`|var|pub|1703||
|`RECORD`|var|pub|1706||
|`SEMVER_RE`|var|pub|1722||
|`SECTION_EMOJI`|var|pub|1725||
|`_tag_semver_tuple`|fn|priv|1743-1746|def _tag_semver_tuple(tag_name: str) -> Optional[Tuple[in...|
|`_latest_supported_tag_name`|fn|priv|1751-1754|def _latest_supported_tag_name(tags: List[TagInfo]) -> Op...|
|`_is_minor_release_tag`|fn|priv|1762-1769|def _is_minor_release_tag(tag_name: str) -> bool|
|`_latest_patch_tag_after`|fn|priv|1778-1779|def _latest_patch_tag_after(|
|`list_tags_sorted_by_date`|fn|pub|1797-1798|def list_tags_sorted_by_date(|
|`git_log_subjects`|fn|pub|1828-1839|def git_log_subjects(repo_root: Path, rev_range: str) -> ...|
|`parse_conventional_commit`|fn|pub|1845-1846|def parse_conventional_commit(|
|`_format_changelog_description`|fn|priv|1877-1900|def _format_changelog_description(desc: str) -> List[str]|
|`categorize_commit`|fn|pub|1918-1947|def categorize_commit(subject: str) -> Tuple[Optional[str...|
|`_extract_release_version`|fn|priv|1952-1962|def _extract_release_version(subject: str) -> Optional[str]|
|`_is_release_marker_commit`|fn|priv|1967-1970|def _is_release_marker_commit(subject: str) -> bool|
|`generate_section_for_range`|fn|pub|1979-1984|def generate_section_for_range(|
|`_get_remote_name_for_branch`|fn|priv|2032-2040|def _get_remote_name_for_branch(branch_name: str, repo_ro...|
|`_extract_owner_repo`|fn|priv|2048-2072|def _extract_owner_repo(remote_url: str) -> Optional[Tupl...|
|`_canonical_origin_base`|fn|priv|2082-2097|def _canonical_origin_base(repo_root: Path) -> Optional[str]|
|`get_origin_compare_url`|fn|pub|2104-2105|def get_origin_compare_url(|
|`get_release_page_url`|fn|pub|2119-2124|def get_release_page_url(base_url: Optional[str], tag: st...|
|`build_history_section`|fn|pub|2132-2136|def build_history_section(|
|`generate_changelog_document`|fn|pub|2186-2187|def generate_changelog_document(|
|`VersionRuleContext`|class|pub|2259-2266|class VersionRuleContext|
|`_normalize_version_rule_pattern`|fn|priv|2274-2285|def _normalize_version_rule_pattern(pattern: str) -> str|
|`_split_negation_pattern`|fn|priv|2292-2298|def _split_negation_pattern(pattern: str) -> Tuple[bool, ...|
|`_version_pathspec_matches`|fn|priv|2306-2316|def _version_pathspec_matches(spec, normalized_pattern: s...|
|`_build_version_negation_specs`|fn|priv|2325-2339|def _build_version_negation_specs(rules) -> List|
|`_version_path_is_negated`|fn|priv|2347-2353|def _version_path_is_negated(relative: str, negation_spec...|
|`_build_version_file_inventory`|fn|priv|2359-2386|def _build_version_file_inventory(root: Path) -> List[Tup...|
|`_collect_version_files`|fn|priv|2397-2415|def _collect_version_files(root, pattern, *, inventory=No...|
|`_is_version_path_excluded`|fn|priv|2420-2423|def _is_version_path_excluded(relative_path: str) -> bool|
|`_iter_versions_in_text`|fn|priv|2429-2440|def _iter_versions_in_text(text, compiled_regexes)|
|`_read_version_file_text`|fn|priv|2447-2448|def _read_version_file_text(|
|`_prepare_version_rule_contexts`|fn|priv|2475-2476|def _prepare_version_rule_contexts(|
|`_determine_canonical_version`|fn|priv|2527-2534|def _determine_canonical_version(|
|`_parse_semver_tuple`|fn|priv|2587-2593|def _parse_semver_tuple(text: str) -> Optional[Tuple[int,...|
|`_replace_versions_in_text`|fn|priv|2600-2615|def _replace_versions_in_text(text, compiled_regex, repla...|
|`_current_branch_name`|fn|priv|2619-2631|def _current_branch_name()|
|`_ref_exists`|fn|priv|2636-2645|def _ref_exists(ref_name)|
|`_local_branch_exists`|fn|priv|2650-2653|def _local_branch_exists(branch_name)|
|`_remote_branch_exists`|fn|priv|2658-2661|def _remote_branch_exists(branch_name)|
|`_list_worktree_associations`|fn|priv|2669-2694|def _list_worktree_associations() -> List[WorktreeInfo]|
|`_find_worktree_for_branch`|fn|priv|2702-2703|def _find_worktree_for_branch(|
|`_find_association_for_worktree`|fn|priv|2718-2719|def _find_association_for_worktree(|
|`_parse_bd_target`|fn|priv|2735-2749|def _parse_bd_target(args: List[str]) -> Tuple[str, bool]|
|`_parse_wtd_target`|fn|priv|2757-2771|def _parse_wtd_target(args: List[str]) -> Tuple[str, bool]|
|`_preflight_branch_delete`|fn|priv|2781-2812|def _preflight_branch_delete(branch_name: str, alias: str...|
|`_preflight_worktree_delete`|fn|priv|2822-2850|def _preflight_worktree_delete(worktree_path: Path, alias...|
|`_print_paired_delete_success`|fn|priv|2858-2862|def _print_paired_delete_success(worktree_path: Path, bra...|
|`_delete_associated_branch_and_worktree`|fn|priv|2873-2874|def _delete_associated_branch_and_worktree(|
|`_ensure_release_prerequisites`|fn|priv|2903-2956|def _ensure_release_prerequisites()|
|`_bump_semver_version`|fn|priv|2962-2982|def _bump_semver_version(current_version, level)|
|`_run_release_step`|fn|priv|2989-3015|def _run_release_step(level, step_name, action)|
|`_create_release_commit_for_flow`|fn|priv|3020-3025|def _create_release_commit_for_flow(target_version)|
|`_push_release_refs`|fn|priv|3045-3074|def _push_release_refs(level, version, branch, include_br...|
|`_resume_release_flow`|fn|priv|3089-3165|def _resume_release_flow(level, dev_release=False)|
|`_execute_release_flow`|fn|priv|3190-3289|def _execute_release_flow(level, changelog_args=None, exe...|
|`_execute_backup_flow`|fn|priv|3297-3314|def _execute_backup_flow()|
|`_run_release_command`|fn|priv|3329-3353|def _run_release_command(level, changelog_args=None, exec...|
|`_run_backup_command`|fn|priv|3358-3365|def _run_backup_command()|
|`_run_reset_with_help`|fn|priv|3371-3378|def _run_reset_with_help(base_args, extra)|
|`_reject_extra_arguments`|fn|priv|3384-3390|def _reject_extra_arguments(extra, alias)|
|`_parse_release_flags`|fn|priv|3412-3464|def _parse_release_flags(extra, alias)|
|`_prepare_commit_message`|fn|priv|3470-3480|def _prepare_commit_message(extra, alias)|
|`_normalize_conventional_description`|fn|priv|3487-3497|def _normalize_conventional_description(description: str)...|
|`_build_conventional_message`|fn|priv|3506-3527|def _build_conventional_message(kind: str, extra, alias: ...|
|`_run_conventional_commit`|fn|priv|3545-3550|def _run_conventional_commit(kind: str, alias: str, extra)|
|`_execute_commit`|fn|priv|3557-3589|def _execute_commit(message, alias, allow_amend=True)|
|`_ensure_clean_worktree_and_index`|fn|priv|3597-3613|def _ensure_clean_worktree_and_index(alias: str) -> bool|
|`_resolve_rollback_target_commit`|fn|priv|3621-3631|def _resolve_rollback_target_commit(target: str) -> str|
|`_is_commit_ancestor`|fn|priv|3638-3647|def _is_commit_ancestor(ancestor_commit: str, descendant_...|
|`_is_commit_hash_token`|fn|priv|3652-3655|def _is_commit_hash_token(token: str) -> bool|
|`_tag_exists`|fn|priv|3660-3663|def _tag_exists(tag_name: str) -> bool|
|`_abort_rollback_version_restore`|fn|priv|3675-3695|def _abort_rollback_version_restore(failure)|
|`_is_linux_platform`|fn|priv|3700-3703|def _is_linux_platform() -> bool|
|`_print_non_linux_management_command`|fn|priv|3710-3712|def _print_non_linux_management_command(|
|`upgrade_self`|fn|pub|3738-3761|def upgrade_self(repo_root: Optional[Path] = None, github...|
|`_remove_version_check_cache_artifacts`|fn|priv|3768-3789|def _remove_version_check_cache_artifacts() -> None|
|`uninstall_self`|fn|pub|3794-3801|def uninstall_self()|
|`cmd_aa`|fn|pub|3806-3813|def cmd_aa(extra)|
|`cmd_ra`|fn|pub|3818-3841|def cmd_ra(extra)|
|`cmd_ar`|fn|pub|3846-3864|def cmd_ar(extra)|
|`cmd_br`|fn|pub|3869-3872|def cmd_br(extra)|
|`cmd_bd`|fn|pub|3881-3899|def cmd_bd(extra)|
|`cmd_ck`|fn|pub|3904-3907|def cmd_ck(extra)|
|`_ensure_commit_ready`|fn|priv|3912-3925|def _ensure_commit_ready(alias)|
|`_ensure_commit_ready_with_stage`|fn|priv|3943-3957|def _ensure_commit_ready_with_stage(alias)|
|`cmd_cm`|fn|pub|3962-3967|def cmd_cm(extra)|
|`cmd_wip`|fn|pub|3977-3989|def cmd_wip(extra)|
|`cmd_release`|fn|pub|3994-4016|def cmd_release(extra)|
|`cmd_new`|fn|pub|4021-4024|def cmd_new(extra)|
|`cmd_refactor`|fn|pub|4029-4032|def cmd_refactor(extra)|
|`cmd_fix`|fn|pub|4037-4040|def cmd_fix(extra)|
|`cmd_change`|fn|pub|4045-4048|def cmd_change(extra)|
|`cmd_implement`|fn|pub|4053-4056|def cmd_implement(extra)|
|`cmd_docs`|fn|pub|4061-4064|def cmd_docs(extra)|
|`cmd_style`|fn|pub|4069-4072|def cmd_style(extra)|
|`cmd_revert`|fn|pub|4077-4080|def cmd_revert(extra)|
|`cmd_rollback`|fn|pub|4094-4169|def cmd_rollback(extra)|
|`cmd_misc`|fn|pub|4174-4177|def cmd_misc(extra)|
|`cmd_cover`|fn|pub|4182-4185|def cmd_cover(extra)|
|`cmd_co`|fn|pub|4190-4193|def cmd_co(extra)|
|`_selected_diff_command_parts`|fn|priv|4207-4217|def _selected_diff_command_parts() -> List[str]|
|`_run_configured_diff`|fn|priv|4235-4242|def _run_configured_diff(refs, extra=None)|
|`cmd_dc`|fn|pub|4256-4269|def cmd_dc(extra)|
|`cmd_dcc`|fn|pub|4276-4279|def cmd_dcc(extra)|
|`cmd_dccc`|fn|pub|4286-4289|def cmd_dccc(extra)|
|`cmd_de`|fn|pub|4294-4297|def cmd_de(extra)|
|`cmd_di`|fn|pub|4302-4305|def cmd_di(extra)|
|`cmd_diyou`|fn|pub|4310-4313|def cmd_diyou(extra)|
|`cmd_dime`|fn|pub|4318-4321|def cmd_dime(extra)|
|`cmd_dwc`|fn|pub|4328-4331|def cmd_dwc(extra)|
|`cmd_dw`|fn|pub|4340-4347|def cmd_dw(extra)|
|`cmd_dwcc`|fn|pub|4355-4358|def cmd_dwcc(extra)|
|`cmd_dcd`|fn|pub|4365-4370|def cmd_dcd(extra)|
|`cmd_dcm`|fn|pub|4377-4382|def cmd_dcm(extra)|
|`cmd_ddm`|fn|pub|4390-4395|def cmd_ddm(extra)|
|`cmd_ed`|fn|pub|4400-4409|def cmd_ed(extra)|
|`cmd_fe`|fn|pub|4414-4417|def cmd_fe(extra)|
|`cmd_feall`|fn|pub|4422-4425|def cmd_feall(extra)|
|`_execute_get_flow`|fn|priv|4437-4511|def _execute_get_flow()|
|`cmd_get`|fn|pub|4518-4532|def cmd_get(extra)|
|`cmd_gp`|fn|pub|4537-4542|def cmd_gp(extra)|
|`cmd_gr`|fn|pub|4547-4552|def cmd_gr(extra)|
|`OVERVIEW_COLOR_RESET`|var|pub|4554||
|`OVERVIEW_COLOR_SECTION_PURPLE`|var|pub|4556||
|`OVERVIEW_COLOR_AHEAD`|var|pub|4558||
|`OVERVIEW_COLOR_BEHIND`|var|pub|4560||
|`OVERVIEW_COLOR_LABEL`|var|pub|4562||
|`OVERVIEW_COLOR_WHITE`|var|pub|4564||
|`OVERVIEW_COLOR_WHITE_BOLD`|var|pub|4566||
|`OVERVIEW_SECTION_TEMPLATE`|var|pub|4568||
|`OVERVIEW_SUBSECTION_TEMPLATE`|var|pub|4570||
|`OVERVIEW_DISTANCE_TEMPLATE`|var|pub|4572||
|`_overview_branch_identifier`|fn|priv|4581-4584|def _overview_branch_identifier(|
|`_overview_work_prefix_color`|fn|priv|4598-4605|def _overview_work_prefix_color(worktree_state: str) -> str|
|`_overview_logical_branch_name`|fn|priv|4613-4617|def _overview_logical_branch_name(|
|`_overview_current_branch_display`|fn|priv|4636-4641|def _overview_current_branch_display(|
|`_overview_ref_is_available`|fn|priv|4663-4672|def _overview_ref_is_available(ref_name: str) -> bool|
|`_overview_ref_latest_subject`|fn|priv|4678-4688|def _overview_ref_latest_subject(ref_name: str) -> str|
|`_overview_discovered_branch_refs`|fn|priv|4693-4716|def _overview_discovered_branch_refs() -> List[str]|
|`_overview_branch_summary_lines`|fn|priv|4749-4760|def _overview_branch_summary_lines(|
|`_overview_relation_state`|fn|priv|4803-4812|def _overview_relation_state(ahead: int, behind: int) -> str|
|`_overview_worktree_state`|fn|priv|4817-4829|def _overview_worktree_state(status_lines=None) -> str|
|`_overview_distance_text`|fn|priv|4835-4843|def _overview_distance_text(is_ahead: bool, count: int) -...|
|`_overview_compare_refs`|fn|priv|4850-4892|def _overview_compare_refs(base_ref: str, target_ref: str...|
|`_overview_ascii_topology_lines`|fn|priv|4927-4938|def _overview_ascii_topology_lines(|
|`_overview_current_branch_state_lines`|fn|priv|5030-5049|def _overview_current_branch_state_lines(current_branch_d...|
|`cmd_o`|fn|pub|5055-5209|def cmd_o(extra)|
|`cmd_str`|fn|pub|5214-5243|def cmd_str(extra)|
|`cmd_l`|fn|pub|5252-5258|def cmd_l(extra)|
|`cmd_lb`|fn|pub|5263-5266|def cmd_lb(extra)|
|`cmd_lg`|fn|pub|5271-5284|def cmd_lg(extra)|
|`cmd_lh`|fn|pub|5289-5292|def cmd_lh(extra)|
|`cmd_ll`|fn|pub|5297-5309|def cmd_ll(extra)|
|`cmd_lm`|fn|pub|5314-5317|def cmd_lm(extra)|
|`cmd_ls`|fn|pub|5323-5326|def cmd_ls(extra)|
|`cmd_lsi`|fn|pub|5344-5364|def cmd_lsi(extra)|
|`cmd_lsa`|fn|pub|5370-5373|def cmd_lsa(extra)|
|`cmd_lt`|fn|pub|5379-5398|def cmd_lt(extra)|
|`cmd_me`|fn|pub|5403-5406|def cmd_me(extra)|
|`cmd_pl`|fn|pub|5411-5414|def cmd_pl(extra)|
|`cmd_pt`|fn|pub|5419-5422|def cmd_pt(extra)|
|`cmd_pu`|fn|pub|5427-5430|def cmd_pu(extra)|
|`cmd_rf`|fn|pub|5435-5438|def cmd_rf(extra)|
|`cmd_rmtg`|fn|pub|5443-5453|def cmd_rmtg(extra)|
|`cmd_rmloc`|fn|pub|5458-5461|def cmd_rmloc(extra)|
|`cmd_rmstg`|fn|pub|5466-5469|def cmd_rmstg(extra)|
|`cmd_rmunt`|fn|pub|5474-5477|def cmd_rmunt(extra)|
|`cmd_rs`|fn|pub|5482-5485|def cmd_rs(extra)|
|`cmd_rssft`|fn|pub|5490-5493|def cmd_rssft(extra)|
|`cmd_rsmix`|fn|pub|5498-5501|def cmd_rsmix(extra)|
|`cmd_rshrd`|fn|pub|5506-5509|def cmd_rshrd(extra)|
|`cmd_rsmrg`|fn|pub|5514-5517|def cmd_rsmrg(extra)|
|`cmd_rskep`|fn|pub|5522-5525|def cmd_rskep(extra)|
|`cmd_st`|fn|pub|5530-5533|def cmd_st(extra)|
|`cmd_tg`|fn|pub|5538-5541|def cmd_tg(extra)|
|`cmd_unstg`|fn|pub|5546-5549|def cmd_unstg(extra)|
|`cmd_wt`|fn|pub|5559-5562|def cmd_wt(extra)|
|`cmd_wtl`|fn|pub|5572-5575|def cmd_wtl(extra)|
|`cmd_wtp`|fn|pub|5580-5583|def cmd_wtp(extra)|
|`cmd_wtd`|fn|pub|5592-5618|def cmd_wtd(extra)|
|`cmd_ver`|fn|pub|5623-5649|def cmd_ver(extra)|
|`cmd_chver`|fn|pub|5654-5737|def cmd_chver(extra)|
|`cmd_major`|fn|pub|5751-5758|def cmd_major(extra)|
|`cmd_minor`|fn|pub|5772-5779|def cmd_minor(extra)|
|`cmd_patch`|fn|pub|5793-5800|def cmd_patch(extra)|
|`cmd_backup`|fn|pub|5808-5818|def cmd_backup(extra)|
|`cmd_changelog`|fn|pub|5828-5865|def cmd_changelog(extra)|
|`COMMANDS`|var|pub|5868||
|`print_command_help`|fn|pub|5957-5964|def print_command_help(name, width=None)|
|`print_all_help`|fn|pub|5968-6002|def print_all_help()|
|`main`|fn|pub|6015-6094|def main(argv=None, *, check_updates: bool = True)|


---

# foresta.py | Python | 1639L | 34 symbols | 8 imports | 349 comments
> Path: `src/git_alias/foresta.py`

## Imports
```
import os
import re
import signal
import shutil
import subprocess
import sys
from time import localtime, strftime
from typing import Dict, List, Optional, Tuple
```

## Definitions

### fn `def _maxof(x: int, y: int) -> int` `priv` (L134-144)
- @brief Compiled matcher for ANSI SGR escape sequences.
- @brief Return the greater of two integers.
- @details Performs a single conditional comparison and returns the larger operand.
- @param x {int} First operand.
- @param y {int} Second operand.
- @return {int} max(x, y).

### fn `def _round_down2(i: int) -> int` `priv` (L145-156)
- @brief Round down to the nearest even number.
- @details Preserves negative values; for non-negative values clears the least-significant bit.
- @param i {int} Input integer.
- @return {int} Nearest even number <= i; returns i unchanged if negative.

### fn `def _str_expand(s: str, length: int) -> str` `priv` (L157-169)
- @brief Expand string to at least the given length with spaces.
- @details Appends trailing spaces only when the current length is smaller than the target.
- @param s {str} Input string.
- @param length {int} Minimum required length.
- @return {str} String padded with trailing spaces if shorter than length.

### fn `def _remove_trailing_blanks(vine: list) -> None` `priv` (L170-180)
- @brief Remove trailing None entries from vine array in place.
- @details Pops elements from the tail while the last slot is `None`.
- @param vine {list} Column array of expected parent commit IDs.
- @return None. Mutates vine in place.

### fn `def _trgen(` `priv` (L196-201)
- @brief Build a character translation function for graph control codes.
- @details Maps single-character control codes C/M/O/r/t to the configured graph symbols.
Uses a chained replace pipeline because `str.translate` does not support
multi-codepoint replacement targets.
- @param sym_commit {str} Replacement for 'C' (commit marker).
- @param sym_merge {str} Replacement for 'M' (merge marker).
- @param sym_overpass {str} Replacement for 'O' (overpass marker).
- @param sym_root {str} Replacement for 'r' (root marker).
- @param sym_tip {str} Replacement for 't' (tip marker).
- @return {Callable[[str], str]} Translator closure that maps control strings to rendered symbols.

### fn `def translate(s: str) -> str` (L208-215)
- @brief Translate graph control markers into configured symbol glyphs.
- @details Applies deterministic single-character substitutions for commit, merge,
overpass, root, and tip tokens.
- @param s {str} Graph control-string segment to transform.
- @return {str} Transformed control string with configured symbols.

### fn `def _git_command(args: List[str], cwd: Optional[str] = None) -> str` `priv` (L224-243)
- @brief Execute a git command and return stripped stdout.
- @details Invokes `subprocess.run(..., check=True)` and propagates non-zero exits as `CalledProcessError`.
- @param args {List[str]} Git sub-command and arguments.
- @param cwd {Optional[str]} Working directory override.
- @return {str} Stripped stdout text.
- @throws {subprocess.CalledProcessError} On non-zero git exit.

### fn `def _git_command_output_pipe(` `priv` (L249-250)
- @brief Open a git command subprocess with piped stdout for streaming.
- @details Spawns `git <args>` with text-mode stdout/stderr pipes and optional working-directory override.
- @param args {List[str]} Git sub-command tokens forwarded without transformation.
- @param cwd {Optional[str]} Optional command working directory.
- @return {subprocess.Popen} Process handle with readable stdout pipe.

### fn `def _get_status(repo_path: str, git_dir: str) -> str` `priv` (L266-339)
- @brief Determine working tree dirty flags and mid-flow state indicators.
- @details Checks for unstaged, staged, stash, and untracked changes, then probes git internal state files for rebase/merge/cherry-pick/revert/bisect.
- @param repo_path {str} Path to .git directory (or gitdir for worktrees).
- @param git_dir {str} GIT_DIR value used for git commands.
- @return {str} Status string like " *+$%|REBASE-i" or empty.
- @satisfies REQ-106, REQ-107

### fn `def _get_next_pick(lines: List[str], start: int) -> Optional[str]` `priv` (L345-361)
- @brief Parse rebase-todo file lines to find the next pick target.
- @details Skips comments/blank lines and returns the second token from the first actionable row.
- @param lines {List[str]} Lines from git-rebase-todo.
- @param start {int} Starting line index.
- @return {Optional[str]} Short SHA of next pick target, or None.

### fn `def _get_refs(` `priv` (L368-369)
- @brief Build a SHA-to-ref mapping from repository references and HEAD state.
- @details Parses `git show-ref`, resolves annotated tags to target commits, and conditionally
augments the map with active rebase markers (`rebase/next`, `rebase/onto`, `rebase/new`).
- @param show_rebase {bool} Enables inclusion of rebase markers when true.
- @return {Dict[str, List[str]]} Map from full commit SHA to rendered ref labels.
- @satisfies REQ-108

### fn `def _vine_branch(` `priv` (L488-499)
- @brief Draw branch fan topology when a commit SHA appears in multiple vine columns.
- @brief Execute `_vine_branch` graph-processing logic for Foresta rendering.
- @details Scans vine slots for duplicate commit references, emits a branch fan line when needed,
and preserves branch-color continuity via `_vis_post`.
- @details Executes `_vine_branch` as deterministic commit-graph transformation/output logic.
- @param vine {list} Mutable vine columns storing expected parent SHAs.
- @param rev {str} Current commit SHA.
- @param color {Dict[str,str]} ANSI color token map.
- @param hash_width {int} Width of abbreviated hash column.
- @param date_width {int} Width of formatted date column.
- @param graph_margin_left {int} Left-side graph margin.
- @param style {int} Active graph style identifier.
- @param reverse_order {bool} Indicates reverse rendering order.
- @param graph_symbol_tr {Callable[[str], str]} Graph control-code translator.
- @param branch_colors_now {List[str]} Current branch color assignments.
- @param branch_colors_ref {List[str]} Allowed branch color palette.
- @param vine Input parameter consumed by `_vine_branch`.
- @param rev Input parameter consumed by `_vine_branch`.
- @param color Input parameter consumed by `_vine_branch`.
- @param hash_width Input parameter consumed by `_vine_branch`.
- @param date_width Input parameter consumed by `_vine_branch`.
- @param graph_margin_left Input parameter consumed by `_vine_branch`.
- @param style Input parameter consumed by `_vine_branch`.
- @param reverse_order Input parameter consumed by `_vine_branch`.
- @param graph_symbol_tr Input parameter consumed by `_vine_branch`.
- @param branch_colors_now Input parameter consumed by `_vine_branch`.
- @param branch_colors_ref Input parameter consumed by `_vine_branch`.
- @return {Optional[str]} Rendered branch line or None if no duplicate SHA columns exist.
- @return Result emitted by `_vine_branch` according to command contract.
- @satisfies REQ-109

### fn `def _vine_commit(vine: list, rev: str, parents: List[str]) -> str` `priv` (L540-589)
- @brief Draw commit node on the vine graph.
- @details Places the commit at its vine position or allocates a new tip slot. Differentiates commit types: 'C' regular, 'r' root (no parents), M' merge (multiple parents), 't' tip (new branch head).
- @param vine {list} Column array of expected parent IDs.
- @param rev {str} Current commit SHA.
- @param parents {List[str]} Parent commit SHAs.
- @return {str} Control string representing the commit line.
- @satisfies REQ-109

### fn `def _vine_merge(` `priv` (L624-637)
- @brief Draw merge fan topology and update vine state across commit parents.
- @brief Execute `_vine_merge` graph-processing logic for Foresta rendering.
- @details For single-parent commits the vine is only advanced; for merge commits a fan visualization
is generated, using lookahead heuristics to preserve adjacent branch continuity.
- @details Executes `_vine_merge` as deterministic commit-graph transformation/output logic.
- @param vine {list} Mutable vine columns storing expected parent SHAs.
- @param rev {str} Current commit SHA.
- @param next_sha {List[Optional[str]]} Lookahead SHAs used for branch-placement heuristics.
- @param parents {list} Mutable parent SHA list for merge fan rendering.
- @param color {Dict[str,str]} ANSI color token map.
- @param hash_width {int} Width of abbreviated hash column.
- @param date_width {int} Width of formatted date column.
- @param graph_margin_left {int} Left-side graph margin.
- @param style {int} Active graph style identifier.
- @param reverse_order {bool} Indicates reverse rendering order.
- @param graph_symbol_tr {Callable[[str], str]} Graph control-code translator.
- @param branch_colors_now {List[str]} Current branch color assignments.
- @param branch_colors_ref {List[str]} Allowed branch color palette.
- @param vine Input parameter consumed by `_vine_merge`.
- @param rev Input parameter consumed by `_vine_merge`.
- @param next_sha Input parameter consumed by `_vine_merge`.
- @param parents Input parameter consumed by `_vine_merge`.
- @param color Input parameter consumed by `_vine_merge`.
- @param hash_width Input parameter consumed by `_vine_merge`.
- @param date_width Input parameter consumed by `_vine_merge`.
- @param graph_margin_left Input parameter consumed by `_vine_merge`.
- @param style Input parameter consumed by `_vine_merge`.
- @param reverse_order Input parameter consumed by `_vine_merge`.
- @param graph_symbol_tr Input parameter consumed by `_vine_merge`.
- @param branch_colors_now Input parameter consumed by `_vine_merge`.
- @param branch_colors_ref Input parameter consumed by `_vine_merge`.
- @return {Optional[str]} Rendered merge line or None when no explicit merge line is emitted.
- @return Result emitted by `_vine_merge` according to command contract.
- @satisfies REQ-109

### fn `def _vis_commit(s: str, f: Optional[str] = None) -> str` `priv` (L772-785)
- @brief Post-process commit control string.
- @details Trims trailing spaces and appends the optional suffix segment when provided.
- @param s {str} Raw control string from vine_commit.
- @param f {Optional[str]} Optional suffix.
- @return {str} Trimmed control string.

### fn `def _vis_fan(s: str, fan_type: str) -> str` `priv` (L786-860)
- @brief Transform control string for branch/merge fan visualization.
- @details Converts 's' fan markers into directional edge characters, resolves overpass sequences, and performs left/right edge transforms. Normalizes interior spaces between fan markers (`S`/`s`) to preserve continuous connector rendering.
- @param s {str} Raw control string.
- @param fan_type {str} Either "branch" or "merge".
- @return {str} Transformed control string.

### fn `def _overpass_replace(m)` `priv` (L822-824)
- @brief Expand matched overpass control segments to contiguous overpass markers.
- @details Converts regex match groups for `O[DO]+O` into equal-length `O...O` spans.
- @param m {re.Match[str]} Regex match object for the overpass control segment.
- @return {str} Replacement string composed only of `O` markers.

### fn `def _vis_fan2L(left: str) -> str` `priv` (L861-875)
- @brief Transform left side of fan visualization.
- @details Converts the first `s` marker to `e` and remaining `s` markers to `f`, preserving any leading spacing used for vine alignment.
- @param left {str} Left portion of control string.
- @return {str} Transformed left portion.

### fn `def _vis_fan2R(right: str) -> str` `priv` (L876-891)
- @brief Transform right side of fan visualization.
- @details Converts the rightmost `s` marker to `g` and remaining `s` markers to `f`, preserving trailing spacing used for vine alignment.
- @param right {str} Right portion of control string.
- @return {str} Transformed right portion.

### fn `def _vis_xfrm(` `priv` (L924-929)
- @brief Convert graph control-string tokens into styled Unicode output.
- @details Applies optional space-filling after commit markers, reverse-order fan transformation,
style-specific Unicode translation, and final graph-symbol replacement.
- @param s {str} Graph control-string line.
- @param spc {bool} Enables post-commit-space fill when true.
- @param style {int} Style selector (`1`, `2`, `10`, `15`).
- @param reverse_order {bool} Enables reverse fan transformation when true.
- @param graph_symbol_tr {Callable[[str], str]} Control-to-symbol translator function.
- @return {str} Rendered graph line with selected style and symbols.
- @satisfies REQ-101

### fn `def _vis_post(` `priv` (L977-985)
- @brief Post-process graph control strings with style transform and branch coloring.
- @brief Execute `_vis_post` graph-processing logic for Foresta rendering.
- @details Applies `_vis_xfrm` to graph/control suffix segments, preserves ANSI spans, and injects
branch-color-specific commit glyph coloring based on tracked branch state.
- @details Executes `_vis_post` as deterministic commit-graph transformation/output logic.
- @param s {str} Primary graph control string.
- @param f {Optional[str]} Optional suffix containing refs/message text.
- @param style {int} Active graph style identifier.
- @param reverse_order {bool} Indicates reverse rendering order.
- @param graph_symbol_tr {Callable[[str], str]} Graph control-code translator.
- @param color {Dict[str,str]} ANSI color token map (empty in no-color mode).
- @param branch_colors_now {List[str]} Current branch color assignments.
- @param branch_colors_ref {List[str]} Allowed branch color palette.
- @param s Input parameter consumed by `_vis_post`.
- @param f Input parameter consumed by `_vis_post`.
- @param style Input parameter consumed by `_vis_post`.
- @param reverse_order Input parameter consumed by `_vis_post`.
- @param graph_symbol_tr Input parameter consumed by `_vis_post`.
- @param color Input parameter consumed by `_vis_post`.
- @param branch_colors_now Input parameter consumed by `_vis_post`.
- @param branch_colors_ref Input parameter consumed by `_vis_post`.
- @return {str} Final rendered line with style transformation and ANSI colors.
- @return Result emitted by `_vis_post` according to command contract.

### fn `def _update_branch_colors(` `priv` (L1054-1057)
- @brief Update branch-color assignments using current vine control-string content.
- @details Scans even vine slots for branch indicators (`e`, `f`, `g`, `t`) and assigns colors
from the reference palette while avoiding immediate neighbor color collisions.
- @param s {str} Vine control string for the current rendered line.
- @param branch_colors_now {List[str]} Mutable current branch-color assignments.
- @param branch_colors_ref {List[str]} Fixed branch-color palette.
- @return None. Mutates `branch_colors_now` in place.
- @satisfies REQ-110

### fn `def _get_line_block(` `priv` (L1101-1102)
- @brief Read one commit-log line plus bounded lookahead for subvine processing.
- @details Maintains a rolling prefetch buffer and returns the current line with up to
`max_count - 1` subsequent entries for merge lookahead heuristics.
- @param lines_iter {Iterator[str]} Iterator yielding raw git-log lines.
- @param buffer {list} Mutable rolling prefetch buffer.
- @param max_count {int} Maximum total items in returned block.
- @return {Tuple[Optional[str], List[Optional[str]]]} Current line and lookahead list.

### class `class _ReverseOutput` `priv` (L1124-1163)
- @brief Buffer that collects output and writes it in reverse line order.
- @details Used when --reverse is specified. Accumulates all printed output and flushes in reverse order on close().
- fn `def __init__(self, stream)` `priv` (L1131-1138)
  - @brief Buffer that collects output and writes it in reverse line order.
  - @brief Initialize reverse output buffer.
  - @details Used when --reverse is specified. Accumulates all printed output
and flushes in reverse order on close().
  - @param stream Output stream to write reversed content to.
- fn `def write(self, text: str) -> None` (L1139-1145)
  - @brief Accumulate text for later reversed output.
  - @param text {str} Text to buffer.
- fn `def flush(self) -> None` (L1146-1151)
  - @brief No-op flush for buffered mode.
- fn `def close(self) -> None` (L1152-1163)
  - @brief Write buffered content in reverse line order to the stream.

### fn `def _resolve_terminal_columns() -> int` `priv` (L1174-1177)
- @brief Resolve terminal column width for default non-wrapping rendering.
- @details Reads active terminal size using `shutil.get_terminal_size` and enforces
a minimum width of one printable column.
- @return {int} Terminal columns used for line truncation.
- @satisfies REQ-100

### fn `def _truncate_line_to_terminal_width(line: str, terminal_columns: int) -> str` `priv` (L1185-1213)
- @brief Truncate one rendered line to a visible terminal-width budget.
- @details Preserves ANSI escape sequences as zero-width tokens, truncates only
printable glyph columns, and preserves trailing newline semantics.
- @param line {str} Rendered output line with optional ANSI escape sequences.
- @param terminal_columns {int} Maximum number of visible printable columns.
- @return {str} Width-bounded line preserving ANSI tokens and newline suffix.
- @satisfies REQ-100

### fn `def _write_rendered_line(` `priv` (L1222-1225)
- @brief Write one rendered line with optional terminal-width truncation.
- @details Applies width truncation only when `terminal_columns` is provided;
otherwise writes the full input line.
- @param output_stream {IO[str]} Destination stream.
- @param line {str} Rendered output line.
- @param terminal_columns {Optional[int]} Width budget or `None` for wrapping.
- @return None.
- @satisfies REQ-100, REQ-104

### fn `def _process(` `priv` (L1284-1303)
- @brief Stream git log commits, render vine graph lines, and emit final output.
- @brief Execute `_process` graph-processing logic for Foresta rendering.
- @details Opens a `git log` pipe, iterates commits, executes vine_branch/vine_commit/vine_merge
rendering stages, and writes normalized lines to the configured output stream.
- @details Executes `_process` as deterministic commit-graph transformation/output logic.
- @param refs {Dict[str,List[str]]} SHA-to-reference mapping.
- @param status {str} Working-tree status token set.
- @param show_status {bool} Enables status markers in HEAD decorations.
- @param pretty_fmt {str} Git pretty-format expression.
- @param argv {List[str]} Additional passthrough arguments for `git log`.
- @param color {Dict[str,str]} ANSI color token map.
- @param hash_width {int} Width of hash output column.
- @param date_width {int} Width of date output column.
- @param date_format {str} Datetime format string for commit dates.
- @param graph_margin_left {int} Left graph margin width.
- @param graph_margin_right {int} Right graph margin width.
- @param subvine_depth {int} Maximum subvine lookahead depth.
- @param style {int} Active graph style identifier.
- @param reverse_order {bool} Enables reverse commit-output ordering.
- @param graph_symbol_tr {Callable[[str], str]} Graph symbol translator function.
- @param output_stream {IO[str]} Destination stream for rendered lines.
- @param branch_colors_now {List[str]} Mutable current branch-color state.
- @param branch_colors_ref {List[str]} Fixed branch-color palette.
- @param terminal_columns {Optional[int]} Visible-width budget; `None` disables truncation.
- @param refs Input parameter consumed by `_process`.
- @param status Input parameter consumed by `_process`.
- @param show_status Input parameter consumed by `_process`.
- @param pretty_fmt Input parameter consumed by `_process`.
- @param argv Input parameter consumed by `_process`.
- @param color Input parameter consumed by `_process`.
- @param hash_width Input parameter consumed by `_process`.
- @param date_width Input parameter consumed by `_process`.
- @param date_format Input parameter consumed by `_process`.
- @param graph_margin_left Input parameter consumed by `_process`.
- @param graph_margin_right Input parameter consumed by `_process`.
- @param subvine_depth Input parameter consumed by `_process`.
- @param style Input parameter consumed by `_process`.
- @param reverse_order Input parameter consumed by `_process`.
- @param graph_symbol_tr Input parameter consumed by `_process`.
- @param output_stream Input parameter consumed by `_process`.
- @param branch_colors_now Input parameter consumed by `_process`.
- @param branch_colors_ref Input parameter consumed by `_process`.
- @param terminal_columns Input parameter consumed by `_process`.
- @return None.
- @return Result emitted by `_process` according to command contract.
- @satisfies REQ-099, REQ-100, REQ-109

### fn `def _lines_iter()` `priv` (L1320-1324)
- @brief Yield streamed git-log lines from subprocess stdout.
- @details Wraps `proc.stdout` iteration to keep generator creation local to `_process`.
- @return {Iterator[str]} Iterator emitting raw log lines including trailing newlines.

### fn `def run(extra_args: Optional[List[str]] = None) -> None` (L1467-1640)
- @brief Execute the tree visualization command.
- @details Parses command-line options, configures the visualization engine, and runs the main processing loop. Unrecognized options are passed through to git log.
- @param extra_args {Optional[List[str]]} CLI arguments from the dispatcher.
- @return None. Output written to stdout.
- @satisfies REQ-098, REQ-099, REQ-100, REQ-104, REQ-111

## Symbol Index
|Symbol|Kind|Vis|Lines|Sig|
|---|---|---|---|---|
|`_maxof`|fn|priv|134-144|def _maxof(x: int, y: int) -> int|
|`_round_down2`|fn|priv|145-156|def _round_down2(i: int) -> int|
|`_str_expand`|fn|priv|157-169|def _str_expand(s: str, length: int) -> str|
|`_remove_trailing_blanks`|fn|priv|170-180|def _remove_trailing_blanks(vine: list) -> None|
|`_trgen`|fn|priv|196-201|def _trgen(|
|`translate`|fn|pub|208-215|def translate(s: str) -> str|
|`_git_command`|fn|priv|224-243|def _git_command(args: List[str], cwd: Optional[str] = No...|
|`_git_command_output_pipe`|fn|priv|249-250|def _git_command_output_pipe(|
|`_get_status`|fn|priv|266-339|def _get_status(repo_path: str, git_dir: str) -> str|
|`_get_next_pick`|fn|priv|345-361|def _get_next_pick(lines: List[str], start: int) -> Optio...|
|`_get_refs`|fn|priv|368-369|def _get_refs(|
|`_vine_branch`|fn|priv|488-499|def _vine_branch(|
|`_vine_commit`|fn|priv|540-589|def _vine_commit(vine: list, rev: str, parents: List[str]...|
|`_vine_merge`|fn|priv|624-637|def _vine_merge(|
|`_vis_commit`|fn|priv|772-785|def _vis_commit(s: str, f: Optional[str] = None) -> str|
|`_vis_fan`|fn|priv|786-860|def _vis_fan(s: str, fan_type: str) -> str|
|`_overpass_replace`|fn|priv|822-824|def _overpass_replace(m)|
|`_vis_fan2L`|fn|priv|861-875|def _vis_fan2L(left: str) -> str|
|`_vis_fan2R`|fn|priv|876-891|def _vis_fan2R(right: str) -> str|
|`_vis_xfrm`|fn|priv|924-929|def _vis_xfrm(|
|`_vis_post`|fn|priv|977-985|def _vis_post(|
|`_update_branch_colors`|fn|priv|1054-1057|def _update_branch_colors(|
|`_get_line_block`|fn|priv|1101-1102|def _get_line_block(|
|`_ReverseOutput`|class|priv|1124-1163|class _ReverseOutput|
|`_ReverseOutput.__init__`|fn|priv|1131-1138|def __init__(self, stream)|
|`_ReverseOutput.write`|fn|pub|1139-1145|def write(self, text: str) -> None|
|`_ReverseOutput.flush`|fn|pub|1146-1151|def flush(self) -> None|
|`_ReverseOutput.close`|fn|pub|1152-1163|def close(self) -> None|
|`_resolve_terminal_columns`|fn|priv|1174-1177|def _resolve_terminal_columns() -> int|
|`_truncate_line_to_terminal_width`|fn|priv|1185-1213|def _truncate_line_to_terminal_width(line: str, terminal_...|
|`_write_rendered_line`|fn|priv|1222-1225|def _write_rendered_line(|
|`_process`|fn|priv|1284-1303|def _process(|
|`_lines_iter`|fn|priv|1320-1324|def _lines_iter()|
|`run`|fn|pub|1467-1640|def run(extra_args: Optional[List[str]] = None) -> None|

