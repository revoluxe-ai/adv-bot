"""Unit: Telegram-уведомления в ARQ adv_creator не роняют задачу при сбое прокси."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from aiogram.exceptions import TelegramNetworkError

from app.modules.adv_creator.backend import tasks


@pytest.mark.unit
@pytest.mark.asyncio
async def test_send_user_message_best_effort_swallows_telegram_error() -> None:
    bot = MagicMock()
    bot.send_message = AsyncMock(
        side_effect=TelegramNetworkError(
            method=MagicMock(), message="Request timeout error"
        )
    )
    await tasks._send_user_message_best_effort(
        bot,
        123,
        "progress",
        log_context="test",
    )
    bot.send_message.assert_awaited_once()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_create_complex_advs_runs_wb_create_when_progress_message_fails() -> None:
    """Прогресс в Telegram упал — create_complex_advs на MainAdvManager всё равно вызывается."""
    from typing import Any

    bot = MagicMock()
    call_count = 0

    async def _send_side_effect(*_args: Any, **_kwargs: Any) -> MagicMock:
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            raise TelegramNetworkError(
                method=MagicMock(), message="Request timeout error"
            )
        return MagicMock()

    bot.send_message = AsyncMock(side_effect=_send_side_effect)

    manager = MagicMock()
    manager.create_complex_advs = AsyncMock(return_value=(111, 222))

    ctx: dict[str, Any] = {"bot": bot, "client_session": MagicMock()}
    access = MagicMock()

    mock_http_session = MagicMock()
    mock_http_session.__aenter__ = AsyncMock(return_value=MagicMock())
    mock_http_session.__aexit__ = AsyncMock(return_value=None)

    with (
        patch.object(
            tasks.super_cabinet_manager,
            "get_access_for_wb_cabinet",
            AsyncMock(return_value=access),
        ),
        patch.object(tasks.data_manager, "ensure_card_in_db", AsyncMock(return_value=True)),
        patch.object(
            tasks.data_manager,
            "update_advs_data_from_wb_to_pg",
            AsyncMock(return_value=None),
        ),
        patch.object(tasks, "MainAdvManager", MagicMock(return_value=manager)),
        patch.object(tasks.aiohttp, "ClientSession", return_value=mock_http_session),
        patch(
            "app.modules.shop_runner.modules.wb_api.WBApi",
            return_value=MagicMock(),
        ),
    ):
        await tasks._create_complex_advs(
            ctx, 138252141, "shop-id", False, 373435337
        )

    manager.create_complex_advs.assert_awaited_once()
