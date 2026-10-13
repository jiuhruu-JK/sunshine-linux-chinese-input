from __future__ import annotations

import json
import sys
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path
from stat import S_IXUSR
from unittest.mock import patch

from dockle import __version__
from dockle.builders import BuildError, BuildManager, Command, RustdocBuilder
from dockle.config import load_config

ALL_TARGETS_CONFIG = """
[project]
name = "Example API"
version = "2.4.0"
description = "Example documentation"
repository = "https://example.invalid/project"
favicon = "favicon.svg"

[theme]
primary = "#7c4dff"

[build]
strict = true

[[targets]]
name = "sphinx"
framework = "sphinx"
source = "sphinx-docs"

[[targets]]
name = "doxygen"
framework = "doxygen"
source = "cpp"

[[targets]]
name = "mkdocs"
framework = "mkdocs"
source = "markdown"

[[targets]]
name = "jsdoc"
framework = "jsdoc"
source = "javascript"

[[targets]]
name = "rustdoc"
framework = "rustdoc"
source = "rust"
"""


class RecordingRunner:
    def __init__(self, html_output: Path) -> None:
        self.html_output = html_output
        self.commands: list[Command] = []

    def run(self, command: Command) -> None:
        self.commands.append(command)
        self.html_output.mkdir(parents=True, exist_ok=True)
        is_jsdoc = any("jsdoc.json" in argument for argument in command.args)
        root = ' data-dockle-framework="jsdoc"' if is_jsdoc else ""
        favicon = (
            '<link data-dockle-favicon><link data-dockle-theme="jsdoc">'
            if is_jsdoc
            else ""
        )
        (self.html_output / "index.html").write_text(
            f"<!doctype html><html{root}><head><title>Fixture</title>"
            f"{favicon}</head><body><main><h1>Docs</h1></main></body></html>",
            encoding="utf-8",
        )
        if is_jsdoc:
            (self.html_output / "dockle.css").write_text(
                "body {}", encoding="utf-8"
            )
            (self.html_output / "dockle-favicon.svg").write_text(
                "<svg/>", encoding="utf-8"
            )


class BuilderTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_directory = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_directory.name)
        for name in ("sphinx-docs", "cpp", "markdown", "javascript", "rust"):
            (self.root / name).mkdir()
        (self.root / "favicon.svg").write_text("<svg/>", encoding="utf-8")
        self.config_path = self.root / "dockle.toml"
        self.config_path.write_text(ALL_TARGETS_CONFIG, encoding="utf-8")
        self.config = load_config(self.config_path)
        self.manager = BuildManager(self.config)

    def tearDown(self) -> None:
        self.temp_directory.cleanup()

    def test_sphinx_plan_uses_dockle_theme_and_generated_config(self) -> None:
        plan = self.manager.plan(self.config.targets[0])
        conf = plan.generated_files[plan.work / "conf.py"]

        self.assertIn("html_theme = 'dockle'", conf)
        self.assertIn("'dockle.sphinx_theme'", conf)
        self.assertIn("'myst_parser'", conf)
        self.assertIn("myst_enable_extensions = ['alert']", conf)
        self.assertIn("'sphinx.ext.autodoc'", conf)
        self.assertIn("#7c4dff", conf)
        self.assertIn("-W", plan.command.args)
        self.assertNotIn("conf.py", plan.command.args)

    def test_sphinx_plan_uses_typed_static_assets(self) -> None:
        static = self.root / "sphinx-docs" / "_static"
        static.mkdir()
        extra_config = self.root / "sphinx-docs" / "extra_conf.py"
        extra_config.write_text(
            "extensions.append('example')\n", encoding="utf-8"
        )
        configured = ALL_TARGETS_CONFIG.replace(
            'framework = "sphinx"\nsource = "sphinx-docs"',
            '''framework = "sphinx"
source = "sphinx-docs"

[targets.sphinx]
exclude_patterns = ["drafts/**"]
static_paths = ["sphinx-docs/_static"]
extra_stylesheets = ["project.css"]
extra_javascript = ["project.js"]
extra_config = "sphinx-docs/extra_conf.py"
source_edit_link = "https://example.invalid/edit/{filename}"''',
        )
        self.config_path.write_text(configured, encoding="utf-8")
        config = load_config(self.config_path)

        plan = BuildManager(config).plan(config.targets[0])
        conf = plan.generated_files[plan.work / "conf.py"]

        self.assertIn("exclude_patterns = ['drafts/**']", conf)
        self.assertIn(repr(str(static.resolve())), conf)
        self.assertIn("html_css_files = ['project.css']", conf)
        self.assertIn("html_js_files = ['project.js']", conf)
        self.assertIn(
            "'source_edit_link': 'https://example.invalid/edit/{filename}'",
            conf,
        )
        self.assertIn(repr(str(extra_config.resolve())), conf)
        self.assertIn("exec(compile(_dockle_extra_config.read_bytes()", conf)

    def test_doxygen_plan_uses_supported_extra_stylesheet_hook(self) -> None:
        (self.config.targets[1].source / "index").write_text(
            "# API\n", encoding="utf-8"
        )
        plan = self.manager.plan(self.config.targets[1])
        doxyfile = plan.generated_files[plan.work / "Doxyfile"]

        self.assertIn("HTML_EXTRA_STYLESHEET", doxyfile)
        self.assertIn("GENERATE_TREEVIEW", doxyfile)
        self.assertIn("WARN_AS_ERROR", doxyfile)
        self.assertIn("USE_MDFILE_AS_MAINPAGE", doxyfile)
        self.assertIn(
            "EXTENSION_MAPPING        = python=Python "
            "javascript=JavaScript typescript=JavaScript "
            "json=JavaScript csharp=Csharp "
            "objective-c=Objective-C",
            doxyfile,
        )
        self.assertIn('ALIASES                += "danger{1}', doxyfile)
        self.assertIn('"_dockle_alert{4|:|}', doxyfile)
        self.assertIn('"admonition{2|:|}', doxyfile)
        self.assertIn("\\1|:|note|:|info|:|\\2", doxyfile)
        self.assertIn('data-lucide=\\"\\3\\"', doxyfile)
        self.assertIn('"tab{2|:|}', doxyfile)
        self.assertNotIn('"tab_with_pipe{2|:|}', doxyfile)
        self.assertIn('PREDEFINED               = "DOXYGEN"', doxyfile)
        self.assertNotIn('"_WIN32"', doxyfile)
        self.assertNotIn('"__linux__"', doxyfile)
        self.assertIn('"tabs{1}', doxyfile)
        self.assertIn('"tabs_grouped{2|:|}', doxyfile)
        self.assertIn('"expander{2|:|}', doxyfile)
        self.assertIn('data-dockle-tab-group=\\"\\1\\"', doxyfile)
        self.assertIn(
            "dockle-alert-\\2\\\"><dt",
            doxyfile,
        )
        self.assertNotIn("dockle-alert- \\2", doxyfile)
        self.assertIn("WARN_IF_UNDOC_ENUM_VAL   = YES", doxyfile)
        self.assertIn("WARN_IF_UNDOCUMENTED     = YES", doxyfile)
        self.assertIn("WARN_NO_PARAMDOC         = YES", doxyfile)

    def test_doxygen_plan_uses_typed_project_settings(self) -> None:
        custom_css = self.root / "cpp" / "custom.css"
        custom_js = self.root / "cpp" / "custom.js"
        main_page = self.root / "README.md"
        fake_doxygen = self.root / "bin" / "doxygen"
        fake_doxygen.parent.mkdir()
        fake_doxygen.touch()
        for path in (custom_css, custom_js, main_page):
            path.touch()
        configured = ALL_TARGETS_CONFIG.replace(
            "[build]\nstrict = true",
            '''[build]
strict = true

[tools]
doxygen = "bin/doxygen"''',
        ).replace(
            'framework = "doxygen"\nsource = "cpp"',
            '''framework = "doxygen"
source = "cpp"

[targets.doxygen]
inputs = ["README.md", "cpp"]
exclude_patterns = ["*/generated/*"]
predefined = ["EXAMPLE=1"]
extra_stylesheets = ["cpp/custom.css"]
extra_javascript = ["cpp/custom.js"]
extra_files = ["cpp/custom.js"]
aliases = ['example{1}=<strong>\\1</strong>']
main_page = "README.md"
dot_graph_max_nodes = 75
optimize_output_java = true
separate_member_pages = true
generate_xml = true''',
        )
        self.config_path.write_text(configured, encoding="utf-8")
        config = load_config(self.config_path)

        with patch("dockle.builders.shutil.which", return_value=None):
            plan = BuildManager(config).plan(config.targets[1])
        doxyfile = plan.generated_files[plan.work / "Doxyfile"]
        settings = config.targets[1].doxygen
        assert settings is not None

        self.assertIn(f'"{settings.main_page.as_posix()}"', doxyfile)
        self.assertNotIn(custom_css.as_posix(), doxyfile)
        self.assertIn(f'"{settings.extra_files[0].as_posix()}"', doxyfile)
        self.assertIn('"EXAMPLE=1"', doxyfile)
        self.assertIn('EXCLUDE_PATTERNS         = "*/generated/*"', doxyfile)
        self.assertRegex(doxyfile, r"(?m)^HAVE_DOT\s+= NO$")

        fake_doxygen.with_name("dot").touch()
        with patch("dockle.builders.shutil.which", return_value=None):
            plan = BuildManager(config).plan(config.targets[1])
        doxyfile = plan.generated_files[plan.work / "Doxyfile"]
        self.assertRegex(doxyfile, r"(?m)^HAVE_DOT\s+= YES$")
        self.assertIn("DOT_GRAPH_MAX_NODES      = 75", doxyfile)
        self.assertIn("OPTIMIZE_OUTPUT_JAVA     = YES", doxyfile)
        self.assertIn("SEPARATE_MEMBER_PAGES    = YES", doxyfile)
        self.assertIn("GENERATE_XML             = YES", doxyfile)
        self.assertIn("WARN_IF_UNDOC_ENUM_VAL   = YES", doxyfile)
        self.assertIn("WARN_IF_UNDOCUMENTED     = YES", doxyfile)
        self.assertIn("WARN_NO_PARAMDOC         = YES", doxyfile)
        self.assertIn('ALIASES                += "example{1}', doxyfile)

    def test_doxygen_build_injects_local_and_remote_extra_assets(self) -> None:
        custom_css = self.root / "custom.css"
        custom_js = self.root / "custom.js"
        fake_doxygen = self.root / "fake-doxygen"
        custom_css.write_text("body {}", encoding="utf-8")
        custom_js.write_text("void 0", encoding="utf-8")
        fake_doxygen.touch()
        configured = ALL_TARGETS_CONFIG.replace(
            "[build]\nstrict = true",
            '[build]\nstrict = true\n\n[tools]\ndoxygen = "./fake-doxygen"',
        ).replace(
            'framework = "doxygen"\nsource = "cpp"',
            '''framework = "doxygen"
source = "cpp"

[targets.doxygen]
extra_stylesheets = ["custom.css", "https://example.invalid/widget.css"]
extra_javascript = ["custom.js", "https://example.invalid/widget.js"]''',
        )
        self.config_path.write_text(configured, encoding="utf-8")
        config = load_config(self.config_path)
        target = config.targets[1]

        result = BuildManager(
            config, runner=RecordingRunner(target.output)
        ).build((target,))

        self.assertEqual(result[0].themed_pages, 1)
        html = (target.output / "index.html").read_text(encoding="utf-8")
        self.assertIn(
            '<link rel="stylesheet" href="custom.css" '
            'data-dockle-extra-stylesheet="0">',
            html,
        )
        self.assertIn('href="https://example.invalid/widget.css"', html)
        self.assertIn(
            '<script defer src="custom.js" '
            'data-dockle-extra-javascript="0"></script>',
            html,
        )
        self.assertIn('src="https://example.invalid/widget.js"', html)
        self.assertEqual(
            (target.output / "custom.js").read_text(encoding="utf-8"),
            "void 0",
        )

    def test_doxygen_plan_copies_local_project_logo(self) -> None:
        logo = self.root / "logo.svg"
        logo.write_text("<svg/>", encoding="utf-8")
        self.config_path.write_text(
            ALL_TARGETS_CONFIG.replace(
                'description = "Example documentation"',
                'description = "Example documentation"\nlogo = "logo.svg"',
            ),
            encoding="utf-8",
        )
        config = load_config(self.config_path)

        plan = BuildManager(config).plan(config.targets[1])
        doxyfile = plan.generated_files[plan.work / "Doxyfile"]

        self.assertIn(f'"{logo.resolve().as_posix()}"', doxyfile)

    def test_unpublished_doxygen_target_generates_xml_without_html(self) -> None:
        configured = ALL_TARGETS_CONFIG.replace(
            'framework = "doxygen"\nsource = "cpp"',
            '''framework = "doxygen"
source = "cpp"
publish = false

[targets.doxygen]
generate_xml = true''',
        )
        self.config_path.write_text(configured, encoding="utf-8")
        config = load_config(self.config_path)

        plan = BuildManager(config).plan(config.targets[1])
        doxyfile = plan.generated_files[plan.work / "Doxyfile"]

        self.assertIn("GENERATE_HTML            = NO", doxyfile)
        self.assertIn("GENERATE_XML             = YES", doxyfile)

    def test_mkdocs_plan_generates_only_dockle_owned_config(self) -> None:
        plan = self.manager.plan(self.config.targets[2])
        native = plan.generated_files[plan.work / "mkdocs.yml"]

        self.assertIn('site_name: "Example API"', native)
        self.assertIn('repo_url: "https://example.invalid/project"', native)
        self.assertIn('edit_uri: ""', native)
        self.assertIn("name: dockle", native)
        self.assertIn('primary: "#7c4dff"', native)
        self.assertIn("- dockle.markdown", native)
        self.assertIn("  - codehilite:", native)
        self.assertIn("      guess_lang: false", native)
        self.assertIn("      lang_prefix: language-", native)
        self.assertIn("      use_pygments: false", native)
        self.assertIn(f'dockle_version: "{__version__}"', native)
        self.assertIn("--strict", plan.command.args)

    def test_mkdocs_plan_uses_typed_extra_assets(self) -> None:
        configured = ALL_TARGETS_CONFIG.replace(
            'framework = "mkdocs"\nsource = "markdown"',
            '''framework = "mkdocs"
source = "markdown"

[targets.mkdocs]
extra_stylesheets = ["https://example.invalid/project.css"]
extra_javascript = ["_static/project.js"]''',
        )
        self.config_path.write_text(configured, encoding="utf-8")
        config = load_config(self.config_path)

        plan = BuildManager(config).plan(config.targets[2])
        native = plan.generated_files[plan.work / "mkdocs.yml"]

        self.assertIn("extra_css:", native)
        self.assertIn('"https://example.invalid/project.css"', native)
        self.assertIn("extra_javascript:", native)
        self.assertIn('"_static/project.js"', native)

    def test_frozen_build_uses_bundled_python_generators(self) -> None:
        with patch.object(sys, "frozen", True, create=True):
            sphinx = self.manager.plan(self.config.targets[0])
            mkdocs = self.manager.plan(self.config.targets[2])

        self.assertEqual(sphinx.command.args[:2], (sys.executable, "_run-sphinx"))
        self.assertEqual(mkdocs.command.args[:2], (sys.executable, "_run-mkdocs"))

    def test_jsdoc_plan_generates_json(self) -> None:
        (self.config.targets[3].source / "index").write_text(
            "# API\n", encoding="utf-8"
        )
        plan = self.manager.plan(self.config.targets[3])
        native = plan.generated_files[plan.work / "jsdoc.json"]

        self.assertIn('"destination"', native)
        self.assertIn('"recurse": true', native)
        self.assertIn('"readme"', native)
        self.assertIn('"template"', native)
        self.assertIn('"dockleVersion"', native)
        self.assertIn('"projectName": "Example API"', native)
        self.assertIn(
            '"repositoryUrl": "https://example.invalid/project"', native
        )
        self.assertIn('"targetTitle": "Jsdoc"', native)
        self.assertIn('"stylesheet"', native)
        self.assertIn(
            plan.work / "theme" / "dockle.css", plan.generated_files
        )
        self.assertEqual(plan.command.args[1], "--configure")
        self.assertIn("--pedantic", plan.command.args)

    def test_jsdoc_plan_uses_typed_inputs_and_readme(self) -> None:
        readme = self.root / "README.md"
        readme.write_text("# Project\n", encoding="utf-8")
        configured = ALL_TARGETS_CONFIG.replace(
            'framework = "jsdoc"\nsource = "javascript"',
            '''framework = "jsdoc"
source = "javascript"

[targets.jsdoc]
inputs = ["javascript"]
readme = "README.md"
include_pattern = ".+\\\\.js$"
exclude_pattern = "generated/"''',
        )
        self.config_path.write_text(configured, encoding="utf-8")
        config = load_config(self.config_path)

        plan = BuildManager(config).plan(config.targets[3])
        native = plan.generated_files[plan.work / "jsdoc.json"]
        parsed = json.loads(native)

        self.assertEqual(parsed["opts"]["readme"], str(readme.resolve()))
        self.assertEqual(parsed["source"]["includePattern"], r".+\.js$")
        self.assertEqual(
            parsed["source"]["excludePattern"], "generated/"
        )

    def test_jsdoc_plan_discovers_tutorials(self) -> None:
        source = self.config.targets[3].source
        (source / "tutorials").mkdir()
        plan = self.manager.plan(self.config.targets[3])
        native = plan.generated_files[plan.work / "jsdoc.json"]

        self.assertIn('"tutorials"', native)

    def test_rustdoc_plan_uses_cargo_without_dependencies(self) -> None:
        with patch.dict("os.environ", {}, clear=True):
            plan = self.manager.plan(self.config.targets[4])

        self.assertEqual(plan.command.args[1], "doc")
        self.assertIn("--no-deps", plan.command.args)
        self.assertEqual(plan.command.cwd, self.config.targets[4].source)
        self.assertIn("--config", plan.command.args)
        self.assertIn(
            'build.rustdocflags=["-D","warnings"]', plan.command.args
        )
        self.assertNotIn("RUSTDOCFLAGS", plan.command.env)

    def test_rustdoc_plan_extends_explicit_environment_flags(self) -> None:
        with patch.dict("os.environ", {"RUSTDOCFLAGS": "--cfg docsrs"}):
            plan = self.manager.plan(self.config.targets[4])

        self.assertEqual(
            plan.command.env["RUSTDOCFLAGS"], "--cfg docsrs -D warnings"
        )

    def test_rustdoc_entry_selects_primary_workspace_crate(self) -> None:
        target = replace(self.config.targets[4], entry="koko")
        builder = RustdocBuilder(self.config, target, "cargo")
        for crate in ("koko", "xtask"):
            crate_output = target.output / crate
            crate_output.mkdir(parents=True)
            (crate_output / "index.html").write_text(
                f"<h1>{crate}</h1>", encoding="utf-8"
            )

        builder._write_index()

        index = (target.output / "index.html").read_text(encoding="utf-8")
        self.assertIn("url=koko/", index)
        self.assertIn('window.location.replace("koko/")', index)
        self.assertNotIn("xtask", index)

    def test_rustdoc_entry_must_match_generated_crate(self) -> None:
        target = replace(self.config.targets[4], entry="missing")
        builder = RustdocBuilder(self.config, target, "cargo")
        crate_output = target.output / "koko"
        crate_output.mkdir(parents=True)
        (crate_output / "index.html").write_text(
            "<h1>Koko</h1>", encoding="utf-8"
        )

        with self.assertRaisesRegex(BuildError, "rustdoc entry"):
            builder._write_index()

    def test_rustdoc_finalize_injects_local_and_remote_extra_assets(
        self,
    ) -> None:
        custom_css = self.root / "custom.css"
        custom_js = self.root / "custom.js"
        custom_css.write_text("body {}", encoding="utf-8")
        custom_js.write_text("void 0", encoding="utf-8")
        configured = ALL_TARGETS_CONFIG.replace(
            'framework = "rustdoc"\nsource = "rust"',
            '''framework = "rustdoc"
source = "rust"
entry = "fixture"

[targets.rustdoc]
extra_stylesheets = ["custom.css", "https://example.invalid/widget.css"]
extra_javascript = ["custom.js", "https://example.invalid/widget.js"]''',
        )
        self.config_path.write_text(configured, encoding="utf-8")
        config = load_config(self.config_path)
        target = config.targets[4]
        builder = RustdocBuilder(config, target, "cargo")
        crate_output = builder.work / "cargo-target" / "doc" / "fixture"
        nested_output = crate_output / "module"
        nested_output.mkdir(parents=True)
        for path in (crate_output / "index.html", nested_output / "index.html"):
            path.write_text(
                "<!doctype html><html><head></head><body>Docs</body></html>",
                encoding="utf-8",
            )

        themed_pages = builder.finalize("body {}")

        self.assertEqual(themed_pages, 3)
        html = (target.output / "fixture" / "module" / "index.html").read_text(
            encoding="utf-8"
        )
        self.assertIn(
            '<link rel="stylesheet" href="../../custom.css" '
            'data-dockle-extra-stylesheet="0">',
            html,
        )
        self.assertIn('href="https://example.invalid/widget.css"', html)
        self.assertIn(
            '<script defer src="../../custom.js" '
            'data-dockle-extra-javascript="0"></script>',
            html,
        )
        self.assertIn('src="https://example.invalid/widget.js"', html)
        self.assertTrue((target.output / "custom.css").is_file())

    def test_build_writes_generated_config_and_themes_html(self) -> None:
        fake_tool = self.root / "fake-jsdoc"
        fake_tool.touch()
        (self.root / "project.css").write_text("body {}", encoding="utf-8")
        (self.root / "project.js").write_text("void 0", encoding="utf-8")
        configured = ALL_TARGETS_CONFIG.replace(
            'framework = "jsdoc"\nsource = "javascript"',
            '''framework = "jsdoc"
source = "javascript"

[targets.jsdoc]
extra_files = ["project.css", "project.js"]
extra_stylesheets = ["project.css"]
extra_javascript = ["project.js"]''',
        ).replace(
            "[build]\nstrict = true",
            '[build]\nstrict = true\n\n[tools]\njsdoc = "./fake-jsdoc"',
        )
        self.config_path.write_text(configured, encoding="utf-8")
        config = load_config(self.config_path)
        target = config.select_targets(["jsdoc"])[0]
        runner = RecordingRunner(target.output)

        result = BuildManager(config, runner=runner).build((target,))

        self.assertEqual(result[0].themed_pages, 1)
        generated = (config.build.work / "jsdoc" / "jsdoc.json").read_text(
            encoding="utf-8"
        )
        html = (target.output / "index.html").read_text(encoding="utf-8")
        self.assertIn('"destination"', generated)
        self.assertIn('data-dockle-theme="jsdoc"', html)
        self.assertIn('data-dockle-framework="jsdoc"', html)
        self.assertIn(
            '<link rel="stylesheet" href="project.css" '
            'data-dockle-extra-stylesheet="0">',
            html,
        )
        self.assertIn(
            '<script defer src="project.js" '
            'data-dockle-extra-javascript="0"></script>',
            html,
        )
        self.assertIn('"extraJavascript"', generated)
        self.assertIn('"extraStylesheets"', generated)
        self.assertEqual(
            (target.output / "project.js").read_text(encoding="utf-8"),
            "void 0",
        )
        self.assertTrue((target.output / "dockle.css").is_file())
        self.assertTrue((target.output / "dockle-favicon.svg").is_file())
        self.assertIn("data-dockle-favicon", html)
        portal = (config.build.output / "index.html").read_text(
            encoding="utf-8"
        )
        self.assertIn('data-dockle-framework="portal"', portal)
        self.assertIn('href="jsdoc/"', portal)
        self.assertIn("data-dockle-favicon", portal)

    def test_home_jsdoc_ignores_other_target_pages(self) -> None:
        fake_tool = self.root / "fake-jsdoc"
        fake_tool.touch()
        configured = '''
[project]
name = "Example API"

[build]
strict = true

[tools]
jsdoc = "./fake-jsdoc"

[[targets]]
name = "jsdoc"
framework = "jsdoc"
source = "javascript"
home = true

[[targets]]
name = "doxygen"
framework = "doxygen"
source = "cpp"
'''
        self.config_path.write_text(configured, encoding="utf-8")
        config = load_config(self.config_path)
        target = config.targets[0]
        target.output.mkdir(parents=True)
        unrelated = target.output / "doxygen" / "index.html"
        unrelated.parent.mkdir()
        unrelated.write_text("<html><body>Doxygen</body></html>", encoding="utf-8")
        runner = RecordingRunner(target.output)

        result = BuildManager(config, runner=runner).build((target,))

        self.assertGreater(result[0].themed_pages, 0)
        self.assertTrue(unrelated.is_file())

    def test_resolves_project_local_node_tool(self) -> None:
        executable = (
            self.root
            / "node_modules"
            / ".bin"
            / ("jsdoc.cmd" if sys.platform == "win32" else "jsdoc")
        )
        executable.parent.mkdir(parents=True)
        executable.touch()
        executable.chmod(executable.stat().st_mode | S_IXUSR)

        plan = self.manager.plan(self.config.targets[3], require_tool=True)

        self.assertTrue(Path(plan.command.args[0]).samefile(executable))

    def test_plan_rejects_targets_without_framework_settings(self) -> None:
        cases = (
            (self.config.targets[0], "sphinx"),
            (self.config.targets[1], "doxygen"),
            (self.config.targets[2], "mkdocs"),
            (self.config.targets[3], "jsdoc"),
        )
        for target, framework in cases:
            with self.subTest(framework=framework):
                malformed = replace(target, **{framework: None})
                with self.assertRaisesRegex(
                    BuildError,
                    rf"{framework} target is missing generated settings",
                ):
                    self.manager.plan(malformed)

    def test_check_validates_every_typed_project_path(self) -> None:
        self.config_path.write_text(
            """
[project]
name = "Path checks"

[[targets]]
name = "doxygen"
framework = "doxygen"
source = "cpp"

[targets.doxygen]
inputs = ["cpp"]
image_paths = ["missing-images"]
include_paths = ["cpp"]
extra_stylesheets = ["favicon.svg"]
extra_files = ["favicon.svg"]
main_page = "missing-main.md"

[[targets]]
name = "jsdoc"
framework = "jsdoc"
source = "javascript"

[targets.jsdoc]
inputs = ["javascript"]
readme = "missing-readme.md"

[[targets]]
name = "sphinx"
framework = "sphinx"
source = "sphinx-docs"

[targets.sphinx]
static_paths = ["sphinx-docs"]
extra_config = "missing-conf.py"

[[targets]]
name = "rustdoc"
framework = "rustdoc"
source = "rust"

[targets.rustdoc]
extra_files = ["missing-rustdoc.css"]
""",
            encoding="utf-8",
        )
        config = load_config(self.config_path)

        checks = BuildManager(config).check(config.targets)

        expected = (
            config.root / "missing-images",
            config.root / "missing-readme.md",
            config.root / "missing-conf.py",
            config.root / "missing-rustdoc.css",
        )
        self.assertEqual(
            [problem for _, problem in checks],
            [f"source does not exist: {path}" for path in expected],
        )

    def test_full_build_removes_stale_target_output(self) -> None:
        fake_tool = self.root / "fake-sphinx"
        fake_tool.touch()
        configured = ALL_TARGETS_CONFIG.replace(
            "[build]\nstrict = true",
            '[build]\nstrict = true\n\n[tools]\nsphinx = "./fake-sphinx"',
        )
        self.config_path.write_text(configured, encoding="utf-8")
        config = load_config(self.config_path)
        stale = config.build.output / "removed-target" / "index.html"
        stale.parent.mkdir(parents=True)
        stale.write_text("stale", encoding="utf-8")
        target = config.targets[0]

        BuildManager(config, runner=RecordingRunner(target.output)).build(
            config.targets[:1]
        )
        self.assertTrue(
            stale.is_file(),
            "a selected build must preserve other target outputs",
        )

        # A complete build owns the whole output tree. Use a runner that writes
        # minimal HTML wherever each adapter expects native output.
        class MultiTargetRunner:
            def run(inner_self, command: Command) -> None:
                for candidate in config.targets:
                    native_output = candidate.output
                    if candidate.framework == "rustdoc":
                        native_output = (
                            config.build.work
                            / candidate.name
                            / "cargo-target"
                            / "doc"
                            / "fixture"
                        )
                    native_output.mkdir(parents=True, exist_ok=True)
                    root = (
                        ' data-dockle-framework="jsdoc"'
                        if candidate.framework == "jsdoc"
                        else ""
                    )
                    (native_output / "index.html").write_text(
                        f"<!doctype html><html{root}><head></head>"
                        "<body>Docs</body></html>",
                        encoding="utf-8",
                    )

        # Point every native executable at the same harmless file; the custom
        # runner records no process invocation.
        frameworks = sorted({target.framework for target in config.targets})
        tools = "\n".join(
            f'{framework} = "./fake-sphinx"' for framework in frameworks
        )
        self.config_path.write_text(
            configured.replace('sphinx = "./fake-sphinx"', tools),
            encoding="utf-8",
        )
        config = load_config(self.config_path)
        BuildManager(config, runner=MultiTargetRunner()).build(config.targets)

        self.assertFalse(stale.exists())


if __name__ == "__main__":
    unittest.main()
