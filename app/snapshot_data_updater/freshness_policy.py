"""Двухпороговая политика свежести для snapshot updater и consumers.

Окно [skip_refresh_sec, stale_sec]:
- возраст < ``skip_refresh_sec`` — не обновляем (skip refresh), чтение OK;
- ``skip_refresh_sec`` ≤ возраст ≤ ``stale_sec`` — допустимо, чтение OK, updater может обновить;
- возраст > ``stale_sec`` — ``CacheStaleError`` при чтении (протухло).

``stale_sec <= 0`` — проверка протухания при чтении выключена.
``skip_refresh_sec <= 0`` — never skip refresh по этому порогу.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.snapshot_data_updater.cache_freshness import CacheStaleError, cache_age_sec


@dataclass(frozen=True, slots=True)
class FreshnessPolicy:
    """Пороги свежести одной секции данных (секунды)."""

    skip_refresh_sec: float = 300.0
    """Моложе — пропуск тяжёлого refresh (warmup / shop task)."""

    stale_sec: float = 900.0
    """Старше — ошибка при чтении из кеша consumer'ом."""


def classify_age_sec(age_sec: float, policy: FreshnessPolicy) -> str:
    """Классификация возраста: ``too_fresh`` | ``acceptable`` | ``stale``."""
    if policy.stale_sec > 0 and age_sec > policy.stale_sec:
        return "stale"
    if policy.skip_refresh_sec > 0 and age_sec < policy.skip_refresh_sec:
        return "too_fresh"
    return "acceptable"


def should_skip_refresh(age_sec: float, policy: FreshnessPolicy) -> bool:
    """``True`` — refresh не нужен (данные слишком свежие)."""
    return policy.skip_refresh_sec > 0 and age_sec < policy.skip_refresh_sec


def should_refresh(age_sec: float, policy: FreshnessPolicy) -> bool:
    """``True`` — нужен refresh (протухло или нет skip-окна)."""
    if policy.stale_sec > 0 and age_sec > policy.stale_sec:
        return True
    return not should_skip_refresh(age_sec, policy)


def enforce_cache_stale(
    timestamp: object,
    policy: FreshnessPolicy,
    *,
    context: str,
    require_timestamp: bool = True,
) -> None:
    """Жёсткий fail при чтении, если возраст > ``policy.stale_sec``.

    Args:
        timestamp: ``datetime`` (UTC) или ``None``.
        context: подпись для ошибки.
        require_timestamp: при включённой проверке stale — нет timestamp = ошибка.

    Raises:
        CacheStaleError: протухло или нет метки времени.
    """
    from datetime import datetime

    if policy.stale_sec <= 0:
        return
    if timestamp is None:
        if require_timestamp:
            raise CacheStaleError(
                f"{context}: cache timestamp missing (cannot verify age)",
                context=context,
                max_age_sec=policy.stale_sec,
            )
        return
    if not isinstance(timestamp, datetime):
        raise TypeError("timestamp must be datetime")
    age = cache_age_sec(timestamp)
    if age > policy.stale_sec:
        raise CacheStaleError(
            f"{context}: cache age {age:.1f}s exceeds stale {policy.stale_sec:.1f}s",
            context=context,
            age_sec=age,
            max_age_sec=policy.stale_sec,
        )
