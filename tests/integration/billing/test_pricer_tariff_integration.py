"""Integration: Pricer tariff AUTO/OLD modes against live test PG.

``wb_cabinet`` consumes baseline ``wbcabinet`` id=1 from
``reset_postgres_test_data(restore_baseline=True)`` — do not INSERT id=1 again.
"""

from __future__ import annotations

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.billing.pricer.pricer import Pricer, TariffMode
from app.modules.billing.pricer.tariffs import tariffs, tariffs_for_auto_setting
from app.modules.common_slaves.wildberries.models import AdvSetting
from app.modules.common_slaves.wildberries.models.wb_cabinet import WBCabinet


pytestmark = [pytest.mark.integration, pytest.mark.asyncio, pytest.mark.destructive_local]


@pytest.fixture
async def wb_cabinet(async_session: AsyncSession) -> WBCabinet:
    """Baseline WBCabinet id=1 после destructive PG reset (без повторного INSERT).

    ``async_engine`` → ``reset_postgres_test_data(restore_baseline=True)`` уже
    сеет ``wbcabinet`` id=1 / ``shop_id=test_shop_id``. Повторный insert даёт
    ``UniqueViolationError`` на ``wbcabinet_pkey``.
    """
    row = await async_session.get(WBCabinet, 1)
    assert row is not None, (
        "expected baseline wbcabinet id=1 from reset_postgres_test_data"
    )
    assert row.shop_id == "test_shop_id"
    return row


def _make_search_adv(*, adv_id: int, wb_cabinet_id: int) -> AdvSetting:
    return AdvSetting(
        adv_id=adv_id,
        name=f"search_{adv_id}",
        wb_cabinet_id=wb_cabinet_id,
        active_status="started",
        bot_active=False,
    )


def _make_auto_adv(
    *,
    adv_id: int,
    wb_cabinet_id: int,
    search_adv_id: int,
    automatic_version: int,
    wl: bool,
    tp: bool,
) -> AdvSetting:
    return AdvSetting(
        adv_id=adv_id,
        name=f"auto_{adv_id}",
        wb_cabinet_id=wb_cabinet_id,
        bot_active=True,
        active_status="started",
        _search_adv_id=search_adv_id,  # noqa: SLF001
        automatic_version=automatic_version,
        auto_update_white_list=wl,
        auto_update_target_place=tp,
    )


async def test_auto_mode_applies_new_tariffs_when_any_part_auto_enabled(
    async_session: AsyncSession,
    wb_cabinet: WBCabinet,
):
    wb_cabinet_id = 1
    shop_id = "test_shop_id"

    search = _make_search_adv(adv_id=90001, wb_cabinet_id=wb_cabinet_id)
    auto = _make_auto_adv(
        adv_id=90002,
        wb_cabinet_id=wb_cabinet_id,
        search_adv_id=search.adv_id,
        automatic_version=2,
        wl=True,
        tp=False,
    )

    async_session.add_all([search, auto])
    await async_session.flush()

    details = await Pricer().get_tariff_details(async_session, shop_id)

    assert details.count == 1
    assert details.mode == TariffMode.AUTO
    assert details.price_per_adv == float(tariffs_for_auto_setting[1])
    assert details.total_per_month == float(tariffs_for_auto_setting[1])


async def test_old_mode_applies_old_tariffs_when_no_part_auto_enabled(
    async_session: AsyncSession,
    wb_cabinet: WBCabinet,
):
    wb_cabinet_id = 1
    shop_id = "test_shop_id"

    search = _make_search_adv(adv_id=90101, wb_cabinet_id=wb_cabinet_id)
    auto = _make_auto_adv(
        adv_id=90102,
        wb_cabinet_id=wb_cabinet_id,
        search_adv_id=search.adv_id,
        automatic_version=2,
        wl=False,
        tp=False,
    )

    async_session.add_all([search, auto])
    await async_session.flush()

    details = await Pricer().get_tariff_details(async_session, shop_id)

    # count=1, но режим старый, т.к. авто-настройки не включены
    assert details.count == 1
    assert details.mode == TariffMode.OLD
    assert details.price_per_adv == float(tariffs[2])
    assert details.total_per_month == float(tariffs[2])


async def test_auto_mode_applies_without_active_search_campaigns(
    async_session: AsyncSession,
    wb_cabinet: WBCabinet,
):
    wb_cabinet_id = 1
    shop_id = "test_shop_id"

    auto = _make_auto_adv(
        adv_id=90402,
        wb_cabinet_id=wb_cabinet_id,
        search_adv_id=None,
        automatic_version=2,
        wl=True,
        tp=False,
    )

    async_session.add(auto)
    await async_session.flush()

    details = await Pricer().get_tariff_details(async_session, shop_id)

    assert details.count == 0.5
    assert details.mode == TariffMode.AUTO
    assert details.total_per_month == 0.5 * float(tariffs_for_auto_setting[1])


async def test_auto_mode_triggered_by_individual_keyword_target_places(
    async_session: AsyncSession,
    wb_cabinet: WBCabinet,
):
    wb_cabinet_id = 1
    shop_id = "test_shop_id"

    search = _make_search_adv(adv_id=90601, wb_cabinet_id=wb_cabinet_id)
    auto = _make_auto_adv(
        adv_id=90602,
        wb_cabinet_id=wb_cabinet_id,
        search_adv_id=search.adv_id,
        automatic_version=1,
        wl=False,
        tp=False,
    )
    auto.individual_keywords_target_place_mode = True

    async_session.add_all([search, auto])
    await async_session.flush()

    details = await Pricer().get_tariff_details(async_session, shop_id)

    assert details.count == 1
    assert details.mode == TariffMode.AUTO
    assert details.price_per_adv == float(tariffs_for_auto_setting[1])
    assert details.total_per_month == float(tariffs_for_auto_setting[1])


async def test_count_includes_auto_advs_even_if_search_campaign_not_started(
    async_session: AsyncSession,
    wb_cabinet: WBCabinet,
):
    wb_cabinet_id = 1
    shop_id = "test_shop_id"

    search = AdvSetting(
        adv_id=90201,
        name="search_90201",
        wb_cabinet_id=wb_cabinet_id,
        active_status="paused",
        bot_active=False,
    )
    auto = _make_auto_adv(
        adv_id=90202,
        wb_cabinet_id=wb_cabinet_id,
        search_adv_id=search.adv_id,
        automatic_version=1,
        wl=True,
        tp=True,
    )

    async_session.add_all([search, auto])
    await async_session.flush()

    details = await Pricer().get_tariff_details(async_session, shop_id)
    assert details.count == 0.5
    assert details.total_per_month == 0.5 * float(tariffs_for_auto_setting[1])


async def test_auto_tariff_thresholds_apply_to_total_count(
    async_session: AsyncSession,
    wb_cabinet: WBCabinet,
):
    wb_cabinet_id = 1
    shop_id = "test_shop_id"

    search = _make_search_adv(adv_id=90301, wb_cabinet_id=wb_cabinet_id)
    async_session.add(search)
    await async_session.flush()

    # 4 кампании -> порог <=10 => 3000
    autos = [
        _make_auto_adv(
            adv_id=90310 + i,
            wb_cabinet_id=wb_cabinet_id,
            search_adv_id=search.adv_id,
            automatic_version=1,
            wl=True if i == 0 else False,  # достаточно одной, чтобы включить AUTO
            tp=False,
        )
        for i in range(4)
    ]
    async_session.add_all(autos)
    await async_session.flush()

    details = await Pricer().get_tariff_details(async_session, shop_id)
    assert details.count == 4
    assert details.mode == TariffMode.AUTO
    assert details.price_per_adv == float(tariffs_for_auto_setting[10])
    assert details.total_per_month == 4 * float(tariffs_for_auto_setting[10])

