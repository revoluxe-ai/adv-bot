"""Canonical JSON serialization (key-order independent)."""

from __future__ import annotations

import hashlib
import json
from typing import Any, cast


def canonicalize(value: Any) -> Any:
    """Привести значение to JSON-canonical form для детерминированного hash."""
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
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    if hasattr(value, "value"):  # Enum
        return value.value
    return str(value)


def canonical_json_dumps(value: Any) -> str:
    """Canonical JSON: sorted keys, compact separators."""
    return json.dumps(canonicalize(value), sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def canonical_sha256(value: Any, *, prefix: str = "") -> str:
    """SHA-256 hex digest canonical projection."""
    digest = hashlib.sha256(canonical_json_dumps(value).encode("utf-8")).hexdigest()
    return f"{prefix}{digest}" if prefix else digest
