"""``ComplexAdv`` для UI V3: Redis-провайдер keywords."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.client_bot.user_interface.services.keyword_v3_profile_loader import (
    _build_complex_adv,
    _ui_get_keywords_from_redis,
)
from app.modules.shop_runner.required_data_miss import ShopRunnerKeywordsCacheMissError
from app.modules.shop_runner.service_manager.wb_shop_data_manager import ComplexAdv


@pytest.mark.unit
@pytest.mark.asyncio
async def test_build_complex_adv_wires_redis_keywords_provider() -> None:
    """``_build_complex_adv`` задаёт ``get_keywords_func`` для ``load_campaign_v3_contexts``."""
    adv_setting = MagicMock()
    adv_setting.search_adv_id = None

    with (
        patch(
            "app.client_bot.user_interface.services.keyword_v3_profile_loader.sm",
        ) as sm_mock,
        patch(
            "app.client_bot.user_interface.services.keyword_v3_profile_loader.load_leg_cpo_snapshot",
            new=AsyncMock(side_effect=RuntimeError("leg CPO unavailable in unit")),
        ),
    ):
        session = AsyncMock()
        sm_mock.return_value.__aenter__.return_value = session
        complex_adv = await _build_complex_adv(adv_setting, "shop-42")

    assert isinstance(complex_adv, ComplexAdv)
    assert complex_adv._get_keywords is _ui_get_keywords_from_redis  # noqa: SLF001


@pytest.mark.unit
@pytest.mark.asyncio
async def test_ui_get_keywords_from_redis_delegates_to_fetch() -> None:
    """Провайдер UI читает strict Redis без пересчёта из БД."""
    complex_adv = MagicMock()
    complex_adv.adv_id = 77
    complex_adv.shop_id = "shop-77"
    cached = [MagicMock()]

    with patch(
        "app.modules.shop_runner.required_data_miss.fetch_calculated_keywords_from_redis",
        new=AsyncMock(return_value=cached),
    ) as fetch_redis:
        result = await _ui_get_keywords_from_redis(complex_adv, cache_only=True)

    fetch_redis.assert_awaited_once_with(77, shop_id="shop-77")
    assert result is cached


@pytest.mark.unit
@pytest.mark.asyncio
async def test_complex_adv_get_keywords_raises_cache_miss_not_runtime() -> None:
    """При miss Redis — ``ShopRunnerKeywordsCacheMissError``, не ``_get_keywords not set``."""
    adv_setting = MagicMock()
    adv_setting.search_adv_id = None
    adv_setting.adv_id = 88

    with (
        patch(
            "app.client_bot.user_interface.services.keyword_v3_profile_loader.sm",
        ) as sm_mock,
        patch(
            "app.modules.shop_runner.required_data_miss.fetch_calculated_keywords_from_redis",
            new=AsyncMock(
                side_effect=ShopRunnerKeywordsCacheMissError("miss", shop_id="s", adv_id=88)
            ),
        ),
        patch(
            "app.client_bot.user_interface.services.keyword_v3_profile_loader.load_leg_cpo_snapshot",
            new=AsyncMock(side_effect=RuntimeError("leg CPO unavailable in unit")),
        ),
    ):
        session = AsyncMock()
        sm_mock.return_value.__aenter__.return_value = session
        complex_adv = await _build_complex_adv(adv_setting, "shop-88")

        with pytest.raises(ShopRunnerKeywordsCacheMissError):
            await complex_adv.get_keywords()
