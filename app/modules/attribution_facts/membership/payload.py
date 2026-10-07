"""Извлечение promoted nm ids из canonical history payload_json."""

from __future__ import annotations

import json

from app.modules.attribution_facts.domain.enums import AttributionReasonCode


def promoted_nm_ids_from_payload(payload_json: str) -> frozenset[int] | None:
    """
    Распарсить promoted nm ids из canonical campaign settings payload.

    Returns:
        frozenset nm ids или None при parse/structure ошибке.
    """
    try:
        data = json.loads(payload_json)
    except json.JSONDecodeError:
        return None
    if not isinstance(data, dict):
        return None
    campaign = data.get("campaign")
    if not isinstance(campaign, dict):
        return None
    nmids = campaign.get("nmids")
    if not isinstance(nmids, list):
        return None
    result: set[int] = set()
    for item in nmids:
        if isinstance(item, bool) or not isinstance(item, (int, str, float)):
            continue
        try:
            result.add(int(item))
        except (TypeError, ValueError):
            continue
    return frozenset(result)


def empty_promoted_is_ambiguous(
    promoted: frozenset[int] | None,
) -> bool:
    """True если membership пустой или не распознан."""
    return promoted is None or len(promoted) == 0


__all__ = ["empty_promoted_is_ambiguous", "promoted_nm_ids_from_payload"]
