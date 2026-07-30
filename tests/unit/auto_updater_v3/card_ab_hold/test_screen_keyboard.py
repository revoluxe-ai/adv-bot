"""§12: keyboard MAY hide Enable while PENDING/ACTIVE (decision §11).

OFF → Enable+Disable+Back; PENDING/ACTIVE → Disable+Back, Enable absent.
§10 handler no-op остаётся safety net (см. test_enable_idempotent).
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.modules.shop_runner.service_manager.services.auto_updater_v3.card_ab_hold.mode import (
    CardAbHoldMode,
    CardAbHoldPhase,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.card_ab_hold.telegram import (
    handlers,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.card_ab_hold.telegram.callbacks import (
    CardAbHoldBack,
    CardAbHoldDisable,
    CardAbHoldEnable,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.card_ab_hold.ui_access import (
    should_offer_card_ab_hold_enable_control,
)


def _button_callback_prefixes(markup) -> list[str]:
    """Собрать prefix callback_data кнопок клавиатуры."""
    prefixes: list[str] = []
    for row in markup.inline_keyboard:
        for btn in row:
            data = btn.callback_data or ""
            prefixes.append(data.split(":")[0])
    return prefixes


@pytest.mark.unit
@pytest.mark.parametrize(
    ("mode", "offer_enable"),
    [
        (CardAbHoldMode.OFF, True),
        (CardAbHoldMode.PENDING_SETUP, False),
        (CardAbHoldMode.ACTIVE, False),
    ],
)
def test_should_offer_enable_control_matrix(
    mode: CardAbHoldMode, offer_enable: bool
) -> None:
    """12.1: Enable только при OFF; PENDING/ACTIVE — скрыть."""
    assert should_offer_card_ab_hold_enable_control(mode) is offer_enable


@pytest.mark.unit
def test_screen_keyboard_off_has_enable_disable_back() -> None:
    """12.1 OFF: Enable + Disable + Back."""
    markup = handlers._screen_keyboard(42, CardAbHoldMode.OFF)
    prefixes = _button_callback_prefixes(markup)
    assert CardAbHoldEnable.__prefix__ in prefixes
    assert CardAbHoldDisable.__prefix__ in prefixes
    assert CardAbHoldBack.__prefix__ in prefixes


@pytest.mark.unit
@pytest.mark.parametrize(
    "mode",
    [CardAbHoldMode.PENDING_SETUP, CardAbHoldMode.ACTIVE],
)
def test_screen_keyboard_pending_or_active_hides_enable(
    mode: CardAbHoldMode,
) -> None:
    """12.1 PENDING/ACTIVE: Disable+Back, Enable отсутствует."""
    markup = handlers._screen_keyboard(42, mode)
    prefixes = _button_callback_prefixes(markup)
    assert CardAbHoldEnable.__prefix__ not in prefixes
    assert CardAbHoldDisable.__prefix__ in prefixes
    assert CardAbHoldBack.__prefix__ in prefixes


@pytest.mark.unit
@pytest.mark.asyncio
async def test_edit_screen_passes_mode_into_keyboard() -> None:
    """12.2 wiring: ``_edit_screen`` прокидывает mode (+phase) в ``_screen_keyboard``."""
    query = MagicMock()
    query.message = MagicMock()
    query.message.answer = AsyncMock()
    keyboard = MagicMock(name="markup")
    with (
        patch.object(handlers, "Message", type(query.message)),
        patch.object(handlers, "_screen_keyboard", return_value=keyboard) as kb,
    ):
        ok = await handlers._edit_screen(
            query,
            text="payload",
            adv_id=42,
            mode=CardAbHoldMode.ACTIVE,
            phase=CardAbHoldPhase.READY_ACTIVE,
        )
    assert ok is True
    kb.assert_called_once_with(
        42,
        CardAbHoldMode.ACTIVE,
        phase=CardAbHoldPhase.READY_ACTIVE,
        emergency_educated=False,
        emergency_latch=False,
    )
    query.message.answer.assert_awaited_once_with(
        "payload", reply_markup=keyboard
    )
