"""Markdown helpers shared by the portal and compatible generators."""

from __future__ import annotations

import re

from markdown import Markdown
from markdown.extensions import Extension
from markdown.preprocessors import Preprocessor

_ALERT_START = re.compile(
    r"^>\s*\[!(ATTENTION|CAUTION|DANGER|ERROR|HINT|IMPORTANT|NOTE|SEEALSO|TIP|TODO|WARNING)\]\s*$",
    re.IGNORECASE,
)
_FENCE_START = re.compile(r"^ {0,3}(`{3,}|~{3,})")


def normalize_github_alerts(source: str) -> str:
    """Translate GitHub alerts into Python-Markdown admonitions."""

    lines = source.splitlines()
    normalized: list[str] = []
    index = 0
    fence_character = ""
    fence_length = 0
    while index < len(lines):
        line = lines[index]
        if fence_character:
            normalized.append(line)
            if _closes_fence(line, fence_character, fence_length):
                fence_character = ""
                fence_length = 0
            index += 1
            continue

        opening_fence = _opening_fence(line)
        if opening_fence is not None:
            fence_character, fence_length = opening_fence
            normalized.append(line)
            index += 1
            continue

        match = _ALERT_START.match(line)
        if match is None:
            normalized.append(line)
            index += 1
            continue

        index = _append_alert(lines, index, match.group(1), normalized)
    return "\n".join(normalized)


def _opening_fence(line: str) -> tuple[str, int] | None:
    match = _FENCE_START.match(line)
    if match is None:
        return None
    fence = match.group(1)
    return fence[0], len(fence)


def _closes_fence(line: str, character: str, length: int) -> bool:
    stripped = line.lstrip(" ")
    indentation = len(line) - len(stripped)
    fence = stripped.rstrip()
    return (
        indentation <= 3
        and len(fence) >= length
        and set(fence) == {character}
    )


def _append_alert(
    lines: list[str],
    index: int,
    alert_type: str,
    normalized: list[str],
) -> int:
    normalized.append(f"!!! {alert_type.lower()}")
    index += 1
    while index < len(lines) and lines[index].startswith(">"):
        content = lines[index][1:].removeprefix(" ")
        normalized.append(f"    {content}" if content else "")
        index += 1
    normalized.append("")
    return index


class GithubAlertPreprocessor(Preprocessor):
    """Normalize GitHub alert blockquotes before Markdown parsing."""

    def run(self, lines: list[str]) -> list[str]:
        """Return normalized source lines."""

        return normalize_github_alerts("\n".join(lines)).splitlines()


class GithubAlertsExtension(Extension):
    """Add GitHub alert syntax to Python-Markdown."""

    def extendMarkdown(self, md: Markdown) -> None:  # noqa: N802
        """Register the alert preprocessor."""

        processor = GithubAlertPreprocessor(md)
        md.preprocessors.register(processor, "dockle_github_alerts", 35)


def makeExtension(**kwargs: object) -> GithubAlertsExtension:  # noqa: N802  # NOSONAR
    """Return the extension for Python-Markdown and MkDocs."""

    return GithubAlertsExtension(**kwargs)


def render_markdown(source: str) -> str:
    """Render project Markdown with Dockle's supported extensions."""

    renderer = Markdown(
        extensions=[
            "extra",
            "admonition",
            GithubAlertsExtension(),
        ]
    )
    return renderer.convert(source)
