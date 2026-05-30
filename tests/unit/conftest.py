"""Фикстуры только для ``tests/unit/``: без ClickHouse при V3 RK ratio.

``load_rk_orders_per_cart_7d`` (wb_common_stat) вызывается из orchestrator и
``target_place_sync`` — unit-тесты мокают его здесь, а не поднимают CH на :8124.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from tests.unit.auto_updater_v3.conftest import RK_ORDERS_PER_CART_TEST


@pytest.fixture(autouse=True)
def _unit_mock_v3_clickhouse_deps(request: pytest.FixtureRequest) -> object:
    """RK/rec baseline и worst-cost cache не ходят в CH/Redis в unit."""
    if request.node.get_closest_marker("unit") is None:
        yield
        return
    with (
        patch(
            "app.modules.shop_runner.service_manager.services.v3_point_order_cpo.load_rk_orders_per_cart_7d",
            new=AsyncMock(return_value=RK_ORDERS_PER_CART_TEST),
        ),
        patch(
            "app.modules.shop_runner.service_manager.services.v3_point_order_cpo.load_rec_orders_per_view_for_v3",
            new=AsyncMock(return_value=None),
        ),
        patch(
            "app.modules.shop_runner.service_manager.services.auto_updater_v3.orchestrator.cache_worst_costs_for_adv",
            new=AsyncMock(return_value=None),
        ),
    ):
        yield
