"""Согласование ``WBCabinet.shop_id`` (str) с ``ExportManifest.shop_id`` (int)."""

from __future__ import annotations


def manifest_shop_id(pg_shop_id: str) -> int:
    """
    Преобразует authoritative PG ``shop_id`` в int для manifest и CH строк.

    ``WBCabinet.shop_id`` типизирован как ``str``; manifest v1 хранит ``shop_id``
    как int для согласованности с ``CampaignStatRow.shop_id``.

    Args:
        pg_shop_id: Значение ``WBCabinet.shop_id``.

    Returns:
        Целочисленный идентификатор магазина.

    Raises:
        ValueError: если строка не является десятичным целым (fail-closed v1).
    """
    stripped = pg_shop_id.strip()
    if not stripped.isdigit():
        raise ValueError(
            f"shop_id must be numeric for manifest v1, got {pg_shop_id!r}"
        )
    return int(stripped)
