from __future__ import annotations

from polyforge.canonicalize.schema import load_canonical_ir_schema, validate_canonical_ir
from polyforge.canonicalize.json_ir import canonicalize_program
from polyforge.parser.ast_builder import build_ast
from polyforge.parser.parse import parse_polyforge_source


def _canonical(source: str):
    parsed = parse_polyforge_source(source, filename="schema_fixture.pdsl")
    assert parsed.diagnostics == []
    assert parsed.tree is not None
    return canonicalize_program(build_ast(parsed.tree))


def test_loads_versioned_canonical_ir_json_schema():
    schema = load_canonical_ir_schema()

    assert schema["$schema"] == "https://json-schema.org/draft/2020-12/schema"
    assert schema["title"] == "PolyForge Canonical IR v0.1"
    assert schema["properties"]["schema"]["const"] == "polyforge.v0.1"


def test_validate_canonical_ir_rejects_missing_required_fields():
    canonical = _canonical(
        """
        polymer PMMA {
          monomer MMA {
            smiles: "C=C(C)C(=O)OC"
            polymerization: vinyl
          }
          architecture: linear
          sequence: homopolymer(MMA)
        }
        """
    )
    canonical.pop("name")

    errors = validate_canonical_ir(canonical)

    assert errors == ["missing required canonical IR field: name"]


def test_validate_canonical_ir_rejects_malformed_hash_fields():
    canonical = _canonical(
        """
        polymer PMMA {
          monomer MMA {
            smiles: "C=C(C)C(=O)OC"
            polymerization: vinyl
          }
          architecture: linear
          sequence: homopolymer(MMA)
        }
        """
    )
    canonical["structure_hash"] = "sha256:not-a-valid-digest"
    canonical["canonical_id"] = "PolyForge:v0.1:sha256:not-a-valid-digest"

    errors = validate_canonical_ir(canonical)

    assert "canonical IR field structure_hash has invalid format" in errors
    assert "canonical IR field canonical_id has invalid format" in errors
