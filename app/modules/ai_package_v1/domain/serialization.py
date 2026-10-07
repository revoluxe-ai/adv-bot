"""Детерминированная сериализация доменного контракта."""

from __future__ import annotations

import json
from typing import Any


def canonical_json_bytes(payload: dict[str, Any]) -> bytes:
    """
    UTF-8 JSON с сортировкой ключей и фиксированными разделителями.

    Используется для manifest и сравнения sha256 в тестах.
    """
    text = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    return text.encode("utf-8")
