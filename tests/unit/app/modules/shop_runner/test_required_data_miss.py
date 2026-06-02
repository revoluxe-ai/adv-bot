"""Утилиты required data miss в shop-runner."""

from __future__ import annotations

import pytest

from unittest.mock import AsyncMock, patch

from app.modules.shop_runner.required_data_miss import (
    ShopRunnerKeywordsCacheMissError,
    fetch_calculated_keywords_from_redis,
    is_required_data_miss,
    make_keywords_cache_miss_error,
    required_data_miss_max_attempts,
    required_data_miss_retry_sec,
    resolve_calculated_keywords_cache,
)
from app.modules.shop_runner.service_manager.old_modules.setting_auto_updater.modules.first_key_updater.exc import (
    FirstKeyUpdaterError,
)
from app.snapshot_data_updater.cache_errors import RequiredDataMissError


@pytest.mark.unit
def test_is_required_data_miss_direct() -> None:
    err = ShopRunnerKeywordsCacheMissError("x", shop_id="s", adv_id=1)
    assert is_required_data_miss(err) is True
    assert isinstance(err, RequiredDataMissError)


@pytest.mark.unit
def test_is_required_data_miss_via_first_key_updater_cause() -> None:
    miss = ShopRunnerKeywordsCacheMissError("x", shop_id="s", adv_id=1)
    wrapped = FirstKeyUpdaterError()
    wrapped.__cause__ = miss
    assert is_required_data_miss(wrapped) is True


@pytest.mark.unit
def test_is_required_data_miss_false_for_other() -> None:
    assert is_required_data_miss(ValueError("nope")) is False


@pytest.mark.unit
def test_retry_sec_legacy_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("SHOP_RUNNER_REQUIRED_DATA_MISS_RETRY_SEC", raising=False)
    monkeypatch.setenv("SHOP_RUNNER_KEYWORDS_CACHE_MISS_RETRY_SEC", "99")
    assert required_data_miss_retry_sec() == 99


@pytest.mark.unit
def test_max_attempts_from_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SHOP_RUNNER_REQUIRED_DATA_MISS_MAX_ATTEMPTS", "5")
    assert required_data_miss_max_attempts() == 5


@pytest.mark.unit
def test_resolve_accepts_empty_list() -> None:
    assert resolve_calculated_keywords_cache([], shop_id="shop-1", adv_id=99) == []


@pytest.mark.unit
def test_resolve_raises_shop_runner_miss() -> None:
    with pytest.raises(ShopRunnerKeywordsCacheMissError, match="cache miss"):
        resolve_calculated_keywords_cache(None, shop_id="shop-1", adv_id=99)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_fetch_from_redis_returns_empty_when_warmup_meta_count_zero() -> None:
    with (
        patch(
            "app.modules.calculated_keywords_redis_cache_manager.redis_manager."
            "RedisCalculatedKeywordsCacheManager.get_all_calculated_keywords_for_adv",
            new_callable=AsyncMock,
            return_value=None,
        ),
        patch(
            "app.snapshot_data_updater.cache_freshness.load_keywords_meta",
            new_callable=AsyncMock,
            return_value={
                "keywords_count": "0",
                "source": "recalculated",
                "warmed_at": "2026-01-01T00:00:00+00:00",
            },
        ),
    ):
        result = await fetch_calculated_keywords_from_redis(99, shop_id="shop-1")

    assert result == []


@pytest.mark.unit
@pytest.mark.asyncio
async def test_fetch_from_redis_raises_on_miss() -> None:
    with (
        patch(
            "app.modules.calculated_keywords_redis_cache_manager.redis_manager."
            "RedisCalculatedKeywordsCacheManager.get_all_calculated_keywords_for_adv",
            new_callable=AsyncMock,
            return_value=None,
        ),
        patch(
            "app.snapshot_data_updater.cache_freshness.load_keywords_meta",
            new_callable=AsyncMock,
            return_value=None,
        ),
    ):
        with pytest.raises(ShopRunnerKeywordsCacheMissError, match="cache miss"):
            await fetch_calculated_keywords_from_redis(99, shop_id="shop-1")


@pytest.mark.unit
def test_make_keywords_cache_miss_error_fields() -> None:
    err = make_keywords_cache_miss_error(shop_id="s", adv_id=7)
    assert err.shop_id == "s"
    assert err.adv_id == 7
    assert err.resource == "calculated_keywords"
