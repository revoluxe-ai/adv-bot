"""Unit: V3 переиспользует fact из WBAdvDTO без второго get_stat_data."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from app.modules.common_slaves.wildberries.models.fact_methods_enum import FactMethods
from app.modules.shop_runner.service_manager.old_modules.setting_auto_updater.data_classes import (
    FactData,
    PlanData,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.data_update_manager.loaders import (
    resolve_v3_fact_data,
)
from app.shared.domains.wb.dto.wb_adv_dto import WBAdvDTO


@pytest.mark.unit
@pytest.mark.asyncio
async def test_resolve_v3_fact_data_reuses_wb_adv_dto_fact() -> None:
    fact = FactData(
        pay_for_order=42.0,
        predict_orders=3.0,
        original_orders=3.0,
        fact_method=FactMethods.DIRECT_SALES,
    )
    plan = PlanData(orders=10, target_pay_for_order=80, max_pay_for_order=100)
    complex_adv = MagicMock()
    complex_adv.search_fact_cpo = 18.0
    dto = WBAdvDTO(
        complex_adv=complex_adv,
        plan=plan,
        fact=fact,
        keywords=[],
        min_bids=MagicMock(search={1: 50}),
    )
    updater = MagicMock()
    updater.get_fact_data = AsyncMock()

    resolved, source = await resolve_v3_fact_data(
        dto=dto,
        updater=updater,
        keywords=[],
        max_last_period=2,
    )

    assert resolved is not fact
    assert resolved.predict_orders == fact.predict_orders
    assert resolved.original_orders == fact.original_orders
    assert resolved.pay_for_order == 18.0
    assert fact.pay_for_order == 42.0
    assert source == "dto_search_leg"
    updater.get_fact_data.assert_not_awaited()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_resolve_v3_fact_data_falls_back_when_no_dto() -> None:
    fact = MagicMock()
    updater = MagicMock()
    updater.get_fact_data = AsyncMock(return_value=fact)

    resolved, source = await resolve_v3_fact_data(
        dto=None,
        updater=updater,
        keywords=[],
        max_last_period=2,
    )

    assert resolved is fact
    assert source == "updater"
    updater.get_fact_data.assert_awaited_once_with([])
