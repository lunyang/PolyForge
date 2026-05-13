"""PolyForge check package."""

from .diagnostics import Diagnostic, ParseResult
from .semantics import check_program, check_programs

__all__ = [
    "Diagnostic",
    "ParseResult",
    "check_program",
    "check_programs",
]
