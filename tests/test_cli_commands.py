from __future__ import annotations

import csv
import json
import subprocess
import sys
from pathlib import Path

from polyforge.canonicalize.json_ir import canonicalize_program, dumps_canonical_json
from polyforge.emit.bigsmiles import export_bigsmiles
from polyforge.emit.descriptors import descriptor_row
from polyforge.emit.tokens import token_sequence
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


def _canonical(source: str):
    return canonicalize_program(_program(source))


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


PMMA_STRICT = """
polymer PMMA {
  monomer MMA {
    smiles: "C=C(C)C(=O)OC"
    polymerization: vinyl
    attach: [0, 1]
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


BAD_ARCHITECTURE = """
polymer BadArchitecture {
  monomer MMA {
    smiles: "C=C(C)C(=O)OC"
    polymerization: vinyl
  }
  architecture: branched
  sequence: homopolymer(MMA)
}
"""


def test_validate_accepts_pdsl_and_canonical_json(tmp_path):
    canonical = _canonical(PMMA_STRICT)

    pdsl_path = tmp_path / "pmma.pdsl"
    json_path = tmp_path / "pmma.json"
    pdsl_path.write_text(PMMA_STRICT, encoding="utf-8")
    json_path.write_text(dumps_canonical_json(canonical), encoding="utf-8")

    for path in (pdsl_path, json_path):
        result = _run_cli("validate", str(path))

        assert result.returncode == 0
        assert "OK" in result.stdout
        assert result.stderr == ""


def test_validate_reports_semantic_errors(tmp_path):
    path = tmp_path / "bad.pdsl"
    path.write_text(BAD_ARCHITECTURE, encoding="utf-8")

    result = _run_cli("validate", str(path))

    assert result.returncode != 0
    assert "unsupported_architecture" in result.stderr


def test_export_backends_emit_expected_output(tmp_path):
    canonical = _canonical(PMMA)
    path = tmp_path / "pmma.pdsl"
    path.write_text(PMMA, encoding="utf-8")

    expectations = {
        "json": dumps_canonical_json(canonical),
        "tokens": "\n".join(token_sequence(canonical)),
        "descriptors": json.dumps(descriptor_row(canonical), ensure_ascii=False, sort_keys=True),
        "bigsmiles": export_bigsmiles(canonical),
    }

    for mode, expected in expectations.items():
        result = _run_cli("export", str(path), "--to", mode)

        assert result.returncode == 0
        assert result.stdout.strip() == expected
        assert result.stderr == ""


def test_validate_rejects_structurally_invalid_canonical_json(tmp_path):
    canonical = _canonical(PMMA_STRICT)
    canonical.pop("name")
    path = tmp_path / "invalid-canonical.json"
    path.write_text(json.dumps(canonical), encoding="utf-8")

    result = _run_cli("validate", str(path))

    assert result.returncode != 0
    assert "invalid_canonical_json" in result.stderr
    assert "missing required canonical IR field: name" in result.stderr


def test_schema_show_outputs_canonical_ir_schema():
    result = _run_cli("schema", "show", "v0.1")

    assert result.returncode == 0
    payload = json.loads(result.stdout)
    assert payload["$id"] == "https://polyforge.dev/schemas/canonical-ir-v0.1.schema.json"
    assert payload["properties"]["schema"]["const"] == "polyforge.v0.1"
