"""Regression: epoch-managed S0 MUST bridge to confirm-flow.

BUGCASE-EPOCHS0-20260727T214440Z / ROOT-001:
После epoch Enable (mode≠OFF, phase AWAITING_KEYWORD_CONFIRM) S0/status
клавиатура MUST содержать «Открыть текущий шаг» (CahOpenCurrentStep) —
UX contract §5. Запрещён MVP-1 набор только Disable/Back без confirm bridge.

До фикса тест обязан падать: ``_screen_keyboard`` не эмитит cah_os.
"""

from __future__ import annotations

import inspect
from types import SimpleNamespace
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from aiogram.types import InlineKeyboardMarkup

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
from app.modules.shop_runner.service_manager.services.auto_updater_v3.card_ab_hold.telegram.confirm_callbacks import (
    CahOpenCurrentStep,
)

_OPEN_STEP_LABEL = "Открыть текущий шаг"


def _button_texts(markup: InlineKeyboardMarkup) -> list[str]:
    """Тексты кнопок клавиатуры сверху вниз."""
    return [btn.text or "" for row in markup.inline_keyboard for btn in row]


def _button_callback_prefixes(markup: InlineKeyboardMarkup) -> list[str]:
    """Prefix callback_data кнопок (до первого ``:``)."""
    prefixes: list[str] = []
    for row in markup.inline_keyboard:
        for btn in row:
            data = btn.callback_data or ""
            prefixes.append(data.split(":")[0])
    return prefixes


def _call_screen_keyboard(
    adv_id: int,
    mode: CardAbHoldMode | str,
    *,
    phase: CardAbHoldPhase | str | None = None,
    revision: int | None = None,
) -> InlineKeyboardMarkup:
    """Вызвать ``_screen_keyboard`` с ``phase=`` когда seam уже есть.

    До GO production принимает только ``(adv_id, mode)`` — тогда epoch-баг
    проявляется на том же PENDING keyboard (нет Open). После GO с ``phase=``
    тест передаёт phase явно. ``revision=`` передаётся только после появления
    production seam, чтобы RED-тест проверял текущий hard-coded callback.
    """
    sig = inspect.signature(handlers._screen_keyboard)
    kwargs: dict[str, Any] = {}
    if "phase" in sig.parameters:
        kwargs["phase"] = phase
    if revision is not None and "revision" in sig.parameters:
        kwargs["revision"] = revision
    return handlers._screen_keyboard(adv_id, mode, **kwargs)


@pytest.mark.unit
def test_s0_epoch_pending_keyboard_offers_open_current_step_bridge() -> None:
    """ROOT-001 blocked: epoch PENDING + AWAITING_KEYWORD_CONFIRM → Open bridge.

    Инвариант: S0 mode≠OFF с epoch phase MUST дать «Открыть текущий шаг»
    и ``CahOpenCurrentStep`` (cah_os), плюс Disable/Back; Enable скрыт.
    Падает на текущем MVP-1 Disable/Back-only keyboard.
    """
    markup = _call_screen_keyboard(
        42,
        CardAbHoldMode.PENDING_SETUP,
        phase=CardAbHoldPhase.AWAITING_KEYWORD_CONFIRM,
    )
    texts = _button_texts(markup)
    prefixes = _button_callback_prefixes(markup)

    assert _OPEN_STEP_LABEL in texts, (
        "S0 epoch-managed PENDING MUST offer «Открыть текущий шаг» "
        "(UX §5 / ROOT-001); got texts=%r" % (texts,)
    )
    assert CahOpenCurrentStep.__prefix__ in prefixes
    assert CardAbHoldDisable.__prefix__ in prefixes
    assert CardAbHoldBack.__prefix__ in prefixes
    assert CardAbHoldEnable.__prefix__ not in prefixes


@pytest.mark.unit
def test_s0_open_current_step_carries_current_revision() -> None:
    """S0 bridge MUST carry the current draft/epoch revision, not ``1``."""
    current_revision = 7
    markup = _call_screen_keyboard(
        42,
        CardAbHoldMode.PENDING_SETUP,
        phase=CardAbHoldPhase.AWAITING_KEYWORD_CONFIRM,
        revision=current_revision,
    )

    open_button = next(
        button
        for row in markup.inline_keyboard
        for button in row
        if button.text == _OPEN_STEP_LABEL
    )
    callback = CahOpenCurrentStep.unpack(open_button.callback_data or "")

    assert callback.revision == current_revision


@pytest.mark.unit
def test_s0_off_keyboard_does_not_offer_open_current_step() -> None:
    """Allowed: mode OFF — Enable/Disable/Back, без confirm deep-link."""
    markup = _call_screen_keyboard(42, CardAbHoldMode.OFF, phase=None)
    texts = _button_texts(markup)
    prefixes = _button_callback_prefixes(markup)

    assert _OPEN_STEP_LABEL not in texts
    assert CahOpenCurrentStep.__prefix__ not in prefixes
    assert CardAbHoldEnable.__prefix__ in prefixes
    assert CardAbHoldDisable.__prefix__ in prefixes
    assert CardAbHoldBack.__prefix__ in prefixes


@pytest.mark.unit
def test_s0_legacy_pending_without_phase_does_not_offer_open_current_step() -> None:
    """Allowed: legacy MVP-1 PENDING (phase NULL) — без Open (ROOT-001 scope).

    Требует production seam ``phase=`` на ``_screen_keyboard``. Без seam
    skip: иначе нельзя отличить legacy от epoch на одном mode.
    """
    if "phase" not in inspect.signature(handlers._screen_keyboard).parameters:
        pytest.skip(
            "phase= seam ещё нет на _screen_keyboard; paired legacy gate "
            "включится после GO"
        )
    markup = _call_screen_keyboard(
        42, CardAbHoldMode.PENDING_SETUP, phase=None
    )
    texts = _button_texts(markup)
    prefixes = _button_callback_prefixes(markup)

    assert _OPEN_STEP_LABEL not in texts
    assert CahOpenCurrentStep.__prefix__ not in prefixes
    assert CardAbHoldDisable.__prefix__ in prefixes
    assert CardAbHoldBack.__prefix__ in prefixes


class _FakeMessage:
    """Message-двойник для post-enable ``_edit_screen`` → ``answer``."""

    def __init__(self) -> None:
        self.answer = AsyncMock()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_epoch_enable_renders_s0_with_open_current_step_bridge() -> None:
    """ROOT-001 runtime: epoch Enable → экран S0 с confirm bridge в keyboard.

    Падает, пока post-enable ``_edit_screen`` рисует MVP-1 keyboard без Open
    (или пока Enable не уходит сразу в ``_render_for_adv`` с тем же bridge).
    """
    adv = SimpleNamespace(
        id=9,
        adv_id=99,
        wb_cabinet=SimpleNamespace(shop_id="1"),
        bot_active=True,
        max_price_for_order=100.0,
        card_ab_hold_mode=CardAbHoldMode.OFF.value,
        card_ab_hold_degraded=False,
    )
    session = MagicMock()
    session.scalar = AsyncMock(return_value=adv)
    session_cm = MagicMock()
    session_cm.__aenter__ = AsyncMock(return_value=session)
    session_cm.__aexit__ = AsyncMock(return_value=None)

    refreshed = SimpleNamespace(
        id=9,
        adv_id=99,
        bot_active=True,
        card_ab_hold_mode=CardAbHoldMode.PENDING_SETUP.value,
        card_ab_hold_phase=CardAbHoldPhase.AWAITING_KEYWORD_CONFIRM.value,
        card_ab_hold_degraded=False,
    )
    refresh_session = MagicMock()
    refresh_session.scalar = AsyncMock(return_value=refreshed)
    refresh_cm = MagicMock()
    refresh_cm.__aenter__ = AsyncMock(return_value=refresh_session)
    refresh_cm.__aexit__ = AsyncMock(return_value=None)

    msg = _FakeMessage()
    query = MagicMock()
    query.answer = AsyncMock()
    query.message = msg
    callback = CardAbHoldEnable(adv_setting_original_id=9)
    start_epoch = AsyncMock(return_value=True)
    render_for_adv = AsyncMock(name="_render_for_adv")

    with (
        patch.object(handlers, "Message", _FakeMessage),
        patch.object(handlers, "sm", side_effect=[session_cm, refresh_cm]),
        patch.object(handlers, "start_epoch_on_enable", start_epoch),
        patch.object(
            handlers,
            "evaluate_ab_hold_enable_stats",
            new_callable=AsyncMock,
            return_value=(True, None),
        ),
        patch.object(
            handlers,
            "evaluate_ab_hold_launch_view_volume",
            new_callable=AsyncMock,
        ) as eval_volume,
        patch.object(
            handlers,
            "CardAbHoldSignalRedisCache",
            return_value=MagicMock(set_signal=AsyncMock()),
        ),
        patch.object(
            handlers,
            "CardAbHoldLastAbortRedisCache",
            return_value=MagicMock(get_abort=AsyncMock(return_value=None)),
        ),
        patch(
            "app.modules.shop_runner.service_manager.services.auto_updater_v3."
            "card_ab_hold.telegram.confirm_handlers._render_for_adv",
            render_for_adv,
        ),
    ):
        eval_volume.return_value.is_unavailable = False
        eval_volume.return_value.is_sufficient = True
        await handlers.enable_card_ab_hold(query, callback)

    start_epoch.assert_awaited_once()

    # Accept either immediate confirm render OR S0 keyboard with Open bridge.
    if render_for_adv.await_count:
        return

    assert msg.answer.await_count >= 1, (
        "epoch Enable MUST render a screen (answer) or _render_for_adv"
    )
    reply_markup = None
    for call in msg.answer.await_args_list:
        if "reply_markup" in call.kwargs:
            reply_markup = call.kwargs["reply_markup"]
            break
        if len(call.args) >= 2:
            reply_markup = call.args[1]
            break
    assert isinstance(reply_markup, InlineKeyboardMarkup)
    texts = _button_texts(reply_markup)
    prefixes = _button_callback_prefixes(reply_markup)
    assert _OPEN_STEP_LABEL in texts, (
        "post-enable S0 keyboard MUST include «Открыть текущий шаг»; "
        "got texts=%r" % (texts,)
    )
    assert CahOpenCurrentStep.__prefix__ in prefixes
