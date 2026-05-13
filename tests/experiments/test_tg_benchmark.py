from __future__ import annotations

import csv
import json
import subprocess
import sys

from experiments.tg_benchmark.benchmark import run_tg_benchmark


def test_run_tg_benchmark_writes_required_artifacts(tmp_path):
    result = run_tg_benchmark(
        dataset_path="bigsmiles-Tg.csv",
        output_dir=tmp_path,
        representations=["bigsmiles_char"],
        models=["mean", "random_forest"],
        n_splits=5,
        seed=13,
    )

    assert (tmp_path / "dataset_audit.json").exists()
    assert (tmp_path / "splits.json").exists()
    assert (tmp_path / "metrics.json").exists()
    assert (tmp_path / "predictions.csv").exists()
    assert result["dataset"]["rows"] == 304

    metrics = json.loads((tmp_path / "metrics.json").read_text(encoding="utf-8"))
    assert {entry["model"] for entry in metrics["runs"]} == {"mean", "random_forest"}
    assert {entry["representation"] for entry in metrics["runs"]} == {"bigsmiles_char"}

    with (tmp_path / "predictions.csv").open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    assert len(rows) == 304 * 2
    assert {"representation", "model", "fold", "row_index", "tg_k", "prediction"}.issubset(rows[0])


def test_tg_benchmark_cli_writes_outputs(tmp_path):
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "experiments.tg_benchmark.cli",
            "--dataset",
            "bigsmiles-Tg.csv",
            "--out",
            str(tmp_path),
            "--representation",
            "bigsmiles_char",
            "--model",
            "mean",
        ],
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
    assert str(tmp_path) in result.stdout
    assert (tmp_path / "metrics.json").exists()
