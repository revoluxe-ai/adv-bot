"""ComplexAdv.get_keywords: только Redis, без пересчёта CH."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from app.modules.shop_runner.service_manager.wb_shop_data_manager.dto.complex_adv import (
    ComplexAdv,
)
from app.modules.shop_runner.required_data_miss import (
    ShopRunnerKeywordsCacheMissError,
)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_keywords_raises_on_cache_only_false() -> None:
    complex_adv = ComplexAdv(
        shop_id="s1",
        adv_setting=MagicMock(),
        get_keywords_func=AsyncMock(return_value=[]),
    )

    with pytest.raises(RuntimeError, match="cache_only=False"):
        await complex_adv.get_keywords(cache_only=False)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_keywords_strict_miss_raises() -> None:
    """Miss — ответственность провайдера (как у Redis path)."""
    adv_setting = MagicMock()
    adv_setting.id = 1
    adv_setting.adv_id = 42
    miss = ShopRunnerKeywordsCacheMissError(
        "cache miss", shop_id="shop-1", adv_id=42
    )
    provider = AsyncMock(side_effect=miss)
    complex_adv = ComplexAdv(
        shop_id="shop-1",
        adv_setting=adv_setting,
        get_keywords_func=provider,
    )

    with pytest.raises(ShopRunnerKeywordsCacheMissError, match="cache miss"):
        await complex_adv.get_keywords()

    provider.assert_awaited_once()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_keywords_empty_list_refetches_redis() -> None:
    """Пустой [] (__empty__) не кэшируется на инстансе — повтор читает Redis."""
    provider = AsyncMock(return_value=[])
    complex_adv = ComplexAdv(
        shop_id="shop-1",
        adv_setting=MagicMock(),
        get_keywords_func=provider,
    )

    first = await complex_adv.get_keywords()
    second = await complex_adv.get_keywords()

    assert first == []
    assert second == []
    assert provider.await_count == 2


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_keywords_caches_nonempty_without_refetch() -> None:
    """Непустой список кэшируется на инстансе — повторный вызов без Redis."""
    kw = MagicMock()
    provider = AsyncMock(return_value=[kw])
    complex_adv = ComplexAdv(
        shop_id="shop-1",
        adv_setting=MagicMock(),
        get_keywords_func=provider,
    )

    first = await complex_adv.get_keywords()
    second = await complex_adv.get_keywords()

    assert len(first) == 1
    assert first == second
    provider.assert_awaited_once()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_keywords_empty_then_nonempty_on_refetch() -> None:
    """После __empty__ warmup может заполнить hash — второй вызов видит keywords."""
    kw = MagicMock()
    provider = AsyncMock(side_effect=[[], [kw]])
    complex_adv = ComplexAdv(
        shop_id="shop-1",
        adv_setting=MagicMock(),
        get_keywords_func=provider,
    )

    assert await complex_adv.get_keywords() == []
    loaded = await complex_adv.get_keywords()

    assert loaded == [kw]
    assert provider.await_count == 2
