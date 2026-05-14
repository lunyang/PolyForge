from __future__ import annotations

import json

from experiments.llm_generation.evaluate import evaluate_saved_llm_outputs
from experiments.llm_generation.repair import make_repair_prompt


def test_evaluate_llm_outputs_reports_validation_stages(tmp_path):
    result = evaluate_saved_llm_outputs(
        fixture_dir="experiments/fixtures/llm_outputs",
        output_dir=tmp_path,
    )

    assert result["total_outputs"] == 2
    assert result["total_candidates"] == 3
    assert "parse_pass_rate" in result
    assert "semantic_pass_rate" in result
    assert "chemistry_pass_rate" in result
    assert "canonicalization_pass_rate" in result
    assert 0.0 < result["canonicalization_pass_rate"] < 1.0

    metrics_path = tmp_path / "llm_generation_metrics.json"
    candidates_path = tmp_path / "llm_generation_candidates.json"
    assert metrics_path.exists()
    assert candidates_path.exists()
    assert json.loads(metrics_path.read_text(encoding="utf-8")) == result


def test_make_repair_prompt_includes_diagnostics():
    prompt = make_repair_prompt("polymer Bad {", ["syntax error at line 1"])

    assert "polymer Bad {" in prompt
    assert "syntax error at line 1" in prompt
    assert "Return only corrected PolyForge" in prompt
