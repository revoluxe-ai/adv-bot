"""Схема Redis-ключей snapshot layer (новый namespace).

Важно: **не** меняем legacy ключи:
- ``calculated_keywords:{adv_id}`` — hash keywords (читает/пишет warmup);
- ``min_bids:v2:adv:...`` — min bids (только read в ``RedisSnapshotProviderLive``).

Snapshot пишет только в префикс ``adv_snapshot:v1:...``.
"""

from __future__ import annotations

SCHEMA_VERSION = "v1"


def keywords_meta_key(adv_id: int) -> str:
    """Metadata прогрева keywords (snapshot-owned, TTL отдельно от legacy hash).

    Поля JSON: ``warmed_at``, ``source``, ``schema_version``, ``keywords_count``, ``error``.
    """
    return f"adv_snapshot:{SCHEMA_VERSION}:keywords_meta:adv:{adv_id}"


def shop_batch_key(shop_id: str) -> str:
    """Последний ``ShopAdvSnapshotBatchDTO`` магазина (JSON)."""
    return f"adv_snapshot:{SCHEMA_VERSION}:shop:{shop_id}:latest"


def adv_snapshot_key(shop_id: str, adv_id: int) -> str:
    """Один ``AdvDataSnapshotDTO`` для быстрого read consumer adapter."""
    return f"adv_snapshot:{SCHEMA_VERSION}:shop:{shop_id}:adv:{adv_id}"
