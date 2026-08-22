"""Integration coverage for batch-A PG seam handoffs.

Все тесты используют живой ``async_session`` и повторное чтение из БД, но не
запускают live/destructive work outside the test database.
"""

from __future__ import annotations

from datetime import datetime, timedelta
import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.client_bot.user_interface.handlers.adv_setting import adv_setting as adv_setting_handler
from app.client_bot.user_interface.handlers import keyword_settings, set_common_bid_manual
from app.modules.common_slaves.wildberries.models import (
    AdvSetting,
    KeywordSetting,
    WBCabinet,
    WBUserCabinet,
)
from app.utils.db.models import User

pytestmark = [pytest.mark.integration, pytest.mark.asyncio, pytest.mark.destructive_local]


async def _create_cabinet(async_session: AsyncSession) -> WBCabinet:
    cabinet = WBCabinet(
        shop_id=f"batch_a_{uuid.uuid4().hex}",
        active=True,
        expiration_time=datetime.utcnow() + timedelta(days=7),
        balance=0.0,
        bonus=0.0,
        demo=True,
        expiration_alarm_days_pass=None,
    )
    async_session.add(cabinet)
    await async_session.flush()
    return cabinet


async def _create_user_cabinet(async_session: AsyncSession, cabinet: WBCabinet) -> WBUserCabinet:
    user = User(
        user_telegram_id=9_200_001,
        username=f"batch_a_{uuid.uuid4().hex}",
        passed_gate=True,
    )
    async_session.add(user)
    await async_session.flush()

    wb_user_cabinet = WBUserCabinet(user_id=user.id, wb_cabinet_id=cabinet.id, name="batch-a")
    async_session.add(wb_user_cabinet)
    await async_session.flush()
    return wb_user_cabinet


async def _create_keyword_fixture(
    async_session: AsyncSession,
) -> tuple[KeywordSetting, AdvSetting]:
    cabinet = await _create_cabinet(async_session)
    adv = AdvSetting(
        adv_id=777_001,
        name="keyword-target-place",
        wb_cabinet_id=cabinet.id,
        active_status="started",
        bot_active=True,
        plan_for_sales_for_day=1,
        target_price_for_order=100.0,
        max_price_for_order=150.0,
        max_cpm=1000,
        cpm=100,
    )
    async_session.add(adv)
    await async_session.flush()

    keyword = KeywordSetting(
        adv_setting_id=adv.id,
        text="alpha",
        hard_status=1,
        target_place=5,
    )
    async_session.add(keyword)
    await async_session.flush()
    return keyword, adv


async def _create_common_bid_fixture(
    async_session: AsyncSession,
) -> tuple[AdvSetting, AdvSetting, WBUserCabinet]:
    cabinet = await _create_cabinet(async_session)
    wb_user_cabinet = await _create_user_cabinet(async_session, cabinet)

    main_adv = AdvSetting(
        adv_id=888_001,
        name="main-common-bid",
        wb_cabinet_id=cabinet.id,
        active_status="started",
        bot_active=True,
        plan_for_sales_for_day=1,
        target_price_for_order=100.0,
        max_price_for_order=150.0,
        max_cpm=1000,
        cpm=100,
        search_adv_id=888_002,
        nmids=[12345, 67890],
    )
    search_adv = AdvSetting(
        adv_id=888_002,
        name="search-common-bid",
        wb_cabinet_id=cabinet.id,
        active_status="started",
        bot_active=True,
        plan_for_sales_for_day=1,
        target_price_for_order=100.0,
        max_price_for_order=150.0,
        max_cpm=1000,
        cpm=100,
        nmids=[12345, 67890],
    )
    async_session.add_all([main_adv, search_adv])
    await async_session.flush()
    return main_adv, search_adv, wb_user_cabinet


async def test_turn_adv_on_in_session_persists_bot_active(
    async_session: AsyncSession,
) -> None:
    """WRITE session confirms bot activation by re-reading AdvSetting.bot_active."""
    cabinet = await _create_cabinet(async_session)
    wb_user_cabinet = await _create_user_cabinet(async_session, cabinet)
    adv = AdvSetting(
        adv_id=123_777,
        name="turn-adv-on",
        wb_cabinet_id=cabinet.id,
        active_status="started",
        bot_active=False,
        plan_for_sales_for_day=1,
        target_price_for_order=100.0,
        max_price_for_order=150.0,
        max_cpm=1000,
        cpm=100,
    )
    async_session.add(adv)
    await async_session.flush()
    adv_pk = adv.id
    wb_user_cabinet_pk = wb_user_cabinet.id

    callback = SimpleNamespace(
        message=SimpleNamespace(chat=SimpleNamespace(id=202)),
    )
    callback_data = SimpleNamespace(
        wb_user_cabinet_original_id=wb_user_cabinet_pk,
        adv_original_id=adv_pk,
    )
    bot = AsyncMock()
    state = AsyncMock()

    with (
        patch.object(
            adv_setting_handler,
            "balance_manager",
            MagicMock(get_cabinet_balance_and_bonuses=AsyncMock(return_value=(1000, 0))),
        ),
        patch.object(adv_setting_handler.pricer, "get_price_for_day_for_shop", AsyncMock(return_value=100)),
        patch.object(
            adv_setting_handler,
            "_shop_has_read_only_only_tokens",
            AsyncMock(return_value=False),
        ),
        patch.object(adv_setting_handler, "AdvSettingMenu", MagicMock(return_value=AsyncMock())),
    ):
        await adv_setting_handler.turn_adv_on_in_session(
            async_session,
            callback,
            state,
            callback_data,
            bot,
        )

    # Capture PKs before expire: expired instance attrs trigger MissingGreenlet.
    async_session.expire_all()
    reread = await async_session.scalar(
        select(AdvSetting.bot_active).where(AdvSetting.id == adv_pk)
    )
    assert reread is True
    state.update_data.assert_any_await(wb_user_cabinet_original_id=wb_user_cabinet_pk)
    state.update_data.assert_any_await(adv_original_id=adv_pk)


async def test_change_keyword_target_place_in_session_reads_keyword(
    async_session: AsyncSession,
) -> None:
    """Read-only session must load the same KeywordSetting row that DB stores."""
    keyword, adv = await _create_keyword_fixture(async_session)
    callback_query = SimpleNamespace(message=SimpleNamespace(chat=SimpleNamespace(id=303)))
    callback_data = SimpleNamespace(keyword_setting_original_id=keyword.id)
    bot = AsyncMock()
    state = AsyncMock()
    state.set_state = AsyncMock()
    state.update_data = AsyncMock()

    with patch.object(
        keyword_settings,
        "messages",
        MagicMock(KeywordTargetPlacePrompt=MagicMock(return_value=AsyncMock())),
    ):
        await keyword_settings.change_keyword_target_place_in_session(
            async_session,
            callback_query,
            callback_data,
            bot,
            state,
        )

    reread = await async_session.scalar(
        select(KeywordSetting.target_place).where(KeywordSetting.id == keyword.id)
    )
    assert reread == keyword.target_place
    state.update_data.assert_any_await(keyword_setting_for_target_place=keyword.id)
    state.set_state.assert_awaited()
    assert adv.id > 0


async def test_keyword_target_place_value_in_session_persists_change(
    async_session: AsyncSession,
) -> None:
    """Write session updates target_place and the new value is visible on reread."""
    keyword, _adv = await _create_keyword_fixture(async_session)
    keyword_pk = keyword.id
    message = SimpleNamespace(
        chat=SimpleNamespace(id=404),
        text="10",
        from_user=SimpleNamespace(id=77),
    )
    bot = AsyncMock()
    state = AsyncMock()
    state.get_data = AsyncMock(
        return_value={
            "keyword_setting_for_target_place": keyword_pk,
            "last_keyword_setting_page": 1,
        }
    )
    state.update_data = AsyncMock()
    state.set_state = AsyncMock()

    with (
        patch.object(
            keyword_settings,
            "messages",
            MagicMock(
                KeywordTargetPlaceUpdated=MagicMock(return_value=AsyncMock()),
                KeywordSettingMessage=MagicMock(return_value=AsyncMock()),
            ),
        ),
    ):
        await keyword_settings.keyword_target_place_value_in_session(
            async_session,
            message,
            bot,
            state,
        )

    async_session.expire_all()
    reread = await async_session.scalar(
        select(KeywordSetting.target_place).where(KeywordSetting.id == keyword_pk)
    )
    assert reread == 10
    state.update_data.assert_any_await(keyword_setting_for_target_place=None)
    state.set_state.assert_awaited()


async def test_set_common_bid_manual_start_in_session_reads_campaigns(
    async_session: AsyncSession,
) -> None:
    """Read-only session must read both campaigns and derive the min bid."""
    main_adv, search_adv, wb_user_cabinet = await _create_common_bid_fixture(async_session)
    main_adv_pk = main_adv.id
    expected_search_adv_id = search_adv.adv_id
    callback = SimpleNamespace(message=SimpleNamespace(chat=SimpleNamespace(id=505)))
    callback_data = SimpleNamespace(
        adv_setting_original_id=main_adv_pk,
        wb_user_cabinet_original_id=wb_user_cabinet.id,
    )
    bot = AsyncMock()
    state = AsyncMock()
    state.update_data = AsyncMock()
    state.set_state = AsyncMock()

    min_bids = SimpleNamespace(search={12345: 50, 67890: 75})
    hub = MagicMock()
    hub.wb_manager.get_min_bids_cache_only = AsyncMock(return_value=min_bids)
    container = MagicMock()
    container.__aenter__ = AsyncMock(return_value=container)
    container.__aexit__ = AsyncMock(return_value=None)
    container.module_resources.wb_manager_hub_factory_container.wb_manager_hub_factory.return_value.get_wb_manager_hub.return_value = hub

    with (
        patch.object(set_common_bid_manual, "_is_manual_search_campaign", return_value=True),
        patch.object(set_common_bid_manual.DIManager, "create", AsyncMock(return_value=container)),
    ):
        await set_common_bid_manual.set_common_bid_manual_start_in_session(
            async_session,
            callback,
            callback_data,
            bot,
            state,
        )

    # ``search_adv_id`` is a @property; DB column is ``_search_adv_id``.
    reread = await async_session.scalar(
        select(AdvSetting._search_adv_id).where(AdvSetting.id == main_adv_pk)  # pyright: ignore[reportPrivateUsage]
    )
    assert reread == expected_search_adv_id
    state.update_data.assert_awaited()
    state.set_state.assert_awaited()


async def test_set_common_bid_manual_apply_in_session_reads_campaigns(
    async_session: AsyncSession,
) -> None:
    """Apply path reads persisted campaigns and leaves rows available on reread."""
    main_adv, search_adv, wb_user_cabinet = await _create_common_bid_fixture(async_session)
    main_adv_pk = main_adv.id
    expected_search_adv_id = search_adv.adv_id
    message = SimpleNamespace(
        chat=SimpleNamespace(id=606),
        text="100",
        answer=AsyncMock(),
    )
    bot = AsyncMock()
    state = AsyncMock()
    state.get_data = AsyncMock(
        return_value={
            "adv_setting_original_id": main_adv_pk,
            "wb_user_cabinet_original_id": wb_user_cabinet.id,
            "min_bid_search": 50,
        }
    )
    state.set_state = AsyncMock()

    hub = MagicMock()
    hub.wb_modifier.update_search_adv_common_cpm = AsyncMock()
    hub.wb_modifier.set_normquery_bids = AsyncMock()
    hub.wb_data_manager.get_current_bids_for_advs = AsyncMock(return_value=[])
    hub.redis_client_wrapper = MagicMock()
    container = MagicMock()
    container.__aenter__ = AsyncMock(return_value=container)
    container.__aexit__ = AsyncMock(return_value=None)
    container.module_resources.wb_manager_hub_factory_container.wb_manager_hub_factory.return_value.get_wb_manager_hub.return_value = hub

    with (
        patch.object(set_common_bid_manual, "_is_manual_search_campaign", return_value=True),
        patch.object(set_common_bid_manual.DIManager, "create", AsyncMock(return_value=container)),
        patch.object(set_common_bid_manual, "RedisCommonBidValueManager") as mock_value_manager,
        patch.object(set_common_bid_manual, "RedisCommonBidTimestampManager") as mock_ts_manager,
        patch.object(set_common_bid_manual, "AdvSettingMenu", MagicMock(return_value=AsyncMock())),
    ):
        mock_value_instance = MagicMock()
        mock_value_instance.set_bids = AsyncMock()
        mock_value_manager.return_value = mock_value_instance
        mock_ts_instance = MagicMock()
        mock_ts_instance.set = AsyncMock()
        mock_ts_manager.return_value = mock_ts_instance
        await set_common_bid_manual.set_common_bid_manual_apply_in_session(
            async_session,
            message,
            bot,
            state,
        )

    reread = await async_session.scalar(
        select(AdvSetting._search_adv_id).where(AdvSetting.id == main_adv_pk)  # pyright: ignore[reportPrivateUsage]
    )
    assert reread == expected_search_adv_id
    state.set_state.assert_awaited()
    message.answer.assert_awaited()


async def test_load_adv_setting_menu_entities_in_session_reads_rows(
    async_session: AsyncSession,
) -> None:
    """PURE_READ child returns WBUserCabinet + AdvSetting via injected session."""
    main_adv, _search_adv, wb_user_cabinet = await _create_common_bid_fixture(
        async_session
    )
    cabinet_pk = wb_user_cabinet.id
    adv_pk = main_adv.id
    await async_session.commit()

    cabinet, adv = await set_common_bid_manual.load_adv_setting_menu_entities_in_session(
        async_session,
        cabinet_pk,
        adv_pk,
    )

    assert cabinet is not None
    assert adv is not None
    assert cabinet.id == cabinet_pk
    assert adv.id == adv_pk

    reread_adv = await async_session.scalar(
        select(AdvSetting.id).where(AdvSetting.id == adv_pk)
    )
    assert reread_adv == adv_pk
