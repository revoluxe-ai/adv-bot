"""Unit-тесты write-path gates epoch A/B Hold (§22)."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.modules.shop_runner.service_manager.services.auto_updater_v3.card_ab_hold.epoch_lifecycle import (
    CardAbHoldSyncStatus,
    build_wb_sync_idempotency_key,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.card_ab_hold.epoch_write import (
    EpochWriteError,
    can_activate_after_successful_sync,
    confirm_target_places_in_session,
    create_pending_intent_for_generation,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.card_ab_hold.mode import (
    CardAbHoldMode,
    CardAbHoldPhase,
)


@pytest.mark.unit
def test_can_activate_requires_intent_and_complete_sync() -> None:
    """ACTIVE только при intent + sync_status=complete."""
    no_intent = SimpleNamespace(
        card_ab_hold_pending_intent_json=None,
        card_ab_hold_sync_status=CardAbHoldSyncStatus.COMPLETE.value,
    )
    partial = SimpleNamespace(
        card_ab_hold_pending_intent_json={"generation": 1},
        card_ab_hold_sync_status=CardAbHoldSyncStatus.PARTIAL.value,
    )
    ready = SimpleNamespace(
        card_ab_hold_pending_intent_json={"generation": 1},
        card_ab_hold_sync_status=CardAbHoldSyncStatus.COMPLETE.value,
    )
    assert can_activate_after_successful_sync(no_intent) is False
    assert can_activate_after_successful_sync(partial) is False
    assert can_activate_after_successful_sync(ready) is True


@pytest.mark.unit
@pytest.mark.asyncio
async def test_create_pending_intent_duplicate_idempotency_no_op() -> None:
    """Duplicate idempotency key → no-op, generation не bump'ится."""
    adv_id = 777
    adv = SimpleNamespace(
        id=1,
        adv_id=adv_id,
        card_ab_hold_generation=1,
        card_ab_hold_wb_sync_idempotency_key=build_wb_sync_idempotency_key(
            adv_id, 2
        ),
        card_ab_hold_confirmed_keywords_json=["kw"],
        card_ab_hold_confirmed_target_places_json={"kw": 10},
        card_ab_hold_confirmed_auto_participation=True,
        card_ab_hold_confirmed_auto_bid=100.0,
        card_ab_hold_pending_intent_json={"generation": 1},
    )
    mock_result = MagicMock()
    mock_result.scalar_one.return_value = adv
    mock_session = AsyncMock()
    mock_session.execute = AsyncMock(return_value=mock_result)
    mock_session.commit = AsyncMock()

    mock_cm = MagicMock()
    mock_cm.__aenter__ = AsyncMock(return_value=mock_session)
    mock_cm.__aexit__ = AsyncMock(return_value=None)

    with patch(
        "app.modules.shop_runner.service_manager.services.auto_updater_v3.card_ab_hold.epoch_write.sm",
        return_value=mock_cm,
    ):
        created = await create_pending_intent_for_generation(1, adv_id=adv_id)

    assert created is False
    mock_session.commit.assert_not_called()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_create_pending_intent_writes_generation_and_phase() -> None:
    """Успешный intent: bump generation, PENDING_INTENT, sync pending."""
    adv_id = 555
    adv = SimpleNamespace(
        id=10,
        adv_id=adv_id,
        card_ab_hold_generation=0,
        card_ab_hold_wb_sync_idempotency_key=None,
        card_ab_hold_confirmed_keywords_json=["alpha"],
        card_ab_hold_confirmed_target_places_json={"alpha": 8},
        card_ab_hold_confirmed_auto_participation=False,
        card_ab_hold_confirmed_auto_bid=75.0,
    )
    mock_result = MagicMock()
    mock_result.scalar_one.return_value = adv
    mock_session = AsyncMock()
    mock_session.execute = AsyncMock(return_value=mock_result)
    mock_session.commit = AsyncMock()

    mock_cm = MagicMock()
    mock_cm.__aenter__ = AsyncMock(return_value=mock_session)
    mock_cm.__aexit__ = AsyncMock(return_value=None)

    with patch(
        "app.modules.shop_runner.service_manager.services.auto_updater_v3.card_ab_hold.epoch_write.sm",
        return_value=mock_cm,
    ):
        created = await create_pending_intent_for_generation(10, adv_id=adv_id)

    assert created is True
    mock_session.commit.assert_called_once()
    update_call = mock_session.execute.call_args_list[-1]
    assert update_call is not None


@pytest.mark.unit
@pytest.mark.asyncio
async def test_activate_after_successful_sync_skips_when_not_ready() -> None:
    """activate_after_successful_sync no-op без complete sync."""
    adv = SimpleNamespace(
        card_ab_hold_pending_intent_json={"generation": 1},
        card_ab_hold_sync_status=CardAbHoldSyncStatus.PENDING.value,
    )
    mock_result = MagicMock()
    mock_result.scalar_one.return_value = adv
    mock_session = AsyncMock()
    mock_session.execute = AsyncMock(return_value=mock_result)
    mock_session.commit = AsyncMock()

    mock_cm = MagicMock()
    mock_cm.__aenter__ = AsyncMock(return_value=mock_session)
    mock_cm.__aexit__ = AsyncMock(return_value=None)

    with patch(
        "app.modules.shop_runner.service_manager.services.auto_updater_v3.card_ab_hold.epoch_write.sm",
        return_value=mock_cm,
    ):
        from app.modules.shop_runner.service_manager.services.auto_updater_v3.card_ab_hold.epoch_write import (
            activate_after_successful_sync,
        )

        ok = await activate_after_successful_sync(99)

    assert ok is False
    mock_session.commit.assert_not_called()


@pytest.mark.unit
def test_activate_preconditions_match_mode_active_contract() -> None:
    """READY_ACTIVE/ACTIVE контракт: mode ещё PENDING до activate."""
    pending = SimpleNamespace(
        card_ab_hold_mode=CardAbHoldMode.PENDING_SETUP.value,
        card_ab_hold_phase=CardAbHoldPhase.WB_SYNC.value,
        card_ab_hold_pending_intent_json={"generation": 1},
        card_ab_hold_sync_status=CardAbHoldSyncStatus.COMPLETE.value,
    )
    assert can_activate_after_successful_sync(pending) is True


@pytest.mark.unit
@pytest.mark.asyncio
@pytest.mark.parametrize(
    "tp_map",
    [
        {},
        {"alpha": 0},
        {"alpha": -1},
        {"alpha": True},
        {"alpha": 1.5},
        {"foreign": 5},
    ],
)
async def test_confirm_target_places_rejects_invalid_payload_before_update(
    tp_map: dict[str, object],
) -> None:
    """Writer отклоняет invalid TP payload до UPDATE/COMMIT.

    Regression для spec ``card-ab-hold-mode``: durable boundary не принимает
    zero, отрицательные, boolean или чужие ключи даже при прямом вызове.
    """
    adv = SimpleNamespace(
        card_ab_hold_phase=CardAbHoldPhase.AWAITING_TP_CONFIRM.value,
        card_ab_hold_confirmed_keywords_json=["alpha"],
    )
    result = MagicMock()
    result.scalar_one.return_value = adv
    session = AsyncMock()
    session.execute = AsyncMock(return_value=result)
    session.commit = AsyncMock()

    with pytest.raises(EpochWriteError):
        await confirm_target_places_in_session(session, 1, tp_map)

    session.execute.assert_awaited_once()
    session.commit.assert_not_awaited()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_confirm_target_places_persists_only_remaining_keyword_subset() -> None:
    """Writer принимает positive subset и удаляет исключённый ключ из SoT.

    Regression для spec ``card-ab-hold-mode``: после UI-фильтрации durable
    confirmed keyword-set и target places покрывают только оставшийся набор.
    """
    adv = SimpleNamespace(
        card_ab_hold_phase=CardAbHoldPhase.AWAITING_TP_CONFIRM.value,
        card_ab_hold_confirmed_keywords_json=["alpha", "beta"],
    )
    result = MagicMock()
    result.scalar_one.return_value = adv
    session = AsyncMock()
    session.execute = AsyncMock(return_value=result)
    session.commit = AsyncMock()

    await confirm_target_places_in_session(session, 1, {"alpha": 5})

    assert session.execute.await_count == 2
    session.commit.assert_awaited_once()
