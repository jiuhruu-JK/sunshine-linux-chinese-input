"""Framework adapters and build orchestration."""

from __future__ import annotations

import json
import os
import shlex
import shutil
import subprocess
import sys
from abc import ABC, abstractmethod
from collections.abc import Mapping
from dataclasses import dataclass, field
from html import escape
from pathlib import Path

from dockle import __version__
from dockle.config import AssetReference, DockleConfig, TargetConfig
from dockle.theme import (
    ThemeError,
    _theme_asset,
    annotate_doxygen_code_languages,
    apply_theme,
    render_theme,
    write_home_aliases,
    write_portal,
)

_INDEX_DOCUMENT = "index.html"
_DOXYGEN_PREDEFINED = ("DOXYGEN",)


class BuildError(RuntimeError):
    """Raised when a documentation build cannot complete."""


@dataclass(frozen=True)
class Command:
    """A subprocess invocation without shell interpolation."""

    args: tuple[str, ...]
    cwd: Path
    env: Mapping[str, str] = field(default_factory=dict)

    def display(self) -> str:
        """Return a copyable representation for the current platform."""

        if os.name == "nt":
            return subprocess.list2cmdline(self.args)
        return shlex.join(self.args)


@dataclass(frozen=True)
class BuildPlan:
    """Everything needed to execute one target."""

    target: TargetConfig
    command: Command
    work: Path
    generated_files: Mapping[Path, str]


@dataclass(frozen=True)
class BuildResult:
    """The result of a completed target build."""

    target: TargetConfig
    themed_pages: int


class ProcessRunner:
    """Run adapter commands without invoking a shell."""

    def run(self, command: Command) -> None:
        environment = os.environ.copy()
        environment.update(command.env)
        try:
            completed = subprocess.run(
                command.args,
                cwd=command.cwd,
                env=environment,
                check=False,
            )
        except OSError as error:
            raise BuildError(
                f"could not start {command.args[0]!r}: {error}"
            ) from error
        if completed.returncode:
            raise BuildError(
                f"command failed with exit code {completed.returncode}: {command.display()}"
            )


class Builder(ABC):
    """Base class for a documentation framework adapter."""

    def __init__(
        self, config: DockleConfig, target: TargetConfig, executable: str
    ) -> None:
        self.config = config
        self.target = target
        self.executable = executable
        self.work = config.build.work / target.name

    @abstractmethod
    def plan(self) -> BuildPlan:
        """Create a non-mutating build plan."""

    def finalize(self, stylesheet: str) -> int:
        """Collect framework output and apply the compatibility theme."""

        if not self.target.publish:
            return 0
        return apply_theme(
            self.target.output,
            self.target.framework,
            stylesheet,
            portal=(None if self.target.home else self.config.build.output),
            project_name=self.config.project.name,
            project_version=self.config.project.version,
            target_title=self.target.title,
            repository=self.config.project.repository,
            logo=self.config.project.logo,
            favicon=self.config.project.favicon,
        )

    def _theme_file(self) -> Path:
        return self.work / "theme" / "dockle.css"

    def _inject_extra_assets(
        self,
        stylesheets: tuple[AssetReference, ...],
        javascript: tuple[AssetReference, ...],
        *,
        framework_marker: str | None = None,
    ) -> int:
        """Copy configured project assets and inject every asset by URL."""

        local_assets: dict[str, Path] = {}
        for asset in (*stylesheets, *javascript):
            if not isinstance(asset, Path):
                continue
            existing = local_assets.get(asset.name)
            if existing is not None and existing != asset:
                raise BuildError(
                    "extra assets must have unique filenames: "
                    f"{existing} and {asset}"
                )
            local_assets[asset.name] = asset
        for name, source in local_assets.items():
            shutil.copy2(source, self.target.output / name)

        matched = 0
        for html_file in sorted(self.target.output.rglob("*.html")):
            document = html_file.read_text(encoding="utf-8")
            if (
                framework_marker is not None
                and f'data-dockle-framework="{framework_marker}"'
                not in document
            ):
                continue
            matched += 1
            assets = [
                *(
                    '<link rel="stylesheet" href="'
                    f'{escape(self._asset_url(asset, html_file), quote=True)}" '
                    f'data-dockle-extra-stylesheet="{index}">'
                    for index, asset in enumerate(stylesheets)
                    if f'data-dockle-extra-stylesheet="{index}"'
                    not in document
                ),
                *(
                    '<script defer src="'
                    f'{escape(self._asset_url(asset, html_file), quote=True)}" '
                    f'data-dockle-extra-javascript="{index}"></script>'
                    for index, asset in enumerate(javascript)
                    if f'data-dockle-extra-javascript="{index}"'
                    not in document
                ),
            ]
            if not assets:
                continue
            if "</head>" not in document:
                raise ThemeError(f"generated HTML has no </head>: {html_file}")
            document = document.replace(
                "</head>", "\n".join(assets) + "\n</head>", 1
            )
            html_file.write_text(document, encoding="utf-8")
        return matched

    def _asset_url(self, asset: AssetReference, html_file: Path) -> str:
        if isinstance(asset, str):
            return asset
        return Path(
            os.path.relpath(self.target.output / asset.name, html_file.parent)
        ).as_posix()


class SphinxBuilder(Builder):
    """Build Sphinx with Dockle's packaged theme and no consumer ``conf.py``."""

    def _output(self) -> Path:
        """Keep the root site isolated until Sphinx finishes successfully."""

        if self.target.home:
            return self.work / "site"
        return self.target.output

    def plan(self) -> BuildPlan:
        config_file = self.work / "conf.py"
        doctrees = self.work / "doctrees"
        settings = self.target.sphinx
        if settings is None:
            raise BuildError("sphinx target is missing generated settings")
        theme_options = {
            "primary": self.config.theme.primary,
            "content": self.config.theme.content,
            "light_background": self.config.theme.light_background,
            "dark_background": self.config.theme.dark_background,
            "font": self.config.theme.font,
            "code_font": self.config.theme.code_font,
            "repository_url": self.config.project.repository,
            "target_title": self.target.title,
            "source_edit_link": settings.source_edit_link,
            "dockle_version": __version__,
            "dockle_url": "https://github.com/LizardByte/dockle",
        }
        lines = [
            "# Generated by Dockle. Changes will be overwritten.",
            "import sys",
            "from pathlib import Path",
            f"sys.path.insert(0, {str(self.target.source)!r})",
            f"dockle_project_root = Path({str(self.config.root)!r})",
            f"project = {self.config.project.name!r}",
            f"author = {self.config.project.author!r}",
            f"copyright = {self.config.project.copyright!r}",
            f"version = release = {self.config.project.version!r}",
            f"root_doc = {self.target.entry!r}",
            "extensions = [",
            "    'dockle.sphinx_theme',",
            "    'myst_parser',",
            "    'sphinx.ext.autodoc',",
            "]",
            "source_suffix = {'.rst': 'restructuredtext', '.md': 'markdown'}",
            "myst_enable_extensions = ['alert']",
            "html_theme = 'dockle'",
            f"html_theme_options = {theme_options!r}",
            f"exclude_patterns = {list(settings.exclude_patterns)!r}",
            f"html_static_path = {[str(path) for path in settings.static_paths]!r}",
            f"html_css_files = {list(settings.extra_stylesheets)!r}",
            f"html_js_files = {list(settings.extra_javascript)!r}",
            "",
        ]
        if isinstance(self.config.project.logo, Path):
            lines.insert(
                -2, f"html_logo = {str(self.config.project.logo)!r}"
            )
        if settings.extra_config is not None:
            lines.extend(
                [
                    f"_dockle_extra_config = Path({str(settings.extra_config)!r})",
                    "exec(compile(_dockle_extra_config.read_bytes(), "
                    "str(_dockle_extra_config), 'exec'), globals())",
                    "",
                ]
            )
        args = [
            *_generator_command(self.config, "sphinx", self.executable),
            "-b",
            "html",
            "-c",
            str(self.work),
            "-d",
            str(doctrees),
        ]
        if self.config.build.strict:
            args.extend(["-W", "--keep-going"])
        args.extend([str(self.target.source), str(self._output())])
        return BuildPlan(
            target=self.target,
            command=Command(tuple(args), self.config.root),
            work=self.work,
            generated_files={config_file: "\n".join(lines)},
        )

    def finalize(self, stylesheet: str) -> int:
        """Theme and publish an optional root Sphinx site."""

        if not self.target.home:
            return super().finalize(stylesheet)

        staging = self._output()
        themed_pages = apply_theme(
            staging,
            self.target.framework,
            stylesheet,
            portal=None,
            project_name=self.config.project.name,
            project_version=self.config.project.version,
            target_title=self.target.title,
            repository=self.config.project.repository,
            logo=self.config.project.logo,
            favicon=self.config.project.favicon,
        )
        shutil.copytree(staging, self.target.output, dirs_exist_ok=True)
        return themed_pages


class DoxygenBuilder(Builder):
    """Build API documentation from a generated Doxyfile."""

    def plan(self) -> BuildPlan:
        config_file = self.work / "Doxyfile"
        settings = self.target.doxygen
        if settings is None:
            raise BuildError("doxygen target is missing generated settings")
        warn_as_error = (
            "FAIL_ON_WARNINGS" if self.config.build.strict else "NO"
        )
        values = {
            "DOXYFILE_ENCODING": "UTF-8",
            "PROJECT_NAME": _doxygen_quote(self.config.project.name),
            "PROJECT_NUMBER": _doxygen_quote(self.config.project.version),
            "PROJECT_BRIEF": _doxygen_quote(self.config.project.description),
            "OUTPUT_DIRECTORY": _doxygen_quote(_posix(self.target.output)),
            "INPUT": _doxygen_paths(settings.inputs),
            "RECURSIVE": "YES",
            "EXTRACT_ALL": "NO",
            "GENERATE_HTML": _doxygen_yes_no(self.target.publish),
            "HTML_OUTPUT": ".",
            "HTML_COLORSTYLE": "LIGHT",
            "HTML_COPY_CLIPBOARD": "NO",
            "HTML_EXTRA_STYLESHEET": _doxygen_paths((self._theme_file(),)),
            "GENERATE_TREEVIEW": "YES",
            "FULL_SIDEBAR": "YES",
            "HTML_DYNAMIC_MENUS": "YES",
            "HTML_DYNAMIC_SECTIONS": "YES",
            "SEARCHENGINE": "YES",
            "CASE_SENSE_NAMES": "YES",
            "CREATE_SUBDIRS": "NO",
            "DISABLE_INDEX": "NO",
            "EXTENSION_MAPPING": (
                "python=Python javascript=JavaScript "
                "typescript=JavaScript json=JavaScript "
                "csharp=Csharp objective-c=Objective-C"
            ),
            "GENERATE_LATEX": "NO",
            "GENERATE_XML": _doxygen_yes_no(settings.generate_xml),
            "MACRO_EXPANSION": "YES",
            "MARKDOWN_ID_STYLE": "GITHUB",
            "MARKDOWN_SUPPORT": "YES",
            "PREDEFINED": _doxygen_strings(
                (*_DOXYGEN_PREDEFINED, *settings.predefined)
            ),
            "OPTIMIZE_OUTPUT_JAVA": _doxygen_yes_no(
                settings.optimize_output_java
            ),
            "SEPARATE_MEMBER_PAGES": _doxygen_yes_no(
                settings.separate_member_pages
            ),
            "SORT_BRIEF_DOCS": "YES",
            "STRIP_FROM_INC_PATH": _doxygen_quote(
                _posix(self.config.root)
            ),
            "STRIP_FROM_PATH": _doxygen_quote(_posix(self.config.root)),
            "TOC_INCLUDE_HEADINGS": "5",
            "WARNINGS": "YES",
            "WARN_AS_ERROR": warn_as_error,
            "WARN_IF_DOC_ERROR": "YES",
            "WARN_IF_INCOMPLETE_DOC": "YES",
            "WARN_IF_UNDOC_ENUM_VAL": _doxygen_yes_no(
                settings.warn_if_undoc_enum_val
            ),
            "WARN_IF_UNDOCUMENTED": _doxygen_yes_no(
                settings.warn_if_undocumented
            ),
            "WARN_NO_PARAMDOC": _doxygen_yes_no(settings.warn_no_paramdoc),
            "QUIET": "YES",
            "DOT_GRAPH_MAX_NODES": str(settings.dot_graph_max_nodes),
        }
        optional_paths = {
            "EXCLUDE": settings.excludes,
            "HTML_EXTRA_FILES": _doxygen_extra_files(
                settings.extra_files, self.config.project.logo
            ),
            "IMAGE_PATH": settings.image_paths,
            "INCLUDE_PATH": settings.include_paths,
        }
        for key, paths in optional_paths.items():
            if paths:
                values[key] = _doxygen_paths(paths)
        if settings.exclude_patterns:
            values["EXCLUDE_PATTERNS"] = _doxygen_strings(
                settings.exclude_patterns
            )
        entry = settings.main_page or self.target.source / self.target.entry
        if entry.is_file():
            values["USE_MDFILE_AS_MAINPAGE"] = _doxygen_quote(_posix(entry))
        dot = shutil.which("dot")
        executable_path = Path(self.executable)
        sibling_dots = (
            executable_path.with_name("dot"),
            executable_path.with_name("dot.exe"),
        )
        if dot:
            values["DOT_PATH"] = _doxygen_quote(_posix(Path(dot).parent))
            values["HAVE_DOT"] = "YES"
        else:
            sibling_dot = next(
                (candidate for candidate in sibling_dots if candidate.is_file()),
                None,
            )
            if sibling_dot is not None:
                values["DOT_PATH"] = _doxygen_quote(
                    _posix(sibling_dot.parent)
                )
                values["HAVE_DOT"] = "YES"
        if values.get("HAVE_DOT") == "YES":
            values["DOT_IMAGE_FORMAT"] = "svg"
            values["DOT_NUM_THREADS"] = "0"
            values["INTERACTIVE_SVG"] = "YES"
        else:
            values["HAVE_DOT"] = "NO"
        aliases = (
            'ALIASES                 = ""\n'
            'ALIASES                += "_dockle_alert{4|:|}=<dl class=\\"dockle-alert '
            'dockle-alert-\\2\\"><dt class=\\"dockle-alert-title\\"><i data-lucide=\\"\\3\\" '
            'aria-hidden=\\"true\\"></i> \\1</dt><dd>\\4</dd></dl>"\n'
            'ALIASES                += "admonition{2|:|}=@_dockle_alert{\\1|:|note|:|info|:|\\2}"\n'
            'ALIASES                += "attention{1}=@_dockle_alert{Attention|:|attention|:|circle-alert|:|\\1}"\n'
            'ALIASES                += "caution{1}=@_dockle_alert{Caution|:|caution|:|circle-alert|:|\\1}"\n'
            'ALIASES                += "danger{1}=@_dockle_alert{Danger|:|danger|:|octagon-alert|:|\\1}"\n'
            'ALIASES                += "error{1}=@_dockle_alert{Error|:|error|:|circle-x|:|\\1}"\n'
            'ALIASES                += "hint{1}=@_dockle_alert{Hint|:|hint|:|lightbulb|:|\\1}"\n'
            'ALIASES                += "important{1}=@_dockle_alert{Important|:|important|:|flame|:|\\1}"\n'
            'ALIASES                += "note{1}=@_dockle_alert{Note|:|note|:|info|:|\\1}"\n'
            'ALIASES                += "seealso{1}=@_dockle_alert{See also|:|seealso|:|eye|:|\\1}"\n'
            'ALIASES                += "tip{1}=@_dockle_alert{Tip|:|tip|:|lightbulb|:|\\1}"\n'
            'ALIASES                += "todo{1}=@_dockle_alert{TODO|:|todo|:|list-todo|:|\\1}"\n'
            'ALIASES                += "warning{1}=@_dockle_alert{Warning|:|warning|:|triangle-alert|:|\\1}"\n'
            'ALIASES                += "_dockle_tab{2|:|}=<li><strong class=\\"dockle-tab-title\\">'
            '\\1</strong>^^\\2^^</li>"\n'
            'ALIASES                += "tab{2|:|}=@_dockle_tab{\\1|:|\\2}"\n'
            'ALIASES                += "tabs{1}=<div class=\\"dockle-tabs dockle-tabs-alias\\">'
            '<ul>^^\\1^^</ul></div>"\n'
            'ALIASES                += "tabs_grouped{2|:|}=<div class=\\"dockle-tabs '
            'dockle-tabs-alias\\" data-dockle-tab-group=\\"\\1\\"><ul>^^\\2^^</ul></div>"\n'
            'ALIASES                += "examples=^^**Examples**^^@code{.cpp}"\n'
            'ALIASES                += "examples_end=@endcode^^"\n'
            'ALIASES                += "red{1}=<span style=\\"color:red\\">\\1</span>"\n'
            'ALIASES                += "blue{1}=<span style=\\"color:blue\\">\\1</span>"\n'
            'ALIASES                += "green{1}=<span style=\\"color:green\\">\\1</span>"\n'
            'ALIASES                += "yellow{1}=<span style=\\"color:yellow\\">\\1</span>"\n'
            'ALIASES                += "expander{2|:|}=@htmlonly<details><summary>^^\\1^^'
            '</summary><div>@endhtmlonly^^\\2^^@htmlonly</div></details>@endhtmlonly"\n'
        )
        custom_aliases = "".join(
            f"ALIASES                += {_doxygen_quote(alias)}\n"
            for alias in settings.aliases
        )
        contents = (
            "# Generated by Dockle. Changes will be overwritten.\n"
            + "".join(
                f"{key:<24} = {value}\n" for key, value in values.items()
            )
            + aliases
            + custom_aliases
        )
        return BuildPlan(
            target=self.target,
            command=Command(
                (self.executable, str(config_file)), self.config.root
            ),
            work=self.work,
            generated_files={
                config_file: contents,
                self._theme_file(): render_theme(self.config.theme),
            },
        )

    def finalize(self, stylesheet: str) -> int:
        """Restore fence metadata before applying the shared theme."""

        settings = self.target.doxygen
        if settings is not None:
            annotate_doxygen_code_languages(
                self.target.output, settings.inputs
            )
        themed_pages = super().finalize(stylesheet)
        if settings is not None:
            self._inject_extra_assets(
                settings.extra_stylesheets, settings.extra_javascript
            )
        return themed_pages


class MkDocsBuilder(Builder):
    """Build Markdown with a generated MkDocs configuration."""

    def plan(self) -> BuildPlan:
        config_file = self.work / "mkdocs.yml"
        settings = self.target.mkdocs
        if settings is None:
            raise BuildError("mkdocs target is missing generated settings")
        lines = [
            "# Generated by Dockle. Changes will be overwritten.",
            f"site_name: {_yaml_string(self.config.project.name)}",
            f"site_description: {_yaml_string(self.config.project.description)}",
            f"site_author: {_yaml_string(self.config.project.author)}",
            f"copyright: {_yaml_string(self.config.project.copyright)}",
            f"docs_dir: {_yaml_string(str(self.target.source))}",
            f"site_dir: {_yaml_string(str(self.target.output))}",
            'edit_uri: ""',
            "theme:",
            "  name: dockle",
            f"  primary: {_yaml_string(self.config.theme.primary)}",
            f"  content: {_yaml_string(self.config.theme.content)}",
            f"  light_background: {_yaml_string(self.config.theme.light_background)}",
            f"  dark_background: {_yaml_string(self.config.theme.dark_background)}",
            f"  font: {_yaml_string(self.config.theme.font)}",
            f"  code_font: {_yaml_string(self.config.theme.code_font)}",
            f"  version: {_yaml_string(self.config.project.version)}",
            f"  target_title: {_yaml_string(self.target.title)}",
            f"  dockle_version: {_yaml_string(__version__)}",
            '  dockle_url: "https://github.com/LizardByte/dockle"',
            "markdown_extensions:",
            "  - admonition",
            "  - codehilite:",
            "      guess_lang: false",
            "      lang_prefix: language-",
            "      use_pygments: false",
            "  - dockle.markdown",
        ]
        if self.config.project.repository:
            lines.append(
                f"repo_url: {_yaml_string(self.config.project.repository)}"
            )
        if settings.extra_stylesheets:
            lines.append("extra_css:")
            lines.extend(
                f"  - {_yaml_string(stylesheet)}"
                for stylesheet in settings.extra_stylesheets
            )
        if settings.extra_javascript:
            lines.append("extra_javascript:")
            lines.extend(
                f"  - {_yaml_string(javascript)}"
                for javascript in settings.extra_javascript
            )
        args = [
            *_generator_command(self.config, "mkdocs", self.executable),
            "build",
            "--config-file",
            str(config_file),
        ]
        if self.config.build.strict:
            args.append("--strict")
        return BuildPlan(
            target=self.target,
            command=Command(tuple(args), self.config.root),
            work=self.work,
            generated_files={config_file: "\n".join(lines) + "\n"},
        )


class JsDocBuilder(Builder):
    """Build JavaScript API documentation with Dockle's native template."""

    def plan(self) -> BuildPlan:
        config_file = self.work / "jsdoc.json"
        settings = self.target.jsdoc
        if settings is None:
            raise BuildError("jsdoc target is missing generated settings")
        portal = Path(
            os.path.relpath(
                self.config.build.output / _INDEX_DOCUMENT,
                self.target.output,
            )
        ).as_posix()
        native = {
            "source": {
                "include": [str(path) for path in settings.inputs],
                "includePattern": settings.include_pattern,
            },
            "opts": {
                "destination": str(self.target.output),
                "encoding": "utf8",
                "recurse": True,
                "template": str(_jsdoc_template()),
            },
            "templates": {
                "default": {
                    "includeDate": False,
                    "outputSourceFiles": True,
                },
                "dockle": {
                    "dockleVersion": __version__,
                    "favicon": (
                        str(self.config.project.favicon)
                        if self.config.project.favicon
                        else ""
                    ),
                    "logo": (
                        str(self.config.project.logo)
                        if self.config.project.logo
                        else ""
                    ),
                    "portalUrl": portal,
                    "projectName": self.config.project.name,
                    "projectUrl": portal,
                    "projectVersion": self.config.project.version,
                    "repositoryUrl": self.config.project.repository,
                    "stylesheet": str(self._theme_file()),
                    "targetTitle": self.target.title,
                    "extraJavascript": [
                        str(asset) for asset in settings.extra_javascript
                    ],
                    "extraStylesheets": [
                        str(asset) for asset in settings.extra_stylesheets
                    ],
                },
            },
        }
        if settings.exclude_pattern:
            native["source"]["excludePattern"] = settings.exclude_pattern
        entry = settings.readme or self.target.source / self.target.entry
        if entry.is_file():
            native["opts"]["readme"] = str(entry)
        tutorials = self.target.source / "tutorials"
        if tutorials.is_dir():
            native["opts"]["tutorials"] = str(tutorials)
        args = [self.executable, "--configure", str(config_file)]
        if self.config.build.strict:
            args.append("--pedantic")
        return BuildPlan(
            target=self.target,
            command=Command(tuple(args), self.config.root),
            work=self.work,
            generated_files={
                config_file: json.dumps(native, indent=2) + "\n",
                self._theme_file(): render_theme(self.config.theme),
            },
        )

    def finalize(self, stylesheet: str) -> int:
        """Validate the pages emitted by the native JSDoc template."""

        del stylesheet
        if not self.target.publish:
            return 0
        settings = self.target.jsdoc
        if settings is None:
            raise BuildError("jsdoc target is missing generated settings")
        for extra_file in settings.extra_files:
            shutil.copy2(extra_file, self.target.output / extra_file.name)
        for name in ("lucide.min.js", "highlight.min.js"):
            shutil.copyfile(_theme_asset(name), self.target.output / name)
        html_files = self._inject_extra_assets(
            settings.extra_stylesheets,
            settings.extra_javascript,
            framework_marker="jsdoc",
        )
        if not html_files:
            raise ThemeError(
                "jsdoc did not generate HTML with Dockle's native template in "
                f"{self.target.output}"
            )
        return html_files


class RustdocBuilder(Builder):
    """Build a Cargo package or workspace with rustdoc."""

    def plan(self) -> BuildPlan:
        manifest = self.target.source
        if manifest.is_dir():
            manifest /= "Cargo.toml"
        cargo_target = self.work / "cargo-target"
        args = [
            self.executable,
            "doc",
            "--manifest-path",
            str(manifest),
            "--target-dir",
            str(cargo_target),
            "--no-deps",
        ]
        env: dict[str, str] = {}
        if self.config.build.strict:
            existing_flags = os.environ.get("RUSTDOCFLAGS", "").strip()
            if existing_flags:
                env["RUSTDOCFLAGS"] = f"{existing_flags} -D warnings"
            else:
                args.extend(
                    ["--config", 'build.rustdocflags=["-D","warnings"]']
                )
        return BuildPlan(
            target=self.target,
            command=Command(tuple(args), manifest.parent, env),
            work=self.work,
            generated_files={},
        )

    def finalize(self, stylesheet: str) -> int:
        source = self.work / "cargo-target" / "doc"
        if not source.is_dir():
            raise BuildError(
                f"cargo did not generate rustdoc output in {source}"
            )
        shutil.copytree(source, self.target.output, dirs_exist_ok=True)
        settings = self.target.rustdoc
        if settings is not None and settings.extra_files:
            html_directories = {
                path.parent for path in self.target.output.rglob("*.html")
            }
            for directory in html_directories:
                for extra_file in settings.extra_files:
                    shutil.copy2(extra_file, directory / extra_file.name)
        self._write_index()
        themed_pages = super().finalize(stylesheet)
        if settings is not None:
            self._inject_extra_assets(
                settings.extra_stylesheets, settings.extra_javascript
            )
        return themed_pages

    def _write_index(self) -> None:
        """Create the root page that Cargo omits for package documentation."""

        crates = sorted(
            path
            for path in self.target.output.iterdir()
            if path.is_dir() and (path / _INDEX_DOCUMENT).is_file()
        )
        if not crates:
            raise BuildError(
                f"cargo did not generate a crate index in {self.target.output}"
            )

        requested_entry = self.target.entry.removesuffix("/index.html")
        requested_entry = requested_entry.removesuffix("/")
        selected_crate = next(
            (crate for crate in crates if crate.name == requested_entry),
            None,
        )
        if self.target.entry != _INDEX_DOCUMENT.removesuffix(".html"):
            if selected_crate is None:
                raise BuildError(
                    "rustdoc entry does not match a generated crate: "
                    f"{self.target.entry}"
                )
            destination = f"{selected_crate.name}/"
        elif len(crates) == 1:
            destination = f"{crates[0].name}/"
        else:
            destination = ""

        if destination:
            script_destination = json.dumps(destination)
            head_extra = (
                '<meta http-equiv="refresh" content="0; '
                f'url={escape(destination)}">\n'
                "  <script>window.location.replace("
                f"{script_destination});</script>"
            )
            crate_name = destination.rstrip("/")
            body = f'  <p>Continue to <a href="{escape(destination)}">{escape(crate_name)}</a>.</p>'
        else:
            head_extra = ""
            links = "\n".join(
                f'    <li><a href="{escape(crate.name)}/">{escape(crate.name)}</a></li>'
                for crate in crates
            )
            body = f"  <h1>{escape(self.target.title)}</h1>\n  <ul>\n{links}\n  </ul>"

        document = f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{escape(self.target.title)}</title>
  {head_extra}
</head>
<body>
  <main>
{body}
  </main>
</body>
</html>
"""
        (self.target.output / _INDEX_DOCUMENT).write_text(
            document, encoding="utf-8"
        )


_BUILDERS: dict[str, type[Builder]] = {
    "doxygen": DoxygenBuilder,
    "jsdoc": JsDocBuilder,
    "mkdocs": MkDocsBuilder,
    "rustdoc": RustdocBuilder,
    "sphinx": SphinxBuilder,
}


def _required_paths(target: TargetConfig) -> tuple[Path, ...]:
    """Return every configured project path required by a target."""

    paths = [target.source]
    if target.doxygen is not None:
        paths.extend(target.doxygen.inputs)
        paths.extend(target.doxygen.image_paths)
        paths.extend(target.doxygen.include_paths)
        paths.extend(_local_assets(target.doxygen.extra_stylesheets))
        paths.extend(_local_assets(target.doxygen.extra_javascript))
        paths.extend(target.doxygen.extra_files)
        if target.doxygen.main_page is not None:
            paths.append(target.doxygen.main_page)
    if target.jsdoc is not None:
        paths.extend(target.jsdoc.inputs)
        if target.jsdoc.readme is not None:
            paths.append(target.jsdoc.readme)
        paths.extend(target.jsdoc.extra_files)
        paths.extend(_local_assets(target.jsdoc.extra_stylesheets))
        paths.extend(_local_assets(target.jsdoc.extra_javascript))
    if target.sphinx is not None:
        paths.extend(target.sphinx.static_paths)
        if target.sphinx.extra_config is not None:
            paths.append(target.sphinx.extra_config)
    if target.rustdoc is not None:
        paths.extend(target.rustdoc.extra_files)
        paths.extend(_local_assets(target.rustdoc.extra_stylesheets))
        paths.extend(_local_assets(target.rustdoc.extra_javascript))
    return tuple(paths)


def _local_assets(assets: tuple[AssetReference, ...]) -> tuple[Path, ...]:
    return tuple(asset for asset in assets if isinstance(asset, Path))


class BuildManager:
    """Resolve tools and execute one or more framework adapters."""

    def __init__(
        self, config: DockleConfig, runner: ProcessRunner | None = None
    ) -> None:
        self.config = config
        self.runner = runner or ProcessRunner()

    def plan(
        self, target: TargetConfig, *, require_tool: bool = False
    ) -> BuildPlan:
        """Create a target plan, optionally requiring its executable."""

        executable = self._resolve_tool(
            target.framework, required=require_tool
        )
        builder = _BUILDERS[target.framework](self.config, target, executable)
        return builder.plan()

    def check(
        self, targets: tuple[TargetConfig, ...]
    ) -> list[tuple[TargetConfig, str | None]]:
        """Check source paths and tool availability without writing files."""

        checks: list[tuple[TargetConfig, str | None]] = []
        for target in targets:
            problem: str | None = None
            missing_path = next(
                (path for path in _required_paths(target) if not path.exists()),
                None,
            )
            if missing_path is not None:
                problem = f"source does not exist: {missing_path}"
            else:
                try:
                    self._resolve_tool(target.framework, required=True)
                except BuildError as error:
                    problem = str(error)
            checks.append((target, problem))
        return checks

    def build(
        self, targets: tuple[TargetConfig, ...]
    ) -> tuple[BuildResult, ...]:
        """Build selected targets in configuration order."""

        results: list[BuildResult] = []
        stylesheet = render_theme(self.config.theme)
        if self.config.build.clean and targets == self.config.targets:
            self._prepare_directory(self.config.build.output, clean=True)
        for target in targets:
            if not target.source.exists():
                raise BuildError(
                    f"source does not exist for target {target.name!r}: {target.source}"
                )
            executable = self._resolve_tool(target.framework, required=True)
            builder = _BUILDERS[target.framework](
                self.config, target, executable
            )
            plan = builder.plan()
            self._prepare_directory(plan.work, clean=True)
            if not target.home:
                self._prepare_directory(
                    target.output, clean=self.config.build.clean
                )
            for path, contents in plan.generated_files.items():
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(contents, encoding="utf-8")
            self.runner.run(plan.command)
            themed_pages = builder.finalize(stylesheet)
            results.append(
                BuildResult(target=target, themed_pages=themed_pages)
            )
        write_portal(self.config, targets, stylesheet)
        write_home_aliases(self.config)
        return tuple(results)

    def _resolve_tool(self, framework: str, *, required: bool) -> str:
        if _uses_bundled_generator(self.config, framework):
            return sys.executable
        configured = self.config.tool(framework)
        candidate = Path(configured)
        resolved: str | None
        if candidate.is_absolute() or "/" in configured or "\\" in configured:
            local = (
                candidate
                if candidate.is_absolute()
                else self.config.root / candidate
            )
            resolved = str(local.resolve()) if local.exists() else None
        else:
            interpreter_scripts = str(Path(sys.executable).resolve().parent)
            local_node_modules = str(
                self.config.root / "node_modules" / ".bin"
            )
            resolved = (
                shutil.which(configured, path=interpreter_scripts)
                or shutil.which(configured, path=local_node_modules)
                or shutil.which(configured)
            )
        if resolved:
            return resolved
        if required:
            raise BuildError(
                f"tool for {framework!r} was not found: {configured!r}; "
                f"install it or set tools.{framework} in {self.config.path.name}"
            )
        return configured

    def _prepare_directory(self, path: Path, *, clean: bool) -> None:
        root = self.config.root.resolve()
        resolved = path.resolve()
        if resolved == root or not resolved.is_relative_to(root):
            raise BuildError(
                f"refusing to prepare unsafe directory: {resolved}"
            )
        if clean and resolved.exists():
            shutil.rmtree(resolved)
        resolved.mkdir(parents=True, exist_ok=True)


def _doxygen_quote(value: str) -> str:
    escaped = value.replace('"', '\\"')
    return f'"{escaped}"'


def _doxygen_paths(paths: tuple[Path, ...]) -> str:
    return " ".join(_doxygen_quote(_posix(path)) for path in paths)


def _doxygen_extra_files(
    paths: tuple[Path, ...], logo: Path | str | None
) -> tuple[Path, ...]:
    if isinstance(logo, Path) and logo not in paths:
        return (*paths, logo)
    return paths


def _doxygen_strings(values: tuple[str, ...]) -> str:
    return " ".join(_doxygen_quote(value) for value in values)


def _doxygen_yes_no(value: bool) -> str:
    return "YES" if value else "NO"


def _posix(path: Path) -> str:
    return path.as_posix()


def _yaml_string(value: str) -> str:
    return json.dumps(value, ensure_ascii=False)


def _jsdoc_template() -> Path:
    """Return the first-party JSDoc template bundled with Dockle."""

    return Path(__file__).resolve().parent / "jsdoc_template"


def _uses_bundled_generator(config: DockleConfig, framework: str) -> bool:
    return (
        bool(getattr(sys, "frozen", False))
        and framework in {"mkdocs", "sphinx"}
        and framework not in config.tools
    )


def _generator_command(
    config: DockleConfig,
    framework: str,
    executable: str,
) -> list[str]:
    if _uses_bundled_generator(config, framework):
        return [sys.executable, f"_run-{framework}"]
    return [executable]
