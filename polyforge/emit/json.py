from __future__ import annotations

from typing import Any

from polyforge.canonicalize.json_ir import canonicalize_ir, dumps_canonical_json


def export_json(canonical_ir: dict[str, Any]) -> str:
    return dumps_canonical_json(canonicalize_ir(canonical_ir))
