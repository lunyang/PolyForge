from __future__ import annotations

from experiments.tg_benchmark.dataset import audit_dataset, load_bigsmiles_tg_csv


def test_load_bigsmiles_tg_dataset_normalizes_columns():
    dataset = load_bigsmiles_tg_csv("bigsmiles-Tg.csv")

    assert list(dataset.frame.columns) == [
        "row_index",
        "polymer_name",
        "smiles",
        "bigsmiles",
        "tg_k",
        "structure_key",
    ]
    assert len(dataset.frame) == 304
    assert dataset.source_path.name == "bigsmiles-Tg.csv"
    assert dataset.frame["tg_k"].notna().all()
    assert dataset.frame["structure_key"].str.fullmatch(r"sha256:[0-9a-f]{64}").all()


def test_dataset_audit_reports_expected_counts():
    dataset = load_bigsmiles_tg_csv("bigsmiles-Tg.csv")

    audit = audit_dataset(dataset.frame)

    assert audit["rows"] == 304
    assert audit["target_missing_or_bad"] == 0
    assert audit["tg_min_k"] == 130.0
    assert audit["tg_max_k"] == 685.0
    assert audit["tg_mean_k"] == 360.566
    assert audit["tg_median_k"] == 359.0
    assert audit["tg_population_std_k"] == 114.546
    assert audit["unique_polymer_names"] == 276
    assert audit["exact_duplicate_rows"] == 0
    assert audit["duplicate_structure_pairs"] == 0
    assert audit["duplicate_smiles"] == 2
    assert audit["duplicate_bigsmiles"] == 2
