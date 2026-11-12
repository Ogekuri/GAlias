---
title: "GAlias CLI Requirements"
description: "Software Requirements Specification"
date: "2026-02-25"
author: "Francesco Rolando"
scope:
  paths:
    - "src/**/*.py"
    - "scripts/*.sh"
    - ".gitignore"
    - ".github/workflows/**/*.yml"
  excludes:
    - "tests/**"
    - "doxygen/**"
visibility: "draft"
tags: ["requirements", "srs", "galias"]
---

# GAlias CLI Requirements
**Version**: 1.57
**Author**: Francesco Rolando
**Date**: 2026-11-12

## Revision History
| Date | Version | Change Summary |
|------|---------|----------------|
| 2026-11-12 | 1.57 | Removed the build-preparatory `test-release` job (lock synchronization and pytest) from `release-pypi.yml` and gated `publish-release` only on the branch-containment job (REQ-228, REQ-229, REQ-213): the automation consumes and publishes the pre-built `dist/` artifacts of the tagged release commit and never executes `scripts/build.sh` or `scripts/pre-release-check.sh` (REQ-313). |
| 2026-11-12 | 1.56 | Removed `scripts/clean.sh` (REQ-309..REQ-312) and integrated its cleanup into the start of every `scripts/build.sh` build (REQ-286, REQ-317): all `dist/` release artifacts of every version are removed regardless of git tracking status (REQ-282), build intermediates stay behind the tracked-content guard (REQ-288, REQ-316), and a successful build leaves only the produced artifacts with no intermediate residue (REQ-284). |
| 2026-11-11 | 1.55 | Changed `release-pypi.yml` to a build-free automation consuming the pre-built `dist/` artifacts of the tagged release commit: provenance attestation without any distribution build (REQ-113), asset upload from the tagged commit (REQ-114), pre-built PyPI publication (REQ-194), renamed `publish-release` gate (REQ-229), and the new tagged-artifact consumption and validation contracts (REQ-313..REQ-315). |
| 2026-11-11 | 1.54 | Added `scripts/clean.sh` as the dedicated cleanup entry point for every artifact created by `scripts/build.sh` (REQ-309..REQ-312), made `scripts/build.sh --clean` delegate to it (REQ-286), and routed the pre-release cleanup through it (REQ-226, REQ-288). |
| 2026-11-11 | 1.53 | Changed `dist/` release artifacts to git-versionable: `.gitignore` re-includes `dist/` through `!dist/` and `!dist/**/*` in the include section with no later artifact exclusion (REQ-301, REQ-302), and the pre-release artifact ignore check verifies artifacts are not ignored (REQ-295). |
| 2026-11-11 | 1.52 | Defined the sdist content policy: the sdist is restricted to runtime sources and metadata and excludes tests, scripts, usereq, MANIFEST.in, and generated egg-info (REQ-304, REQ-305); the parity clause moved from REQ-128 to REQ-306; REQ-307 and REQ-308 extend the staged-build and artifact-validation gates of REQ-283 and REQ-294. |
| 2026-11-11 | 1.51 | Added the `scripts/build.sh` release-artifact build script with targeted `--clean`/`--list-artifacts` modes, expanded `scripts/pre-release-check.sh` into the complete release-readiness check invoking `scripts/build.sh` with artifact validation, signal-safe cleanup, and repository-integrity verification, and replaced the blanket `.gitignore` `dist/` exclusion with targeted artifact rules (REQ-222, REQ-226, REQ-227, REQ-280..REQ-303). |
| 2026-11-11 | 1.50 | Renamed the configuration documentation command from `--params` to `--info`, keeping its schema-derived hierarchy, subtree filtering, metadata children, and tables (REQ-243, REQ-251, REQ-263, REQ-264, REQ-273, REQ-275, REQ-276, REQ-278). |
| 2026-11-11 | 1.49 | Replaced name-length-driven padding in `--print`/`--params` tree rendering with fixed four-character depth indentation, metadata children rendered through standard connectors, and table indent derived from the owning node (REQ-275..REQ-279). |
| 2026-11-10 | 1.48 | Expanded the schema-driven configuration CLI with `--print`/`--params` subtree paths, annotated tree rendering with default/custom badges and typed tables, `append`/`insert`/row/cell/map-key path tokens, global auto-initialization, and strict stdout/stderr and exit-code contracts (REQ-097, REQ-245, REQ-250, REQ-251, REQ-252, REQ-254, REQ-257..REQ-274). |
| 2026-11-10 | 1.47 | Renamed the Italian-derived `foresta.py` module to `forest.py` (CPT-008) and mandated English-only Python identifier naming under `src/` (REQ-256). |
| 2026-11-10 | 1.46 | Replaced configuration normalization with schema-driven hierarchical CLI management, raw/tree output, typed parameter discovery with input examples, and mandatory CLI synchronization (DES-010, REQ-014, REQ-015, REQ-097, REQ-207, REQ-242..REQ-255). |
| 2026-11-10 | 1.45 | Indented changelog continuation lines to align with the commit bullet text (REQ-232). |
| 2026-11-10 | 1.44 | Aligned `--ver`/`--version` report output so the installed, PyPI, and GitHub version lines render 18-character left-justified labels followed by `: <version>` (REQ-202, REQ-230, REQ-241). |
| 2026-11-09 | 1.43 | Added the `--upgrade` auxiliary `--force` flag forcing download and complete reinstallation through the uv forcing options `--force --reinstall --refresh` on both PyPI and GitHub sources while the unforced path runs the standard install (REQ-001, REQ-129, REQ-209, REQ-236..REQ-240). |
| 2026-11-09 | 1.42 | Changed `changelog` multiline rendering: markdown bullet lists in description lines after the first are stripped and replaced with `'; '`-separated lines while non-bullet lines stay verbatim, keeping cleanup and assembly logic (REQ-232, REQ-234, REQ-235). |
| 2026-11-09 | 1.41 | Changed `changelog` multiline commit rendering: description lines after the first are preserved verbatim without sub-bullet transformation while keeping `Co-authored-by`/empty-line cleanup and the `- <description> *(<scope>)*` top-level bullet format (REQ-078, REQ-232, REQ-233). |
| 2026-11-08 | 1.40 | Added `--ver`/`--version` GitHub latest-version failure reporting: resolution failures now print `GitHub latest: unknown (<reason>)` with the intercepted failure reason, including HTTP status code and the API rate-limit message (REQ-230, REQ-231). |
| 2026-11-07 | 1.39 | Added the `test-release` GitHub Actions job running `uv lock --check` plus the full pytest suite and gated `build-release` on it, preventing release artifacts and any publication when tests fail (REQ-228, REQ-229). |
| 2026-11-07 | 1.38 | Tightened `scripts/pre-release-check.sh` post-run cleanup so execution leaves the repository free of build and intermediate validation artifacts, preserving only the uv-managed environment (REQ-223, REQ-226, REQ-227). |
| 2026-11-07 | 1.37 | Added the repository-local `scripts/pre-release-check.sh` official-release pre-validation script covering prerequisite checks, lockfile sync verification, full pytest execution, and distribution build (REQ-217..REQ-225). |
| 2026-11-07 | 1.33 | Renamed the `--upgrade` GitHub-source option from `--github` to `--develop` with equivalent `--dev` (REQ-001, REQ-201, REQ-203, REQ-198). |
| 2026-11-07 | 1.34 | Made `--upgrade --develop`/`--dev` resolve and install the newest GitHub release tag via the GitHub releases API regardless of branch (REQ-201, REQ-208, REQ-209, REQ-210). |
| 2026-11-07 | 1.35 | Migrated release automation to the GitHub Actions Node24 runner generation, pinning Node24-based action majors and banning Node20 opt-out overrides (REQ-211, REQ-212, REQ-213). |
| 2026-11-07 | 1.36 | Resolved the `--dev`/`--develop` flag collision: `major`, `minor`, and `patch` now accept the release-scope flags alongside `--upgrade`, with dual-meaning documentation in inline help and README (REQ-203, REQ-214, REQ-215, REQ-216). |
| 2026-11-07 | 1.32 | Removed the undocumented legacy `ver_rules` `glob` key alias; added REQ-207 defining the canonical `ver_rules` entry schema resolved solely from the `pattern` field. |
| 2026-11-07 | 1.31 | Removed the legacy global `editor` to `edit_command` migration from `--write-config`; REQ-015 now mandates persisting only the eight canonical REQ-186 global keys while ignoring out-of-scope keys per DES-006. |
| 2026-11-05 | 1.30 | Widened the release workflow containment gate to `origin/master` or `origin/develop` (REQ-112), gated PyPI publication to master-contained tag commits (REQ-205), and required develop-only tag commits to run the release workflow without PyPI publication (REQ-206). |
| 2026-11-05 | 1.29 | Added the `--github` self-upgrade source override (REQ-201, REQ-203), dual PyPI/GitHub version reporting for `--ver`/`--version` (REQ-202, REQ-204), restricted default checks/upgrades to PyPI (REQ-001, REQ-129, REQ-199), and made `uv tool install galias` the documented primary install method with dedicated GitHub and uvx sections (REQ-198). |
| 2026-11-05 | 1.28 | Unified default `patch` publication with `major`/`minor` (REQ-072), repurposed REQ-045 for the develop-scoped `--dev`/`--develop` release option available on `major`, `minor`, and `patch` (REQ-200), and extended `--resume` composition and push-recovery guidance to develop-scoped releases (REQ-176, REQ-180). |
| 2026-11-05 | 1.27 | Switched update checks to the PyPI JSON API `info.version` (REQ-124, REQ-199), switched `--upgrade` to the PyPI-sourced `uv tool install galias --force` (REQ-001, REQ-199), and made pipx the documented primary install method with Astral uv/uvx as alternative (REQ-198). |
| 2026-11-05 | 1.26 | Renamed the release workflow file to `release-pypi.yml` (REQ-112) and added PyPI OIDC Trusted Publishing requirements for release permissions, publication steps, packaging metadata, license declaration, and install documentation (REQ-193, REQ-194, REQ-195, REQ-196, REQ-197, REQ-198). |
| 2026-11-05 | 1.25 | Renamed the repository-local configuration file from `.g.conf` to `.galias.conf` without backward compatibility (DES-006, DES-009, REQ-006, REQ-014, REQ-017, REQ-116, REQ-119). |
| 2026-11-05 | 1.24 | Renamed the upstream GitHub repository to `Ogekuri/GAlias` (REQ-001, REQ-124), renamed the distribution/tool/binaries to `galias` with `g` and removed `git-alias` (PRJ-001, CPT-002, REQ-001, REQ-002), and renamed user-facing cache/config paths to `~/.cache/galias` and `~/.config/galias` (REQ-002, REQ-013, REQ-014, REQ-030, REQ-033, REQ-126, REQ-136, REQ-137, CTN-003, DES-006, DES-009, REQ-186). |
| 2026-11-05 | 1.23 | Renamed the upstream GitHub repository from `Ogekuri/G` to `Ogekuri/GitAlias` in the `--upgrade` source URL (REQ-001) and the release-check API URL (REQ-124). |
| 2026-11-03 | 1.22 | Imposed defaults `edit`/`sublime_text`, `icdiff`/`meld`, `tig`/`gitg`, `gitui`/`sublime_merge --multiinstance .` for the eight global command keys (REQ-191) and required their contiguous canonical print order in Configuration Parameters output (REQ-192). |
| 2026-11-03 | 1.21 | Changed visual diff execution to `git difftool -d` with the environment-selected `diff_command`/`diff_command_gfx` injected as `--extcmd`, overriding git's configured diff tool; empty resolved command runs plain `git difftool -d`. |
| 2026-11-03 | 1.20 | Added environment-aware dual external-command configuration (`<id>_command`/`<id>_command_gfx`), the dedicated `diff_command` pair driving visual diff aliases, and the single `_run_checked` subprocess interception wrapper. |
| 2026-11-03 | 1.19 | Changed `dc` so `<ref_b>` is optional and defaults to the commit preceding `<ref>`, renamed operands `<ref_a>`/`<ref_b>` to `<ref>`/`<ref_prev>`, and enforced `ref_prev -> ref` diff direction. |
| 2026-10-22 | 1.18 | Added `rollback` version pre-flight check, version preservation via `chver` restore before the revert commit, abort-on-restore-failure semantics, and help/README documentation. |
| 2026-10-02 | 1.16 | Required gitignore(5) escaping and negation exclusion semantics for `ver_rules.pattern` with anchoring preserved and README documentation. |
| 2026-10-21 | 1.17 | Added `--exec <command> [params...]` option for `major`/`minor`/`patch` release commands with argv execution between version update and staging and fail-fast abort semantics. |
| 2026-04-22 | 1.15 | Changed `wt` to execute `git worktree` while keeping `wtl` as the dedicated `git worktree list` alias. |
| 2026-03-30 | 1.14 | Required idle-time JSON rewrites for every version-check error while keeping 3600-second success delay and 86400-second error delay. |
| 2026-03-30 | 1.13 | Changed release-check idle delays to 3600 seconds after success and 86400 seconds after release-check API-call errors. |
| 2026-03-30 | 1.12 | Replaced release-check rate-limit backoff with a fixed 3600-second idle delay for HTTP 429 and HTTP 403 API rate-limit responses. |
| 2026-03-27 | 1.11 | Changed `--ver`/`--version` behavior to force online update checks while ignoring idle-time cache state gating. |
| 2026-03-18 | 1.10 | Replaced update-check idle cache path with `~/.cache/git-alias/check_version_idle-time.json`, required parent directory creation, and required Linux uninstall cache cleanup. |
| 2026-03-17 | 1.09 | Updated `l` rendering contract to enforce terminal-width truncation by default via `shutil` and added `--wrap` to disable truncation. |
| 2026-03-17 | 1.08 | Restricted `--upgrade`/`--uninstall` local execution to Linux and required explicit manual-command guidance on non-Linux platforms. |
| 2026-03-17 | 1.07 | Added explicit pytest dependency requirement for Astral uv-managed project dependencies in pyproject/lock synchronization policy. |
| 2026-03-17 | 1.06 | Removed README-specific synchronization requirement from the SRS requirement set. |
| 2026-03-17 | 1.05 | Aligned documentation-generation and release-workflow trigger requirements to current implementation (optional Doxygen assets and dual workflow triggers with master-containment gate). |
| 2026-03-07 | 1.04 | Replaced update-check idle-time policy with fixed 300-second delay semantics and added HTTP 429 Retry-After backoff persistence requirements. |
| 2026-03-07 | 1.03 | Replaced update-check repository/program resolution with fixed constants, set successful idle-time default to 24 hours, and added minimum check-interval floor. |
| 2026-03-07 | 1.02 | Changed update-check idle default from 24 hours to 300 seconds and aligned idle-time cache filename requirement with `<program_name>`. |
| 2026-03-07 | 1.01 | Replaced hardcoded self-management executable names with package-tool identifier policy and required explicit package inclusion policy for uv release artifacts. |
| 2026-03-06 | 1.00 | Replaced update-check cache behavior with remote-derived GitHub API release checks, idle-time JSON policy, bright-green availability output, and `--uninstall` management command. |
| 2026-03-06 | 0.99 | Moved startup update-check ordering before argument validation and formalized bright-red update warning format. |
| 2026-02-24 | 0.97 | Added `l` command contracts and foresta engine requirements. |
| 2026-02-25 | 0.98 | Recreated SRS structure in English from repository evidence while preserving existing requirement IDs and appending workflow coverage requirements. |

## 1. Introduction
This SRS defines machine-testable requirements for the GAlias CLI and associated release automation implemented in the repository.

### 1.1 Document Rules
- The document MUST be written in English.
- Requirement identifiers MUST remain unique and stable once assigned.
- Existing requirement IDs MUST NOT be renumbered or reused for different behavior.
- Requirement statements MUST use RFC 2119 keywords (MUST, MUST NOT, SHOULD, SHOULD NOT, MAY).
- Each requirement MUST be atomic, verifiable, and testable.

### 1.2 Project Scope
The project provides a Python CLI (`galias` / `g`) that executes curated git aliases, manages local/global configuration, automates release-oriented operations, and exposes text/GUI repository inspection commands.

## 2. Project Requirements
### 2.1 Project Functions
- **PRJ-001**: MUST expose `galias` and `g` commands that dispatch to aliases implemented in `core.py` for execution in the current git repository.
- **PRJ-002**: MUST provide integrated help that lists available aliases and prints each alias description in English.
- **PRJ-003**: MUST support self-upgrade and self-uninstall through dedicated CLI management commands (`--upgrade`, `--uninstall`).

### 2.2 Project Constraints
- **CTN-001**: MUST require Python 3.11 or newer at runtime.
- **CTN-002**: MUST require `git` in PATH, MUST require `gitk` and Astral `uv` for related aliases and launcher flows, and MUST NOT require external or system-managed Python virtual environments.
- **CTN-003**: MUST file-edit aliases MUST use a CLI-invokable editor configured by `edit_command` in `$HOME/.config/galias/config.json`, defaulting to `edit` when the file, key, or value is missing or invalid, with graphical environments selecting `edit_command_gfx` per REQ-187 and REQ-188.

### 2.3 Components and Libraries
- **CPT-001**: MUST implement CLI dispatch and alias runtime behavior in `src/git_alias/core.py`.
- **CPT-002**: MUST provide package entrypoints through `src/git_alias/__main__.py` and console scripts `galias` and `g`.
- **CPT-003**: MUST include automated tests under `tests/` covering user-visible command contracts.
- **CPT-004**: MUST treat `uv.lock` as canonical dependency lock inventory, MUST keep `pyproject.toml` synchronized with it, MUST include `pytest` as an Astral `uv`-managed dependency, and MAY generate transient `requirements.txt` via `uv export` only when explicitly needed.
- **CPT-005**: MUST invoke external executables `git`, `gitk`, and Astral `uv` (including `uvx` and `uv run`) for delegated operations.
- **CPT-006**: MUST use `pathspec` for gitignore-style pattern matching in version rules processing.
- **CPT-007**: MAY include repository-local Doxygen launcher assets; runtime behavior MUST NOT depend on documentation-generation scripts.
- **CPT-008**: MUST include `src/git_alias/forest.py` implementing text-based commit tree visualization.

## 3. Software Requirements
### 3.1 Design and Implementation
- **DES-001**: MUST accept the first CLI argument as command, dispatch mapped aliases, and fallback to native `git <command> <args>` when command is unknown while preserving help/error behavior.
- **DES-002**: MUST forward extra arguments to delegated git commands, propagate external exit codes, and convert subprocess failures into explicit user-facing errors without raw Python tracebacks.
- **DES-003**: MUST define help text for every command and list commands alphabetically in global help output.
- **DES-004**: MUST print an explicit message plus full help and exit non-zero when invoked without arguments.
- **DES-005**: MUST compose complex aliases by reusing simpler alias functions when overlapping behavior exists.
- **DES-006**: MUST the executable MUST load `.galias.conf` for `master`, `develop`, `work`, `default_commit_module`, and `ver_rules`, and `$HOME/.config/galias/config.json` for `edit_command`, `edit_command_gfx`, `gp_command`, `gp_command_gfx`, `gr_command`, `gr_command_gfx`, `diff_command`, and `diff_command_gfx`, and MUST ignore out-of-scope keys in each file.
- **DES-007**: MUST centralize commit-readiness checks in reusable functions shared by `cm`, `wip`, and related aliases; readiness MUST succeed when staging is non-empty OR working-tree is dirty; MUST fail when both staging and working-tree have no committable data; MUST invoke `aa` to auto-stage working-tree changes when staging is empty and working-tree is dirty.
- **DES-008**: MUST print all console messages in English.
- **DES-009**: MUST the global `--help` output MUST be ordered as usage, Management Commands, Configuration Parameters, and Commands, and Configuration Parameters MUST print resolved values from `.galias.conf` plus `$HOME/.config/galias/config.json`, otherwise defaults from `DEFAULT_CONFIG`.

- **DES-010**: MUST update configuration CLI access, validation, help, parameter discovery, rendering, and tests whenever any configuration field, type, default, scope, structure, or allowed value changes.

### 3.2 Functional Requirements
- **REQ-001**: MUST execute `uv tool install galias` with no forcing options, installing the latest PyPI release, when `--upgrade` without `--develop`, `--dev`, or `--force` is invoked on Linux.
- **REQ-002**: MUST when `--uninstall` is invoked on Linux, delete `~/.cache/galias/check_version_idle-time.json`, remove `~/.cache/galias`, and execute `uv tool uninstall galias`.
- **REQ-129**: MUST NOT execute local `uv tool install` when `--upgrade` is invoked on non-Linux platforms, and MUST print the exact manual install command matching the selected source and `--force` mode (PyPI or REQ-201 GitHub).
- **REQ-130**: MUST NOT execute local `uv tool uninstall` when `--uninstall` is invoked on non-Linux platforms, and MUST print the exact manual uninstall command for user execution.
- **REQ-003**: MUST show global command help or specific command help via `--help`, and per-command help text MUST explicitly list supported options when present.
- **REQ-004**: MUST execute `git add --all` for alias `aa` only after reusable diagnostics confirm pending unstaged/untracked changes, and MUST fail with explicit error when nothing can be added.
- **REQ-005**: MUST validate `cm` preconditions (no unstaged changes, non-empty index, and WIP-amend decision) and MUST amend `wip: work in progress.` only when not yet merged to configured `develop` and `master`.
- **REQ-006**: MUST support targeted branch checkout via `co` using configured branch names from `.galias.conf` defaults (`work`, `develop`, `master`).
- **REQ-007**: MUST implement generic current-branch fetch/pull/push aliases (`fe`, `feall`, `pl`, `pt`, `pu`) without dedicated per-branch shortcuts.
- **REQ-008**: MUST inspection aliases MUST provide branch, log, and status views via `br`, `lb`, `ck`, `l`, `lg`, `ll`, `lm`, `lh`, `lt`, `ver`, `gp`, `gr`, `de`, `rf`, `st`, `str`, `dw`, `dwc`, `dcc`, `dc`, `ls`, `lsi`, `lsa`.
- **REQ-009**: MUST provide generic merge integration through alias `me` for configured branch workflows without extra automation wrappers.
- **REQ-010**: MUST the system MUST limit automated workflow aliases to the documented set (currently `major`, `minor`, `patch`, `backup`) and MUST NOT introduce additional automatic workflow shortcuts beyond those specified.
- **REQ-011**: MUST provide reset/cleanup aliases (`rs`, `rssft`, `rsmix`, `rshrd`, `rsmrg`, `rskep`, `unstg`, `rmloc`, `rmstg`, `rmunt`) and MUST print dedicated reset help when `rs*` commands receive `--help`.
- **REQ-012**: MUST tagging and archive aliases MUST support annotated tag creation (`tg`), local/remote tag deletion (`rmtg`), tag listing (`lt`), and archiving configured `master` in tar.gz (`ar`).
- **REQ-013**: MUST open file paths through `ed` using `edit_command` from `$HOME/.config/galias/config.json` (default `edit`) and MUST fail with explicit error when no path is supplied.
- **REQ-014**: MUST persist the selected configuration scope as JSON through `--set` and `--unset`, replacing `--write-config`.
- **REQ-015**: MUST persist only DES-006 canonical keys in the selected scope during configuration mutations.
- **REQ-016**: MUST show management commands before alias listings when global help is requested or when command input is missing.
- **REQ-017**: MUST evaluate `ver_rules` from `.galias.conf` (or defaults), build repository candidates from `git ls-files`, apply pathspec matching plus hardcoded cache/temp exclusions, and fail on mismatched or missing version matches as specified.
- **REQ-118**: MUST abort `ver` and `chver` when a `ver_rules.pattern` matches zero repository files, and MUST report the offending pattern with guidance that only repository files can be configured in `ver_rules.pattern`.
- **REQ-160**: MUST treat each backslash in `ver_rules.pattern` as a gitignore(5) escape of the next character and MUST NOT convert backslashes to path separators.
- **REQ-161**: MUST exclude candidate files matching the remainder of a `ver_rules.pattern` starting with `!` from every version rule matched file list.
- **REQ-162**: MUST accept `ver_rules` entries whose pattern starts with `!` without a `regex` field and MUST NOT evaluate such entries as version detection rules.
- **REQ-163**: MUST NOT count negation-excluded files as `ver_rules.pattern` matches and MUST apply the REQ-118 zero-match abort only to non-excluded matches.
- **REQ-164**: MUST keep `ver_rules.pattern` anchoring unchanged: patterns containing `/` MUST be anchored to repository root and patterns without `/` MUST match at any depth.
- **REQ-165**: MUST document `ver_rules.pattern` in `README.md` as gitignore(5)-compatible including backslash escaping and `!` negation exclusion.
- **REQ-018**: MUST the `changelog` command MUST generate `CHANGELOG.md` grouping commits by minor releases (semver tags where `patch=0` AND version `>=0.1.0`); MUST include only minor releases by default with all commits between consecutive minor releases (from repository beginning for the first minor); MUST produce an empty changelog body when no minor releases exist; MUST list releases reverse-chronologically (newest first).
- **REQ-019**: MUST alias `bd` accept exactly one local branch target, MAY accept one leading `--force`, and MUST NOT accept any other flags or extra operands.
- **REQ-138**: MUST `bd` execute `git branch -d <branch>` when the target branch has no associated worktree and `--force` is absent.
- **REQ-139**: MUST `bd` and `wtd` derive worktree-to-branch associations from `git worktree list --porcelain` before evaluating deletion targets.
- **REQ-140**: MUST when an association exists and `--force` is absent, `bd` and `wtd` preflight both deletions and abort before changes if either the worktree or branch cannot be deleted.
- **REQ-141**: MUST when an association exists and deletion proceeds, `bd` and `wtd` delete the associated worktree before deleting the associated local branch.
- **REQ-142**: MUST after paired deletion, `bd` and `wtd` print explicit English output identifying the deleted worktree path and branch name.
- **REQ-020**: MUST provide reusable checks for unstaged changes, staged changes, and remote-forward status of configured `develop` and `master`, including remote reference update before ahead/behind evaluation.
- **REQ-021**: MUST implement `wip` using the fixed message `wip: work in progress.`; MUST call `aa` (stage all) when staging is empty and working-tree is dirty; MUST fail with explicit error when both working-tree and staging have no committable data.
- **REQ-022**: MUST aliases `new`, `fix`, `change`, `implement`, `refactor`, `docs`, `style`, `revert`, `misc`, and `cover` execute conventional commits; MUST call `aa` when staging is empty and working-tree is dirty; MUST fail with explicit error when both working-tree and staging have no committable data; MUST reuse WIP-amend decision logic used by `cm` and `wip`.
- **REQ-115**: MUST conventional aliases require non-empty commit text and support optional `<module>: <description>` prefix parsing before message construction.
- **REQ-116**: MUST resolve omitted module from `.galias.conf.default_commit_module`; when key is absent use hardcoded default `""`; when effective module is empty emit `<type>: <description>`, otherwise emit `<type>(<module>): <description>`.
- **REQ-117**: MUST uppercase the first character of `<description>` unless numeric and MUST append `.` when `<description>` does not already end with a period.
- **REQ-023**: MUST keep all `core.py` output messages (stdout/stderr, normal/verbose/debug, help/errors) in English.
- **REQ-025**: MUST require exactly one `major.minor.patch` argument for `chver`, update matching version occurrences from active `ver_rules`, and re-run `ver` to confirm the requested target version.
- **REQ-026**: MUST the `major`, `minor`, and `patch` commands MUST automate version release by incrementing the corresponding semver index (resetting lower-order indices), MUST share the same support implementation, MUST accept `--include-patch` flag forwarded to `changelog` together with `--force-write`, MUST accept `--dev`/`--develop` per REQ-200, and MUST accept `--exec <command> [params...]` per REQ-166, REQ-167, and REQ-168 with the optional injected exec release step between version update and staging; the `patch` command MUST automatically include `--include-patch` in the changelog regeneration step even when the flag is not supplied by the user; the `major` and `minor` commands MUST NOT automatically include `--include-patch`, MUST enforce release prerequisites on configured local branches (`master`, `develop`, `work`), configured remotes (`origin/master`, `origin/develop`), remote update status for `master` and `develop`, current branch equal to `work`, clean working tree, and empty index, MUST print release step logs in the `--- [release:<level>] ... ---` format with one blank line before the first release step, and after `chver` plus staging MUST create the first release commit by amending HEAD when HEAD is an amendable `wip: work in progress.` commit not yet contained in configured `develop` and `master` or by creating a new commit otherwise; before changelog regeneration the flow MUST create a temporary annotated `v<target>` tag on configured local `work`, MUST regenerate changelog, and MUST delete that temporary local tag before any branch integration.
- **REQ-166**: MUST accept `--exec <command> [params...]` on `major`, `minor`, and `patch`, parsed by `_parse_release_flags` with rest-of-argv semantics, keeping captured operands separate from `changelog_args`.
- **REQ-167**: MUST when `--exec` is supplied, execute the captured command as an argv list without shell, with repository root as CWD and inherited stdio, as a release step between version update and staging.
- **REQ-168**: MUST abort the release with the `--- [release:<level>] Step ... failed: ... ---` diagnostic when the `--exec` command exits non-zero, before any staging, commit, tag, or push.
- **REQ-027**: MUST the internal `cmd_release` function MUST reuse the same staging/worktree readiness and WIP amend decision logic used by `wip`, MUST determine the current version via `ver` before committing, MUST fail with the propagated detection error when version resolution fails, MUST create a `release: Release version <ver>` commit (where `<ver>` is `major.minor.patch`) by amending HEAD only when HEAD is an amendable `wip: work in progress.` commit not yet contained in configured `develop` and `master` and otherwise by creating a new commit, and MUST remain unavailable as a user-exposed CLI command.
- **REQ-028**: MUST implement `ra` as inverse of `aa` by requiring configured `work` branch, no pending unstaged changes, and non-empty staging before unstaging all indexed entries.
- **REQ-029**: MUST print usage with package version suffix `(x.y.z)` when CLI is invoked without command arguments.
- **REQ-030**: MUST when invoked with `--ver` or `--version`, force an online update check that ignores `~/.cache/galias/check_version_idle-time.json` and then print the package version and exit successfully.
- **REQ-031**: MUST keep all CLI output messages in English, including usage/help/info/debug/error paths.
- **REQ-033**: MUST execute update checks before CLI argument validation only when `~/.cache/galias/check_version_idle-time.json` does not exist or its `idle_until_unix` timestamp is expired, except when REQ-030 mandates a forced online check.
- **REQ-034**: MUST run `git remote -v`, print unique remote names, and run `git remote show <remote>` for each discovered remote in alias `str`.
- **REQ-035**: MUST support `ver --verbose` (per-file regex outcome output) and `ver --debug` (full glob-match listing for each rule pattern).
- **REQ-036**: MAY provide repository-local Doxygen generation assets; when present they SHOULD generate documentation under `doxygen/` from `src/`; CLI runtime and release workflow MUST remain functional when such assets are absent.
- **REQ-037**: MUST visual diff aliases `dwc`, `dcc`, and `dw` execute through the environment-aware diff wrapper (REQ-189) with ref operands `HEAD`, `HEAD~1 HEAD`, and exactly one positional `<ref>` respectively, forwarding tool errors unchanged.
- **REQ-182**: MUST `dc` accept exactly one required positional git ref `<ref>` plus at most one optional positional git ref `<ref_prev>` and MUST reject zero or extra positional refs with an explicit English usage error.
- **REQ-183**: MUST `dc` execute `git difftool -d <ref_prev> <ref>` so the shown diff direction is `<ref_prev>` -> `<ref>` and MUST NOT invert the operand order.
- **REQ-184**: MUST `dc` resolve an omitted `<ref_prev>` to the commit preceding `<ref>` (`<ref>~1`) before diff execution.
- **REQ-185**: MUST `core.py` execute every external command through the shared `_run_checked` subprocess wrapper, allowing no direct `subprocess.run` or `subprocess.Popen` calls elsewhere.
- **REQ-186**: MUST global configuration support paired keys `<id>_command` (terminal) and `<id>_command_gfx` (graphical) for `id` in `edit`, `gp`, `gr`, and `diff` in `$HOME/.config/galias/config.json`.
- **REQ-187**: MUST command resolution detect graphical environments as non-POSIX `os.name` or non-empty `DISPLAY`/`WAYLAND_DISPLAY` on POSIX, selecting `<id>_command_gfx` when graphical and `<id>_command` otherwise.
- **REQ-188**: MUST an absent or empty `<id>_command_gfx` value in a graphical environment fall back to the `<id>_command` value.
- **REQ-189**: MUST visual diff aliases execute `git difftool -d` with the environment-resolved `diff_command`/`diff_command_gfx` value injected as `--extcmd=<command>`, followed by their ref operands and extra arguments.
- **REQ-190**: MUST visual diff execution omit `--extcmd` and run plain `git difftool -d <refs> <extras>` when the resolved diff command is empty.
- **REQ-191**: MUST set `DEFAULT_CONFIG` values for the eight REQ-186 global command keys to `edit_command="edit"`, `edit_command_gfx="sublime_text"`, `diff_command="icdiff"`, `diff_command_gfx="meld"`, `gr_command="tig"`, `gr_command_gfx="gitg"`, `gp_command="gitui"`, and `gp_command_gfx="sublime_merge --multiinstance ."`.
- **REQ-192**: MUST print the eight REQ-186 global command keys contiguously, in the exact order `edit_command`, `edit_command_gfx`, `diff_command`, `diff_command_gfx`, `gr_command`, `gr_command_gfx`, `gp_command`, `gp_command_gfx`, in Configuration Parameters output.
- **REQ-038**: MUST the visual diff aliases include `dwcc` with refs `HEAD~1` and `dccc` with refs `HEAD~2 HEAD`, both executed through the environment-aware diff wrapper (REQ-189), and both aliases MUST expose explicit help text in global and per-command help outputs.
- **REQ-039**: MUST every command `<command>` present in the CLI command dispatch map MUST be implemented by a Python function named exactly `cmd_<command>`, and the dispatch entry for `<command>` MUST reference that exact function symbol.
- **REQ-040**: MUST the `changelog` `--include-patch` option MUST prepend the chronologically latest patch release after the last minor release, including all commits from the last minor to that patch; if no minor release exists MUST include only the latest patch with all commits from the beginning.
- **REQ-041**: MUST the `changelog` command MUST support `--force-write`, `--print-only`, and `--disable-history`; command help MUST list all available options; disk writes MUST occur only when `CHANGELOG.md` is absent or `--force-write` is provided.
- **REQ-042**: MUST the `changelog` commit parser MUST recognize types: `new` (Features), `implement` (Implementations), `fix` (Bug Fixes), `change` (Changes), `cover` (Cover Requirements), `refactor` (Refactor), `docs` (Documentation), `style` (Styling), `revert` (Revert), `misc` (Miscellaneous Tasks); MUST parse headers `<type>:`, `<type>(<module>):`, `<type>!:`, and `<type>(<module>)!:` extracting type, optional module, optional breaking marker, and description; MUST ignore `perf`, `test`, `build`, `ci`, `chore`; MUST ignore commits whose subject matches `release: Release version <semver>`; MUST NOT generate an "Other" section; Implementations section header MUST use the 🏗️ icon.
- **REQ-043**: MUST the `changelog` `# History` section MUST be enabled by default, MUST be skipped when `--disable-history` is provided, and MUST be skipped when owner/repository resolution via REQ-046 fails with command error.
- **REQ-044**: MUST each `changelog` entry MUST remove lines matching `^Co-authored-by:.*` before normalization and MUST remove empty lines from commit descriptions.
- **REQ-045**: MUST `major`, `minor`, and `patch` invoked with `--dev`/`--develop` integrate only configured `develop` and atomically push that branch with only `refs/tags/v<target>` to `origin`, leaving `master` unchanged.
- **REQ-046**: MUST the `changelog` GitHub URL resolver MUST query `git config branch.<master_branch>.remote` (fallback `origin`) and `git remote get-url <remote>`; MUST parse SSH/HTTPS URL formats into `<owner>` and `<repo>` using shared string-parsing utilities; MUST NOT perform network operations.
- **REQ-047**: MUST the `backup` command MUST enforce the same preflight checks and error reporting used by the `major`/`minor`/`patch` workflows, including: current branch equals configured `work`, clean working tree, empty index, and remote-update checks for configured `develop` and `master`.
- **REQ-048**: MUST the `backup` command MUST merge the configured local `work` branch into the configured local `develop` branch, and MUST push the updated `develop` branch to its configured remote tracking branch.
- **REQ-049**: MUST on success, the `backup` command MUST checkout back to configured `work` and MUST print a success message stating that all local `work` changes were merged and pushed to the configured remote `develop`.
- **REQ-068**: MUST without `--include-patch`, `# History` MUST contain only minor-release tags present in the changelog body; with `--include-patch`, it MUST additionally include the latest patch tag, using last minor or repository start as diff baseline.
- **REQ-069**: MUST `# History` release links MUST use template `https://github.com/<OWNER>/<REPO>/releases/tag/<TAG>` and diff links MUST use template `https://github.com/<OWNER>/<REPO>/compare/<TAG_FROM>..<TAG_TO>` generated deterministically from local changelog tags.
- **REQ-070**: MUST `# History` generation MUST NOT verify remote tag existence and MUST NOT query remote tags; changelog tag and commit collection MUST use only local git commands.
- **REQ-072**: MUST `major`, `minor`, and `patch` without `--dev` create definitive annotated `v<target>` on configured `master` before publication, push only configured `develop` first, then atomically push configured `master` with only that release tag.
- **REQ-200**: MUST `major`, `minor`, and `patch` accept equivalent flags `--dev` and `--develop` parsed by `_parse_release_flags`, selecting the develop-scoped release workflow per REQ-045.
- **REQ-201**: MUST when `--upgrade --develop` (equivalent `--dev`) is invoked on Linux, install the newest GitHub release tag resolved per REQ-208, selected regardless of the branch containing it.
- **REQ-202**: MUST `--ver`/`--version` print the installed version plus the latest versions available on PyPI (REQ-124) and GitHub (REQ-204) as three REQ-241-aligned lines before exiting successfully.
- **REQ-203**: MUST reject `--develop` or `--dev` when the first CLI token is neither `--upgrade`, `major`, `minor`, nor `patch`, with an explicit English error and non-zero exit.
- **REQ-204**: MUST resolve the GitHub release-check URL exactly as `https://api.github.com/repos/Ogekuri/GAlias/releases/latest` and parse `tag_name`, stripping one leading `v`.
- **REQ-208**: MUST resolve the `--upgrade --develop`/`--dev` install ref by querying `https://api.github.com/repos/Ogekuri/GAlias/releases/latest` and parsing `tag_name` verbatim.
- **REQ-209**: MUST execute `uv tool install --from git+https://github.com/Ogekuri/GAlias@<tag> galias` without forcing options on Linux when `--force` is absent, where `<tag>` is the REQ-208-resolved `tag_name`.
- **REQ-210**: MUST abort `--upgrade --develop`/`--dev` with an explicit English error and non-zero exit when REQ-208 resolution fails, without executing any install.
- **REQ-230**: MUST when GitHub latest-version resolution fails during `--ver`/`--version`, print the REQ-241 `Latest @ GitHub` line with version text `unknown (<reason>)`, where `<reason>` is a non-empty English description of the intercepted failure.
- **REQ-231**: MUST derive `<reason>` for GitHub HTTP transport failures from the HTTP status code, the HTTP reason phrase, and the API-provided `message` field when present; MUST derive `<reason>` from the exception text for every other GitHub resolution failure.
- **REQ-214**: MUST document in `--upgrade` inline help that `--develop`/`--dev` select the newest GitHub release tag as install source.
- **REQ-215**: MUST document in `major`, `minor`, and `patch` inline help that `--develop`/`--dev` select the develop-scoped release workflow of REQ-045.
- **REQ-216**: MUST document in `README.md` that `--develop`/`--dev` mean GitHub-source install with `--upgrade` and develop-scoped release with `major`, `minor`, and `patch`.
- **REQ-176**: MUST `major`, `minor`, and `patch` accept standalone `--resume`, optionally combined with `--dev`/`--develop` per REQ-200, and document its recovery behavior in command help.
- **REQ-177**: MUST resume validate a clean index/worktree, configured work release-commit version, requested level compatibility, matching integrated branch tips, and the existing annotated release tag targeting that commit before publication.
- **REQ-178**: MUST resume query current remote branch and tag identities and reject conflicting tags, missing branches, or remote branch tips not ancestral to the prepared release commit before any push.
- **REQ-179**: MUST resume publish only missing branch/tag updates and restore configured work checkout while preserving version files, existing commits, and tag objects, including when publication already completed.
- **REQ-180**: MUST release push failures report the prepared version, local and remote branch/tag references to inspect, and the matching `g <level> --resume` recovery command including `--dev` for develop-scoped releases.
- **REQ-181**: MUST release publication attempt each required push once per invocation, propagate rejection diagnostics, and retain the prepared local release for explicit recovery.
- **REQ-073**: MUST the `lt` alias MUST print one line per tag as `<tag>: <branch_1>, <branch_2>, ...`, where branches are the refs returned by `git branch -a --contains <tag>` after marker trimming.
- **REQ-074**: MUST the alias `wt` MUST execute `git worktree` and `wtl` MUST execute `git worktree list`, while both aliases forward all provided arguments unchanged.
- **REQ-075**: MUST the alias `wtl` MUST accept and forward `-v`, `--porcelain`, and `-z` options as native `git worktree list` arguments without CLI-side transformation.
- **REQ-076**: MUST the alias `wtp` MUST execute `git worktree prune` and MUST forward `-n`, `-v`, `--expire <expire>`, and additional git-compatible arguments unchanged.
- **REQ-077**: MUST the user-exposed worktree-delete alias be named `wtd`, accept exactly one `<worktree>` target, MAY accept one leading `--force`, and MUST NOT accept any other flags or extra operands.
- **REQ-143**: MUST the `wtd` worktree-delete alias execute `git worktree remove <worktree>` when the target worktree has no associated local branch and `--force` is absent.
- **REQ-144**: MUST when `--force` is supplied without an association, `bd` execute `git branch -D <branch>` and `wtd` execute `git worktree remove --force <worktree>`.
- **REQ-145**: MUST when `--force` is supplied with an association, `bd` and `wtd` delete the associated worktree with `git worktree remove --force <path>` before deleting the branch with `git branch -D <branch>`.
- **REQ-078**: MUST changelog markdown MUST render one top-level bullet per commit as `- <description> *(<scope>)*`, where the ` *(<scope>)*` suffix is present only when the parsed scope is non-empty.
- **REQ-232**: MUST indent every rendered changelog description line after the first with two spaces to align it with the top-level bullet text.
- **REQ-233**: MUST changelog rendering MUST NOT insert blank separator lines between consecutive top-level commit bullets.
- **REQ-234**: MUST changelog rendering strip a leading markdown bullet marker (`-`, `*`, `+`, `1.`, `1)`) from every cleaned description line after the first.
- **REQ-235**: MUST changelog rendering collapse each maximal run of consecutive bullet-item description lines after the first into one line whose item texts are joined by `'; '`.
- **REQ-236**: MUST execute `uv tool install galias --force --reinstall --refresh` when `--upgrade --force` without `--develop` or `--dev` is invoked on Linux.
- **REQ-237**: MUST execute `uv tool install --force --reinstall --refresh --from git+https://github.com/Ogekuri/GAlias@<tag> galias` when `--upgrade --develop`/`--dev` runs with `--force` on Linux.
- **REQ-238**: MUST accept `--force` as an auxiliary `--upgrade` flag combinable with `--develop`/`--dev`, and MUST reject `--force` as the first CLI token with any other command through an explicit English error and non-zero exit.
- **REQ-239**: MUST document in `--upgrade` inline help that `--force` forces download and complete reinstallation through the uv forcing options.
- **REQ-240**: MUST document in `README.md` that `--upgrade --force` forces download and complete reinstallation on both the PyPI and the GitHub install sources.
- **REQ-241**: MUST render each `--ver`/`--version` line as its label left-justified in an 18-character field followed by `: <version>`, using the labels `Current Installed`, `Latest @ PyPI`, and `Latest @ GitHub` in this order.
- **REQ-079**: MUST the `ls` alias MUST run `git ls-files --exclude-standard` and MUST pass any additional arguments to the git command unchanged.
- **REQ-080**: MUST the `lsi` alias MUST run `git ls-files --others --ignored --exclude-standard`, MUST filter output by excluding paths where any path component matches any entry in `LSI_DEFAULT_EXCLUDED_DIRS` or ends with any suffix in `LSI_DEFAULT_EXCLUDED_DIR_SUFFIXES`, and MUST pass any additional arguments to the git command unchanged.
- **REQ-081**: MUST the `lsa` alias MUST run `git ls-files --others --exclude-standard` and MUST pass any additional arguments to the git command unchanged.
- **REQ-082**: MUST the CLI MUST expose an `o` alias in `COMMANDS` and `HELP_TEXTS`, and `--help` outputs MUST include `o` in global and per-command help paths.
- **REQ-083**: MUST the `o` alias MUST terminate with non-zero exit when executed outside a Git repository and MUST print an explicit English error message to stderr.
- **REQ-084**: MUST the `o` alias MUST print sections in order as: section 1 working area context, section 2 branch distances, section 3 active worktrees, section 4 qualitative topology, section 5 branches, and section 6 current-branch state only when `WorkingTree` state is not `clean`.
- **REQ-085**: MUST the `o` alias MUST always use configured `work`, `develop`, and `master` branch names, MUST print identifiers `Work(⎇ <work>)`, `Develop(⎇ <develop>)`, `Master(⎇ <master>)`, and MUST print `Current Branch: <Logical>(⎇ <current>)`.
- **REQ-086**: MUST the `o` alias MUST print verbose divergence rows with explicit configured labels and remote labels `RemoteDevelop(⎇ origin/<develop>)` and `RemoteMaster(⎇ origin/<master>)`, using `git rev-list` counts when compared refs exist.
- **REQ-087**: MUST the `o` alias MUST color ahead counters with bright green (`\033[92m`) and behind counters with bright red (`\033[31;1m`); zero-value counters and non-delta text MUST remain white.
- **REQ-088**: MUST the `o` alias MUST render section titles in purple (`\033[35;1m`), branch/remote identifier tuples `(⎇ <name>)` in bright yellow (`\033[38;5;226m`), subsection titles in bright white, and every rendered `Work(⎇ <work>)` logical prefix in bright green (`\033[92m`) when state is `clean`, bright red (`\033[31;1m`) when state is `unstaged`, otherwise bright white (`\033[97m`), reusing the same formatting in all sections.
- **REQ-089**: MUST the `o` alias MUST print section 4 with title `QUALITATIVE TOPOLOGY` and MUST render a chronological-position tree where node placement derives from actual commit positions in the repository history.
- **REQ-090**: MUST the section-4 infographic MUST include `WorkingTree`, `Work`, `Develop`, `RemoteDevelop`, `Master`, and `RemoteMaster`; MUST resolve each ref hash via `git rev-parse`; MUST group refs sharing the same commit hash on the same output line except `WorkingTree`; MUST order nodes by descending `git rev-list --count` from the octopus merge-base of available refs.
- **REQ-091**: MUST the section-4 infographic MUST NOT emit qualitative-state labels (`in_sync`, `ahead`, `behind`, `diverged`, `unknown`) in the topology output lines.
- **REQ-092**: MUST the section-4 root node MUST be the node or group with the highest commit count from the merge-base; remaining nodes MUST appear as `|-- ` children ordered by descending commit count; `WorkingTree` MUST be positioned immediately above the line containing `Work` when at the same commit position or when the working tree is dirty.
- **REQ-093**: MUST the section-4 infographic MUST preserve the overview color contract: purple section title, yellow `(⎇ <name>)` tuples, and white generic text including tree connectors and `WorkingTree` state annotation.
- **REQ-094**: MUST the `o` alias MUST execute `git worktree list --verbose` in section 3, MUST execute `git status -sb` only when `WorkingTree` state is not `clean`, and in section 6 MUST normalize the status header line from `## <branch>` to `## <Logical>(⎇ <branch>)` using the same color formatting as section-1 `Current Branch`, and MUST render each non-header status line two-character status prefix in bright red (`\033[31;1m`).
- **REQ-095**: MUST the section-4 `WorkingTree` node MUST display `WorkingTree [<state>]` where `<state>` is the working-tree state string (`clean`, `unstaged`, `staged`, or `mixed`) derived from the same diagnostic function used by `cmd_o`.
- **REQ-096**: MUST the `o` alias MUST print section `=== 5. BRANCHES ===` with configured aligned rows for `Work`, `Develop`, `Master`, `RemoteDevelop`, `RemoteMaster`, formatted `<Identifier> | <latest commit subject>`; commit subject text MUST be uncolored and MUST strip ANSI escape sequences before rendering.
- **REQ-097**: MUST restrict configuration-file value changes to explicit `--set` or `--unset` invocations plus REQ-272 default initialization.
- **REQ-098**: MUST the CLI MUST expose an `l` alias in `COMMANDS` and `HELP_TEXTS`, and `--help` outputs MUST include `l` in global and per-command help paths.
- **REQ-099**: MUST the `l` alias MUST render a text-based tree visualization of git commit history by invoking `git log --date-order` with a custom pretty format and processing the output through a vine-based graph algorithm.
- **REQ-100**: MUST each `l` output line display columns in fixed order (hash, date `%Y-%m-%d %H:%M`, graph, author, refs, subject), and MUST truncate rendered line length to current terminal width resolved via `shutil.get_terminal_size`.
- **REQ-101**: MUST the `l` alias MUST support `--style=<n>` with values: 1 (single-line Unicode, default), 2 (double-line Unicode), 10 (rounded Unicode edges), 15 (bold-line Unicode).
- **REQ-102**: MUST the `l` alias MUST use configurable graph symbols with defaults: commit `●`, merge `◎`, overpass `═`, root `■`, tip `○`; overridable via `--graph-symbol-commit=<s>`, `--graph-symbol-merge=<s>`, `--graph-symbol-overpass=<s>`, `--graph-symbol-root=<s>`, `--graph-symbol-tip=<s>`.
- **REQ-103**: MUST the `l` alias MUST apply ANSI color scheme: tree (cyan `\033[0;36m`), hash (magenta `\033[0;35m`), date (blue `\033[0;34m`), author (yellow `\033[0;33m`), tag (bold magenta `\033[1;35m`), default (reset `\033[0m`); `--no-color` MUST disable all ANSI color output.
- **REQ-104**: MUST the `l` alias support `--all`, `--reverse`, `--abbrev=<n>` (4..40), `--svdepth=<n>` (default 2), `--no-status`, and `--wrap`; `--wrap` MUST disable terminal-width truncation and preserve full rendered lines.
- **REQ-105**: MUST the `l` alias MUST support `--graph-margin-left=<n>` (left margin columns, default 2) and `--graph-margin-right=<n>` (right margin columns, default 1) controlling spacing around the graph tree segment.
- **REQ-106**: MUST the `l` alias MUST display working tree status indicators appended to the HEAD ref decoration: `*` (unstaged changes), `+` (staged changes), `$` (stash entries), `%` (untracked files); the status display MUST be disabled when `--no-status` is specified.
- **REQ-107**: MUST the `l` alias MUST detect and display mid-flow state indicators appended to the working tree status: `|REBASE-i`, `|REBASE-m`, `|REBASE`, `|AM`, `|AM/REBASE`, `|MERGING`, `|CHERRY-PICKING`, `|REVERTING`, `|BISECTING`.
- **REQ-108**: MUST the `l` alias MUST detect an active interactive rebase state and annotate the ref map with `rebase/next`, `rebase/onto`, and `rebase/new` markers at the corresponding commit SHA positions.
- **REQ-109**: MUST the `l` alias MUST implement a vine-based graph algorithm with three phases per commit: vine_branch (draw branch convergence connectors), vine_commit (place commit node and assign tip positions), vine_merge (draw merge fan-out connectors and allocate parent vine slots).
- **REQ-110**: MUST the `l` alias MUST cycle branch colors from a predefined palette (`blue_bold`, `yellow_bold`, `magenta_bold`, `green_bold`, `cyan_bold`) with neighbor-avoidance logic ensuring adjacent branches use distinct colors.
- **REQ-111**: MUST the `l` alias inject `-n 25` only when invoked with no user arguments, and MUST pass all user-provided unrecognized arguments through to `git log` unchanged without appending `-n 25`.
- **REQ-112**: MUST trigger GitHub release workflow `release-pypi.yml` on `workflow_dispatch` and pushed tags matching `v<major>.<minor>.<patch>`; execution MUST continue only when `${GITHUB_SHA}` is contained in `origin/master` or `origin/develop`.
- **REQ-113**: MUST attest build provenance for the pre-built `dist/*` release artifacts contained in the tagged release commit, and MUST NOT build any distribution inside GitHub Actions.
- **REQ-114**: MUST publish a non-draft, non-prerelease GitHub Release for the triggering tag, uploading the pre-built `dist/**/*` assets of the tagged commit using changelog content produced by the configured changelog-builder step.
- **REQ-193**: MUST grant workflow `release-pypi.yml` top-level permissions `contents: write`, `id-token: write`, and `attestations: write` for release publication and PyPI OIDC Trusted Publishing.
- **REQ-194**: MUST publish the pre-built `dist/` distributions of the tagged release commit to PyPI project `galias` through `pypa/gh-action-pypi-publish` using OIDC Trusted Publishing without API tokens or username/password credentials.
- **REQ-195**: MUST execute PyPI publication as post-steps after the GitHub Release step while preserving existing artifact-verification, attestation, changelog, and release steps in `release-pypi.yml`.
- **REQ-205**: MUST execute the PyPI publication step (REQ-194) only when the triggering tag commit `${GITHUB_SHA}` is contained in `origin/master`.
- **REQ-206**: MUST skip PyPI publication and execute all remaining release workflow steps when the triggering tag commit is contained in `origin/develop` and not in `origin/master`.
- **REQ-211**: MUST execute all `release-pypi.yml` automation on the GitHub Actions Node24 runner generation or newer, preserving every existing release step, trigger, gate, and publication behavior.
- **REQ-212**: MUST NOT set `FORCE_JAVASCRIPT_ACTIONS_TO_NODE24` or `ACTIONS_ALLOW_USE_UNSECURE_NODE_VERSION` in any repository workflow file.
- **REQ-213**: MUST reference Node24-based action majors `actions/checkout@v5`, `actions/setup-python@v6`, and `actions/attest-build-provenance@v3` in `release-pypi.yml`.
- **REQ-207**: MUST resolve configured `ver_rules` entries from JSON objects containing `pattern` and `regex`, with `regex` optional for negation patterns; entries without a `pattern` value MUST be ignored.
- **REQ-196**: MUST declare PyPI-compliant `[project]` metadata in `pyproject.toml`: `name = "galias"`, `description`, `readme`, `requires-python`, `keywords`, `classifiers`, and project URLs.
- **REQ-197**: MUST declare the `pyproject.toml` project license as the PEP 639 SPDX expression `GPL-3.0-only` with explicit `license-files` including `LICENSE`.
- **REQ-198**: MUST document `uv tool install galias` as the primary `README.md` install method (Astral uv, PyPI source) with a dedicated uvx alternative-usage section and a dedicated non-primary GitHub install section covering `--upgrade --develop`.
- **REQ-199**: MUST source default update checks and default self-upgrades exclusively from PyPI project `galias`; only REQ-201 upgrades and REQ-202 version reporting query GitHub.
- **REQ-115**: MUST section `=== 5. BRANCHES ===` append, after configured rows, aligned `<Identifier> | <latest commit subject>` rows for every discovered local or remote branch not already rendered.
- **REQ-119**: MUST visual diff aliases `dcd`, `dcm`, and `ddm` execute through the environment-aware diff wrapper (REQ-189) with refs `<develop> <work>`, `<master> <work>`, and `<master> <develop>` from `.galias.conf`, each exposing explicit help text in help outputs.
- **REQ-120**: MUST define `LSI_DEFAULT_EXCLUDED_DIRS` as a `frozenset` containing: `.cache`, `.claude`, `.codex`, `.eslintcache`, `.gemini`, `.git`, `.github`, `.kiro`, `.mypy_cache`, `.npm`, `.opencode`, `.parcel-cache`, `.pytest_cache`, `.ruff_cache`, `.sass-cache`, `.terragrunt-cache`, `.tox`, `.venv`, `.vscode`, `__pycache__`, `build`, `dist`, `htmlcov`, `node_modules`, `temp`, `tmp`, `venv`.
- **REQ-121**: MUST the `lsi` alias MUST accept `--include-all` flag; when present, MUST bypass `LSI_DEFAULT_EXCLUDED_DIRS` and `LSI_DEFAULT_EXCLUDED_DIR_SUFFIXES` filtering and print all ignored files unfiltered.
- **REQ-123**: MUST when a newer version is detected, print a bright-green (`\033[92;1m`) message `Update available: <latest> (installed: <current>)` before command execution.
- **REQ-124**: MUST resolve the release-check URL exactly as `https://pypi.org/pypi/galias/json` and parse the latest version from its `info.version` JSON field.
- **REQ-125**: MUST execute release-check HTTP requests with a hardcoded configurable timeout defaulting to 2 seconds.
- **REQ-126**: MUST after successful release checks write `~/.cache/galias/check_version_idle-time.json` JSON fields `last_check_unix`, `last_check_human`, `idle_until_unix`, and `idle_until_human`, with `idle_until_unix = last_check_unix + 3600`.
- **REQ-127**: MUST print bright-red (`\033[31;1m`) update-check errors, including HTTP status diagnostics and API-provided messages such as `rate limit exceeded`.
- **REQ-128**: MUST package and distribute every runtime-required file for CLI execution in uv release artifacts via explicit setuptools configuration in `pyproject.toml`; the sdist content is defined by REQ-304 and REQ-305.
- **REQ-129**: MUST define a hardcoded `idle_delay_seconds` value equal to `3600` for successful release-check scheduling.
- **REQ-130**: MUST define a hardcoded `error_idle_delay_seconds` value equal to `86400` for version-check error scheduling.
- **REQ-131**: MUST on any version-check error calculate `idle_until_unix = now + error_idle_delay_seconds`.
- **REQ-136**: MUST create directory `~/.cache/galias` before writing update-check idle-time state when the directory does not exist.
- **REQ-137**: MUST on any version-check error rewrite `~/.cache/galias/check_version_idle-time.json` with synchronized `last_check_*` and `idle_until_*` fields before returning control.
- **REQ-122**: MUST define `LSI_DEFAULT_EXCLUDED_DIR_SUFFIXES` as a `tuple` containing: `.egg-info`.
- **REQ-132**: MUST expose `rollback` as a CLI command in `COMMANDS` and `HELP_TEXTS`, and MUST support `git rollback --help` output.
- **REQ-133**: MUST `rollback` execute only when both working tree and staging area are clean; otherwise MUST print explicit English error and exit non-zero.
- **REQ-134**: MUST `rollback` accept exactly one `<target>` argument resolvable to a commit hash or tag reachable from `HEAD`; unresolved or unreachable targets MUST fail with explicit English error.
- **REQ-135**: MUST `rollback` create one non-amend commit restoring branch content to `<target>` by reverting `<target>..HEAD`; commit subject MUST be `revert: Roll back branch to <target> (<resolved_hash>).`; post-commit index and working tree MUST be clean.
- **REQ-169**: MUST `rollback` execute the canonical version detection check used by `major`, `minor`, and `patch` as pre-flight validation after target validation.
- **REQ-170**: MUST `rollback` terminate with non-zero exit and explicit English guidance when version rules are missing or the pre-flight version detection fails.
- **REQ-171**: MUST `rollback` store the detected current application version when the pre-flight version check succeeds.
- **REQ-172**: MUST `rollback` restore the stored application version through the `chver` flow after applying inverse revert changes and before the revert commit.
- **REQ-173**: MUST `rollback` stage restored version files so the revert commit preserves the pre-rollback version.
- **REQ-174**: MUST `rollback` abort through `git revert --abort` before creating the revert commit with explicit English error and non-zero exit when the version restore fails.
- **REQ-175**: MUST `rollback` inline help and `README.md` documentation describe the version pre-flight check and version preservation behavior.
- **REQ-146**: MUST expose `get` as a CLI command in `COMMANDS` and `HELP_TEXTS`, and MUST support `git get --help` output.
- **REQ-147**: MUST `get` reject any positional arguments and exit non-zero with explicit English error when extra operands are supplied.
- **REQ-148**: MUST `get` abort with explicit English error when the staging area is non-empty or when the working tree has pending changes, before any remote operation.
- **REQ-149**: MUST `get` abort with explicit English error when the current branch is not the configured `work` branch.
- **REQ-150**: MUST `get` abort with explicit English error when the local configured `work` HEAD commit is not contained in the local configured `develop` branch.
- **REQ-151**: MUST `get` abort with explicit English error when the local configured `develop` and the local configured `master` branches are not aligned on the same commit.
- **REQ-152**: MUST `get` abort with explicit English error when the local configured `develop` HEAD is not contained in `origin/<develop>` or when the local configured `master` HEAD is not contained in `origin/<master>`.
- **REQ-153**: MUST `get` abort with explicit English error when `origin/<develop>` has zero pending commits relative to the local configured `develop` branch.
- **REQ-154**: MUST `get` fast-forward the local configured `master` branch from `origin/<master>` including tags, then fast-forward the local configured `develop` branch from `origin/<develop>` including tags, and finally fast-forward merge the local configured `develop` branch into the currently checked out local `work` branch.
- **REQ-155**: MUST `get` terminate with explicit English error and non-zero exit status when any fetch or merge step of the synchronization flow fails.
- **REQ-217**: MUST provide `scripts/pre-release-check.sh` as an executable Bash script validating repository readiness before an official release.
- **REQ-218**: MUST resolve the repository root from the script location so execution succeeds from any working directory.
- **REQ-219**: MUST verify `git` and Astral `uv` executables exist in PATH before validation steps and abort with explicit English errors when missing.
- **REQ-220**: MUST verify `uv.lock` synchronization with `pyproject.toml` via `uv lock --check` before test execution.
- **REQ-221**: MUST execute the complete pytest suite through `uv run pytest` and abort with non-zero exit when the suite fails.
- **REQ-222**: MUST generate release artifacts during pre-release validation exclusively by executing `scripts/build.sh`, aborting when that script exits non-zero.
- **REQ-223**: MUST NOT modify tracked repository files at any validation step.
- **REQ-226**: MUST remove at exit every generated artifact (`dist/` release artifacts, `build/`, `src/*.egg-info`), `.pytest_cache`, `src/`/`tests/` `__pycache__` directories, and its temporary directory.
- **REQ-227**: MUST preserve a pre-existing uv-managed `.venv` environment and remove at exit a `.venv` created during the run.
- **REQ-228**: MUST execute `release-pypi.yml` without any build-preparatory validation job, consuming the pre-built tagged-commit `dist/` artifacts directly.
- **REQ-229**: MUST gate `publish-release` only on the `check-branch` job via `needs`, so no test, build, or pre-release validation job participates in the release pipeline.
- **REQ-313**: MUST create GitHub Release assets exclusively from the pre-built `dist/` sdist and wheel committed in the tagged release commit, and MUST NOT execute `scripts/build.sh`, `scripts/pre-release-check.sh`, `uv build`, or `python -m build` in `release-pypi.yml`.
- **REQ-314**: MUST verify with Python 3.11 before attestation and publication that `dist/` holds exactly one git-tracked sdist and one git-tracked wheel matching the `pyproject.toml` name and version, aborting otherwise.
- **REQ-315**: MUST publish to PyPI the pre-built `dist/` distributions of the tagged release commit through REQ-194 without rebuilding them.
- **REQ-224**: MUST print one `--- [pre-release-check] <message> ---` English progress line per step plus a final success line.
- **REQ-225**: MUST abort at the first failing step with non-zero exit status and skip all subsequent steps.
- **REQ-256**: MUST define every Python module, package, class, function, variable, and constant name under `src/` using English tokens without Italian-derived identifiers.

### 3.2.1 Configuration Command Interface
- **REQ-242**: MUST derive configurable paths, types, descriptions, defaults, allowed values, and input examples from one shared schema covering every DES-006 key.
- **REQ-243**: MUST expose `--print-raw`, `--print`, `--info`, `--set`, `--unset`, and `--get` as standalone management commands with exact operand validation and command-specific `--help`.
- **REQ-244**: MUST address configuration using case-sensitive colon-separated paths rooted at `Global` or `Local`, with zero-based array indices and nested object field names.
- **REQ-245**: MUST implement `--set PATH VALUE` assigning schema-validated scalar, object, array, and map values, casting string arguments to strict schema types and accepting complex values as one JSON argument.
- **REQ-246**: MUST implement `--get PATH` by printing the selected effective scalar, array, object, or scope as JSON, resolving absent top-level keys from existing defaults.
- **REQ-247**: MUST implement `--unset PATH` by removing persisted keys, scope contents, array entries, or optional object fields, restoring existing defaults for absent top-level keys.
- **REQ-248**: MUST reject invalid paths, wrong value types, malformed JSON, invalid rule structures, and unreadable configuration with English diagnostics and non-zero status before mutation.
- **REQ-249**: MUST implement `--print-raw [Global|Local]` by emitting existing selected files byte-for-byte, global then local, with file identification and missing-file diagnostics exclusively on stderr.
- **REQ-250**: MUST implement `--print [PATH]` rendering the effective configuration as a box-drawing tree with an `Application_Configuration` root header omitted from CLI paths, printing the whole tree without PATH and only the PATH subtree otherwise.
- **REQ-251**: MUST implement `--info [PATH]` rendering the schema-derived parameter hierarchy, printing the whole tree without PATH and only the PATH subtree otherwise.
- **REQ-252**: MUST document colon paths, zero-based indices, `append`, `insert`, row, cell, and map-key tokens, unset/default semantics, and shell-quoted JSON input with application-specific examples in configuration command help.
- **REQ-253**: MUST preserve the unselected configuration file and existing alias algorithms during configuration management, including the independent repository-synchronization alias `get`.
- **REQ-254**: MUST atomically replace the selected configuration file after successful validation by writing a flushed same-directory temporary file and renaming it over the target.
- **REQ-255**: MUST permit global configuration commands outside repositories and resolve local configuration through the existing repository-root-or-current-directory policy.
- **REQ-257**: MUST label every `--print` section node with its canonical `[Path: <colon path>]` badge and render every parameter name exactly as its CLI path token.
- **REQ-258**: MUST annotate every `--print` scalar and selection value with `(default)` when equal to the schema default and `(custom | default: <default>)` otherwise.
- **REQ-259**: MUST render `--print` selections as `Sel`/`Value` tables marking the active row `[*]` and dynamic maps as `Key`/`Value` tables headed by `(<N> entries | key target: <path>:<Key>)`.
- **REQ-260**: MUST render `--print` primitive arrays as `Idx`/`Value` tables headed by `(<N> items | row target: <path>:<Idx> | add: :+)`.
- **REQ-261**: MUST render `--print` object arrays as `Idx`-plus-field tables headed by `(<N> rows | cell target: <path>:<Idx>:<Field> | add: :+)`.
- **REQ-262**: MUST render empty `--print` arrays as `(empty list — add row with: --set <path>:+ <value>)` and empty maps as `(empty map — set key with: --set <path>:<Key> <value>)`.
- **REQ-263**: MUST render each `--info` parameter as a `[<type and constraints>] <description>` header line followed by a `Default : <default>` line naming its `--unset` restore command and full-path `--set` example commands.
- **REQ-264**: MUST render `--info` selections as `Value`/`Default`/`Meaning` tables and object arrays with an `Item Schema` table followed by append, insert, update, reset, replace, delete, overwrite, and clear command examples.
- **REQ-265**: MUST implement `--set <array path>:append VALUE` (alias `:+`) by validating the item against the array schema, appending it, and printing a confirmation naming the assigned index.
- **REQ-266**: MUST implement `--set <array path>:insert:<Idx> VALUE` inserting at `<Idx>` with subsequent items shifted down, behaving as append when `<Idx>` equals the array length.
- **REQ-267**: MUST implement `--set <path>:<Idx>`, `--set <path>:<Idx>:<Field>`, and `--set <path>:<Key>` replacing a whole row, updating one object cell, and adding or updating a map key.
- **REQ-268**: MUST implement `--get <path>:<Idx>`, `--get <path>:<Idx>:<Field>`, and `--get <path>:<Key>` printing the row, cell, or map value as JSON.
- **REQ-269**: MUST implement `--unset <path>:<Idx>` deleting the row and re-indexing remaining items contiguously from zero, and `--unset <path>:<Idx>:<Field>` restoring the cell default.
- **REQ-270**: MUST reject out-of-range `--set` and `--unset` indices with exit status 1 and a stderr error stating the valid index range and the `:append` alternative.
- **REQ-271**: MUST print an English confirmation line to stdout for every successful `--set` or `--unset` mutation and exit with status 0.
- **REQ-272**: MUST create the missing global configuration directory tree and `config.json` initialized with schema defaults before executing any configuration command.
- **REQ-273**: MUST print valid `--get`, `--print`, `--print-raw`, and `--info` output to stdout with exit status 0 and error diagnostics to stderr with exit status 1.
- **REQ-274**: MUST store and display every configuration value, including credentials and API keys, in plain text without masking across `--print`, `--print-raw`, and `--get`.
- **REQ-275**: MUST indent `--print` and `--info` tree output by exactly four characters per node depth level, independent of node name, value, and metadata text lengths.
- **REQ-276**: MUST NOT pad `--print` or `--info` node names, values, or metadata prefixes to any computed column width.
- **REQ-277**: MUST render each parameter metadata entry (`Default`, `Set cmd`, `Allowed Values`, `Item Schema`, command sets, `Full overwrite`, `Reset block`) as a child of that parameter one depth level deeper using `├──` or `└──` connectors.
- **REQ-278**: MUST render `--print` and `--info` tables one depth level below their owning parameter or labelled metadata entry.
- **REQ-279**: MUST nest child parameters under their parent section node at exactly one additional depth level with `├──` or `└──` connectors.

### 3.2.2 Release Build and Pre-Release Validation Scripts
- **REQ-280**: MUST provide `scripts/build.sh` as an executable Bash script generating exactly one sdist and one wheel into `dist/` under the repository root resolved from the script location.
- **REQ-281**: MUST abort `scripts/build.sh` with explicit English errors when `uv` is missing from PATH or when `pyproject.toml` or `src/git_alias/` is absent.
- **REQ-282**: MUST remove, before every build, every `dist/galias-*.tar.gz` and `dist/galias-*.whl` release artifact of any version regardless of git tracking status, and MUST remove an emptied `dist/` directory.
- **REQ-283**: MUST build through `uv build --out-dir <temporary staging directory>` and move artifacts into `dist/` only after verifying the staging directory holds exactly one non-empty sdist and one non-empty wheel.
- **REQ-284**: MUST remove at `scripts/build.sh` exit the staging directory and every build intermediate (`build/`, `src/*.egg-info`), leaving only the produced `dist/` release artifacts, and MUST remove generated `dist/` artifacts when the build fails.
- **REQ-285**: MUST exit `scripts/build.sh` non-zero at the first failing step and print on success a summary listing each produced artifact path with its byte size.
- **REQ-286**: MUST implement `scripts/build.sh --clean` executing the REQ-282, REQ-288, and REQ-316 cleanup without building and without invoking any separate script.
- **REQ-287**: MUST implement `scripts/build.sh --list-artifacts` printing one existing `dist/` release artifact path per line, and reject unknown options with usage text and non-zero exit.
- **REQ-288**: MUST make `scripts/build.sh` and `scripts/pre-release-check.sh` refuse to delete `build/` or `src/*.egg-info` targets containing git-tracked files and report the refusal as an error.
- **REQ-289**: MUST validate before other pre-release checks that the repository root is a git work tree containing `pyproject.toml`, `uv.lock`, `README.md`, `LICENSE`, `src/git_alias/__init__.py`, `tests/`, and executable `scripts/build.sh`.
- **REQ-290**: MUST abort pre-release validation before any build or removal when `scripts/build.sh --list-artifacts` reports pre-existing release artifacts, printing each path and the `scripts/build.sh --clean` remedy.
- **REQ-291**: MUST verify Bash syntax of every `scripts/*.sh` file via `bash -n` during pre-release validation.
- **REQ-292**: MUST verify via `uv run python` that every Python file under `src/` and `tests/` compiles and that `pyproject.toml` parses as TOML.
- **REQ-293**: MUST verify version consistency across version-managed files by executing the `ver` alias with update checks disabled before test execution.
- **REQ-294**: MUST validate built artifacts as exactly one sdist and one wheel matching the `pyproject.toml` name and version, with intact archives, every `src/git_alias/*.py` module, matching metadata, and declared console scripts.
- **REQ-295**: MUST verify through `git check-ignore` that git does not ignore any built release artifact, so every artifact remains versionable.
- **REQ-296**: MUST verify the built wheel installs into an isolated uv environment where `git_alias` modules import and every declared console-script entry point loads.
- **REQ-297**: MUST run pre-release cleanup through `EXIT`, `INT`, `TERM`, and `HUP` traps and exit non-zero when interrupted, using status `128+<signal number>` when Bash dispatches the signal trap.
- **REQ-298**: MUST verify after cleanup that no generated artifact remains, the tracked-file state equals the pre-run state, and no new untracked or ignored file exists outside `.venv`.
- **REQ-299**: MUST preserve the failing-step non-zero exit status when cleanup succeeds, and MUST exit non-zero when cleanup or post-cleanup verification fails after all checks passed.
- **REQ-300**: MUST print a final `--- [pre-release-check] Result: PASSED ---` or `--- [pre-release-check] Result: FAILED (<failed step>) ---` summary line on every exit path.
- **REQ-301**: MUST keep the `.gitignore` exclude-all-then-re-include strategy and re-include root `dist/` through `!dist/` and `!dist/**/*` rules placed in the include section.
- **REQ-302**: MUST keep generated release artifacts `dist/**/*.whl` and `dist/**/*.tar.gz` git-visible by applying no exclusion rule to them after the `dist/` re-inclusion rules.
- **REQ-303**: MUST ignore directories named `dist` below the repository root level through the `/*/**/dist/` rule replacing the unanchored `dist/` rule.
- **REQ-304**: MUST restrict the sdist to runtime sources, `pyproject.toml`, `README.md`, `LICENSE`, `uv.lock`, and setuptools-generated metadata (`PKG-INFO`, `setup.cfg`, `src/galias.egg-info/SOURCES.txt`), selected by the tracked `MANIFEST.in`.
- **REQ-305**: MUST exclude from the sdist the `tests/`, `scripts/`, and `usereq/` trees, `MANIFEST.in`, and every generated `src/galias.egg-info` file except `SOURCES.txt`.
- **REQ-306**: MUST ensure parity between local execution and uv/uvx-installed execution of the packaged CLI.
- **REQ-307**: MUST verify, before moving artifacts into `dist/`, that the staged sdist contains every REQ-304 member and no REQ-305 excluded member, extending REQ-283.
- **REQ-308**: MUST validate the built sdist against REQ-304 and REQ-305 during pre-release artifact validation, extending REQ-294.
- **REQ-316**: MUST remove, before every build, the `build/` directory and every `src/*.egg-info` directory through the REQ-288 git-tracked-content guard.
- **REQ-317**: MUST execute the REQ-282, REQ-316, and REQ-288 cleanup automatically at the start of every default `scripts/build.sh` build, before `uv build`.

### 3.3 Project File Structure
```
.
├── .github/
│   └── workflows/
│       └── release-pypi.yml
├── scripts/
│   ├── build.sh
│   ├── g.sh
│   └── pre-release-check.sh
├── docs/
│   ├── REQUIREMENTS.md
│   ├── REFERENCES.md
│   └── WORKFLOW.md
├── src/
│   └── git_alias/
│       ├── __init__.py
│       ├── __main__.py
│       ├── core.py
│       └── forest.py
├── tests/
├── pyproject.toml
├── README.md
└── CHANGELOG.md
```

### 3.4 Component Organization
- `core.py` implements dispatch, command handlers, config loading/writing, git subprocess wrappers, and release/changelog flows.
- `forest.py` implements vine-based text tree rendering for git history (`l` alias).
- `release-pypi.yml` implements manual-or-tag-triggered publication of the pre-built `dist/` artifacts of the tagged release commit, GitHub Release publication, and PyPI OIDC Trusted Publishing without executing any distribution build (REQ-113, REQ-313); tag commits contained in `origin/master` or `origin/develop` run the release workflow, and only master-contained tag commits publish to PyPI (REQ-205, REQ-206). Release automation executes on the GitHub Actions Node24 runner generation without Node20 opt-out overrides (REQ-211, REQ-212, REQ-213). `publish-release` is gated only on the `check-branch` job and runs no build-preparatory validation (REQ-228, REQ-229); the workflow never executes `scripts/build.sh` or `scripts/pre-release-check.sh` (REQ-313). Artifact presence, tagged-commit tracking, and name/version agreement are verified before attestation and publication (REQ-314), and PyPI receives the unchanged pre-built distributions (REQ-194, REQ-315).
- `scripts/build.sh` implements the release-artifact build flow: prerequisite checks, automatic cleanup of every previous `dist/` release artifact of any version plus `build/` and `src/*.egg-info` (REQ-282, REQ-316, REQ-317), staged `uv build`, artifact verification, installation into `dist/`, post-build intermediate removal (REQ-284), and the `--clean`/`--list-artifacts` modes (REQ-280..REQ-288).
- `scripts/pre-release-check.sh` implements the repository-local release-readiness flow: toolchain and structure checks, syntax checks, lockfile synchronization, version consistency, full pytest execution, `scripts/build.sh` invocation, artifact validation, and signal-safe cleanup with repository-integrity verification (REQ-217..REQ-227, REQ-288..REQ-300).
- `.gitignore` implements the exclude-all-then-re-include strategy, re-includes root `dist/` release artifacts as versionable files, and excludes nested `dist` directories (REQ-301..REQ-303).
- No explicit performance optimizations identified.

### 3.5 Evidence for Added Requirements
- **REQ-112** evidence: `.github/workflows/release-pypi.yml` lines 3-7 (`workflow_dispatch` plus pushed-tag trigger), lines 18-21 and 28-51 (master/develop containment gate exporting `is_master`, `is_develop`, `is_release`).
- **REQ-113** evidence: `.github/workflows/release-pypi.yml` attestation step over `dist/*` with no `scripts/build.sh`, `uv build`, or `python -m build` invocation anywhere in the workflow.
- **REQ-114** evidence: `.github/workflows/release-pypi.yml` GitHub Release step (non-draft/non-prerelease, `files: dist/**/*` upload of the tagged-commit assets, changelog body wiring).
- **REQ-193** evidence: `.github/workflows/release-pypi.yml` lines 9-13 (top-level `permissions` granting `contents: write`, `id-token: write`, `attestations: write`).
- **REQ-194** evidence: `.github/workflows/release-pypi.yml` `pypa/gh-action-pypi-publish` step publishing the checked-out tagged-commit `dist/` directory with no credential inputs and no rebuild step.
- **REQ-195** evidence: `.github/workflows/release-pypi.yml` publish step ordered after the GitHub Release step with all preceding steps unchanged.
- **REQ-205** evidence: `.github/workflows/release-pypi.yml` lines 144-145 (publish step gated by `if: needs.check-branch.outputs.is_master == 'true'`).
- **REQ-206** evidence: `.github/workflows/release-pypi.yml` lines 54-57 (`build-release` job gated by `is_release` output covering develop-only tags) and lines 144-145 (publish step skipped when the tag is not master-contained).
- **REQ-211** evidence: `.github/workflows/release-pypi.yml` executes every job on `ubuntu-latest` with the Node24 runner default, preserving triggers, containment gate, and publication steps unchanged.
- **REQ-212** evidence: `.github/workflows/release-pypi.yml` contains no `FORCE_JAVASCRIPT_ACTIONS_TO_NODE24` and no `ACTIONS_ALLOW_USE_UNSECURE_NODE_VERSION` entries.
- **REQ-213** evidence: `.github/workflows/release-pypi.yml` pins `actions/checkout@v5` (check-branch and publish-release jobs), `actions/setup-python@v6`, and `actions/attest-build-provenance@v3`, with no `astral-sh/setup-uv@v6` step.
- **REQ-196** evidence: `pyproject.toml` `[project]` table (`name`, `description`, `readme`, `requires-python`, `keywords`, `classifiers`) plus `[project.urls]` entries.
- **REQ-197** evidence: `pyproject.toml` `license = "GPL-3.0-only"` SPDX expression, `license-files` declaration, and `build-system` `setuptools>=77.0.0` requirement.
- **REQ-198** evidence: `README.md` Quick Start primary `uv tool install galias --force` command plus the dedicated uvx alternative-usage and GitHub install sections.
- **REQ-001** evidence: `src/git_alias/core.py` `UV_TOOL_UPGRADE_COMMAND` constant (`uv tool install galias`, no forcing options, no `--from` override) executed by `upgrade_self` on Linux for the default PyPI path.
- **REQ-124** evidence: `src/git_alias/core.py` `PYPI_LATEST_VERSION_API` constant and `check_for_newer_version` `info.version` JSON parsing.
- **REQ-199** evidence: `src/git_alias/core.py` PyPI-only `PYPI_LATEST_VERSION_API`/`UV_TOOL_UPGRADE_COMMAND` constants driving the default check and upgrade paths; GitHub constants participate only via REQ-201/REQ-202 flows.
- **REQ-201** evidence: `src/git_alias/core.py` `upgrade_self(github=True)` Linux path installing through `_build_github_upgrade_command` with the REQ-208-resolved release tag.
- **REQ-202** evidence: `src/git_alias/core.py` `main` `--ver`/`--version` branch printing installed, PyPI, and GitHub latest versions through `_format_version_report_line`.
- **REQ-203** evidence: `src/git_alias/core.py` `main` rejecting `--develop`/`--dev` when the first CLI token is outside `--upgrade`/`major`/`minor`/`patch` with English stderr and non-zero exit.
- **REQ-204** evidence: `src/git_alias/core.py` `GITHUB_LATEST_RELEASE_API` constant and `_fetch_github_latest_version` `tag_name` parsing.
- **REQ-208** evidence: `src/git_alias/core.py` `_fetch_github_latest_release_tag` querying `GITHUB_LATEST_RELEASE_API` and returning the raw `tag_name`.
- **REQ-209** evidence: `src/git_alias/core.py` `_build_github_upgrade_command` composing `git+https://github.com/Ogekuri/GAlias@<tag>` for `uv tool install`.
- **REQ-210** evidence: `src/git_alias/core.py` `upgrade_self` explicit English error and non-zero exit when `_fetch_github_latest_release_tag` returns None.
- **REQ-230** evidence: `src/git_alias/core.py` `main` `--ver`/`--version` branch printing the `Latest @ GitHub` line with `unknown (<reason>)` value using the failure reason returned by `_fetch_github_latest_version`.
- **REQ-231** evidence: `src/git_alias/core.py` `_github_failure_reason` composing the reason from `HTTPError` status code, reason phrase, and the API JSON `message` field, with `_fetch_github_release_tag_with_reason` intercepting transport and payload failures.
- **REQ-214** evidence: `src/git_alias/core.py` `MANAGEMENT_HELP` `--upgrade` entry documenting the `--develop`/`--dev` GitHub latest-release install source.
- **REQ-215** evidence: `src/git_alias/core.py` `HELP_TEXTS` entries for `major`, `minor`, and `patch` documenting the develop-scoped release option.
- **REQ-216** evidence: `README.md` GitHub install and release sections documenting the dual meaning of `--develop`/`--dev`.
- **REQ-045** evidence: `src/git_alias/core.py` `_execute_release_flow` `dev_release` branch integrating/tagging/pushing configured `develop` only and `_resume_release_flow` develop-only integrated-branch set.
- **REQ-072** evidence: `src/git_alias/core.py` `_execute_release_flow` default integration tagging configured `master` and publishing configured `develop` first, then configured `master` with the release tag atomically.
- **REQ-200** evidence: `src/git_alias/core.py` `_parse_release_flags` `--dev`/`--develop` whitelist returning the develop-scope selector and `HELP_TEXTS` option documentation for `major`, `minor`, and `patch`.
- **REQ-169** evidence: `src/git_alias/core.py` `cmd_rollback` pre-flight `_determine_canonical_version` call executed after target validation.
- **REQ-170** evidence: `src/git_alias/core.py` `cmd_rollback` non-zero exits for missing `ver_rules` and `VersionDetectionError`.
- **REQ-171** evidence: `src/git_alias/core.py` `cmd_rollback` `current_version` capture after successful detection.
- **REQ-172** evidence: `src/git_alias/core.py` `cmd_rollback` `cmd_chver([current_version])` call between `git revert --no-commit` and `_execute_commit`.
- **REQ-173** evidence: `src/git_alias/core.py` `cmd_rollback` `git add --all` staging step before the revert commit.
- **REQ-174** evidence: `src/git_alias/core.py` `cmd_rollback` `git revert --abort` failure handler for the version restore step.
- **REQ-175** evidence: `src/git_alias/core.py` `HELP_TEXTS["rollback"]` and `README.md` rollback command/example entries.
- **REQ-182** evidence: `src/git_alias/core.py` `cmd_dc` arity validation rejecting zero or more than two positional refs.
- **REQ-183** evidence: `src/git_alias/core.py` `cmd_dc` `git difftool -d <ref_prev> <ref>` operand order.
- **REQ-184** evidence: `src/git_alias/core.py` `cmd_dc` `<ref>~1` default resolution for omitted `<ref_prev>`.
- **REQ-185** evidence: `src/git_alias/core.py` `_run_checked` as the sole subprocess entry point for every external command execution.
- **REQ-186** evidence: `src/git_alias/core.py` `DEFAULT_CONFIG` and `GLOBAL_CONFIG_KEYS` defining the paired global command keys.
- **REQ-187** evidence: `src/git_alias/core.py` `_is_graphical_environment` detection and `_environment_config_command_parts` key selection.
- **REQ-188** evidence: `src/git_alias/core.py` `_environment_config_command_parts` graphical fallback branch for empty `<id>_command_gfx` values.
- **REQ-189** evidence: `src/git_alias/core.py` `_run_configured_diff` `--extcmd` injection of the environment-selected `diff_command`/`diff_command_gfx` value.
- **REQ-190** evidence: `src/git_alias/core.py` `_run_configured_diff` empty-tool branch executing plain `git difftool -d`.
- **REQ-191** evidence: `src/git_alias/core.py` `DEFAULT_CONFIG` plus `DEFAULT_GP_COMMAND`/`DEFAULT_GR_COMMAND` constants defining the imposed default command values.
- **REQ-192** evidence: `src/git_alias/core.py` `DEFAULT_CONFIG` key order plus `GLOBAL_CONFIG_KEYS` order driving `print_all_help` Configuration Parameters rendering.
- **REQ-015** evidence target: schema-scoped persistence invoked by configuration `--set` and `--unset`.
- **REQ-207** evidence target: `_load_config_rules` resolves only object `pattern` and `regex` fields; configuration validation checks canonical rule structures.
- **REQ-232** evidence: `src/git_alias/core.py` `categorize_commit` prefixes each rendered continuation line with two spaces to align with the top-level bullet text.
- **REQ-233** evidence: `src/git_alias/core.py` `generate_section_for_range` appends entry blocks contiguously under each section header and emits a single trailing blank line only after each section block.
- **REQ-234** evidence: `src/git_alias/core.py` `_format_changelog_description` strips the leading markdown bullet marker (`-`, `*`, `+`, `1.`, `1)` plus whitespace) from every cleaned description line after the first.
- **REQ-235** evidence: `src/git_alias/core.py` `_format_changelog_description` collapses each maximal run of consecutive bullet-item lines into one line whose item texts are joined by `'; '`.
- **REQ-217** evidence: `scripts/pre-release-check.sh` executable Bash script implementing the official-release pre-validation entrypoint.
- **REQ-218** evidence: `scripts/pre-release-check.sh` `REPO_ROOT` resolution from `BASH_SOURCE` followed by repository-root execution.
- **REQ-219** evidence: `scripts/pre-release-check.sh` `git --version` and `uv --version` prerequisite steps with explicit English abort diagnostics.
- **REQ-220** evidence: `scripts/pre-release-check.sh` `uv lock --check` step ordered before the pytest step.
- **REQ-221** evidence: `scripts/pre-release-check.sh` `uv run pytest` step executing the complete unit-test suite.
- **REQ-222** evidence: `scripts/pre-release-check.sh` `Build release artifacts` step executing `scripts/build.sh`.
- **REQ-223** evidence: `scripts/pre-release-check.sh` validation commands preserving tracked repository content and the EXIT trap removing only script-created artifact paths.
- **REQ-226** evidence: `scripts/pre-release-check.sh` `cleanup_generated_artifacts` invoked by the `on_exit` trap, delegating build outputs to `scripts/build.sh --clean` and removing `.pytest_cache` plus `src/`/`tests/` `__pycache__` directories.
- **REQ-227** evidence: `scripts/pre-release-check.sh` `record_baseline` `VENV_PREEXISTED` flag gating `.venv` removal in `cleanup_generated_artifacts`.
- **REQ-280** evidence: `scripts/build.sh` executable script with `REPO_ROOT` resolution from `BASH_SOURCE` and `run_build` installing artifacts into `dist/`.
- **REQ-281** evidence: `scripts/build.sh` `check_build_prerequisites`.
- **REQ-282** evidence: `scripts/build.sh` `collect_release_artifacts` selecting every `dist/galias-*` release artifact regardless of version and tracking status, plus `remove_release_artifacts` and `remove_empty_dist_dir` executed before `uv build`.
- **REQ-283** evidence: `scripts/build.sh` `run_build` `uv build --out-dir "$STAGING_DIR"`, `verify_staged_artifacts`, and `install_staged_artifacts`.
- **REQ-284** evidence: `scripts/build.sh` `on_exit` trap.
- **REQ-285** evidence: `scripts/build.sh` `fail` helper and `print_build_summary`.
- **REQ-286** evidence: `scripts/build.sh` `--clean` branch executing `clean_generated_outputs` and `run_cleanup` inline.
- **REQ-287** evidence: `scripts/build.sh` `list_release_artifacts` printing every existing `dist/` release artifact and the unknown-option branch printing `print_usage` with exit status 2.
- **REQ-288** evidence: `has_tracked_content` guard inside `remove_generated_path` in `scripts/build.sh` and `scripts/pre-release-check.sh`.
- **REQ-289** evidence: `scripts/pre-release-check.sh` `validate_repository_structure`.
- **REQ-290** evidence: `scripts/pre-release-check.sh` `check_preexisting_artifacts` failing on non-empty `scripts/build.sh --list-artifacts` output before `record_baseline` sets `BASELINE_READY`, the flag gating every cleanup removal.
- **REQ-291** evidence: `scripts/pre-release-check.sh` `check_shell_syntax`.
- **REQ-292** evidence: `scripts/pre-release-check.sh` `check_python_sources`.
- **REQ-293** evidence: `scripts/pre-release-check.sh` `check_version_consistency` calling `main(["ver"], check_updates=False)` before the pytest step.
- **REQ-294** evidence: `scripts/pre-release-check.sh` `validate_release_artifacts`.
- **REQ-295** evidence: `scripts/pre-release-check.sh` `check_artifacts_not_ignored`.
- **REQ-296** evidence: `scripts/pre-release-check.sh` `check_wheel_installation` running `uv run --isolated --no-project --with <wheel>`.
- **REQ-297** evidence: `scripts/pre-release-check.sh` `on_signal` and `on_exit` trap registrations for `EXIT`, `INT`, `TERM`, and `HUP`.
- **REQ-298** evidence: `scripts/pre-release-check.sh` `verify_repository_integrity` comparing `snapshot_tracked_state` and `snapshot_untracked_files` baselines.
- **REQ-299** evidence: `scripts/pre-release-check.sh` `on_exit` exit-status resolution.
- **REQ-300** evidence: `scripts/pre-release-check.sh` `on_exit` `Result: PASSED`/`Result: FAILED (...)` summary lines.
- **REQ-301** evidence: `.gitignore` leading `/*`, `*.*`, `*/**` exclusions followed by `!dist/` and `!dist/**/*` re-inclusions in the include section.
- **REQ-302** evidence: `.gitignore` contains no exclusion rule matching `dist/**/*.whl` or `dist/**/*.tar.gz`; `tests/test_gitignore_rules.py` `test_generated_dist_artifacts_are_versionable`.
- **REQ-303** evidence: `.gitignore` `/*/**/dist/` rule in the exclusion section.
- **REQ-316** evidence: `scripts/build.sh` `remove_build_intermediates` invoked by `run_cleanup` before `uv build` and by `on_exit` after every build.
- **REQ-317** evidence: `scripts/build.sh` `run_build` `Clean previous build outputs` step executing `run_cleanup` before the `uv build` step.
- **REQ-224** evidence: `scripts/pre-release-check.sh` `--- [pre-release-check] ... ---` progress lines plus the final success line.
- **REQ-225** evidence: `scripts/pre-release-check.sh` `run_step` fail-fast handler exiting non-zero at the first failed step.
- **REQ-228** evidence: `.github/workflows/release-pypi.yml` declares no `test-release` job and no `uv lock --check`, `uv run pytest`, or build-preparatory validation step.
- **REQ-229** evidence: `.github/workflows/release-pypi.yml` `publish-release` `needs: [check-branch]` dependency only.
- **REQ-313** evidence: `.github/workflows/release-pypi.yml` absence of `scripts/build.sh`, `scripts/pre-release-check.sh`, `uv build`, and `python -m build`, with assets consumed from the checked-out tagged commit `dist/` directory.
- **REQ-314** evidence: `.github/workflows/release-pypi.yml` `Verify pre-built release artifacts` step resolving the `pyproject.toml` version, requiring exactly one sdist and one wheel, and failing on missing, untracked, or mismatched artifacts before attestation.
- **REQ-315** evidence: `.github/workflows/release-pypi.yml` PyPI publication step consuming the verified `dist/` directory without a preceding build.
- **REQ-236** evidence: `src/git_alias/core.py` `UV_TOOL_FORCE_UPGRADE_OPTIONS` constant (`--force`, `--reinstall`, `--refresh`) appended to `UV_TOOL_UPGRADE_COMMAND` by `upgrade_self(force=True)` on the Linux PyPI path.
- **REQ-237** evidence: `src/git_alias/core.py` `_build_github_upgrade_command(tag, force=True)` inserting `UV_TOOL_FORCE_UPGRADE_OPTIONS` before the `--from` override, executed by `upgrade_self(github=True, force=True)` on Linux.
- **REQ-238** evidence: `src/git_alias/core.py` `main` first-token `--force` gate rejecting the token outside `--upgrade` with English stderr and non-zero exit, and the `--upgrade` dispatch forwarding `force=('--force' in args)`.
- **REQ-239** evidence: `src/git_alias/core.py` `MANAGEMENT_HELP` `--upgrade` entry documenting the `--force` forced download and complete reinstallation.
- **REQ-240** evidence: `README.md` Prerequisites, GitHub install, and Management Commands sections documenting `--upgrade --force`.
- **REQ-241** evidence: `src/git_alias/core.py` `VERSION_REPORT_LABEL_WIDTH` constant and `_format_version_report_line` emitting `<label>` left-justified to width 18 followed by `: <version>`, consumed by the `main` `--ver`/`--version` branch for all three REQ-202 lines.
- **REQ-256** evidence: `src/git_alias/` module inventory (`__init__.py`, `__main__.py`, `core.py`, `configuration.py`, `forest.py`) containing zero Italian-derived identifiers after the `foresta.py` to `forest.py` rename mandated by CPT-008.
- **REQ-097** evidence: `src/git_alias/configuration.py` `execute` (L998) performing exactly one `write_scope` per `--set`/`--unset` invocation plus the sole `_bootstrap_global` default initialization (L461-474).
- **REQ-245** evidence: `src/git_alias/configuration.py` `parse_value` (L249-266) casting CLI strings to strict schema types and `validate` (L204-247) rejecting mismatches before persistence.
- **REQ-250** evidence: `src/git_alias/configuration.py` `render_values_tree` (L719-750) rendering the `Application_Configuration` root header with optional subtree selection and `execute` `--print` routing (L1022-1030).
- **REQ-251** evidence: `src/git_alias/configuration.py` `execute` routing the `--info` command to `render_params_tree` with optional subtree path filtering, rendering the whole schema tree when PATH is absent.
- **REQ-252** evidence: `src/git_alias/configuration.py` `INPUT_HELP` (L131-164) documenting colon paths, zero-based indices, `append`/`insert`/row/cell/map-key tokens, unset/default semantics, and shell-quoted JSON input.
- **REQ-254** evidence: `src/git_alias/configuration.py` `write_scope` (L289-315) writing a flushed and fsynced same-directory temporary file renamed over the target.
- **REQ-257** evidence: `src/git_alias/configuration.py` `_values_node` (L667-717) printing `[Path: ...]` badges and verbatim node names; `_values_map` and `_values_array` carrying the parameter path into target hints.
- **REQ-258** evidence: `src/git_alias/configuration.py` `_default_note` (L495-507) emitting `(default)` or `(custom | default: <default>)`.
- **REQ-259** evidence: `src/git_alias/configuration.py` `_values_node` selection branch (L699-708) rendering the Sel/Value table and `_values_map` (L641-665) rendering the entries header and Key/Value table.
- **REQ-260** evidence: `src/git_alias/configuration.py` `_values_array` (L605-639) primitive-array header `(N items | row target: ...:<Idx> | add: :+)` plus Idx/Value table.
- **REQ-261** evidence: `src/git_alias/configuration.py` `_values_array` object-array branch (L622-632) header `(N rows | cell target: ...:<Idx>:<Field> | add: :+)` plus Idx-plus-field table.
- **REQ-262** evidence: `src/git_alias/configuration.py` `_values_array` empty branch (L615-619) and `_values_map` empty branch (L648-652) rendering the copy-pasteable empty hints.
- **REQ-263** evidence: `src/git_alias/configuration.py` `_params_node` scalar branch (L806-820) with the `[<type and constraints>] <description>` header, `Default :` line, and full-path `Set cmd :` line; `_params_type_label` (L549-569).
- **REQ-264** evidence: `src/git_alias/configuration.py` `_params_array` (L822-869) Item Schema table plus append/insert/update/reset/replace/delete/overwrite/clear command set and `_params_node` selection Allowed Values table (L782-805).
- **REQ-265** evidence: `src/git_alias/configuration.py` `_split_set_target` (L443-459) reserving `:append`/`:+`, `_mutate_array` append path (L402-441), and the index-naming confirmation printed by `execute` (L1052-1063).
- **REQ-266** evidence: `src/git_alias/configuration.py` `_mutate_array` insert branch (L424-436) shifting later items and treating length as append.
- **REQ-267** evidence: `src/git_alias/configuration.py` `resolve_path` (L178-201) traversing fields, indices, and map keys, plus `change_scope` (L334-374) assigning rows, cells, and map keys.
- **REQ-268** evidence: `src/git_alias/configuration.py` `execute` `--get` branch (L1032-1036) printing row, cell, and map-key selections from `descend` (L317-332) as JSON.
- **REQ-269** evidence: `src/git_alias/configuration.py` `change_scope` list-parent deletion (L356-363) compacting indices contiguously and `_unset_confirmation` cell branch (L978-980).
- **REQ-270** evidence: `src/git_alias/configuration.py` `_array_index` (L376-400) and `_mutate_array` insert bounds (L426-431) raising English out-of-bounds diagnostics carrying the valid range and `:append` hint, converted by `core.py` `main` into stderr plus exit 1.
- **REQ-271** evidence: `src/git_alias/configuration.py` `_assign_confirmation` (L913-941), `_overwrite_confirmation` (L943-959), and `_unset_confirmation` (L961-996) printed by `execute` after each successful mutation.
- **REQ-272** evidence: `src/git_alias/configuration.py` `_bootstrap_global` (L461-474) invoked first in `execute` (L1003) writing schema defaults atomically when `config.json` is missing.
- **REQ-273** evidence: `src/git_alias/core.py` `main` (L5938-6041) catching configuration failures and printing `Configuration error: ...` to stderr with `sys.exit(1)` while `configuration.execute` writes valid output to stdout.
- **REQ-274** evidence: `src/git_alias/configuration.py` `_scalar_text` rendering every value unmasked and `print_raw` emitting exact stored bytes.
- **REQ-275** evidence: `src/git_alias/configuration.py` `_tree_prefix` resolving the four-character branch and child prefixes consumed by `_values_node` and `_params_node` without any width input.
- **REQ-276** evidence: `src/git_alias/configuration.py` `_values_node`, `_values_array`, `_values_map`, `_params_node`, and `_params_array` emit node names, values, and metadata text without padding fields.
- **REQ-277** evidence: `src/git_alias/configuration.py` `_append_metadata` rendering every parameter metadata entry as a `├──`/`└──` child of the owning parameter.
- **REQ-278** evidence: `src/git_alias/configuration.py` `_values_array`, `_values_map`, `_params_node`, and `_params_array` indenting table rows with the child prefix of the owning node or labelled entry.
- **REQ-279** evidence: `src/git_alias/configuration.py` `_values_node` and `_params_node` recursing over schema fields with the parent child prefix.
