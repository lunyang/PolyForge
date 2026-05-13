from __future__ import annotations

from ast import literal_eval
from collections.abc import Iterable

from lark import Token, Tree, Transformer, v_args

from polyforge.ir.nodes import (
    AlternatingCopolymerSequence,
    Block,
    BlockCopolymerSequence,
    HomopolymerSequence,
    MolecularWeight,
    MonomerDef,
    PolymerProgram,
    PropertyTarget,
    Quantity,
    RandomCopolymerSequence,
    Stereochemistry,
)


def _to_number(token: Token | str) -> int | float:
    value = str(token)
    return int(value) if value.isdigit() else float(value)


@v_args(inline=True)
class _AstTransformer(Transformer):
    def IDENT(self, token: Token) -> str:
        return str(token)

    def NUMBER(self, token: Token) -> int | float:
        return _to_number(token)

    def STRING(self, token: Token) -> str:
        return literal_eval(str(token))

    def unit(self, *parts: str) -> str:
        return "/".join(parts)

    def quantity(self, value: int | float, unit: str | None = None) -> Quantity:
        return Quantity(value=value, unit=unit)

    def list(self, *items):
        return list(items)

    def pair(self, key: str, value):
        return key, value

    def dict(self, *items):
        return dict(items)

    def attach_value(self, *children):
        return "inferred" if not children else children[0]

    def polymer_stmt(self, stmt):
        return stmt

    def monomer_stmt(self, stmt):
        return stmt

    def smiles_stmt(self, value: str):
        return ("smiles", value)

    def polymerization_stmt(self, value: str):
        return ("polymerization", value)

    def attach_stmt(self, value):
        return ("attach", value)

    def monomer_def(self, name: str, *stmts):
        fields = dict(stmts)
        return MonomerDef(
            name=name,
            smiles=fields["smiles"],
            polymerization=fields["polymerization"],
            attach=fields.get("attach"),
        )

    def architecture_stmt(self, value: str):
        return value

    def sequence_stmt(self, value):
        return value

    def sequence_expr(self, value):
        return value

    def homopolymer_expr(self, monomer: str):
        return HomopolymerSequence(monomer=monomer)

    def units_stmt(self, units):
        return ("units", units)

    def composition_stmt(self, composition):
        return ("composition", composition)

    def random_copolymer_stmt(self, stmt):
        return stmt

    def random_copolymer_expr(self, *stmts):
        fields = dict(stmts)
        return RandomCopolymerSequence(units=fields["units"], composition=fields["composition"])

    def alternating_copolymer_expr(self, monomer_a: str, monomer_b: str):
        return AlternatingCopolymerSequence(units=[monomer_a, monomer_b])

    def block_expr(self, monomer: str, dp: int | float | None = None):
        return Block(monomer=monomer, DP=dp)

    def block_list(self, *blocks):
        return list(blocks)

    def blocks_stmt(self, blocks):
        return ("blocks", blocks)

    def block_copolymer_stmt(self, stmt):
        return stmt

    def block_copolymer_expr(self, *stmts):
        fields = dict(stmts)
        return BlockCopolymerSequence(blocks=fields["blocks"])

    def mn_stmt(self, value):
        return ("Mn", value)

    def mw_stmt2(self, value):
        return ("Mw", value)

    def mw_stmt(self, stmt):
        return stmt

    def dpn_stmt(self, value):
        return ("DPn", value)

    def dispersity_stmt(self, value):
        return ("dispersity", value)

    def distribution_stmt(self, value: str):
        return ("distribution", value)

    def molecular_weight_block(self, *stmts):
        fields = dict(stmts)
        return MolecularWeight(
            Mn=fields.get("Mn"),
            Mw=fields.get("Mw"),
            DPn=fields.get("DPn"),
            dispersity=fields.get("dispersity"),
            distribution=fields.get("distribution"),
        )

    def stereo_stmt(self, value: str):
        return ("tacticity", value)

    def stereochemistry_stmt(self, stmt):
        return stmt

    def stereochemistry_block(self, *stmts):
        fields = dict(stmts)
        return Stereochemistry(tacticity=fields.get("tacticity"))

    def predict_stmt(self, key: str, value):
        return key, value

    def predict_block(self, name: str, *stmts):
        return PropertyTarget(name=name, fields=dict(stmts))

    def polymer_def(self, name: str, *stmts):
        monomer_definitions: list[MonomerDef] = []
        monomers: dict[str, MonomerDef] = {}
        architecture: str | None = None
        sequence = None
        molecular_weight: MolecularWeight | None = None
        stereochemistry: Stereochemistry | None = None
        property_targets: list[PropertyTarget] = []

        for stmt in stmts:
            if isinstance(stmt, MonomerDef):
                monomer_definitions.append(stmt)
                monomers[stmt.name] = stmt
            elif isinstance(stmt, str):
                architecture = stmt
            elif isinstance(stmt, (HomopolymerSequence, RandomCopolymerSequence, AlternatingCopolymerSequence, BlockCopolymerSequence)):
                sequence = stmt
            elif isinstance(stmt, MolecularWeight):
                molecular_weight = stmt
            elif isinstance(stmt, Stereochemistry):
                stereochemistry = stmt
            elif isinstance(stmt, PropertyTarget):
                property_targets.append(stmt)
            else:  # pragma: no cover - defensive
                raise TypeError(f"Unexpected AST node: {stmt!r}")

        if architecture is None:
            raise ValueError(f"polymer {name!r} is missing architecture")
        if sequence is None:
            raise ValueError(f"polymer {name!r} is missing sequence")

        return PolymerProgram(
            name=name,
            monomers=monomers,
            architecture=architecture,
            sequence=sequence,
            molecular_weight=molecular_weight,
            stereochemistry=stereochemistry,
            property_targets=property_targets,
            monomer_definitions=tuple(monomer_definitions),
        )

    def start(self, program: PolymerProgram):
        return program


def build_ast(tree: Tree) -> PolymerProgram:
    return _AstTransformer().transform(tree)
