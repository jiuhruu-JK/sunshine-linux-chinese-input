from __future__ import annotations

import json
import tomllib
import unittest
from pathlib import Path

from dockle.config import load_config

PROJECT_ROOT = Path(__file__).resolve().parents[1]


class ProjectDogfoodTests(unittest.TestCase):
    def test_root_config_exercises_every_adapter(self) -> None:
        config = load_config(PROJECT_ROOT / "dockle.toml")

        self.assertEqual(
            [target.framework for target in config.targets],
            ["sphinx", "sphinx", "doxygen", "mkdocs", "jsdoc", "rustdoc"],
        )
        for target in config.targets:
            self.assertTrue(target.source.exists(), target.source)
        self.assertIsNone(config.project.home)
        self.assertTrue(config.targets[0].home)
        self.assertEqual(config.targets[0].output, config.build.output)
        self.assertEqual(
            config.project.logo,
            PROJECT_ROOT / "branding" / "dockle-logo.svg",
        )
        self.assertEqual(
            config.project.favicon,
            PROJECT_ROOT / "branding" / "dockle-logo.svg",
        )

    def test_conda_dependencies_are_hard_pinned(self) -> None:
        lines = (
            (PROJECT_ROOT / "environment.yml")
            .read_text(encoding="utf-8")
            .splitlines()
        )
        dependencies = []
        for line in lines[lines.index("dependencies:") + 1:]:
            if line and not line.startswith(" "):
                break
            if line.startswith("  - "):
                dependencies.append(line.removeprefix("  - "))

        self.assertTrue(dependencies)
        for dependency in dependencies:
            self.assertRegex(
                dependency, r"^[A-Za-z0-9_.-]+==[A-Za-z0-9_.+-]+$"
            )

    def test_furo_is_not_a_package_dependency(self) -> None:
        with (PROJECT_ROOT / "pyproject.toml").open("rb") as stream:
            project = tomllib.load(stream)["project"]
        declared = list(project.get("dependencies", []))
        for extra in project.get("optional-dependencies", {}).values():
            declared.extend(extra)

        self.assertNotIn("furo", " ".join(declared).lower())

    def test_lucide_runtime_is_managed_by_npm(self) -> None:
        with (PROJECT_ROOT / "package.json").open(encoding="utf-8") as stream:
            package = json.load(stream)
        self.assertEqual(package["name"], "@lizardbyte/dockle")
        self.assertEqual(package["version"], "0.0.0")
        self.assertEqual(package["author"], "LizardByte")
        self.assertEqual(package["license"], "MIT")
        self.assertNotIn("private", package)
        self.assertEqual(
            package["bin"]["dockle-jsdoc"], "bin/dockle-jsdoc.cjs"
        )
        self.assertEqual(package["dependencies"]["jsdoc"], "4.0.5")
        version = package["devDependencies"]["lucide"]
        runtime = (
            PROJECT_ROOT
            / "src"
            / "dockle"
            / "sphinx"
            / "themes"
            / "dockle"
            / "static"
            / "lucide.min.js"
        ).read_text(encoding="utf-8")

        self.assertRegex(version, r"^\d+\.\d+\.\d+$")
        self.assertTrue(
            runtime.startswith(f"/*! Lucide {version} | ISC |"),
            "run npm run sync:lucide after changing the Lucide dependency",
        )

    def test_highlighter_runtime_is_managed_by_npm(self) -> None:
        with (PROJECT_ROOT / "package.json").open(encoding="utf-8") as stream:
            package = json.load(stream)
        version = package["devDependencies"]["@highlightjs/cdn-assets"]
        fixture_manifest = PROJECT_ROOT / "third-party" / "highlight.js" / "package.json"
        with fixture_manifest.open(encoding="utf-8") as stream:
            fixtures = json.load(stream)
        runtime = (
            PROJECT_ROOT
            / "src"
            / "dockle"
            / "sphinx"
            / "themes"
            / "dockle"
            / "static"
            / "highlight.min.js"
        ).read_text(encoding="utf-8")

        self.assertRegex(version, r"^\d+\.\d+\.\d+$")
        self.assertEqual(fixtures["version"], version)
        self.assertTrue(
            runtime.startswith(
                f"/*! Highlight.js {version} | BSD-3-Clause |"
            ),
            "run npm run sync:highlighter after changing the dependency",
        )

    def test_third_party_browser_assets_are_generated_not_tracked(self) -> None:
        ignored = (PROJECT_ROOT / ".gitignore").read_text(encoding="utf-8")
        with (PROJECT_ROOT / "package.json").open(encoding="utf-8") as stream:
            package = json.load(stream)

        for filename in (
            "HIGHLIGHT_LICENSE.txt",
            "LUCIDE_LICENSE.txt",
            "highlight.min.js",
            "lucide.min.js",
        ):
            self.assertIn(
                f"src/dockle/sphinx/themes/dockle/static/{filename}",
                ignored,
            )
        self.assertEqual(package["scripts"]["prepack"], "npm run build")
        self.assertEqual(package["scripts"]["pretest"], "npm run build")

    def test_reference_doxygen_projects_are_not_dependencies(self) -> None:
        dependency_files = [
            PROJECT_ROOT / "pyproject.toml",
            PROJECT_ROOT / "package.json",
        ]

        declared = "\n".join(
            path.read_text(encoding="utf-8") for path in dependency_files
        ).lower()
        self.assertNotIn("doxygen-awesome-css", declared)
        self.assertNotIn("doxyconfig", declared)

    def test_component_references_are_composed_from_shared_source(self) -> None:
        common = (
            PROJECT_ROOT
            / "examples"
            / "shared"
            / "component-reference.md.inc"
        ).read_text(encoding="utf-8").strip()
        references = {
            "sphinx": PROJECT_ROOT / "examples" / "sphinx",
            "doxygen": PROJECT_ROOT / "examples" / "doxygen",
            "mkdocs": PROJECT_ROOT / "examples" / "mkdocs",
        }

        for framework, directory in references.items():
            specific = (
                directory / "component-reference.md.inc"
            ).read_text(encoding="utf-8").strip()
            generated = (
                PROJECT_ROOT
                / ".dockle"
                / "example-sources"
                / framework
                / "component-reference.md"
            ).read_text(encoding="utf-8")
            self.assertFalse((directory / "component-reference.md").exists())
            self.assertIn(common, generated, framework)
            self.assertIn(specific, generated, framework)
            self.assertIn('class="dockle-language-gallery"', generated)
            self.assertIn(
                'class="dockle-language-gallery-end"', generated
            )
            self.assertNotIn(" code block", specific.lower())

        shared_only_references = {
            "jsdoc": (
                PROJECT_ROOT
                / ".dockle"
                / "example-sources"
                / "jsdoc"
                / "tutorials"
                / "component-reference.md"
            ),
            "rustdoc": (
                PROJECT_ROOT
                / ".dockle"
                / "example-sources"
                / "rustdoc"
                / "component-reference.md"
            ),
        }
        for framework, generated_path in shared_only_references.items():
            generated = generated_path.read_text(encoding="utf-8")
            source = PROJECT_ROOT / "examples" / framework
            source_reference = source / "component-reference.md"
            if framework == "jsdoc":
                source_reference = source / "tutorials" / source_reference.name
            self.assertFalse((source / "component-reference.md.inc").exists())
            self.assertFalse(source_reference.exists())
            self.assertIn(common, generated, framework)
            self.assertIn('class="dockle-language-gallery"', generated)

        rst_reference = (
            PROJECT_ROOT
            / ".dockle"
            / "example-sources"
            / "sphinx"
            / "component-reference-rst.rst"
        ).read_text(encoding="utf-8")
        self.assertFalse(
            (
                PROJECT_ROOT
                / "examples"
                / "sphinx"
                / "component-reference-rst.rst"
            ).exists()
        )
        self.assertIn("actual reStructuredText code block", rst_reference)
        self.assertIn('class="dockle-language-gallery"', rst_reference)

    def test_command_examples_use_the_shared_shell_language(self) -> None:
        markdown_files = [
            PROJECT_ROOT / "README.md",
            PROJECT_ROOT / "examples" / "sphinx" / "index.md",
            PROJECT_ROOT / "examples" / "doxygen" / "README.md",
            PROJECT_ROOT / "examples" / "mkdocs" / "index.md",
            PROJECT_ROOT / "examples" / "jsdoc" / "README.md",
            PROJECT_ROOT / "examples" / "rustdoc" / "README.md",
        ]
        for path in markdown_files:
            source = path.read_text(encoding="utf-8")
            self.assertIn("```shell", source, path)
            self.assertNotIn("```console", source, path)

        for filename in ("index.rst", "distribution.rst"):
            source = (PROJECT_ROOT / "docs" / filename).read_text(
                encoding="utf-8"
            )
            self.assertIn(".. code-block:: shell", source, filename)
            self.assertNotIn(".. code-block:: console", source, filename)

    def test_python_packaging_uses_locked_uv_dependencies(self) -> None:
        with (PROJECT_ROOT / "pyproject.toml").open("rb") as stream:
            project = tomllib.load(stream)

        self.assertEqual(project["project"]["name"], "lizardbyte-dockle")
        self.assertEqual(project["project"]["version"], "0.0.0")
        self.assertEqual(
            project["project"]["authors"], [{"name": "LizardByte"}]
        )
        self.assertEqual(project["project"]["license"], "MIT")
        self.assertNotIn(
            "Development Status :: 2 - Pre-Alpha",
            project["project"]["classifiers"],
        )
        self.assertIn("test", project["dependency-groups"])
        self.assertIn("package", project["dependency-groups"])
        self.assertEqual(
            project["tool"]["hatch"]["build"]["targets"]["sdist"]["include"],
            ["/LICENSE", "/README.md", "/pyproject.toml", "/src"],
        )
        self.assertEqual(
            project["tool"]["hatch"]["build"]["artifacts"],
            [
                "/src/dockle/sphinx/themes/dockle/static/HIGHLIGHT_LICENSE.txt",
                "/src/dockle/sphinx/themes/dockle/static/LUCIDE_LICENSE.txt",
                "/src/dockle/sphinx/themes/dockle/static/highlight.min.js",
                "/src/dockle/sphinx/themes/dockle/static/lucide.min.js",
            ],
        )
        self.assertTrue((PROJECT_ROOT / "uv.lock").is_file())

    def test_pypi_publish_requires_a_stable_release_event(self) -> None:
        workflow = (
            PROJECT_ROOT / ".github" / "workflows" / "ci-release.yml"
        ).read_text(encoding="utf-8")

        self.assertIn("release:", workflow)
        self.assertIn("- released", workflow)
        self.assertIn("github.event.action == 'released'", workflow)
        self.assertIn("github.event.release.draft == false", workflow)
        self.assertIn("github.event.release.prerelease == false", workflow)
        self.assertIn("gh release download", workflow)
        self.assertIn("https://pypi.org/p/lizardbyte-dockle", workflow)
        self.assertIn('"lizardbyte_dockle-*.whl"', workflow)
        self.assertIn('"lizardbyte_dockle-*.tar.gz"', workflow)
        self.assertIn("gh-action-pypi-publish@", workflow)


if __name__ == "__main__":
    unittest.main()
