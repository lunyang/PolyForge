from __future__ import annotations

from typing import Any


def rank_candidates(
    candidates: list[dict[str, Any]],
    *,
    target_low: float,
    target_high: float,
    training_structure_keys: set[str],
) -> list[dict[str, Any]]:
    center = (target_low + target_high) / 2.0
    ranked: list[dict[str, Any]] = []
    for candidate in candidates:
        predicted = float(candidate["predicted_tg_k"])
        target_hit = target_low <= predicted <= target_high
        error_to_center = abs(predicted - center)
        structure_key = str(candidate.get("structure_key", ""))
        novel = structure_key not in training_structure_keys
        enriched = {
            **candidate,
            "target_low": float(target_low),
            "target_high": float(target_high),
            "target_hit": target_hit,
            "target_error_to_center": error_to_center,
            "novel": novel,
            "rank_score": _rank_score(target_hit=target_hit, novel=novel, error_to_center=error_to_center),
        }
        ranked.append(enriched)
    return sorted(ranked, key=lambda candidate: candidate["rank_score"])


def _rank_score(*, target_hit: bool, novel: bool, error_to_center: float) -> float:
    miss_penalty = 0.0 if target_hit else 10000.0
    novelty_penalty = 0.0 if novel else 1000.0
    return miss_penalty + novelty_penalty + error_to_center
