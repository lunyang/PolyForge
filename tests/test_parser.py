from polyforge.parser.ast_builder import build_ast
from polyforge.parser.parse import parse_polyforge_source


VALID_PROGRAM = """
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
    distribution: lognormal
  }

  stereochemistry {
    tacticity: atactic
  }

  predict Tg {
    method: DSC
    heating_rate: 10 K/min
    sample_state: amorphous
  }
}
"""


INVALID_PROGRAM = """
polymer Bad {
  monomer M1 {
    smiles: "C=C"
    polymerization: vinyl
    attach: inferred
  }

  architecture: linear
  sequence: homopolymer(M1)
"""


def test_parse_and_build_ast_for_valid_program():
    result = parse_polyforge_source(VALID_PROGRAM, filename="pmma.pdsl")

    assert result.tree is not None
    assert result.diagnostics == []

    program = build_ast(result.tree)

    assert program.name == "PMMA"
    assert list(program.monomers) == ["MMA"]
    assert program.architecture == "linear"
    assert program.sequence.kind == "homopolymer"
    assert program.sequence.monomer == "MMA"


def test_parse_reports_syntax_error_for_invalid_program():
    result = parse_polyforge_source(INVALID_PROGRAM, filename="bad.pdsl")

    assert result.tree is None
    assert result.diagnostics
    assert result.diagnostics[0].severity == "error"
    assert result.diagnostics[0].stage == "syntax"
