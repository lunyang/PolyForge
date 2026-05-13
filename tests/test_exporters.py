import pytest

from polyforge.canonicalize.json_ir import canonicalize_program, dumps_canonical_json
from polyforge.emit.bigsmiles import UnsupportedBigSMILESExport, export_bigsmiles
from polyforge.emit.descriptors import descriptor_row
from polyforge.emit.json import export_json
from polyforge.emit.tokens import token_sequence
from polyforge.parser.ast_builder import build_ast
from polyforge.parser.parse import parse_polyforge_source


def _canonical(source: str):
    result = parse_polyforge_source(source, filename="fixture.pdsl")
    assert result.diagnostics == []
    assert result.tree is not None
    return canonicalize_program(build_ast(result.tree))


def test_json_export_matches_canonical_serialization():
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

    assert export_json(canonical) == dumps_canonical_json(canonical)


def test_token_sequence_is_deterministic_and_uses_canonical_ids():
    canonical = _canonical(
        """
        polymer P_random {
          monomer BA {
            smiles: "C=CC(=O)OCCCC"
            polymerization: vinyl
          }
          monomer MMA {
            smiles: "C=C(C)C(=O)OC"
            polymerization: vinyl
          }
          architecture: linear
          sequence: random_copolymer {
            units: [MMA, BA]
            composition: {MMA: 0.70, BA: 0.30}
          }
        }
        """
    )

    assert token_sequence(canonical) == [
        "polymer:P_random",
        "architecture:linear",
        "monomer:M0:C=CC(=O)OCCCC",
        "monomer:M1:C=C(C)C(=O)OC",
        "sequence:random_copolymer",
        "unit:M1",
        "unit:M0",
        "composition:M0:0.3",
        "composition:M1:0.7",
    ]


def test_descriptor_export_is_stable_and_numeric():
    canonical = _canonical(
        """
        polymer PMMA {
          monomer MMA {
            smiles: "C=C(C)C(=O)OC"
            polymerization: vinyl
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
    )

    assert descriptor_row(canonical) == {
        "canonical_id": canonical["canonical_id"],
        "descriptor.dispersity": 1.6,
        "descriptor.monomer_count": 1,
        "descriptor.Mn_g_mol": 120000.0,
        "descriptor.sequence_alternating_copolymer": 0,
        "descriptor.sequence_block_copolymer": 0,
        "descriptor.sequence_homopolymer": 1,
        "descriptor.sequence_random_copolymer": 0,
        "descriptor.target_count": 1,
        "structure_hash": canonical["structure_hash"],
    }


def test_bigsmiles_export_support_matrix():
    homopolymer = _canonical(
        """
        polymer PE {
          monomer E {
            smiles: "C=C"
            polymerization: vinyl
          }
          architecture: linear
          sequence: homopolymer(E)
        }
        """
    )
    random = _canonical(
        """
        polymer P_random {
          monomer E {
            smiles: "C=C"
            polymerization: vinyl
          }
          monomer P {
            smiles: "C=CC"
            polymerization: vinyl
          }
          architecture: linear
          sequence: random_copolymer {
            units: [E, P]
            composition: {E: 0.4, P: 0.6}
          }
        }
        """
    )

    assert export_bigsmiles(homopolymer) == "{[<]C=C[>]}"
    assert export_bigsmiles(random) == "{[<]C=C:0.4[>],[<]C=CC:0.6[>]}"

    unsupported = dict(homopolymer)
    unsupported["sequence"] = {"type": "gradient_copolymer"}
    with pytest.raises(UnsupportedBigSMILESExport):
        export_bigsmiles(unsupported)
