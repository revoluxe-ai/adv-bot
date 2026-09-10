"""Integration: apply campaign/shop defaults handlers against live test PG.

Fixtures reuse baseline ``wbcabinet`` id=1 from
``reset_postgres_test_data(restore_baseline=True)`` вЂ” do not INSERT id=1 again
via ``WBCabinetFactory`` (Sequence starts at 1 в†’ UniqueViolation on pkey).
"""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from aiogram.types import CallbackQuery, Chat, Message, User as TelegramUser
from sqlalchemy.ext.asyncio import AsyncSession

from app.client_bot.modules.default_settings.default_models.common_default import (
    CampaignDefaultsV1,
)
from app.client_bot.user_interface.handlers.adv_setting import (
    apply_campaign_defaults,  # РҐСЌРЅРґР»РµСЂ РґР»СЏ РѕРґРЅРѕР№ РєР°РјРїР°РЅРёРё
    apply_defaults_for_shop,  # РҐСЌРЅРґР»РµСЂ РґР»СЏ РІСЃРµС… РєР°РјРїР°РЅРёР№ РјР°РіР°Р·РёРЅР°
    turn_adv_on,  # РҐСЌРЅРґР»РµСЂ РґР»СЏ РІРєР»СЋС‡РµРЅРёСЏ РѕРґРЅРѕР№ РєР°РјРїР°РЅРёРё
)
from app.client_bot.user_interface.views.callbacks import (
    ApplyCampaignDefaults,
    ApplyDefaultsForShop,
    TurnBot,
)
from app.modules.common_slaves.wildberries.models import AdvSetting
from app.modules.common_slaves.wildberries.models.enums import OrdersSourceForAutoMode
from app.modules.common_slaves.wildberries.models.fact_methods_enum import FactMethods
from app.modules.common_slaves.wildberries.models.models import (
    BidderCoroutineType,
    WBUserCabinet,
)
from app.modules.common_slaves.wildberries.models.wb_cabinet import WBCabinet
from app.utils.db.models import User

# Р¤Р°Р±СЂРёРєРё РґР»СЏ UserCabinet / AdvSetting; РєР°Р±РёРЅРµС‚ Р±РµСЂС‘Рј РёР· baseline (РЅРµ WBCabinetFactory)
from tests.factories.adv_factory import AdvSettingFactory, WBUserCabinetFactory


pytestmark = [pytest.mark.integration, pytest.mark.asyncio, pytest.mark.destructive_local]

# Shared-defaults path (``apply_common_defaults_settings_for_adv``) applies only
# ``CommonCampaignDefaultsPolicy``. FREE/PAID overlay fields stay untouched.
_COMMON_DEFAULT_FIELDS = (
    "bidder_mode",
    "bidder_coroutine_type",
    "orders_source_for_auto_mode",
    "sales_predict_method",
    "auto_budget_watchdog_enabled",
    "use_common_budget",
    "target_ctr_mode",
    "new_auto_min_ctr_mode",
    "reset_place",
)
_MODE_OVERLAY_FIELDS = (
    "bidder_active",
    "bidder_for_auto",
    "auto_update_white_list",
    "auto_update_target_place",
    "auto_update_minus_phrases",
)


def _assert_common_defaults_applied(
    updated: AdvSetting,
    *,
    expected: CampaignDefaultsV1,
    overlay_before: dict[str, object],
) -> None:
    """Assert common policy fields match defaults; mode overlays unchanged."""
    for key in _COMMON_DEFAULT_FIELDS:
        assert hasattr(updated, key), f"AdvSetting missing attribute {key}"
        assert getattr(updated, key) == getattr(expected, key), f"Mismatch for {key}"
    for key in _MODE_OVERLAY_FIELDS:
        assert getattr(updated, key) == overlay_before[key], (
            f"Mode overlay field {key} must not change under common apply"
        )


class MockSessionMaker:
    """РњРѕРє РґР»СЏ session maker, С‡С‚РѕР±С‹ С…СЌРЅРґР»РµСЂС‹ РёСЃРїРѕР»СЊР·РѕРІР°Р»Рё С‚РµСЃС‚РѕРІСѓСЋ СЃРµСЃСЃРёСЋ"""
    def __init__(self, session):
        self.session = session
    def __call__(self, read_only=False):
        return self
    async def __aenter__(self):
        return self.session
    async def __aexit__(self, *args):
        pass


async def _baseline_wb_cabinet(async_session: AsyncSession) -> WBCabinet:
    """Р’РµСЂРЅСѓС‚СЊ baseline WBCabinet id=1 РїРѕСЃР»Рµ destructive PG reset (Р±РµР· РїРѕРІС‚РѕСЂРЅРѕРіРѕ INSERT)."""
    row = await async_session.get(WBCabinet, 1)
    assert row is not None, (
        "expected baseline wbcabinet id=1 from reset_postgres_test_data"
    )
    assert row.shop_id == "test_shop_id"
    return row


def _build_wb_user_cabinet(*, user: User, wb_cabinet: WBCabinet) -> WBUserCabinet:
    """РЎРѕР±СЂР°С‚СЊ WBUserCabinet Р±РµР· factory Sequence id (РёР·Р±РµРіР°РµС‚ wbusercabinet_pkey).

    ``WBUserCabinetFactory.id = Sequence(n+1)`` СЃС‚Р°СЂС‚СѓРµС‚ СЃ 1 Рё РєРѕРЅС„Р»РёРєС‚СѓРµС‚ СЃ
    residual rows / РЅРµРѕС‚РґРІРёРЅСѓС‚С‹Рј sequence РїРѕСЃР»Рµ РіРѕРЅРѕРє truncate. РџРѕСЃР»Рµ
    ``TRUNCATE ... RESTART IDENTITY`` id РЅР°Р·РЅР°С‡Р°РµС‚ PostgreSQL.
    """
    wb_user_cabinet = WBUserCabinetFactory.build(user=user, wb_cabinet=wb_cabinet)
    # Drop factory Sequence id so INSERT omits PK в†’ DB serial after RESTART IDENTITY.
    wb_user_cabinet.id = None  # type: ignore[assignment]
    wb_user_cabinet.wb_cabinet_id = int(wb_cabinet.id)
    assert user.id is not None, "user must be flushed before linking WBUserCabinet"
    wb_user_cabinet.user_id = int(user.id)
    return wb_user_cabinet


@pytest.fixture
def mock_bot():
    return AsyncMock()


@pytest.fixture
def mock_state():
    state = AsyncMock()
    state.update_data = AsyncMock()
    state.get_data = AsyncMock(return_value={"last_wb_user_cabinet_original_id": 1})
    return state


@pytest.fixture
async def setup_adv_data(async_session: AsyncSession):
    """Seed user/cabinet/advs inside the fixture transaction (flush, not commit).

    ``async_session`` already opened an outer transaction; ``commit()``+``refresh()``
    breaks that boundary and can leave orphaned rows when setup errors mid-way.
    """
    user = User(user_telegram_id=12345, username="test_user")
    async_session.add(user)
    await async_session.flush()

    # Baseline wbcabinet id=1 СѓР¶Рµ СЃРµРµС‚СЃСЏ reset_postgres_test_data вЂ” РЅРµ INSERT С‡РµСЂРµР· factory
    wb_cabinet = await _baseline_wb_cabinet(async_session)

    wb_user_cabinet = _build_wb_user_cabinet(user=user, wb_cabinet=wb_cabinet)
    async_session.add(wb_user_cabinet)
    await async_session.flush()
    assert wb_user_cabinet.id is not None, "wbusercabinet id must be assigned on flush"
    assert await async_session.get(WBUserCabinet, wb_user_cabinet.id) is not None

    # РЎРѕР·РґР°РµРј AdvSetting СЃ РЅРµРґРµС„РѕР»С‚РЅС‹РјРё Р·РЅР°С‡РµРЅРёСЏРјРё
    adv_setting = AdvSettingFactory.build(
        adv_id=1000,
        name="Test Campaign 1",
        wb_cabinet=wb_cabinet,
        wb_cabinet_id=wb_cabinet.id,
        bot_active=True,  # РђРєС‚РёРІРЅР°СЏ РєР°РјРїР°РЅРёСЏ
        bidder_active=False,  # РќРµРґРµС„РѕР»С‚РЅРѕРµ Р·РЅР°С‡РµРЅРёРµ
        auto_update_white_list=False,  # РќРµРґРµС„РѕР»С‚РЅРѕРµ Р·РЅР°С‡РµРЅРёРµ
    )
    async_session.add(adv_setting)
    await async_session.flush()

    adv_setting_inactive = AdvSettingFactory.build(
        adv_id=1001,
        name="Test Campaign Inactive",
        wb_cabinet=wb_cabinet,
        wb_cabinet_id=wb_cabinet.id,
        bot_active=False,  # РќРµР°РєС‚РёРІРЅР°СЏ РєР°РјРїР°РЅРёСЏ
        bidder_active=False,  # РќРµРґРµС„РѕР»С‚РЅРѕРµ Р·РЅР°С‡РµРЅРёРµ
        auto_update_white_list=False,  # РќРµРґРµС„РѕР»С‚РЅРѕРµ Р·РЅР°С‡РµРЅРёРµ
    )
    async_session.add(adv_setting_inactive)
    await async_session.flush()
    assert adv_setting.id is not None
    assert adv_setting_inactive.id is not None

    return {
        "user": user,
        "wb_cabinet": wb_cabinet,
        "wb_user_cabinet": wb_user_cabinet,
        "adv_setting": adv_setting,
        "adv_setting_inactive": adv_setting_inactive,
    }


@pytest.fixture
async def setup_multiple_advs_data(async_session: AsyncSession):
    """Seed multi-adv shop data with flush-only fixture writes (СЃРј. setup_adv_data)."""
    user = User(user_telegram_id=45678, username="test_user_multi")
    async_session.add(user)
    await async_session.flush()

    # Baseline wbcabinet id=1 вЂ” Р±РµР· РїРѕРІС‚РѕСЂРЅРѕРіРѕ INSERT (СЃРј. setup_adv_data)
    wb_cabinet = await _baseline_wb_cabinet(async_session)

    wb_user_cabinet = _build_wb_user_cabinet(user=user, wb_cabinet=wb_cabinet)
    async_session.add(wb_user_cabinet)
    await async_session.flush()
    assert wb_user_cabinet.id is not None

    # РђРєС‚РёРІРЅС‹Рµ РєР°РјРїР°РЅРёРё СЃ РЅРµРґРµС„РѕР»С‚РЅС‹РјРё Р·РЅР°С‡РµРЅРёСЏРјРё
    adv_active_1 = AdvSettingFactory.build(
        adv_id=2000,
        name="Multi Adv Active 1",
        wb_cabinet=wb_cabinet,
        wb_cabinet_id=wb_cabinet.id,
        bot_active=True,
        bidder_active=False,
    )
    adv_active_2 = AdvSettingFactory.build(
        adv_id=2001,
        name="Multi Adv Active 2",
        wb_cabinet=wb_cabinet,
        wb_cabinet_id=wb_cabinet.id,
        bot_active=True,
        bidder_active=False,
    )
    # РќРµР°РєС‚РёРІРЅР°СЏ РєР°РјРїР°РЅРёСЏ
    adv_inactive_1 = AdvSettingFactory.build(
        adv_id=2002,
        name="Multi Adv Inactive 1",
        wb_cabinet=wb_cabinet,
        wb_cabinet_id=wb_cabinet.id,
        bot_active=False,
        bidder_active=True,  # РќРµРґРµС„РѕР»С‚РЅРѕРµ Р·РЅР°С‡РµРЅРёРµ, РЅРѕ РЅРµ РґРѕР»Р¶РЅРѕ Р±С‹С‚СЊ РёР·РјРµРЅРµРЅРѕ
    )
    async_session.add_all([adv_active_1, adv_active_2, adv_inactive_1])
    await async_session.flush()

    return {
        "user": user,
        "wb_cabinet": wb_cabinet,
        "wb_user_cabinet": wb_user_cabinet,
        "adv_active_1": adv_active_1,
        "adv_active_2": adv_active_2,
        "adv_inactive_1": adv_inactive_1,
    }


@pytest.mark.integration
async def test_apply_campaign_defaults_single_active_campaign(
    mock_bot, async_session: AsyncSession, setup_adv_data
):
    adv_setting = setup_adv_data["adv_setting"]
    wb_user_cabinet = setup_adv_data["wb_user_cabinet"]

    initial_defaults = CampaignDefaultsV1()

    # Invert common-policy fields so apply must rewrite them; leave overlays alone.
    adv_setting.target_ctr_mode = not initial_defaults.target_ctr_mode
    adv_setting.new_auto_min_ctr_mode = not initial_defaults.new_auto_min_ctr_mode
    adv_setting.reset_place = not initial_defaults.reset_place
    adv_setting.auto_budget_watchdog_enabled = (
        not initial_defaults.auto_budget_watchdog_enabled
    )
    adv_setting.use_common_budget = not initial_defaults.use_common_budget
    adv_setting.bot_active = True
    if initial_defaults.bidder_coroutine_type == BidderCoroutineType.UPDATE_CLUSTER_BIDS:
        adv_setting.bidder_coroutine_type = BidderCoroutineType.OLD_UPDATE_CPM_BIDDER
    else:
        adv_setting.bidder_coroutine_type = BidderCoroutineType.UPDATE_CLUSTER_BIDS
    if initial_defaults.orders_source_for_auto_mode == OrdersSourceForAutoMode.COMMON_STATISTIC:
        adv_setting.orders_source_for_auto_mode = OrdersSourceForAutoMode.ADV_SUM
    else:
        adv_setting.orders_source_for_auto_mode = OrdersSourceForAutoMode.COMMON_STATISTIC
    if initial_defaults.sales_predict_method == FactMethods.BY_CARTS:
        adv_setting.sales_predict_method = FactMethods.DIRECT_SALES
    else:
        adv_setting.sales_predict_method = FactMethods.BY_CARTS

    overlay_before = {key: getattr(adv_setting, key) for key in _MODE_OVERLAY_FIELDS}
    await async_session.flush()

    # Р’С‹Р·С‹РІР°РµРј С…СЌРЅРґР»РµСЂ
    callback_data = ApplyCampaignDefaults(
        adv_setting_original_id=adv_setting.id,
        wb_user_cabinet_original_id=wb_user_cabinet.id,
    )
    telegram_user = TelegramUser(
        id=wb_user_cabinet.user.user_telegram_id,
        is_bot=False,
        first_name="Test",
    )
    chat = Chat(id=wb_user_cabinet.user.user_telegram_id, type="private")
    message = Message(
        message_id=1,
        date=1234567890,
        chat=chat,
        from_user=telegram_user,
    )
    callback_query = CallbackQuery(
        id="123",
        from_user=telegram_user,
        chat_instance="some_id",
        data=callback_data.pack(),
        message=message,
    )

    mock_menu_instance = AsyncMock()
    mock_menu_instance.return_value = None

    # РњРѕРєР°РµРј session maker С‡С‚РѕР±С‹ С…СЌРЅРґР»РµСЂ РёСЃРїРѕР»СЊР·РѕРІР°Р» С‚РµСЃС‚РѕРІСѓСЋ СЃРµСЃСЃРёСЋ
    class MockSessionMaker:
        def __init__(self, session):
            self.session = session
        def __call__(self, read_only=False):
            return self
        async def __aenter__(self):
            return self.session
        async def __aexit__(self, *args):
            pass

    with (
        patch(
            "app.client_bot.user_interface.handlers.adv_setting.adv_setting.sm",
            MockSessionMaker(async_session),
        ),
        patch(
            "app.client_bot.user_interface.handlers.adv_setting.adv_setting.AdvSettingMenu",
            return_value=mock_menu_instance,
        ),
    ):
        await apply_campaign_defaults(callback_query, callback_data, mock_bot)

    # Handler commits on the shared test session; re-load for assertion freshness
    updated_adv_setting = await async_session.get(AdvSetting, adv_setting.id)
    assert updated_adv_setting is not None

    _assert_common_defaults_applied(
        updated_adv_setting,
        expected=CampaignDefaultsV1(),
        overlay_before=overlay_before,
    )


@pytest.mark.integration
async def test_apply_campaign_defaults_single_inactive_campaign(
    mock_bot, async_session: AsyncSession, setup_adv_data
):
    adv_setting_inactive = setup_adv_data["adv_setting_inactive"]
    wb_user_cabinet = setup_adv_data["wb_user_cabinet"]

    overlay_before = {
        key: getattr(adv_setting_inactive, key) for key in _MODE_OVERLAY_FIELDS
    }

    callback_data = ApplyCampaignDefaults(
        adv_setting_original_id=adv_setting_inactive.id,
        wb_user_cabinet_original_id=wb_user_cabinet.id,
    )
    telegram_user = TelegramUser(
        id=wb_user_cabinet.user.user_telegram_id,
        is_bot=False,
        first_name="Test",
    )
    chat = Chat(id=wb_user_cabinet.user.user_telegram_id, type="private")
    message = Message(
        message_id=1,
        date=1234567890,
        chat=chat,
        from_user=telegram_user,
    )
    callback_query = CallbackQuery(
        id="124",
        from_user=telegram_user,
        chat_instance="some_id_inactive",
        data=callback_data.pack(),
        message=message,
    )

    # flush-only: keep outer fixture transaction (СЃРј. active-campaign test)
    await async_session.flush()

    mock_menu_instance = AsyncMock()
    with (
        patch(
            "app.client_bot.user_interface.handlers.adv_setting.adv_setting.sm",
            MockSessionMaker(async_session),
        ),
        patch(
            "app.client_bot.user_interface.handlers.adv_setting.adv_setting.AdvSettingMenu",
            return_value=mock_menu_instance,
        ),
    ):
        await apply_campaign_defaults(callback_query, callback_data, mock_bot)

    updated_adv_setting = await async_session.get(AdvSetting, adv_setting_inactive.id)
    assert updated_adv_setting is not None

    _assert_common_defaults_applied(
        updated_adv_setting,
        expected=CampaignDefaultsV1(),
        overlay_before=overlay_before,
    )


@pytest.mark.integration
async def test_turn_adv_on_applies_defaults(
    mock_bot, mock_state, async_session: AsyncSession, setup_adv_data
):
    adv_setting_inactive = setup_adv_data["adv_setting_inactive"]
    wb_user_cabinet = setup_adv_data["wb_user_cabinet"]

    # РџСЂРѕРІРµСЂСЏРµРј, С‡С‚Рѕ РёР·РЅР°С‡Р°Р»СЊРЅРѕ Р±РѕС‚ РЅРµР°РєС‚РёРІРµРЅ
    assert not adv_setting_inactive.bot_active

    # РЎРѕС…СЂР°РЅСЏРµРј РЅРµРґРµС„РѕР»С‚РЅС‹Рµ Р·РЅР°С‡РµРЅРёСЏ
    initial_defaults = CampaignDefaultsV1()
    # РЇРІРЅРѕ СѓСЃС‚Р°РЅР°РІР»РёРІР°РµРј РѕС‚Р»РёС‡Р°СЋС‰РёРµСЃСЏ Р·РЅР°С‡РµРЅРёСЏ РґР»СЏ С‚РµСЃС‚РѕРІРѕР№ РєР°РјРїР°РЅРёРё
    # Р”Р»СЏ Р±СѓР»РµРІС‹С… РїРѕР»РµР№ РёРЅРІРµСЂС‚РёСЂСѓРµРј Р·РЅР°С‡РµРЅРёРµ
    adv_setting_inactive.bidder_active = not initial_defaults.bidder_active
    adv_setting_inactive.auto_update_white_list = not initial_defaults.auto_update_white_list
    adv_setting_inactive.auto_update_target_place = not initial_defaults.auto_update_target_place
    adv_setting_inactive.target_ctr_mode = not initial_defaults.target_ctr_mode
    adv_setting_inactive.new_auto_min_ctr_mode = not initial_defaults.new_auto_min_ctr_mode
    adv_setting_inactive.reset_place = not initial_defaults.reset_place
    adv_setting_inactive.bot_active = False

    # bidder_coroutine_type
    if initial_defaults.bidder_coroutine_type == BidderCoroutineType.UPDATE_CLUSTER_BIDS:
        adv_setting_inactive.bidder_coroutine_type = BidderCoroutineType.OLD_UPDATE_CPM_BIDDER
    else:
        adv_setting_inactive.bidder_coroutine_type = BidderCoroutineType.UPDATE_CLUSTER_BIDS

    # orders_source_for_auto_mode
    if initial_defaults.orders_source_for_auto_mode == OrdersSourceForAutoMode.COMMON_STATISTIC:
        adv_setting_inactive.orders_source_for_auto_mode = OrdersSourceForAutoMode.ADV_SUM
    else:
        adv_setting_inactive.orders_source_for_auto_mode = OrdersSourceForAutoMode.COMMON_STATISTIC

    # sales_predict_method
    if initial_defaults.sales_predict_method == FactMethods.BY_CARTS:
        adv_setting_inactive.sales_predict_method = FactMethods.DIRECT_SALES
    else:
        adv_setting_inactive.sales_predict_method = FactMethods.BY_CARTS

    await async_session.flush()

    # Р’С‹Р·С‹РІР°РµРј С…СЌРЅРґР»РµСЂ turn_adv_on
    callback_data = TurnBot(
        action="on",
        adv_original_id=adv_setting_inactive.id,
        wb_user_cabinet_original_id=wb_user_cabinet.id,
    )
    telegram_user = TelegramUser(
        id=wb_user_cabinet.user.user_telegram_id,
        is_bot=False,
        first_name="Test",
    )
    chat = Chat(id=wb_user_cabinet.user.user_telegram_id, type="private")
    message = Message(
        message_id=1,
        date=1234567890,
        chat=chat,
        from_user=telegram_user,
    )
    callback_query = CallbackQuery(
        id="125",
        from_user=telegram_user,
        chat_instance="some_id_turn_on",
        data=callback_data.pack(),
        message=message,
    )

    # Mock Pricer.get_price_for_day_for_shop and balance_manager.get_cabinet_balance_and_bonuses
    with (
        patch("app.modules.billing.pricer.Pricer.get_price_for_day_for_shop", new_callable=AsyncMock) as mock_get_price,
        patch("app.modules.billing.pricer.Pricer.get_tariff_for_day", return_value=100) as mock_get_tariff,
        patch("app.modules.balance_manager.get_cabinet_balance_and_bonuses", new_callable=AsyncMock) as mock_get_balance,
    ):
        mock_get_price.return_value = 100
        mock_get_balance.return_value = (1000, 0) # Р”РѕСЃС‚Р°С‚РѕС‡РЅРѕ СЃСЂРµРґСЃС‚РІ

        mock_menu_instance = AsyncMock()
        with (
            patch(
                "app.client_bot.user_interface.handlers.adv_setting.adv_setting.sm",
                MockSessionMaker(async_session),
            ),
            patch(
                "app.client_bot.user_interface.handlers.adv_setting.adv_setting.AdvSettingMenu",
                return_value=mock_menu_instance,
            ),
            patch(
                "app.client_bot.user_interface.handlers.adv_setting.adv_setting._shop_has_read_only_only_tokens",
                AsyncMock(return_value=False),
            ),
        ):
            await turn_adv_on(callback_query, mock_state, callback_data, mock_bot)

    # РџСЂРѕРІРµСЂСЏРµРј С‚РѕР»СЊРєРѕ bot_active, РґРµС„РѕР»С‚С‹ РќР• РґРѕР»Р¶РЅС‹ РїСЂРёРјРµРЅСЏС‚СЊСЃСЏ
    expected_bidder_active = adv_setting_inactive.bidder_active
    updated_adv_setting = await async_session.get(AdvSetting, adv_setting_inactive.id)
    assert updated_adv_setting is not None

    assert updated_adv_setting.bot_active
    # РћСЃС‚Р°Р»СЊРЅС‹Рµ РЅР°СЃС‚СЂРѕР№РєРё (РЅР°РїСЂРёРјРµСЂ, bidder_active) РЅРµ РґРѕР»Р¶РЅС‹ СЃР±СЂР°СЃС‹РІР°С‚СЊСЃСЏ Рє РґРµС„РѕР»С‚Р°Рј
    assert updated_adv_setting.bidder_active == expected_bidder_active


@pytest.mark.integration
async def test_apply_defaults_for_shop_multiple_campaigns(
    mock_bot, mock_state, async_session: AsyncSession, setup_multiple_advs_data
):
    wb_user_cabinet = setup_multiple_advs_data["wb_user_cabinet"]
    adv_active_1 = setup_multiple_advs_data["adv_active_1"]
    adv_active_2 = setup_multiple_advs_data["adv_active_2"]
    adv_inactive_1 = setup_multiple_advs_data["adv_inactive_1"]

    initial_defaults = CampaignDefaultsV1()
    overlays_before: dict[int, dict[str, object]] = {}
    for adv in [adv_active_1, adv_active_2]:
        adv.target_ctr_mode = not initial_defaults.target_ctr_mode
        adv.new_auto_min_ctr_mode = not initial_defaults.new_auto_min_ctr_mode
        adv.reset_place = not initial_defaults.reset_place
        adv.auto_budget_watchdog_enabled = (
            not initial_defaults.auto_budget_watchdog_enabled
        )
        adv.use_common_budget = not initial_defaults.use_common_budget
        adv.bot_active = True
        if initial_defaults.bidder_coroutine_type == BidderCoroutineType.UPDATE_CLUSTER_BIDS:
            adv.bidder_coroutine_type = BidderCoroutineType.OLD_UPDATE_CPM_BIDDER
        else:
            adv.bidder_coroutine_type = BidderCoroutineType.UPDATE_CLUSTER_BIDS
        if initial_defaults.orders_source_for_auto_mode == OrdersSourceForAutoMode.COMMON_STATISTIC:
            adv.orders_source_for_auto_mode = OrdersSourceForAutoMode.ADV_SUM
        else:
            adv.orders_source_for_auto_mode = OrdersSourceForAutoMode.COMMON_STATISTIC
        if initial_defaults.sales_predict_method == FactMethods.BY_CARTS:
            adv.sales_predict_method = FactMethods.DIRECT_SALES
        else:
            adv.sales_predict_method = FactMethods.BY_CARTS
        overlays_before[int(adv.id)] = {
            key: getattr(adv, key) for key in _MODE_OVERLAY_FIELDS
        }


    await async_session.flush()

    # Р’С‹Р·С‹РІР°РµРј С…СЌРЅРґР»РµСЂ РґР»СЏ РјР°РіР°Р·РёРЅР°
    callback_data = ApplyDefaultsForShop(wb_user_cabinet_original_id=wb_user_cabinet.id)
    telegram_user = TelegramUser(
        id=wb_user_cabinet.user.user_telegram_id,
        is_bot=False,
        first_name="Test",
    )
    chat = Chat(id=wb_user_cabinet.user.user_telegram_id, type="private")
    message = Message(
        message_id=1,
        date=1234567890,
        chat=chat,
        from_user=telegram_user,
    )
    callback_query = CallbackQuery(
        id="126",
        from_user=telegram_user,
        chat_instance="some_id_shop_defaults",
        data=callback_data.pack(),
        message=message,
    )

    mock_shop_menu = AsyncMock()
    with (
        patch(
            "app.client_bot.user_interface.handlers.adv_setting.adv_setting.sm",
            MockSessionMaker(async_session),
        ),
        patch(
            "app.client_bot.user_interface.handlers.adv_setting.adv_setting.ShopMenu",
            return_value=mock_shop_menu,
        ),
    ):
        await apply_defaults_for_shop(callback_query, callback_data, mock_bot, mock_state)

    expected_defaults = CampaignDefaultsV1()
    for adv_id in (adv_active_1.id, adv_active_2.id):
        updated = await async_session.get(AdvSetting, adv_id)
        assert updated is not None
        assert adv_id is not None
        _assert_common_defaults_applied(
            updated,
            expected=expected_defaults,
            overlay_before=overlays_before[int(adv_id)],
        )

    updated_inactive = await async_session.get(AdvSetting, adv_inactive_1.id)
    assert updated_inactive is not None
    assert updated_inactive.bot_active is False
