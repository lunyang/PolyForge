from __future__ import annotations

from functools import lru_cache
from importlib.resources import files

from lark import Lark
from lark.exceptions import UnexpectedInput

from polyforge.check.diagnostics import Diagnostic, ParseResult


@lru_cache(maxsize=1)
def _load_parser() -> Lark:
    grammar = files("polyforge.grammar").joinpath("polyforge.lark").read_text(encoding="utf-8")
    return Lark(grammar, start="start", parser="lalr", propagate_positions=True, maybe_placeholders=False)


def _syntax_diagnostic(exc: UnexpectedInput, filename: str, source: str) -> Diagnostic:
    return Diagnostic(
        code="polyforge.syntax.error",
        severity="error",
        message=str(exc).strip(),
        file=filename,
        line=getattr(exc, "line", None),
        column=getattr(exc, "column", None),
        stage="syntax",
    )


def parse_polyforge_source(source: str, filename: str = "<string>") -> ParseResult:
    try:
        tree = _load_parser().parse(source)
    except UnexpectedInput as exc:
        return ParseResult(tree=None, diagnostics=[_syntax_diagnostic(exc, filename, source)])
    return ParseResult(tree=tree, diagnostics=[])

