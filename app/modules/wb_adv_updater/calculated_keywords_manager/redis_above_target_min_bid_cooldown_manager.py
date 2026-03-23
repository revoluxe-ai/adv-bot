"""Redis-хранилище cooldown «выше цели при мин. ставке» (JSON: время + показы)."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import cast

from app.core.redis_manager_v2.redis_client import RedisClient
from app.modules.wb_adv_updater.calculated_keywords_manager.above_target_cooldown_entry import (
    AboveTargetCooldownEntry,
)

_KEY_PREFIX = "kw_cooldown:above_target_min"
_TTL_SECONDS = 25 * 60 * 60


def _key(adv_id: int, normalized_text: str) -> str:
    return f"{_KEY_PREFIX}:{adv_id}:{normalized_text}"


def _serialize(entry: AboveTargetCooldownEntry) -> str:
    return json.dumps(
        {
            "t": entry.last_disabled_at.timestamp(),
            "v": entry.views_at_freeze,
        },
        separators=(",", ":"),
    )


def _parse_payload(raw: str) -> AboveTargetCooldownEntry | None:
    raw = raw.strip()
    if not raw:
        return None
    try:
        parsed: object = json.loads(raw)
    except json.JSONDecodeError:
        parsed = None
    if isinstance(parsed, dict):
        data = cast(dict[str, object], parsed)
        t_raw = data.get("t")
        v_raw = data.get("v", 0)
        if isinstance(t_raw, (int, float)):
            t = float(t_raw)
            v = _coerce_views_int(v_raw)
            return AboveTargetCooldownEntry(datetime.fromtimestamp(t, tz=UTC), v)
    try:
        ts = float(raw)
        return AboveTargetCooldownEntry(datetime.fromtimestamp(ts, tz=UTC), 0)
    except (TypeError, ValueError, OSError):
        return None


def _coerce_views_int(v_raw: object) -> int:
    if isinstance(v_raw, bool):
        return 0
    if isinstance(v_raw, int):
        return v_raw
    if isinstance(v_raw, float):
        return int(v_raw)
    if isinstance(v_raw, str):
        try:
            return int(v_raw)
        except ValueError:
            return 0
    return 0


class RedisAboveTargetMinBidCooldownManager:
    """Хранит last_disabled_at + views_at_freeze по ключу adv_id + normalized_text."""

    def __init__(self, redis: RedisClient) -> None:
        self._redis = redis

    async def get_many(
        self,
        adv_id: int,
        normalized_texts: list[str],
    ) -> dict[str, AboveTargetCooldownEntry | None]:
        if not normalized_texts:
            return {}
        keys = [_key(adv_id, t) for t in normalized_texts]
        values = await self._redis.mget(keys)
        out: dict[str, AboveTargetCooldownEntry | None] = {}
        for text, raw in zip(normalized_texts, values, strict=True):
            if raw is None:
                out[text] = None
                continue
            out[text] = _parse_payload(raw)
        return out

    async def apply_updates(
        self,
        adv_id: int,
        updates: dict[str, AboveTargetCooldownEntry | None],
    ) -> None:
        if not updates:
            return
        for text, entry in updates.items():
            k = _key(adv_id, text)
            if entry is None:
                await self._redis.delete(k)
            else:
                await self._redis.set(k, _serialize(entry), ex=_TTL_SECONDS)
