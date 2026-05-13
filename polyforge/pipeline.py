from __future__ import annotations

import json
from dataclasses import dataclass, field
from json import JSONDecodeError
from pathlib import Path
from typing import Any

from polyforge.canonicalize.json_ir import canonicalize_ir, canonicalize_program
from polyforge.check.chemistry import check_program_chemistry
from polyforge.check.diagnostics import Diagnostic
from polyforge.check.semantics import check_program
from polyforge.parser.ast_builder import build_ast
from polyforge.parser.parse import parse_polyforge_source


@dataclass(frozen=True)
class SourceArtifact:
    source_file: str
    source_format: str
    canonical_ir: dict[str, Any] | None
    diagnostics: list[Diagnostic] = field(default_factory=list)

    @property
    def errors(self) -> list[Diagnostic]:
        return [diagnostic for diagnostic in self.diagnostics if diagnostic.severity == "error"]

    @property
    def warnings(self) -> list[Diagnostic]:
        return [diagnostic for diagnostic in self.diagnostics if diagnostic.severity == "warning"]


def format_diagnostic(diagnostic: Diagnostic) -> str:
    location = diagnostic.file or "<input>"
    if diagnostic.line is not None:
        location = f"{location}:{diagnostic.line}"
        if diagnostic.column is not None:
            location = f"{location}:{diagnostic.column}"
    return f"{location}: [{diagnostic.severity}] {diagnostic.code}: {diagnostic.message}"


def load_source(path: str | Path) -> SourceArtifact:
    path = Path(path)
    text = path.read_text(encoding="utf-8")
    is_json_source = path.suffix.lower() == ".json" or text.lstrip().startswith("{")

    if is_json_source:
        return _load_canonical_json(path, text)
    return _load_pdsl(path, text)


def _syntax_diagnostic(code: str, message: str, *, path: Path, line: int | None = None, column: int | None = None, stage: str = "syntax") -> Diagnostic:
    return Diagnostic(
        code=code,
        severity="error",
        message=message,
        file=str(path),
        line=line,
        column=column,
        stage=stage,
    )


def _load_canonical_json(path: Path, text: str) -> SourceArtifact:
    try:
        payload = json.loads(text)
    except JSONDecodeError as exc:
        return SourceArtifact(
            source_file=str(path),
            source_format="canonical_json",
            canonical_ir=None,
            diagnostics=[
                _syntax_diagnostic(
                    "polyforge.syntax.invalid_json",
                    str(exc).strip(),
                    path=path,
                    line=exc.lineno,
                    column=exc.colno,
                )
            ],
        )

    try:
        canonical = canonicalize_ir(payload)
    except (AttributeError, KeyError, TypeError, ValueError) as exc:
        return SourceArtifact(
            source_file=str(path),
            source_format="canonical_json",
            canonical_ir=None,
            diagnostics=[
                _syntax_diagnostic(
                    "polyforge.input.invalid_canonical_json",
                    str(exc),
                    path=path,
                    stage="semantic",
                )
            ],
        )

    return SourceArtifact(
        source_file=str(path),
        source_format="canonical_json",
        canonical_ir=canonical,
        diagnostics=[],
    )


def _load_pdsl(path: Path, text: str) -> SourceArtifact:
    parse_result = parse_polyforge_source(text, filename=str(path))
    diagnostics = list(parse_result.diagnostics)

    if parse_result.tree is None:
        return SourceArtifact(
            source_file=str(path),
            source_format="pdsl",
            canonical_ir=None,
            diagnostics=diagnostics,
        )

    try:
        program = build_ast(parse_result.tree)
    except (TypeError, ValueError) as exc:
        diagnostics.append(
            _syntax_diagnostic(
                "polyforge.semantic.invalid_program",
                str(exc),
                path=path,
                stage="semantic",
            )
        )
        return SourceArtifact(
            source_file=str(path),
            source_format="pdsl",
            canonical_ir=None,
            diagnostics=diagnostics,
        )

    diagnostics.extend(check_program(program, filename=str(path)))
    chemistry = check_program_chemistry(program, filename=str(path))
    diagnostics.extend(chemistry.diagnostics)

    if any(diagnostic.severity == "error" for diagnostic in diagnostics):
        return SourceArtifact(
            source_file=str(path),
            source_format="pdsl",
            canonical_ir=None,
            diagnostics=diagnostics,
        )

    canonical = canonicalize_program(program, filename=str(path))
    return SourceArtifact(
        source_file=str(path),
        source_format="pdsl",
        canonical_ir=canonical,
        diagnostics=diagnostics,
    )
