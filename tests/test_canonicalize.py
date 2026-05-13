import json
import re

from polyforge.canonicalize.json_ir import canonicalize_ir, canonicalize_program, dumps_canonical_json
from polyforge.parser.ast_builder import build_ast
from polyforge.parser.parse import parse_polyforge_source


def _program(source: str):
    result = parse_polyforge_source(source, filename="fixture.pdsl")
    assert result.diagnostics == []
    assert result.tree is not None
    return build_ast(result.tree)


def test_canonical_id_format_hashing_and_unit_normalization():
    canonical = canonicalize_program(
        _program(
            """
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
                distribution: unknown
              }
              stereochemistry {
                tacticity: unknown
              }
              predict Tg {
                method: DSC
                heating_rate: 10 K/min
                pressure: 1 atm
                sample_state: amorphous
              }
            }
            """
        )
    )

    assert re.fullmatch(r"PolyForge:v0\.1:sha256:[0-9a-f]{64}", canonical["canonical_id"])
    assert re.fullmatch(r"sha256:[0-9a-f]{64}", canonical["structure_hash"])
    assert canonical["molecular_weight"]["Mn_g_mol"] == 120000.0
    assert canonical["targets"][0]["heating_rate_K_per_min"] == 10.0
    assert canonical["targets"][0]["pressure_Pa"] == 101325.0


def test_preserves_explicit_unknown_and_inferred_provenance():
    canonical = canonicalize_program(
        _program(
            """
            polymer PMMA {
              monomer MMA {
                smiles: "C=C(C)C(=O)OC"
                polymerization: vinyl
                attach: inferred
              }
              architecture: linear
              sequence: homopolymer(MMA)
              molecular_weight {
                distribution: unknown
              }
              stereochemistry {
                tacticity: unknown
              }
            }
            """
        )
    )

    assert canonical["molecular_weight"]["distribution"] == {"value": None, "explicit_unknown": True}
    assert canonical["stereochemistry"]["tacticity"] == {"value": None, "explicit_unknown": True}
    assert canonical["monomers"]["M0"]["attach"] == [0, 1]
    assert canonical["monomers"]["M0"]["provenance"] == {"attach": "inferred"}


def test_canonical_sequence_forms_for_supported_sequence_kinds():
    random = canonicalize_program(
        _program(
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
    )
    alternating = canonicalize_program(
        _program(
            """
            polymer P_alt {
              monomer MMA {
                smiles: "C=C(C)C(=O)OC"
                polymerization: vinyl
              }
              monomer BA {
                smiles: "C=CC(=O)OCCCC"
                polymerization: vinyl
              }
              architecture: linear
              sequence: alternating_copolymer(MMA, BA)
            }
            """
        )
    )
    block = canonicalize_program(
        _program(
            """
            polymer P_block {
              monomer Styrene {
                smiles: "C=CC1=CC=CC=C1"
                polymerization: vinyl
              }
              monomer MMA {
                smiles: "C=C(C)C(=O)OC"
                polymerization: vinyl
              }
              architecture: linear
              sequence: block_copolymer {
                blocks: [
                  block(Styrene, DP=100),
                  block(MMA, DP=80)
                ]
              }
            }
            """
        )
    )

    assert random["sequence"] == {
        "type": "random_copolymer",
        "units": ["M1", "M0"],
        "composition": {"M0": 0.3, "M1": 0.7},
    }
    assert alternating["sequence"] == {
        "type": "alternating_copolymer",
        "units": ["M1", "M0"],
    }
    assert block["sequence"] == {
        "type": "block_copolymer",
        "blocks": [{"monomer": "M1", "DP": 100}, {"monomer": "M0", "DP": 80}],
    }


def test_canonical_json_round_trip_is_idempotent_and_stable():
    canonical = canonicalize_program(
        _program(
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
    )

    dumped = dumps_canonical_json(canonical)
    assert not dumped.endswith("\n")
    loaded = json.loads(dumped)

    assert canonicalize_ir(loaded) == canonical
    assert dumps_canonical_json(canonicalize_ir(loaded)) == dumped
