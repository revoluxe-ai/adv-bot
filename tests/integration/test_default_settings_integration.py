"""Integration: apply campaign/shop defaults handlers against live test PG.

Fixtures reuse baseline ``wbcabinet`` id=1 from
``reset_postgres_test_data(restore_baseline=True)`` — do not INSERT id=1 again
via ``WBCabinetFactory`` (Sequence starts at 1 → UniqueViolation on pkey).
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
    apply_campaign_defaults,  # Хэндлер для одной кампании
    apply_defaults_for_shop,  # Хэндлер для всех кампаний магазина
    turn_adv_on,  # Хэндлер для включения одной кампании
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

# Фабрики для UserCabinet / AdvSetting; кабинет берём из baseline (не WBCabinetFactory)
from tests.factories.adv_factory import AdvSettingFactory, WBUserCabinetFactory


pytestmark = [pytest.mark.integration, pytest.mark.asyncio, pytest.mark.destructive_local]


class MockSessionMaker:
    """Мок для session maker, чтобы хэндлеры использовали тестовую сессию"""
    def __init__(self, session):
        self.session = session
    def __call__(self, read_only=False):
        return self
    async def __aenter__(self):
        return self.session
    async def __aexit__(self, *args):
        pass


async def _baseline_wb_cabinet(async_session: AsyncSession) -> WBCabinet:
    """Вернуть baseline WBCabinet id=1 после destructive PG reset (без повторного INSERT)."""
    row = await async_session.get(WBCabinet, 1)
    assert row is not None, (
        "expected baseline wbcabinet id=1 from reset_postgres_test_data"
    )
    assert row.shop_id == "test_shop_id"
    return row


def _build_wb_user_cabinet(*, user: User, wb_cabinet: WBCabinet) -> WBUserCabinet:
    """Собрать WBUserCabinet без factory Sequence id (избегает wbusercabinet_pkey).

    ``WBUserCabinetFactory.id = Sequence(n+1)`` стартует с 1 и конфликтует с
    residual rows / неотдвинутым sequence после гонок truncate. После
    ``TRUNCATE ... RESTART IDENTITY`` id назначает PostgreSQL.
    """
    wb_user_cabinet = WBUserCabinetFactory.build(user=user, wb_cabinet=wb_cabinet)
    # Drop factory Sequence id so INSERT omits PK → DB serial after RESTART IDENTITY.
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

    # Baseline wbcabinet id=1 уже сеется reset_postgres_test_data — не INSERT через factory
    wb_cabinet = await _baseline_wb_cabinet(async_session)

    wb_user_cabinet = _build_wb_user_cabinet(user=user, wb_cabinet=wb_cabinet)
    async_session.add(wb_user_cabinet)
    await async_session.flush()
    assert wb_user_cabinet.id is not None, "wbusercabinet id must be assigned on flush"
    assert await async_session.get(WBUserCabinet, wb_user_cabinet.id) is not None

    # Создаем AdvSetting с недефолтными значениями
    adv_setting = AdvSettingFactory.build(
        adv_id=1000,
        name="Test Campaign 1",
        wb_cabinet=wb_cabinet,
        wb_cabinet_id=wb_cabinet.id,
        bot_active=True,  # Активная кампания
        bidder_active=False, # Недефолтное значение
        automatic_version=1, # Недефолтное значение
        auto_update_white_list=False, # Недефолтное значение
    )
    async_session.add(adv_setting)
    await async_session.flush()

    adv_setting_inactive = AdvSettingFactory.build(
        adv_id=1001,
        name="Test Campaign Inactive",
        wb_cabinet=wb_cabinet,
        wb_cabinet_id=wb_cabinet.id,
        bot_active=False,  # Неактивная кампания
        bidder_active=False, # Недефолтное значение
        automatic_version=1, # Недефолтное значение
        auto_update_white_list=False, # Недефолтное значение
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
    """Seed multi-adv shop data with flush-only fixture writes (см. setup_adv_data)."""
    user = User(user_telegram_id=45678, username="test_user_multi")
    async_session.add(user)
    await async_session.flush()

    # Baseline wbcabinet id=1 — без повторного INSERT (см. setup_adv_data)
    wb_cabinet = await _baseline_wb_cabinet(async_session)

    wb_user_cabinet = _build_wb_user_cabinet(user=user, wb_cabinet=wb_cabinet)
    async_session.add(wb_user_cabinet)
    await async_session.flush()
    assert wb_user_cabinet.id is not None

    # Активные кампании с недефолтными значениями
    adv_active_1 = AdvSettingFactory.build(
        adv_id=2000,
        name="Multi Adv Active 1",
        wb_cabinet=wb_cabinet,
        wb_cabinet_id=wb_cabinet.id,
        bot_active=True,
        bidder_active=False,
        automatic_version=1,
    )
    adv_active_2 = AdvSettingFactory.build(
        adv_id=2001,
        name="Multi Adv Active 2",
        wb_cabinet=wb_cabinet,
        wb_cabinet_id=wb_cabinet.id,
        bot_active=True,
        bidder_active=False,
        automatic_version=1,
    )
    # Неактивная кампания
    adv_inactive_1 = AdvSettingFactory.build(
        adv_id=2002,
        name="Multi Adv Inactive 1",
        wb_cabinet=wb_cabinet,
        wb_cabinet_id=wb_cabinet.id,
        bot_active=False,
        bidder_active=True, # Недефолтное значение, но не должно быть изменено
        automatic_version=1,
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

    # Проверяем, что начальные значения отличаются от дефолтных
    initial_defaults = CampaignDefaultsV1()

    # Явно устанавливаем отличающиеся значения для тестовой кампании
    # Для булевых полей инвертируем значение
    adv_setting.bidder_active = not initial_defaults.bidder_active
    adv_setting.auto_update_white_list = not initial_defaults.auto_update_white_list
    adv_setting.auto_update_minus_phrases = (
        not initial_defaults.auto_update_minus_phrases
    )
    adv_setting.auto_update_target_place = not initial_defaults.auto_update_target_place
    adv_setting.target_ctr_mode = not initial_defaults.target_ctr_mode
    adv_setting.new_auto_min_ctr_mode = not initial_defaults.new_auto_min_ctr_mode
    adv_setting.reset_place = not initial_defaults.reset_place
    # Для полей типа Enum выбираем другое валидное значение, если оно есть
    if initial_defaults.automatic_version == 2:
        adv_setting.automatic_version = 1
    else:
        adv_setting.automatic_version = 2

    # bidder_coroutine_type
    if initial_defaults.bidder_coroutine_type == BidderCoroutineType.UPDATE_CLUSTER_BIDS:
        adv_setting.bidder_coroutine_type = BidderCoroutineType.OLD_UPDATE_CPM_BIDDER
    else:
        adv_setting.bidder_coroutine_type = BidderCoroutineType.UPDATE_CLUSTER_BIDS

    # orders_source_for_auto_mode
    if initial_defaults.orders_source_for_auto_mode == OrdersSourceForAutoMode.COMMON_STATISTIC:
        adv_setting.orders_source_for_auto_mode = OrdersSourceForAutoMode.ADV_SUM
    else:
        adv_setting.orders_source_for_auto_mode = OrdersSourceForAutoMode.COMMON_STATISTIC

    # sales_predict_method
    if initial_defaults.sales_predict_method == FactMethods.BY_CARTS:
        adv_setting.sales_predict_method = FactMethods.DIRECT_SALES
    else:
        adv_setting.sales_predict_method = FactMethods.BY_CARTS

    # flush into fixture transaction — avoid commit()+refresh() vs outer session.begin()
    await async_session.flush()

    # Вызываем хэндлер
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

    # Мокаем session maker чтобы хэндлер использовал тестовую сессию
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

    expected_defaults = CampaignDefaultsV1()

    # Поля, которые должны быть в дефолтах (из apply_defaults_to_adv_setting)
    default_fields = [
        "bidder_active", "bidder_for_auto", "bidder_mode", "automatic_version",
        "bidder_coroutine_type", "orders_source_for_auto_mode", "sales_predict_method",
        "auto_update_white_list", "auto_update_target_place", "target_ctr_mode",
        "auto_update_minus_phrases",
        "new_auto_min_ctr_mode", "reset_place"
    ]

    for key in default_fields:
        assert hasattr(updated_adv_setting, key), f"AdvSetting missing attribute {key}"
        assert getattr(updated_adv_setting, key) == getattr(expected_defaults, key), f"Mismatch for {key}"


@pytest.mark.integration
async def test_apply_campaign_defaults_single_inactive_campaign(
    mock_bot, async_session: AsyncSession, setup_adv_data
):
    adv_setting_inactive = setup_adv_data["adv_setting_inactive"]
    wb_user_cabinet = setup_adv_data["wb_user_cabinet"]

    # Сохраняем исходные значения AdvSetting, чтобы проверить те поля,
    # которые не затрагиваются дефолтными настройками
    initial_adv_setting_state = {key: getattr(adv_setting_inactive, key) for key in adv_setting_inactive.__table__.columns.keys()}

    # Вызываем хэндлер для неактивной кампании
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

    # flush-only: keep outer fixture transaction (см. active-campaign test)
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

    defaults_v1 = CampaignDefaultsV1()

    # Поля, которые должны быть в дефолтах (из apply_defaults_to_adv_setting)
    default_fields = [
        "bidder_active", "bidder_for_auto", "bidder_mode", "automatic_version",
        "bidder_coroutine_type", "orders_source_for_auto_mode", "sales_predict_method",
        "auto_update_white_list", "auto_update_target_place", "target_ctr_mode",
        "auto_update_minus_phrases",
        "new_auto_min_ctr_mode", "reset_place"
    ]

    for key in default_fields:
        assert getattr(updated_adv_setting, key) == getattr(defaults_v1, key), f"Mismatch for {key} (expected default)"


@pytest.mark.integration
async def test_turn_adv_on_applies_defaults(
    mock_bot, mock_state, async_session: AsyncSession, setup_adv_data
):
    adv_setting_inactive = setup_adv_data["adv_setting_inactive"]
    wb_user_cabinet = setup_adv_data["wb_user_cabinet"]

    # Проверяем, что изначально бот неактивен
    assert not adv_setting_inactive.bot_active

    # Сохраняем недефолтные значения
    initial_defaults = CampaignDefaultsV1()
    # Явно устанавливаем отличающиеся значения для тестовой кампании
    # Для булевых полей инвертируем значение
    adv_setting_inactive.bidder_active = not initial_defaults.bidder_active
    adv_setting_inactive.auto_update_white_list = not initial_defaults.auto_update_white_list
    adv_setting_inactive.auto_update_minus_phrases = (
        not initial_defaults.auto_update_minus_phrases
    )
    adv_setting_inactive.auto_update_target_place = not initial_defaults.auto_update_target_place
    adv_setting_inactive.target_ctr_mode = not initial_defaults.target_ctr_mode
    adv_setting_inactive.new_auto_min_ctr_mode = not initial_defaults.new_auto_min_ctr_mode
    adv_setting_inactive.reset_place = not initial_defaults.reset_place
    # Для полей типа Enum выбираем другое валидное значение, если оно есть
    if initial_defaults.automatic_version == 2:
        adv_setting_inactive.automatic_version = 1
    else:
        adv_setting_inactive.automatic_version = 2

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

    # Вызываем хэндлер turn_adv_on
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
        mock_get_balance.return_value = (1000, 0) # Достаточно средств

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
            await turn_adv_on(callback_query, mock_state, callback_data, mock_bot)

    # Проверяем только bot_active, дефолты НЕ должны применяться
    expected_bidder_active = adv_setting_inactive.bidder_active
    updated_adv_setting = await async_session.get(AdvSetting, adv_setting_inactive.id)
    assert updated_adv_setting is not None

    assert updated_adv_setting.bot_active
    # Остальные настройки (например, bidder_active) не должны сбрасываться к дефолтам
    assert updated_adv_setting.bidder_active == expected_bidder_active


@pytest.mark.integration
async def test_apply_defaults_for_shop_multiple_campaigns(
    mock_bot, mock_state, async_session: AsyncSession, setup_multiple_advs_data
):
    wb_user_cabinet = setup_multiple_advs_data["wb_user_cabinet"]
    adv_active_1 = setup_multiple_advs_data["adv_active_1"]
    adv_active_2 = setup_multiple_advs_data["adv_active_2"]
    adv_inactive_1 = setup_multiple_advs_data["adv_inactive_1"]

    # Проверяем, что начальные значения отличаются от дефолтных для активных кампаний
    initial_defaults = CampaignDefaultsV1()
    for adv in [adv_active_1, adv_active_2]:
        # Явно устанавливаем отличающиеся значения для тестовой кампании
        # Для булевых полей инвертируем значение
        adv.bidder_active = not initial_defaults.bidder_active
        adv.auto_update_white_list = not initial_defaults.auto_update_white_list
        adv.auto_update_minus_phrases = not initial_defaults.auto_update_minus_phrases
        adv.auto_update_target_place = not initial_defaults.auto_update_target_place
        adv.target_ctr_mode = not initial_defaults.target_ctr_mode
        adv.new_auto_min_ctr_mode = not initial_defaults.new_auto_min_ctr_mode
        adv.reset_place = not initial_defaults.reset_place

        # Для полей типа Enum выбираем другое валидное значение, если оно есть
        if initial_defaults.automatic_version == 2:
            adv.automatic_version = 1
        else:
            adv.automatic_version = 2

        # bidder_coroutine_type
        if initial_defaults.bidder_coroutine_type == BidderCoroutineType.UPDATE_CLUSTER_BIDS:
            adv.bidder_coroutine_type = BidderCoroutineType.OLD_UPDATE_CPM_BIDDER
        else:
            adv.bidder_coroutine_type = BidderCoroutineType.UPDATE_CLUSTER_BIDS

        # orders_source_for_auto_mode
        if initial_defaults.orders_source_for_auto_mode == OrdersSourceForAutoMode.COMMON_STATISTIC:
            adv.orders_source_for_auto_mode = OrdersSourceForAutoMode.ADV_SUM
        else:
            adv.orders_source_for_auto_mode = OrdersSourceForAutoMode.COMMON_STATISTIC

        # sales_predict_method
        if initial_defaults.sales_predict_method == FactMethods.BY_CARTS:
            adv.sales_predict_method = FactMethods.DIRECT_SALES
        else:
            adv.sales_predict_method = FactMethods.BY_CARTS

    await async_session.flush()

    # Вызываем хэндлер для магазина
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

    # Проверяем активные кампании
    updated_adv_active_1 = await async_session.get(AdvSetting, adv_active_1.id)
    assert updated_adv_active_1 is not None

    expected_defaults = CampaignDefaultsV1()
    default_fields = [
        "bidder_active", "bidder_for_auto", "bidder_mode", "automatic_version",
        "bidder_coroutine_type", "orders_source_for_auto_mode", "sales_predict_method",
        "auto_update_white_list", "auto_update_target_place", "target_ctr_mode",
        "new_auto_min_ctr_mode", "reset_place"
        "auto_update_minus_phrases",
    ]

    for key in default_fields:
        assert hasattr(updated_adv_active_1, key), f"AdvSetting missing attribute {key}"
        assert getattr(updated_adv_active_1, key) == getattr(expected_defaults, key), f"Mismatch for {key} in active_1"

    updated_adv_active_2 = await async_session.get(AdvSetting, adv_active_2.id)
    assert updated_adv_active_2 is not None
    for key in default_fields:
        assert hasattr(updated_adv_active_2, key), f"AdvSetting missing attribute {key}"
        assert getattr(updated_adv_active_2, key) == getattr(expected_defaults, key), f"Mismatch for {key} in active_2"
