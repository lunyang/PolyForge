from __future__ import annotations

from collections.abc import Iterable

RESERVED_IDENTIFIERS = frozenset(
    {
        "polymer",
        "monomer",
        "architecture",
        "sequence",
        "homopolymer",
        "random_copolymer",
        "alternating_copolymer",
        "block_copolymer",
        "block",
        "predict",
        "molecular_weight",
        "stereochemistry",
        "vinyl",
        "step_growth",
        "ring_opening",
        "atactic",
        "isotactic",
        "syndiotactic",
        "inferred",
        "unknown",
        "linear",
    }
)


def duplicates(names: Iterable[str]) -> set[str]:
    seen: set[str] = set()
    repeated: set[str] = set()
    for name in names:
        if name in seen:
            repeated.add(name)
        seen.add(name)
    return repeated


def is_reserved_identifier(name: str) -> bool:
    return name in RESERVED_IDENTIFIERS
