"""Unit tests for guarding bot activation with read-only WB tokens."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.client_bot.user_interface.handlers.adv_setting import turn_adv_on
from app.modules.token_monitoring.services.token_info_service import (
    TokenInfo,
    TokenStatusReport,
)

pytestmark = [pytest.mark.unit, pytest.mark.asyncio]


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
    """Build a callback object with chat context."""
    return SimpleNamespace(message=SimpleNamespace(chat=SimpleNamespace(id=chat_id)))


def _build_callback_data(
    wb_user_cabinet_original_id: int = 77, adv_original_id: int = 55
) -> SimpleNamespace:
    """Build callback data for turn bot on action."""
    return SimpleNamespace(
        wb_user_cabinet_original_id=wb_user_cabinet_original_id,
        adv_original_id=adv_original_id,
    )


def _build_token_status(*, is_read_only_only: bool) -> TokenStatusReport:
    """Create token status for read-only and paid activation scenarios."""
    token = TokenInfo(
        id=1,
        api_key="key",
        user_id=1,
        shop_id="shop_77",
        expires=datetime.now(UTC) + timedelta(days=30),
        categories={
            "РљРѕРЅС‚РµРЅС‚",
            "РЎС‚Р°С‚РёСЃС‚РёРєР°",
            "РђРЅР°Р»РёС‚РёРєР°",
            "РџСЂРѕРґРІРёР¶РµРЅРёРµ",
        },
        is_read_only=is_read_only_only,
        is_valid=True,
        is_expired=False,
        is_personal=True,
    )
    valid_tokens = [] if is_read_only_only else [token]
    return TokenStatusReport(
        shop_id="shop_77",
        shop_name="Shop 77",
        status="Insufficient" if is_read_only_only else "Complete",
        all_tokens=[token],
        valid_tokens=valid_tokens,
        expired_tokens=[],
        available_permissions=set() if is_read_only_only else token.categories,
        missing_permissions={"РџСЂРѕРґРІРёР¶РµРЅРёРµ"} if is_read_only_only else set(),
        has_all_required_permissions=not is_read_only_only,
        expiring_tokens=[],
    )


def _build_session_objects() -> tuple[MagicMock, SimpleNamespace, SimpleNamespace]:
    """Create session and ORM-like objects consumed by the handler."""
    wb_cabinet = SimpleNamespace(id=31, shop_id="shop_77")
    wb_user_cabinet = SimpleNamespace(id=77, wb_cabinet=wb_cabinet)
    adv = SimpleNamespace(id=55, bot_active=False)

    result_wb_user_cabinet = MagicMock()
    result_wb_user_cabinet.scalar_one.return_value = wb_user_cabinet
    result_adv = MagicMock()
    result_adv.scalar_one.return_value = adv

    session = MagicMock()
    session.begin = MagicMock()
    session.commit = AsyncMock()
    session.execute = AsyncMock(
        side_effect=[
            result_wb_user_cabinet,
            result_adv,
            result_wb_user_cabinet,
        ]
    )
    return session, wb_user_cabinet, adv


async def test_turn_adv_on_blocks_read_only_token_activation() -> None:
    """Read-only token blocks bot activation before bot_active commit."""
    callback = _build_callback()
    callback_data = _build_callback_data()
    bot = AsyncMock()
    state = AsyncMock()
    session, _, adv = _build_session_objects()

    shop_menu_call = AsyncMock()
    shop_menu_ctor = MagicMock(return_value=shop_menu_call)
    token_service = AsyncMock()
    token_service.get_shop_token_status = AsyncMock(
        return_value=_build_token_status(is_read_only_only=True)
    )

    with (
        patch("app.client_bot.user_interface.handlers.adv_setting.sm", _MockSessionMaker(session)),
        patch(
            "app.client_bot.user_interface.handlers.adv_setting.TokenInfoService",
            MagicMock(return_value=token_service),
        ),
        patch(
            "app.client_bot.user_interface.handlers.adv_setting.balance_manager.get_cabinet_balance_and_bonuses",
            AsyncMock(return_value=(1000, 0)),
        ),
        patch(
            "app.client_bot.user_interface.handlers.adv_setting.pricer.get_price_for_day_for_shop",
            AsyncMock(return_value=100),
        ),
        patch(
            "app.client_bot.user_interface.handlers.adv_setting.pricer.get_tariff_for_day",
            MagicMock(return_value=100),
        ),
        patch("app.client_bot.user_interface.handlers.adv_setting.ShopMenu", shop_menu_ctor),
    ):
        await turn_adv_on(callback, state, callback_data, bot)

    assert adv.bot_active is False
    session.commit.assert_not_awaited()
    token_service.get_shop_token_status.assert_awaited_once_with("shop_77")
    bot.send_message.assert_awaited_once()
    assert "только права чтения" in bot.send_message.await_args.args[1]
    shop_menu_ctor.assert_called_once_with(bot, 202, state, 77)
    shop_menu_call.assert_awaited_once()


async def test_turn_adv_on_keeps_paid_enable_path_for_normal_token() -> None:
    """Normal token keeps the previous activation path unchanged."""
    callback = _build_callback()
    callback_data = _build_callback_data()
    bot = AsyncMock()
    state = AsyncMock()
    session, wb_user_cabinet, adv = _build_session_objects()

    token_service = AsyncMock()
    token_service.get_shop_token_status = AsyncMock(
        return_value=_build_token_status(is_read_only_only=False)
    )
    adv_menu_call = AsyncMock()
    adv_menu_ctor = MagicMock(return_value=adv_menu_call)

    with (
        patch("app.client_bot.user_interface.handlers.adv_setting.sm", _MockSessionMaker(session)),
        patch(
            "app.client_bot.user_interface.handlers.adv_setting.TokenInfoService",
            MagicMock(return_value=token_service),
        ),
        patch(
            "app.client_bot.user_interface.handlers.adv_setting.balance_manager.get_cabinet_balance_and_bonuses",
            AsyncMock(return_value=(1000, 0)),
        ),
        patch(
            "app.client_bot.user_interface.handlers.adv_setting.pricer.get_price_for_day_for_shop",
            AsyncMock(return_value=100),
        ),
        patch(
            "app.client_bot.user_interface.handlers.adv_setting.pricer.get_tariff_for_day",
            MagicMock(return_value=100),
        ),
        patch(
            "app.client_bot.user_interface.handlers.adv_setting.AdvSettingMenu",
            adv_menu_ctor,
        ),
    ):
        await turn_adv_on(callback, state, callback_data, bot)

    assert adv.bot_active is True
    session.commit.assert_awaited_once()
    bot.send_message.assert_awaited_once()
    state.update_data.assert_any_await(wb_user_cabinet_original_id=77)
    state.update_data.assert_any_await(adv_original_id=55)
    adv_menu_ctor.assert_called_once_with(bot, 202, wb_user_cabinet, adv)
    adv_menu_call.assert_awaited_once()
