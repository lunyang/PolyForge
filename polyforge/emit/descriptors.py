from __future__ import annotations

from typing import Any

SEQUENCE_TYPES = (
    "alternating_copolymer",
    "block_copolymer",
    "homopolymer",
    "random_copolymer",
)


def descriptor_row(canonical_ir: dict[str, Any]) -> dict[str, int | float | str | None]:
    molecular_weight = canonical_ir.get("molecular_weight") or {}
    sequence_type = canonical_ir["sequence"]["type"]

    row: dict[str, int | float | str | None] = {
        "canonical_id": canonical_ir["canonical_id"],
        "descriptor.dispersity": molecular_weight.get("dispersity"),
        "descriptor.monomer_count": len(canonical_ir["monomers"]),
        "descriptor.Mn_g_mol": molecular_weight.get("Mn_g_mol"),
    }
    for candidate in SEQUENCE_TYPES:
        row[f"descriptor.sequence_{candidate}"] = 1 if sequence_type == candidate else 0

    row["descriptor.target_count"] = len(canonical_ir.get("targets", []))
    row["structure_hash"] = canonical_ir["structure_hash"]
    return row
