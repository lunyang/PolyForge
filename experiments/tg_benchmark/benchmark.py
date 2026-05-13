from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

from experiments.tg_benchmark.dataset import audit_dataset, load_bigsmiles_tg_csv
from experiments.tg_benchmark.features import FeatureTable, make_bigsmiles_char_features, make_smiles_features
from experiments.tg_benchmark.splits import make_grouped_folds
from polyforge.ml.models import SUPPORTED_MODELS, make_estimator

SUPPORTED_REPRESENTATIONS = ("smiles_rdkit", "bigsmiles_char")


def run_tg_benchmark(
    *,
    dataset_path: str | Path,
    output_dir: str | Path,
    representations: list[str] | tuple[str, ...] = ("bigsmiles_char",),
    models: list[str] | tuple[str, ...] = ("mean", "random_forest"),
    n_splits: int = 5,
    seed: int = 13,
) -> dict[str, Any]:
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    dataset = load_bigsmiles_tg_csv(dataset_path)
    audit = audit_dataset(dataset.frame)
    folds = make_grouped_folds(dataset.frame, n_splits=n_splits, seed=seed)

    metrics: list[dict[str, Any]] = []
    prediction_frames: list[pd.DataFrame] = []

    for representation in representations:
        feature_table = _make_features(representation, dataset.frame)
        for model_name in models:
            run_predictions, run_metrics = _cross_validate(
                feature_table,
                folds=folds,
                representation=representation,
                model_name=model_name,
                seed=seed,
            )
            prediction_frames.append(run_predictions)
            metrics.append(run_metrics)

    metrics_payload = {
        "dataset": audit,
        "n_splits": n_splits,
        "seed": seed,
        "runs": metrics,
    }

    _write_json(output_path / "dataset_audit.json", audit)
    _write_json(output_path / "splits.json", {"folds": folds})
    _write_json(output_path / "metrics.json", metrics_payload)
    pd.concat(prediction_frames, ignore_index=True).to_csv(output_path / "predictions.csv", index=False)

    return metrics_payload


def _make_features(representation: str, frame: pd.DataFrame) -> FeatureTable:
    if representation == "smiles_rdkit":
        return make_smiles_features(frame)
    if representation == "bigsmiles_char":
        return make_bigsmiles_char_features(frame)
    raise ValueError(f"unsupported representation: {representation}")


def _cross_validate(
    feature_table: FeatureTable,
    *,
    folds: list[dict[str, Any]],
    representation: str,
    model_name: str,
    seed: int,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    if model_name not in SUPPORTED_MODELS:
        raise ValueError(f"unsupported model: {model_name}")

    frame = feature_table.frame
    features = frame[feature_table.feature_columns].apply(pd.to_numeric, errors="coerce")
    target = pd.to_numeric(frame["tg_k"], errors="raise")
    predictions = np.empty(len(frame), dtype=float)
    fold_numbers = np.empty(len(frame), dtype=int)

    for fold in folds:
        train_indices = fold["train_indices"]
        test_indices = fold["test_indices"]
        estimator = make_estimator(model_name, random_state=seed)
        estimator.fit(features.iloc[train_indices], target.iloc[train_indices])
        predictions[test_indices] = estimator.predict(features.iloc[test_indices])
        fold_numbers[test_indices] = int(fold["fold"])

    prediction_frame = frame[["row_index", "polymer_name", "structure_key", "tg_k"]].copy()
    prediction_frame["representation"] = representation
    prediction_frame["model"] = model_name
    prediction_frame["fold"] = fold_numbers
    prediction_frame["prediction"] = predictions

    run_metrics = {
        "representation": representation,
        "model": model_name,
        "n_rows": int(len(frame)),
        "n_features": int(len(feature_table.feature_columns)),
        "mae": float(mean_absolute_error(target, predictions)),
        "rmse": float(np.sqrt(mean_squared_error(target, predictions))),
        "r2": float(r2_score(target, predictions)),
    }
    return prediction_frame, run_metrics


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
