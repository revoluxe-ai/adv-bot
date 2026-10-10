"""Semantic fingerprint for configured row content (not write-version authority)."""

from __future__ import annotations

import hashlib
import json
from typing import Any


def compute_ad_control_state_token(parts: dict[str, Any]) -> str:
    """
    Stable content fingerprint including monotonic ``revision``.

    Used for audit/diff display; CAS writes bind to ``revision``, not this token alone.
    """
    canonical = json.dumps(parts, sort_keys=True, separators=(",", ":"), default=str)
    digest = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    return f"acs_{digest[:32]}"
