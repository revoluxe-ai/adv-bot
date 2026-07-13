"""Integration tests for paid/free auto-management activation service and handler wiring."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from aiogram.types import CallbackQuery, Chat, Message, User as TelegramUser
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.client_bot.user_interface.handlers.adv_setting import turn_adv_off, turn_adv_on
from app.client_bot.user_interface.services.adv_auto_management_activation import (
    activate_adv_paid_mode,
    deactivate_adv_free_mode,
)
from app.client_bot.user_interface.views.callbacks import TurnBot
from app.modules.common_slaves.wildberries.models import AdvSetting
from app.modules.common_slaves.wildberries.models.enums import OrdersSourceForAutoMode
from app.modules.common_slaves.wildberries.models.fact_methods_enum import FactMethods
from app.modules.common_slaves.wildberries.models.models import BidderCoroutineType
from app.modules.common_slaves.wildberries.models.white_list_mode import WhiteListMode
from app.utils.db.models import User
from tests.factories.adv_factory import AdvSettingFactory, WBCabinetFactory, WBUserCabinetFactory

pytestmark = [pytest.mark.integration, pytest.mark.asyncio]

_SERVICE_MODULE = (
    "app.client_bot.user_interface.services.adv_auto_management_activation"
)
_HANDLER_MODULE = "app.client_bot.user_interface.handlers.adv_setting.adv_setting"


class MockSessionMaker:
    """Подмена session maker для handler integration smoke."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    def __call__(self, read_only: bool = False) -> "MockSessionMaker":
        return self

    async def __aenter__(self) -> AsyncSession:
        return self.session

    async def __aexit__(self, *args: object) -> None:
        return None


@pytest.fixture
def mock_bot() -> AsyncMock:
    return AsyncMock()


@pytest.fixture
def mock_state() -> AsyncMock:
    state = AsyncMock()
    state.update_data = AsyncMock()
    return state


@pytest.fixture
async def activation_setup(async_session: AsyncSession):
    """Минимальный набор сущностей для activate/deactivate integration."""
    user = User(user_telegram_id=54321, username="activation_user")
    async_session.add(user)
    await async_session.commit()
    await async_session.refresh(user)

    wb_cabinet = WBCabinetFactory.build()
    async_session.add(wb_cabinet)
    await async_session.flush()

    wb_user_cabinet = WBUserCabinetFactory.build(user=user, wb_cabinet=wb_cabinet)
    async_session.add(wb_user_cabinet)
    await async_session.flush()

    adv_setting = AdvSettingFactory.build(
        adv_id=3001,
        name="Activation Campaign",
        wb_cabinet=wb_cabinet,
        bot_active=False,
        automatic_version=2,
        white_list_mode=WhiteListMode.ABOVE_MIN_RATING,
        bidder_coroutine_type=BidderCoroutineType.OLD_UPDATE_CPM_BIDDER,
        orders_source_for_auto_mode=OrdersSourceForAutoMode.ADV_SUM,
        sales_predict_method=FactMethods.DIRECT_SALES,
    )
    async_session.add(adv_setting)
    await async_session.flush()

    return {
        "wb_cabinet": wb_cabinet,
        "wb_user_cabinet": wb_user_cabinet,
        "adv_setting": adv_setting,
    }


@pytest.mark.integration
async def test_activate_adv_paid_mode_persists_bot_active_and_paid_fields(
    async_session: AsyncSession,
    activation_setup,
) -> None:
    adv_setting = activation_setup["adv_setting"]
    wb_cabinet = activation_setup["wb_cabinet"]
    adv_id = adv_setting.id

    with patch(
        f"{_SERVICE_MODULE}.backfill_v3_hard_statuses_and_states_consistency",
        new=AsyncMock(),
    ):
        await activate_adv_paid_mode(async_session, adv_setting, wb_cabinet)

    updated = (
        await async_session.execute(select(AdvSetting).where(AdvSetting.id == adv_id))
    ).scalar_one()

    assert updated.bot_active is True
    assert updated.automatic_version == 3
    assert updated.white_list_mode == WhiteListMode.REPLACE_ON_TRIM


@pytest.mark.integration
async def test_activate_does_not_reset_common_default_fields(
    async_session: AsyncSession,
    activation_setup,
) -> None:
    adv_setting = activation_setup["adv_setting"]
    wb_cabinet = activation_setup["wb_cabinet"]
    adv_id = adv_setting.id

    with patch(
        f"{_SERVICE_MODULE}.backfill_v3_hard_statuses_and_states_consistency",
        new=AsyncMock(),
    ):
        await activate_adv_paid_mode(async_session, adv_setting, wb_cabinet)

    updated = (
        await async_session.execute(select(AdvSetting).where(AdvSetting.id == adv_id))
    ).scalar_one()

    assert updated.bidder_coroutine_type == BidderCoroutineType.OLD_UPDATE_CPM_BIDDER
    assert updated.orders_source_for_auto_mode == OrdersSourceForAutoMode.ADV_SUM
    assert updated.sales_predict_method == FactMethods.DIRECT_SALES


@pytest.mark.integration
async def test_deactivate_adv_free_mode_persists_free_fields(
    async_session: AsyncSession,
    activation_setup,
) -> None:
    adv_setting = activation_setup["adv_setting"]
    wb_cabinet = activation_setup["wb_cabinet"]
    adv_id = adv_setting.id

    adv_setting.bot_active = True
    adv_setting.automatic_version = 3
    adv_setting.white_list_mode = WhiteListMode.REPLACE_ON_TRIM
    adv_setting.auto_update_white_list = True
    adv_setting.auto_update_target_place = True
    adv_setting.bidder_for_auto = True
    adv_setting.bidder_active = True
    adv_setting.max_place = 7
    adv_setting.max_cpm = 4567
    await async_session.commit()

    await deactivate_adv_free_mode(async_session, adv_setting, wb_cabinet)

    updated = (
        await async_session.execute(select(AdvSetting).where(AdvSetting.id == adv_id))
    ).scalar_one()

    assert updated.bot_active is False
    assert updated.automatic_version == 2
    assert updated.white_list_mode == WhiteListMode.ABOVE_MIN_RATING
    assert updated.auto_update_white_list is False
    assert updated.auto_update_target_place is False
    assert updated.bidder_for_auto is False
    assert updated.bidder_active is False
    assert updated.max_place == 7
    assert updated.max_cpm == 4567


@pytest.mark.integration
async def test_activate_adv_paid_mode_commits_before_backfill(
    activation_setup,
) -> None:
    adv_setting = activation_setup["adv_setting"]
    wb_cabinet = activation_setup["wb_cabinet"]

    session = AsyncMock()
    call_order: list[str] = []

    async def _commit() -> None:
        call_order.append("commit")

    async def _backfill(**_kwargs: object) -> None:
        call_order.append("backfill")

    session.commit = AsyncMock(side_effect=_commit)

    with patch(
        f"{_SERVICE_MODULE}.backfill_v3_hard_statuses_and_states_consistency",
        new=AsyncMock(side_effect=_backfill),
    ):
        await activate_adv_paid_mode(session, adv_setting, wb_cabinet)

    assert call_order == ["commit", "backfill"]


@pytest.mark.integration
async def test_turn_adv_on_handler_wires_service_and_persists(
    mock_bot,
    mock_state,
    async_session: AsyncSession,
    activation_setup,
) -> None:
    adv_setting = activation_setup["adv_setting"]
    wb_user_cabinet = activation_setup["wb_user_cabinet"]
    adv_id = adv_setting.id

    callback_data = TurnBot(
        action="on",
        adv_original_id=adv_setting.id,
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
        id="integration-on",
        from_user=telegram_user,
        chat_instance="integration_on",
        data=callback_data.pack(),
        message=message,
    )

    with (
        patch.object(async_session, "begin", new=AsyncMock()),
        patch(
            f"{_SERVICE_MODULE}.pricer.get_price_for_day_for_shop",
            new=AsyncMock(return_value=100),
        ),
        patch(
            f"{_SERVICE_MODULE}.pricer.get_tariff_for_day",
            return_value=100,
        ),
        patch(
            f"{_SERVICE_MODULE}.balance_manager.get_cabinet_balance_and_bonuses",
            new=AsyncMock(return_value=(1000, 0)),
        ),
        patch(
            f"{_SERVICE_MODULE}._shop_has_read_only_only_tokens",
            new=AsyncMock(return_value=False),
        ),
        patch(
            f"{_SERVICE_MODULE}.backfill_v3_hard_statuses_and_states_consistency",
            new=AsyncMock(),
        ) as backfill_mock,
        patch(f"{_HANDLER_MODULE}.sm", MockSessionMaker(async_session)),
        patch(
            f"{_HANDLER_MODULE}.AdvSettingMenu",
            return_value=AsyncMock(),
        ),
    ):
        await turn_adv_on(callback_query, mock_state, callback_data, mock_bot)

    updated = (
        await async_session.execute(select(AdvSetting).where(AdvSetting.id == adv_id))
    ).scalar_one()

    assert updated.bot_active is True
    backfill_mock.assert_awaited_once_with(dry_run=False, adv_setting_id=adv_id)


@pytest.mark.integration
async def test_turn_adv_off_handler_wires_service_and_persists(
    mock_bot,
    async_session: AsyncSession,
    activation_setup,
) -> None:
    adv_setting = activation_setup["adv_setting"]
    wb_user_cabinet = activation_setup["wb_user_cabinet"]
    adv_id = adv_setting.id

    adv_setting.bot_active = True
    adv_setting.automatic_version = 3
    adv_setting.white_list_mode = WhiteListMode.REPLACE_ON_TRIM
    await async_session.commit()

    callback_data = TurnBot(
        action="off",
        adv_original_id=adv_setting.id,
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
        id="integration-off",
        from_user=telegram_user,
        chat_instance="integration_off",
        data=callback_data.pack(),
        message=message,
    )

    with (
        patch(f"{_HANDLER_MODULE}.sm", MockSessionMaker(async_session)),
        patch(
            f"{_HANDLER_MODULE}.AdvSettingMenu",
            return_value=AsyncMock(),
        ),
    ):
        await turn_adv_off(callback_query, callback_data, mock_bot)

    updated = (
        await async_session.execute(select(AdvSetting).where(AdvSetting.id == adv_id))
    ).scalar_one()

    assert updated.bot_active is False
    assert updated.automatic_version == 2
    assert updated.white_list_mode == WhiteListMode.ABOVE_MIN_RATING
