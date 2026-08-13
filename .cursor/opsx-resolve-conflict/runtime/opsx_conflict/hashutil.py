"""Канонические хеши и JSON для receipts/ledger."""

from __future__ import annotations

import hashlib
import json
from typing import Any


def sha256_bytes(data: bytes) -> str:
    """SHA-256 hex digest for raw bytes."""
    return hashlib.sha256(data).hexdigest()


def sha256_text(text: str) -> str:
    """SHA-256 hex digest for UTF-8 text."""
    return sha256_bytes(text.encode("utf-8"))


def canonical_json(value: Any) -> bytes:
    """Stable JSON bytes for hashing (sorted keys, no whitespace variance)."""
    return json.dumps(
        value,
        ensure_ascii=True,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def sha256_canonical(value: Any) -> str:
    """SHA-256 of canonical JSON."""
    return sha256_bytes(canonical_json(value))
