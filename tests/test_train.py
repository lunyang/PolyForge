from __future__ import annotations

import csv
import json
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


def _run_cli(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "polyforge", *args],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
    )


def _feature_rows(missing_target: bool = False, non_numeric_target: bool = False):
    descriptor_columns = [
        "descriptor.Mn_g_mol",
        "descriptor.dispersity",
        "descriptor.monomer_count",
        "descriptor.sequence_alternating_copolymer",
        "descriptor.sequence_block_copolymer",
        "descriptor.sequence_homopolymer",
        "descriptor.sequence_random_copolymer",
        "descriptor.target_count",
    ]

    rows = []
    for index in range(5):
        row = {
            "canonical_id": f"PolyForge:v0.1:sha256:{index:064x}",
            "source_file": f"sample_{index}.pdsl",
            "source_format": "pdsl",
            "structure_hash": f"sha256:{index:064x}",
            "target_property": "Tg",
            "target_units": "K",
            "descriptor.Mn_g_mol": float(10000 * (index + 1)),
            "descriptor.dispersity": 1.1 + index * 0.1,
            "descriptor.monomer_count": 1,
            "descriptor.sequence_alternating_copolymer": 0,
            "descriptor.sequence_block_copolymer": 0,
            "descriptor.sequence_homopolymer": 1,
            "descriptor.sequence_random_copolymer": 0,
            "descriptor.target_count": 1,
        }
        if not missing_target:
            row["target_value"] = "oops" if non_numeric_target and index == 0 else float(100 + index * 10)
        rows.append(row)
    return rows, descriptor_columns


def _write_feature_csv(path: Path, *, missing_target: bool = False, non_numeric_target: bool = False) -> None:
    rows, descriptor_columns = _feature_rows(
        missing_target=missing_target,
        non_numeric_target=non_numeric_target,
    )
    fieldnames = [
        "canonical_id",
        "source_file",
        "source_format",
        "structure_hash",
        "target_property",
        "target_value",
        "target_units",
        *descriptor_columns,
    ]
    if missing_target:
        fieldnames.remove("target_value")

    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def test_train_writes_artifacts_for_supported_models(tmp_path):
    feature_csv = tmp_path / "features.csv"
    _write_feature_csv(feature_csv)

    for model in ("mean", "linear_regression", "random_forest"):
        run_dir = tmp_path / model
        result = _run_cli(
            "train",
            str(feature_csv),
            "--model",
            model,
            "--run-dir",
            str(run_dir),
        )

        assert result.returncode == 0
        assert (run_dir / "metrics.json").exists()
        assert (run_dir / "model.joblib").exists()
        assert (run_dir / "predictions.csv").exists()

        metrics = json.loads((run_dir / "metrics.json").read_text(encoding="utf-8"))
        assert metrics["model"] == model
        assert metrics["split"] == "grouped"
        assert metrics["target_column"] == "target_value"
        assert metrics["folds"] == 5

        with (run_dir / "predictions.csv").open(newline="", encoding="utf-8") as handle:
            rows = list(csv.DictReader(handle))
        assert len(rows) == 5


def test_train_rejects_missing_target_column(tmp_path):
    feature_csv = tmp_path / "features.csv"
    _write_feature_csv(feature_csv, missing_target=True)

    result = _run_cli("train", str(feature_csv), "--run-dir", str(tmp_path / "run"))

    assert result.returncode != 0
    assert "target_value" in result.stderr


def test_train_rejects_nonnumeric_target_values(tmp_path):
    feature_csv = tmp_path / "features.csv"
    _write_feature_csv(feature_csv, non_numeric_target=True)

    result = _run_cli("train", str(feature_csv), "--run-dir", str(tmp_path / "run"))

    assert result.returncode != 0
    assert "numeric" in result.stderr
