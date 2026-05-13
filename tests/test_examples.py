from __future__ import annotations

from pathlib import Path

from polyforge.pipeline import load_source


REPO_ROOT = Path(__file__).resolve().parents[1]


VALID_EXAMPLES = [
    REPO_ROOT / "examples" / "pmma.pdsl",
    REPO_ROOT / "examples" / "random_copolymer.pdsl",
    REPO_ROOT / "examples" / "block_copolymer.pdsl",
]

INVALID_EXAMPLES = {
    REPO_ROOT / "examples" / "invalid" / "duplicate_name.pdsl": "polyforge.semantic.duplicate_monomer",
    REPO_ROOT / "examples" / "invalid" / "bad_composition.pdsl": "polyforge.semantic.invalid_composition",
    REPO_ROOT / "examples" / "invalid" / "invalid_smiles.pdsl": "polyforge.chemistry.invalid_smiles",
}


def test_valid_examples_compile_to_canonical_ir():
    for path in VALID_EXAMPLES:
        artifact = load_source(path)
        assert artifact.errors == []
        assert artifact.canonical_ir is not None


def test_invalid_examples_report_expected_errors():
    for path, expected_code in INVALID_EXAMPLES.items():
        artifact = load_source(path)
        assert artifact.canonical_ir is None
        assert expected_code in {diagnostic.code for diagnostic in artifact.errors}
