"""Unit tests for turn_adv_on/off handler wiring and UX."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.client_bot.user_interface.handlers.adv_setting import turn_adv_off, turn_adv_on
from app.client_bot.user_interface.services.adv_auto_management_activation import (
    PaidActivationBlockReason,
    PaidActivationEligibility,
)

pytestmark = [pytest.mark.unit, pytest.mark.asyncio]

_HANDLER_MODULE = "app.client_bot.user_interface.handlers.adv_setting.adv_setting"


class _MockSessionMaker:
    """Async session maker wrapper for handler unit tests."""

    def __init__(self, session: MagicMock) -> None:
        self._session = session

    def __call__(self, read_only: bool = False) -> "_MockSessionMaker":
        return self

    async def __aenter__(self) -> MagicMock:
        return self._session

    async def __aexit__(self, *args: object) -> None:
        return None


def _build_callback(chat_id: int = 202) -> SimpleNamespace:
    return SimpleNamespace(message=SimpleNamespace(chat=SimpleNamespace(id=chat_id)))


def _build_callback_data(
    wb_user_cabinet_original_id: int = 77, adv_original_id: int = 55
) -> SimpleNamespace:
    return SimpleNamespace(
        wb_user_cabinet_original_id=wb_user_cabinet_original_id,
        adv_original_id=adv_original_id,
    )


def _build_session_objects() -> tuple[MagicMock, SimpleNamespace, SimpleNamespace]:
    wb_cabinet = SimpleNamespace(id=31, shop_id="shop_77")
    wb_user_cabinet = SimpleNamespace(id=77, wb_cabinet=wb_cabinet)
    adv = SimpleNamespace(id=55, bot_active=False, automatic_version=2)

    result_wb_user_cabinet = MagicMock()
    result_wb_user_cabinet.scalar_one.return_value = wb_user_cabinet
    result_adv = MagicMock()
    result_adv.scalar_one.return_value = adv

    session = MagicMock()
    session.begin = AsyncMock()
    session.commit = AsyncMock()
    session.execute = AsyncMock(
        side_effect=[
            result_wb_user_cabinet,
            result_adv,
            result_wb_user_cabinet,
        ]
    )
    return session, wb_user_cabinet, adv


@pytest.mark.parametrize(
    ("block_reason", "expected_fragment"),
    [
        (
            PaidActivationBlockReason.ZERO_BALANCE,
            "Пополните баланс",
        ),
        (
            PaidActivationBlockReason.INSUFFICIENT_FOR_DAY,
            "Недостаточно средств",
        ),
        (
            PaidActivationBlockReason.READ_ONLY_TOKEN,
            "только права чтения",
        ),
    ],
)
async def test_turn_adv_on_blocks_activation_and_shows_reason_message(
    block_reason: PaidActivationBlockReason,
    expected_fragment: str,
) -> None:
    callback = _build_callback()
    callback_data = _build_callback_data()
    bot = AsyncMock()
    state = AsyncMock()
    session, _, adv = _build_session_objects()

    shop_menu_call = AsyncMock()
    shop_menu_ctor = MagicMock(return_value=shop_menu_call)
    activate_mock = AsyncMock()

    with (
        patch(f"{_HANDLER_MODULE}.sm", _MockSessionMaker(session)),
        patch(
            f"{_HANDLER_MODULE}.check_paid_activation_eligibility",
            new=AsyncMock(
                return_value=PaidActivationEligibility(
                    allowed=False,
                    block_reason=block_reason,
                )
            ),
        ),
        patch(f"{_HANDLER_MODULE}.activate_adv_paid_mode", activate_mock),
        patch(f"{_HANDLER_MODULE}.ShopMenu", shop_menu_ctor),
    ):
        await turn_adv_on(callback, state, callback_data, bot)

    assert adv.bot_active is False
    activate_mock.assert_not_awaited()
    bot.send_message.assert_awaited_once()
    assert expected_fragment in bot.send_message.await_args.args[1]
    shop_menu_ctor.assert_called_once_with(bot, 202, state, 77)
    shop_menu_call.assert_awaited_once()


async def test_turn_adv_on_allowed_path_calls_activate_and_adv_menu() -> None:
    callback = _build_callback()
    callback_data = _build_callback_data()
    bot = AsyncMock()
    state = AsyncMock()
    session, wb_user_cabinet, adv = _build_session_objects()

    activate_mock = AsyncMock()
    adv_menu_call = AsyncMock()
    adv_menu_ctor = MagicMock(return_value=adv_menu_call)

    with (
        patch(f"{_HANDLER_MODULE}.sm", _MockSessionMaker(session)),
        patch(
            f"{_HANDLER_MODULE}.check_paid_activation_eligibility",
            new=AsyncMock(
                return_value=PaidActivationEligibility(allowed=True),
            ),
        ),
        patch(f"{_HANDLER_MODULE}.activate_adv_paid_mode", activate_mock),
        patch(f"{_HANDLER_MODULE}.AdvSettingMenu", adv_menu_ctor),
    ):
        await turn_adv_on(callback, state, callback_data, bot)

    activate_mock.assert_awaited_once_with(session, adv, wb_user_cabinet.wb_cabinet)
    bot.send_message.assert_awaited_once_with(202, "Включаю бота")
    state.update_data.assert_any_await(wb_user_cabinet_original_id=77)
    state.update_data.assert_any_await(adv_original_id=55)
    adv_menu_ctor.assert_called_once_with(bot, 202, wb_user_cabinet, adv)
    adv_menu_call.assert_awaited_once()


async def test_turn_adv_off_calls_deactivate_service_and_adv_menu() -> None:
    callback = _build_callback()
    callback_data = _build_callback_data()
    bot = AsyncMock()
    session, wb_user_cabinet, adv = _build_session_objects()
    adv.bot_active = True

    wb_user_cabinet_result = MagicMock()
    wb_user_cabinet_result.scalar_one.return_value = wb_user_cabinet
    adv_result = MagicMock()
    adv_result.scalar_one.return_value = adv
    session.execute = AsyncMock(side_effect=[wb_user_cabinet_result, adv_result])

    deactivate_mock = AsyncMock()
    adv_menu_call = AsyncMock()
    adv_menu_ctor = MagicMock(return_value=adv_menu_call)

    with (
        patch(f"{_HANDLER_MODULE}.sm", _MockSessionMaker(session)),
        patch(f"{_HANDLER_MODULE}.deactivate_adv_free_mode", deactivate_mock),
        patch(f"{_HANDLER_MODULE}.AdvSettingMenu", adv_menu_ctor),
    ):
        await turn_adv_off(callback, callback_data, bot)

    deactivate_mock.assert_awaited_once_with(
        session, adv, wb_user_cabinet.wb_cabinet
    )
    adv_menu_ctor.assert_called_once_with(bot, 202, wb_user_cabinet, adv)
    adv_menu_call.assert_awaited_once()
