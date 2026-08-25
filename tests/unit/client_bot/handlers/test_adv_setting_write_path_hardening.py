"""Unit tests for adv_setting write-path owner checks and backfill compensation."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.client_bot.user_interface.handlers.adv_setting import (
    adv_handler,
    turn_adv_off,
    turn_adv_on,
)
from app.client_bot.user_interface.handlers.adv_setting.adv_setting import (
    ADV_ACCESS_DENIED_MESSAGE,
    CABINET_ACCESS_DENIED_MESSAGE,
    V3_BACKFILL_FAILURE_MESSAGE,
)
from app.modules.common_slaves.wildberries.models.white_list_mode import WhiteListMode
from app.modules.token_monitoring.services.token_info_service import (
    TokenInfo,
    TokenStatusReport,
)

pytestmark = [pytest.mark.unit, pytest.mark.asyncio]


class _MockSessionMaker:
    """Async session maker wrapper for handler unit tests."""

    def __init__(self, *sessions: MagicMock) -> None:
        self._sessions = list(sessions)

    def __call__(self, read_only: bool = False) -> "_MockSessionMaker":
        return self

    async def __aenter__(self) -> MagicMock:
        if not self._sessions:
            raise RuntimeError("no sessions left")
        return self._sessions.pop(0)

    async def __aexit__(self, *args: object) -> None:
        return None


def _build_callback(chat_id: int = 303, user_id: int = 9001) -> SimpleNamespace:
    """Build callback with chat and owner telegram id."""
    return SimpleNamespace(
        message=SimpleNamespace(chat=SimpleNamespace(id=chat_id)),
        from_user=SimpleNamespace(id=user_id),
    )


def _build_turn_callback_data(
    wb_user_cabinet_original_id: int = 77, adv_original_id: int = 55
) -> SimpleNamespace:
    """Build callback data for turn bot handlers."""
    return SimpleNamespace(
        wb_user_cabinet_original_id=wb_user_cabinet_original_id,
        adv_original_id=adv_original_id,
    )


def _build_adv_callback_data(adv_original_id: int = 55) -> SimpleNamespace:
    """Build callback data for adv menu open."""
    return SimpleNamespace(adv_original_id=adv_original_id)


def _build_token_status() -> TokenStatusReport:
    """Create a valid non-read-only token status."""
    token = TokenInfo(
        id=1,
        api_key="key",
        user_id=1,
        shop_id="shop_77",
        expires=datetime.now(UTC) + timedelta(days=30),
        categories={"Контент", "Статистика", "Аналитика", "Продвижение"},
        is_read_only=False,
        is_valid=True,
        is_expired=False,
        is_personal=True,
    )
    return TokenStatusReport(
        shop_id="shop_77",
        shop_name="Shop 77",
        status="Complete",
        all_tokens=[token],
        valid_tokens=[token],
        expired_tokens=[],
        available_permissions=token.categories,
        missing_permissions=set(),
        has_all_required_permissions=True,
        expiring_tokens=[],
    )


def _build_activation_session_objects() -> tuple[MagicMock, SimpleNamespace, SimpleNamespace]:
    """Create session and ORM-like objects for paid activation."""
    wb_cabinet = SimpleNamespace(id=31, shop_id="shop_77")
    wb_user_cabinet = SimpleNamespace(id=77, wb_cabinet_id=31, wb_cabinet=wb_cabinet)
    adv = SimpleNamespace(
        id=55,
        wb_cabinet_id=31,
        bot_active=False,
        automatic_version=2,
        white_list_mode=WhiteListMode.ABOVE_MIN_RATING,
        auto_update_white_list=False,
        auto_update_target_place=False,
        bidder_for_auto=False,
        bidder_active=False,
        auto_update_minus_phrases=False,
        payments=[],
    )

    owner_result = MagicMock()
    owner_result.scalar_one_or_none.return_value = wb_user_cabinet
    owner_result.unique.return_value = owner_result
    adv_result = MagicMock()
    adv_result.scalar_one_or_none.return_value = adv
    reload_result = MagicMock()
    reload_result.scalar_one_or_none.return_value = wb_user_cabinet

    session = MagicMock()
    session.commit = AsyncMock()
    session.execute = AsyncMock(
        side_effect=[owner_result, adv_result, reload_result]
    )
    return session, wb_user_cabinet, adv


async def test_turn_adv_on_compensates_when_v3_backfill_fails() -> None:
    """Backfill failure must revert paid activation and show user-facing error."""
    callback = _build_callback()
    callback_data = _build_turn_callback_data()
    bot = AsyncMock()
    state = AsyncMock()
    session, wb_user_cabinet, adv = _build_activation_session_objects()
    compensate_session = MagicMock()
    compensate_session.commit = AsyncMock()
    compensate_adv_result = MagicMock()
    compensate_adv_result.scalar_one_or_none.return_value = adv
    compensate_session.execute = AsyncMock(return_value=compensate_adv_result)
    shop_menu_call = AsyncMock()
    shop_menu_ctor = MagicMock(return_value=shop_menu_call)
    token_service = AsyncMock()
    token_service.get_shop_token_status = AsyncMock(
        return_value=_build_token_status()
    )

    with (
        patch(
            "app.client_bot.user_interface.handlers.adv_setting.adv_setting.sm",
            _MockSessionMaker(session, compensate_session),
        ),
        patch(
            "app.client_bot.user_interface.handlers.adv_setting.adv_setting.TokenInfoService",
            MagicMock(return_value=token_service),
        ),
        patch(
            "app.client_bot.user_interface.handlers.adv_setting.adv_setting.balance_manager.get_cabinet_balance_and_bonuses",
            AsyncMock(return_value=(1000, 0)),
        ),
        patch(
            "app.client_bot.user_interface.handlers.adv_setting.adv_setting.pricer.get_price_for_day_for_shop",
            AsyncMock(return_value=100),
        ),
        patch(
            "app.client_bot.user_interface.handlers.adv_setting.adv_setting.backfill_v3_hard_statuses_and_states_consistency",
            AsyncMock(side_effect=RuntimeError("backfill failed")),
        ),
        patch(
            "app.client_bot.user_interface.handlers.adv_setting.adv_setting.apply_free_mode_transition",
        ) as revert_mock,
        patch("app.client_bot.user_interface.handlers.adv_setting.adv_setting.ShopMenu", shop_menu_ctor),
    ):
        await turn_adv_on(callback, state, callback_data, bot)

    session.commit.assert_awaited_once()
    revert_mock.assert_called_once_with(adv, wb_user_cabinet.wb_cabinet)
    compensate_session.commit.assert_awaited_once()
    assert any(
        V3_BACKFILL_FAILURE_MESSAGE in str(call.args[1])
        for call in bot.send_message.await_args_list
    )
    shop_menu_ctor.assert_called_once_with(bot, 303, state, 77)
    shop_menu_call.assert_awaited_once()


async def test_turn_adv_on_rejects_foreign_cabinet() -> None:
    """Write path must reject cabinet ids not owned by callback user."""
    callback = _build_callback()
    callback_data = _build_turn_callback_data()
    bot = AsyncMock()
    state = AsyncMock()
    owner_result = MagicMock()
    owner_result.scalar_one_or_none.return_value = None
    owner_result.unique.return_value = owner_result
    session = MagicMock()
    session.commit = AsyncMock()
    session.execute = AsyncMock(return_value=owner_result)
    shop_menu_call = AsyncMock()
    shop_menu_ctor = MagicMock(return_value=shop_menu_call)

    with (
        patch(
            "app.client_bot.user_interface.handlers.adv_setting.adv_setting.sm",
            _MockSessionMaker(session),
        ),
        patch("app.client_bot.user_interface.handlers.adv_setting.adv_setting.ShopMenu", shop_menu_ctor),
    ):
        await turn_adv_on(callback, state, callback_data, bot)

    session.commit.assert_not_awaited()
    bot.send_message.assert_awaited_once_with(303, CABINET_ACCESS_DENIED_MESSAGE)
    shop_menu_ctor.assert_called_once()


async def test_turn_adv_off_rejects_foreign_adv() -> None:
    """Turn-off must not mutate campaigns outside owner cabinet."""
    callback = _build_callback()
    callback_data = _build_turn_callback_data()
    bot = AsyncMock()
    wb_cabinet = SimpleNamespace(id=31, shop_id="shop_77")
    wb_user_cabinet = SimpleNamespace(id=77, wb_cabinet_id=31, wb_cabinet=wb_cabinet)
    owner_result = MagicMock()
    owner_result.scalar_one_or_none.return_value = wb_user_cabinet
    owner_result.unique.return_value = owner_result
    adv_result = MagicMock()
    adv_result.scalar_one_or_none.return_value = None
    session = MagicMock()
    session.commit = AsyncMock()
    session.execute = AsyncMock(side_effect=[owner_result, adv_result])

    with patch(
        "app.client_bot.user_interface.handlers.adv_setting.adv_setting.sm",
        _MockSessionMaker(session),
    ):
        await turn_adv_off(callback, callback_data, bot)

    session.commit.assert_not_awaited()
    bot.send_message.assert_awaited_once_with(303, ADV_ACCESS_DENIED_MESSAGE)


async def test_adv_handler_uses_owner_validated_cabinet_not_stale_fsm() -> None:
    """Adv open must resolve cabinet via owner+adv join, ignoring stale FSM."""
    callback = _build_callback()
    callback_data = _build_adv_callback_data()
    bot = AsyncMock()
    state = AsyncMock()
    wb_cabinet = SimpleNamespace(shop_id="shop_77")
    wb_user_cabinet = SimpleNamespace(id=99, wb_cabinet_id=31, wb_cabinet=wb_cabinet)
    adv = SimpleNamespace(
        id=55,
        wb_cabinet_id=31,
        nmids=[12345],
    )
    owner_result = MagicMock()
    owner_result.scalar_one_or_none.return_value = wb_user_cabinet
    owner_result.unique.return_value = owner_result
    adv_result = MagicMock()
    adv_result.scalar_one_or_none.return_value = adv
    session = MagicMock()
    session.execute = AsyncMock(side_effect=[owner_result, adv_result])
    adv_menu_call = AsyncMock()
    adv_menu_ctor = MagicMock(return_value=adv_menu_call)

    with (
        patch(
            "app.client_bot.user_interface.handlers.adv_setting.adv_setting.sm",
            _MockSessionMaker(session),
        ),
        patch(
            "app.client_bot.user_interface.handlers.adv_setting.adv_setting.messages.LongTimeOperation",
            MagicMock(return_value=AsyncMock()),
        ),
        patch(
            "app.client_bot.user_interface.handlers.adv_setting.adv_setting.wb_data_manager.ensure_card_with_image_for_ui",
            AsyncMock(return_value=SimpleNamespace(ok=True)),
        ),
        patch(
            "app.client_bot.user_interface.handlers.adv_setting.adv_setting.AdvSettingMenu",
            adv_menu_ctor,
        ),
    ):
        await adv_handler(callback, callback_data, bot, state)

    state.get_data.assert_not_awaited()
    adv_menu_ctor.assert_called_once_with(bot, 303, wb_user_cabinet, adv)
    adv_menu_call.assert_awaited_once()
