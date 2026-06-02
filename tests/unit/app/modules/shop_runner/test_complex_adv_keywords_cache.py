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
    adv_setting = MagicMock()
    adv_setting.id = 1
    provider = AsyncMock(return_value=None)
    complex_adv = ComplexAdv(
        shop_id="shop-1",
        adv_setting=adv_setting,
        get_keywords_func=provider,
    )

    with pytest.raises(ShopRunnerKeywordsCacheMissError, match="cache miss"):
        await complex_adv.get_keywords()

    provider.assert_awaited_once()
    assert provider.await_args.kwargs.get("cache_only") is True


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_keywords_allow_miss_returns_none() -> None:
    adv_setting = MagicMock()
    provider = AsyncMock(return_value=None)
    complex_adv = ComplexAdv(
        shop_id="shop-1",
        adv_setting=adv_setting,
        get_keywords_func=provider,
    )

    assert await complex_adv.get_keywords(allow_miss=True) is None
