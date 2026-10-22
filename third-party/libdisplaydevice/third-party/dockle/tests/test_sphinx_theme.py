from __future__ import annotations

import unittest

from dockle.sphinx_theme import THEME_DIRECTORY, setup


class FakeSphinxApp:
    def __init__(self) -> None:
        self.themes: list[tuple[str, object]] = []

    def add_html_theme(self, name: str, path: object) -> None:
        self.themes.append((name, path))


class SphinxThemeTests(unittest.TestCase):
    def test_setup_registers_first_party_theme(self) -> None:
        app = FakeSphinxApp()

        metadata = setup(app)

        self.assertEqual(app.themes, [("dockle", THEME_DIRECTORY)])
        self.assertTrue(metadata["parallel_write_safe"])

    def test_theme_contains_owned_template_and_assets(self) -> None:
        self.assertTrue((THEME_DIRECTORY / "theme.toml").is_file())
        self.assertTrue((THEME_DIRECTORY / "layout.html").is_file())
        self.assertTrue((THEME_DIRECTORY / "static" / "dockle.css").is_file())
        self.assertTrue((THEME_DIRECTORY / "static" / "dockle.js").is_file())
        self.assertTrue(
            (THEME_DIRECTORY / "static" / "lucide.min.js").is_file()
        )
        self.assertTrue(
            (THEME_DIRECTORY / "static" / "highlight.min.js").is_file()
        )
        self.assertTrue(
            (THEME_DIRECTORY / "static" / "HIGHLIGHT_LICENSE.txt").is_file()
        )
        self.assertTrue(
            (THEME_DIRECTORY / "static" / "LUCIDE_LICENSE.txt").is_file()
        )
        self.assertTrue((THEME_DIRECTORY / "main.html").is_file())
        self.assertTrue((THEME_DIRECTORY / "mkdocs_theme.yml").is_file())
        self.assertNotIn(
            "furo",
            (THEME_DIRECTORY / "theme.toml")
            .read_text(encoding="utf-8")
            .lower(),
        )
        sphinx_layout = (THEME_DIRECTORY / "layout.html").read_text(
            encoding="utf-8"
        )
        mkdocs_layout = (THEME_DIRECTORY / "main.html").read_text(
            encoding="utf-8"
        )
        for layout in (sphinx_layout, mkdocs_layout):
            self.assertLess(
                layout.index("lucide.min.js"), layout.index("dockle.js")
            )
            self.assertLess(
                layout.index("highlight.min.js"), layout.index("dockle.js")
            )

    def test_theme_supports_auto_light_and_dark_modes(self) -> None:
        script = (THEME_DIRECTORY / "static" / "dockle.js").read_text(
            encoding="utf-8"
        )

        self.assertIn('["auto", "light", "dark"]', script)
        self.assertIn('auto: "sun-moon"', script)
        self.assertIn("localStorage.removeItem(storageKey)", script)

    def test_admonitions_use_one_left_accent_layout(self) -> None:
        stylesheet = (
            THEME_DIRECTORY / "static" / "dockle.css"
        ).read_text(encoding="utf-8")

        self.assertIn("dl.dockle-alert", stylesheet)
        self.assertIn(
            "border-left: 0.25rem solid var(--dockle-alert-color)",
            stylesheet,
        )
        self.assertNotIn(
            "border-top: 0.25rem solid var(--dockle-alert-color)",
            stylesheet,
        )

    def test_compatibility_sidebars_share_current_page_styles(self) -> None:
        stylesheet = (
            THEME_DIRECTORY / "static" / "dockle.css"
        ).read_text(encoding="utf-8")
        script = (THEME_DIRECTORY / "static" / "dockle.js").read_text(
            encoding="utf-8"
        )

        self.assertIn('#nav-tree a[href="javascript:void(0)"]', stylesheet)
        self.assertIn("a.dockle-current", stylesheet)
        self.assertIn("markCurrentNavigation", script)
        self.assertIn('doxygen: "#nav-tree .label > a[href]"', script)
        self.assertIn('mkdocs: ".dockle-tree a[href]"', script)
        self.assertIn("normalizeDoxygenSidebar", script)
        self.assertNotIn('link.closest("li")?.remove()', script)
        self.assertIn("new MutationObserver(normalizeHierarchy)", script)
        self.assertIn(".dockle-current-item", stylesheet)
        self.assertIn("#nav-tree ul.children_ul", stylesheet)
        self.assertIn('body > nav li {', stylesheet)

    def test_anchor_navigation_uses_one_shared_feedback_effect(self) -> None:
        stylesheet = (
            THEME_DIRECTORY / "static" / "dockle.css"
        ).read_text(encoding="utf-8")
        script = (THEME_DIRECTORY / "static" / "dockle.js").read_text(
            encoding="utf-8"
        )

        self.assertIn("setupAnchorHighlights", script)
        self.assertIn('window.addEventListener("hashchange"', script)
        self.assertIn('target.classList.add("dockle-anchor-highlight")', script)
        self.assertIn("@keyframes dockle-anchor-highlight", stylesheet)
        self.assertIn(".dockle-anchor-highlight", stylesheet)
        self.assertIn("animation: dockle-anchor-highlight 650ms ease-out", stylesheet)
        self.assertIn("var(--dockle-primary) 4%", stylesheet)
        self.assertIn("var(--dockle-primary) 62%", stylesheet)
        self.assertNotIn(
            "background-color: color-mix(in srgb, var(--dockle-primary) 9%",
            stylesheet,
        )
        self.assertIn(':target.dockle-anchor-highlight {', stylesheet)
        self.assertIn('link.classList.add("dockle-toc-current")', script)
        self.assertIn('link.setAttribute("aria-current", "location")', script)
        self.assertNotIn('target.classList.remove("dockle-anchor-highlight");\n        if', script)
        self.assertIn('setTimeout(() => link.blur(), 700)', script)
        self.assertIn(".dockle-toc-current", stylesheet)

    def test_doxygen_sidebar_normalization_is_idempotent(self) -> None:
        script = (THEME_DIRECTORY / "static" / "dockle.js").read_text(
            encoding="utf-8"
        )

        self.assertIn("if (label.textContent !== pageTitle)", script)
        self.assertIn("new MutationObserver(normalizeHierarchy)", script)
        self.assertNotIn("removePageFragments", script)

    def test_tabs_support_keyboard_navigation_and_named_groups(self) -> None:
        stylesheet = (
            THEME_DIRECTORY / "static" / "dockle.css"
        ).read_text(encoding="utf-8")
        script = (THEME_DIRECTORY / "static" / "dockle.js").read_text(
            encoding="utf-8"
        )

        self.assertIn("data-dockle-tab-group", script)
        self.assertIn("dockle-tab-title", script)
        self.assertIn('["ArrowLeft", "ArrowRight", "Home", "End"]', script)
        self.assertIn("sessionStorage.getItem", script)
        self.assertIn("sessionStorage.setItem", script)
        self.assertIn("normalizeAliasTable", script)
        self.assertIn("dockle-alias-table", stylesheet)
        self.assertIn(".dockle-tab-list button:focus-visible", stylesheet)
        self.assertIn(".dockle-tab-panel[hidden]", stylesheet)
        self.assertIn("display: none !important", stylesheet)

    def test_sidebar_identity_stays_pinned_and_compacts_on_scroll(self) -> None:
        stylesheet = (
            THEME_DIRECTORY / "static" / "dockle.css"
        ).read_text(encoding="utf-8")
        script = (THEME_DIRECTORY / "static" / "dockle.js").read_text(
            encoding="utf-8"
        )

        self.assertIn(".dockle-sidebar::before", stylesheet)
        self.assertIn("--dockle-sidebar-header-height", stylesheet)
        self.assertIn("scrollbar-gutter: stable", stylesheet)
        self.assertIn("data-dockle-has-logo", stylesheet)
        self.assertIn("data-dockle-sidebar-compact", stylesheet)
        self.assertIn("const sidebarScroller", script)
        self.assertIn("--dockle-sidebar-logo-size: 4.5rem", stylesheet)
        self.assertIn(
            "padding: var(--dockle-sidebar-header-height)", stylesheet
        )
        self.assertIn("overflow-anchor: none", stylesheet)
        self.assertIn("sidebarScroller.scrollTop >= 72", script)

    def test_sidebar_brand_links_share_hover_and_type_spacing(self) -> None:
        stylesheet = (
            THEME_DIRECTORY / "static" / "dockle.css"
        ).read_text(encoding="utf-8")

        self.assertIn(".dockle-compat-brand:hover", stylesheet)
        self.assertIn(".dockle-brand a:hover", stylesheet)
        self.assertIn("line-height: 1.3", stylesheet)

    def test_content_columns_keep_a_stable_wide_screen_origin(self) -> None:
        stylesheet = (
            THEME_DIRECTORY / "static" / "dockle.css"
        ).read_text(encoding="utf-8")

        self.assertIn("--dockle-column-gap", stylesheet)
        self.assertIn("justify-content: start", stylesheet)
        self.assertIn(
            'body.rustdoc:not(.src) > main {',
            stylesheet,
        )
        self.assertIn(
            "var(--dockle-content-width) + var(--dockle-column-gap)",
            stylesheet,
        )

    def test_attribution_resets_framework_typography(self) -> None:
        stylesheet = (
            THEME_DIRECTORY / "static" / "dockle.css"
        ).read_text(encoding="utf-8")
        attribution = stylesheet.split(
            ".dockle-footer,\n.dockle-built-with {", 1
        )[1].split("}", 1)[0]

        self.assertIn("font-style: normal", attribution)

    def test_compatibility_adapters_receive_right_page_navigation(self) -> None:
        stylesheet = (
            THEME_DIRECTORY / "static" / "dockle.css"
        ).read_text(encoding="utf-8")
        script = (THEME_DIRECTORY / "static" / "dockle.js").read_text(
            encoding="utf-8"
        )

        self.assertIn("ensureCompatibilityPageToc", script)
        self.assertIn('["doxygen", "jsdoc", "rustdoc"]', script)
        self.assertIn('a[href] > .anchor[id]', script)
        self.assertIn(':scope > strong, :scope > b', script)
        self.assertIn("preserveDoxygenPageTocNavigation", script)
        self.assertIn("event.stopPropagation()", script)
        self.assertIn("dockle-compat-toc", script)
        self.assertIn(".dockle-compat-toc", stylesheet)
        self.assertIn("border-left: 0 !important", stylesheet)
        self.assertIn("contents.replaceChildren()", script)
        self.assertIn("#page-nav .dockle-toc-depth-1", stylesheet)

    def test_sphinx_pages_expose_repository_and_source_actions(self) -> None:
        layout = (THEME_DIRECTORY / "layout.html").read_text(encoding="utf-8")
        theme = (THEME_DIRECTORY / "theme.toml").read_text(encoding="utf-8")
        stylesheet = (
            THEME_DIRECTORY / "static" / "dockle.css"
        ).read_text(encoding="utf-8")

        self.assertIn('source_edit_link = ""', theme)
        self.assertIn("sourcename[-4:] == '.txt'", layout)
        self.assertIn(
            "theme_source_edit_link|replace('{filename}', source_filename)",
            layout,
        )
        self.assertIn("Edit this page", layout)
        self.assertIn('data-lucide="pencil"', layout)
        self.assertNotIn('data-lucide="square-pen"', layout)
        self.assertIn('class="dockle-page-actions"', layout)
        self.assertIn("data-dockle-repository-action", layout)
        self.assertIn('class="dockle-page-action dockle-repository-link"', layout)
        self.assertIn('data-dockle-repository-service="github"', layout)
        self.assertIn('data-dockle-repository-service="gitlab"', layout)
        self.assertIn('data-dockle-repository-service="generic"', layout)
        self.assertEqual(layout.count('target="_blank"'), 2)
        self.assertEqual(layout.count('rel="noopener noreferrer"'), 2)
        self.assertNotIn('aria-label="Source repository"', layout)
        self.assertNotIn('aria-label="Edit this page"', layout)
        self.assertLess(
            layout.index("dockle-source-edit"),
            layout.index("dockle-repository-link"),
        )
        self.assertLess(
            layout.index("dockle-repository-link"),
            layout.index("data-dockle-theme-toggle"),
        )
        self.assertIn('data-lucide="sun-moon"', layout)
        self.assertIn(".dockle-page-actions", stylesheet)
        self.assertIn(".dockle-page-action", stylesheet)
        self.assertIn(".dockle-theme-toggle .lucide", stylesheet)
        self.assertIn(".dockle-repository-icon", stylesheet)
        self.assertIn("color: var(--dockle-content) !important", stylesheet)
        self.assertIn(".headertitle\n  > .dockle-page-actions", stylesheet)
        doxygen_title = stylesheet.split(
            'html[data-dockle-framework="doxygen"] div.header .title {', 1
        )[1].split("}", 1)[0]
        self.assertIn("padding-right", doxygen_title)

    def test_sphinx_signatures_do_not_add_a_card_container(self) -> None:
        stylesheet = (
            THEME_DIRECTORY / "static" / "dockle.css"
        ).read_text(encoding="utf-8")
        signature = stylesheet.split(".sig-object {", 1)[1].split("}", 1)[0]

        self.assertIn("background: transparent", signature)
        self.assertIn("border: 0", signature)
        self.assertIn("padding: 0", signature)

    def test_code_blocks_receive_shared_copy_controls(self) -> None:
        stylesheet = (
            THEME_DIRECTORY / "static" / "dockle.css"
        ).read_text(encoding="utf-8")
        script = (THEME_DIRECTORY / "static" / "dockle.js").read_text(
            encoding="utf-8"
        )

        self.assertIn("addCodeCopyButtons", script)
        self.assertIn('button.className = "dockle-copy-button"', script)
        self.assertIn('data-lucide="copy"', script)
        self.assertIn(".dockle-copy-button", stylesheet)
        self.assertNotIn(
            ".dockle-code-block:hover > .dockle-copy-button",
            stylesheet,
        )
        self.assertIn("div.fragment .clipboard", stylesheet)
        self.assertIn(
            '#nav-tree a:hover {\n  background-image: none !important;',
            stylesheet,
        )
        self.assertIn("font-size: 1rem !important", stylesheet)
        self.assertIn("text-indent: 0 !important", stylesheet)

    def test_code_tokens_and_jsdoc_inline_code_share_theme_colors(self) -> None:
        stylesheet = (
            THEME_DIRECTORY / "static" / "dockle.css"
        ).read_text(encoding="utf-8")

        self.assertIn("--dockle-code-keyword", stylesheet)
        self.assertIn("--dockle-code-string", stylesheet)
        self.assertIn("span.keywordflow", stylesheet)
        self.assertIn("span.stringliteral", stylesheet)
        self.assertIn(".hljs-keyword", stylesheet)
        self.assertIn(".hljs-string", stylesheet)
        self.assertIn('html[data-dockle-framework="jsdoc"]', stylesheet)
        self.assertIn(":is(.params, .props)", stylesheet)
        self.assertIn(".name\n  code {", stylesheet)

    def test_every_authored_fence_uses_the_packaged_highlighter(self) -> None:
        script = (THEME_DIRECTORY / "static" / "dockle.js").read_text(
            encoding="utf-8"
        )
        stylesheet = (
            THEME_DIRECTORY / "static" / "dockle.css"
        ).read_text(encoding="utf-8")
        highlighter = (
            THEME_DIRECTORY / "static" / "highlight.min.js"
        ).read_text(encoding="utf-8")

        self.assertIn("applySyntaxHighlighting", script)
        self.assertIn("addLanguageGalleries", script)
        self.assertIn("addLanguageGalleryTocLinks", script)
        self.assertIn('querySelectorAll(".dockle-language-gallery")', script)
        self.assertIn("dockle-language-gallery-end", script)
        self.assertIn(".dockle-language-toc", stylesheet)
        self.assertIn("grid-template-columns: minmax(0, 1fr)", stylesheet)
        self.assertIn("item.dataset.dockleLanguage", script)
        self.assertIn("dataset.dockleLanguage", script)
        metadata_lookup = script.index("candidate.dataset.dockleLanguage")
        native_class_lookup = script.index("for (const candidate of ancestors)")
        self.assertLess(metadata_lookup, native_class_lookup)
        self.assertIn('["shell", "bash"]', script)
        self.assertIn('["shell-session", "console"]', script)
        self.assertIn('document.querySelectorAll("pre")', script)
        self.assertIn("code.textContent = source", script)
        self.assertIn("isBreakOnlyMarkup", script)
        self.assertNotIn("<br\\s*\\/?\\s*>", script)
        self.assertIn("normalizeDoxygenBlankCodeLines", script)
        self.assertIn("globalThis.hljs.highlightElement", script)
        self.assertTrue(
            highlighter.startswith(
                "/*! Highlight.js 11.12.0 | BSD-3-Clause |"
            )
        )

    def test_doxygen_generated_indexes_use_shared_surface_styles(self) -> None:
        stylesheet = (
            THEME_DIRECTORY / "static" / "dockle.css"
        ).read_text(encoding="utf-8")

        self.assertIn('table.directory tr.even', stylesheet)
        self.assertIn('table.directory tr:nth-child(even)', stylesheet)
        self.assertIn('table.directory td.entry', stylesheet)
        self.assertIn('html[data-dockle-framework="doxygen"] .levels', stylesheet)
        self.assertIn('html[data-dockle-framework="doxygen"] .icon', stylesheet)

    def test_rustdoc_uses_shared_lucide_toolbar_icons(self) -> None:
        stylesheet = (
            THEME_DIRECTORY / "static" / "dockle.css"
        ).read_text(encoding="utf-8")
        script = (THEME_DIRECTORY / "static" / "dockle.js").read_text(
            encoding="utf-8"
        )

        self.assertIn("replaceRustdocIcons", script)
        self.assertIn('["#copy-path", "copy"]', script)
        self.assertIn('[".settings-menu > a", "settings"]', script)
        self.assertIn('[".help-menu > a", "circle-help"]', script)
        self.assertIn(
            '["button#toggle-all-docs", "chevrons-down"]',
            script,
        )
        self.assertIn(".dockle-rustdoc-icon", stylesheet)
        self.assertIn("#copy-path::before", stylesheet)
        self.assertIn(
            '.dockle-code-block > pre > code {\n'
            "  background: transparent !important;\n"
            "  border-radius: 0 !important;",
            stylesheet,
        )
        self.assertIn(
            '.dockle-code-block\n  > .button-holder {\n'
            "  display: none !important;",
            stylesheet,
        )

    def test_footer_moves_into_each_framework_content_column(self) -> None:
        script = (THEME_DIRECTORY / "static" / "dockle.js").read_text(
            encoding="utf-8"
        )

        self.assertIn('doxygen: "#doc-content .contents"', script)
        self.assertIn('jsdoc: "#main"', script)
        self.assertIn('mkdocs: ".dockle-article"', script)
        self.assertIn('rustdoc: "#main-content"', script)
        self.assertIn('sphinx: ".dockle-article"', script)

    def test_headings_receive_shared_lucide_permalinks(self) -> None:
        stylesheet = (
            THEME_DIRECTORY / "static" / "dockle.css"
        ).read_text(encoding="utf-8")
        script = (THEME_DIRECTORY / "static" / "dockle.js").read_text(
            encoding="utf-8"
        )

        self.assertIn("addHeadingPermalinks", script)
        self.assertIn("globalThis.lucide", script)
        self.assertIn("lucide.createIcons", script)
        self.assertNotIn("const iconNodes", script)
        self.assertIn('link.className = "dockle-heading-anchor"', script)
        self.assertIn('data-lucide="pilcrow"', script)
        self.assertIn(".headerlink, :scope > .doc-anchor", script)
        self.assertIn(
            'pageNav.querySelectorAll(".dockle-heading-anchor")', script
        )
        self.assertIn(".dockle-heading-anchor", stylesheet)
        self.assertIn(
            ":where(h1, h2, h3, h4, h5, h6):hover", stylesheet
        )
        self.assertIn(".dockle-heading-anchor:focus-visible", stylesheet)


if __name__ == "__main__":
    unittest.main()
