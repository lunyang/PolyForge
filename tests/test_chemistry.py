from polyforge.check.chemistry import check_program_chemistry, rdkit_version
from polyforge.parser.ast_builder import build_ast
from polyforge.parser.parse import parse_polyforge_source


def _program(source: str):
    result = parse_polyforge_source(source, filename="fixture.pdsl")
    assert result.diagnostics == []
    assert result.tree is not None
    return build_ast(result.tree)


def test_valid_monomer_smiles_yields_canonical_smiles_and_rdkit_version():
    result = check_program_chemistry(
        _program(
            """
            polymer PMMA {
              monomer MMA {
                smiles: "C=C(C)C(=O)OC"
                polymerization: vinyl
                attach: [0, 1]
              }
              architecture: linear
              sequence: homopolymer(MMA)
            }
            """
        ),
        filename="fixture.pdsl",
    )

    assert result.errors == []
    assert result.canonical_smiles["MMA"] == "C=C(C)C(=O)OC"
    assert result.rdkit_version == rdkit_version()
    assert result.rdkit_version.startswith("2025.09")


def test_invalid_monomer_smiles_reports_chemistry_error():
    result = check_program_chemistry(
        _program(
            """
            polymer BadSmiles {
              monomer Bad {
                smiles: "C1CC"
                polymerization: vinyl
              }
              architecture: linear
              sequence: homopolymer(Bad)
            }
            """
        ),
        filename="fixture.pdsl",
    )

    assert [diagnostic.code for diagnostic in result.errors] == ["polyforge.chemistry.invalid_smiles"]


def test_inferred_attachment_points_emit_warning_and_are_materialized():
    result = check_program_chemistry(
        _program(
            """
            polymer Ethylene {
              monomer E {
                smiles: "C=C"
                polymerization: vinyl
                attach: inferred
              }
              architecture: linear
              sequence: homopolymer(E)
            }
            """
        ),
        filename="fixture.pdsl",
    )

    assert result.errors == []
    assert [diagnostic.code for diagnostic in result.warnings] == ["polyforge.chemistry.inferred_attach"]
    assert result.attachments["E"] == [0, 1]
