from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class Quantity:
    value: float | int
    unit: str | None = None


@dataclass(frozen=True)
class MonomerDef:
    name: str
    smiles: str
    polymerization: str
    attach: Any | None = None


@dataclass(frozen=True)
class MolecularWeight:
    Mn: Quantity | None = None
    Mw: Quantity | None = None
    DPn: float | int | None = None
    dispersity: float | int | None = None
    distribution: str | None = None


@dataclass(frozen=True)
class Stereochemistry:
    tacticity: str | None = None


@dataclass(frozen=True)
class PropertyTarget:
    name: str
    fields: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class Block:
    monomer: str
    DP: float | int | None = None


@dataclass(frozen=True)
class HomopolymerSequence:
    monomer: str
    kind: str = field(init=False, default="homopolymer")


@dataclass(frozen=True)
class RandomCopolymerSequence:
    units: list[str]
    composition: dict[str, Quantity | float | int]
    kind: str = field(init=False, default="random_copolymer")


@dataclass(frozen=True)
class AlternatingCopolymerSequence:
    units: list[str]
    kind: str = field(init=False, default="alternating_copolymer")


@dataclass(frozen=True)
class BlockCopolymerSequence:
    blocks: list[Block]
    kind: str = field(init=False, default="block_copolymer")


SequenceExpr = HomopolymerSequence | RandomCopolymerSequence | AlternatingCopolymerSequence | BlockCopolymerSequence


@dataclass(frozen=True)
class PolymerProgram:
    name: str
    monomers: dict[str, MonomerDef]
    architecture: str
    sequence: SequenceExpr
    molecular_weight: MolecularWeight | None = None
    stereochemistry: Stereochemistry | None = None
    property_targets: list[PropertyTarget] = field(default_factory=list)
    monomer_definitions: tuple[MonomerDef, ...] = field(default_factory=tuple)
