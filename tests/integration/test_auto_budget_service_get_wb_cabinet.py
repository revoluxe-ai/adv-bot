from datetime import datetime, timedelta

import pytest

from app.modules.auto_budget_manager.service import AutoBudgetService
from app.modules.common_slaves.wildberries.models import AdvSetting, WBCabinet



pytestmark = pytest.mark.destructive_local
@pytest.mark.integration
@pytest.mark.asyncio
async def test_get_wb_shop_id_fetches_shop_id(async_session) -> None:
    """AutoBudgetService._get_wb_shop_id должен вернуть shop_id по adv_setting.id."""
    cabinet = WBCabinet(
        shop_id="auto_budget_test_shop",
        active=True,
        expiration_time=datetime.utcnow() + timedelta(days=7),
        balance=0.0,
        bonus=0.0,
        demo=True,
        expiration_alarm_days_pass=None,
    )
    async_session.add(cabinet)
    await async_session.flush()

    adv_setting = AdvSetting(
        adv_id=123_456,
        name="auto-budget-test",
        wb_cabinet_id=cabinet.id,
        active_status="started",
        bot_active=True,
        plan_for_sales_for_day=1,
        target_price_for_order=100.0,
        max_price_for_order=150.0,
        max_cpm=1000,
    )
    async_session.add(adv_setting)
    await async_session.flush()

    found = await AutoBudgetService._get_wb_shop_id(async_session, adv_setting.id)
    assert found == cabinet.shop_id
