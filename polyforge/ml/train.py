from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import GroupKFold, KFold

from polyforge.ml.models import SUPPORTED_MODELS, make_estimator


TARGET_COLUMN = "target_value"
GROUP_COLUMN = "structure_hash"


@dataclass(frozen=True)
class TrainResult:
    run_dir: Path
    metrics_path: Path
    model_path: Path
    predictions_path: Path
    metrics: dict[str, Any]


def _feature_columns(frame: pd.DataFrame) -> list[str]:
    return sorted(column for column in frame.columns if column.startswith("descriptor."))


def _validate_frame(frame: pd.DataFrame) -> tuple[pd.DataFrame, list[str], pd.Series, pd.Series]:
    missing_columns = [column for column in (TARGET_COLUMN, GROUP_COLUMN) if column not in frame.columns]
    if missing_columns:
        raise ValueError(f"missing required column(s): {', '.join(missing_columns)}")

    feature_columns = _feature_columns(frame)
    if not feature_columns:
        raise ValueError("no descriptor columns found")

    features = frame[feature_columns].apply(pd.to_numeric, errors="coerce")
    if features.isna().any().any():
        raise ValueError("feature columns must be numeric")

    target = pd.to_numeric(frame[TARGET_COLUMN], errors="coerce")
    if target.isna().any():
        raise ValueError("target_value column must be numeric")

    groups = frame[GROUP_COLUMN].astype(str)
    return features, feature_columns, target, groups


def _make_splitter(split: str, *, n_rows: int, n_groups: int, random_state: int) -> tuple[Any, int]:
    if split == "grouped":
        n_splits = min(5, n_groups)
        if n_splits < 2:
            raise ValueError("grouped cross-validation requires at least two structure_hash groups")
        return GroupKFold(n_splits=n_splits), n_splits

    if split == "random":
        n_splits = min(5, n_rows)
        if n_splits < 2:
            raise ValueError("random cross-validation requires at least two rows")
        return KFold(n_splits=n_splits, shuffle=True, random_state=random_state), n_splits

    raise ValueError(f"unsupported split strategy: {split}")


def _fit_predict(
    frame: pd.DataFrame,
    *,
    model_name: str,
    split: str,
    random_state: int,
) -> tuple[pd.DataFrame, dict[str, Any], Any]:
    features, feature_columns, target, groups = _validate_frame(frame)
    splitter, fold_count = _make_splitter(split, n_rows=len(frame), n_groups=groups.nunique(), random_state=random_state)

    predictions = np.empty(len(frame), dtype=float)
    folds = np.empty(len(frame), dtype=int)

    for fold, split_indices in enumerate(
        splitter.split(features, target, groups if split == "grouped" else None),
        start=1,
    ):
        train_index, test_index = split_indices
        estimator = make_estimator(model_name, random_state=random_state)
        estimator.fit(features.iloc[train_index], target.iloc[train_index])
        predictions[test_index] = estimator.predict(features.iloc[test_index])
        folds[test_index] = fold

    metrics = {
        "model": model_name,
        "split": split,
        "folds": fold_count,
        "target_column": TARGET_COLUMN,
        "n_rows": int(len(frame)),
        "n_features": int(len(feature_columns)),
        "mae": float(mean_absolute_error(target, predictions)),
        "rmse": float(np.sqrt(mean_squared_error(target, predictions))),
        "r2": float(r2_score(target, predictions)),
    }

    predictions_frame = frame[[
        column
        for column in [
            "canonical_id",
            "source_file",
            "source_format",
            GROUP_COLUMN,
            "target_property",
            "target_units",
        ]
        if column in frame.columns
    ]].copy()
    predictions_frame["fold"] = folds
    predictions_frame["target_value"] = target.values
    predictions_frame["prediction"] = predictions

    estimator = make_estimator(model_name, random_state=random_state)
    estimator.fit(features, target)
    return predictions_frame, metrics, estimator


def train_feature_csv(
    feature_csv: str | Path,
    *,
    model_name: str,
    run_dir: str | Path,
    split: str = "grouped",
    random_state: int = 0,
) -> TrainResult:
    if model_name not in SUPPORTED_MODELS:
        raise ValueError(f"unsupported model: {model_name}")

    frame = pd.read_csv(feature_csv)
    predictions_frame, metrics, estimator = _fit_predict(
        frame,
        model_name=model_name,
        split=split,
        random_state=random_state,
    )

    run_dir = Path(run_dir)
    run_dir.mkdir(parents=True, exist_ok=True)
    metrics_path = run_dir / "metrics.json"
    model_path = run_dir / "model.joblib"
    predictions_path = run_dir / "predictions.csv"

    metrics_path.write_text(json.dumps(metrics, indent=2, sort_keys=True), encoding="utf-8")
    predictions_frame.to_csv(predictions_path, index=False)
    joblib.dump(
        {
            "model": estimator,
            "feature_columns": _feature_columns(frame),
            "target_column": TARGET_COLUMN,
            "split": split,
            "random_state": random_state,
        },
        model_path,
    )

    return TrainResult(
        run_dir=run_dir,
        metrics_path=metrics_path,
        model_path=model_path,
        predictions_path=predictions_path,
        metrics=metrics,
    )
