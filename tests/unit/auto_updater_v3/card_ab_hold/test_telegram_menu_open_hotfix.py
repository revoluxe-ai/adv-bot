"""Hotfix тесты открытия экрана A/B Hold новым сообщением.

Контракт hotfix:
- экран A/B Hold отправляется только как новое сообщение через ``message.answer``;
- исходное callback-сообщение не редактируется;
- при unsupported callback message type возвращается явный alert без изменения mode;
- произвольные ошибки отправки не проглатываются.
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.modules.shop_runner.service_manager.services.auto_updater_v3.card_ab_hold.mode import (
    CardAbHoldMode,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.card_ab_hold.telegram import (
    handlers,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.card_ab_hold.telegram.callbacks import (
    CardAbHoldBack,
    CardAbHoldDisable,
    CardAbHoldEnable,
    CardAbHoldMenu,
)


class _FakeMessage:
    """Минимальный message-двойник для unit-тестов aiogram callback flow."""

    def __init__(
        self,
        *,
        text: str | None,
        caption: str | None,
        answer_side_effect: BaseException | None = None,
    ) -> None:
        self.text = text
        self.caption = caption
        self.answer = AsyncMock(side_effect=answer_side_effect)
        self.edit_text = AsyncMock()
        self.edit_caption = AsyncMock()


def _make_adv() -> SimpleNamespace:
    """Сконструировать paid/V3 кампанию с режимом OFF для открытия меню."""
    return SimpleNamespace(
        id=42,
        adv_id=4242,
        bot_active=True,
        card_ab_hold_mode=CardAbHoldMode.OFF.value,
        card_ab_hold_degraded=False,
    )


def _make_session(adv: SimpleNamespace) -> tuple[MagicMock, MagicMock]:
    """Вернуть мок session и async context manager для ``sm()``."""
    session = MagicMock()
    session.scalar = AsyncMock(return_value=adv)
    session.commit = AsyncMock()
    session_cm = MagicMock()
    session_cm.__aenter__ = AsyncMock(return_value=session)
    session_cm.__aexit__ = AsyncMock(return_value=None)
    return session, session_cm


def _make_query(message: object) -> MagicMock:
    """Собрать callback query-двойник с настраиваемым ``message``."""
    query = MagicMock()
    query.message = message
    query.answer = AsyncMock()
    return query


def _extract_answer_call(msg: _FakeMessage) -> tuple[str, object]:
    """Извлечь ``text`` и ``reply_markup`` из вызова ``message.answer``."""
    args = msg.answer.await_args.args
    kwargs = msg.answer.await_args.kwargs
    text = kwargs.get("text", args[0] if args else "")
    reply_markup = kwargs.get("reply_markup")
    return text, reply_markup


@pytest.mark.unit
@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("text", "caption"),
    [
        ("Меню кампании", None),
        (None, "media caption"),
    ],
)
async def test_menu_open_sends_new_message_for_text_and_media_callbacks(
    text: str | None, caption: str | None
) -> None:
    """Нажатие callback из text/media message всегда отправляет новый экран."""
    adv = _make_adv()
    session, session_cm = _make_session(adv)
    msg = _FakeMessage(text=text, caption=caption)
    query = _make_query(msg)
    status = "Статус: off"

    with (
        patch.object(handlers, "Message", _FakeMessage),
        patch.object(handlers, "sm", return_value=session_cm),
        patch.object(
            handlers, "_screen_status_text", new=AsyncMock(return_value=status)
        ),
    ):
        await handlers.open_card_ab_hold_menu(
            query, CardAbHoldMenu(adv_setting_original_id=adv.id)
        )

    msg.answer.assert_awaited_once()
    msg.edit_text.assert_not_awaited()
    msg.edit_caption.assert_not_awaited()
    query.answer.assert_not_awaited()
    session.commit.assert_not_awaited()
    assert adv.card_ab_hold_mode == CardAbHoldMode.OFF.value


@pytest.mark.unit
@pytest.mark.asyncio
async def test_menu_open_new_message_has_expected_text_and_keyboard() -> None:
    """Новое сообщение содержит инструкцию + статус и клавиатуру экрана."""
    adv = _make_adv()
    session, session_cm = _make_session(adv)
    msg = _FakeMessage(text="open", caption=None)
    query = _make_query(msg)
    status = "Статус: off"

    with (
        patch.object(handlers, "Message", _FakeMessage),
        patch.object(handlers, "sm", return_value=session_cm),
        patch.object(
            handlers, "_screen_status_text", new=AsyncMock(return_value=status)
        ),
    ):
        await handlers.open_card_ab_hold_menu(
            query, CardAbHoldMenu(adv_setting_original_id=adv.id)
        )

    text, keyboard = _extract_answer_call(msg)
    assert text == f"{handlers._INSTRUCTION}\n{status}"
    assert keyboard is not None
    prefixes = [
        button.callback_data.split(":")[0]
        for row in keyboard.inline_keyboard
        for button in row
        if button.callback_data
    ]
    assert CardAbHoldEnable.__prefix__ in prefixes
    assert CardAbHoldDisable.__prefix__ in prefixes
    assert CardAbHoldBack.__prefix__ in prefixes


@pytest.mark.unit
@pytest.mark.asyncio
async def test_menu_open_unsupported_message_type_alerts_and_keeps_state() -> None:
    """Unsupported callback message type обрабатывается явно и не меняет mode."""
    adv = _make_adv()
    session, session_cm = _make_session(adv)
    query = _make_query(object())
    query.bot = MagicMock()
    query.bot.send_message = AsyncMock()
    query.from_user = SimpleNamespace(id=1)
    before_mode = adv.card_ab_hold_mode

    with (
        patch.object(handlers, "sm", return_value=session_cm),
        patch.object(
            handlers, "_screen_status_text", new=AsyncMock(return_value="Статус: off")
        ),
    ):
        await handlers.open_card_ab_hold_menu(
            query, CardAbHoldMenu(adv_setting_original_id=adv.id)
        )

    query.answer.assert_not_awaited()
    query.bot.send_message.assert_awaited_once()
    alert_text = query.bot.send_message.await_args.args[1]
    assert "неподдерживаемый тип" in alert_text.lower()
    assert adv.card_ab_hold_mode == before_mode
    session.commit.assert_not_awaited()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_edit_screen_does_not_swallow_send_errors() -> None:
    """Произвольные ошибки ``message.answer`` пробрасываются наружу."""
    msg = _FakeMessage(text="open", caption=None, answer_side_effect=RuntimeError("boom"))
    query = _make_query(msg)
    with patch.object(handlers, "Message", _FakeMessage):
        with pytest.raises(RuntimeError, match="boom"):
            await handlers._edit_screen(
                query,
                text="payload",
                adv_id=42,
                mode=CardAbHoldMode.OFF,
            )
    query.answer.assert_not_awaited()

