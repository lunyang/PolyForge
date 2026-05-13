from __future__ import annotations

from collections.abc import Sequence

from polyforge.check.diagnostics import Diagnostic
from polyforge.check.symbols import duplicates, is_reserved_identifier
from polyforge.ir.nodes import (
    AlternatingCopolymerSequence,
    BlockCopolymerSequence,
    HomopolymerSequence,
    MolecularWeight,
    PolymerProgram,
    Quantity,
    RandomCopolymerSequence,
    Stereochemistry,
)

COMPOSITION_TOLERANCE = 1e-6
SUPPORTED_ARCHITECTURES = frozenset({"linear"})
SUPPORTED_POLYMERIZATIONS = frozenset({"vinyl", "step_growth", "ring_opening"})
SUPPORTED_TACTICITIES = frozenset({"atactic", "isotactic", "syndiotactic", "unknown"})


def _error(code: str, message: str, *, filename: str | None, path: str | None = None) -> Diagnostic:
    return Diagnostic(
        code=code,
        severity="error",
        message=message,
        file=filename,
        path=path,
        stage="semantic",
    )


def _value(value: Quantity | int | float | None) -> int | float | None:
    if isinstance(value, Quantity):
        return value.value
    return value


def _check_positive(
    diagnostics: list[Diagnostic],
    value: Quantity | int | float | None,
    *,
    code: str,
    field: str,
    filename: str | None,
) -> None:
    numeric = _value(value)
    if numeric is not None and numeric <= 0:
        diagnostics.append(
            _error(
                code,
                f"{field} must be positive",
                filename=filename,
                path=field,
            )
        )


def _monomer_definitions(program: PolymerProgram):
    return program.monomer_definitions or tuple(program.monomers.values())


def _check_reserved_identifiers(program: PolymerProgram, diagnostics: list[Diagnostic], filename: str | None) -> None:
    if is_reserved_identifier(program.name):
        diagnostics.append(
            _error(
                "polyforge.semantic.reserved_identifier",
                f"polymer name {program.name!r} is reserved",
                filename=filename,
                path="polymer.name",
            )
        )

    for monomer in _monomer_definitions(program):
        if is_reserved_identifier(monomer.name):
            diagnostics.append(
                _error(
                    "polyforge.semantic.reserved_identifier",
                    f"monomer name {monomer.name!r} is reserved",
                    filename=filename,
                    path=f"monomers.{monomer.name}",
                )
            )


def _check_monomers(program: PolymerProgram, diagnostics: list[Diagnostic], filename: str | None) -> None:
    monomers = _monomer_definitions(program)
    for name in sorted(duplicates(monomer.name for monomer in monomers)):
        diagnostics.append(
            _error(
                "polyforge.semantic.duplicate_monomer",
                f"monomer name {name!r} is defined more than once",
                filename=filename,
                path=f"monomers.{name}",
            )
        )

    for monomer in monomers:
        if monomer.polymerization not in SUPPORTED_POLYMERIZATIONS:
            diagnostics.append(
                _error(
                    "polyforge.semantic.unsupported_polymerization",
                    f"polymerization {monomer.polymerization!r} is not supported in v0.1",
                    filename=filename,
                    path=f"monomers.{monomer.name}.polymerization",
                )
            )


def _check_monomer_reference(
    name: str,
    defined_monomers: set[str],
    diagnostics: list[Diagnostic],
    *,
    filename: str | None,
    path: str,
) -> None:
    if name not in defined_monomers:
        diagnostics.append(
            _error(
                "polyforge.semantic.undefined_monomer",
                f"monomer {name!r} is not defined",
                filename=filename,
                path=path,
            )
        )


def _check_random_composition(
    sequence: RandomCopolymerSequence,
    diagnostics: list[Diagnostic],
    *,
    filename: str | None,
) -> None:
    total = 0.0
    invalid_fraction = False
    for monomer, fraction in sequence.composition.items():
        numeric = _value(fraction)
        if numeric is None:
            continue
        if numeric < 0:
            invalid_fraction = True
        total += float(numeric)

    if invalid_fraction or abs(total - 1.0) > COMPOSITION_TOLERANCE:
        diagnostics.append(
            _error(
                "polyforge.semantic.invalid_composition",
                "random-copolymer composition fractions must be non-negative and sum to 1.0 within 1e-6",
                filename=filename,
                path="sequence.composition",
            )
        )


def _check_sequence(program: PolymerProgram, diagnostics: list[Diagnostic], filename: str | None) -> None:
    sequence = program.sequence
    defined_monomers = set(program.monomers)

    if isinstance(sequence, HomopolymerSequence):
        _check_monomer_reference(
            sequence.monomer,
            defined_monomers,
            diagnostics,
            filename=filename,
            path="sequence.monomer",
        )
        return

    if isinstance(sequence, RandomCopolymerSequence):
        if len(sequence.units) < 2:
            diagnostics.append(
                _error(
                    "polyforge.semantic.invalid_sequence",
                    "random copolymers must contain at least two units",
                    filename=filename,
                    path="sequence.units",
                )
            )
        for unit in sequence.units:
            _check_monomer_reference(unit, defined_monomers, diagnostics, filename=filename, path="sequence.units")
        for monomer in sequence.composition:
            _check_monomer_reference(
                monomer,
                defined_monomers,
                diagnostics,
                filename=filename,
                path="sequence.composition",
            )
        _check_random_composition(sequence, diagnostics, filename=filename)
        return

    if isinstance(sequence, AlternatingCopolymerSequence):
        for unit in sequence.units:
            _check_monomer_reference(unit, defined_monomers, diagnostics, filename=filename, path="sequence.units")
        return

    if isinstance(sequence, BlockCopolymerSequence):
        if len(sequence.blocks) < 2:
            diagnostics.append(
                _error(
                    "polyforge.semantic.invalid_sequence",
                    "block copolymers must contain at least two blocks",
                    filename=filename,
                    path="sequence.blocks",
                )
            )
        for index, block in enumerate(sequence.blocks):
            _check_monomer_reference(
                block.monomer,
                defined_monomers,
                diagnostics,
                filename=filename,
                path=f"sequence.blocks.{index}.monomer",
            )
            if block.DP is None or block.DP <= 0:
                diagnostics.append(
                    _error(
                        "polyforge.semantic.invalid_block_dp",
                        "block DP must be present and positive",
                        filename=filename,
                        path=f"sequence.blocks.{index}.DP",
                    )
                )


def _check_molecular_weight(
    molecular_weight: MolecularWeight | None,
    diagnostics: list[Diagnostic],
    filename: str | None,
) -> None:
    if molecular_weight is None:
        return

    _check_positive(
        diagnostics,
        molecular_weight.Mn,
        code="polyforge.semantic.invalid_molecular_weight",
        field="molecular_weight.Mn",
        filename=filename,
    )
    _check_positive(
        diagnostics,
        molecular_weight.Mw,
        code="polyforge.semantic.invalid_molecular_weight",
        field="molecular_weight.Mw",
        filename=filename,
    )
    _check_positive(
        diagnostics,
        molecular_weight.DPn,
        code="polyforge.semantic.invalid_molecular_weight",
        field="molecular_weight.DPn",
        filename=filename,
    )
    if molecular_weight.dispersity is not None and molecular_weight.dispersity < 1.0:
        diagnostics.append(
            _error(
                "polyforge.semantic.invalid_dispersity",
                "dispersity must be greater than or equal to 1.0",
                filename=filename,
                path="molecular_weight.dispersity",
            )
        )


def _check_stereochemistry(
    stereochemistry: Stereochemistry | None,
    diagnostics: list[Diagnostic],
    filename: str | None,
) -> None:
    if stereochemistry is None or stereochemistry.tacticity is None:
        return
    if stereochemistry.tacticity not in SUPPORTED_TACTICITIES:
        diagnostics.append(
            _error(
                "polyforge.semantic.unsupported_tacticity",
                f"tacticity {stereochemistry.tacticity!r} is not supported in v0.1",
                filename=filename,
                path="stereochemistry.tacticity",
            )
        )


def check_program(program: PolymerProgram, filename: str | None = None) -> list[Diagnostic]:
    diagnostics: list[Diagnostic] = []

    _check_reserved_identifiers(program, diagnostics, filename)
    _check_monomers(program, diagnostics, filename)

    if program.architecture not in SUPPORTED_ARCHITECTURES:
        diagnostics.append(
            _error(
                "polyforge.semantic.unsupported_architecture",
                f"architecture {program.architecture!r} is not supported in v0.1",
                filename=filename,
                path="architecture",
            )
        )

    _check_sequence(program, diagnostics, filename)
    _check_molecular_weight(program.molecular_weight, diagnostics, filename)
    _check_stereochemistry(program.stereochemistry, diagnostics, filename)

    return diagnostics


def check_programs(programs: Sequence[PolymerProgram], filename: str | None = None) -> list[Diagnostic]:
    diagnostics: list[Diagnostic] = []

    for name in sorted(duplicates(program.name for program in programs)):
        diagnostics.append(
            _error(
                "polyforge.semantic.duplicate_polymer",
                f"polymer name {name!r} is defined more than once",
                filename=filename,
                path=f"polymers.{name}",
            )
        )

    for program in programs:
        diagnostics.extend(check_program(program, filename=filename))

    return diagnostics
