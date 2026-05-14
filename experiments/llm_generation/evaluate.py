from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from experiments.llm_generation.extract import extract_pdsl_blocks
from polyforge.pipeline import format_diagnostic, load_source


def evaluate_saved_llm_outputs(fixture_dir: str | Path, output_dir: str | Path) -> dict[str, Any]:
    fixture_path = Path(fixture_dir)
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    candidate_dir = output_path / "candidates"
    candidate_dir.mkdir(parents=True, exist_ok=True)

    records: list[dict[str, Any]] = []
    output_files = sorted(fixture_path.glob("*.txt"))
    for output_index, source_path in enumerate(output_files):
        raw_output = source_path.read_text(encoding="utf-8")
        for candidate_index, pdsl in enumerate(extract_pdsl_blocks(raw_output)):
            candidate_path = candidate_dir / f"{source_path.stem}-{candidate_index}.pdsl"
            candidate_path.write_text(pdsl, encoding="utf-8")
            artifact = load_source(candidate_path)
            records.append(_candidate_record(output_index, source_path, candidate_index, pdsl, artifact))

    metrics = _metrics(records, total_outputs=len(output_files))
    (output_path / "llm_generation_metrics.json").write_text(
        json.dumps(metrics, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    (output_path / "llm_generation_candidates.json").write_text(
        json.dumps(records, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    return metrics


def _candidate_record(output_index: int, source_path: Path, candidate_index: int, pdsl: str, artifact) -> dict[str, Any]:
    errors = artifact.errors
    diagnostics = [format_diagnostic(diagnostic) for diagnostic in artifact.diagnostics]
    parse_pass = not any(diagnostic.stage == "syntax" and diagnostic.severity == "error" for diagnostic in artifact.diagnostics)
    semantic_pass = parse_pass and not any(diagnostic.stage == "semantic" and diagnostic.severity == "error" for diagnostic in artifact.diagnostics)
    chemistry_pass = parse_pass and not any(diagnostic.stage == "chemistry" and diagnostic.severity == "error" for diagnostic in artifact.diagnostics)
    canonicalization_pass = artifact.canonical_ir is not None
    return {
        "output_index": output_index,
        "source_file": str(source_path),
        "candidate_index": candidate_index,
        "pdsl": pdsl,
        "diagnostics": diagnostics,
        "error_count": len(errors),
        "parse_pass": parse_pass,
        "semantic_pass": semantic_pass,
        "chemistry_pass": chemistry_pass,
        "canonicalization_pass": canonicalization_pass,
        "canonical_id": artifact.canonical_ir.get("canonical_id") if artifact.canonical_ir else None,
    }


def _metrics(records: list[dict[str, Any]], *, total_outputs: int) -> dict[str, Any]:
    total_candidates = len(records)
    return {
        "total_outputs": total_outputs,
        "total_candidates": total_candidates,
        "parse_pass_rate": _rate(records, "parse_pass"),
        "semantic_pass_rate": _rate(records, "semantic_pass"),
        "chemistry_pass_rate": _rate(records, "chemistry_pass"),
        "canonicalization_pass_rate": _rate(records, "canonicalization_pass"),
        "valid_candidates": sum(1 for record in records if record["canonicalization_pass"]),
    }


def _rate(records: list[dict[str, Any]], key: str) -> float:
    if not records:
        return 0.0
    return sum(1 for record in records if record[key]) / len(records)
