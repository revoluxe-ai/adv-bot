"""Проверка максимального возраста данных из Redis-кеша.

При ``SNAPSHOT_CACHE_MAX_AGE_SEC > 0`` чтение кеша старше порога завершается
``CacheStaleError`` (жёсткий fail вместо тихого использования stale данных).
"""

from __future__ import annotations

import json
from datetime import UTC, datetime

from app.snapshot_data_updater.cache_errors import (
    CacheStaleError,
    KeywordsCacheMissError,
    RequiredDataMissError,
)
from app.snapshot_data_updater.keys import keywords_meta_key
from typing import TYPE_CHECKING, TypeAlias

from redis.asyncio.client import Redis as AsyncRedisClient

# Legacy app Redis (``redis_client`` без decode_responses) — ответы ``bytes``.
# ``Redis[bytes]`` только для type checker: в runtime redis.Redis не generic.
if TYPE_CHECKING:
    SnapshotRedisClient: TypeAlias = AsyncRedisClient[bytes]
else:
    SnapshotRedisClient: TypeAlias = AsyncRedisClient


def parse_warmed_at(meta: dict[str, str] | None) -> datetime | None:
    """Извлекает ``warmed_at`` из metadata keywords (ISO UTC)."""
    if not meta:
        return None
    warmed_at_raw = meta.get("warmed_at")
    if not warmed_at_raw:
        return None
    try:
        warmed_at = datetime.fromisoformat(warmed_at_raw)
    except ValueError:
        return None
    if warmed_at.tzinfo is None:
        warmed_at = warmed_at.replace(tzinfo=UTC)
    return warmed_at


def cache_age_sec(warmed_at: datetime, *, now: datetime | None = None) -> float:
    """Возраст кеша в секундах относительно ``now`` (UTC)."""
    ref = now or datetime.now(tz=UTC)
    return (ref - warmed_at).total_seconds()


def enforce_cache_max_age(
    warmed_at: datetime | None,
    max_age_sec: float,
    *,
    context: str,
    require_timestamp: bool = True,
) -> None:
    """Проверяет свежесть кеша; при превышении порога — ``CacheStaleError``.

    Args:
        warmed_at: момент записи кеша; ``None`` при отсутствии metadata.
        max_age_sec: порог из ``SNAPSHOT_CACHE_MAX_AGE_SEC``; ``<= 0`` — проверка выкл.
        context: подпись для лога/ошибки (shop_id, adv_id, …).
        require_timestamp: если ``True`` и порог включён — отсутствие timestamp = ошибка.

    Raises:
        CacheStaleError: кеш старше порога или нет timestamp при включённой проверке.
    """
    if max_age_sec <= 0:
        return
    if warmed_at is None:
        if require_timestamp:
            raise CacheStaleError(
                f"{context}: cache timestamp missing (cannot verify age)",
                context=context,
                max_age_sec=max_age_sec,
            )
        return
    age = cache_age_sec(warmed_at)
    if age > max_age_sec:
        raise CacheStaleError(
            f"{context}: cache age {age:.1f}s exceeds max {max_age_sec:.1f}s",
            context=context,
            age_sec=age,
            max_age_sec=max_age_sec,
        )


def enforce_cache_max_age_from_meta(
    meta: dict[str, str] | None,
    max_age_sec: float,
    *,
    context: str,
) -> None:
    """Проверка по metadata keywords (``adv_snapshot:v1:keywords_meta:...``)."""
    enforce_cache_max_age(
        parse_warmed_at(meta),
        max_age_sec,
        context=context,
        require_timestamp=True,
    )


async def load_keywords_meta(
    client: SnapshotRedisClient, adv_id: int
) -> dict[str, str] | None:
    """Читает JSON metadata прогрева keywords для adv_id."""
    raw = await client.get(keywords_meta_key(adv_id))
    if not raw:
        return None
    if isinstance(raw, bytes):
        raw = raw.decode()
    try:
        data = json.loads(raw)
        if isinstance(data, dict):
            return {str(k): str(v) for k, v in data.items()}
    except json.JSONDecodeError:
        return None
    return None
