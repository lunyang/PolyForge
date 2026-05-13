from __future__ import annotations

from experiments.tg_benchmark.dataset import load_bigsmiles_tg_csv
from experiments.tg_benchmark.splits import make_grouped_folds


def test_make_grouped_folds_is_deterministic_and_exhaustive():
    dataset = load_bigsmiles_tg_csv("bigsmiles-Tg.csv")

    folds_a = make_grouped_folds(dataset.frame, n_splits=5, seed=13)
    folds_b = make_grouped_folds(dataset.frame, n_splits=5, seed=13)

    assert folds_a == folds_b
    assert [fold["fold"] for fold in folds_a] == [0, 1, 2, 3, 4]
    test_rows = sorted(row for fold in folds_a for row in fold["test_indices"])
    assert test_rows == list(range(len(dataset.frame)))


def test_grouped_folds_do_not_split_structure_keys():
    dataset = load_bigsmiles_tg_csv("bigsmiles-Tg.csv")
    folds = make_grouped_folds(dataset.frame, n_splits=5, seed=13)

    for fold in folds:
        train_keys = set(dataset.frame.iloc[fold["train_indices"]]["structure_key"])
        test_keys = set(dataset.frame.iloc[fold["test_indices"]]["structure_key"])
        assert train_keys.isdisjoint(test_keys)


def test_grouped_folds_reject_too_many_splits():
    dataset = load_bigsmiles_tg_csv("bigsmiles-Tg.csv")

    try:
        make_grouped_folds(dataset.frame.head(3), n_splits=5, seed=13)
    except ValueError as exc:
        assert "n_splits" in str(exc)
    else:
        raise AssertionError("expected too many splits to fail")
