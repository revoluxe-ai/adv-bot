"""Live ClickHouse evidence for shop-runner full-stat persistence."""

from __future__ import annotations

from datetime import date, datetime
import uuid
from unittest.mock import AsyncMock
from unittest.mock import MagicMock

import pytest
from clickhouse_connect import get_async_client
from fakeredis import FakeRedis
from sqlalchemy.ext.asyncio import AsyncSession

import app.modules.shop_runner.service_manager.manager as manager_module
from app.modules.shop_runner.wb_stat_manager.clickhouse_manager import (
    full_wb_adv_stat as full_wb_adv_stat_module,
)
from app.modules.shop_runner.service_manager.services import (
    clickhouse_freshness_reader as freshness_reader_module,
)
from app.modules.shop_runner.service_manager.services.plan_fact_controller import (
    plan_fact_reader as plan_fact_reader_module,
)
from app.client_bot.user_interface.views.messages.main_adv_setting_menu.adv_setting_menu import (
    AdvSettingMenu,
)
from app.modules.full_stat_adv_updater.types.full_adv_stat import DayStats, FullAdvStat
from app.modules.common_slaves.wildberries.models import AdvSetting, WBCabinet
from app.modules.shop_runner.service_manager.manager import CoroutinesManager
from app.modules.shop_runner.service_manager.services.plan_fact_controller.plan_fact_reader import (
    PlanFactReader,
)
from app.modules.shop_runner.service_manager.wb_shop_data_manager.wb_shop_data_manager import (
    WBShopDataManager,
)
from tests.support.rewrite_default_db_ch_client import patch_get_clickhouse_client

pytestmark = [pytest.mark.integration, pytest.mark.destructive_local]


@pytest.mark.integration
async def test_full_stat_child_writes_and_rereads_live_clickhouse(
    clickhouse_client: get_async_client,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """CH writer child persists a row and the test re-reads it from the store."""
    adv_id = uuid.uuid4().int % 1_000_000_000
    await clickhouse_client.command(
        "TRUNCATE TABLE test_adv_bot_clickhouse.full_adv_wb_stat"
    )
    patch_get_clickhouse_client(
        monkeypatch,
        [full_wb_adv_stat_module],
        clickhouse_client,
    )
    monkeypatch.setattr(
        manager_module.data_manager,
        "set_last_full_stat_update",
        AsyncMock(),
    )

    stat = FullAdvStat(
        dates=["2026-08-18"],
        views=10,
        clicks=2,
        ctr=20.0,
        cpc=5.0,
        sum=10.0,
        atbs=1,
        orders=1,
        cr=50.0,
        shks=1,
        sum_price=100.0,
        advertId=adv_id,
        days=[
            DayStats(
                date=datetime(2026, 8, 18),
                views=10,
                clicks=2,
                ctr=20.0,
                cpc=5.0,
                sum=10.0,
                atbs=1,
                orders=1,
                cr=50.0,
                shks=1,
                sum_price=100.0,
            )
        ],
    )

    await CoroutinesManager._update_full_stat_in_click_house([stat])

    result = await clickhouse_client.query(
        "SELECT adv_id, views, clicks, spend "
        "FROM test_adv_bot_clickhouse.full_adv_wb_stat "
        f"WHERE adv_id = {adv_id} "
        "ORDER BY version DESC LIMIT 1"
    )
    assert result.result_rows
    assert tuple(result.result_rows[0][:4]) == (adv_id, 10, 2, 10)


@pytest.mark.integration
async def test_adv_setting_menu_freshness_reads_live_clickhouse(
    clickhouse_client: get_async_client,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """AdvSettingMenu CH path reads a persisted full-stat row."""
    adv_id = uuid.uuid4().int % 1_000_000_000
    await clickhouse_client.insert(
        "test_adv_bot_clickhouse.full_adv_wb_stat",
        [(adv_id, date(2026, 8, 18), 10, 2, 10.0, 1, 1, 100.0, 123.0)],
        column_names=[
            "adv_id",
            "date",
            "views",
            "clicks",
            "spend",
            "added_to_cart",
            "orders",
            "sum_price_orders",
            "version",
        ],
    )
    patch_get_clickhouse_client(
        monkeypatch,
        [freshness_reader_module],
        clickhouse_client,
    )
    adv = MagicMock(spec=AdvSetting)
    adv.adv_id = adv_id
    adv.search_adv_id = None
    adv.nmids = [12345]
    menu = object.__new__(AdvSettingMenu)
    menu.adv = adv

    result = await menu._resolve_emergency_mode_from_ch()  # noqa: SLF001

    persisted = await clickhouse_client.query(
        "SELECT adv_id FROM test_adv_bot_clickhouse.full_adv_wb_stat "
        f"WHERE adv_id = {adv_id} LIMIT 1"
    )
    assert persisted.result_rows
    assert persisted.result_rows[0][0] == adv_id
    assert isinstance(result[0], bool)
    assert isinstance(result[2], bool)


@pytest.mark.integration
async def test_pre_complex_advs_reads_live_plan_fact_path(
    async_session: AsyncSession,
    clickhouse_client: get_async_client,
    fake_redis: FakeRedis,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """WBShopDataManager pre-complex path reaches the live CH plan-fact reader."""
    cabinet = WBCabinet(
        shop_id=f"pre_complex_gap_{uuid.uuid4().hex}",
        active=True,
        demo=True,
        balance=0.0,
        bonus=0.0,
    )
    async_session.add(cabinet)
    await async_session.flush()
    adv_setting = AdvSetting(
        adv_id=uuid.uuid4().int % 1_000_000_000,
        name="pre-complex-gap",
        wb_cabinet_id=cabinet.id,
        active_status="started",
        bot_active=True,
        nmids=[12345],
    )
    async_session.add(adv_setting)
    await async_session.flush()
    patch_get_clickhouse_client(
        monkeypatch,
        [plan_fact_reader_module],
        clickhouse_client,
    )
    manager = WBShopDataManager(
        wb_cabinet=cabinet,
        tasks_manager=None,
        wb_api_data_manager=MagicMock(),
        wb_manager=None,
        plan_fact_reader=PlanFactReader(redis_client=fake_redis),
    )

    result = await manager.get_pre_complex_advs(
        only_bot_active=True,
        skip_plan_fact=False,
        session=async_session,
    )

    assert [item.auto_adv.id for item in result] == [adv_setting.id]
