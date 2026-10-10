"""Anchor fingerprint и opaque cmp_* resource_id generation."""

from __future__ import annotations

import uuid


def build_anchor_fingerprint(
    *,
    wb_cabinet_id: int,
    auto_adv_id: int | None,
    search_adv_id: int | None,
    nm_ids: list[int],
) -> str:
    """Deterministic anchor excluding legacy shadow semantics."""
    nm_part = ",".join(str(n) for n in sorted(set(nm_ids)))
    return f"cab={wb_cabinet_id}|auto={auto_adv_id}|search={search_adv_id}|nm={nm_part}"


def generate_resource_id() -> str:
    """New opaque cmp_* id independent of WB campaign IDs or anchor fingerprint."""
    return f"cmp_{uuid.uuid4().hex}"
