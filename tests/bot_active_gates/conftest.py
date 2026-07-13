"""Фикстуры gate-тестов: inactive adv с включёнными auto-flags."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from app.core.redis_manager_v2.redis_client import RedisClient
from app.modules.common_slaves.wildberries.models import AdvSetting
from app.modules.shop_runner.modules.wb_api import WBApi
from app.modules.shop_runner.service_manager.manager import CoroutinesManager
from app.modules.shop_runner.service_manager.wb_shop_data_manager.dto.complex_adv import (
    ComplexAdv,
)
from tests.bot_active_gates.helpers import (
    build_coroutines_manager,
    make_adv_setting,
    make_complex_adv,
    make_wb_api,
)

pytestmark = pytest.mark.unit


@pytest.fixture
def inactive_adv_setting() -> AdvSetting:
    """Кампания free: bot_active=False, все auto-flags ON."""
    return make_adv_setting(bot_active=False)


@pytest.fixture
def inactive_complex_adv(inactive_adv_setting: AdvSetting) -> ComplexAdv:
    return make_complex_adv("shop-gate-1", inactive_adv_setting)


@pytest.fixture
def wb_api_gate(access_mock: MagicMock) -> WBApi:
    return make_wb_api(access_mock, "shop-gate-1")


@pytest.fixture
def coroutines_manager_gate(wb_api_gate: WBApi, fake_redis: object) -> CoroutinesManager:
    redis_wrapper = RedisClient(redis_client=fake_redis)
    manager = build_coroutines_manager(wb_api_gate, redis_wrapper)
    manager._split_advs_by_stats_freshness = AsyncMock(
        side_effect=lambda advs, **_: (advs, [])
    )
    return manager
