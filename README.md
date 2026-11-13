> [!CAUTION]
> ### 🚨 STRICTLY EXPERIMENTAL — PROOF OF CONCEPT (PRE-ALPHA)
> 
> ![Status: Proof of Concept](https://img.shields.io/badge/Status-Proof_of_Concept-red?style=flat-square) ![Stage: Pre-Alpha](https://img.shields.io/badge/Stage-Pre--Alpha-critical?style=flat-square) ![Maintenance: Personal Use Only](https://img.shields.io/badge/Scope-Personal_Use_Only-important?style=flat-square) ![Issues: Closed](https://img.shields.io/badge/Issues_%26_PRs-Not_Accepted-inactive?style=flat-square)
>
> **PLEASE READ CAREFULLY BEFORE USING THIS SOFTWARE:**
> 
> * **Very Early Stage:** This project is currently a raw **Proof of Concept (PoC)** in a **pre-alpha** state. It is nowhere near production-ready and may contain severe bugs, breaking changes, or incomplete logic.
> * **Personal Use Only:** This repository is developed, maintained, and shared strictly for **personal use**. 
> * **No Support or Feature Requests:** Please **do not** open issues, bug reports, or feature requests. They will not be addressed or accepted at this stage of development.
> * **No Warranty:** This software is provided **"AS IS"**, without warranty of any kind, express or implied. You may use it strictly for **testing and evaluation purposes** at your own sole risk.

# GAlias CLI (0.52.4)

<p align="center">
  <img src="https://img.shields.io/badge/python-3.11%2B-3776AB?style=flat-square&logo=python&logoColor=white" alt="Python 3.11+">
  <img src="https://img.shields.io/badge/license-GPL--3.0-491?style=flat-square" alt="License: GPL-3.0">
  <img src="https://img.shields.io/badge/platform-Windows%20%7C%20macOS%20%7C%20Linux-6A7EC2?style=flat-square&logo=terminal&logoColor=white" alt="Platforms">
  <img src="https://img.shields.io/badge/docs-live-b31b1b" alt="Docs">
<img src="https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/uv/main/assets/badge/v0.json" alt="uv">
</p>

<p align="center">
<strong>GAlias CLI provides a command-line interface to replicate the Git aliases defined in this package.</strong><br>
This allows them to be run both as a Python package (installed as <b>g</b> or <b>galias</b>) and directly using <b>uvx</b>.<br>
<i>This is a companion script for the <b><a href="https://github.com/Ogekuri/useReq">useReq/req</a></b> </i>🤖✨.
</p>

<p align="center">
  <a href="#quick-start">Quick Start</a> |
  <a href="#feature-highlights">Feature Highlights</a> |
  <a href="#management-commands">Upgrading or Removing</a> |
  <a href="#cli-examples">CLI Examples</a>
</p>

<p align="center">
<br>
🚧 <strong>DRAFT:</strong> Proof-of-Concept (PoC) Version 📝 - Work in Progress 🏗️ 🚧<br>
⚠️ <strong>IMPORTANT NOTICE</strong>: Created with <a href="https://www.npmjs.com/package/pi-usereq"><strong>PI-useReq/pi-usereq</strong></a> 🤖✨ ⚠️<br>
<br>
</p>


## Feature Highlights
- Supports [Conventional Commit Standards](https://www.conventionalcommits.org/en/v1.0.0/) compatible with [release-changelog-builder-action](https://github.com/mikepenz/release-changelog-builder-action).
- Auto-amending `wip` command for day-to-day "work in progress" commits.
- Common aliases for repetitive tasks like `add --all` (`aa`) and more.
- Acts like a `.gitconfig` [alias] section, providing all standard Git commands with a fallback mechanism.
- Customizable three-branch workflow: `master`, `develop`, and `work`.
- Conventional commit aliases support `<module>: <description>` syntax (example: `g new api: add endpoint`) and also accept `<description>` only, using `.galias.conf.default_commit_module` (default: empty, so messages become `<type>: <description>` when no module is configured).
- Standardized commits with specific commands like: `g new core: foo bar.` Use these commands for common activities such as:
  - `new`: Implement new features.
  - `implement`: Implement features or larger changes.
  - `refactor`: Refactor existing code without changing behavior.
  - `fix`: Bug fixes.
  - `change`: Software changes.
  - `docs`: Add/modify documentation.
  - `style`: Styling modifications.
  - `revert`: Revert changes.
  - `rollback`: Restore branch content to a previous commit/tag by creating a dedicated rollback `revert` commit. Runs a version pre-check first and preserves the current application version by restoring it via `chver` before the rollback commit.
  - `misc`: Miscellaneous tasks.
  - `cover`: Add/adjust tests to improve coverage.
- Provides `major`, `minor`, and `patch` release commands that auto-generate a `CHANGELOG.md` and tag the integrated branch: configured `master` by default, or configured `develop` when `--dev`/`--develop` limits the release to it.
  | Command | Branch | Changelog Type |
  | --- | --- | --- |
  | patch --dev | work -> develop | Include patch versions |
  | patch | work -> develop -> master | Include patch versions |
  | minor | work -> develop -> master | Minor versions only |
  | major | work -> develop -> master | Minor versions only |

- Provides `backup` command to run release preflight checks, merge `work` into `develop`, push `develop`, and return to `work`.
- Provides `get` command to fast-forward local `master` and `develop` from `origin` (with tags), then fast-forward merge `develop` into `work` after strict preflight checks.
- Provides `str` command to print all remotes and run `git remote show <remote>` for each.
- Provides visual diff aliases for repository comparisons: `dwc` (working tree vs `HEAD`), `dcc` (`HEAD~1` vs `HEAD`), `dccc` (`HEAD~2` vs `HEAD`), `dwcc` (working tree vs `HEAD~1`), `dw <ref>` (working tree vs a specific ref), `dc <ref> [<ref_prev>]` (diff from `<ref_prev>` to `<ref>`; `<ref_prev>` defaults to `<ref>~1`), plus configured-branch comparisons `dcd` (`develop` vs `work`), `dcm` (`master` vs `work`), and `ddm` (`master` vs `develop`).
- Provides worktree aliases: `wt` (generic `git worktree` subcommands with arguments forwarded unchanged), `wtl` (dedicated `git worktree list` with `-v`/`--porcelain`/`-z` forwarding), `wtp` (`git worktree prune ...`), and `wtd` (worktree delete with paired branch cleanup and optional `--force`).
- Provides file listing aliases: `ls` lists tracked files; `lsa` lists untracked files; `lsi` lists ignored/untracked files and applies a default directory/suffix filter unless `--include-all` is provided.
- Provides an overview alias: `o` prints a structured repository summary with working-tree status, branch divergence/alignment sections, and a branch table that lists configured branches first and then all other local/remote branches with latest commit subjects.
- Version management commands: `ver` checks version consistency (supports `--verbose`/`--debug`), `chver <major.minor.patch>` updates files matched by `ver_rules`, and `changelog` generates `CHANGELOG.md` (supports `--include-patch`, `--force-write`, `--print-only`, `--disable-history`).
- Checks PyPI for a newer release on startup within an idle window (1 hour after success, 24 hours after errors) and prints an update warning; `--ver` forces an online check and reports installed, PyPI, and GitHub versions.
- Self-upgrade and self-uninstall management commands are Linux-only for local execution (`--upgrade`, `--uninstall`), with manual command hints on other platforms.
- Includes a **quick overview** command `o`:
[![Flowchart](https://raw.githubusercontent.com/Ogekuri/GAlias/refs/heads/master/images/command_o_overview_sample1.png)](https://raw.githubusercontent.com/Ogekuri/GAlias/refs/heads/master/images/command_o_overview_sample1.png)
- Includes **git-foresta** command `l`:
[![Flowchart](https://raw.githubusercontent.com/Ogekuri/GAlias/refs/heads/master/images/commnad_l_git-foresta-sample1.png)](https://raw.githubusercontent.com/Ogekuri/GAlias/refs/heads/master/images/commnad_l_git-foresta-sample1.png)
  Options include `--all`, `--no-color`, `--no-status`, `--reverse`, `--wrap`, `--abbrev=<n>`, `--svdepth=<n>`, `--style=<n>`, `--graph-margin-left=<n>`, `--graph-margin-right=<n>`, and `--graph-symbol-*` overrides.


## Requirements

- Astral `uv` is required to install or upgrade GAlias, to run it through `uvx`, and for the repository-local launcher (`uv run`); normal command execution through an installed `g`/`galias` console script does not require `uv`.
- A separate external or system-managed Python virtual environment is not required.
- When needed, you can generate a transient `requirements.txt` file with:
  ```bash
  uv export --format requirements-txt > requirements.txt
  ```


## Quick Start

### Prerequisites

- Supported runtime for the CLI: Linux, macOS, or Windows (with Git + Python 3.11+ available).
- `--upgrade` installs from PyPI by default (`--develop` or `--dev` installs the newest tagged release from GitHub; note that on `major`/`minor`/`patch` the same flags instead limit the release to the configured `develop` branch) and `--uninstall` executes locally only on Linux; other platforms print the equivalent manual `uv tool` command. Add `--force` to `--upgrade` to force the download and a complete reinstallation (the executed `uv tool install` gains `--force --reinstall --refresh`).
- Install the `uv` tool from: [https://docs.astral.sh/uv/getting-started/installation/](https://docs.astral.sh/uv/getting-started/installation/)


### Install GAlias

  - Primary Method: Astral uv (from PyPI)
  ```bash
  uv tool install galias
  ```

  - Alternative Method: uvx, run directly without installation (from PyPI)
  ```bash
  uvx galias <command> [args...]
  ```

  - Install from GitHub (intermediate and test releases)
  ```bash
  uv tool install --from git+https://github.com/Ogekuri/GAlias galias
  ```

  Upgrade to the latest version published on GitHub:
  ```bash
  g --upgrade --develop
  ```

  Force the download and a complete reinstallation on either source (`--force` adds the uv options `--force --reinstall --refresh`):
  ```bash
  g --upgrade --force
  g --upgrade --develop --force
  ```

  - Run with the Repository-Local Launcher (no installation required)
  ```bash
  scripts/g.sh <command> [args...]
  ```

  Requires Astral `uv` in `PATH`: the launcher resolves the repository root and delegates execution to `uv run --project <repo> python -m git_alias`.


### Manage Configuration

Configuration uses `$HOME/.config/galias/config.json` for `Global` and
repository-root `.galias.conf` for `Local` (current directory outside Git).
The global file is auto-created with schema defaults on the first configuration
command; the local file is created only by explicit mutations.

```bash
g --info
g --print
g --print-raw
g --print-raw Global
g --set Global:edit_command 'vim -f'
g --set Global:edit_command "$EDITOR"
g --set Local:work topic
g --get Local
g --get Local:ver_rules:0:pattern
g --set Local:ver_rules '[{"pattern":"VERSION","regex":"(\\d+\\.\\d+\\.\\d+)"}]'
g --unset Local:work
g --unset Local:ver_rules:0
g --unset Local
g --set --help
```

Paths are case-sensitive, use `:` separators, and support zero-based array
indices. `--set PATH VALUE` accepts strings as one argument and objects or
arrays as one shell-quoted JSON argument; regex backslashes must be doubled in
JSON. The shell expands environment variables before invocation; GAlias stores
the received string without executing it. Use `:append` (or `:+`) to add one
array entry and `:insert:<Idx>` to insert at a zero-based position.

`--get` returns JSON and resolves absent top-level keys from defaults.
`--unset` removes persisted keys, restores their defaults, removes array
entries, or clears a scope. Required version-rule fields cannot be removed;
exclusion rules may omit `regex`. Invalid input fails before writing. Each
mutation atomically replaces only the selected file. Read commands never modify
existing configuration files.

`--print` shows effective values as a tree: scalar values print as JSON-style
text (strings quoted) with `(default)` or `(custom | default: ...)`
annotations, while arrays and maps render as box-drawing tables. `--info`
documents every path with its bracketed type and constraints, description,
default, allowed-value tables when constrained, item schema for arrays, and
ready-to-run `--set`/`--unset` commands. `--print-raw [Global|Local]`
emits exact stored bytes; without a selector it concatenates global then local
bytes. File labels and missing-file notices go to stderr; stdout carries no
added separators.

### Configuration Fields

- Customize repository-local `.galias.conf` with `master`, `develop`, `work`, `default_commit_module`, `build_script`, `pre_release_check`, and `ver_rules`.
- `build_script` (default: empty, step skipped) runs after the version update and before the release-version commit; `pre_release_check` (default: empty, step skipped) runs first and aborts the release on a non-zero exit. Both apply to `major`, `minor`, and `patch`.
- Each `ver_rules` entry pairs a `pattern` (file selector) with a `regex` (version extractor).
- **`ver_rules.pattern` uses the `.gitignore` file syntax ([gitignore(5)](https://git-scm.com/docs/gitignore))**. Only tracked repository files (`git ls-files`) are candidates, and hardcoded cache/temporary paths (e.g. `.git`, `tmp`, `temp`, `.cache`, `.pytest_cache`) are always excluded from matching. Semantics:
  - Patterns without `/` match at any depth; patterns containing `/` are anchored to the repository root (a leading `./` is stripped).
  - A backslash escapes the next character and is never treated as a path separator (e.g. `\!file.txt` matches a file literally named `!file.txt`).
  - A pattern starting with `!` is a negation rule: matching files are excluded from every `ver_rules` match list; negation entries do not need a `regex` and are not evaluated for version detection.
  - A `pattern` that matches zero repository files aborts `ver` and `chver` with an explicit error.

Pattern examples (`ver_rules.pattern`, gitignore syntax):

| `pattern` | Matching behavior | Example matched files |
| --- | --- | --- |
| `README.md` | No `/`: matches at any depth | `README.md`, `docs/README.md` |
| `pyproject.toml` | No `/`: matches at any depth | `pyproject.toml`, `tools/pyproject.toml` |
| `src/**/*.py` | Contains `/`: anchored to the repository root; `**` spans any number of directories | all `.py` files under `src/` (e.g. `src/git_alias/core.py`) |
| `src/*.py` | Contains `/`: anchored to the repository root, direct children of `src/` only | `src/main.py` (not `src/git_alias/core.py`) |
| `docs/CHANGELOG.md` | Anchored exact repository path | `docs/CHANGELOG.md` only |
| `./pyproject.toml` | Leading `./` is stripped before matching | equivalent to `pyproject.toml` (matches at any depth) |
| `!src/experimental/**` | Negation: excludes matched files from every rule's match list; no `regex` needed | removes all files under `src/experimental/` from the match lists |
| `\!file.txt` | Backslash escape: matches the next character literally | a file literally named `!file.txt` |

The default `ver_rules` select `README.md`, `src/**/*.py`, and `pyproject.toml`.

- Global settings contain terminal/graphical pairs for `edit_command`, `diff_command`, `gr_command`, and `gp_command`; graphical variants end in `_gfx`.
- Configuration mutations persist canonical keys only; unrelated file keys are ignored.


### Work-in-Progress Commits

```bash
g st
g wip
```

`g wip` auto-stages tracked/untracked working-tree changes when the index is empty.


### Override a `wip` Commit with a Final Commit

```bash
g new core: finalize release notes
```

### Release a New Version (with all changes committed)

When your `work` branch is fully committed, release a new version with:

```bash
g minor
```

The command must run from the `work` branch with a clean working tree; it bumps versions per `ver_rules`, creates a temporary local annotated `v<next>` tag only for changelog generation, deletes that temporary tag after changelog generation, and creates the definitive tag immediately before push (`--dev`/`--develop`: on `develop`, then an atomic push of `develop` with the release tag only; default: on `master`, then an atomic push of `master` with the release tag after pushing `develop`).

Add `--include-patch` to include the latest patch release after the last minor release in the regenerated changelog. Use `--resume` (optionally with `--dev`/`--develop`) to validate and publish an already prepared release without bumping versions, amending commits, or recreating its tag; completed publication is a no-op.


## Management Commands

Upgrade or uninstall the GAlias CLI:

- `g --upgrade` / `galias --upgrade`: Reinstalls the tool from PyPI on Linux; `g --upgrade --develop` (or the equivalent `--dev`) reinstalls the newest tagged release from GitHub; on non-Linux platforms it prints the equivalent manual command. Add `--force` to force the download and a complete reinstallation through the uv options `--force --reinstall --refresh`. The same `--dev`/`--develop` flags have a different meaning on `major`/`minor`/`patch`, where they limit the release to the configured `develop` branch.
- `g --uninstall` / `galias --uninstall`: Uninstalls the tool on Linux; on non-Linux platforms it prints the equivalent manual command.
- `--set PATH VALUE`, `--unset PATH`, `--get PATH`: Manage a field or scope through colon-separated paths.
- `--print`, `--print-raw [Global|Local]`, `--info`: Display effective values, exact file bytes, or typed parameter documentation.
- `g --ver` / `g --version` / `galias --ver` / `galias --version`: Prints the CLI version and the latest versions available on PyPI and GitHub.
- `g --help` / `galias --help`: Prints management commands, configuration parameters, and the alias list; use `g --help <command>` for a single command.

## CLI Examples

Some CLI examples:

- `g`: Prints `Please provide a command or --help` and `Usage: g <command> [options] (<version>)`.
- `g --help` / `galias --help`: Prints management commands, configuration parameters, and the alias list; use `g --help <command>` for a single command.
- `g lg --help`: Shows the help text for the `lg` alias.
- `g cm "Message"`: Runs `git commit` with the provided message.
- `g new api: add endpoint`: Creates `new(api): Add endpoint.` (first letter normalized to uppercase and a trailing period added when missing).
- `g new add endpoint`: Creates `new: Add endpoint.` when `.galias.conf.default_commit_module` is empty.
- `g wip`: Auto-stages when needed and commits `wip: work in progress.`.
- `g backup`: Merges configured `work` into `develop`, pushes `develop`, and checks out back to `work`.
- `g get`: Fast-forwards local `master` and `develop` from `origin` and then fast-forward merges `develop` into `work`.
- `g str`: Lists remotes and prints `git remote show` details for each.
- `g rollback v1.2.3`: Reverts commits after `v1.2.3` and creates `revert: Roll back branch to v1.2.3 (<hash>).`; the application version detected before the rollback is preserved and restored via `chver` inside the rollback commit.
- `g dcd`: Runs `git difftool -d <develop> <work>` using configured branch names.
- `g dcm`: Runs `git difftool -d <master> <work>` using configured branch names.
- `g ddm`: Runs `git difftool -d <master> <develop>` using configured branch names.
- `g bd --force feature/demo`: Removes the associated worktree first when present, then force-deletes `feature/demo`.
- `g wt list`: Runs `git worktree list`; `wt` forwards any `git worktree` subcommand/argument (e.g. `g wt add <path> <branch>`) unchanged.
- `g wtl --porcelain`: Lists worktrees via `git worktree list --porcelain`; `g wtp` runs `git worktree prune`.
- `g wtd --force ../repo-worktree`: Force-removes the target worktree; when it is associated to a local branch, the worktree is deleted before the branch.
- `g ls -z`: Lists tracked files using `git ls-files --exclude-standard`.
- `g lsi -z`: Lists ignored/untracked files using `git ls-files --others --ignored --exclude-standard` plus the default filter.
- `g lsi --include-all -z`: Lists all ignored/untracked files without the default filter.
- `g o`: Prints a verbose overview with status, branch distances, active worktrees, and a qualitative ASCII topology tree.
- `g ver --verbose`: Verifies version consistency with detailed output.
- `g chver 1.2.3`: Updates the project version to 1.2.3 using `ver_rules`.
- `g changelog --print-only`: Prints the generated changelog without writing `CHANGELOG.md`.

## Acknowledgments

Special thanks to Jan Engelhardt and Takaaki Kasai, authors of the Perl
[git-foresta](https://github.com/takaaki-kasai/git-foresta) program, integrated in GAlias CLI.
