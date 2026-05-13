from __future__ import annotations

import copy
import hashlib
import json
from typing import Any


def canonical_json_bytes(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def sha256_digest(value: Any) -> str:
    return hashlib.sha256(canonical_json_bytes(value)).hexdigest()


def sha256_prefixed(value: Any) -> str:
    return f"sha256:{sha256_digest(value)}"


def canonical_id(value: dict[str, Any], schema_version: str) -> str:
    payload = copy.deepcopy(value)
    payload.pop("canonical_id", None)
    return f"PolyForge:{schema_version}:sha256:{sha256_digest(payload)}"
