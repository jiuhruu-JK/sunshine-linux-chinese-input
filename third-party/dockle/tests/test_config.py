from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from dockle.config import ConfigError, load_config

MINIMAL_CONFIG = """
[project]
name = "Example"

[[targets]]
name = "manual"
framework = "sphinx"
source = "docs"
"""


class ConfigTests(unittest.TestCase):
    def test_loads_defaults_and_resolves_paths(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            path = root / "dockle.toml"
            path.write_text(MINIMAL_CONFIG, encoding="utf-8")

            config = load_config(path)

            self.assertEqual(config.project.name, "Example")
            self.assertEqual(config.build.output, root.resolve() / "_site")
            self.assertEqual(config.targets[0].source, root.resolve() / "docs")
            self.assertEqual(
                config.targets[0].output, root.resolve() / "_site" / "manual"
            )
            self.assertEqual(config.targets[0].title, "Manual")
            self.assertEqual(config.targets[0].description, "")
            self.assertIsNone(config.targets[0].doxygen)
            self.assertFalse(config.build.strict)
            self.assertTrue(config.build.clean)

    def test_doxygen_warning_defaults_are_enabled(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "docs").mkdir()
            path = root / "dockle.toml"
            path.write_text(
                MINIMAL_CONFIG.replace(
                    'framework = "sphinx"', 'framework = "doxygen"'
                ),
                encoding="utf-8",
            )

            doxygen = load_config(path).targets[0].doxygen

            assert doxygen is not None
            self.assertTrue(doxygen.warn_if_undoc_enum_val)
            self.assertTrue(doxygen.warn_if_undocumented)
            self.assertTrue(doxygen.warn_no_paramdoc)

    def test_rejects_unknown_keys(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "dockle.toml"
            contents = MINIMAL_CONFIG.replace(
                'name = "Example"', 'name = "Example"\ncolour = "blue"'
            )
            path.write_text(contents, encoding="utf-8")

            with self.assertRaisesRegex(ConfigError, "unknown key.*colour"):
                load_config(path)

    def test_resolves_project_assets(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "home.md").write_text("# Home\n", encoding="utf-8")
            (root / "logo.png").write_bytes(b"logo")
            (root / "favicon.svg").write_text("<svg/>", encoding="utf-8")
            path = root / "dockle.toml"
            contents = MINIMAL_CONFIG.replace(
                'name = "Example"',
                'name = "Example"\nhome = "home.md"\nlogo = "logo.png"\n'
                'favicon = "favicon.svg"',
            )
            path.write_text(contents, encoding="utf-8")

            config = load_config(path)

            self.assertEqual(config.project.home, (root / "home.md").resolve())
            self.assertEqual(config.project.logo, (root / "logo.png").resolve())
            self.assertEqual(
                config.project.favicon,
                (root / "favicon.svg").resolve(),
            )

    def test_accepts_remote_project_assets(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "dockle.toml"
            logo = "https://example.com/logo.png"
            favicon = "https://example.com/favicon.svg"
            path.write_text(
                MINIMAL_CONFIG.replace(
                    'name = "Example"',
                    f'name = "Example"\nlogo = "{logo}"\nfavicon = "{favicon}"',
                ),
                encoding="utf-8",
            )

            project = load_config(path).project
            self.assertEqual(project.logo, logo)
            self.assertEqual(project.favicon, favicon)

    def test_project_logo_is_the_default_favicon(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "dockle.toml"
            logo = "https://example.com/logo.svg"
            path.write_text(
                MINIMAL_CONFIG.replace(
                    'name = "Example"', f'name = "Example"\nlogo = "{logo}"'
                ),
                encoding="utf-8",
            )

            project = load_config(path).project

            self.assertEqual(project.logo, logo)
            self.assertEqual(project.favicon, logo)

    def test_derives_project_version_from_read_the_docs(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "dockle.toml"
            path.write_text(
                MINIMAL_CONFIG.replace(
                    'name = "Example"', 'name = "Example"\nversion = "0.0.0"'
                ),
                encoding="utf-8",
            )

            with patch.dict("os.environ", {"READTHEDOCS_VERSION": "908"}):
                self.assertEqual(load_config(path).project.version, "0.0.908")
            with patch.dict("os.environ", {"READTHEDOCS_VERSION": "latest"}):
                self.assertEqual(load_config(path).project.version, "latest")

    def test_rejects_missing_project_asset(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "dockle.toml"
            contents = MINIMAL_CONFIG.replace(
                'name = "Example"',
                'name = "Example"\nlogo = "missing.png"',
            )
            path.write_text(contents, encoding="utf-8")

            with self.assertRaisesRegex(ConfigError, "project.logo"):
                load_config(path)

            path.write_text(
                MINIMAL_CONFIG.replace(
                    'name = "Example"',
                    'name = "Example"\nfavicon = "missing.svg"',
                ),
                encoding="utf-8",
            )
            with self.assertRaisesRegex(ConfigError, "project.favicon"):
                load_config(path)

    def test_rejects_theme_values_that_could_escape_css(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "dockle.toml"
            path.write_text(
                MINIMAL_CONFIG.replace(
                    "[[targets]]",
                    '[theme]\nprimary = "red; display: none"\n\n[[targets]]',
                ),
                encoding="utf-8",
            )

            with self.assertRaisesRegex(ConfigError, "unsafe in CSS"):
                load_config(path)

    def test_rejects_output_outside_project(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "dockle.toml"
            path.write_text(
                MINIMAL_CONFIG.replace(
                    "[[targets]]",
                    '[build]\noutput = "../published"\n\n[[targets]]',
                ),
                encoding="utf-8",
            )

            with self.assertRaisesRegex(ConfigError, "build.output"):
                load_config(path)

    def test_rejects_duplicate_target_names(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "dockle.toml"
            path.write_text(
                MINIMAL_CONFIG
                + """
[[targets]]
name = "manual"
framework = "mkdocs"
source = "guide"
""",
                encoding="utf-8",
            )

            with self.assertRaisesRegex(ConfigError, "duplicate target name"):
                load_config(path)

    def test_rejects_overlapping_target_outputs(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "dockle.toml"
            path.write_text(
                MINIMAL_CONFIG.replace(
                    'name = "manual"', 'name = "manual"\noutput = "reference"'
                )
                + """
[[targets]]
name = "api"
framework = "doxygen"
source = "src"
output = "reference/api"
""",
                encoding="utf-8",
            )

            with self.assertRaisesRegex(ConfigError, "output overlaps"):
                load_config(path)

    def test_sphinx_home_target_owns_build_root(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "dockle.toml"
            path.write_text(
                MINIMAL_CONFIG.replace(
                    'source = "docs"', 'source = "docs"\nhome = true'
                )
                + """
[[targets]]
name = "api"
framework = "doxygen"
source = "src"
""",
                encoding="utf-8",
            )

            config = load_config(path)

            self.assertTrue(config.targets[0].home)
            self.assertEqual(config.targets[0].output, config.build.output)
            self.assertEqual(
                config.targets[1].output, config.build.output / "api"
            )

    def test_non_sphinx_home_target_owns_build_root(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "dockle.toml"
            path.write_text(
                MINIMAL_CONFIG.replace(
                    'framework = "sphinx"', 'framework = "mkdocs"'
                ).replace('source = "docs"', 'source = "docs"\nhome = true'),
                encoding="utf-8",
            )

            config = load_config(path)

            self.assertTrue(config.targets[0].home)
            self.assertEqual(config.targets[0].output, config.build.output)

    def test_loads_unpublished_target_and_rejects_unpublished_home(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "dockle.toml"
            path.write_text(
                MINIMAL_CONFIG.replace(
                    'source = "docs"', 'source = "docs"\npublish = false'
                ),
                encoding="utf-8",
            )
            self.assertFalse(load_config(path).targets[0].publish)

            path.write_text(
                MINIMAL_CONFIG.replace(
                    'source = "docs"',
                    'source = "docs"\nhome = true\npublish = false',
                ),
                encoding="utf-8",
            )
            with self.assertRaisesRegex(ConfigError, "home requires publish"):
                load_config(path)

    def test_rejects_multiple_home_targets(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "dockle.toml"
            path.write_text(
                MINIMAL_CONFIG.replace(
                    'source = "docs"', 'source = "docs"\nhome = true'
                )
                + """
[[targets]]
name = "second"
framework = "sphinx"
source = "other-docs"
home = true
""",
                encoding="utf-8",
            )

            with self.assertRaisesRegex(ConfigError, "only one home target"):
                load_config(path)

    def test_rejects_entry_outside_source(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "dockle.toml"
            path.write_text(
                MINIMAL_CONFIG.replace(
                    'source = "docs"', 'source = "docs"\nentry = "../README"'
                ),
                encoding="utf-8",
            )

            with self.assertRaisesRegex(
                ConfigError, "entry must be a relative path"
            ):
                load_config(path)

    def test_loads_typed_doxygen_settings(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for name in ("docs", "src", "images", "include"):
                (root / name).mkdir()
            for name in ("README.md", "docs/custom.css", "docs/custom.js"):
                path = root / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.touch()
            path = root / "dockle.toml"
            path.write_text(
                MINIMAL_CONFIG.replace(
                    'framework = "sphinx"', 'framework = "doxygen"'
                )
                + """
[targets.doxygen]
inputs = ["README.md", "src"]
image_paths = ["images"]
include_paths = ["include"]
predefined = ["EXAMPLE=1"]
extra_stylesheets = ["docs/custom.css"]
extra_javascript = ["docs/custom.js", "https://example.invalid/widget.js"]
extra_files = ["docs/custom.js"]
aliases = ['example{1}=<strong>\\1</strong>']
main_page = "README.md"
dot_graph_max_nodes = 75
optimize_output_java = true
separate_member_pages = true
generate_xml = true
warn_if_undoc_enum_val = false
warn_if_undocumented = false
warn_no_paramdoc = false
""",
                encoding="utf-8",
            )

            config = load_config(path)
            doxygen = config.targets[0].doxygen

            self.assertIsNotNone(doxygen)
            assert doxygen is not None
            self.assertEqual(
                doxygen.inputs,
                ((root / "README.md").resolve(), (root / "src").resolve()),
            )
            self.assertEqual(doxygen.predefined, ("EXAMPLE=1",))
            self.assertEqual(
                doxygen.extra_javascript,
                (
                    (root / "docs" / "custom.js").resolve(),
                    "https://example.invalid/widget.js",
                ),
            )
            self.assertEqual(doxygen.main_page, (root / "README.md").resolve())
            self.assertEqual(doxygen.dot_graph_max_nodes, 75)
            self.assertTrue(doxygen.optimize_output_java)
            self.assertTrue(doxygen.separate_member_pages)
            self.assertTrue(doxygen.generate_xml)
            self.assertFalse(doxygen.warn_if_undoc_enum_val)
            self.assertFalse(doxygen.warn_if_undocumented)
            self.assertFalse(doxygen.warn_no_paramdoc)

    def test_rejects_doxygen_settings_for_other_frameworks(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "dockle.toml"
            path.write_text(
                MINIMAL_CONFIG + "\n[targets.doxygen]\ninputs = [\"src\"]\n",
                encoding="utf-8",
            )

            with self.assertRaisesRegex(ConfigError, "requires framework"):
                load_config(path)

    def test_loads_typed_jsdoc_and_mkdocs_settings(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "docs").mkdir()
            (root / "src").mkdir()
            (root / "README.md").touch()
            (root / "project.js").touch()
            path = root / "dockle.toml"
            path.write_text(
                MINIMAL_CONFIG.replace(
                    'framework = "sphinx"', 'framework = "jsdoc"'
                )
                + '''
[targets.jsdoc]
inputs = ["src"]
readme = "README.md"
extra_files = ["project.js"]
extra_javascript = ["project.js"]
extra_stylesheets = ["https://example.invalid/project.css"]

[[targets]]
name = "website"
framework = "mkdocs"
source = "docs"

[targets.mkdocs]
extra_javascript = ["_static/project.js"]
extra_stylesheets = ["https://example.invalid/project.css"]
''',
                encoding="utf-8",
            )

            config = load_config(path)
            jsdoc = config.targets[0].jsdoc
            mkdocs = config.targets[1].mkdocs

            assert jsdoc is not None
            assert mkdocs is not None
            self.assertEqual(jsdoc.inputs, ((root / "src").resolve(),))
            self.assertEqual(jsdoc.readme, (root / "README.md").resolve())
            self.assertEqual(
                jsdoc.extra_files, ((root / "project.js").resolve(),)
            )
            self.assertEqual(
                jsdoc.extra_javascript,
                ((root / "project.js").resolve(),),
            )
            self.assertEqual(
                jsdoc.extra_stylesheets,
                ("https://example.invalid/project.css",),
            )
            self.assertEqual(
                mkdocs.extra_javascript, ("_static/project.js",)
            )
            self.assertEqual(
                mkdocs.extra_stylesheets,
                ("https://example.invalid/project.css",),
            )

    def test_loads_typed_sphinx_settings(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "docs" / "_static").mkdir(parents=True)
            (root / "docs" / "extra_conf.py").touch()
            path = root / "dockle.toml"
            path.write_text(
                MINIMAL_CONFIG
                + '''
[targets.sphinx]
exclude_patterns = ["drafts/**"]
static_paths = ["docs/_static"]
extra_javascript = ["project.js"]
extra_stylesheets = ["project.css"]
extra_config = "docs/extra_conf.py"
source_edit_link = "https://example.invalid/edit/{filename}"
''',
                encoding="utf-8",
            )

            config = load_config(path)
            sphinx = config.targets[0].sphinx

            assert sphinx is not None
            self.assertEqual(
                sphinx.static_paths, ((root / "docs" / "_static").resolve(),)
            )
            self.assertEqual(sphinx.extra_javascript, ("project.js",))
            self.assertEqual(sphinx.extra_stylesheets, ("project.css",))
            self.assertEqual(
                sphinx.extra_config,
                (root / "docs" / "extra_conf.py").resolve(),
            )
            self.assertEqual(
                sphinx.source_edit_link,
                "https://example.invalid/edit/{filename}",
            )

    def test_sphinx_source_edit_link_requires_filename_placeholder(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "dockle.toml"
            path.write_text(
                MINIMAL_CONFIG
                + """
[targets.sphinx]
source_edit_link = "https://example.invalid/edit"
""",
                encoding="utf-8",
            )

            with self.assertRaisesRegex(ConfigError, "must contain.*filename"):
                load_config(path)

    def test_loads_typed_rustdoc_assets(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "docs").mkdir()
            extra_file = root / "crowdin.js"
            extra_file.touch()
            stylesheet = root / "crowdin.css"
            stylesheet.touch()
            path = root / "dockle.toml"
            path.write_text(
                MINIMAL_CONFIG.replace(
                    'framework = "sphinx"', 'framework = "rustdoc"'
                )
                + '''
[targets.rustdoc]
extra_files = ["crowdin.js"]
extra_javascript = ["crowdin.js", "https://example.invalid/widget.js"]
extra_stylesheets = ["crowdin.css"]
''',
                encoding="utf-8",
            )

            config = load_config(path)
            rustdoc = config.targets[0].rustdoc

            assert rustdoc is not None
            self.assertEqual(rustdoc.extra_files, (extra_file.resolve(),))
            self.assertEqual(
                rustdoc.extra_javascript,
                (extra_file.resolve(), "https://example.invalid/widget.js"),
            )
            self.assertEqual(
                rustdoc.extra_stylesheets, (stylesheet.resolve(),)
            )

    def test_selects_targets_in_configuration_order(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "dockle.toml"
            path.write_text(
                MINIMAL_CONFIG
                + """
[[targets]]
name = "api"
framework = "doxygen"
source = "src"
""",
                encoding="utf-8",
            )
            config = load_config(path)

            selected = config.select_targets(["api", "manual"])

            self.assertEqual(
                [target.name for target in selected], ["manual", "api"]
            )

    def test_allows_project_root_as_source(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "dockle.toml"
            path.write_text(
                MINIMAL_CONFIG.replace(
                    'framework = "sphinx"', 'framework = "rustdoc"'
                ).replace('source = "docs"', 'source = "."'),
                encoding="utf-8",
            )

            config = load_config(path)

            self.assertEqual(config.targets[0].source, path.parent.resolve())


if __name__ == "__main__":
    unittest.main()
