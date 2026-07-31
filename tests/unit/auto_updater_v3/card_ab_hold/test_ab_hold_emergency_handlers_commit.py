"""RED: Emergency handlers must await session.commit() after AdvSetting mutations.

ROOT-001: ``emergency_educate_ack`` / ``emergency_confirm_execute`` mutate latch /
education inside ``sm(read_only=False)`` but never commit; helper contract says
caller commits. Peer Hold handlers do await ``session.commit()``.
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.modules.shop_runner.service_manager.services.auto_updater_v3.card_ab_hold.emergency import (
    EmergencyApplyResult,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.card_ab_hold.mode import (
    CardAbHoldMode,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.card_ab_hold.telegram import (
    emergency_handlers,
    handlers,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.card_ab_hold.telegram.callbacks import (
    CardAbHoldEmergencyConfirm,
    CardAbHoldEmergencyEducate,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.card_ab_hold.telegram.emergency_handlers import (
    EmergencyEducateAckOutcome,
)

pytestmark = pytest.mark.unit


def _writable_session(adv: SimpleNamespace) -> tuple[AsyncMock, MagicMock]:
    """Собрать writable session + async CM для патча ``emergency_handlers.sm``."""
    session = AsyncMock()
    session.get = AsyncMock(return_value=adv)
    session.commit = AsyncMock()
    session_cm = MagicMock()
    session_cm.__aenter__ = AsyncMock(return_value=session)
    session_cm.__aexit__ = AsyncMock(return_value=None)
    return session, session_cm


def _hold_adv(*, adv_id: int = 55) -> SimpleNamespace:
    """AdvSetting-двойник с Hold ACTIVE и paid UI visibility."""
    return SimpleNamespace(
        id=adv_id,
        card_ab_hold_mode=CardAbHoldMode.ACTIVE.value,
        card_ab_hold_phase=None,
        card_ab_hold_emergency_latch=False,
        card_ab_hold_emergency_educated=False,
        bot_active=True,
    )


@pytest.mark.asyncio
async def test_emergency_educate_ack_awaits_session_commit(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Educate ACK ok → await session.commit() до UX (caller-commit contract)."""
    adv = _hold_adv(adv_id=77)
    session, session_cm = _writable_session(adv)
    monkeypatch.setattr(emergency_handlers, "sm", MagicMock(return_value=session_cm))
    seam = AsyncMock(
        return_value=EmergencyEducateAckOutcome(kind="ok", adv=adv)
    )
    monkeypatch.setattr(
        emergency_handlers,
        "acknowledge_emergency_education_in_session",
        seam,
    )
    monkeypatch.setattr(
        handlers, "_screen_status_text", AsyncMock(return_value="Статус: active")
    )
    monkeypatch.setattr(handlers, "_notify_callback_user", AsyncMock())
    monkeypatch.setattr(handlers, "_edit_screen", AsyncMock())

    query = MagicMock()
    cb = CardAbHoldEmergencyEducate(adv_setting_original_id=77)
    await emergency_handlers.emergency_educate_ack(query, cb)

    seam.assert_awaited_once()
    assert seam.await_args is not None
    assert seam.await_args.args[0] is session
    assert seam.await_args.kwargs["adv_setting_original_id"] == 77
    session.commit.assert_awaited()


@pytest.mark.asyncio
async def test_emergency_confirm_execute_awaits_session_commit(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Confirm apply latch — обязан await session.commit() после мутаций."""
    adv = _hold_adv(adv_id=55)
    session, session_cm = _writable_session(adv)
    monkeypatch.setattr(emergency_handlers, "sm", MagicMock(return_value=session_cm))
    monkeypatch.setattr(
        emergency_handlers, "is_card_ab_hold_ui_visible", lambda _adv: True
    )
    apply_result = EmergencyApplyResult(
        latch_already_active=False,
        latch_set=True,
        keywords_blocked=3,
        target_status_paused=True,
        status="ok",
    )
    apply_mock = AsyncMock(return_value=apply_result)
    monkeypatch.setattr(
        emergency_handlers, "apply_ab_hold_emergency_in_session", apply_mock
    )
    monkeypatch.setattr(handlers, "_notify_callback_user", AsyncMock())
    monkeypatch.setattr(handlers, "_edit_screen", AsyncMock())

    query = MagicMock()
    cb = CardAbHoldEmergencyConfirm(adv_setting_original_id=55)
    await emergency_handlers.emergency_confirm_execute(query, cb)

    apply_mock.assert_awaited_once()
    session.commit.assert_awaited()
