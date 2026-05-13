from __future__ import annotations

import copy
import json
from typing import Any

from polyforge.canonicalize.hash import canonical_id, sha256_prefixed
from polyforge.canonicalize.normalize import (
    normalize_measurement_field,
    normalize_molar_mass,
    normalize_unknown,
    numeric_value,
)
from polyforge.check.chemistry import check_program_chemistry
from polyforge.ir.nodes import (
    AlternatingCopolymerSequence,
    BlockCopolymerSequence,
    HomopolymerSequence,
    MolecularWeight,
    PolymerProgram,
    PropertyTarget,
    RandomCopolymerSequence,
    Stereochemistry,
)

SCHEMA = "polyforge.v0.1"
SCHEMA_VERSION = "v0.1"


def dumps_canonical_json(value: dict[str, Any]) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _monomer_ids(program: PolymerProgram) -> dict[str, str]:
    return {name: f"M{index}" for index, name in enumerate(sorted(program.monomers))}


def _sequence_ir(program: PolymerProgram, name_to_id: dict[str, str]) -> dict[str, Any]:
    sequence = program.sequence
    if isinstance(sequence, HomopolymerSequence):
        return {"type": "homopolymer", "monomer": name_to_id[sequence.monomer]}
    if isinstance(sequence, RandomCopolymerSequence):
        composition: dict[str, float] = {}
        for name, value in sequence.composition.items():
            numeric = numeric_value(value)
            if numeric is None:
                raise ValueError(f"composition for monomer {name!r} is not numeric")
            composition[name_to_id[name]] = float(numeric)
        return {
            "type": "random_copolymer",
            "units": [name_to_id[name] for name in sequence.units],
            "composition": dict(sorted(composition.items())),
        }
    if isinstance(sequence, AlternatingCopolymerSequence):
        return {"type": "alternating_copolymer", "units": [name_to_id[name] for name in sequence.units]}
    if isinstance(sequence, BlockCopolymerSequence):
        return {
            "type": "block_copolymer",
            "blocks": [
                {"monomer": name_to_id[block.monomer], "DP": block.DP}
                for block in sequence.blocks
            ],
        }
    raise TypeError(f"unsupported sequence type: {type(sequence).__name__}")


def _molecular_weight_ir(molecular_weight: MolecularWeight | None) -> dict[str, Any] | None:
    if molecular_weight is None:
        return None
    return {
        "Mn_g_mol": normalize_molar_mass(molecular_weight.Mn),
        "Mw_g_mol": normalize_molar_mass(molecular_weight.Mw),
        "DPn": molecular_weight.DPn,
        "dispersity": molecular_weight.dispersity,
        "distribution": normalize_unknown(molecular_weight.distribution),
    }


def _stereochemistry_ir(stereochemistry: Stereochemistry | None) -> dict[str, Any] | None:
    if stereochemistry is None:
        return None
    return {"tacticity": normalize_unknown(stereochemistry.tacticity)}


def _target_ir(target: PropertyTarget) -> dict[str, Any]:
    result: dict[str, Any] = {"property": target.name}
    for key in sorted(target.fields):
        canonical_key, canonical_value = normalize_measurement_field(key, target.fields[key])
        result[canonical_key] = canonical_value
    return result


def _structure_payload(ir: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema": ir["schema"],
        "monomers": ir["monomers"],
        "architecture": ir["architecture"],
        "sequence": ir["sequence"],
        "stereochemistry": ir["stereochemistry"],
    }


def _with_hashes(ir: dict[str, Any]) -> dict[str, Any]:
    result = copy.deepcopy(ir)
    result["structure_hash"] = sha256_prefixed(_structure_payload(result))
    result["canonical_id"] = canonical_id(result, SCHEMA_VERSION)
    return result


def canonicalize_program(program: PolymerProgram, filename: str | None = None) -> dict[str, Any]:
    name_to_id = _monomer_ids(program)
    chemistry = check_program_chemistry(program, filename=filename)
    if chemistry.errors:
        messages = "; ".join(diagnostic.message for diagnostic in chemistry.errors)
        raise ValueError(messages)

    ir: dict[str, Any] = {
        "schema": SCHEMA,
        "name": program.name,
        "monomers": {},
        "architecture": program.architecture,
        "sequence": _sequence_ir(program, name_to_id),
        "molecular_weight": _molecular_weight_ir(program.molecular_weight),
        "stereochemistry": _stereochemistry_ir(program.stereochemistry),
        "targets": [_target_ir(target) for target in program.property_targets],
        "metadata": {},
        "rdkit_version": chemistry.rdkit_version,
        "structure_hash": None,
        "canonical_id": None,
    }

    monomers: dict[str, dict[str, Any]] = {}
    for original_name in sorted(program.monomers):
        monomer = program.monomers[original_name]
        monomer_id = name_to_id[original_name]
        monomer_ir: dict[str, Any] = {
            "original_name": original_name,
            "canonical_smiles": chemistry.canonical_smiles.get(original_name),
            "polymerization": monomer.polymerization,
            "attach": chemistry.attachments.get(original_name),
            "provenance": {},
        }
        if monomer.attach == "inferred" and original_name in chemistry.attachments:
            monomer_ir["provenance"]["attach"] = "inferred"
        monomers[monomer_id] = monomer_ir
    ir["monomers"] = monomers

    return _with_hashes(ir)


def canonicalize_ir(ir: dict[str, Any]) -> dict[str, Any]:
    if ir.get("schema") != SCHEMA:
        raise ValueError(f"unsupported canonical schema: {ir.get('schema')}")
    normalized = copy.deepcopy(ir)
    normalized.pop("canonical_id", None)
    normalized.pop("structure_hash", None)
    normalized["structure_hash"] = None
    normalized["canonical_id"] = None
    return _with_hashes(normalized)
