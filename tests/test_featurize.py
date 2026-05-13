from __future__ import annotations

import csv
import subprocess
import sys
from pathlib import Path

from polyforge.canonicalize.json_ir import canonicalize_program, dumps_canonical_json
from polyforge.emit.descriptors import descriptor_row
from polyforge.parser.ast_builder import build_ast
from polyforge.parser.parse import parse_polyforge_source


REPO_ROOT = Path(__file__).resolve().parents[1]


def _run_cli(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "polyforge", *args],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
    )


def _program(source: str):
    result = parse_polyforge_source(source, filename="fixture.pdsl")
    assert result.diagnostics == []
    assert result.tree is not None
    return build_ast(result.tree)


PMMA = """
polymer PMMA {
  monomer MMA {
    smiles: "C=C(C)C(=O)OC"
    polymerization: vinyl
    attach: inferred
  }
  architecture: linear
  sequence: homopolymer(MMA)
  molecular_weight {
    Mn: 120000 g/mol
    dispersity: 1.6
  }
  predict Tg {
    value: 390 K
  }
}
"""


PBA = """
polymer PBA {
  monomer BA {
    smiles: "C=CC(=O)OCCCC"
    polymerization: vinyl
    attach: inferred
  }
  architecture: linear
  sequence: homopolymer(BA)
  molecular_weight {
    Mn: 80000 g/mol
    dispersity: 2.1
  }
  predict Tg {
    value: 250 K
  }
}
"""


def _read_csv(path: Path):
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        return reader.fieldnames, list(reader)


def test_featurize_writes_stable_csv_with_fixed_prefix(tmp_path):
    pdsl_path = tmp_path / "pmma.pdsl"
    json_path = tmp_path / "pba.json"
    out_path = tmp_path / "features.csv"

    pdsl_path.write_text(PMMA, encoding="utf-8")
    json_path.write_text(dumps_canonical_json(canonicalize_program(_program(PBA))), encoding="utf-8")

    result = _run_cli(
        "featurize",
        "--input",
        str(pdsl_path),
        "--input",
        str(json_path),
        "--target",
        "Tg",
        "--out",
        str(out_path),
    )

    assert result.returncode == 0
    assert out_path.exists()

    fieldnames, rows = _read_csv(out_path)
    assert fieldnames is not None
    assert fieldnames[:7] == [
        "canonical_id",
        "source_file",
        "source_format",
        "structure_hash",
        "target_property",
        "target_value",
        "target_units",
    ]

    descriptor_keys = sorted(k for k in descriptor_row(canonicalize_program(_program(PMMA))) if k not in {"canonical_id", "structure_hash"})
    assert fieldnames[7:] == descriptor_keys

    assert [row["source_format"] for row in rows] == ["pdsl", "canonical_json"]
    assert [row["target_property"] for row in rows] == ["Tg", "Tg"]
    assert [row["target_units"] for row in rows] == ["K", "K"]
    assert [float(row["target_value"]) for row in rows] == [390.0, 250.0]


def test_featurize_supports_inputs_dir(tmp_path):
    inputs_dir = tmp_path / "inputs"
    inputs_dir.mkdir()
    out_path = tmp_path / "features.csv"

    (inputs_dir / "pmma.pdsl").write_text(PMMA, encoding="utf-8")

    result = _run_cli(
        "featurize",
        "--inputs-dir",
        str(inputs_dir),
        "--target",
        "Tg",
        "--out",
        str(out_path),
    )

    assert result.returncode == 0
    _, rows = _read_csv(out_path)
    assert len(rows) == 1
