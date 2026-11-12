## @file test_release_workflow_pypi.py
# @brief Unit tests validating the PyPI release workflow and packaging contracts.

import re
import tomllib
import unittest
from pathlib import Path


## @brief Test suite for release-pypi.yml workflow and PyPI packaging contracts.
# @details Level 1 static-contract tests over committed release assets: verifies
#          the workflow rename (REQ-112), provenance attestation of the tagged
#          commit pre-built artifacts without any distribution build
#          (REQ-113, REQ-313), preserved GitHub Release upload of the tagged
#          commit assets (REQ-114), OIDC permissions (REQ-193), PyPI Trusted
#          Publishing post-steps without credentials over the unchanged
#          pre-built distributions (REQ-194, REQ-195, REQ-315), PyPI project
#          metadata (REQ-196), PEP 639 license declaration (REQ-197), README
#          install documentation (REQ-198), Node24 runner-generation pins
#          without Node20 opt-out overrides (REQ-211, REQ-212, REQ-213), the
#          tagged-artifact validation gate (REQ-314), and the publication
#          pipeline that runs no build-preparatory validation and is gated only
#          on branch containment (REQ-228, REQ-229).
# @satisfies REQ-112, REQ-113, REQ-114, REQ-193, REQ-194, REQ-195, REQ-196, REQ-197, REQ-198, REQ-211, REQ-212, REQ-213, REQ-228, REQ-229, REQ-313, REQ-314, REQ-315
class ReleaseWorkflowPyPiTest(unittest.TestCase):
    ## @brief Repository root path used by release-contract tests.
    REPO_ROOT = Path(__file__).resolve().parents[1]

    ## @brief Resolve the release workflow file path.
    # @return {Path} Absolute path of .github/workflows/release-pypi.yml.
    def _workflow_path(self) -> Path:
        return self.REPO_ROOT / ".github" / "workflows" / "release-pypi.yml"

    ## @brief Read the release workflow text.
    # @return {str} Full YAML text of the release workflow.
    def _workflow_text(self) -> str:
        return self._workflow_path().read_text(encoding="utf-8")

    ## @brief Extract one workflow step block by anchor token.
    # @details Returns the text spanning from the `- name:` line preceding the
    #          anchor occurrence up to the next sibling step start or EOF.
    # @param anchor {str} Unique token identifying the step (e.g. action ref).
    # @return {str} Step block text containing the anchor.
    def _workflow_step_block(self, anchor: str) -> str:
        text = self._workflow_text()
        anchor_index = text.index(anchor)
        step_start = text.rindex("\n      - name:", 0, anchor_index)
        next_step = text.find("\n      - name:", anchor_index)
        step_end = len(text) if next_step == -1 else next_step
        return text[step_start:step_end]

    ## @brief Load the pyproject.toml project table.
    # @return {dict} Parsed [project] table mapping.
    def _pyproject(self) -> dict:
        return tomllib.loads((self.REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8"))

    ## @brief Verify workflow file is renamed to release-pypi.yml.
    # @return None.
    # @satisfies REQ-112
    def test_workflow_file_renamed_to_release_pypi(self):
        self.assertTrue(self._workflow_path().is_file())
        legacy = self.REPO_ROOT / ".github" / "workflows" / "release-uvx.yml"
        self.assertFalse(legacy.exists())

    ## @brief Verify workflow triggers and master-containment gate are preserved.
    # @return None.
    # @satisfies REQ-112
    def test_workflow_triggers_and_master_gate_preserved(self):
        text = self._workflow_text()
        self.assertIn("workflow_dispatch:", text)
        self.assertIn("'v[0-9]+.[0-9]+.[0-9]+'", text)
        self.assertIn("origin/master", text)

    ## @brief Verify workflow grants OIDC release permissions.
    # @return None.
    # @satisfies REQ-193
    def test_workflow_grants_oidc_release_permissions(self):
        text = self._workflow_text()
        permissions_block = text[text.index("permissions:") : text.index("jobs:")]
        self.assertIn("contents: write", permissions_block)
        self.assertIn("id-token: write", permissions_block)
        self.assertIn("attestations: write", permissions_block)

    ## @brief Verify provenance attestation covers the pre-built tagged artifacts.
    # @details REQ-113 and REQ-313: the workflow attests the pre-built `dist/*`
    #          artifacts of the tagged commit with Python 3.11 and never runs a
    #          distribution build inside GitHub Actions.
    # @return None.
    # @satisfies REQ-113, REQ-313
    def test_workflow_attests_prebuilt_artifacts_without_build(self):
        # Arrange
        text = self._workflow_text()
        # Act
        attestation_block = self._workflow_step_block("actions/attest-build-provenance")
        # Assert
        self.assertIn('python-version: "3.11"', text)
        self.assertIn("subject-path: dist/*", attestation_block)
        for build_command in ("python -m build", "uv build", "scripts/build.sh"):
            self.assertNotIn(build_command, text)
        self.assertNotIn("scripts/pre-release-check.sh", text)

    ## @brief Verify the tagged-commit pre-built artifacts are validated before use.
    # @details REQ-313 and REQ-314: the publish job requires exactly one
    #          sdist and one wheel named after the `pyproject.toml` name and
    #          version, requires both to be git-tracked in the tagged commit,
    #          and aborts before attestation and publication otherwise.
    # @return None.
    # @satisfies REQ-313, REQ-314
    def test_workflow_verifies_prebuilt_tagged_artifacts(self):
        # Arrange
        text = self._workflow_text()
        # Act
        verify_block = self._workflow_step_block("Verify pre-built release artifacts")
        # Assert
        self.assertIn("dist/galias-${VERSION}.tar.gz", verify_block)
        self.assertIn("dist/galias-${VERSION}-\"*.whl", verify_block)
        self.assertIn("git ls-files --error-unmatch", verify_block)
        self.assertIn("exit 1", verify_block)
        self.assertLess(
            text.index("Verify pre-built release artifacts"),
            text.index("actions/attest-build-provenance"),
        )
        self.assertLess(
            text.index("Verify pre-built release artifacts"),
            text.index("pypa/gh-action-pypi-publish"),
        )

    ## @brief Verify PyPI receives the unchanged pre-built distributions.
    # @details REQ-315: publication consumes the verified `dist/` directory of
    #          the tagged commit without any intermediate rebuild step.
    # @return None.
    # @satisfies REQ-315
    def test_workflow_publishes_prebuilt_distributions_to_pypi(self):
        # Arrange
        text = self._workflow_text()
        # Act
        job_block = text[text.index("  publish-release:") :]
        # Assert
        self.assertIn("pypa/gh-action-pypi-publish", job_block)
        for build_command in ("python -m build", "uv build", "scripts/build.sh"):
            self.assertNotIn(build_command, job_block)
        self.assertNotIn("scripts/pre-release-check.sh", job_block)

    ## @brief Verify GitHub Release step semantics are preserved.
    # @return None.
    # @satisfies REQ-114
    def test_workflow_github_release_step_preserved(self):
        release_block = self._workflow_step_block("softprops/action-gh-release")
        self.assertIn("draft: false", release_block)
        self.assertIn("prerelease: false", release_block)
        self.assertIn("files: dist/**/*", release_block)

    ## @brief Verify PyPI publication runs after the GitHub Release step.
    # @return None.
    # @satisfies REQ-195
    def test_workflow_pypi_publish_runs_after_github_release(self):
        text = self._workflow_text()
        release_index = text.index("softprops/action-gh-release")
        publish_index = text.index("pypa/gh-action-pypi-publish")
        self.assertLess(release_index, publish_index)

    ## @brief Verify PyPI publication uses OIDC without credential inputs.
    # @return None.
    # @satisfies REQ-194
    def test_workflow_pypi_publish_uses_oidc_without_credentials(self):
        publish_block = self._workflow_step_block("pypa/gh-action-pypi-publish")
        self.assertIn("uses: pypa/gh-action-pypi-publish@release/v1", publish_block)
        self.assertNotIn("password", publish_block)
        self.assertNotIn("api-token", publish_block)
        self.assertNotIn("secrets.", publish_block)

    ## @brief Verify pyproject declares PyPI-compliant project metadata.
    # @return None.
    # @satisfies REQ-196
    def test_pyproject_declares_pypi_project_metadata(self):
        project = self._pyproject()["project"]
        self.assertEqual(project["name"], "galias")
        self.assertTrue(project["description"])
        self.assertEqual(project["readme"], "README.md")
        self.assertEqual(project["requires-python"], ">=3.11")
        self.assertTrue(project["keywords"])
        self.assertTrue(project["classifiers"])
        urls = project["urls"]
        for key in ("Homepage", "Repository"):
            self.assertIn(key, urls)
            self.assertIn("https://github.com/Ogekuri/GAlias", urls[key])

    ## @brief Registered trove classifier inventory declared by pyproject.toml.
    # @details Exact-contract set of officially registered PyPI trove classifiers;
    #          PyPI warehouse rejects any classifier outside the published list
    #          with HTTP 400 during upload.
    VALID_TROVE_CLASSIFIERS = (
        "Development Status :: 4 - Beta",
        "Environment :: Console",
        "Intended Audience :: Developers",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Topic :: Software Development :: Version Control",
    )

    ## @brief Verify pyproject classifiers are registered trove entries.
    # @details Reproduces the PyPI upload 400 rejection: declaring the
    #          unregistered classifier
    #          `Topic :: Software Development :: Configuration Management`
    #          makes warehouse refuse the distribution metadata.
    # @return None.
    # @satisfies REQ-196
    def test_pyproject_classifiers_are_registered_trove_entries(self):
        project = self._pyproject()["project"]
        self.assertEqual(tuple(project["classifiers"]), self.VALID_TROVE_CLASSIFIERS)
        self.assertNotIn(
            "Topic :: Software Development :: Configuration Management",
            project["classifiers"],
        )

    ## @brief Verify pyproject declares a PEP 639 SPDX license.
    # @return None.
    # @satisfies REQ-197
    def test_pyproject_declares_pep639_spdx_license(self):
        project = self._pyproject()["project"]
        self.assertEqual(project["license"], "GPL-3.0-only")
        self.assertIn("LICENSE", project["license-files"])
        build_requires = self._pyproject()["build-system"]["requires"]
        setuptools_specs = [spec for spec in build_requires if spec.startswith("setuptools")]
        self.assertTrue(setuptools_specs)
        floor_versions = []
        for spec in setuptools_specs:
            version_match = re.search(r">=(\d+)", spec)
            if version_match is not None:
                floor_versions.append(int(version_match.group(1)))
        self.assertTrue(floor_versions)
        self.assertGreaterEqual(max(floor_versions), 77)

    ## @brief Verify README documents uv tool install as primary with uvx and GitHub sections.
    # @details REQ-198: primary install is `uv tool install galias` from PyPI with a
    #          dedicated uvx alternative-usage section and a dedicated non-primary
    #          GitHub install section covering `--upgrade --develop` (REQ-201).
    # @return None.
    # @satisfies REQ-198, REQ-199, REQ-201
    def test_readme_documents_uv_primary_with_uvx_and_github_sections(self):
        readme = (self.REPO_ROOT / "README.md").read_text(encoding="utf-8")
        for command in (
            "uv tool install galias",
            "uvx galias <command> [args...]",
            "uv tool install --from git+https://github.com/Ogekuri/GAlias galias",
            "g --upgrade --develop",
            "g --upgrade --force",
        ):
            self.assertIn(command, readme)
        for removed in (
            "sudo apt install pipx",
            "pipx ensurepath",
            "pipx install galias",
        ):
            self.assertNotIn(removed, readme)

    ## @brief Verify README documents the dual meaning of --dev/--develop (REQ-216).
    # @details REQ-216: the flags install the newest GitHub release tag with
    #          --upgrade and scope the release to develop on major/minor/patch.
    # @return None.
    # @satisfies REQ-216
    def test_readme_documents_dev_flag_dual_meaning(self):
        readme = (self.REPO_ROOT / "README.md").read_text(encoding="utf-8")
        self.assertIn("installs the newest tagged release from GitHub", readme)
        self.assertIn(
            "limit the release to the configured `develop` branch", readme
        )

    ## @brief Verify workflow pins Node24-based action major versions.
    # @details REQ-213: checkout v5, setup-python v6, and
    #          attest-build-provenance v3 execute on the Node24 runtime
    #          generation while every surrounding step stays unchanged; the
    #          removed build-preparatory job leaves no setup-uv step behind.
    # @return None.
    # @satisfies REQ-211, REQ-213
    def test_workflow_pins_node24_action_majors(self):
        # REQ-213: Node24-based action majors replace Node20-based majors.
        text = self._workflow_text()
        self.assertEqual(text.count("uses: actions/checkout@v5"), 2)
        self.assertIn("uses: actions/setup-python@v6", text)
        self.assertNotIn("uses: astral-sh/setup-uv@v6", text)
        self.assertIn("uses: actions/attest-build-provenance@v3", text)

    ## @brief Verify workflow keeps no Node20 fallback override.
    # @details REQ-211/REQ-212: automation must execute on the Node24 runner
    #          generation without transitional force or opt-out environments.
    # @return None.
    # @satisfies REQ-211, REQ-212
    def test_workflow_has_no_node20_optout_overrides(self):
        # REQ-212: no transitional Node20 opt-out or force environment remains.
        text = self._workflow_text()
        self.assertNotIn("node20", text.lower())
        self.assertNotIn("FORCE_JAVASCRIPT_ACTIONS_TO_NODE24", text)
        self.assertNotIn("ACTIONS_ALLOW_USE_UNSECURE_NODE_VERSION", text)
    ## @brief Verify the workflow runs no build-preparatory validation.
    # @details REQ-228: the workflow declares no `test-release` job and runs no
    #          `uv lock --check`, pytest suite, `scripts/build.sh`, or
    #          `scripts/pre-release-check.sh`, because no build ever executes
    #          inside GitHub Actions.
    # @return None.
    # @satisfies REQ-228
    def test_workflow_has_no_build_preparatory_validation(self):
        # Arrange
        text = self._workflow_text()
        # Assert
        for forbidden in (
            "test-release:",
            "uv lock --check",
            "uv run pytest",
            "uses: astral-sh/setup-uv@v6",
            "scripts/build.sh",
            "scripts/pre-release-check.sh",
        ):
            self.assertNotIn(forbidden, text)

    ## @brief Verify publish-release is gated only on the branch-containment job.
    # @details REQ-229: `needs` lists `check-branch` only, so no test, build, or
    #          pre-release validation job can gate publication.
    # @return None.
    # @satisfies REQ-229
    def test_workflow_gates_publish_release_only_on_check_branch(self):
        # Arrange
        text = self._workflow_text()
        # Act
        publish_job_block = text[text.index("  publish-release:"):]
        # Assert
        self.assertIn("needs: [check-branch]", publish_job_block)
        self.assertNotIn("test-release", publish_job_block)


if __name__ == "__main__":
    unittest.main()
