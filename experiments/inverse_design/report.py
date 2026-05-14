from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def write_inverse_design_report(
    *,
    output_dir: str | Path,
    generated_count: int,
    parsed_count: int,
    valid_count: int,
    ranked_candidates: list[dict[str, Any]],
) -> dict[str, Any]:
    report = {
        "funnel": {
            "generated": int(generated_count),
            "parsed": int(parsed_count),
            "valid": int(valid_count),
            "ranked": int(len(ranked_candidates)),
        },
        "top_candidates": ranked_candidates,
        "summary": {
            "target_hits": sum(1 for candidate in ranked_candidates if candidate.get("target_hit")),
            "novel_candidates": sum(1 for candidate in ranked_candidates if candidate.get("novel")),
            "unique_structure_keys": len({candidate.get("structure_key") for candidate in ranked_candidates}),
        },
    }
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    (output_path / "inverse_design_report.json").write_text(
        json.dumps(report, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    return report
