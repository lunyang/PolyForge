"""PolyForge canonical IR package."""

from .json_ir import canonicalize_ir, canonicalize_program, dumps_canonical_json

__all__ = [
    "canonicalize_ir",
    "canonicalize_program",
    "dumps_canonical_json",
]
