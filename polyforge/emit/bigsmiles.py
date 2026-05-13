from __future__ import annotations

from typing import Any


class UnsupportedBigSMILESExport(ValueError):
    pass


def _smiles(canonical_ir: dict[str, Any], monomer_id: str) -> str:
    return canonical_ir["monomers"][monomer_id]["canonical_smiles"]


def export_bigsmiles(canonical_ir: dict[str, Any]) -> str:
    sequence = canonical_ir["sequence"]
    sequence_type = sequence["type"]

    if canonical_ir.get("architecture") != "linear":
        raise UnsupportedBigSMILESExport("BigSMILES export supports only linear v0.1 polymers")

    if sequence_type == "homopolymer":
        return f"{{[<]{_smiles(canonical_ir, sequence['monomer'])}[>]}}"

    if sequence_type == "alternating_copolymer":
        repeat = "".join(f"[<]{_smiles(canonical_ir, monomer_id)}[>]" for monomer_id in sequence["units"])
        return f"{{{repeat}}}"

    if sequence_type == "block_copolymer":
        return "".join(
            f"{{[<]{_smiles(canonical_ir, block['monomer'])}[>]}}"
            for block in sequence["blocks"]
        )

    if sequence_type == "random_copolymer":
        composition = sequence.get("composition")
        if not composition:
            raise UnsupportedBigSMILESExport("random copolymer BigSMILES export requires composition")
        units = sequence["units"]
        body = ",".join(
            f"[<]{_smiles(canonical_ir, monomer_id)}:{composition[monomer_id]:g}[>]"
            for monomer_id in units
        )
        return f"{{{body}}}"

    raise UnsupportedBigSMILESExport(f"unsupported sequence type for BigSMILES export: {sequence_type}")
