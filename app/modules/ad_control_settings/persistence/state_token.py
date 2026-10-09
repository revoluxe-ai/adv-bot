"""Deterministic generation tokens для optimistic concurrency (st1-like)."""

from __future__ import annotations

import hashlib
import json
from typing import Any


def compute_ad_control_state_token(parts: dict[str, Any]) -> str:
    """
    Стабильный token по semantic parts row (без id / updated_at).

    Используется dry-run preconditions и PG writes (future Apply).
    """
    canonical = json.dumps(parts, sort_keys=True, separators=(",", ":"), default=str)
    digest = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    return f"acs_{digest[:32]}"
