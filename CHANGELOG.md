# Changelog

## [0.51.2](https://github.com/Ogekuri/GAlias/compare/v0.51.0..v0.51.2) - 2026-11-10
### 🚜  Changes
- align --ver/--version output to REQ-241 label format [useReq] *(version-report)*
REQUIREMENTS.md v1.44: add REQ-241 aligned 18-character label-field
format; update REQ-202 and REQ-230 to render the three-line report
through it.
core.py: add VERSION_REPORT_LABEL_WIDTH and _format_version_report_line;
main --ver/--version branch prints aligned 'Current Installed',
'Latest @ PyPI', and 'Latest @ GitHub' lines including the
'unknown (<reason>)' GitHub degradation.
tests: update --ver/--version output expectations in test_alias_help.py.; WORKFLOW.md/REFERENCES.md: trace _format_version_report_line in PROC:main.
- add --force to --upgrade for forced uv reinstall [useReq] *(upgrade)*
Add the auxiliary --force flag to --upgrade, combinable with --develop/--dev:
forced path appends the uv forcing options --force --reinstall --refresh
(REQ-236, REQ-237); the standard path runs the unforced install (REQ-001, REQ-209)
first-token --force outside --upgrade is rejected with English error (REQ-238); inline help (REQ-239) and README (REQ-240) document the forced reinstall; SRS updated to 1.43 with REQ-236..REQ-240 and evidence entries; unit tests updated for the unforced default and forced argv variants

## [0.51.0](https://github.com/Ogekuri/GAlias/compare/v0.50.0..v0.51.0) - 2026-11-09
### 🚜  Changes
- flatten markdown bullet lists to semicolon lists [useReq] *(changelog)*
New REQ-234: strip leading markdown bullet markers from continuation lines.; New REQ-235: collapse consecutive bullet-item runs into '; '-joined lines.; REQ-232 narrowed: only non-bullet continuation lines stay verbatim.; _format_changelog_description implements stripping and '; ' flattening.; categorize_commit Doxygen contract updated for REQ-234/REQ-235.; Changelog test realigned to the semicolon-list rendering contract.
- preserve multiline commit body verbatim in entries [useReq] *(changelog)*
REQ-078 rewritten: one top-level bullet `- <description> *(<scope>)*` per commit.; New REQ-232: continuation description lines render verbatim, no sub-bullets.; New REQ-233: no blank separator lines between consecutive commit bullets.; _format_changelog_description keeps Co-authored-by/empty-line cleanup only.; categorize_commit drops sub-bullet generation; Doxygen docstrings updated.; Changelog tests realigned to the updated rendering contract.
- report GitHub fetch failure reason in --ver output [useReq] *(version-check)*
Encode REQ-230/REQ-231 in the SRS: failed GitHub latest-version
resolution now prints 'GitHub latest: unknown (<reason>)' instead of a
bare placeholder. Add _github_failure_reason deriving the reason from
HTTPError status, reason phrase, and the API 'message' field; add
_fetch_github_release_tag_with_reason so _fetch_github_latest_version
returns (version, reason) to main, keeping REQ-127 stderr diagnostics.
Update WORKFLOW/REFERENCES and version-reporting unit tests for the
new tuple contract and 404 rate-limit interception coverage.

## [0.50.0](https://github.com/Ogekuri/GAlias/compare/v0.49.0..v0.50.0) - 2026-11-08
### ⛰️  Features
- add pre-release validation script with tests and SRS [useReq] *(pre-release-check)*
Add executable scripts/pre-release-check.sh running fail-fast official-
release pre-validation: git/uv prerequisite checks, uv lock --check
dependency synchronization, full pytest suite via uv run pytest, and
uv build into a temporary directory removed at exit (REQ-217..REQ-225).
Add HDT unit tests with fake git/uv shims covering step order, cleanup,
progress output, and abort semantics. Update SRS to v1.37 with scope,
file-structure, and evidence entries; add PROC:pre-release-check unit
and communication edges to WORKFLOW.md; regenerate REFERENCES.md.

### 🐛  Bug Fixes
- compile negation specs with supported pathspec gitignore style [useReq] *(ver-rules)*
Replace the deprecated pathspec gitwildmatch registered style with the
supported gitignore style in _build_version_negation_specs, eliminating
DeprecationWarning emissions from ver_rules negation processing and
preventing a future pathspec removal crash in ver/chver/release/rollback.
Matching behavior is preserved (differential-verified; REQ-160, REQ-161,
REQ-163, REQ-164, CPT-006). Add HDT reproducer test asserting warning-free
negation spec compilation.
- correct inaccurate inline help entries for 13 aliases [useReq] *(help)*
ar: zip -> tar.gz archive named after the latest tag (REQ-012); ll: full-hash history graph instead of 'latest full commit hash'; br: list or create branches (native git branch, REQ-008); ck: git diff --check semantics; de: git describe nearest tag; feall: all remotes with tags and prune; me: fast-forward-only; gp/gr: configured gp_command/gr_command viewers replace 'Git K'; rmtg: local + origin tag delete with required <tag> operand; tg/rf/aa: annotated tag grammar, HEAD reflog, aa phrasing fix; add failing-first reproducer test for corrected help contracts

### 🚜  Changes
- gate release build and publish on test job [useReq] *(release-workflow)*
Add the test-release GitHub Actions job running uv lock --check and the
full pytest suite via uv run pytest, mirroring the scripts/pre-release-
check.sh validation chain, and gate build-release on it through needs:
[check-branch, test-release]. A failing test job now skips distribution
build, provenance attestation, GitHub Release upload, and PyPI OIDC
publication (REQ-228, REQ-229). Update the checkout@v5 pin contract to
three jobs and extend the workflow contract suite accordingly; update
SRS to v1.39.
- remove build and intermediate artifacts after run [useReq] *(pre-release-check)*
Extend the EXIT cleanup so scripts/pre-release-check.sh leaves the
repository free of every validation artifact it created: temporary
build directory, setuptools build/ tree, src/*.egg-info directories,
.pytest_cache, and __pycache__ under src/ and tests/, while preserving
tracked files and the uv-managed .venv environment (REQ-223, REQ-226,
REQ-227). Extend fake-uv build shim with residue creation and assert
artifact removal in the HDT suite. Update SRS to v1.38 and reflect the
renamed cleanup_validation_artifacts node in WORKFLOW.md.
- accept --dev/--develop on major/minor/patch [useReq] *(release-flags)*
Requirements (v1.36): REQ-203 reworded so the --develop/--dev rejection applies only when the first CLI token is outside --upgrade/major/minor/patch, resolving the collision with REQ-200/REQ-045; added REQ-214/REQ-215/REQ-216 requiring inline-help and README documentation of the flags' dual meaning.
Source: main now whitelists major/minor/patch as first tokens, reports the allowed commands in the rejection message, and MANAGEMENT_HELP/--upgrade plus HELP_TEXTS major/minor/patch spell out the two different meanings (GitHub newest-tagged-release install vs develop-scoped release).
Docs: README Prerequisites and Management Commands sections state the dual meaning explicitly.
Tests: release commands accept --dev/--develop through main for all six level/flag combinations; --develop standalone and co --dev still exit non-zero; README dual-meaning contract asserted.
- migrate workflow automation to Node24 runner generation [useReq] *(release)*
Requirements (v1.35): added REQ-211 (release automation runs on the GitHub Actions Node24 runner generation or newer with all steps preserved), REQ-212 (no FORCE_JAVASCRIPT_ACTIONS_TO_NODE24 or ACTIONS_ALLOW_USE_UNSECURE_NODE_VERSION overrides), REQ-213 (Node24-based action majors pinned in release-pypi.yml).
Workflow: bumped actions/checkout v4->v5 (both jobs), actions/setup-python v5->v6, astral-sh/setup-uv v3->v6, and actions/attest-build-provenance v1->v3; triggers, containment gate, build, attestation, changelog, release, and PyPI OIDC publication steps are unchanged.
Tests: tests/test_release_workflow_pypi.py enforces the Node24 action majors and the absence of Node20 fallback overrides.
- install newest GitHub release tag for --upgrade --develop [useReq] *(upgrade)*
Requirements (v1.34): REQ-201 now installs the newest GitHub release tag resolved via https://api.github.com/repos/Ogekuri/GAlias/releases/latest regardless of the branch containing it; added REQ-208 (raw tag_name resolution), REQ-209 (tag-scoped uv tool install --from git+https://github.com/Ogekuri/GAlias@<tag>), REQ-210 (explicit English abort with non-zero exit when tag resolution fails).
Source: added _fetch_github_latest_release_tag and _build_github_upgrade_command, refactored _fetch_github_latest_version to delegate, rewrote upgrade_self, removed the static UV_TOOL_GITHUB_UPGRADE_COMMAND constant.
Tests: updated tests/test_update_check.py GitHub-upgrade coverage to the tag-scoped contract (install argv, abort on failure, raw tag parsing).
Docs: WORKFLOW.md call-traces/edges and REFERENCES.md regenerated; --ver/--version PyPI/GitHub reporting behavior is unchanged.
- BREAKING CHANGE: rename --github upgrade option to --develop with --dev alias [useReq] *(upgrade)*
REQ-001/REQ-201 (SRS v1.33): the GitHub source is now selected via
--upgrade --develop, with --dev added as equivalent command-line flag
REQ-203: --develop/--dev outside --upgrade exit non-zero with explicit
English error; main dispatch and diagnostics updated
REQ-198: README GitHub install section documents --upgrade --develop; MANAGEMENT_HELP --upgrade entry updated for --help output; WORKFLOW.md runtime model: upgrade_self node and PROC:main -> PROC:uv
edge payloads renamed
tests aligned: develop-flag rejection and dual-flag GitHub-source
routing (subtests for --develop and --dev)
- BREAKING CHANGE: remove legacy glob key alias from ver_rules entries [useReq] *(ver_rules)*
REQ-207 (SRS v1.32): ver_rules entries resolve the pattern solely
from the 'pattern' field or the first sequence pair element
_load_config_rules drops the undocumented 'glob' dict-key fallback;
entries without 'pattern' are ignored (REQ-162 negation unaffected)
print_all_help renders only the 'pattern' field in Configuration
Parameters output
program behavior unchanged for canonical pattern-keyed configs;
inline help and README carry no legacy references
- BREAKING CHANGE: remove legacy editor key migration from write-config [useReq] *(config)*
REQ-015 redefined (SRS v1.31): --write-config persists only the
eight canonical REQ-186 global keys
legacy global 'editor' key is ignored, never read, migrated, or
persisted (DES-006, REQ-097)
_write_missing_config_values drops the migration block; docstrings
document the normalization-only contract
config-io test asserts the default edit_command instead of the
migrated value; README.md documents out-of-scope-key ignoring

### 📚  Documentation
- Update TODO.md file.

## [0.49.0](https://github.com/Ogekuri/GAlias/compare/v0.48.0..v0.49.0) - 2026-11-05
### 🚜  Changes
- gate PyPI publish to master, run release for develop tags [useReq] *(release-pypi)*
Widen workflow gate: release runs for tags on origin/master or origin/develop (REQ-112); Export is_master/is_develop/is_release containment outputs from check-branch job; Gate PyPI publication step to master-contained tag commits (REQ-205); Skip PyPI publication for develop-only tags while keeping GitHub Release (REQ-206); Update SRS to v1.30 with revised REQ-112 and new REQ-205/REQ-206 evidence

## [0.48.0](https://github.com/Ogekuri/GAlias/compare/v0.47.0..v0.48.0) - 2026-11-05
### 🐛  Bug Fixes
- Ux.lock version.
- Scripts/g.sh version.

### 🚜  Changes
- add --github upgrade source and dual PyPI/GitHub --ver report [useReq] *(update-check)*
REQ-201/REQ-203: new --github modifier for --upgrade installs from
git+https://github.com/Ogekuri/GAlias; rejected without --upgrade
REQ-202/REQ-204: --ver/--version prints installed plus latest PyPI and
GitHub release versions via _fetch_github_latest_version
REQ-001/REQ-129/REQ-199: default checks/upgrades stay PyPI-only; REQ-198: README primary install is uv tool install galias with dedicated
uvx and GitHub install/upgrade sections; update tests
- unify patch scope with major/minor and add --dev option [useReq] *(release)*
REQ-072: patch default publication now matches major/minor (push develop,
then master with the release tag atomically)
REQ-045/REQ-200: new --dev/--develop flag on major/minor/patch limits the
release to configured develop (previous patch workflow)
REQ-176/REQ-180: --resume composes with --dev; push failures report the
scope-aware recovery command
Update REQUIREMENTS/WORKFLOW/REFERENCES docs, README, and release tests.

### 📚  Documentation
- Update README.md file.

## [0.47.0](https://github.com/Ogekuri/GAlias/compare/v0.46.0..v0.47.0) - 2026-11-05
### 🐛  Bug Fixes
- replace invalid trove classifier blocking PyPI upload *(packaging)*
Replace unregistered classifier 'Topic :: Software Development :: Configuration Management' with the registered 'Topic :: Software Development :: Version Control' entry (REQ-196).; Defect evidence: PyPI warehouse rejected galias-0.46.0 upload with HTTP 400 'is not a valid classifier'.; Add reproducer test asserting the exact registered trove classifier inventory of pyproject.toml (REQ-196, REQ-194).

## [0.46.0](https://github.com/Ogekuri/GAlias/compare/v0.45.0..v0.46.0) - 2026-11-05
### 🚜  Changes
- switch update check and self-upgrade to PyPI as only source *(core)*
Resolve update checks via https://pypi.org/pypi/galias/json parsing info.version (REQ-124, REQ-199).; Execute --upgrade as uv tool install galias --force from PyPI without git --from source (REQ-001, REQ-199).; Document pipx as primary install method with Astral uv/uvx alternative section in README.md (REQ-198).; Remove GitHub/git-URL constants from update and upgrade paths; align tests to the PyPI contracts.
- add PyPI OIDC trusted publishing and rename release workflow *(release-pypi)*
Rename .github/workflows/release-uvx.yml to release-pypi.yml preserving triggers, gate, build, attestation, and release steps (REQ-112, REQ-195).; Add pypa/gh-action-pypi-publish post-step using OIDC Trusted Publishing without credentials (REQ-193, REQ-194).; Declare PEP 639 SPDX license GPL-3.0-only with license-files and setuptools>=77 in pyproject.toml (REQ-197).; Extend PyPI project metadata and URLs (REQ-196) and document PyPI install/uvx usage in README.md (REQ-198).; Add tests/test_release_workflow_pypi.py and align stale suites to REQ-186..REQ-192, CTN-003 defaults.
- BREAKING CHANGE: rename repository-local configuration file to .galias.conf [useReq] *(config)*
CONFIG_FILENAME constant renamed; config loading and --write-config now use .galias.conf only.; No backward compatibility: existing .g.conf files are not read or migrated (explicit request).; Tracked .g.conf renamed to .galias.conf; .gitignore negation updated for the blanket-ignore scheme.; --write-config management-help text and README documentation updated.; SRS v1.25: DES-006, DES-009, REQ-006, REQ-014, REQ-017, REQ-116, REQ-119 updated.; ver end-to-end returns 0.45.0; test failure baseline unchanged (no new failures).
- BREAKING CHANGE: rename distribution and repository to galias and GAlias [useReq] *(core)*
Upstream repository renamed Ogekuri/GitAlias -> Ogekuri/GAlias (REQ-001, REQ-124).; Distribution/tool/binaries renamed to galias with g; git-alias script removed (PRJ-001, CPT-002).; User-facing paths renamed to ~/.cache/galias and ~/.config/galias (REQ-002/030/033/126/136/137, CTN-003, DES-006/009, REQ-013/014/186).; uv.lock regenerated and .g.conf ver_rules regex updated to keep ver/chver detection working.; SRS v1.24, README, WORKFLOW.md, REFERENCES.md updated accordingly.; Tests: rename-relevant suites pass; 1 stale config-path expectation documented (tests untouched).
- rename upstream GitHub repository G to GitAlias [useReq] *(core)*
REQ-001 upgrade source URL and REQ-124 release-check API URL now target Ogekuri/GitAlias.; GITHUB_REPOSITORY constant in core.py renamed with Doxygen contract and REQ links.; pyproject project.urls and README install/uvx/raw-image URLs updated to GitAlias.; SRS bumped to v1.23 with revision-history entry documenting the repository rename.; REFERENCES.md regenerated; WORKFLOW.md unchanged (no runtime-model impact).; Tests: update-check and dependency-manifest suites pass; launcher-suite failure is a sandbox PATH artifact; 23 unrelated pre-existing stale-test failures left untouched per policy.

## [0.45.0](https://github.com/Ogekuri/GAlias/compare/v0.44.0..v0.45.0) - 2026-11-04
### 🐛  Bug Fixes
- restore inherited-stdio push and fail-closed remote refresh [useReq] *(release)*
Release pushes execute via run_git_cmd (inherited stdio) instead of piped
run_git_text, restoring interactive SSH authentication and live push output
regressed by commit 8e4abd26 (publickey push rejection while the same-run
inherited-stdio fetch succeeded).
Release preflight aborts when the origin remote-reference refresh fails,
preventing full local release preparation against unverifiable remote state.
Remote refresh scoped to 'git remote update origin' instead of the malformed
'git remote -v update' that fetched every configured remote.
Add release push/preflight regression reproducer suite; update related
release, resume, and remote-status test assertions; refresh docs.

## [0.44.0](https://github.com/Ogekuri/GAlias/compare/v0.43.0..v0.44.0) - 2026-11-03
### 🚜  Changes
- impose default command values and canonical print order [useReq] *(config)*
REQ-191: default edit/sublime_text, icdiff/meld, tig/gitg, gitui/sublime_merge pairs; REQ-192: print the eight global command keys contiguously in canonical order; Reorder DEFAULT_CONFIG and GLOBAL_CONFIG_KEYS to the canonical order; SRS v1.22 with REQ-191/REQ-192 and evidence entries; REFERENCES regenerated; Tests intentionally not modified; outdated default-value assertions reported

## [0.43.0](https://github.com/Ogekuri/GAlias/compare/v0.42.0..v0.43.0) - 2026-11-03
### 🚜  Changes
- BREAKING CHANGE: inject configured diff tool via git difftool --extcmd [useReq] *(diff)*
REQUIREMENTS 1.21: rewrite REQ-189 so visual diff aliases run
git difftool -d with the environment-selected diff_command/
diff_command_gfx injected as --extcmd, overriding git's configured
diff tool; add REQ-190 plain git difftool fallback when the resolved
command is empty.
core.py: new _selected_diff_command_parts (empty->no override);
_run_configured_diff builds git difftool -d [--extcmd=<tool>] <refs>;
DEFAULT diff_command is now empty; GIT_DIFFTOOL_COMMAND base constant.
tests: diff-alias and environment suites updated to the extcmd
contract (terminal icdiff via -x in SSH sessions, _gfx in graphical
sessions).
WORKFLOW.md: diff flow now targets PROC:git; PROC:diff-tool removed.
- BREAKING CHANGE: add env-aware dual external-command config and unified subprocess wrapper [useReq] *(core)*
REQUIREMENTS 1.20: add REQ-185 (single _run_checked subprocess wrapper),
REQ-186 (<id>_command/<id>_command_gfx pairs for edit/gp/gr/diff),
REQ-187 (DISPLAY/WAYLAND_DISPLAY graphical detection), REQ-188 (gfx
fallback to terminal command), REQ-189 (diff aliases run the
environment-resolved diff_command); amend REQ-037/038/119/014, DES-006,
CTN-003.
core.py: new _is_graphical_environment, _environment_config_command_parts,
_run_configured_diff; ed/gp/gr and dc/dcc/dccc/dw/dwc/dwcc/dcd/dcm/ddm
route through the environment-aware wrapper; all subprocess executions
(incl. cmd_ar streaming Popen) funnel through _run_checked.
tests: update diff-alias and config-io suites; add
test_command_environment.py covering detection, selection matrix, diff
routing, and wrapper isolation.
- BREAKING CHANGE: make <ref_prev> optional with ref_prev -> ref diff direction [useReq] *(dc)*
REQUIREMENTS 1.19: split REQ-037; add REQ-182 (dc accepts <ref> plus
optional <ref_prev>), REQ-183 (executes git difftool -d <ref_prev> <ref>,
diff direction ref_prev -> ref, never inverted), REQ-184 (omitted
<ref_prev> defaults to the commit preceding <ref>, <ref>~1).
core.py: cmd_dc validates 1..2 positional refs, resolves the <ref>~1
default, and delegates git difftool -d <ref_prev> <ref>; HELP_TEXTS[dc]
documents the new syntax and default.
tests: test_cmd_diff_aliases.py dc suite updated to the new contract.; dcc, dccc, dwc, and dw behaviors are unchanged.

## [0.42.0](https://github.com/Ogekuri/GAlias/compare/v0.41.0..v0.42.0) - 2026-11-02
### 🐛  Bug Fixes
- Fix .gitignore file.

### 🚜  Changes
- add atomic tag push and --resume recovery for releases [useReq] *(release)*
Rewrite REQ-045/REQ-072 and add REQ-176..REQ-181 requirements.; Publish exact release tag atomically with explicit refspecs; develop-only preliminary push for major/minor.; Add g major/minor/patch --resume to validate and publish only missing refs without bump/amend/tag recreation.; Add push-failure diagnostics with version, refs to verify, and resume command.; Update WORKFLOW.md, REFERENCES.md, and release unit suites.

## [0.41.0](https://github.com/Ogekuri/GAlias/compare/v0.40.0..v0.41.0) - 2026-10-22
### 🚜  Changes
- preserve application version across rollback [useReq] *(rollback)*
rollback now runs the release-style canonical version detection as a
pre-flight check and aborts with explicit guidance on failure (REQ-169,
REQ-170).
The detected version is stored and restored via chver after the inverse
revert, before the revert commit; restored files are staged so the commit
preserves the pre-rollback version (REQ-171, REQ-172, REQ-173).
A failed version restore aborts via git revert --abort with non-zero exit
(REQ-174).
Inline help and README document the new behavior (REQ-175); SRS updated to
1.18; WORKFLOW.md rollback trace and REFERENCES.md regenerated; rollback
unit tests updated and extended (13 tests).

## [0.40.0](https://github.com/Ogekuri/GAlias/compare/v0.39.0..v0.40.0) - 2026-10-21
### 🐛  Bug Fixes
- .gitignore file.

## [0.39.0](https://github.com/Ogekuri/GAlias/compare/v0.38.0..v0.39.0) - 2026-10-21
### 🚜  Changes
- add --exec option to major/minor/patch release commands [useReq] *(core)*
Add `--exec <command> [params...]` to major/minor/patch releases: the operand tail is parsed by _parse_release_flags with rest-of-argv semantics, kept separate from changelog args, and executed as an argv list (repository root CWD, inherited stdio) between the version-update and staging steps of _execute_release_flow. A non-zero exit aborts the release with the standard --- [release:<level>] Step ... failed: ... --- diagnostic before staging, commit, tag, or push. Help texts and the SRS document the option (new REQ-166, REQ-167, REQ-168; REQ-026 extended). Also fixes pre-existing Doxygen block adjacency defects in core.py launcher helpers.

## [0.38.0](https://github.com/Ogekuri/GAlias/compare/v0.37.0..v0.38.0) - 2026-10-02
### 🚜  Changes
- add gitignore escaping and negation to ver_rules.pattern [useReq] *(core)*
Preserve gitignore(5) backslash escaping in ver_rules.pattern
normalization (REQ-160); backslashes are no longer converted to
path separators.
Add negation exclusion: patterns starting with '!' exclude matched
files from every rule's file list (REQ-161); such entries accept
no regex and are skipped as detection rules (REQ-162).
Negation-excluded files no longer count as matches and the REQ-118
zero-match abort applies only to non-excluded matches (REQ-163).
Anchoring semantics unchanged (REQ-164); README documents full
gitignore(5) compatibility (REQ-165).
Add HDT unit tests in tests/test_ver_rule_patterns.py.

## [0.37.0](https://github.com/Ogekuri/GAlias/compare/v0.36.0..v0.37.0) - 2026-07-08
### 🐛  Bug Fixes
- Fix ignore file.

## [0.36.0](https://github.com/Ogekuri/GAlias/compare/v0.35.0..v0.36.0) - 2026-07-08
### 🐛  Bug Fixes
- Update README.md file.

## [0.35.0](https://github.com/Ogekuri/GAlias/compare/v0.34.0..v0.35.0) - 2026-06-08
### 🐛  Bug Fixes
- support Git Bash shell-script launchers [useReq] *(core)*
resolve Windows PATH lookup for non-PATHEXT launchers such as gitk\n- add a reproducer test for gr_command on Git Bash\n- update pi-usereq workflow and references docs

## [0.34.0](https://github.com/Ogekuri/GAlias/compare/v0.33.0..v0.34.0) - 2026-06-08
### ⛰️  Features
- Check edit, gp, gr commands.

### 🐛  Bug Fixes
- Move docs dir.

## [0.33.0](https://github.com/Ogekuri/GAlias/compare/v0.32.0..v0.33.0) - 2026-04-22
### 🚜  Changes
- BREAKING CHANGE: switch wt alias to git worktree [useReq] *(core)*
update REQ-074 and related traceability docs; dispatch wt to git worktree while keeping wtl on worktree list; adjust help text and worktree alias tests

## [0.32.0](https://github.com/Ogekuri/GAlias/compare/v0.31.0..v0.32.0) - 2026-04-12
### 📚  Documentation
- align README with current CLI behavior [useReq] *(readme)*
Correct global config path and default commit-module behavior.; Document get/str commands and lsi filtering semantics.; Clarify Linux-only scope for upgrade/uninstall commands.; Update examples for wip auto-stage and normalized conventional messages.
- Update README.md file.

## [0.31.0](https://github.com/Ogekuri/GAlias/compare/v0.30.0..v0.31.0) - 2026-04-07
### ⛰️  Features
- add get command for fast-forward sync of master/develop/work [useReq] *(core)*
Implement `git get` CLI command with preflight verifications and
fast-forward synchronization of configured master, develop and work
branches from origin.
Add REQ-146..REQ-155 covering verifications and fast-forward flow.; Update WORKFLOW.md and regenerate REFERENCES.md.; Silence Windows-only Pylance SIGPIPE attribute check in foresta.

### 🐛  Bug Fixes
- normalize Windows launcher drive casing [useReq] *(g.sh)*
Normalize Git Bash launcher path comparison on Windows.
Add launcher regression coverage for slash and drive-letter variants.
Update workflow and references documentation for the launcher flow.

## [0.30.0](https://github.com/Ogekuri/GAlias/compare/v0.29.0..v0.30.0) - 2026-04-01
### 🐛  Bug Fixes
- Fix git repository.

## [0.29.0](https://github.com/Ogekuri/GAlias/compare/v0.28.0..v0.29.0) - 2026-03-31
### 🚜  Changes
- BREAKING CHANGE: add force-aware paired delete for bd and wtd [useReq] *(core)*
Update requirements, core delete flow, tests, workflow, and references.
- align worktree-delete alias naming to wtd [useReq] *(core)*
update REQ-077 and REQ-143 to encode the user-exposed alias name; replace legacy README references to wtr with wtd usage

## [0.28.0](https://github.com/Ogekuri/GAlias/compare/v0.27.0..v0.28.0) - 2026-03-31
### 🚜  Changes
- coordinate bd and wtd deletions [useReq] *(core)*
Update requirements for paired branch/worktree deletion.
Replace worktree delete alias with wtd and add shared preflight logic.
Abort without partial deletion when either side cannot be removed.
Refresh tests, workflow, and references for the new command flow.

## [0.27.0](https://github.com/Ogekuri/GAlias/compare/v0.26.0..v0.27.0) - 2026-03-30
### 🚜  Changes
- rewrite idle-time JSON on all errors [useReq] *(version-check)*
update SRS to require JSON rewrites on every terminal version-check error; rename error idle helper/constants to generic version-check error semantics; cover invalid installed-version error path and refresh workflow/references docs
- update release-check idle delays [useReq] *(version-check)*
change SRS idle delays to 3600 on success and 86400 on API errors; persist extended backoff across HTTP, network, timeout, and payload failures; update targeted tests plus workflow and references docs
- persist fixed rate-limit idle delay [useReq] *(version-check)*
update requirements for fixed 3600-second backoff on HTTP 429/403 rate limits; persist rate-limit idle windows in version-check cache; refresh workflow, references, and targeted tests

## [0.26.0](https://github.com/Ogekuri/GAlias/compare/v0.25.0..v0.26.0) - 2026-03-27
### 🚜  Changes
- force online update check for --version flags [useReq] *(core)*
Update REQ-030 and REQ-033 to require forced online checks for --ver/--version.
Implement check_for_newer_version(ignore_idle_cache) and route version flags through forced checks.
Add and adjust unit tests for idle-cache bypass and version-flag update-check behavior.
Update WORKFLOW.md and regenerate REFERENCES.md for traceability.

## [0.24.0](https://github.com/Ogekuri/GAlias/compare/v0.23.0..v0.24.0) - 2026-03-18
### 🚜  Changes
- move idle cache path and uninstall cleanup [useReq] *(update-check)*
Update requirements REQ-002/033/126/131 and add REQ-136 for cache directory creation.; Store idle-time state in ~/.cache/git-alias/check_version_idle-time.json.; Create cache directory during state writes and remove cache file+directory on Linux --uninstall.; Update unit tests and regenerate WORKFLOW/REFERENCES docs.

## [0.23.0](https://github.com/Ogekuri/GAlias/compare/v0.22.0..v0.23.0) - 2026-03-17
### 🚜  Changes
- enforce terminal-width l output with --wrap [useReq] *(foresta)*
Update SRS: revise REQ-100 and REQ-104 for terminal-width truncation and --wrap option.
Implement foresta terminal-width detection via shutil and ANSI-safe line truncation helpers.
Extend l option parsing/help to include --wrap and keep default -n 25 behavior.
Add unit tests for truncation behavior and --wrap terminal-width bypass.

## [0.22.0](https://github.com/Ogekuri/GAlias/compare/v0.21.0..v0.22.0) - 2026-03-17
### ⛰️  Features
- Update .g.conf file.
- Add uv.lock file.

### 🚜  Changes
- gate self-management to Linux [useReq] *(core)*
Update SRS: revise REQ-001/REQ-002 and add REQ-129/REQ-130.
Implement Linux-only local execution for --upgrade/--uninstall.
Print explicit manual uv commands on non-Linux runtimes.
Regenerate WORKFLOW.md and REFERENCES.md for traceability.

## [0.21.0](https://github.com/Ogekuri/GAlias/compare/v0.20.0..v0.21.0) - 2026-03-17
### ⛰️  Features
- Add uv.lock file.

### 🚜  Changes
- add uv-managed pytest dev dependency [useReq] *(pyproject)*
Update CPT-004 in SRS to require pytest in uv-managed dependencies.
Add pytest under [dependency-groups].dev in pyproject.toml.
Regenerate uv.lock to include pytest and transitive packages.
Extend dependency manifest tests for pytest declaration and lock presence.

## [0.20.0](https://github.com/Ogekuri/GAlias/compare/v0.19.0..v0.20.0) - 2026-03-17
### 🐛  Bug Fixes
- Fix workflow.

### 🚜  Changes
- remove README-bound SRS rule [useReq] *(requirements)*
Remove REQ-071 from docs/REQUIREMENTS.md.
Bump SRS version to 1.06 and update revision history.
No runtime code/test behavior changes required by this requirement removal.
- align SRS with current release/docs behavior [useReq] *(requirements)*
Update CPT-007 and REQ-036 to optional Doxygen asset semantics.
Update REQ-112 to include workflow_dispatch plus tag trigger with SHA gate.
Refresh metadata and evidence lines to match repository implementation.

## [0.19.0](https://github.com/Ogekuri/GAlias/compare/v0.18.0..v0.19.0) - 2026-03-17
### ⛰️  Features
- Implment astral uv tool.

### 🐛  Bug Fixes
- remove unsupported tool.uv.forms config [useReq] *(pyproject)*
Fix uv settings-discovery warning triggered by [tool.uv.forms.git-alias].
Add a reproducer test for unsupported tool.uv sections and remove invalid TOML block.
Resolve existing static-check failures in tests to keep req --here --static-check clean.
- Remove .req dir.

## [0.18.0](https://github.com/Ogekuri/GAlias/compare/v0.17.0..v0.18.0) - 2026-03-16
### ⛰️  Features
- add rollback command and rollback requirements [useReq] *(core)*
Append REQ-132..REQ-135 for rollback command semantics.
Implement git rollback with clean-state prechecks, target validation, reachability check, and non-amend revert commit generation.
Add rollback unit tests and update README/workflow/references docs.
- Update useReq files.

### 🐛  Bug Fixes
- Update .gitignore file.

## [0.17.0](https://github.com/Ogekuri/GAlias/compare/v0.16.0..v0.17.0) - 2026-03-07
### 🚜  Changes
- align update-check idle and 429 backoff [useReq] *(core)*
update REQ-126 and REQ-129, and add REQ-130/REQ-131 for Retry-After behavior; enforce fixed 300-second idle-delay for successful update-check cache scheduling; persist HTTP 429 backoff using max(existing idle_until, now + max(300, Retry-After)); keep fixed GitHub release URL, timeout wiring, and management flag contracts; extend update-check tests and refresh WORKFLOW/REFERENCES documentation
- BREAKING CHANGE: align fixed GitHub update flow [useReq] *(update-check)*
Update requirements for fixed owner/repo/program update policy.; Implement fixed release URL, fixed upgrade source, and 24h idle-time with 300s floor.; Update tests, workflow model, and generated references.

## [0.16.0](https://github.com/Ogekuri/GAlias/compare/v0.15.0..v0.16.0) - 2026-03-07
### 🚜  Changes
- reduce update idle window to 300s [useReq] *(core)*
Update REQ-126 default idle interval from 24 hours to 300 seconds.
Align REQ-033 idle-state filename template with <program_name>.
Replace VERSION_CHECK_TTL_HOURS with VERSION_CHECK_IDLE_SECONDS in core update-check flow.
Adjust update-check test to verify exact idle window in seconds.
Update WORKFLOW wording and regenerate REFERENCES for symbol changes.
- align uv tool name for self-management [useReq] *(core)*
Update REQ-001, REQ-002, and REQ-126 to use <program_name> semantics.
Add REQ-128 for explicit setuptools package inclusion in uv artifacts.
Use UV_TOOL_NAME for upgrade, uninstall, cache-file naming, and request User-Agent.
Adjust update-check tests to assert tool-name-driven command and cache behavior.
Standardize pyproject setuptools package discovery and package-data inclusion.
Regenerate REFERENCES and update WORKFLOW call-trace notes for uv management paths.

## [0.15.0](https://github.com/Ogekuri/GAlias/compare/v0.14.0..v0.15.0) - 2026-03-07
### 🐛  Bug Fixes
- Minor fixes.

## [0.14.0](https://github.com/Ogekuri/GAlias/compare/v0.13.0..v0.14.0) - 2026-03-07
### 🐛  Bug Fixes
- repair l graph fan connector rendering [useReq] *(foresta)*
normalize S/s fan spans so spaces render as connector dashes; preserve one-sided fan prefixes/suffixes without duplicated branches; map terminal fan markers to corner glyphs when padded by spaces; add regression test covering merge/branch connector edge cases; update WORKFLOW.md call-trace and regenerate REFERENCES.md
- support URI-style SSH remote parsing [useReq] *(update-check)*
add a failing update-check reproducer for ssh:// remotes; accept ssh and git+ssh remote URL schemes in owner/repo parsing; update workflow/runtime references for the parsing behavior

### 🚜  Changes
- default l output limit to 25 commits [useReq] *(cmd_l)*
update REQ-111 default injection from -n 35 to -n 25; implement cmd_l runtime default argument change in core.py; refactor cmd_l unit tests to assert new default depth behavior; update WORKFLOW.md call-trace default value for cmd_l; regenerate REFERENCES.md for synchronized symbol metadata

## [0.13.0](https://github.com/Ogekuri/GAlias/compare/v0.12.0..v0.13.0) - 2026-03-06
### 🚜  Changes
- BREAKING CHANGE: switch to remote-driven update checks [useReq] *(core)*
Update SRS for uninstall flag and idle-time release checks.
- run update check before arg validation [useReq] *(core)*
Update REQ-033 and add REQ-123 for startup update-check behavior.
Move check_for_newer_version execution before CLI argument validation in main.
Render newer-version warning in bright red with format: Update available: <latest> (current: <current>).
Adjust and extend tests for warning format and startup ordering.
Refresh WORKFLOW and regenerate REFERENCES.

## [0.12.0](https://github.com/Ogekuri/GAlias/compare/v0.11.0..v0.12.0) - 2026-03-05
### ⛰️  Features
- Update .req/models.json file.
- add lsi output filtering with --include-all bypass [useReq] *(core)*

### 🐛  Bug Fixes
- Add .place-holder files.
- complete Doxygen coverage for uncovered symbols [useReq] *(core)*
Add missing @brief/@details/@param/@return Doxygen blocks in core and foresta where coverage gaps remained.
Keep runtime behavior unchanged; documentation-only edits.
Verification: PYTHONPATH=src .venv/bin/python -m pytest -q (256 passed).
- Remove unused scripts.

### 🚜  Changes
- remove mandatory venv refresh [useReq] *(requirements)*
remove CPT-009 requirement from SRS; drop hash-based .venv auto-refresh logic from scripts/g.sh; remove CPT-009 test assertions; update WORKFLOW/REFERENCES to match launcher flow
- enforce venv and dependency sync [useReq] *(packaging)*
update CPT-004 to define canonical requirements alignment; add CPT-009 for .venv refresh on requirements changes; implement hash-based .venv synchronization in scripts/g.sh; extend dependency tests with launcher sync contract; update WORKFLOW and REFERENCES for launcher process/symbols
- align dependency manifests with requirements [useReq] *(packaging)*
update CPT-004 to require dependency manifest synchronization; align requirements.txt to runtime/build-only dependency set; declare runtime dependency and build constraints in pyproject.toml; add tests validating pyproject/requirements alignment
- add auto-staging to wip and conventional commit aliases [useReq] *(core)*
- add suffix-pattern exclusion for *.egg-info directories [useReq] *(lsi)*
Add LSI_DEFAULT_EXCLUDED_DIR_SUFFIXES tuple with .egg-info suffix (REQ-122); Update cmd_lsi to filter paths by both exact-match (LSI_DEFAULT_EXCLUDED_DIRS)
and suffix-match (LSI_DEFAULT_EXCLUDED_DIR_SUFFIXES) on path components (REQ-080)
Update --include-all to bypass both filtering mechanisms (REQ-121); Add tests for suffix tuple type/entries, egg-info filtering, and --include-all bypass; Update REQUIREMENTS.md with REQ-122 and modified REQ-080, REQ-121; Update WORKFLOW.md and REFERENCES.md
- filter excluded dirs at any path depth instead of root only [useReq] *(lsi)*
- expand lsi default exclusions with AI tooling directories [useReq] *(core)*

### 📚  Documentation
- Update README.md document.

## [0.11.0](https://github.com/Ogekuri/GAlias/compare/v0.10.0..v0.11.0) - 2026-03-04
### ⛰️  Features
- Implement new commands.
- Update .req/models.json file.

### 🐛  Bug Fixes
- Include .req directory to support worktree.

### 🚜  Changes
- enforce Doxygen metadata coverage [useReq] *(core)*
update REQ-036 to require Doxygen coverage aligned to REFERENCES index; normalize Doxygen tags in core.py and foresta.py declarations; regenerate docs/REFERENCES.md from source metadata; verify req static-check and full test suite pass

### 📚  Documentation
- normalize workflow evidence paths [useReq] *(workflow)*
update docs/WORKFLOW.md runtime model references to file-level evidence; keep execution-unit IDs and call-trace structure stable; preserve process/thread model and communication-edge semantics

## [0.9.0](https://github.com/Ogekuri/GAlias/compare/v0.8.0..v0.9.0) - 2026-02-28
### ⛰️  Features
- add dwd diff alias and traceability [useReq] *(core)*
append REQ-119 for dwd visual diff behavior; implement cmd_dwd with configured work/develop refs; add tests for dwd dispatch and command execution; update WORKFLOW and regenerate REFERENCES

### 📚  Documentation
- Update README.md document.
- document dwd diff alias usage in README [useReq] *(core)*
add feature highlight for dwd visual diff alias\n- add CLI example for g dwd with configured branches

## [0.8.0](https://github.com/Ogekuri/GAlias/compare/v0.7.0..v0.8.0) - 2026-02-28
### 🐛  Bug Fixes
- Remove colors from commits.

### 🚜  Changes
- switch version inventory to git ls-files [useReq] *(ver)*
update REQ-017 and add REQ-118 for ver_rules pattern constraints; build shared version inventory from git ls-files output; fail ver/chver on unmatched ver_rules patterns with explicit guidance; refresh ver/chver tests for ls-files-driven discovery; update workflow and regenerate references docs

### 📚  Documentation
- Update TODO.md file.

## [0.7.0](https://github.com/Ogekuri/GAlias/compare/v0.6.0..v0.7.0) - 2026-02-25
### ⛰️  Features
- Add Acknowledgments section in README.md. *(core)*
- Add 'l' command for text-based commit tree visualization [useReq] *(core)*
Added REQ-098..REQ-111 for tree visualization with vine-based graph algorithm; Created foresta.py module (Perl-to-Python port) with configurable styles,
symbols, colors, margins, and working tree status display
Registered cmd_l in COMMANDS/HELP_TEXTS with full option passthrough to git log; Added CPT-008 for foresta.py module; updated REQ-008 to include 'l'; Added 37 unit tests in test_cmd_l.py covering helpers, styles, symbols, colors; Updated WORKFLOW.md and REFERENCES.md

### 🐛  Bug Fixes
- Update default module in G.

### 🚜  Changes
- default to -n 35 with no args [useReq] *(cmd-l)*
Update REQ-111 to require default depth limiting only when l has no parameters.
Implement cmd_l argument injection: use '-n 35' only for empty invocation and preserve provided args unchanged.
Add unit tests validating default injection and non-injection when parameters are provided.
Update WORKFLOW runtime note and regenerate REFERENCES for traceability.
- append unconfigured overview branches [useReq] *(core)*
Update REQ-096 wording and add REQ-115 for section-5 branch ordering.
Implement section 5 to append all non-configured local/remote branches after configured rows.
Add normalization helper for git branch -a parsing and extend branch summary rendering.
Adjust cmd_o tests and add coverage for normalized branch discovery and appended rows.
Update WORKFLOW and regenerate REFERENCES for traceability.
- support empty conventional scope [useReq] *(core)*
Update REQ-022 and add REQ-115..REQ-117 for empty-module commit format.; Change default_commit_module hardcoded default to empty string.; Accept explicit empty default_commit_module in config load/write paths.; Emit '<type>: <description>' when effective module is empty.; Update conventional and config I/O tests; refresh WORKFLOW and REFERENCES docs.

### 📚  Documentation
- Update README.md file.
- align README overview branch-table behavior [useReq] *(cmd-o)*
Update Feature Highlights and CLI Examples for /home/ogekuri/G                              5f8bd03 [work]
/home/ogekuri/userReq-G-work-20260225142452  5f8bd03 [userReq-G-work-20260225142452]
[35;1m=== 1. WORKING AREA, STAGE & CURRENT BRANCH ===[0m
[97mConfigured branches: [97mWork[97m([38;5;226m⎇ work[0m[97m)[0m, [97mDevelop[97m([38;5;226m⎇ develop[0m[97m)[0m, [97mMaster[97m([38;5;226m⎇ master[0m[97m)[0m[0m
[97mConfigured remotes: [97mRemoteDevelop[97m([38;5;226m⎇ origin/develop[0m[97m)[0m, [97mRemoteMaster[97m([38;5;226m⎇ origin/master[0m[97m)[0m[0m
[97mCurrent Branch: [31;1mCurrent[97m([38;5;226m⎇ userReq-G-work-20260225142452[0m[97m)[0m[0m
[35;1m=== 2. BRANCH DISTANCES (COMMITS) ===[0m
[97m[97mWork[97m([38;5;226m⎇ work[0m[97m)[0m vs [97mDevelop[97m([38;5;226m⎇ develop[0m[97m)[0m[0m | [97mahead 0[0m | [97mbehind 0[0m
[97m[97mWork[97m([38;5;226m⎇ work[0m[97m)[0m vs [97mMaster[97m([38;5;226m⎇ master[0m[97m)[0m[0m | [92m↑ ahead 7[0m | [97mbehind 0[0m
[97;1m--- Server Alignment ---[0m
[97m[97mDevelop[97m([38;5;226m⎇ develop[0m[97m)[0m vs [97mRemoteDevelop[97m([38;5;226m⎇ origin/develop[0m[97m)[0m[0m | [97mahead 0[0m | [97mbehind 0[0m
[97m[97mMaster[97m([38;5;226m⎇ master[0m[97m)[0m vs [97mRemoteMaster[97m([38;5;226m⎇ origin/master[0m[97m)[0m[0m | [97mahead 0[0m | [97mbehind 0[0m
[35;1m=== 3. ACTIVE WORKTREES ===[0m
[35;1m=== 4. QUALITATIVE TOPOLOGY ===[0m
[97mWorkingTree [staged][0m
[97m|[0m
[97m|-- [0m[97mWork[97m([38;5;226m⎇ work[0m[97m)[0m, [97mDevelop[97m([38;5;226m⎇ develop[0m[97m)[0m, [97mRemoteDevelop[97m([38;5;226m⎇ origin/develop[0m[97m)[0m
[97m|-- [0m[97mMaster[97m([38;5;226m⎇ master[0m[97m)[0m, [97mRemoteMaster[97m([38;5;226m⎇ origin/master[0m[97m)[0m
[97m|[0m
[35;1m=== 5. BRANCHES ===[0m
[97m[97mWork[97m([38;5;226m⎇ work[0m[97m)[0m[97m                                                   | [0m[97;1mrelease: Release version 0.6.1[0m[0m
[97m[97mDevelop[97m([38;5;226m⎇ develop[0m[97m)[0m[97m                                             | [0m[97;1mrelease: Release version 0.6.1[0m[0m
[97m[97mMaster[97m([38;5;226m⎇ master[0m[97m)[0m[97m                                               | [0m[97;1mrelease: Release version 0.6.0[0m[0m
[97m[97mRemoteDevelop[97m([38;5;226m⎇ origin/develop[0m[97m)[0m[97m                                | [0m[97;1mrelease: Release version 0.6.1[0m[0m
[97m[97mRemoteMaster[97m([38;5;226m⎇ origin/master[0m[97m)[0m[97m                                  | [0m[97;1mrelease: Release version 0.6.0[0m[0m
[97m[97muserReq-G-work-20260225142452[97m([38;5;226m⎇ userReq-G-work-20260225142452[0m[97m)[0m[97m | [0m[97;1mrelease: Release version 0.6.1[0m[0m
[97m[97m+ work[97m([38;5;226m⎇ + work[0m[97m)[0m[97m                                               | [0m[97;1mn/a[0m[0m
[35;1m=== 6. CURRENT BRANCH STATE ===[0m
[97m## [31;1mCurrent[97m([38;5;226m⎇ userReq-G-work-20260225142452[0m[97m)[0m[0m
[31;1mM [0m README.md.
Document that section  prints configured rows first and appends all other local/remote branches with latest commit subjects.
- Recreate SRS in English [useReq] *(requirements)*
Reorganized requirements with RFC 2119 statements.; Preserved existing IDs and appended REQ-112..REQ-114.

## [0.6.0](https://github.com/Ogekuri/GAlias/compare/v0.5.0..v0.6.0) - 2026-02-24
### ⛰️  Features
- add overview ASCII topology section [useReq] *(core)*
append REQ-089..REQ-093 for qualitative topology output\n- add section 4 ASCII tree rendering in cmd_o\n- map divergence counts to qualitative states\n- extend overview tests for section ordering and topology nodes\n- update workflow and regenerate references
- add o overview alias with templates [useReq] *(core)*
append REQ-082..REQ-088 for overview command\n- implement cmd_o with reusable formatting templates and help wiring\n- add tests and update README/WORKFLOW/REFERENCES
- add .place-holder files. *(core)*
- add ls/lsi file listing aliases [useReq] *(cli)*
Add REQ-079/REQ-080 and update REQ-008.\nAdd cmd_ls/cmd_lsi, help text, tests.\nUpdate WORKFLOW/REFERENCES and README.\nTests: PYTHONPATH=src /tmp/venv-userReq-G-work-3af15715-c78b-405c-a749-bf538bb2225a/bin/python -m pytest
- add guidelines/, update .gitignore. *(core)*

### 🐛  Bug Fixes
- Fix workflow file. *(core)*
- .g.conf. *(core)*
- fiw workflow file. *(core)*

### 🚜  Changes
- BREAKING CHANGE: enforce strict local/global config schemas [useReq] *(config)*
Normalize .g.conf to local-only keys and $HOME/.g/g.conf to global-only keys.
Rename global legacy key editor to edit_command during --write-config.
Keep startup configuration loading read-only with scoped key application.
Update requirements, workflow model, references, and configuration IO tests.
- BREAKING CHANGE: split local and global configuration files [useReq] *(config)*
Update REQUIREMENTS for split local/global config contracts and renamed keys.
Refactor core config loading to read .g.conf and $HOME/.g/g.conf.
Rename default_module->default_commit_module and editor->edit_command.
Make --write-config add only missing keys without overwriting existing values.
Remove runtime autofill persistence for missing gp_command/gr_command.
Update config/help/conventional tests and refresh WORKFLOW/REFERENCES docs.
- normalize description casing and period [useReq] *(conventional-commit)*
Update REQ-022 to require conventional commit description normalization.
Capitalize first description character unless numeric.
Append trailing period when missing across conventional aliases.
Add regression tests and refresh workflow/reference docs.
- make gp/gr commands configurable [useReq] *(config)*
Update DES-006, REQ-014, and REQ-015 for gp/gr configurable command keys and runtime fallback behavior.
Add REQ-097 to persist missing gp_command/gr_command defaults into existing .g.conf while preserving existing keys.
Refactor core command resolution for gp/gr with executable availability checks and fallback to default templates.
Add tests for config IO autofill and gp/gr command execution/fallback; refresh WORKFLOW and REFERENCES docs.
- color status prefixes in section 6 [useReq] *(overview-o)*
Update REQ-094 for bright-red two-character status prefixes in CURRENT BRANCH STATE.
Apply prefix coloring in _overview_current_branch_state_lines and keep header normalization.
Add/adjust tests for section-6 prefix color rendering and regenerate workflow/reference docs.
- normalize work label and conditional state section [useReq] *(overview-o)*
Update REQ-084/088/094 and bump SRS version to 0.91.
Implement state-aware Work prefix color across overview sections.
Render section 6 only for non-clean worktree and normalize status header.
Add/adjust cmd_o tests for clean/non-clean rendering behavior.
Regenerate WORKFLOW and REFERENCES for updated call-trace/symbol map.
- render aligned configured branch rows [useReq] *(overview-branches)*
Replace section-5 lb-like listing with configured branch summary rows.
Render '<Identifier> | <latest commit subject>' with aligned identifiers.
Print commit subject in bright white bold and update cmd_o tests/spec/docs.
- group Work with aligned refs in topology [useReq] *(overview-topology)*
Update REQ-090 and REQ-092 to allow Work hash grouping.
Implement topology grouping change in _overview_ascii_topology_lines.
Adjust and extend cmd_o topology tests for aligned Work/Develop refs.
- add overview branches section ordering [useReq] *(core)*
update REQ-084 and REQ-094 for six-section overview layout; add section 5 BRANCHES in cmd_o using lb-equivalent branch listing; renumber current branch state heading to section 6; extend cmd_o tests for new section ordering and branch output; update WORKFLOW.md and regenerate REFERENCES.md
- replace qualitative topology with chronological-position tree [useReq] *(core)*
Updated REQ-089..REQ-093, added REQ-095 for chronological topology; Rewritten _overview_ascii_topology_lines to derive node positions
from actual commit hashes via git rev-parse and git merge-base
Removed qualitative-state labels (in_sync/ahead/behind/diverged/unknown)
from section-4 infographic output
Removed _overview_compare_relation, _overview_inverse_relation_state,
_overview_relation_state_text, _overview_normalize_relation_state,
and OVERVIEW_RELATION_STATES constant
Nodes grouped by shared commit hash, ordered most-ahead to most-behind; WorkingTree always separate with [state] annotation; Updated tests, WORKFLOW.md, REFERENCES.md
- rework overview topology infographic [useReq] *(core)*
revise REQ-089/090/092 for commit-alignment semantics\n- render section 4 as work-relative alignment groups\n- add silent relation helper for topology grouping\n- keep ahead/behind color semantics and section title\n- align tests, workflow trace, and regenerated references
- refine overview current branch rendering [useReq] *(core)*
update REQ-084/085/088/089 and add REQ-094 for section flow\n- add highlighted current-branch line in section 1\n- move git status branch-state output to new section 5\n- rename section 4 title to QUALITATIVE TOPOLOGY\n- align tests, workflow model, and regenerated references
- redesign o overview visual output [useReq] *(core)*
revise REQ-084..REQ-088 for configured branch/remote labels and color contract\n- render Work/Develop/Master and RemoteDevelop/RemoteMaster identifiers verbosely\n- enforce purple section titles, bright white subsection title, yellow branch tuples\n- color ahead counters bright green and behind counters bright red\n- align overview tests and refresh WORKFLOW/REFERENCES docs
- extend o overview with active worktree section [useReq] *(core)*
update REQ-084 and REQ-088 for third overview section behavior\n- add section 3 in cmd_o using git worktree list --verbose\n- keep existing overview templates/colors and update tests\n- refresh WORKFLOW.md and regenerate REFERENCES.md
- rename d alias to dr and align handlers [useReq] *(core)*
update REQ-008 and REQ-037 for dr visual diff alias; rename cmd_d to cmd_dr and map command dispatch key to dr; update diff alias tests and regenerate workflow/references docs
- add lsa alias and align lsi ls-files flags [useReq] *(cli)*
Requirement Delta: update REQ-008, REQ-080, add REQ-081 for ls/lsi/lsa behavior.
Implementation Delta: add cmd_lsa, update cmd_lsi flags, register HELP_TEXTS/COMMANDS entries.
Test Delta: extend tests/test_cmd_ls.py for lsi and new lsa forwarding assertions.
Docs Delta: update docs/WORKFLOW.md call-trace nodes and regenerate docs/REFERENCES.md.
Execution-ID: b348bd2e-c5b4-4c5e-b78c-beb5e3b6c97d

### 📚  Documentation
- align config file documentation [useReq] *(readme)*
Update README to document split local/global configuration files.
Document default_commit_module and global edit_command key usage.
Clarify --write-config normalization and legacy editor->edit_command migration.

## [0.5.0](https://github.com/Ogekuri/GAlias/compare/v0.4.0..v0.5.0) - 2026-02-22
### ⛰️  Features
- add worktree aliases wt/wtl/wtp/wtr docs/tests [2026-02-22 16:27:03] *(core)*

### 🐛  Bug Fixes
- normalize multiline list markers [2026-02-22 18:07:32] *(changelog)*
- normalize multiline entry indentation [2026-02-22 17:33:22] *(changelog)*
- align multiline markdown list indentation [2026-02-22 17:25:57] *(changelog)*

### 🚜  Changes
- remove blank commit separators [useReq] *(changelog)*
- resolve duplicate requirement id [useReq] *(requirements)*
- preserve multiline markdown bullets [useReq] *(changelog)*
- remove co-author trailers in markdown [2026-02-22 17:55:36] *(changelog)*
- normalize commit description line breaks [2026-02-22 17:39:18] *(changelog)*
- support breaking and multiline parsing [2026-02-22 13:26:20] *(changelog)*

## [0.4.0](https://github.com/Ogekuri/GAlias/compare/v0.3.0..v0.4.0) - 2026-02-22
### 🐛  Bug Fixes
- workflow. *(core)*

## [0.3.0](https://github.com/Ogekuri/GAlias/compare/v0.2.0..v0.3.0) - 2026-02-22
### 🐛  Bug Fixes
- fix workflow. *(core)*

### 🚜  Changes
- print containing branches for lt tags [2026-02-22 11:42:22] *(cmd_lt)*
- enforce tagged branch pushes in release flow [2026-02-22 11:01:35] *(core)*

### 📚  Documentation
- update README.md. *(core)*

## [0.2.0](https://github.com/Ogekuri/GAlias/compare/v0.1.0..v0.2.0) - 2026-02-22
### 🐛  Bug Fixes
- fix workflow. *(core)*

### 🚜  Changes
- revise tag lifecycle and docs [2026-02-22 10:32:49] *(release-flow)*

### 📚  Documentation
- update README.md. *(core)*
- update README.md. *(core)*

## [0.1.0](https://github.com/Ogekuri/GAlias/releases/tag/v0.1.0) - 2026-02-21
### ⛰️  Features
- update github workflow. *(core)*
- add dwcc and dccc diff aliases [2026-02-20 11:08:34] *(core)*
- add implement command and changelog support [2026-02-18 10:10:46] *(core)*
- add difftool aliases dw dc d [2026-02-17 17:07:56] *(core)*
- add req/ dir. *(core)*
- add test .g.conf for debug. *(core)*
- add clean.sh script. *(core)*
- add pathspec to requirements.txt *(core)*
- add new version check. *(core)*
- removed obsolete release command. *(core)*
- add support for --ver and --version commands. *(core)*
- add ra command. *(core)*
- release version: 0.0.4 *(core)*
- added new release command. *(core)*
- release version: 0.0.3 *(core)*
- release version: 0.0.2 *(core)*
- release version: 0.0.1 *(core)*
- draft release. *(core)*

### 🐛  Bug Fixes
- document module prefix and backup usage [2026-02-21 19:48:24] *(help)*
- fix workflow. *(core)*
- fix workflow file. *(core)*
- fix workflow. *(core)*
- workflow fix. *(core)*
- workflow fix. *(core)*
- workflow fix. *(core)*
- workflow fix. *(core)*
- workflow fix. *(core)*
- workflow fix. *(core)*
- workflow fix. *(core)*
- workflow fix. *(core)*
- workflow fix. *(core)*
- Update REFERENCES.md based on current implementation [2026-02-20 15:08:15] *(docs)*
- drop prova ver rule [2026-02-10 18:54:24] *(ver)*
- normalize git ls-files version paths [2026-02-10 18:22:17] *(ver)*
- normalize pathspec matching and update tests/docs [2026-02-10 17:58:26] *(ver)*
- WORKFLOW.md position. *(core)*
- fix undefined function references [2026-02-04 09:21:40] *(ori)*
- anchor ver_rules glob matching to repo root [2026-02-03 13:21:15] *(useReq)*
- change cover strings. *(core)*
- fix virtual environment creation on g.sh script. *(core)*
- add regression test for --include-draft *(core)*
- fix .gitignore file. *(core)*
- manual update version numbers. *(core)*
- minor changes on major, minor, patch prints. *(core)*
- fix changelog command. *(core)*
- fix history on chanchelog command. *(core)*
- fix history on chanchelog command. *(core)*
- fix on changelog command. *(core)*
- fix test according new code. *(core)*
- minor fix on patch command. *(core)*

### 🚜  Changes
- add backup workflow command [2026-02-21 19:39:09] *(backup)*
- add --disable-history and local history link resolver [2026-02-21 19:18:29] *(changelog)*
- resolve GitHub URL from master-branch remote using only local git commands [2026-02-21 18:15:15] *(_canonical_origin_base)*
Add _get_remote_name_for_branch: queries git config branch.<master>.remote, falls back to origin; Update _canonical_origin_base: uses master-branch remote instead of hardcoded origin; REQ-043 updated: # History links use GitHub templates with OWNER/REPO from master remote URL; REQ-046 added: URL resolver contract (local git commands only, SSH+HTTPS parsing); tests/test_changelog_command.py: GetRemoteNameForBranchTest + CanonicalOriginBaseTest added (9 new cases)
- scope # History to changelog-body tags only [2026-02-21 17:39:45] *(changelog)*
REQ-043 updated: # History now contains only tags present in the changelog body; REQ-068 added: minor-only tags without --include-patch; minor + latest patch with --include-patch; generate_changelog_document: removed list_tags_sorted_by_date(merged_ref=HEAD) call; builds history_tags from minor_tags + optional latest_patch; Tests: replaced test_history_uses_tags_merged_into_head with two focused tests covering both modes
- restrict patch release to develop-only branch integration; update major/minor help [2026-02-21 17:17:41] *(patch)*
REQ-045 added: patch MUST NOT merge/push master; major/minor MUST merge/push develop+master; _execute_release_flow: master branch steps conditioned on level != "patch"; HELP_TEXTS: major and minor now mention Options: --include-patch; Doxygen: updated @details and @satisfies for cmd_major, cmd_minor, cmd_patch, _execute_release_flow; tests: added test_patch_release_skips_master_steps, test_major/minor_release_includes_master_steps; docs/REQUIREMENTS.md: version 0.67, REQ-045 appended; docs/WORKFLOW.md: call-trace updated for level-conditional master branch steps; docs/REFERENCES.md: regenerated
Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>
- move scope indicator to suffix in changelog entry lines [2026-02-21 17:05:56] *(categorize_commit)*
- group by minor releases; replace --include-unreleased with --include-patch [2026-02-21 16:41:16] *(changelog)*
- remove include-draft flag path [2026-02-21 16:21:11] *(core)*
- update release marker commit format [2026-02-21 11:25:21] *(core)*
- amend first release commit from WIP when possible [2026-02-20 13:49:48] *(release-flow)*
- amend conventional commits on pending wip [2026-02-20 13:22:59] *(commit)*
- align command handler naming with aliases [2026-02-20 11:28:33] *(core)*
- rename diff aliases to dwc/dcc and align specs/tests [2026-02-20 11:01:23] *(core)*
- add multi-format doxygen generation workflow [2026-02-17 15:20:24] *(doxygen)*
- enforce doxygen metadata coverage [2026-02-17 15:01:55] *(core)*
- remove doc-comment requirements and normalize source comments [2026-02-15 19:42:27] *(core)*
- standardize Doxygen documentation and specs [2026-02-15 19:26:22] *(core)*
- switch ver matching to rglob and update specs/tests [2026-02-10 19:09:39] *(ver)*
- update ver verbose/debug requirements and tests [2026-02-10 17:44:31] *(core)*
- rename ori command to str, update requirements, code, and comments [2026-02-04 09:26:42] *(str)*
- Add ori command for remote inspection [2026-02-04 08:14:31] *(ori)*
- Optimize performance with git ls-files and version check cache [2026-02-03 14:01:40] *(useReq)*
- filter ver_rules matches from cache paths and cover tests [2026-02-03 13:39:07] *(useReq)*
- use pathspec gitignore for ver_rules matching [2026-02-03 13:28:29] *(useReq)*
- add cover conventional commit alias with emoji 🎯 and update requirements [2026-01-25 14:36:20] *(useReq)*
- add 'refactor' conventional commit type and alias; update requirements to include refactor and ✨ icon [e283ce7d-85bb-472c-b36a-e7c70b68f0ce] *(useReq)*

### ✨  Refactor
- cache ver/chver file discovery and rule contexts [2026-02-21 19:08:32] *(versioning)*

### 📚  Documentation
- Review README.md. *(core)*
- update README.md. *(core)*
- review README.md. *(core)*
- Review README.md. *(core)*
- update README.md. *(core)*
- regenerate runtime model [2026-02-20 15:32:32] *(workflow)*
- Update WORKFLOW.md to match current implementation [2026-02-20 15:16:17] *(core)*
- refresh references index [2026-02-19 17:52:25] *(core)*
- regenerate runtime execution model [2026-02-19 17:47:51] *(workflow)*
- generate source references documentation [2026-02-15 19:19:57] *(references)*
- regenerate workflow call tree [2026-02-15 18:54:30] *(core)*
- add workflow documentation [2026-02-09 16:19:23] *(core)*
- update workflow documentation [2026-02-09 10:24:18] *(core)*
- update WORKFLOW.md with comprehensive technical call tree [2026-02-09 10:19:09] *(core)*
- create WORKFLOW.md with technical call tree structure [2026-02-09 09:53:54] *(core)*
- update WORKFLOW.md with comprehensive technical call tree [2026-02-09 09:25:32] *(core)*
- add workflow analysis [2026-02-08 19:00:42] *(core)*
- update README.md. *(core)*
- add WORKFLOW.md. *(core)*
- update README.md and TODO.md files. *(core)*
- fix command's help. *(core)*
- change TODO.md. *(core)*
- update README.md. *(core)*
- update requirements.md *(core)*
- update requirements file. *(core)*

### ⚙️  Miscellaneous Tasks
- update prompts. *(core)*
- fix git repo. *(core)*


# History

- \[0.1.0\]: https://github.com/Ogekuri/GAlias/releases/tag/v0.1.0
- \[0.2.0\]: https://github.com/Ogekuri/GAlias/releases/tag/v0.2.0
- \[0.3.0\]: https://github.com/Ogekuri/GAlias/releases/tag/v0.3.0
- \[0.4.0\]: https://github.com/Ogekuri/GAlias/releases/tag/v0.4.0
- \[0.5.0\]: https://github.com/Ogekuri/GAlias/releases/tag/v0.5.0
- \[0.6.0\]: https://github.com/Ogekuri/GAlias/releases/tag/v0.6.0
- \[0.7.0\]: https://github.com/Ogekuri/GAlias/releases/tag/v0.7.0
- \[0.8.0\]: https://github.com/Ogekuri/GAlias/releases/tag/v0.8.0
- \[0.9.0\]: https://github.com/Ogekuri/GAlias/releases/tag/v0.9.0
- \[0.10.0\]: https://github.com/Ogekuri/GAlias/releases/tag/v0.10.0
- \[0.11.0\]: https://github.com/Ogekuri/GAlias/releases/tag/v0.11.0
- \[0.12.0\]: https://github.com/Ogekuri/GAlias/releases/tag/v0.12.0
- \[0.13.0\]: https://github.com/Ogekuri/GAlias/releases/tag/v0.13.0
- \[0.14.0\]: https://github.com/Ogekuri/GAlias/releases/tag/v0.14.0
- \[0.15.0\]: https://github.com/Ogekuri/GAlias/releases/tag/v0.15.0
- \[0.16.0\]: https://github.com/Ogekuri/GAlias/releases/tag/v0.16.0
- \[0.17.0\]: https://github.com/Ogekuri/GAlias/releases/tag/v0.17.0
- \[0.18.0\]: https://github.com/Ogekuri/GAlias/releases/tag/v0.18.0
- \[0.19.0\]: https://github.com/Ogekuri/GAlias/releases/tag/v0.19.0
- \[0.20.0\]: https://github.com/Ogekuri/GAlias/releases/tag/v0.20.0
- \[0.21.0\]: https://github.com/Ogekuri/GAlias/releases/tag/v0.21.0
- \[0.22.0\]: https://github.com/Ogekuri/GAlias/releases/tag/v0.22.0
- \[0.23.0\]: https://github.com/Ogekuri/GAlias/releases/tag/v0.23.0
- \[0.24.0\]: https://github.com/Ogekuri/GAlias/releases/tag/v0.24.0
- \[0.25.0\]: https://github.com/Ogekuri/GAlias/releases/tag/v0.25.0
- \[0.26.0\]: https://github.com/Ogekuri/GAlias/releases/tag/v0.26.0
- \[0.27.0\]: https://github.com/Ogekuri/GAlias/releases/tag/v0.27.0
- \[0.28.0\]: https://github.com/Ogekuri/GAlias/releases/tag/v0.28.0
- \[0.29.0\]: https://github.com/Ogekuri/GAlias/releases/tag/v0.29.0
- \[0.30.0\]: https://github.com/Ogekuri/GAlias/releases/tag/v0.30.0
- \[0.31.0\]: https://github.com/Ogekuri/GAlias/releases/tag/v0.31.0
- \[0.32.0\]: https://github.com/Ogekuri/GAlias/releases/tag/v0.32.0
- \[0.33.0\]: https://github.com/Ogekuri/GAlias/releases/tag/v0.33.0
- \[0.34.0\]: https://github.com/Ogekuri/GAlias/releases/tag/v0.34.0
- \[0.35.0\]: https://github.com/Ogekuri/GAlias/releases/tag/v0.35.0
- \[0.36.0\]: https://github.com/Ogekuri/GAlias/releases/tag/v0.36.0
- \[0.37.0\]: https://github.com/Ogekuri/GAlias/releases/tag/v0.37.0
- \[0.38.0\]: https://github.com/Ogekuri/GAlias/releases/tag/v0.38.0
- \[0.39.0\]: https://github.com/Ogekuri/GAlias/releases/tag/v0.39.0
- \[0.40.0\]: https://github.com/Ogekuri/GAlias/releases/tag/v0.40.0
- \[0.41.0\]: https://github.com/Ogekuri/GAlias/releases/tag/v0.41.0
- \[0.42.0\]: https://github.com/Ogekuri/GAlias/releases/tag/v0.42.0
- \[0.43.0\]: https://github.com/Ogekuri/GAlias/releases/tag/v0.43.0
- \[0.44.0\]: https://github.com/Ogekuri/GAlias/releases/tag/v0.44.0
- \[0.45.0\]: https://github.com/Ogekuri/GAlias/releases/tag/v0.45.0
- \[0.46.0\]: https://github.com/Ogekuri/GAlias/releases/tag/v0.46.0
- \[0.47.0\]: https://github.com/Ogekuri/GAlias/releases/tag/v0.47.0
- \[0.48.0\]: https://github.com/Ogekuri/GAlias/releases/tag/v0.48.0
- \[0.49.0\]: https://github.com/Ogekuri/GAlias/releases/tag/v0.49.0
- \[0.50.0\]: https://github.com/Ogekuri/GAlias/releases/tag/v0.50.0
- \[0.51.0\]: https://github.com/Ogekuri/GAlias/releases/tag/v0.51.0
- \[0.51.2\]: https://github.com/Ogekuri/GAlias/releases/tag/v0.51.2

[0.1.0]: https://github.com/Ogekuri/GAlias/releases/tag/v0.1.0
[0.2.0]: https://github.com/Ogekuri/GAlias/compare/v0.1.0..v0.2.0
[0.3.0]: https://github.com/Ogekuri/GAlias/compare/v0.2.0..v0.3.0
[0.4.0]: https://github.com/Ogekuri/GAlias/compare/v0.3.0..v0.4.0
[0.5.0]: https://github.com/Ogekuri/GAlias/compare/v0.4.0..v0.5.0
[0.6.0]: https://github.com/Ogekuri/GAlias/compare/v0.5.0..v0.6.0
[0.7.0]: https://github.com/Ogekuri/GAlias/compare/v0.6.0..v0.7.0
[0.8.0]: https://github.com/Ogekuri/GAlias/compare/v0.7.0..v0.8.0
[0.9.0]: https://github.com/Ogekuri/GAlias/compare/v0.8.0..v0.9.0
[0.10.0]: https://github.com/Ogekuri/GAlias/compare/v0.9.0..v0.10.0
[0.11.0]: https://github.com/Ogekuri/GAlias/compare/v0.10.0..v0.11.0
[0.12.0]: https://github.com/Ogekuri/GAlias/compare/v0.11.0..v0.12.0
[0.13.0]: https://github.com/Ogekuri/GAlias/compare/v0.12.0..v0.13.0
[0.14.0]: https://github.com/Ogekuri/GAlias/compare/v0.13.0..v0.14.0
[0.15.0]: https://github.com/Ogekuri/GAlias/compare/v0.14.0..v0.15.0
[0.16.0]: https://github.com/Ogekuri/GAlias/compare/v0.15.0..v0.16.0
[0.17.0]: https://github.com/Ogekuri/GAlias/compare/v0.16.0..v0.17.0
[0.18.0]: https://github.com/Ogekuri/GAlias/compare/v0.17.0..v0.18.0
[0.19.0]: https://github.com/Ogekuri/GAlias/compare/v0.18.0..v0.19.0
[0.20.0]: https://github.com/Ogekuri/GAlias/compare/v0.19.0..v0.20.0
[0.21.0]: https://github.com/Ogekuri/GAlias/compare/v0.20.0..v0.21.0
[0.22.0]: https://github.com/Ogekuri/GAlias/compare/v0.21.0..v0.22.0
[0.23.0]: https://github.com/Ogekuri/GAlias/compare/v0.22.0..v0.23.0
[0.24.0]: https://github.com/Ogekuri/GAlias/compare/v0.23.0..v0.24.0
[0.25.0]: https://github.com/Ogekuri/GAlias/compare/v0.24.0..v0.25.0
[0.26.0]: https://github.com/Ogekuri/GAlias/compare/v0.25.0..v0.26.0
[0.27.0]: https://github.com/Ogekuri/GAlias/compare/v0.26.0..v0.27.0
[0.28.0]: https://github.com/Ogekuri/GAlias/compare/v0.27.0..v0.28.0
[0.29.0]: https://github.com/Ogekuri/GAlias/compare/v0.28.0..v0.29.0
[0.30.0]: https://github.com/Ogekuri/GAlias/compare/v0.29.0..v0.30.0
[0.31.0]: https://github.com/Ogekuri/GAlias/compare/v0.30.0..v0.31.0
[0.32.0]: https://github.com/Ogekuri/GAlias/compare/v0.31.0..v0.32.0
[0.33.0]: https://github.com/Ogekuri/GAlias/compare/v0.32.0..v0.33.0
[0.34.0]: https://github.com/Ogekuri/GAlias/compare/v0.33.0..v0.34.0
[0.35.0]: https://github.com/Ogekuri/GAlias/compare/v0.34.0..v0.35.0
[0.36.0]: https://github.com/Ogekuri/GAlias/compare/v0.35.0..v0.36.0
[0.37.0]: https://github.com/Ogekuri/GAlias/compare/v0.36.0..v0.37.0
[0.38.0]: https://github.com/Ogekuri/GAlias/compare/v0.37.0..v0.38.0
[0.39.0]: https://github.com/Ogekuri/GAlias/compare/v0.38.0..v0.39.0
[0.40.0]: https://github.com/Ogekuri/GAlias/compare/v0.39.0..v0.40.0
[0.41.0]: https://github.com/Ogekuri/GAlias/compare/v0.40.0..v0.41.0
[0.42.0]: https://github.com/Ogekuri/GAlias/compare/v0.41.0..v0.42.0
[0.43.0]: https://github.com/Ogekuri/GAlias/compare/v0.42.0..v0.43.0
[0.44.0]: https://github.com/Ogekuri/GAlias/compare/v0.43.0..v0.44.0
[0.45.0]: https://github.com/Ogekuri/GAlias/compare/v0.44.0..v0.45.0
[0.46.0]: https://github.com/Ogekuri/GAlias/compare/v0.45.0..v0.46.0
[0.47.0]: https://github.com/Ogekuri/GAlias/compare/v0.46.0..v0.47.0
[0.48.0]: https://github.com/Ogekuri/GAlias/compare/v0.47.0..v0.48.0
[0.49.0]: https://github.com/Ogekuri/GAlias/compare/v0.48.0..v0.49.0
[0.50.0]: https://github.com/Ogekuri/GAlias/compare/v0.49.0..v0.50.0
[0.51.0]: https://github.com/Ogekuri/GAlias/compare/v0.50.0..v0.51.0
[0.51.2]: https://github.com/Ogekuri/GAlias/compare/v0.51.0..v0.51.2
