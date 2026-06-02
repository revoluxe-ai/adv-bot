"""Отсутствие данных snapshot/Redis, без которых корутина shop-runner не может работать.

Модуль на уровне ``app.modules.shop_runner`` (не в ``service_manager``), чтобы
``tasks_manager`` мог импортировать его без цикла через ``service_manager.__init__``.

Единая точка чтения ``calculated_keywords`` — ``fetch_calculated_keywords_from_redis``;
при miss — ``ShopRunnerKeywordsCacheMissError`` (подтип
``RequiredDataMissError``), обрабатывается в ``while_coroutine_decorator``.
"""

from __future__ import annotations

import os
from typing import TYPE_CHECKING

from app.snapshot_data_updater.cache_errors import (
    KeywordsCacheMissError,
    RequiredDataMissError,
)

if TYPE_CHECKING:
    from app.modules.wb_adv_updater.calculated_keywords_manager.dto.calculated_keyword import (
        CalculatedKeyword,
    )


class ShopRunnerKeywordsCacheMissError(KeywordsCacheMissError):
    """Keywords ещё не прогреты snapshot updater для данной РК/магазина."""


def make_keywords_cache_miss_error(*, shop_id: str, adv_id: int) -> ShopRunnerKeywordsCacheMissError:
    """Собрать исключение cache miss для ``calculated_keywords``."""
    return ShopRunnerKeywordsCacheMissError(
        f"calculated_keywords cache miss shop_id={shop_id} "
        f"adv_id={adv_id}: запустите snapshot updater (live) и дождитесь warmup",
        shop_id=shop_id,
        adv_id=adv_id,
    )


def resolve_calculated_keywords_cache(
    cached: list[CalculatedKeyword] | None,
    *,
    shop_id: str,
    adv_id: int,
) -> list[CalculatedKeyword]:
    """Проверить ответ Redis: список (в т.ч. ``[]``) или miss-исключение."""
    if cached is not None:
        return cached
    raise make_keywords_cache_miss_error(shop_id=shop_id, adv_id=adv_id)


async def _empty_keywords_from_warmup_meta(adv_id: int) -> list[CalculatedKeyword] | None:
    """Если snapshot meta фиксирует успешный warmup с 0 keywords — ``[]``, иначе ``None``."""
    from app.core.redis_manager.redis_client import redis_client
    from app.snapshot_data_updater.cache_freshness import load_keywords_meta

    meta = await load_keywords_meta(redis_client, adv_id)
    if meta is None:
        return None
    if meta.get("source") == "error":
        return None
    if meta.get("keywords_count") == "0":
        return []
    return None


async def fetch_calculated_keywords_from_redis(
    adv_id: int,
    *,
    shop_id: str = "",
) -> list[CalculatedKeyword]:
    """Прочитать ``calculated_keywords:{adv_id}`` из Redis (shop-runner, strict).

    Args:
        adv_id: идентификатор РК.
        shop_id: для текста ошибки и логов декоратора.

    Returns:
        Список keywords; ``[]`` — легитимный пустой результат после warmup.

    Raises:
        ShopRunnerKeywordsCacheMissError: hash отсутствует и нет meta count=0.
    """
    from app.modules.calculated_keywords_redis_cache_manager.redis_manager import (
        RedisCalculatedKeywordsCacheManager,
    )

    redis_mgr = RedisCalculatedKeywordsCacheManager()
    cached = await redis_mgr.get_all_calculated_keywords_for_adv(adv_id)
    if cached is not None:
        return cached
    empty_from_meta = await _empty_keywords_from_warmup_meta(adv_id)
    if empty_from_meta is not None:
        return empty_from_meta
    raise make_keywords_cache_miss_error(shop_id=shop_id, adv_id=adv_id)


def _env_int(name: str, default: str, *, legacy_names: tuple[str, ...] = ()) -> int:
    raw = os.getenv(name)
    if raw is not None and raw.strip() != "":
        return int(raw)
    for legacy in legacy_names:
        legacy_raw = os.getenv(legacy)
        if legacy_raw is not None and legacy_raw.strip() != "":
            return int(legacy_raw)
    return int(default)


def required_data_miss_retry_sec(override: int | None = None) -> int:
    """Пауза перед повтором корутины после miss обязательных данных (сек)."""
    if override is not None:
        return override
    return _env_int(
        "SHOP_RUNNER_REQUIRED_DATA_MISS_RETRY_SEC",
        "60",
        legacy_names=("SHOP_RUNNER_KEYWORDS_CACHE_MISS_RETRY_SEC",),
    )


def required_data_miss_max_attempts(override: int | None = None) -> int:
    """Сколько подряд miss без успешного тика, затем re-raise. ``<= 0`` — без лимита."""
    if override is not None:
        return override
    return _env_int(
        "SHOP_RUNNER_REQUIRED_DATA_MISS_MAX_ATTEMPTS",
        "30",
        legacy_names=(),
    )


def is_required_data_miss(exc: BaseException) -> bool:
    """``True``, если исключение или ``__cause__`` — отсутствие обязательных данных."""
    if isinstance(exc, RequiredDataMissError):
        return True
    cause = exc.__cause__
    if cause is not None and cause is not exc:
        return is_required_data_miss(cause)
    return False
