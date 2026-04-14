"""Разбор минимально допустимой ставки из тела BadRequest WB (как legacy get_error_from_response)."""

from __future__ import annotations

import json
import re
from typing import Any

_MIN_PATTERN = re.compile(r"min:\s*(?P<min>\d+)", re.IGNORECASE)


def parse_min_bid_from_bad_request_detail(detail: str) -> int | None:
    """Если WB вернул ``wrong bid value`` и ``min: <int>`` — вернуть минимум, иначе ``None``."""
    if not detail or not detail.strip():
        return None
    try:
        parsed: Any = json.loads(detail)
    except (json.JSONDecodeError, TypeError):
        return _min_from_plain_text(detail)

    if isinstance(parsed, dict):
        errors = parsed.get("errors")
        if isinstance(errors, list):
            for err in errors:
                if not isinstance(err, dict):
                    continue
                d = str(err.get("detail", "") or "")
                m = _extract_min_if_wrong_bid(d)
                if m is not None:
                    return m
        for key in ("detail", "title", "message"):
            val = parsed.get(key)
            if isinstance(val, str):
                m = _extract_min_if_wrong_bid(val)
                if m is not None:
                    return m
    return _min_from_plain_text(detail)


def _extract_min_if_wrong_bid(fragment: str) -> int | None:
    if "wrong bid value" not in fragment.lower():
        return None
    match = _MIN_PATTERN.search(fragment)
    if match:
        return int(match.group("min"))
    return None


def _min_from_plain_text(text: str) -> int | None:
    return _extract_min_if_wrong_bid(text)
