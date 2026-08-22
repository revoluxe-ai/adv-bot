"""Фикстуры только для ``tests/unit/``: без ClickHouse при V3 RK ratio.

``load_campaign_orders_per_cart_7d`` / ``load_rk_orders_per_cart_7d`` (wb_common_stat)
вызываются из orchestrator и ``target_place_sync`` — unit-тесты мокают их здесь.

После empty-keywords apply-hook ``EmptyKeywordsPauseIntentManager`` /
``RedisCalculatedKeywordsCacheManager`` (``BaseRedis._client``) иначе
диалят live ``localhost:6379`` — см. ``_unit_fake_redis_base_redis_managers``.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from unittest.mock import AsyncMock, patch

import fakeredis.aioredis
import pytest

from tests.unit.auto_updater_v3.conftest import RK_ORDERS_PER_CART_TEST

# Nodeids that exercise ApplyManager / process_adv_v3 (empty-keywords Redis HEXISTS).
_UNIT_BASE_REDIS_FAKE_HINTS: tuple[str, ...] = (
    "auto_updater_v3",
    "test_process_adv_v3_plan_fact_cache",
)


@pytest.fixture(autouse=True)
def _unit_mock_v3_clickhouse_deps(request: pytest.FixtureRequest) -> object:
    """RK/rec baseline и worst-cost cache не ходят в CH/Redis в unit."""
    if request.node.get_closest_marker("unit") is None:
        yield
        return
    # carts_per_order=0.5 → orders_per_cart=2.0 (см. orders_per_cart_from_wb_carts_per_order_ratio)
    carts_per_order_mock = AsyncMock(return_value=0.5)
    with (
        patch(
            "app.modules.common_advs_stat.clickhouse_manager.get_cart_to_order_ratio_from_common_items_stat",
            new=carts_per_order_mock,
        ),
        patch(
            "app.modules.shop_runner.service_manager.services.v3_point_order_cpo.load_rk_orders_per_cart_7d",
            new=AsyncMock(return_value=RK_ORDERS_PER_CART_TEST),
        ),
        patch(
            "app.modules.shop_runner.service_manager.services.v3_point_order_cpo.load_campaign_orders_per_cart_7d",
            new=AsyncMock(return_value=RK_ORDERS_PER_CART_TEST),
        ),
        patch(
            "app.modules.shop_runner.service_manager.services.v3_point_order_cpo.load_rec_orders_per_view_for_v3",
            new=AsyncMock(return_value=None),
        ),
    ):
        yield


@pytest.fixture(autouse=True)
async def _unit_fake_redis_base_redis_managers(
    request: pytest.FixtureRequest,
) -> AsyncIterator[None]:
    """Unit: ``RedisManager`` / ``BaseRedis._client`` → FakeRedis, не live :6379.

    Apply path вызывает ``maybe_set_empty_keywords_pause_intent`` →
    ``EmptyKeywordsPauseIntentManager().client.hexists`` на module-level
    ``redis_client``. Без override unit-тесты с FakeRedis-параметром всё равно
    leak'ают на localhost (BAD_TEST / incomplete FakeRedis override).

    Creates FakeRedis only for matching nodeids (not via root ``fake_redis``
    fixture) so unrelated unit tests stay free of Redis setup.
    """
    if request.node.get_closest_marker("unit") is None:
        yield
        return
    if not any(h in request.node.nodeid for h in _UNIT_BASE_REDIS_FAKE_HINTS):
        yield
        return
    from app.core.redis_manager import RedisManager

    fake = await fakeredis.aioredis.FakeRedis(decode_responses=True)
    try:
        with patch.object(RedisManager, "_client", fake):
            yield
    finally:
        try:
            await fake.flushall()
            await fake.aclose()
        except RuntimeError as exc:
            if "Event loop is closed" not in str(exc):
                raise
