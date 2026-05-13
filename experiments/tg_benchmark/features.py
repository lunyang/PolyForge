from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from typing import Any

import pandas as pd
from rdkit import Chem
from rdkit.Chem import Descriptors

BASE_COLUMNS = ["row_index", "polymer_name", "smiles", "bigsmiles", "tg_k", "structure_key"]
BIGSMILES_CHAR_VOCAB = tuple(sorted(set("{}[]()<>$,:=\\/+-#0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz@")))


@dataclass(frozen=True)
class FeatureTable:
    frame: pd.DataFrame
    feature_columns: list[str]
    metadata: dict[str, Any]


def make_smiles_features(frame: pd.DataFrame) -> FeatureTable:
    rows: list[dict[str, Any]] = []
    failed_rows: list[int] = []

    for _, row in frame.reset_index(drop=True).iterrows():
        molecule = Chem.MolFromSmiles(_sanitize_polymer_smiles(row["smiles"]), sanitize=True)
        if molecule is None:
            failed_rows.append(int(row["row_index"]))
            descriptor_values = _empty_smiles_descriptors()
        else:
            descriptor_values = _smiles_descriptors(molecule)
        rows.append({**_base_row(row), **descriptor_values})

    feature_frame = pd.DataFrame(rows).reset_index(drop=True)
    feature_columns = sorted(column for column in feature_frame.columns if column.startswith("smiles."))
    return FeatureTable(
        frame=feature_frame[BASE_COLUMNS + feature_columns],
        feature_columns=feature_columns,
        metadata={
            "representation": "smiles_rdkit",
            "rows": len(feature_frame),
            "failed_row_indices": failed_rows,
        },
    )


def make_bigsmiles_char_features(frame: pd.DataFrame) -> FeatureTable:
    rows: list[dict[str, Any]] = []
    for _, row in frame.reset_index(drop=True).iterrows():
        bigsmiles = str(row["bigsmiles"])
        counts = Counter(bigsmiles)
        features: dict[str, Any] = {
            "bigsmiles.length": float(len(bigsmiles)),
            "bigsmiles.unique_chars": float(len(counts)),
        }
        for char in BIGSMILES_CHAR_VOCAB:
            features[f"bigsmiles.char_{_char_label(char)}"] = float(counts.get(char, 0))
        rows.append({**_base_row(row), **features})

    feature_frame = pd.DataFrame(rows).reset_index(drop=True)
    feature_columns = sorted(column for column in feature_frame.columns if column.startswith("bigsmiles."))
    return FeatureTable(
        frame=feature_frame[BASE_COLUMNS + feature_columns],
        feature_columns=feature_columns,
        metadata={
            "representation": "bigsmiles_char",
            "rows": len(feature_frame),
            "vocab_size": len(BIGSMILES_CHAR_VOCAB),
        },
    )


def _base_row(row: pd.Series) -> dict[str, Any]:
    return {column: row[column] for column in BASE_COLUMNS}


def _sanitize_polymer_smiles(smiles: str) -> str:
    return str(smiles).replace("*", "[H]")


def _smiles_descriptors(molecule: Chem.Mol) -> dict[str, float]:
    return {
        "smiles.mol_wt": float(Descriptors.MolWt(molecule)),
        "smiles.heavy_atom_count": float(Descriptors.HeavyAtomCount(molecule)),
        "smiles.num_valence_electrons": float(Descriptors.NumValenceElectrons(molecule)),
        "smiles.num_rotatable_bonds": float(Descriptors.NumRotatableBonds(molecule)),
        "smiles.ring_count": float(Descriptors.RingCount(molecule)),
        "smiles.tpsa": float(Descriptors.TPSA(molecule)),
    }


def _empty_smiles_descriptors() -> dict[str, float]:
    return {
        "smiles.mol_wt": 0.0,
        "smiles.heavy_atom_count": 0.0,
        "smiles.num_valence_electrons": 0.0,
        "smiles.num_rotatable_bonds": 0.0,
        "smiles.ring_count": 0.0,
        "smiles.tpsa": 0.0,
    }


def _char_label(char: str) -> str:
    if char.isalnum():
        return char
    return {
        "{": "lbrace",
        "}": "rbrace",
        "[": "lbracket",
        "]": "rbracket",
        "(": "lparen",
        ")": "rparen",
        "<": "lt",
        ">": "gt",
        "$": "dollar",
        ",": "comma",
        ":": "colon",
        "=": "eq",
        "\\": "backslash",
        "/": "slash",
        "+": "plus",
        "-": "minus",
        "#": "hash",
        "@": "at",
    }[char]
