from __future__ import annotations

from pathlib import Path

from experiments.llm_generation.artifacts import LlmRunArtifact, read_llm_artifact, write_llm_artifact
from experiments.llm_generation.extract import extract_pdsl_blocks


def test_extract_pdsl_blocks_from_saved_llm_output():
    text = Path("experiments/fixtures/llm_outputs/valid_homopolymer.txt").read_text(encoding="utf-8")

    blocks = extract_pdsl_blocks(text)

    assert len(blocks) == 1
    assert blocks[0].startswith("polymer ")
    assert "sequence: homopolymer(MMA)" in blocks[0]


def test_extract_pdsl_blocks_handles_multiple_fenced_blocks():
    text = Path("experiments/fixtures/llm_outputs/invalid_then_repair.txt").read_text(encoding="utf-8")

    blocks = extract_pdsl_blocks(text)

    assert len(blocks) == 2
    assert blocks[0].startswith("polymer BadCandidate")
    assert blocks[1].startswith("polymer RepairedCandidate")


def test_llm_artifact_round_trip(tmp_path):
    artifact = LlmRunArtifact(
        run_id="fixture-001",
        model="fixture",
        prompt="generate a valid PolyForge program",
        raw_output="polymer PMMA { }",
        extracted_pdsl=["polymer PMMA { }"],
        metadata={"temperature": 0},
    )

    path = write_llm_artifact(artifact, tmp_path)

    assert path.name == "fixture-001.json"
    assert read_llm_artifact(path) == artifact
