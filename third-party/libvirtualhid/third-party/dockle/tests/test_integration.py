from __future__ import annotations

import importlib.util
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from dockle.builders import BuildManager
from dockle.config import load_config


def _tool_available(name: str) -> bool:
    return _tool_path(name) is not None


def _tool_path(name: str) -> Path | None:
    discovered = shutil.which(name)
    if discovered is not None:
        return Path(discovered)
    scripts = Path(sys.executable).resolve().parent
    discovered = shutil.which(name, path=str(scripts))
    return Path(discovered) if discovered is not None else None


def _doxygen_path() -> Path | None:
    discovered = shutil.which("doxygen")
    if discovered:
        return Path(discovered)
    msys2 = Path("C:/msys64/ucrt64/bin/doxygen.exe")
    return msys2 if msys2.is_file() else None


def _jsdoc_path() -> Path | None:
    executable = "jsdoc.cmd" if sys.platform == "win32" else "jsdoc"
    project_local = (
        Path(__file__).resolve().parents[1]
        / "node_modules"
        / ".bin"
        / executable
    )
    if project_local.is_file():
        return project_local
    discovered = shutil.which("jsdoc")
    return Path(discovered) if discovered else None


class AdapterIntegrationTests(unittest.TestCase):
    @unittest.skipUnless(
        _tool_available("cmake") and _tool_available("sphinx-build"),
        "CMake and Sphinx are required",
    )
    def test_installed_cmake_module_builds_consumer_docs(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            docs = root / "docs"
            docs.mkdir()
            (docs / "index.rst").write_text(
                "Consumer\n========\n\nBuilt through CMake.\n",
                encoding="utf-8",
            )
            dockle = _tool_path("dockle")
            sphinx = _tool_path("sphinx-build")
            if dockle is None:
                self.fail("dockle is not installed on PATH")
            if sphinx is None:
                self.fail("sphinx-build is not installed on PATH")
            module_result = subprocess.run(
                [str(dockle), "cmake-dir"],
                cwd=root,
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertEqual(module_result.returncode, 0, module_result.stderr)
            module_dir = Path(module_result.stdout.strip())
            self.assertTrue((module_dir / "Dockle.cmake").is_file())

            config_path = root / "dockle.toml"
            config_path.write_text(
                f"""
[project]
name = "CMake consumer"

[tools]
sphinx = "{sphinx.as_posix()}"

[[targets]]
name = "docs"
framework = "sphinx"
source = "docs"
""",
                encoding="utf-8",
            )
            (root / "CMakeLists.txt").write_text(
                f"""cmake_minimum_required(VERSION 3.24)
project(dockle_consumer LANGUAGES NONE)
list(APPEND CMAKE_MODULE_PATH "{module_dir.as_posix()}")
set(DOCKLE_EXECUTABLE "{dockle.as_posix()}")
include(Dockle)
dockle_add_docs(docs CONFIG "{config_path.as_posix()}")
""",
                encoding="utf-8",
            )
            build = root / "build"
            configure = subprocess.run(
                ["cmake", "-S", str(root), "-B", str(build)],
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertEqual(configure.returncode, 0, configure.stderr)
            built = subprocess.run(
                ["cmake", "--build", str(build), "--target", "docs"],
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertEqual(built.returncode, 0, built.stderr)
            self.assertTrue((root / "_site" / "docs" / "index.html").is_file())

    @unittest.skipUnless(_doxygen_path(), "Doxygen is not installed")
    def test_doxygen_builds_with_native_theme_hook(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "src"
            source.mkdir()
            (source / "example.hpp").write_text(
                """/** @file */
/** An example value. */
inline constexpr int example = 42;
""",
                encoding="utf-8",
            )
            (source / "README.md").write_text(
                """# Example

```python
class Example:
    enabled = True
```

```javascript
const enabled = true;
```

```toml
enabled = true
```

@admonition{Compatible separator |:| Accepts ordinary content.}

@tabs_grouped{runtime|:|
@tab{Python|:|Install from PyPI.}
@tab{Node.js|:|Install from npm.}
}
""",
                encoding="utf-8",
            )
            config_path = root / "dockle.toml"
            config_path.write_text(
                f"""
[project]
name = "Example"

[tools]
doxygen = "{_doxygen_path().as_posix()}"

[[targets]]
name = "docs"
framework = "doxygen"
source = "src"
entry = "README.md"
""",
                encoding="utf-8",
            )
            config = load_config(config_path)

            results = BuildManager(config).build(config.targets)

            html = (config.targets[0].output / "index.html").read_text(
                encoding="utf-8"
            )
            self.assertGreaterEqual(results[0].themed_pages, 1)
            self.assertIn("dockle.css", html)
            self.assertIn("highlight.min.js", html)
            self.assertIn('data-dockle-framework="doxygen"', html)
            self.assertIn('data-dockle-language="python"', html)
            self.assertIn('data-dockle-language="javascript"', html)
            self.assertIn('data-dockle-language="toml"', html)
            self.assertNotIn("data-dockle-home", html)
            self.assertIn("data-dockle-brand", html)
            self.assertIn("Generated by", html)
            self.assertGreaterEqual(html.count('class="keyword"'), 2)
            self.assertIn("dockle-alert", html)
            self.assertIn("Accepts ordinary content.", html)
            self.assertIn("dockle-tabs-alias", html)
            self.assertIn('data-dockle-tab-group="runtime"', html)
            self.assertIn("dockle-tab-title", html)
            self.assertRegex(html, r"Doxygen [0-9]+\.[0-9]+")

    @unittest.skipUnless(
        _tool_available("sphinx-build"), "Sphinx is not installed"
    )
    def test_sphinx_builds_with_first_party_theme(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            docs = root / "docs"
            docs.mkdir()
            (docs / "index.rst").write_text(
                "Example\n=======\n\nA first-party Dockle theme.\n",
                encoding="utf-8",
            )
            config_path = root / "dockle.toml"
            config_path.write_text(
                """
[project]
name = "Example"
repository = "https://github.com/example/project"

[[targets]]
name = "docs"
framework = "sphinx"
source = "docs"

[targets.sphinx]
source_edit_link = "https://github.com/example/project/blob/main/docs/{filename}"
""",
                encoding="utf-8",
            )
            config = load_config(config_path)

            results = BuildManager(config).build(config.targets)

            html = (config.targets[0].output / "index.html").read_text(
                encoding="utf-8"
            )
            self.assertGreaterEqual(results[0].themed_pages, 1)
            self.assertIn('class="dockle-shell"', html)
            self.assertIn("_static/dockle.css", html)
            self.assertNotIn("data-dockle-home", html)
            self.assertIn('aria-current="page"', html)
            self.assertIn(
                'class="dockle-page-action dockle-repository-link"', html
            )
            self.assertIn(
                'data-dockle-repository-service="github"', html
            )
            self.assertIn(
                'href="https://github.com/example/project/blob/main/docs/index.rst"',
                html,
            )
            self.assertIn('data-lucide="pencil"', html)
            self.assertEqual(html.count('target="_blank"'), 2)
            self.assertEqual(html.count('rel="noopener noreferrer"'), 2)
            self.assertLess(
                html.index("dockle-source-edit"),
                html.index("dockle-repository-link"),
            )
            self.assertLess(
                html.index("dockle-repository-link"),
                html.index("data-dockle-theme-toggle"),
            )
            self.assertRegex(html, r"Sphinx [0-9]+\.[0-9]+")

    @unittest.skipUnless(
        _tool_available("sphinx-build"), "Sphinx is not installed"
    )
    def test_sphinx_home_target_publishes_root_and_comparison_cards(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            docs = root / "docs"
            docs.mkdir()
            (docs / "index.rst").write_text(
                "Example\n=======\n\n.. raw:: html\n\n"
                "   <div data-dockle-target-cards></div>\n",
                encoding="utf-8",
            )
            (root / "api").mkdir()
            config_path = root / "dockle.toml"
            config_path.write_text(
                """
[project]
name = "Example"

[[targets]]
name = "docs"
framework = "sphinx"
source = "docs"
home = true

[[targets]]
name = "api"
title = "API example"
framework = "doxygen"
source = "api"
""",
                encoding="utf-8",
            )
            config = load_config(config_path)

            results = BuildManager(config).build(config.targets[:1])

            html = (config.build.output / "index.html").read_text(
                encoding="utf-8"
            )
            self.assertGreaterEqual(results[0].themed_pages, 1)
            self.assertIn('data-dockle-framework="sphinx"', html)
            self.assertIn('class="dockle-portal-card" href="api/"', html)
            self.assertNotIn("data-dockle-home", html)

    @unittest.skipUnless(importlib.util.find_spec("sphinx"), "Sphinx is not installed")
    def test_sphinx_can_discover_dockle_as_a_standalone_theme(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "docs"
            output = root / "html"
            source.mkdir()
            (source / "conf.py").write_text(
                "project = 'Example'\nhtml_theme = 'dockle'\n",
                encoding="utf-8",
            )
            (source / "index.rst").write_text(
                "Example\n=======\n", encoding="utf-8"
            )
            completed = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "sphinx",
                    "-W",
                    "-b",
                    "html",
                    str(source),
                    str(output),
                ],
                check=False,
            )

            self.assertEqual(completed.returncode, 0)
            html = (output / "index.html").read_text(encoding="utf-8")
            self.assertIn('class="dockle-shell"', html)

    @unittest.skipUnless(_tool_available("mkdocs"), "MkDocs is not installed")
    def test_mkdocs_builds_with_first_party_theme(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            docs = root / "docs"
            docs.mkdir()
            (docs / "index.md").write_text(
                "# Example\n\nA themed MkDocs page.\n", encoding="utf-8"
            )
            config_path = root / "dockle.toml"
            config_path.write_text(
                """
[project]
name = "Example"

[[targets]]
name = "docs"
framework = "mkdocs"
source = "docs"
""",
                encoding="utf-8",
            )
            config = load_config(config_path)

            results = BuildManager(config).build(config.targets)

            html = (config.targets[0].output / "index.html").read_text(
                encoding="utf-8"
            )
            self.assertGreaterEqual(results[0].themed_pages, 1)
            self.assertIn('data-dockle-theme="mkdocs"', html)
            self.assertIn('class="dockle-shell"', html)
            self.assertIn("static/dockle.css", html)
            self.assertRegex(html, r"MkDocs [0-9]+\.[0-9]+")
            self.assertTrue(
                (config.targets[0].output / "static" / "dockle.css").is_file()
            )

    @unittest.skipUnless(_jsdoc_path(), "JSDoc is not installed")
    def test_jsdoc_builds_with_project_local_executable(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "src"
            source.mkdir()
            (source / "README.md").write_text(
                "# Example API\n", encoding="utf-8"
            )
            (source / "example.js").write_text(
                "/** Return the answer. @returns {number} The answer. */\nexport function answer() { return 42; }\n",
                encoding="utf-8",
            )
            config_path = root / "dockle.toml"
            config_path.write_text(
                f"""
[project]
name = "Example"

[tools]
jsdoc = "{_jsdoc_path().as_posix()}"

[[targets]]
name = "docs"
framework = "jsdoc"
source = "src"
entry = "README.md"
""",
                encoding="utf-8",
            )
            config = load_config(config_path)

            results = BuildManager(config).build(config.targets)

            html = (config.targets[0].output / "index.html").read_text(
                encoding="utf-8"
            )
            self.assertGreaterEqual(results[0].themed_pages, 1)
            self.assertIn('data-dockle-theme="jsdoc"', html)
            self.assertNotIn("data-dockle-home", html)
            self.assertIn("data-dockle-brand", html)
            self.assertNotIn('class="page-title">Home', html)
            self.assertNotIn("Documentation generated by", html)
            self.assertRegex(html, r"JSDoc [0-9]+\.[0-9]+")

    @unittest.skipUnless(_tool_available("cargo"), "Cargo is not installed")
    def test_rustdoc_builds_and_receives_compatibility_theme(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            crate = root / "crate"
            source = crate / "src"
            source.mkdir(parents=True)
            (crate / "Cargo.toml").write_text(
                '[package]\nname = "dockle-fixture"\nversion = "0.1.0"\nedition = "2024"\n',
                encoding="utf-8",
            )
            (source / "lib.rs").write_text(
                "//! A rustdoc fixture.\n", encoding="utf-8"
            )
            extra_file = root / "rustdoc-extra.css"
            extra_file.write_text("body {}\n", encoding="utf-8")
            config_path = root / "dockle.toml"
            config_path.write_text(
                """
[project]
name = "Example"

[[targets]]
name = "docs"
framework = "rustdoc"
source = "crate"

[targets.rustdoc]
extra_files = ["rustdoc-extra.css"]
""",
                encoding="utf-8",
            )
            config = load_config(config_path)

            results = BuildManager(config).build(config.targets)

            root_html = (config.targets[0].output / "index.html").read_text(
                encoding="utf-8"
            )
            html = (
                config.targets[0].output / "dockle_fixture" / "index.html"
            ).read_text(encoding="utf-8")
            self.assertGreaterEqual(results[0].themed_pages, 1)
            self.assertIn('http-equiv="refresh"', root_html)
            self.assertIn("window.location.replace", root_html)
            self.assertIn("url=dockle_fixture/", root_html)
            self.assertIn('data-dockle-theme="rustdoc"', html)
            self.assertIn("data-dockle-brand", html)
            self.assertRegex(html, r"rustdoc [0-9]+\.[0-9]+")
            self.assertTrue(
                (config.targets[0].output / "_dockle" / "dockle.css").is_file()
            )
            self.assertTrue(
                (
                    config.targets[0].output
                    / "dockle_fixture"
                    / extra_file.name
                ).is_file()
            )
            portal = (config.build.output / "index.html").read_text(
                encoding="utf-8"
            )
            self.assertIn('href="docs/dockle_fixture/"', portal)


if __name__ == "__main__":
    unittest.main()
