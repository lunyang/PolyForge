import pytest

from polyforge.check.semantics import check_program, check_programs
from polyforge.parser.ast_builder import build_ast
from polyforge.parser.parse import parse_polyforge_source


def _program(source: str):
    result = parse_polyforge_source(source, filename="fixture.pdsl")
    assert result.diagnostics == []
    assert result.tree is not None
    return build_ast(result.tree)


def _codes(source: str) -> set[str]:
    return {diagnostic.code for diagnostic in check_program(_program(source), filename="fixture.pdsl")}


def test_reports_duplicate_polymer_names_across_file_programs():
    first = _program(
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
    second = _program(
        """
        polymer PMMA {
          monomer BA {
            smiles: "C=CC(=O)OCCCC"
            polymerization: vinyl
          }
          architecture: linear
          sequence: homopolymer(BA)
        }
        """
    )

    diagnostics = check_programs([first, second], filename="fixture.pdsl")

    assert [diagnostic.code for diagnostic in diagnostics] == ["polyforge.semantic.duplicate_polymer"]


def test_reports_duplicate_monomer_names_before_mapping_collapses_them():
    codes = _codes(
        """
        polymer DuplicateMonomer {
          monomer MMA {
            smiles: "C=C(C)C(=O)OC"
            polymerization: vinyl
          }
          monomer MMA {
            smiles: "C=C"
            polymerization: vinyl
          }
          architecture: linear
          sequence: homopolymer(MMA)
        }
        """
    )

    assert "polyforge.semantic.duplicate_monomer" in codes


@pytest.mark.parametrize(
    ("source", "expected_code"),
    [
        (
            """
            polymer UndefinedHomopolymer {
              monomer MMA {
                smiles: "C=C(C)C(=O)OC"
                polymerization: vinyl
              }
              architecture: linear
              sequence: homopolymer(BA)
            }
            """,
            "polyforge.semantic.undefined_monomer",
        ),
        (
            """
            polymer Branched {
              monomer MMA {
                smiles: "C=C(C)C(=O)OC"
                polymerization: vinyl
              }
              architecture: branched
              sequence: homopolymer(MMA)
            }
            """,
            "polyforge.semantic.unsupported_architecture",
        ),
        (
            """
            polymer BadComposition {
              monomer MMA {
                smiles: "C=C(C)C(=O)OC"
                polymerization: vinyl
              }
              monomer BA {
                smiles: "C=CC(=O)OCCCC"
                polymerization: vinyl
              }
              architecture: linear
              sequence: random_copolymer {
                units: [MMA, BA]
                composition: {MMA: 0.70, BA: 0.20}
              }
            }
            """,
            "polyforge.semantic.invalid_composition",
        ),
        (
            """
            polymer MissingBlockDp {
              monomer MMA {
                smiles: "C=C(C)C(=O)OC"
                polymerization: vinyl
              }
              monomer BA {
                smiles: "C=CC(=O)OCCCC"
                polymerization: vinyl
              }
              architecture: linear
              sequence: block_copolymer {
                blocks: [
                  block(MMA),
                  block(BA, DP=20)
                ]
              }
            }
            """,
            "polyforge.semantic.invalid_block_dp",
        ),
        (
            """
            polymer polymer {
              monomer MMA {
                smiles: "C=C(C)C(=O)OC"
                polymerization: vinyl
              }
              architecture: linear
              sequence: homopolymer(MMA)
            }
            """,
            "polyforge.semantic.reserved_identifier",
        ),
    ],
)
def test_reports_semantic_rule_violations(source, expected_code):
    assert expected_code in _codes(source)


def test_accepts_random_composition_at_tolerance_boundary():
    diagnostics = check_program(
        _program(
            """
            polymer ToleratedComposition {
              monomer MMA {
                smiles: "C=C(C)C(=O)OC"
                polymerization: vinyl
              }
              monomer BA {
                smiles: "C=CC(=O)OCCCC"
                polymerization: vinyl
              }
              architecture: linear
              sequence: random_copolymer {
                units: [MMA, BA]
                composition: {MMA: 0.7000004, BA: 0.2999995}
              }
            }
            """
        ),
        filename="fixture.pdsl",
    )

    assert "polyforge.semantic.invalid_composition" not in {diagnostic.code for diagnostic in diagnostics}
