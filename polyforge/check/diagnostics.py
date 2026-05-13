from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


Severity = Literal["error", "warning", "info"]


@dataclass(frozen=True)
class Diagnostic:
    code: str
    severity: Severity
    message: str
    file: str | None = None
    line: int | None = None
    column: int | None = None
    path: str | None = None
    stage: str = "syntax"


@dataclass(frozen=True)
class ParseResult:
    tree: object | None
    diagnostics: list[Diagnostic]

