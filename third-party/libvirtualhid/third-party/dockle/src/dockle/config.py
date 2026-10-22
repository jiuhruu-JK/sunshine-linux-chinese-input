"""Load and validate Dockle's public TOML configuration."""

from __future__ import annotations

import os
import re
import tomllib
from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path
from types import MappingProxyType
from typing import Any

SUPPORTED_FRAMEWORKS = frozenset(
    {"doxygen", "jsdoc", "mkdocs", "rustdoc", "sphinx"}
)
AssetReference = Path | str
_TARGET_NAME = re.compile(r"^[a-z0-9][a-z0-9_-]*$")
_TARGET_KEYS = {
    "doxygen",
    "jsdoc",
    "mkdocs",
    "sphinx",
    "rustdoc",
    "name",
    "title",
    "description",
    "framework",
    "source",
    "output",
    "publish",
    "entry",
    "home",
}


class ConfigError(ValueError):
    """Raised when ``dockle.toml`` is invalid."""


@dataclass(frozen=True)
class ProjectConfig:
    """Framework-neutral project metadata."""

    name: str
    version: str = ""
    description: str = ""
    repository: str = ""
    author: str = ""
    copyright: str = ""
    home: Path | None = None
    logo: Path | str | None = None
    favicon: Path | str | None = None


@dataclass(frozen=True)
class ThemeConfig:
    """The stable, framework-neutral Dockle design tokens."""

    primary: str = "#2962ff"
    content: str = "#2e3440"
    light_background: str = "#ffffff"
    dark_background: str = "#131416"
    font: str = "ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif"
    code_font: str = "ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, 'Liberation Mono', monospace"


@dataclass(frozen=True)
class BuildConfig:
    """Global build behavior."""

    output: Path
    work: Path
    strict: bool = False
    clean: bool = True


@dataclass(frozen=True)
class DoxygenConfig:
    """Project-specific Doxygen settings owned by ``dockle.toml``."""

    inputs: tuple[Path, ...]
    excludes: tuple[Path, ...] = ()
    exclude_patterns: tuple[str, ...] = ()
    image_paths: tuple[Path, ...] = ()
    include_paths: tuple[Path, ...] = ()
    predefined: tuple[str, ...] = ()
    extra_javascript: tuple[AssetReference, ...] = ()
    extra_stylesheets: tuple[AssetReference, ...] = ()
    extra_files: tuple[Path, ...] = ()
    aliases: tuple[str, ...] = ()
    main_page: Path | None = None
    dot_graph_max_nodes: int = 50
    optimize_output_java: bool = False
    separate_member_pages: bool = False
    generate_xml: bool = False
    warn_if_undoc_enum_val: bool = True
    warn_if_undocumented: bool = True
    warn_no_paramdoc: bool = True


@dataclass(frozen=True)
class JsDocConfig:
    """Project-specific JSDoc settings owned by ``dockle.toml``."""

    inputs: tuple[Path, ...]
    readme: Path | None = None
    include_pattern: str = r".+\.(c|m)?jsx?$"
    exclude_pattern: str = ""
    extra_files: tuple[Path, ...] = ()
    extra_javascript: tuple[AssetReference, ...] = ()
    extra_stylesheets: tuple[AssetReference, ...] = ()


@dataclass(frozen=True)
class MkDocsConfig:
    """Project-specific MkDocs assets owned by ``dockle.toml``."""

    extra_javascript: tuple[str, ...] = ()
    extra_stylesheets: tuple[str, ...] = ()


@dataclass(frozen=True)
class SphinxConfig:
    """Project-specific Sphinx settings owned by ``dockle.toml``."""

    exclude_patterns: tuple[str, ...] = ()
    static_paths: tuple[Path, ...] = ()
    extra_javascript: tuple[str, ...] = ()
    extra_stylesheets: tuple[str, ...] = ()
    extra_config: Path | None = None
    source_edit_link: str = ""


@dataclass(frozen=True)
class RustdocConfig:
    """Project-specific rustdoc settings owned by ``dockle.toml``."""

    extra_files: tuple[Path, ...] = ()
    extra_javascript: tuple[AssetReference, ...] = ()
    extra_stylesheets: tuple[AssetReference, ...] = ()


@dataclass(frozen=True)
class TargetConfig:
    """One documentation target."""

    name: str
    title: str
    description: str
    framework: str
    source: Path
    output: Path
    doxygen: DoxygenConfig | None = None
    jsdoc: JsDocConfig | None = None
    mkdocs: MkDocsConfig | None = None
    sphinx: SphinxConfig | None = None
    rustdoc: RustdocConfig | None = None
    entry: str = "index"
    home: bool = False
    publish: bool = True


@dataclass(frozen=True)
class DockleConfig:
    """Fully resolved Dockle configuration."""

    path: Path
    root: Path
    project: ProjectConfig
    theme: ThemeConfig
    build: BuildConfig
    targets: tuple[TargetConfig, ...]
    tools: Mapping[str, str] = field(
        default_factory=lambda: MappingProxyType({})
    )

    def tool(self, framework: str) -> str:
        """Return the configured executable for a framework."""

        defaults = {
            "doxygen": "doxygen",
            "jsdoc": "jsdoc",
            "mkdocs": "mkdocs",
            "rustdoc": "cargo",
            "sphinx": "sphinx-build",
        }
        return self.tools.get(framework, defaults[framework])

    def select_targets(
        self, names: tuple[str, ...] | list[str]
    ) -> tuple[TargetConfig, ...]:
        """Select named targets while preserving configuration order."""

        if not names:
            return self.targets
        requested = set(names)
        known = {target.name for target in self.targets}
        missing = sorted(requested - known)
        if missing:
            raise ConfigError(f"unknown target(s): {', '.join(missing)}")
        return tuple(
            target for target in self.targets if target.name in requested
        )


def load_config(path: str | Path = "dockle.toml") -> DockleConfig:
    """Load, strictly validate, and resolve a Dockle configuration file."""

    config_path = Path(path).resolve()
    try:
        with config_path.open("rb") as stream:
            raw = tomllib.load(stream)
    except FileNotFoundError as error:
        raise ConfigError(
            f"configuration file not found: {config_path}"
        ) from error
    except tomllib.TOMLDecodeError as error:
        raise ConfigError(f"invalid TOML in {config_path}: {error}") from error

    _reject_unknown(
        raw, {"project", "theme", "build", "targets", "tools"}, "root"
    )
    root = config_path.parent
    project = _load_project(_required_table(raw, "project", "root"), root)
    theme = _load_theme(_optional_table(raw, "theme", "root"))
    build = _load_build(_optional_table(raw, "build", "root"), root)
    targets = _load_targets(raw.get("targets"), root, build)
    tools = _load_tools(_optional_table(raw, "tools", "root"))

    return DockleConfig(
        path=config_path,
        root=root,
        project=project,
        theme=theme,
        build=build,
        targets=targets,
        tools=MappingProxyType(tools),
    )


def _load_project(raw: dict[str, Any], root: Path) -> ProjectConfig:
    allowed = {
        "name",
        "version",
        "description",
        "repository",
        "author",
        "copyright",
        "home",
        "logo",
        "favicon",
    }
    _reject_unknown(raw, allowed, "project")
    logo = _optional_project_asset(raw, "logo", root)
    favicon = _optional_project_asset(raw, "favicon", root) or logo
    return ProjectConfig(
        name=_required_string(raw, "name", "project"),
        version=_readthedocs_version(
            _optional_string(raw, "version", "project")
        ),
        description=_optional_string(raw, "description", "project"),
        repository=_optional_string(raw, "repository", "project"),
        author=_optional_string(raw, "author", "project"),
        copyright=_optional_string(raw, "copyright", "project"),
        home=_optional_project_path(raw, "home", root),
        logo=logo,
        favicon=favicon,
    )


def _optional_project_path(
    raw: dict[str, Any],
    key: str,
    root: Path,
) -> Path | None:
    value = _optional_string(raw, key, "project")
    if not value:
        return None
    resolved = _path_within_root(root, value, f"project.{key}")
    if not resolved.is_file():
        raise ConfigError(f"project.{key} does not exist: {resolved}")
    return resolved


def _optional_project_asset(
    raw: dict[str, Any],
    key: str,
    root: Path,
) -> Path | str | None:
    value = _optional_string(raw, key, "project")
    if value.startswith(("https://", "http://")):
        return value
    return _optional_project_path(raw, key, root)


def _readthedocs_version(configured: str) -> str:
    """Use the hosted version slug while preserving project version width."""

    hosted = os.environ.get("READTHEDOCS_VERSION", "").strip()
    if not hosted:
        return configured
    if hosted.isdecimal() and re.fullmatch(r"0(?:\.0)+", configured):
        parts = configured.split(".")
        parts[-1] = hosted
        return ".".join(parts)
    return hosted


def _load_theme(raw: dict[str, Any]) -> ThemeConfig:
    allowed = {
        "primary",
        "content",
        "light_background",
        "dark_background",
        "font",
        "code_font",
    }
    _reject_unknown(raw, allowed, "theme")
    defaults = ThemeConfig()
    values = {
        key: _theme_value(raw, key, getattr(defaults, key)) for key in allowed
    }
    return ThemeConfig(**values)


def _load_build(raw: dict[str, Any], root: Path) -> BuildConfig:
    _reject_unknown(raw, {"output", "work", "strict", "clean"}, "build")
    output = _path_within_root(
        root, _optional_string(raw, "output", "build", "_site"), "build.output"
    )
    work = _path_within_root(
        root, _optional_string(raw, "work", "build", ".dockle"), "build.work"
    )
    if (
        output == work
        or output.is_relative_to(work)
        or work.is_relative_to(output)
    ):
        raise ConfigError(
            "build.output and build.work must not contain one another"
        )
    return BuildConfig(
        output=output,
        work=work,
        strict=_optional_bool(raw, "strict", "build", False),
        clean=_optional_bool(raw, "clean", "build", True),
    )


def _load_targets(
    raw: Any, root: Path, build: BuildConfig
) -> tuple[TargetConfig, ...]:
    if not isinstance(raw, list) or not raw:
        raise ConfigError("targets must be a non-empty array of tables")

    targets: list[TargetConfig] = []
    names: set[str] = set()
    outputs: set[Path] = set()
    home_target: str | None = None
    for index, item in enumerate(raw):
        where = f"targets[{index}]"
        if not isinstance(item, dict):
            raise ConfigError(f"{where} must be a table")
        target, home_target = _load_target(
            item,
            where,
            root,
            build,
            names,
            outputs,
            home_target,
        )
        targets.append(target)
    return tuple(targets)


def _load_target(
    item: dict[str, Any],
    where: str,
    root: Path,
    build: BuildConfig,
    names: set[str],
    outputs: set[Path],
    home_target: str | None,
) -> tuple[TargetConfig, str | None]:
    _reject_unknown(item, _TARGET_KEYS, where)
    name = _target_name(item, where, names)
    framework = _target_framework(item, where)
    source = _path_within_root(
        root, _required_string(item, "source", where), f"{where}.source"
    )
    doxygen = _load_doxygen(item, where, root, source, framework)
    jsdoc = _load_jsdoc(item, where, root, source, framework)
    mkdocs = _load_mkdocs(item, where, framework)
    sphinx = _load_sphinx(item, where, root, framework)
    rustdoc = _load_rustdoc(item, where, root, framework)
    home = _optional_bool(item, "home", where, False)
    publish = _optional_bool(item, "publish", where, True)
    if home and not publish:
        raise ConfigError(f"{where}.home requires publish = true")
    output, home_target = _target_output(
        item, where, name, home, build, outputs, home_target
    )
    if source == output or source.is_relative_to(output):
        raise ConfigError(
            f"{where}.source must not be inside its generated output"
        )
    return (
        TargetConfig(
            name=name,
            title=_optional_string(
                item, "title", where, name.replace("-", " ").title()
            ),
            description=_optional_string(item, "description", where),
            framework=framework,
            source=source,
            output=output,
            doxygen=doxygen,
            jsdoc=jsdoc,
            mkdocs=mkdocs,
            sphinx=sphinx,
            rustdoc=rustdoc,
            entry=_target_entry(item, where),
            home=home,
            publish=publish,
        ),
        home_target,
    )


def _load_doxygen(
    item: dict[str, Any],
    where: str,
    root: Path,
    source: Path,
    framework: str,
) -> DoxygenConfig | None:
    raw = item.get("doxygen", {})
    if not isinstance(raw, dict):
        raise ConfigError(f"{where}.doxygen must be a table")
    if framework != "doxygen":
        if raw:
            raise ConfigError(
                f"{where}.doxygen requires framework = 'doxygen'"
            )
        return None

    allowed = {
        "aliases",
        "dot_graph_max_nodes",
        "exclude_patterns",
        "excludes",
        "extra_files",
        "extra_javascript",
        "extra_stylesheets",
        "generate_xml",
        "image_paths",
        "include_paths",
        "inputs",
        "main_page",
        "optimize_output_java",
        "predefined",
        "separate_member_pages",
        "warn_if_undoc_enum_val",
        "warn_if_undocumented",
        "warn_no_paramdoc",
    }
    _reject_unknown(raw, allowed, f"{where}.doxygen")
    doxygen_where = f"{where}.doxygen"
    inputs = _path_list(
        raw,
        "inputs",
        doxygen_where,
        root,
        default=(source,),
    )
    if not inputs:
        raise ConfigError(f"{doxygen_where}.inputs must not be empty")
    return DoxygenConfig(
        inputs=inputs,
        excludes=_path_list(raw, "excludes", doxygen_where, root),
        exclude_patterns=_string_list(
            raw, "exclude_patterns", doxygen_where
        ),
        image_paths=_path_list(raw, "image_paths", doxygen_where, root),
        include_paths=_path_list(raw, "include_paths", doxygen_where, root),
        predefined=_string_list(raw, "predefined", doxygen_where),
        extra_javascript=_asset_list(
            raw, "extra_javascript", doxygen_where, root
        ),
        extra_stylesheets=_asset_list(
            raw, "extra_stylesheets", doxygen_where, root
        ),
        extra_files=_path_list(raw, "extra_files", doxygen_where, root),
        aliases=_string_list(raw, "aliases", doxygen_where),
        main_page=_optional_path(raw, "main_page", doxygen_where, root),
        dot_graph_max_nodes=_optional_int(
            raw,
            "dot_graph_max_nodes",
            doxygen_where,
            50,
            minimum=0,
            maximum=10000,
        ),
        optimize_output_java=_optional_bool(
            raw, "optimize_output_java", doxygen_where, False
        ),
        separate_member_pages=_optional_bool(
            raw, "separate_member_pages", doxygen_where, False
        ),
        generate_xml=_optional_bool(
            raw, "generate_xml", doxygen_where, False
        ),
        warn_if_undoc_enum_val=_optional_bool(
            raw, "warn_if_undoc_enum_val", doxygen_where, True
        ),
        warn_if_undocumented=_optional_bool(
            raw, "warn_if_undocumented", doxygen_where, True
        ),
        warn_no_paramdoc=_optional_bool(
            raw, "warn_no_paramdoc", doxygen_where, True
        ),
    )


def _load_jsdoc(
    item: dict[str, Any],
    where: str,
    root: Path,
    source: Path,
    framework: str,
) -> JsDocConfig | None:
    raw = item.get("jsdoc", {})
    if not isinstance(raw, dict):
        raise ConfigError(f"{where}.jsdoc must be a table")
    if framework != "jsdoc":
        if raw:
            raise ConfigError(f"{where}.jsdoc requires framework = 'jsdoc'")
        return None

    jsdoc_where = f"{where}.jsdoc"
    _reject_unknown(
        raw,
        {
            "exclude_pattern",
            "extra_files",
            "extra_javascript",
            "extra_stylesheets",
            "include_pattern",
            "inputs",
            "readme",
        },
        jsdoc_where,
    )
    inputs = _path_list(
        raw, "inputs", jsdoc_where, root, default=(source,)
    )
    if not inputs:
        raise ConfigError(f"{jsdoc_where}.inputs must not be empty")
    return JsDocConfig(
        inputs=inputs,
        readme=_optional_path(raw, "readme", jsdoc_where, root),
        include_pattern=_optional_string(
            raw, "include_pattern", jsdoc_where, r".+\.(c|m)?jsx?$"
        ),
        exclude_pattern=_optional_string(
            raw, "exclude_pattern", jsdoc_where
        ),
        extra_files=_path_list(raw, "extra_files", jsdoc_where, root),
        extra_javascript=_asset_list(
            raw, "extra_javascript", jsdoc_where, root
        ),
        extra_stylesheets=_asset_list(
            raw, "extra_stylesheets", jsdoc_where, root
        ),
    )


def _load_mkdocs(
    item: dict[str, Any], where: str, framework: str
) -> MkDocsConfig | None:
    raw = item.get("mkdocs", {})
    if not isinstance(raw, dict):
        raise ConfigError(f"{where}.mkdocs must be a table")
    if framework != "mkdocs":
        if raw:
            raise ConfigError(
                f"{where}.mkdocs requires framework = 'mkdocs'"
            )
        return None

    mkdocs_where = f"{where}.mkdocs"
    _reject_unknown(
        raw, {"extra_javascript", "extra_stylesheets"}, mkdocs_where
    )
    return MkDocsConfig(
        extra_javascript=_string_list(
            raw, "extra_javascript", mkdocs_where
        ),
        extra_stylesheets=_string_list(
            raw, "extra_stylesheets", mkdocs_where
        ),
    )


def _load_sphinx(
    item: dict[str, Any], where: str, root: Path, framework: str
) -> SphinxConfig | None:
    raw = item.get("sphinx", {})
    if not isinstance(raw, dict):
        raise ConfigError(f"{where}.sphinx must be a table")
    if framework != "sphinx":
        if raw:
            raise ConfigError(
                f"{where}.sphinx requires framework = 'sphinx'"
            )
        return None

    sphinx_where = f"{where}.sphinx"
    _reject_unknown(
        raw,
        {
            "exclude_patterns",
            "extra_javascript",
            "extra_stylesheets",
            "extra_config",
            "source_edit_link",
            "static_paths",
        },
        sphinx_where,
    )
    source_edit_link = _optional_string(
        raw, "source_edit_link", sphinx_where
    )
    if source_edit_link and "{filename}" not in source_edit_link:
        raise ConfigError(
            f"{sphinx_where}.source_edit_link must contain {{filename}}"
        )
    return SphinxConfig(
        exclude_patterns=_string_list(raw, "exclude_patterns", sphinx_where),
        static_paths=_path_list(raw, "static_paths", sphinx_where, root),
        extra_javascript=_string_list(
            raw, "extra_javascript", sphinx_where
        ),
        extra_stylesheets=_string_list(
            raw, "extra_stylesheets", sphinx_where
        ),
        extra_config=_optional_path(raw, "extra_config", sphinx_where, root),
        source_edit_link=source_edit_link,
    )


def _load_rustdoc(
    item: dict[str, Any], where: str, root: Path, framework: str
) -> RustdocConfig | None:
    raw = item.get("rustdoc", {})
    if not isinstance(raw, dict):
        raise ConfigError(f"{where}.rustdoc must be a table")
    if framework != "rustdoc":
        if raw:
            raise ConfigError(
                f"{where}.rustdoc requires framework = 'rustdoc'"
            )
        return None

    rustdoc_where = f"{where}.rustdoc"
    _reject_unknown(
        raw,
        {"extra_files", "extra_javascript", "extra_stylesheets"},
        rustdoc_where,
    )
    return RustdocConfig(
        extra_files=_path_list(raw, "extra_files", rustdoc_where, root),
        extra_javascript=_asset_list(
            raw, "extra_javascript", rustdoc_where, root
        ),
        extra_stylesheets=_asset_list(
            raw, "extra_stylesheets", rustdoc_where, root
        ),
    )


def _target_name(
    item: dict[str, Any], where: str, names: set[str]
) -> str:
    name = _required_string(item, "name", where)
    if not _TARGET_NAME.fullmatch(name):
        raise ConfigError(
            f"{where}.name must use lowercase letters, numbers, hyphens, or underscores"
        )
    if name in names:
        raise ConfigError(f"duplicate target name: {name}")
    names.add(name)
    return name


def _target_framework(item: dict[str, Any], where: str) -> str:
    framework = _required_string(item, "framework", where).lower()
    if framework not in SUPPORTED_FRAMEWORKS:
        supported = ", ".join(sorted(SUPPORTED_FRAMEWORKS))
        raise ConfigError(
            f"unsupported framework {framework!r}; choose one of: {supported}"
        )
    return framework


def _target_output(
    item: dict[str, Any],
    where: str,
    name: str,
    home: bool,
    build: BuildConfig,
    outputs: set[Path],
    home_target: str | None,
) -> tuple[Path, str | None]:
    if home:
        if "output" in item:
            raise ConfigError(f"{where}.output cannot be set for the home target")
        if home_target is not None:
            raise ConfigError(
                f"only one home target is allowed: {home_target}, {name}"
            )
        return build.output, name

    output_name = _optional_string(item, "output", where, name)
    output = _path_within_root(build.output, output_name, f"{where}.output")
    if output == build.output:
        raise ConfigError(
            f"{where}.output must name a directory below build.output"
        )
    if _overlaps_any(output, outputs):
        raise ConfigError(f"target output overlaps another target: {output_name}")
    outputs.add(output)
    return output, home_target


def _overlaps_any(output: Path, existing_outputs: set[Path]) -> bool:
    return any(
        output.is_relative_to(existing) or existing.is_relative_to(output)
        for existing in existing_outputs
    )


def _target_entry(item: dict[str, Any], where: str) -> str:
    entry = _optional_string(item, "entry", where, "index")
    entry_path = Path(entry)
    if entry_path.is_absolute() or ".." in entry_path.parts:
        raise ConfigError(
            f"{where}.entry must be a relative path within the target source"
        )
    return entry


def _load_tools(raw: dict[str, Any]) -> dict[str, str]:
    _reject_unknown(raw, set(SUPPORTED_FRAMEWORKS), "tools")
    return {key: _required_string(raw, key, "tools") for key in raw}


def _path_within_root(root: Path, value: str, where: str) -> Path:
    candidate = Path(value)
    if candidate.is_absolute():
        resolved = candidate.resolve()
    else:
        resolved = (root / candidate).resolve()
    root = root.resolve()
    if resolved != root and not resolved.is_relative_to(root):
        raise ConfigError(f"{where} must stay within {root}")
    return resolved


def _required_table(
    raw: dict[str, Any], key: str, where: str
) -> dict[str, Any]:
    value = raw.get(key)
    if not isinstance(value, dict):
        raise ConfigError(f"{where}.{key} must be a table")
    return value


def _optional_table(
    raw: dict[str, Any], key: str, where: str
) -> dict[str, Any]:
    value = raw.get(key, {})
    if not isinstance(value, dict):
        raise ConfigError(f"{where}.{key} must be a table")
    return value


def _required_string(raw: dict[str, Any], key: str, where: str) -> str:
    value = raw.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ConfigError(f"{where}.{key} must be a non-empty string")
    return value.strip()


def _optional_string(
    raw: dict[str, Any], key: str, where: str, default: str = ""
) -> str:
    value = raw.get(key, default)
    if not isinstance(value, str):
        raise ConfigError(f"{where}.{key} must be a string")
    return value.strip()


def _string_list(
    raw: dict[str, Any], key: str, where: str
) -> tuple[str, ...]:
    value = raw.get(key, [])
    if not isinstance(value, list):
        raise ConfigError(f"{where}.{key} must be an array of strings")
    strings: list[str] = []
    for index, item in enumerate(value):
        if not isinstance(item, str) or not item.strip():
            raise ConfigError(
                f"{where}.{key}[{index}] must be a non-empty string"
            )
        strings.append(item.strip())
    return tuple(strings)


def _path_list(
    raw: dict[str, Any],
    key: str,
    where: str,
    root: Path,
    *,
    default: tuple[Path, ...] = (),
) -> tuple[Path, ...]:
    if key not in raw:
        return default
    return tuple(
        _path_within_root(root, value, f"{where}.{key}[{index}]")
        for index, value in enumerate(_string_list(raw, key, where))
    )


def _asset_list(
    raw: dict[str, Any], key: str, where: str, root: Path
) -> tuple[AssetReference, ...]:
    return tuple(
        value
        if value.casefold().startswith(("https://", "http://"))
        else _path_within_root(root, value, f"{where}.{key}[{index}]")
        for index, value in enumerate(_string_list(raw, key, where))
    )


def _optional_path(
    raw: dict[str, Any], key: str, where: str, root: Path
) -> Path | None:
    value = _optional_string(raw, key, where)
    return _path_within_root(root, value, f"{where}.{key}") if value else None


def _theme_value(raw: dict[str, Any], key: str, default: str) -> str:
    value = _optional_string(raw, key, "theme", default)
    if not value:
        raise ConfigError(f"theme.{key} must not be empty")
    if any(character in value for character in ";{}<>\r\n"):
        raise ConfigError(
            f"theme.{key} contains characters that are unsafe in CSS"
        )
    return value


def _optional_bool(
    raw: dict[str, Any], key: str, where: str, default: bool
) -> bool:
    value = raw.get(key, default)
    if not isinstance(value, bool):
        raise ConfigError(f"{where}.{key} must be true or false")
    return value


def _optional_int(
    raw: dict[str, Any],
    key: str,
    where: str,
    default: int,
    *,
    minimum: int,
    maximum: int,
) -> int:
    value = raw.get(key, default)
    if not isinstance(value, int) or isinstance(value, bool):
        raise ConfigError(f"{where}.{key} must be an integer")
    if value < minimum or value > maximum:
        raise ConfigError(
            f"{where}.{key} must be between {minimum} and {maximum}"
        )
    return value


def _reject_unknown(
    raw: dict[str, Any], allowed: set[str], where: str
) -> None:
    unknown = sorted(set(raw) - allowed)
    if unknown:
        raise ConfigError(f"unknown key(s) in {where}: {', '.join(unknown)}")
