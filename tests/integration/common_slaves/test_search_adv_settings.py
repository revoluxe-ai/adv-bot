"""Integration tests for legacy search AdvSetting synchronization helper."""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.common_slaves.wildberries.models import AdvSetting
from app.modules.common_slaves.wildberries.models.wb_cabinet import WBCabinet
from app.modules.common_slaves.wildberries.search_adv_settings import (
    ensure_search_adv_setting_for_main_adv,
)
from app.modules.shop_runner.service_manager.wb_shop_data_manager.dto.complex_adv import (
    ComplexAdv,
)

pytestmark = [pytest.mark.integration, pytest.mark.asyncio]


async def test_helper_creates_search_row_with_unknown_when_status_absent(
    async_session: AsyncSession,
) -> None:
    """Missing WB status creates a usable search row without fake ready_for_start."""
    wb_cabinet = WBCabinet(
        shop_id="test_search_helper_create",
        active=True,
        demo=True,
        balance=0.0,
        bonus=0.0,
        default_max_cpm=500,
    )
    async_session.add(wb_cabinet)
    await async_session.flush()

    main_adv = AdvSetting(
        adv_id=37848355,
        name="Main campaign",
        max_place=1,
        max_cpm=500,
        active_status="started",
        wb_cabinet_id=wb_cabinet.id,
        bidder_active=False,
        parsing_active=False,
        bot_active=True,
        reset_place=True,
        type=8,
        nmids=[1096147565],
        hard_min_ctr=0.1,
        _search_adv_id=37848369,
    )
    async_session.add(main_adv)
    await async_session.flush()

    search_adv = await ensure_search_adv_setting_for_main_adv(
        async_session,
        main_adv,
        37848369,
        active_status=None,
        nmids=[1096147565],
    )
    await async_session.commit()

    complex_adv = ComplexAdv(main_adv, search_adv)
    assert complex_adv.search_adv is search_adv
    assert complex_adv.auction_adv_id == 37848369
    assert search_adv.active_status == "unknown"
    assert complex_adv.search_adv_active_status_str is None


async def test_helper_sets_ready_for_start_only_when_status_explicit(
    async_session: AsyncSession,
) -> None:
    """Explicit WB status mapping to code 4 may create ready_for_start."""
    wb_cabinet = WBCabinet(
        shop_id="test_search_helper_ready",
        active=True,
        demo=True,
        balance=0.0,
        bonus=0.0,
        default_max_cpm=500,
    )
    async_session.add(wb_cabinet)
    await async_session.flush()

    main_adv = AdvSetting(
        adv_id=4000,
        name="Main campaign",
        max_place=1,
        max_cpm=500,
        active_status="started",
        wb_cabinet_id=wb_cabinet.id,
        bidder_active=False,
        parsing_active=False,
        bot_active=True,
        reset_place=True,
        type=8,
        nmids=[1096147565],
        hard_min_ctr=0.1,
        _search_adv_id=4001,
    )
    async_session.add(main_adv)
    await async_session.flush()

    search_adv = await ensure_search_adv_setting_for_main_adv(
        async_session,
        main_adv,
        4001,
        active_status="ready_for_start",
        nmids=[1096147565],
    )
    await async_session.commit()

    assert search_adv.active_status == "ready_for_start"


@pytest.mark.parametrize("new_status", [None, "unknown"])
async def test_helper_preserves_existing_search_row_status_when_new_status_is_not_explicit(
    async_session: AsyncSession,
    new_status: str | None,
) -> None:
    """Existing search rows keep their current status when new WB status is absent/unknown."""
    old_cabinet = WBCabinet(
        shop_id="test_search_helper_old",
        active=True,
        demo=True,
        balance=0.0,
        bonus=0.0,
        default_max_cpm=300,
    )
    new_cabinet = WBCabinet(
        shop_id="test_search_helper_new",
        active=True,
        demo=True,
        balance=0.0,
        bonus=0.0,
        default_max_cpm=700,
    )
    async_session.add_all([old_cabinet, new_cabinet])
    await async_session.flush()

    main_adv = AdvSetting(
        adv_id=5000,
        name="Main campaign",
        max_place=1,
        max_cpm=700,
        active_status="started",
        wb_cabinet_id=new_cabinet.id,
        bidder_active=False,
        parsing_active=False,
        bot_active=True,
        reset_place=True,
        type=8,
        nmids=[101],
        hard_min_ctr=0.1,
        _search_adv_id=6000,
    )
    existing_search = AdvSetting(
        adv_id=6000,
        name="Manual search row",
        max_place=3,
        max_cpm=321,
        active_status="pause",
        wb_cabinet_id=old_cabinet.id,
        bidder_active=True,
        parsing_active=False,
        bot_active=True,
        reset_place=True,
        type=9,
        nmids=[999],
        hard_min_ctr=0.1,
        cpm=777,
    )
    async_session.add_all([main_adv, existing_search])
    await async_session.flush()

    updated_search = await ensure_search_adv_setting_for_main_adv(
        async_session,
        main_adv,
        6000,
        active_status=new_status,
        nmids=[101],
    )
    await async_session.commit()

    assert updated_search.id == existing_search.id
    assert updated_search.name == "Manual search row"
    assert updated_search.cpm == 777
    assert updated_search.max_cpm == 321
    assert updated_search.nmids == [999]
    assert updated_search.wb_cabinet_id == new_cabinet.id
    assert updated_search.active_status == "pause"
