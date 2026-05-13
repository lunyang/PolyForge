from __future__ import annotations

import json
import re
from importlib import resources
from typing import Any

CANONICAL_IR_SCHEMA_VERSION = "polyforge.v0.1"
CANONICAL_IR_SCHEMA_RESOURCE = "canonical_ir_v0_1.schema.json"

REQUIRED_ROOT_FIELDS = (
    "schema",
    "name",
    "monomers",
    "architecture",
    "sequence",
    "molecular_weight",
    "stereochemistry",
    "targets",
    "metadata",
    "rdkit_version",
    "structure_hash",
    "canonical_id",
)


def load_canonical_ir_schema() -> dict[str, Any]:
    schema_path = resources.files("polyforge.schema").joinpath(CANONICAL_IR_SCHEMA_RESOURCE)
    return json.loads(schema_path.read_text(encoding="utf-8"))


def validate_canonical_ir(ir: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if not isinstance(ir, dict):
        return ["canonical IR must be a JSON object"]

    for field in REQUIRED_ROOT_FIELDS:
        if field not in ir:
            errors.append(f"missing required canonical IR field: {field}")

    if errors:
        return errors

    if ir["schema"] != CANONICAL_IR_SCHEMA_VERSION:
        errors.append(f"unsupported canonical schema: {ir['schema']}")
    if not isinstance(ir["name"], str) or not ir["name"]:
        errors.append("canonical IR field name must be a non-empty string")
    if ir["architecture"] != "linear":
        errors.append("canonical IR field architecture must be linear in v0.1")
    if not isinstance(ir["monomers"], dict) or not ir["monomers"]:
        errors.append("canonical IR field monomers must be a non-empty object")
    if not isinstance(ir["sequence"], dict):
        errors.append("canonical IR field sequence must be an object")
    if not isinstance(ir["targets"], list):
        errors.append("canonical IR field targets must be an array")
    if not isinstance(ir["metadata"], dict):
        errors.append("canonical IR field metadata must be an object")
    if not isinstance(ir["rdkit_version"], str):
        errors.append("canonical IR field rdkit_version must be a string")

    if errors:
        return errors

    monomer_ids = set(ir["monomers"])
    errors.extend(_validate_monomers(ir["monomers"]))
    errors.extend(_validate_sequence(ir["sequence"], monomer_ids))
    errors.extend(_validate_optional_object(ir["molecular_weight"], "molecular_weight"))
    errors.extend(_validate_optional_object(ir["stereochemistry"], "stereochemistry"))
    errors.extend(_validate_hash_field(ir["structure_hash"], "structure_hash", r"sha256:[0-9a-f]{64}"))
    errors.extend(_validate_hash_field(ir["canonical_id"], "canonical_id", r"PolyForge:v0\.1:sha256:[0-9a-f]{64}"))
    return errors


def _validate_monomers(monomers: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    for monomer_id, monomer in monomers.items():
        if not isinstance(monomer_id, str) or not monomer_id.startswith("M") or not monomer_id[1:].isdigit():
            errors.append(f"invalid monomer id: {monomer_id}")
            continue
        if not isinstance(monomer, dict):
            errors.append(f"monomer {monomer_id} must be an object")
            continue
        for field in ("original_name", "canonical_smiles", "polymerization", "attach", "provenance"):
            if field not in monomer:
                errors.append(f"monomer {monomer_id} missing required field: {field}")
        if "attach" in monomer and not _is_attach_list(monomer["attach"]):
            errors.append(f"monomer {monomer_id} attach must be null or an array of non-negative integers")
        if "provenance" in monomer and not isinstance(monomer["provenance"], dict):
            errors.append(f"monomer {monomer_id} provenance must be an object")
    return errors


def _validate_sequence(sequence: dict[str, Any], monomer_ids: set[str]) -> list[str]:
    sequence_type = sequence.get("type")
    if sequence_type == "homopolymer":
        return _validate_monomer_ref(sequence, "monomer", monomer_ids)
    if sequence_type in {"random_copolymer", "alternating_copolymer"}:
        errors = _validate_monomer_ref_list(sequence.get("units"), "sequence.units", monomer_ids)
        if sequence_type == "random_copolymer":
            composition = sequence.get("composition")
            if not isinstance(composition, dict):
                errors.append("random_copolymer sequence requires composition object")
            else:
                for monomer_id, fraction in composition.items():
                    if monomer_id not in monomer_ids:
                        errors.append(f"sequence composition references unknown monomer id: {monomer_id}")
                    if not isinstance(fraction, int | float):
                        errors.append(f"sequence composition for {monomer_id} must be numeric")
        return errors
    if sequence_type == "block_copolymer":
        blocks = sequence.get("blocks")
        if not isinstance(blocks, list) or not blocks:
            return ["block_copolymer sequence requires non-empty blocks array"]
        errors: list[str] = []
        for index, block in enumerate(blocks):
            if not isinstance(block, dict):
                errors.append(f"sequence block {index} must be an object")
                continue
            errors.extend(_validate_monomer_ref(block, "monomer", monomer_ids, prefix=f"sequence block {index}"))
            if not isinstance(block.get("DP"), int | float) or block["DP"] <= 0:
                errors.append(f"sequence block {index} DP must be a positive number")
        return errors
    return [f"unsupported canonical sequence type: {sequence_type}"]


def _validate_monomer_ref(mapping: dict[str, Any], key: str, monomer_ids: set[str], prefix: str = "sequence") -> list[str]:
    value = mapping.get(key)
    if value not in monomer_ids:
        return [f"{prefix} references unknown monomer id: {value}"]
    return []


def _validate_monomer_ref_list(value: Any, label: str, monomer_ids: set[str]) -> list[str]:
    if not isinstance(value, list) or not value:
        return [f"{label} must be a non-empty array"]
    return [f"{label} references unknown monomer id: {item}" for item in value if item not in monomer_ids]


def _validate_optional_object(value: Any, field: str) -> list[str]:
    if value is not None and not isinstance(value, dict):
        return [f"canonical IR field {field} must be null or an object"]
    return []


def _validate_hash_field(value: Any, field: str, pattern: str) -> list[str]:
    if value is None:
        return []
    if not isinstance(value, str) or re.fullmatch(pattern, value) is None:
        return [f"canonical IR field {field} has invalid format"]
    return []


def _is_attach_list(value: Any) -> bool:
    if value is None:
        return True
    return isinstance(value, list) and all(isinstance(item, int) and item >= 0 for item in value)
