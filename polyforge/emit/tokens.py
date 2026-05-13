from __future__ import annotations

from typing import Any


def token_sequence(canonical_ir: dict[str, Any]) -> list[str]:
    tokens = [
        f"polymer:{canonical_ir['name']}",
        f"architecture:{canonical_ir['architecture']}",
    ]

    for monomer_id, monomer in sorted(canonical_ir["monomers"].items()):
        tokens.append(f"monomer:{monomer_id}:{monomer['canonical_smiles']}")

    sequence = canonical_ir["sequence"]
    sequence_type = sequence["type"]
    tokens.append(f"sequence:{sequence_type}")

    if sequence_type == "homopolymer":
        tokens.append(f"unit:{sequence['monomer']}")
    elif sequence_type in {"random_copolymer", "alternating_copolymer"}:
        tokens.extend(f"unit:{unit}" for unit in sequence["units"])
    elif sequence_type == "block_copolymer":
        tokens.extend(f"block:{block['monomer']}:DP={block['DP']}" for block in sequence["blocks"])

    if sequence_type == "random_copolymer":
        tokens.extend(
            f"composition:{monomer_id}:{fraction:g}"
            for monomer_id, fraction in sorted(sequence["composition"].items())
        )

    return tokens
