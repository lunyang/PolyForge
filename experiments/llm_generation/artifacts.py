from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class LlmRunArtifact:
    run_id: str
    model: str
    prompt: str
    raw_output: str
    extracted_pdsl: list[str]
    metadata: dict[str, Any] = field(default_factory=dict)


def write_llm_artifact(artifact: LlmRunArtifact, output_dir: str | Path) -> Path:
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    path = output_path / f"{artifact.run_id}.json"
    path.write_text(json.dumps(asdict(artifact), indent=2, sort_keys=True), encoding="utf-8")
    return path


def read_llm_artifact(path: str | Path) -> LlmRunArtifact:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    return LlmRunArtifact(
        run_id=payload["run_id"],
        model=payload["model"],
        prompt=payload["prompt"],
        raw_output=payload["raw_output"],
        extracted_pdsl=list(payload["extracted_pdsl"]),
        metadata=dict(payload.get("metadata", {})),
    )
