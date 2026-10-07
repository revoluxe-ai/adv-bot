"""Canonical JSON hashing for plan digests and intervention signatures."""

from __future__ import annotations

import hashlib
import json
from typing import Any


def canonical_json_dumps(value: Any) -> str:
    """Serialize value to deterministic JSON (sorted keys, compact separators)."""
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def canonical_sha256(value: Any) -> str:
    """Return sha256 hex digest of canonical JSON for ``value``."""
    return hashlib.sha256(canonical_json_dumps(value).encode("utf-8")).hexdigest()
