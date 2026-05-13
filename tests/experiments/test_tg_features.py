from __future__ import annotations

from experiments.tg_benchmark.dataset import load_bigsmiles_tg_csv
from experiments.tg_benchmark.features import make_bigsmiles_char_features, make_smiles_features


def test_smiles_features_are_numeric_and_row_aligned():
    dataset = load_bigsmiles_tg_csv("bigsmiles-Tg.csv")

    features = make_smiles_features(dataset.frame.head(8))

    assert len(features.frame) == 8
    assert features.frame.index.tolist() == list(range(8))
    assert all(name.startswith("smiles.") for name in features.feature_columns)
    assert features.frame[features.feature_columns].notna().all().all()
    assert features.metadata["representation"] == "smiles_rdkit"


def test_bigsmiles_char_features_are_numeric_and_stable():
    dataset = load_bigsmiles_tg_csv("bigsmiles-Tg.csv")

    first = make_bigsmiles_char_features(dataset.frame.head(8))
    second = make_bigsmiles_char_features(dataset.frame.head(8))

    assert first.feature_columns == second.feature_columns
    assert first.frame[first.feature_columns].equals(second.frame[second.feature_columns])
    assert "bigsmiles.length" in first.feature_columns
    assert all(name.startswith("bigsmiles.") for name in first.feature_columns)
    assert first.metadata["representation"] == "bigsmiles_char"


def test_feature_builders_preserve_target_and_structure_columns():
    dataset = load_bigsmiles_tg_csv("bigsmiles-Tg.csv")

    features = make_bigsmiles_char_features(dataset.frame.head(3))

    assert list(features.frame["row_index"]) == [0, 1, 2]
    assert list(features.frame["tg_k"]) == [130.0, 152.0, 171.0]
    assert list(features.frame["structure_key"]) == list(dataset.frame.head(3)["structure_key"])
