from __future__ import annotations

import hashlib
from typing import Any

import pandas as pd
from sklearn.model_selection import GroupKFold


def make_grouped_folds(frame: pd.DataFrame, n_splits: int = 5, seed: int = 13) -> list[dict[str, Any]]:
    if "structure_key" not in frame.columns:
        raise ValueError("frame must include a structure_key column")
    if n_splits < 2:
        raise ValueError("n_splits must be at least 2")

    working = frame.reset_index(drop=True).copy()
    groups = working["structure_key"].astype(str)
    unique_groups = groups.nunique()
    if unique_groups < n_splits:
        raise ValueError(f"n_splits={n_splits} cannot exceed the number of groups ({unique_groups})")

    # GroupKFold is deterministic but not shuffled. Sort by a stable hash-derived
    # group key first so fold allocation does not depend on source row order.
    working["_original_index"] = range(len(working))
    working["_split_order"] = [
        _stable_group_order(group, seed)
        for group in groups
    ]
    ordered = working.sort_values(["_split_order", "_original_index"], kind="mergesort").reset_index(drop=True)

    splitter = GroupKFold(n_splits=n_splits)
    folds: list[dict[str, Any]] = []
    x = ordered[["_original_index"]]
    y = ordered["tg_k"] if "tg_k" in ordered.columns else None
    ordered_groups = ordered["structure_key"].astype(str)

    for fold_index, (train_positions, test_positions) in enumerate(splitter.split(x, y, ordered_groups)):
        train_indices = sorted(int(ordered.iloc[position]["_original_index"]) for position in train_positions)
        test_indices = sorted(int(ordered.iloc[position]["_original_index"]) for position in test_positions)
        folds.append(
            {
                "fold": fold_index,
                "train_indices": train_indices,
                "test_indices": test_indices,
            }
        )
    return folds


def _stable_group_order(group: str, seed: int) -> str:
    return hashlib.sha256(f"{seed}\n{group}".encode("utf-8")).hexdigest()
