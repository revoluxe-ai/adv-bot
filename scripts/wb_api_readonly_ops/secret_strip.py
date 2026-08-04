"""Secret-strip для Owner-local L0 archive (не Web L2 sanitize)."""

from __future__ import annotations

import re
from typing import Any, cast

_SECRET_KEY_RE = re.compile(
    r"(authorization|api[_-]?key|access[_-]?token|refresh[_-]?token|"
    r"cookie|set-cookie|bearer|wb[_-]?token|x-auth)",
    re.IGNORECASE,
)
_BEARER_RE = re.compile(r"Bearer\s+\S+", re.IGNORECASE)
_REDACTED = "***REDACTED***"


def looks_like_secret_key(key: str) -> bool:
    """True если имя поля похоже на секрет."""
    return bool(_SECRET_KEY_RE.search(key))


def strip_secrets(value: Any) -> Any:
    """Рекурсивно убрать token/Authorization/cookies из структуры для архива."""
    if isinstance(value, dict):
        mapping = cast(dict[Any, Any], value)
        out: dict[str, Any] = {}
        for key, item in mapping.items():
            key_str = str(key)
            if looks_like_secret_key(key_str):
                out[key_str] = _REDACTED
            else:
                out[key_str] = strip_secrets(item)
        return out
    if isinstance(value, list):
        items = cast(list[Any], value)
        return [strip_secrets(item) for item in items]
    if isinstance(value, tuple):
        items_t = cast(tuple[Any, ...], value)
        return [strip_secrets(item) for item in items_t]
    if isinstance(value, str):
        if _BEARER_RE.search(value):
            return _BEARER_RE.sub(f"Bearer {_REDACTED}", value)
        return value
    return value
