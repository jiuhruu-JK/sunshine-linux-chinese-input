from __future__ import annotations

import json
import tempfile
import unittest
from importlib.metadata import PackageNotFoundError
from pathlib import Path
from unittest.mock import Mock, patch

from dockle import __version__
from dockle.config import (
    BuildConfig,
    DockleConfig,
    ProjectConfig,
    TargetConfig,
    ThemeConfig,
)
from dockle.theme import (
    ThemeError,
    _portal_path,
    _theme_asset,
    _update_home_portal,
    annotate_doxygen_code_languages,
    apply_theme,
    render_theme,
    write_home_aliases,
)


class ThemeTests(unittest.TestCase):
    def test_home_aliases_preserve_target_prefixed_deep_links(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "project"
            output = root / "_site"
            nested = output / "about"
            nested.mkdir(parents=True)
            (output / "index.html").write_text("home", encoding="utf-8")
            (nested / "support.html").write_text("support", encoding="utf-8")
            home = TargetConfig(
                name="docs",
                title="Docs",
                description="",
                framework="sphinx",
                source=root / "docs",
                output=output,
                home=True,
            )
            config = DockleConfig(
                path=root / "dockle.toml",
                root=root,
                project=ProjectConfig(name="Example"),
                theme=ThemeConfig(),
                build=BuildConfig(output=output, work=root / ".dockle"),
                targets=(home,),
            )

            aliases = write_home_aliases(config)

            self.assertEqual(aliases, 3)
            self.assertIn(
                'url=../index.html',
                (output / "docs" / "index.html").read_text(encoding="utf-8"),
            )
            self.assertIn(
                'url=../../about/support.html',
                (output / "docs" / "about" / "support.html").read_text(
                    encoding="utf-8"
                ),
            )
            self.assertIn(
                'url=../../../about/support.html',
                (
                    output
                    / "docs"
                    / "about"
                    / "support"
                    / "index.html"
                ).read_text(encoding="utf-8"),
            )

    def test_home_portal_update_uses_generated_index_file(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "project"
            output = root / "_site"
            output.mkdir(parents=True)
            portal = output / "index.html"
            portal.write_text("<h1>Example</h1><p>Docs</p>", encoding="utf-8")
            config = DockleConfig(
                path=root / "dockle.toml",
                root=root,
                project=ProjectConfig(name="Example"),
                theme=ThemeConfig(),
                build=BuildConfig(output=output, work=root / ".dockle"),
                targets=(),
            )

            updated = _update_home_portal(config, "<article>API</article>", True)

            self.assertEqual(updated, portal.resolve())
            self.assertIn(
                '<div data-dockle-target-cards class="dockle-portal-grid"',
                portal.read_text(encoding="utf-8"),
            )

    def test_portal_path_rejects_output_outside_project_root(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            config = DockleConfig(
                path=root / "dockle.toml",
                root=root / "project",
                project=ProjectConfig(name="Example"),
                theme=ThemeConfig(),
                build=BuildConfig(
                    output=root / "outside",
                    work=root / "project" / ".dockle",
                ),
                targets=(),
            )

            with self.assertRaisesRegex(
                ThemeError, "build output must stay within project root"
            ):
                _portal_path(config)

    def test_theme_asset_returns_source_path_without_packaged_asset(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            expected = (
                root
                / "checkout"
                / "sphinx"
                / "themes"
                / "dockle"
                / "static"
                / "missing.js"
            )
            with (
                patch("dockle.theme.__file__", root / "checkout" / "theme.py"),
                patch(
                    "dockle.theme.distribution",
                    side_effect=PackageNotFoundError,
                ),
            ):
                self.assertEqual(_theme_asset("missing.js"), expected)

            installed = Mock(files=[])
            with (
                patch("dockle.theme.__file__", root / "checkout" / "theme.py"),
                patch("dockle.theme.distribution", return_value=installed),
            ):
                self.assertEqual(_theme_asset("missing.js"), expected)

    def test_theme_asset_falls_back_to_installed_distribution(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            relative_asset = Path(
                "dockle",
                "sphinx",
                "themes",
                "dockle",
                "static",
                "lucide.min.js",
            )
            installed_asset = root / "site-packages" / relative_asset
            installed_asset.parent.mkdir(parents=True)
            installed_asset.write_text("installed", encoding="utf-8")
            installed = Mock(files=[relative_asset])
            installed.locate_file.return_value = installed_asset

            with (
                patch("dockle.theme.__file__", root / "checkout" / "theme.py"),
                patch("dockle.theme.distribution", return_value=installed),
            ):
                self.assertEqual(
                    _theme_asset("lucide.min.js"), installed_asset
                )

    def test_render_theme_includes_configured_tokens(self) -> None:
        stylesheet = render_theme(
            ThemeConfig(primary="#abcdef", dark_background="#010203")
        )

        self.assertIn("--dockle-primary: #abcdef", stylesheet)
        self.assertIn("--dockle-background: #010203", stylesheet)
        self.assertIn("body > nav", stylesheet)

    def test_apply_theme_uses_relative_asset_paths_for_nested_pages(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory)
            nested = output / "api" / "types"
            nested.mkdir(parents=True)
            html = nested / "index.html"
            html.write_text(
                "<html><head></head><body></body></html>", encoding="utf-8"
            )

            count = apply_theme(
                output, "rustdoc", "body { color: red; }", portal=output.parent
            )

            document = html.read_text(encoding="utf-8")
            self.assertEqual(count, 1)
            self.assertIn("../../_dockle/dockle.css", document)
            self.assertIn("../../_dockle/lucide.min.js", document)
            self.assertIn("../../_dockle/highlight.min.js", document)
            self.assertLess(
                document.index("lucide.min.js"),
                document.index("highlight.min.js"),
            )
            self.assertLess(
                document.index("highlight.min.js"),
                document.index("dockle.js"),
            )
            self.assertIn('data-dockle-framework="rustdoc"', document)
            self.assertNotIn("data-dockle-home", document)
            self.assertIn("data-dockle-universal-search", document)
            self.assertIn('class="dockle-toolbar"', document)
            self.assertIn("Generated by", document)
            self.assertIn(f"Dockle {__version__}", document)
            self.assertIn('data-lucide="sun-moon"', document)
            self.assertIn(
                'class="dockle-footer dockle-built-with"', document
            )
            self.assertLess(
                document.index("data-dockle-universal-search"),
                document.index("data-dockle-built-with"),
            )
            self.assertIn("../../_dockle/search.json", document)
            self.assertIn('action="../../dockle-search.html"', document)
            self.assertIn('type="submit"', document)
            self.assertIn('name="readthedocs-addons-api-version"', document)
            self.assertTrue((output / "_dockle" / "search.json").is_file())
            search_page = (output / "dockle-search.html").read_text(
                encoding="utf-8"
            )
            self.assertIn('data-dockle-search-page', search_page)
            self.assertIn('data-dockle-search="_dockle/search.json"', search_page)
            self.assertIn('action="dockle-search.html"', search_page)
            self.assertTrue(
                (output / "_dockle" / "lucide.min.js").is_file()
            )
            self.assertTrue(
                (output / "_dockle" / "highlight.min.js").is_file()
            )

    def test_search_index_uses_page_content_and_heading(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            content_roots = {
                "doxygen": '<div class="contents">{content}</div>',
                "jsdoc": '<div id="main">{content}</div>',
                "mkdocs": '<article class="dockle-article">{content}</article>',
                "rustdoc": '<section id="main-content">{content}</section>',
                "sphinx": '<article class="dockle-article">{content}</article>',
            }
            for framework, root in content_roots.items():
                with self.subTest(framework=framework):
                    output = Path(directory) / framework
                    output.mkdir()
                    content = (
                        '<h1>Component reference<a class="headerlink" href="#top">¶</a></h1>'
                        '<p>Reusable components provide a stable API for each framework.</p>'
                    )
                    (output / "guide.html").write_text(
                        '<html><head><title>Component reference &#8212; Example documentation</title>'
                        '</head><body><nav>Repeated navigation labels</nav>'
                        + root.format(content=content)
                        + '<footer>Generated by Example</footer></body></html>',
                        encoding="utf-8",
                    )

                    apply_theme(output, framework, "body {}")

                    search = json.loads(
                        (output / "_dockle" / "search.json").read_text(encoding="utf-8")
                    )
                    self.assertEqual(search["docs"], [{
                        "location": "guide.html",
                        "title": "Component reference",
                        "text": "Reusable components provide a stable API for each framework.",
                    }])

    def test_repository_action_is_added_for_every_framework(self) -> None:
        content = {
            "doxygen": (
                '<div id="doc-content"><div class="header">'
                '<div class="headertitle"><div class="title">Docs</div></div>'
                '</div><div class="contents"><h1>Docs</h1></div></div>'
            ),
            "jsdoc": '<div id="main"><h1>Docs</h1></div>',
            "mkdocs": '<article class="dockle-article"><h1>Docs</h1></article>',
            "rustdoc": '<section id="main-content"><h1>Docs</h1></section>',
            "sphinx": '<article class="dockle-article"><h1>Docs</h1></article>',
        }
        repositories = {
            "doxygen": ("https://github.com/example/project", "github"),
            "jsdoc": ("https://gitlab.com/example/project", "gitlab"),
            "mkdocs": ("https://codeberg.org/example/project", "generic"),
            "rustdoc": ("https://github.com/example/project", "github"),
            "sphinx": ("https://github.com/example/project", "github"),
        }

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for framework, body in content.items():
                with self.subTest(framework=framework):
                    output = root / framework
                    output.mkdir()
                    html = output / "index.html"
                    html.write_text(
                        f"<html><head></head><body>{body}</body></html>",
                        encoding="utf-8",
                    )
                    repository, service = repositories[framework]

                    apply_theme(
                        output,
                        framework,
                        "body {}",
                        repository=repository,
                    )
                    apply_theme(
                        output,
                        framework,
                        "body {}",
                        repository=repository,
                    )

                    document = html.read_text(encoding="utf-8")
                    self.assertEqual(
                        document.count("data-dockle-repository-action"), 1
                    )
                    self.assertIn(f'href="{repository}"', document)
                    self.assertIn('target="_blank"', document)
                    self.assertIn('rel="noopener noreferrer"', document)
                    self.assertIn(
                        f'data-dockle-repository-service="{service}"',
                        document,
                    )
                    self.assertLess(
                        document.index("data-dockle-repository-action"),
                        document.index("<h1>Docs</h1>"),
                    )
                    self.assertLess(
                        document.index("dockle-repository-link"),
                        document.index("data-dockle-theme-toggle"),
                    )
                    self.assertEqual(
                        document.count("data-dockle-theme-toggle"), 1
                    )
                    if framework == "doxygen":
                        self.assertLess(
                            document.index('class="headertitle"'),
                            document.index("data-dockle-repository-action"),
                        )
                        self.assertLess(
                            document.index("data-dockle-repository-action"),
                            document.index('class="title"'),
                        )

    def test_doxygen_fence_languages_are_restored_for_highlighting(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "source"
            output = root / "output"
            source.mkdir()
            output.mkdir()
            (source / "README.md").write_text(
                '```toml\nname = "dockle"\n```\n\n'
                "```shell\ndockle build\n```\n\n"
                "```1c\nname = \"numeric language\"\n```\n\n"
                "```clojure-repl\nuser=> (dockle)\n```\n",
                encoding="utf-8",
            )
            html = output / "index.html"
            html.write_text(
                '<div class="fragment"><div class="line">'
                'name = &quot;dockle&quot;</div></div><!-- fragment -->'
                '<div class="fragment"><div class="line">'
                "dockle build</div></div><!-- fragment -->"
                '<div class="fragment"><div class="line"> 1c</div>'
                '<div class="line">name = &quot;numeric language&quot;</div>'
                "</div><!-- fragment -->"
                '<div class="fragment"><div class="line"> -repl</div>'
                '<div class="line">user=&gt; (dockle)</div>'
                "</div><!-- fragment -->",
                encoding="utf-8",
            )

            count = annotate_doxygen_code_languages(output, source)

            document = html.read_text(encoding="utf-8")
            self.assertEqual(count, 4)
            self.assertIn('data-dockle-language="toml"', document)
            self.assertIn('data-dockle-language="shell"', document)
            self.assertIn('data-dockle-language="1c"', document)
            self.assertIn('data-dockle-language="clojure-repl"', document)
            self.assertNotIn('<div class="line"> 1c</div>', document)
            self.assertNotIn('<div class="line"> -repl</div>', document)

    def test_doxygen_alias_fence_languages_are_restored_for_highlighting(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "source"
            output = root / "output"
            source.mkdir()
            output.mkdir()
            (source / "README.md").write_text(
                "@tab{Stable|:|```bash\n"
                "    sunshine --version\n"
                "    ```}\n",
                encoding="utf-8",
            )
            html = output / "index.html"
            html.write_text(
                '<div class="fragment"><div class="line">'
                "sunshine --version</div></div><!-- fragment -->",
                encoding="utf-8",
            )

            count = annotate_doxygen_code_languages(output, source)

            self.assertEqual(count, 1)
            self.assertIn(
                'data-dockle-language="bash"',
                html.read_text(encoding="utf-8"),
            )

    def test_doxygen_blockquote_fences_keep_language_and_blank_lines(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "source"
            output = root / "output"
            source.mkdir()
            output.mkdir()
            (source / "README.md").write_text(
                "> ```bash\n> echo first\n>\n> echo second\n> ```\n",
                encoding="utf-8",
            )
            html = output / "index.html"
            html.write_text(
                '<div class="fragment"><div class="line">echo first</div>'
                '<div class="line">&lt;br&gt;&lt;br&gt;</div>'
                '<div class="line">echo second</div></div><!-- fragment -->',
                encoding="utf-8",
            )

            count = annotate_doxygen_code_languages(output, source)

            self.assertEqual(count, 1)
            self.assertIn(
                'data-dockle-language="bash"',
                html.read_text(encoding="utf-8"),
            )

    def test_apply_theme_is_idempotent(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory)
            html = output / "index.html"
            html.write_text(
                "<html><head></head><body></body></html>", encoding="utf-8"
            )

            first = apply_theme(output, "jsdoc", "body {}")
            second = apply_theme(output, "jsdoc", "body {}")

            self.assertEqual(first, 1)
            self.assertEqual(second, 0)

    def test_apply_theme_rejects_malformed_html(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory)
            (output / "index.html").write_text(
                "<html><body></body></html>", encoding="utf-8"
            )

            with self.assertRaisesRegex(ThemeError, "closing head"):
                apply_theme(output, "jsdoc", "body {}")

    def test_native_theme_gets_framework_marker_without_duplicate_stylesheet(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory)
            html = output / "index.html"
            html.write_text(
                '<html><head><link rel="stylesheet" href="dockle.css"></head><body></body></html>',
                encoding="utf-8",
            )

            count = apply_theme(
                output,
                "doxygen",
                "unused",
                portal=output.parent,
                project_name="Dockle",
                project_version="0.1.0",
            )

            document = html.read_text(encoding="utf-8")
            self.assertEqual(count, 1)
            self.assertIn('data-dockle-framework="doxygen"', document)
            self.assertIn("data-dockle-brand", document)
            self.assertEqual(document.count("dockle.css"), 1)

    def test_apply_theme_copies_and_exposes_project_logo(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            output = root / "site"
            output.mkdir()
            logo = root / "logo.png"
            logo.write_bytes(b"image")
            html = output / "index.html"
            html.write_text(
                "<html><head></head><body></body></html>",
                encoding="utf-8",
            )

            apply_theme(output, "jsdoc", "body {}", logo=logo)

            document = html.read_text(encoding="utf-8")
            self.assertTrue((output / "_dockle" / "logo.png").is_file())
            self.assertIn('data-dockle-logo-url="_dockle/logo.png"', document)
            self.assertIn(
                'data-dockle-logo-url="_dockle/logo.png"',
                (output / "dockle-search.html").read_text(encoding="utf-8"),
            )

    def test_apply_theme_exposes_remote_project_logo(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory)
            html = output / "index.html"
            html.write_text(
                "<html><head></head><body></body></html>", encoding="utf-8"
            )

            apply_theme(
                output,
                "jsdoc",
                "body {}",
                logo="https://example.com/logo.png",
            )

            document = html.read_text(encoding="utf-8")
            self.assertIn(
                'data-dockle-logo-url="https://example.com/logo.png"',
                document,
            )

    def test_apply_theme_exposes_remote_favicon(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory)
            html = output / "index.html"
            html.write_text(
                "<html><head></head><body></body></html>", encoding="utf-8"
            )

            apply_theme(
                output,
                "jsdoc",
                "body {}",
                favicon="https://example.com/favicon.svg",
            )

            self.assertIn(
                'href="https://example.com/favicon.svg"',
                html.read_text(encoding="utf-8"),
            )
            self.assertIn(
                'rel="icon" href="https://example.com/favicon.svg" '
                "data-dockle-favicon",
                (output / "dockle-search.html").read_text(encoding="utf-8"),
            )

    def test_apply_theme_replaces_favicon_for_every_framework(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            favicon = root / "favicon.svg"
            favicon.write_text("<svg/>", encoding="utf-8")
            for framework in ("doxygen", "jsdoc", "mkdocs", "rustdoc", "sphinx"):
                output = root / framework
                output.mkdir()
                html = output / "index.html"
                html.write_text(
                    '<html><head><link rel="stylesheet" href="keep.css">'
                    '<link href="native>icon.ico" rel="shortcut icon">'
                    '<link REL="apple-touch-icon" href="touch.png"></head>'
                    "<body></body></html>",
                    encoding="utf-8",
                )

                apply_theme(
                    output,
                    framework,
                    "body {}",
                    favicon=favicon,
                )

                document = html.read_text(encoding="utf-8")
                self.assertNotIn("native>icon.ico", document)
                self.assertNotIn("touch.png", document)
                self.assertIn('rel="stylesheet" href="keep.css"', document)
                self.assertIn(
                    'rel="icon" href="_dockle/favicon.svg" '
                    "data-dockle-favicon",
                    document,
                )
                self.assertIn(
                    'rel="icon" href="_dockle/favicon.svg" '
                    "data-dockle-favicon",
                    (output / "dockle-search.html").read_text(encoding="utf-8"),
                )
                self.assertTrue(
                    (output / "_dockle" / "favicon.svg").is_file()
                )

    def test_apply_theme_combines_jsdoc_and_dockle_attribution(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory)
            html = output / "index.html"
            html.write_text(
                """<html><head></head><body>
<footer>Documentation generated by
<a href="https://github.com/jsdoc/jsdoc">JSDoc 4.0.5</a></footer>
</body></html>""",
                encoding="utf-8",
            )

            apply_theme(output, "jsdoc", "body {}")

            document = html.read_text(encoding="utf-8")
            self.assertEqual(document.count("data-dockle-built-with"), 1)
            self.assertIn("Generated by", document)
            self.assertIn(f"Dockle {__version__}", document)
            self.assertIn("JSDoc 4.0.5", document)
            self.assertNotIn("Documentation generated by", document)

    def test_apply_theme_reads_doxygen_generator_version(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory)
            html = output / "index.html"
            html.write_text(
                '<html><head><meta name="generator" content="Doxygen 1.18.0" />'
                '</head><body><div id="nav-path" class="navpath">'
                '<li class="footer">Generated by Doxygen 1.18.0</li>'
                '</div></body></html>',
                encoding="utf-8",
            )

            apply_theme(output, "doxygen", "body {}")

            document = html.read_text(encoding="utf-8")
            self.assertIn("Doxygen 1.18.0", document)
            self.assertIn("https://www.doxygen.nl/", document)
            self.assertIn('id="nav-path"', document)
            self.assertNotIn('class="footer"', document)


if __name__ == "__main__":
    unittest.main()
