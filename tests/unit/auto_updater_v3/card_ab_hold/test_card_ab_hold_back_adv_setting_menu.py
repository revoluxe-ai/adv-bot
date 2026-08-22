"""Regression: CardAbHoldBack должен открыть AdvSettingMenu, не dead-end.

BUGCASE-ABHOLDBACK-20260727T210306Z / ROOT-001:
«← Назад» на экране A/B Hold MUST отправить меню настроек РК
(``AdvSettingMenu``) для той же кампании. Запрещён ``edit_text`` с копией
«Экран A/B Hold закрыт…» и зачистка/удаление старых A/B-сообщений.
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.modules.shop_runner.service_manager.services.auto_updater_v3.card_ab_hold.telegram import (
    handlers,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.card_ab_hold.telegram.callbacks import (
    CardAbHoldBack,
)

_CLOSED_COPY = "Экран A/B Hold закрыт. Откройте меню рекламной кампании снова."


class _FakeMessage:
    """Минимальный message-двойник для callback Back."""

    def __init__(self) -> None:
        self.text = "A/B Hold screen"
        self.caption = None
        self.bot = MagicMock(name="bot")
        self.chat = SimpleNamespace(id=1001)
        self.answer = AsyncMock()
        self.edit_text = AsyncMock()
        self.edit_caption = AsyncMock()
        self.delete = AsyncMock()


def _make_adv() -> SimpleNamespace:
    """Кампания с PG id, на которую указывает CardAbHoldBack."""
    return SimpleNamespace(
        id=42,
        adv_id=4242,
        wb_cabinet_id=7,
    )


def _make_session(adv: SimpleNamespace) -> MagicMock:
    """Async context manager ``sm()`` с ``session.execute`` → adv."""
    session = MagicMock()
    adv_result = MagicMock()
    adv_result.scalar_one_or_none.return_value = adv
    session.execute = AsyncMock(return_value=adv_result)
    session_cm = MagicMock()
    session_cm.__aenter__ = AsyncMock(return_value=session)
    session_cm.__aexit__ = AsyncMock(return_value=None)
    return session_cm


def _make_query(message: _FakeMessage) -> MagicMock:
    """Callback query с from_user и message."""
    query = MagicMock()
    query.message = message
    query.answer = AsyncMock()
    query.from_user = SimpleNamespace(id=9001)
    query.bot = message.bot
    return query


def _edit_text_payloads(msg: _FakeMessage) -> list[str]:
    """Собрать текстовые аргументы всех ``edit_text`` вызовов."""
    texts: list[str] = []
    for call in msg.edit_text.await_args_list:
        if call.args:
            texts.append(str(call.args[0]))
        elif "text" in call.kwargs:
            texts.append(str(call.kwargs["text"]))
    return texts


@pytest.mark.unit
@pytest.mark.asyncio
async def test_card_ab_hold_back_reloads_adv_setting_menu_not_closed_dead_end() -> None:
    """Back MUST вызвать AdvSettingMenu; MUST NOT dead-end closed edit / delete.

    Инвариант ROOT-001: навигация ``CardAbHoldBack`` возвращает в меню РК
    той же кампании. Тест падает на текущем ``edit_text(closed)`` и зеленеет
    только когда handler реально вызывает ``AdvSettingMenu``.
    """
    adv = _make_adv()
    wb_uc = SimpleNamespace(id=77, wb_cabinet_id=adv.wb_cabinet_id)
    msg = _FakeMessage()
    query = _make_query(msg)
    session_cm = _make_session(adv)
    menu_instance = AsyncMock(name="adv_setting_menu_instance")
    mock_menu_cls = MagicMock(return_value=menu_instance)
    resolve_cabinet = AsyncMock(return_value=wb_uc)

    with (
        patch.object(handlers, "Message", _FakeMessage),
        patch.object(handlers, "sm", return_value=session_cm),
        patch.object(
            handlers,
            "_load_adv_setting_menu",
            return_value=mock_menu_cls,
        ),
        patch.object(
            handlers,
            "get_wb_user_cabinet_for_adv_and_telegram",
            resolve_cabinet,
        ),
    ):
        await handlers.back_from_card_ab_hold(
            query,
            CardAbHoldBack(adv_setting_original_id=adv.id),
        )

    query.answer.assert_not_awaited()
    resolve_cabinet.assert_awaited_once()
    mock_menu_cls.assert_called_once_with(
        query.bot, msg.chat.id, wb_uc, adv
    )
    menu_instance.assert_awaited_once()

    closed_payloads = [t for t in _edit_text_payloads(msg) if _CLOSED_COPY in t]
    assert closed_payloads == [], (
        "CardAbHoldBack не должен редактировать сообщение в тупик "
        f"{_CLOSED_COPY!r}; получено: {closed_payloads!r}"
    )
    msg.delete.assert_not_awaited()


@pytest.mark.unit
def test_adv_setting_menu_keyboard_imports_without_circular_import() -> None:
    """Regression: keyboard/callbacks не должны ломаться circular import'ом.

    verify NO_GO: top-level ``AdvSettingMenu`` в ``handlers`` ломал
    ``get_adv_setting_keyboard`` и collection ``test_auto_bid_freeze``.
    """
    from app.client_bot.user_interface.views.messages.main_adv_setting_menu.keyboard.keyboard import (
        get_adv_setting_keyboard,
    )

    assert callable(get_adv_setting_keyboard)


@pytest.mark.unit
def test_change_auto_bid_module_imports_without_circular_import() -> None:
    """Adjacent: ``change_auto_bid`` → AdvSettingMenu path остаётся импортируемым."""
    from app.client_bot.user_interface.handlers import change_auto_bid as change_auto_bid_mod

    assert callable(change_auto_bid_mod.open_change_auto_bid)
