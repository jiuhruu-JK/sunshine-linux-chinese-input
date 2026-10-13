"""Small Python API used to compare Dockle's Sphinx output."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class WarningPolicy(Enum):
    """Control how an adapter handles generator warnings."""

    REPORT = "report"
    FAIL = "fail"


@dataclass(frozen=True)
class DocumentationTarget:
    """Describe one framework-neutral documentation target."""

    name: str
    framework: str
    policy: WarningPolicy

    def summary(self) -> str:
        """Return a human-readable target description."""

        return f"{self.name} ({self.framework})"


def select_by_framework(
    targets: list[DocumentationTarget],
    framework: str,
) -> list[DocumentationTarget]:
    """Return targets that use ``framework`` in their original order."""

    return [target for target in targets if target.framework == framework]
