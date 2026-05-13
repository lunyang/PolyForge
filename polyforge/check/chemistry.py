from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from rdkit import Chem, rdBase
from rdkit.Chem.rdchem import BondType

from polyforge.check.diagnostics import Diagnostic, Severity
from polyforge.ir.nodes import MonomerDef, PolymerProgram, Quantity


@dataclass(frozen=True)
class ChemistryResult:
    diagnostics: list[Diagnostic] = field(default_factory=list)
    canonical_smiles: dict[str, str] = field(default_factory=dict)
    attachments: dict[str, list[int]] = field(default_factory=dict)
    rdkit_version: str = ""

    @property
    def errors(self) -> list[Diagnostic]:
        return [diagnostic for diagnostic in self.diagnostics if diagnostic.severity == "error"]

    @property
    def warnings(self) -> list[Diagnostic]:
        return [diagnostic for diagnostic in self.diagnostics if diagnostic.severity == "warning"]


def rdkit_version() -> str:
    return rdBase.rdkitVersion


def _diagnostic(
    code: str,
    severity: Severity,
    message: str,
    *,
    filename: str | None,
    path: str | None,
) -> Diagnostic:
    return Diagnostic(
        code=code,
        severity=severity,
        message=message,
        file=filename,
        path=path,
        stage="chemistry",
    )


def _numeric_atom_index(value: Any) -> int | None:
    if isinstance(value, Quantity):
        value = value.value
    if isinstance(value, int):
        return value
    if isinstance(value, float) and value.is_integer():
        return int(value)
    return None


def _explicit_attach_points(attach: Any) -> list[int] | None:
    if attach is None or attach == "inferred":
        return None
    if not isinstance(attach, list):
        return None

    points: list[int] = []
    for item in attach:
        index = _numeric_atom_index(item)
        if index is None:
            return None
        points.append(index)
    return points


def _infer_vinyl_attachment_points(mol: Chem.Mol) -> list[int] | None:
    carbon_double_bonds: list[tuple[int, int]] = []
    for bond in mol.GetBonds():
        begin = bond.GetBeginAtom()
        end = bond.GetEndAtom()
        if (
            bond.GetBondType() == BondType.DOUBLE
            and begin.GetAtomicNum() == 6
            and end.GetAtomicNum() == 6
            and not bond.GetIsAromatic()
        ):
            carbon_double_bonds.append((begin.GetIdx(), end.GetIdx()))

    if len(carbon_double_bonds) != 1:
        return None
    return sorted(carbon_double_bonds[0])


def _check_attach(
    monomer: MonomerDef,
    mol: Chem.Mol,
    diagnostics: list[Diagnostic],
    *,
    filename: str | None,
) -> list[int] | None:
    path = f"monomers.{monomer.name}.attach"
    if monomer.attach == "inferred":
        inferred = _infer_vinyl_attachment_points(mol)
        if inferred is None:
            diagnostics.append(
                _diagnostic(
                    "polyforge.chemistry.ambiguous_attach",
                    "error",
                    f"attachment points for monomer {monomer.name!r} could not be inferred unambiguously",
                    filename=filename,
                    path=path,
                )
            )
            return None

        diagnostics.append(
            _diagnostic(
                "polyforge.chemistry.inferred_attach",
                "warning",
                f"attachment points for monomer {monomer.name!r} were inferred",
                filename=filename,
                path=path,
            )
        )
        return inferred

    explicit = _explicit_attach_points(monomer.attach)
    if explicit is None:
        return None

    atom_count = mol.GetNumAtoms()
    invalid = [index for index in explicit if index < 0 or index >= atom_count]
    if invalid:
        diagnostics.append(
            _diagnostic(
                "polyforge.chemistry.invalid_attach",
                "error",
                f"attachment points for monomer {monomer.name!r} are outside the atom index range",
                filename=filename,
                path=path,
            )
        )
        return None

    return explicit


def _check_monomer(
    monomer: MonomerDef,
    diagnostics: list[Diagnostic],
    canonical_smiles: dict[str, str],
    attachments: dict[str, list[int]],
    *,
    filename: str | None,
) -> None:
    mol = Chem.MolFromSmiles(monomer.smiles, sanitize=True)
    if mol is None:
        diagnostics.append(
            _diagnostic(
                "polyforge.chemistry.invalid_smiles",
                "error",
                f"SMILES for monomer {monomer.name!r} could not be parsed by RDKit",
                filename=filename,
                path=f"monomers.{monomer.name}.smiles",
            )
        )
        return

    canonical_smiles[monomer.name] = Chem.MolToSmiles(mol, isomericSmiles=True, canonical=True)
    attach = _check_attach(monomer, mol, diagnostics, filename=filename)
    if attach is not None:
        attachments[monomer.name] = attach


def check_program_chemistry(program: PolymerProgram, filename: str | None = None) -> ChemistryResult:
    diagnostics: list[Diagnostic] = []
    canonical_smiles: dict[str, str] = {}
    attachments: dict[str, list[int]] = {}

    for monomer in program.monomer_definitions or tuple(program.monomers.values()):
        _check_monomer(
            monomer,
            diagnostics,
            canonical_smiles,
            attachments,
            filename=filename,
        )

    return ChemistryResult(
        diagnostics=diagnostics,
        canonical_smiles=canonical_smiles,
        attachments=attachments,
        rdkit_version=rdkit_version(),
    )
