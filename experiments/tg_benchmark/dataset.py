from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd

SOURCE_COLUMNS = {
    "Unnamed: 0": "row_index",
    "Polymer": "polymer_name",
    "SMILES": "smiles",
    "BigSMILES": "bigsmiles",
    "Tg (K) exp": "tg_k",
}

NORMALIZED_COLUMNS = ["row_index", "polymer_name", "smiles", "bigsmiles", "tg_k"]


@dataclass(frozen=True)
class BigSmilesTgDataset:
    frame: pd.DataFrame
    source_path: Path


def load_bigsmiles_tg_csv(path: str | Path) -> BigSmilesTgDataset:
    source_path = Path(path)
    frame = pd.read_csv(source_path, encoding="latin-1")
    frame = _normalize_columns(frame)
    frame["tg_k"] = pd.to_numeric(frame["tg_k"], errors="coerce")
    if frame["tg_k"].isna().any():
        bad_count = int(frame["tg_k"].isna().sum())
        raise ValueError(f"Tg column contains {bad_count} non-numeric or missing values")
    frame["structure_key"] = [
        _structure_key(smiles, bigsmiles)
        for smiles, bigsmiles in zip(frame["smiles"], frame["bigsmiles"], strict=True)
    ]
    return BigSmilesTgDataset(frame=frame, source_path=source_path)


def audit_dataset(frame: pd.DataFrame) -> dict[str, Any]:
    target = pd.to_numeric(frame["tg_k"], errors="coerce")
    duplicate_full_rows = int(frame.duplicated(subset=NORMALIZED_COLUMNS, keep=False).sum())
    duplicate_structure_pairs = int(frame.duplicated(subset=["smiles", "bigsmiles"], keep=False).sum())
    duplicate_smiles = _duplicate_key_count(frame["smiles"])
    duplicate_bigsmiles = _duplicate_key_count(frame["bigsmiles"])

    return {
        "rows": int(len(frame)),
        "target_missing_or_bad": int(target.isna().sum()),
        "tg_min_k": _round3(target.min()),
        "tg_max_k": _round3(target.max()),
        "tg_mean_k": _round3(target.mean()),
        "tg_median_k": _round3(target.median()),
        "tg_population_std_k": _round3(target.std(ddof=0)),
        "unique_polymer_names": int(frame["polymer_name"].nunique()),
        "exact_duplicate_rows": duplicate_full_rows,
        "duplicate_structure_pairs": duplicate_structure_pairs,
        "duplicate_smiles": duplicate_smiles,
        "duplicate_bigsmiles": duplicate_bigsmiles,
    }


def _normalize_columns(frame: pd.DataFrame) -> pd.DataFrame:
    missing = [column for column in SOURCE_COLUMNS if column not in frame.columns]
    if missing:
        raise ValueError(f"missing required dataset columns: {missing}")
    normalized = frame.rename(columns=SOURCE_COLUMNS)[NORMALIZED_COLUMNS].copy()
    normalized["row_index"] = pd.to_numeric(normalized["row_index"], errors="raise").astype(int)
    for column in ("polymer_name", "smiles", "bigsmiles"):
        normalized[column] = normalized[column].astype(str).str.strip()
    return normalized


def _structure_key(smiles: str, bigsmiles: str) -> str:
    payload = f"{str(smiles).strip()}\n{str(bigsmiles).strip()}".encode("utf-8")
    return f"sha256:{hashlib.sha256(payload).hexdigest()}"


def _duplicate_key_count(series: pd.Series) -> int:
    counts = series.value_counts()
    return int((counts > 1).sum())


def _round3(value: float) -> float:
    return round(float(value), 3)
