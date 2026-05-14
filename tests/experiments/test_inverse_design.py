from __future__ import annotations

import json

from experiments.inverse_design.rank import rank_candidates
from experiments.inverse_design.report import write_inverse_design_report


def test_rank_candidates_prefers_target_window_hits():
    candidates = [
        {"canonical_id": "a", "predicted_tg_k": 210.0, "structure_key": "s1"},
        {"canonical_id": "b", "predicted_tg_k": 390.0, "structure_key": "s2"},
        {"canonical_id": "c", "predicted_tg_k": 700.0, "structure_key": "s3"},
    ]

    ranked = rank_candidates(
        candidates,
        target_low=180.0,
        target_high=250.0,
        training_structure_keys=set(),
    )

    assert ranked[0]["canonical_id"] == "a"
    assert ranked[0]["target_hit"] is True
    assert ranked[0]["novel"] is True
    assert ranked[-1]["canonical_id"] == "c"


def test_rank_candidates_marks_non_novel_training_structures():
    candidates = [
        {"canonical_id": "a", "predicted_tg_k": 210.0, "structure_key": "seen"},
    ]

    ranked = rank_candidates(
        candidates,
        target_low=180.0,
        target_high=250.0,
        training_structure_keys={"seen"},
    )

    assert ranked[0]["novel"] is False


def test_inverse_design_report_writes_funnel_metrics(tmp_path):
    report = write_inverse_design_report(
        output_dir=tmp_path,
        generated_count=10,
        parsed_count=8,
        valid_count=5,
        ranked_candidates=[],
    )

    assert report["funnel"]["generated"] == 10
    assert report["funnel"]["parsed"] == 8
    assert report["funnel"]["valid"] == 5
    report_path = tmp_path / "inverse_design_report.json"
    assert report_path.exists()
    assert json.loads(report_path.read_text(encoding="utf-8")) == report
