"""RED regression for atomic A/B Hold EXIT epoch cleanup.

Тест инжектирует сбой на единственной commit-границе общей write-session.
До исправления production-path подготавливал mode/snapshot отдельным commit.
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.modules.shop_runner.service_manager.services.auto_updater_v3.card_ab_hold.epoch_lifecycle import (
    CardAbHoldSyncStatus,
    clear_epoch_fields_values,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.card_ab_hold.mode import (
    CardAbHoldMode,
    CardAbHoldPhase,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.card_ab_hold.telegram import (
    confirm_handlers,
)

_DURABLE_FIELDS = (
    "card_ab_hold_mode",
    "card_ab_hold_allowed_phrases_snapshot",
    "card_ab_hold_phase",
    "card_ab_hold_warmup_started_at",
    "card_ab_hold_warmup_duration_hours",
    "card_ab_hold_generation",
    "card_ab_hold_wb_sync_idempotency_key",
    "card_ab_hold_pending_intent_json",
    "card_ab_hold_sync_status",
    "card_ab_hold_confirmed_keywords_json",
    "card_ab_hold_confirmed_target_places_json",
    "card_ab_hold_confirmed_auto_participation",
    "card_ab_hold_confirmed_auto_bid",
)


def _snapshot(adv: SimpleNamespace) -> dict[str, object]:
    """Снять проверяемые durable-поля кампании."""
    return {
        field: getattr(adv, field)
        for field in _DURABLE_FIELDS
    }


def _session_cm(session: MagicMock) -> MagicMock:
    """Создать async context manager, моделирующий rollback при исключении."""
    context_manager = MagicMock()
    context_manager.__aenter__ = AsyncMock(return_value=session)

    async def exit_session(*args: object) -> None:
        """Откатить fake transaction, если commit завершился ошибкой."""
        if args and args[0] is not None:
            await session.rollback()

    context_manager.__aexit__ = AsyncMock(side_effect=exit_session)
    return context_manager


@pytest.mark.unit
@pytest.mark.asyncio
async def test_exit_failure_does_not_commit_partial_epoch_state() -> None:
    """EXIT обязан откатывать все поля при ошибке единого commit.

    Инъекция ломает единственную commit-границу после подготовки mode/snapshot
    и epoch reset в одной session. Требование atomic EXIT: durable row до
    отказа должен сохраниться целиком, а не остаться частично изменённым.
    """
    adv = SimpleNamespace(
        id=4004,
        card_ab_hold_mode=CardAbHoldMode.ACTIVE.value,
        card_ab_hold_allowed_phrases_snapshot=["alpha"],
        card_ab_hold_phase=CardAbHoldPhase.READY_ACTIVE.value,
        card_ab_hold_warmup_started_at="2026-08-21T10:00:00+00:00",
        card_ab_hold_warmup_duration_hours=48,
        card_ab_hold_generation=7,
        card_ab_hold_wb_sync_idempotency_key="9004:7",
        card_ab_hold_pending_intent_json={"generation": 7},
        card_ab_hold_sync_status=CardAbHoldSyncStatus.COMPLETE.value,
        card_ab_hold_confirmed_keywords_json=["alpha"],
        card_ab_hold_confirmed_target_places_json={"alpha": 5},
        card_ab_hold_confirmed_auto_participation=True,
        card_ab_hold_confirmed_auto_bid=100.0,
    )
    durable_before = _snapshot(adv)
    durable_state = dict(durable_before)
    attempted_commit_state: dict[str, object] = {}

    session = MagicMock(name="exit_mode_session")
    session.scalar = AsyncMock(return_value=adv)

    async def clear_epoch_without_commit(
        _session: MagicMock,
        _adv_setting_id: int,
        *,
        commit: bool,
    ) -> None:
        """Применить второй in-session write без отдельного commit."""
        assert _session is session
        assert commit is False
        for field, value in clear_epoch_fields_values().items():
            setattr(adv, field, value)

    async def fail_at_single_transaction_boundary() -> None:
        """Зафиксировать подготовленный payload и симулировать отказ commit."""
        attempted_commit_state.update(_snapshot(adv))
        raise RuntimeError("injected EXIT transaction commit failure")

    session.rollback = AsyncMock()
    session.commit = AsyncMock(side_effect=fail_at_single_transaction_boundary)

    with (
        patch.object(confirm_handlers, "sm", return_value=_session_cm(session)),
        patch.object(
            confirm_handlers,
            "clear_epoch_on_exit_in_session",
            side_effect=clear_epoch_without_commit,
        ),
    ):
        with pytest.raises(
            RuntimeError,
            match="injected EXIT transaction commit failure",
        ):
            await confirm_handlers._abort_epoch_to_off(adv)  # type: ignore[arg-type]

    expected_commit_state = dict(durable_before)
    expected_commit_state.update(
        {
            "card_ab_hold_mode": CardAbHoldMode.OFF.value,
            "card_ab_hold_allowed_phrases_snapshot": [],
            **clear_epoch_fields_values(),
        }
    )
    assert attempted_commit_state == expected_commit_state, (
        "EXIT commit boundary did not include mode, snapshot, and all epoch "
        "clears in one transaction"
    )
    assert durable_state == durable_before, (
        "failed EXIT commit left partial durable state; EXIT must be atomic"
    )
    session.commit.assert_awaited_once()
    session.rollback.assert_awaited_once()
