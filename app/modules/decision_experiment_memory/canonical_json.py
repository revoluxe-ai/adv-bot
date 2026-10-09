"""Canonical JSON hashing for plan digests and intervention signatures.

Algorithm aligned with ``wb_sky_control_plane.kernel.canonical_json`` (local copy
to avoid control-plane coupling per ownership ADL). Digest inputs MUST use
``canonicalize`` before hashing so enums, tuples, and nested dict key order are
stable.
"""

from __future__ import annotations

import hashlib
import json
from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from typing import Any, cast


def canonicalize(value: Any) -> Any:
    """Normalize a value to JSON-canonical form for deterministic hashing."""
    if isinstance(value, dict):
        mapping = cast(dict[Any, Any], value)
        return {
            str(k): canonicalize(v)
            for k, v in sorted(mapping.items(), key=lambda item: str(item[0]))
        }
    if isinstance(value, list):
        items = cast(list[Any], value)
        return [canonicalize(item) for item in items]
    if isinstance(value, tuple):
        tuple_items = cast(tuple[Any, ...], value)
        return [canonicalize(item) for item in tuple_items]
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    return str(value)


def canonical_json_dumps(value: Any) -> str:
    """Canonical JSON: sorted keys, compact separators."""
    return json.dumps(
        canonicalize(value),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    )


def canonical_sha256(value: Any) -> str:
    """Return sha256 hex digest of canonical JSON for ``value``."""
    return hashlib.sha256(canonical_json_dumps(value).encode("utf-8")).hexdigest()
