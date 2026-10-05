"""JSONL/JSON encoding for keyword performance payloads."""

from __future__ import annotations

import json
from collections.abc import Sequence
from typing import Any

from pydantic import BaseModel

from app.modules.ai_package_v1.domain.serialization import canonical_json_bytes


def encode_jsonl(rows: Sequence[BaseModel]) -> bytes:
    """Deterministic JSONL: sorted rows by serialized key."""
    lines: list[str] = []
    for row in sorted(rows, key=_row_sort_key):
        lines.append(
            json.dumps(row.model_dump(mode="json"), sort_keys=True, separators=(",", ":"))
        )
    if not lines:
        return b""
    return ("\n".join(lines) + "\n").encode("utf-8")


def encode_json_document(payload: dict[str, Any]) -> bytes:
    """Canonical JSON bytes for DATA_MAP/coverage."""
    return canonical_json_bytes(payload)


def _row_sort_key(row: BaseModel) -> str:
    data = row.model_dump(mode="json")
    return json.dumps(data, sort_keys=True, separators=(",", ":"))
