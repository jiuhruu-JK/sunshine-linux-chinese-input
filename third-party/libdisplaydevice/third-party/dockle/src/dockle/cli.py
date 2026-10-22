"""Command-line interface for Dockle."""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from pathlib import Path

from dockle import __version__
from dockle.builders import BuildError, BuildManager
from dockle.config import ConfigError, DockleConfig, TargetConfig, load_config
from dockle.theme import ThemeError


def build_parser() -> argparse.ArgumentParser:
    """Create the Dockle argument parser."""

    parser = argparse.ArgumentParser(
        prog="dockle",
        description="Build documentation with multiple frameworks and one consistent theme.",
    )
    parser.add_argument(
        "--version", action="version", version=f"%(prog)s {__version__}"
    )
    parser.add_argument(
        "-c",
        "--config",
        type=Path,
        default=Path("dockle.toml"),
        help="Dockle configuration file (default: dockle.toml)",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    check = subparsers.add_parser(
        "check", help="validate configuration, sources, and tools"
    )
    check.add_argument(
        "targets", nargs="*", help="target names (default: all)"
    )

    build = subparsers.add_parser(
        "build", help="build one or more documentation targets"
    )
    build.add_argument(
        "targets", nargs="*", help="target names (default: all)"
    )
    build.add_argument(
        "--dry-run",
        action="store_true",
        help="print generated commands without writing or running them",
    )
    subparsers.add_parser(
        "cmake-dir",
        help="print the directory containing Dockle.cmake",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Run the Dockle CLI and return a process exit code."""

    raw_arguments = list(sys.argv[1:] if argv is None else argv)
    internal_status = _run_internal_generator(raw_arguments)
    if internal_status is not None:
        return internal_status

    arguments = build_parser().parse_args(raw_arguments)
    if arguments.command == "cmake-dir":
        print(Path(__file__).with_name("cmake"))
        return 0

    try:
        config = load_config(arguments.config)
        targets = config.select_targets(arguments.targets)
        manager = BuildManager(config)

        if arguments.command == "check":
            return _run_check(config, targets, manager)
        _run_build(targets, manager, arguments.dry_run)
        return 0
    except (BuildError, ConfigError, ThemeError) as error:
        print(f"dockle: error: {error}", file=sys.stderr)
        return 2


def _run_internal_generator(arguments: list[str]) -> int | None:
    """Run a bundled Python generator for a frozen standalone executable."""

    if not arguments or arguments[0] not in {"_run-sphinx", "_run-mkdocs"}:
        return None
    generator, generator_arguments = arguments[0], arguments[1:]
    if generator == "_run-sphinx":
        from sphinx.cmd.build import main as sphinx_main

        return sphinx_main(generator_arguments)

    import click
    from mkdocs.__main__ import cli as mkdocs_cli

    try:
        result = mkdocs_cli.main(
            args=generator_arguments,
            prog_name="mkdocs",
            standalone_mode=False,
        )
    except click.ClickException as error:
        error.show()
        return error.exit_code
    except click.Abort:
        print("Aborted!", file=sys.stderr)
        return 1
    return int(result or 0)


def _run_check(
    config: DockleConfig,
    targets: tuple[TargetConfig, ...],
    manager: BuildManager,
) -> int:
    failed = False
    print(f"OK configuration: {config.path}")
    for target, problem in manager.check(targets):
        if problem:
            failed = True
            print(f"ERROR {target.name} ({target.framework}): {problem}")
        else:
            print(f"OK {target.name} ({target.framework}): {target.source}")
    return 1 if failed else 0


def _run_build(
    targets: tuple[TargetConfig, ...],
    manager: BuildManager,
    dry_run: bool,
) -> None:
    if dry_run:
        for target in targets:
            plan = manager.plan(target)
            print(f"{target.name} ({target.framework}) -> {target.output}")
            print(f"  {plan.command.display()}")
        return

    for result in manager.build(targets):
        suffix = (
            f", themed {result.themed_pages} HTML page(s)"
            if result.themed_pages
            else ""
        )
        print(f"Built {result.target.name} -> {result.target.output}{suffix}")


if __name__ == "__main__":
    raise SystemExit(main())
