"""Unit-тесты epoch tick: PENDING intent WB sync → ACTIVE (§22)."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.modules.shop_runner.service_manager.services.auto_updater_v3.card_ab_hold.epoch_lifecycle import (
    CardAbHoldSyncStatus,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.card_ab_hold.epoch_pipelines import (
    process_ab_epoch,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.card_ab_hold.mode import (
    CardAbHoldMode,
    CardAbHoldPhase,
)


@pytest.fixture(autouse=True)
def _stub_enter_common_bid_reset() -> None:
    """Изолировать §22 sync-тесты от §19 ENTER common-bid Redis/WB path.

    ``process_ab_epoch`` always calls ``ensure_search_common_bid_reset_on_enter``;
    stubs without AdvSetting.adv_id / Redis would otherwise fail before sync body.
    """
    with patch(
        "app.modules.shop_runner.service_manager.services.auto_updater_v3."
        "card_ab_hold.epoch_pipelines.ensure_search_common_bid_reset_on_enter",
        new_callable=AsyncMock,
    ):
        yield


def _sync_adv(
    *,
    intent: dict | None,
    generation: int = 1,
    sync_status: str = "pending",
    phase: str | None = None,
) -> SimpleNamespace:
    """Собрать ComplexAdv-подобный stub с production enum values."""
    adv_setting = SimpleNamespace(
        id=99,
        adv_id=5000,
        card_ab_hold_phase=phase or CardAbHoldPhase.PENDING_INTENT.value,
        card_ab_hold_sync_status=sync_status,
        card_ab_hold_pending_intent_json=intent,
        card_ab_hold_generation=generation,
        card_ab_hold_mode=CardAbHoldMode.PENDING_SETUP.value,
    )
    return SimpleNamespace(
        adv_id=5000,
        shop_id=1,
        card_ab_hold_mode=CardAbHoldMode.PENDING_SETUP.value,
        adv_setting=adv_setting,
        nmids=[10, 20],
        auto_adv_id=5001,
    )


_INTENT = {
    "generation": 1,
    "keywords": ["alpha"],
    "target_places": {"alpha": 8},
    "auto_participation": True,
    "auto_bid": 120.0,
}


@pytest.mark.unit
@pytest.mark.asyncio
async def test_no_intent_stays_non_active() -> None:
    """Нет durable intent → no ACTIVE, no sync."""
    adv = _sync_adv(intent=None)
    with patch(
        "app.modules.shop_runner.service_manager.services.auto_updater_v3."
        "card_ab_hold.epoch_pipelines.apply_confirmed_intent_to_pg",
        new_callable=AsyncMock,
    ) as mock_pg:
        await process_ab_epoch(
            adv,
            wb_shop_data_manager=MagicMock(),
            wb_manager_hub=MagicMock(),
        )
    mock_pg.assert_not_called()
    assert adv.card_ab_hold_mode == CardAbHoldMode.PENDING_SETUP.value


@pytest.mark.unit
@pytest.mark.asyncio
async def test_sync_partial_keeps_generation_and_phase_wb_sync() -> None:
    """WB fail → partial, generation/intent без bump."""
    adv = _sync_adv(intent=_INTENT, generation=1)
    with (
        patch(
            "app.modules.shop_runner.service_manager.services.auto_updater_v3."
            "card_ab_hold.epoch_pipelines.apply_confirmed_intent_to_pg",
            new_callable=AsyncMock,
        ),
        patch(
            "app.modules.shop_runner.service_manager.services.auto_updater_v3."
            "card_ab_hold.epoch_pipelines.sync_intent_to_wb",
            new_callable=AsyncMock,
            side_effect=RuntimeError("wb down"),
        ),
        patch(
            "app.modules.shop_runner.service_manager.services.auto_updater_v3."
            "card_ab_hold.epoch_pipelines.mark_wb_sync_status",
            new_callable=AsyncMock,
        ) as mock_mark,
        patch(
            "app.modules.shop_runner.service_manager.services.auto_updater_v3."
            "card_ab_hold.epoch_pipelines.activate_after_successful_sync",
            new_callable=AsyncMock,
        ) as mock_activate,
    ):
        await process_ab_epoch(
            adv,
            wb_shop_data_manager=MagicMock(),
            wb_manager_hub=MagicMock(),
            stats_fresh=True,
        )
    mock_mark.assert_awaited_once_with(99, CardAbHoldSyncStatus.PARTIAL)
    mock_activate.assert_not_called()
    assert adv.adv_setting.card_ab_hold_phase == CardAbHoldPhase.WB_SYNC.value
    assert adv.adv_setting.card_ab_hold_generation == 1


@pytest.mark.unit
@pytest.mark.asyncio
async def test_sync_success_activates_campaign() -> None:
    """Full success → complete sync + ACTIVE."""
    adv = _sync_adv(intent=_INTENT)
    with (
        patch(
            "app.modules.shop_runner.service_manager.services.auto_updater_v3."
            "card_ab_hold.epoch_pipelines.apply_confirmed_intent_to_pg",
            new_callable=AsyncMock,
        ),
        patch(
            "app.modules.shop_runner.service_manager.services.auto_updater_v3."
            "card_ab_hold.epoch_pipelines.sync_intent_to_wb",
            new_callable=AsyncMock,
        ),
        patch(
            "app.modules.shop_runner.service_manager.services.auto_updater_v3."
            "card_ab_hold.epoch_pipelines.mark_wb_sync_status",
            new_callable=AsyncMock,
        ) as mock_mark,
        patch(
            "app.modules.shop_runner.service_manager.services.auto_updater_v3."
            "card_ab_hold.epoch_pipelines.activate_after_successful_sync",
            new_callable=AsyncMock,
            return_value=True,
        ) as mock_activate,
    ):
        await process_ab_epoch(
            adv,
            wb_shop_data_manager=MagicMock(),
            wb_manager_hub=MagicMock(),
            stats_fresh=True,
        )
    mock_mark.assert_awaited_once_with(99, CardAbHoldSyncStatus.COMPLETE)
    mock_activate.assert_awaited_once_with(99)
    assert adv.card_ab_hold_mode == CardAbHoldMode.ACTIVE.value
    assert adv.adv_setting.card_ab_hold_mode == CardAbHoldMode.ACTIVE.value


@pytest.mark.unit
@pytest.mark.asyncio
async def test_stale_stats_does_not_block_pending_intent_wb_sync() -> None:
    """PBH-005 / §17 carve-out: stale MUST NOT skip apply snapshot of PENDING intent.

    Decide-class freeze remains elsewhere; after durable intent, PG apply + WB sync
    proceed even when ``stats_fresh=False``.
    """
    adv = _sync_adv(intent=_INTENT)
    with (
        patch(
            "app.modules.shop_runner.service_manager.services.auto_updater_v3."
            "card_ab_hold.epoch_pipelines.apply_confirmed_intent_to_pg",
            new_callable=AsyncMock,
        ) as mock_pg,
        patch(
            "app.modules.shop_runner.service_manager.services.auto_updater_v3."
            "card_ab_hold.epoch_pipelines.sync_intent_to_wb",
            new_callable=AsyncMock,
        ) as mock_wb,
        patch(
            "app.modules.shop_runner.service_manager.services.auto_updater_v3."
            "card_ab_hold.epoch_pipelines.mark_wb_sync_status",
            new_callable=AsyncMock,
        ),
        patch(
            "app.modules.shop_runner.service_manager.services.auto_updater_v3."
            "card_ab_hold.epoch_pipelines.activate_after_successful_sync",
            new_callable=AsyncMock,
            return_value=True,
        ),
    ):
        await process_ab_epoch(
            adv,
            wb_shop_data_manager=MagicMock(),
            wb_manager_hub=MagicMock(),
            stats_fresh=False,
        )
    mock_pg.assert_awaited_once()
    mock_wb.assert_awaited_once()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_complete_residual_activates_without_wb_reentry() -> None:
    """Residual complete + WB_SYNC: activate-only, без PG/WB re-apply."""
    adv = _sync_adv(
        intent=_INTENT,
        sync_status=CardAbHoldSyncStatus.COMPLETE.value,
        phase=CardAbHoldPhase.WB_SYNC.value,
    )
    with (
        patch(
            "app.modules.shop_runner.service_manager.services.auto_updater_v3."
            "card_ab_hold.epoch_pipelines.apply_confirmed_intent_to_pg",
            new_callable=AsyncMock,
        ) as mock_pg,
        patch(
            "app.modules.shop_runner.service_manager.services.auto_updater_v3."
            "card_ab_hold.epoch_pipelines.sync_intent_to_wb",
            new_callable=AsyncMock,
        ) as mock_wb,
        patch(
            "app.modules.shop_runner.service_manager.services.auto_updater_v3."
            "card_ab_hold.epoch_pipelines.activate_after_successful_sync",
            new_callable=AsyncMock,
            return_value=True,
        ) as mock_activate,
    ):
        await process_ab_epoch(
            adv,
            wb_shop_data_manager=MagicMock(),
            wb_manager_hub=MagicMock(),
            stats_fresh=True,
        )
    mock_pg.assert_not_called()
    mock_wb.assert_not_called()
    mock_activate.assert_awaited_once_with(99)
    assert adv.card_ab_hold_mode == CardAbHoldMode.ACTIVE.value
    assert adv.adv_setting.card_ab_hold_phase == CardAbHoldPhase.READY_ACTIVE.value
    assert (
        adv.adv_setting.card_ab_hold_sync_status
        == CardAbHoldSyncStatus.COMPLETE.value
    )


@pytest.mark.unit
@pytest.mark.asyncio
async def test_complete_residual_stale_stats_still_activates() -> None:
    """§23 freeze не блокирует activate-only после durable complete."""
    adv = _sync_adv(
        intent=_INTENT,
        sync_status=CardAbHoldSyncStatus.COMPLETE.value,
        phase=CardAbHoldPhase.WB_SYNC.value,
    )
    with (
        patch(
            "app.modules.shop_runner.service_manager.services.auto_updater_v3."
            "card_ab_hold.epoch_pipelines.sync_intent_to_wb",
            new_callable=AsyncMock,
        ) as mock_wb,
        patch(
            "app.modules.shop_runner.service_manager.services.auto_updater_v3."
            "card_ab_hold.epoch_pipelines.apply_confirmed_intent_to_pg",
            new_callable=AsyncMock,
        ) as mock_pg,
        patch(
            "app.modules.shop_runner.service_manager.services.auto_updater_v3."
            "card_ab_hold.epoch_pipelines.activate_after_successful_sync",
            new_callable=AsyncMock,
            return_value=True,
        ) as mock_activate,
    ):
        await process_ab_epoch(
            adv,
            wb_shop_data_manager=MagicMock(),
            wb_manager_hub=MagicMock(),
            stats_fresh=False,
        )
    mock_wb.assert_not_called()
    mock_pg.assert_not_called()
    mock_activate.assert_awaited_once_with(99)
    assert adv.card_ab_hold_mode == CardAbHoldMode.ACTIVE.value


@pytest.mark.unit
@pytest.mark.asyncio
async def test_pending_still_enters_wb_sync() -> None:
    """Allowed sibling: pending остаётся eligible для WB sync."""
    adv = _sync_adv(
        intent=_INTENT,
        sync_status=CardAbHoldSyncStatus.PENDING.value,
        phase=CardAbHoldPhase.PENDING_INTENT.value,
    )
    with (
        patch(
            "app.modules.shop_runner.service_manager.services.auto_updater_v3."
            "card_ab_hold.epoch_pipelines.apply_confirmed_intent_to_pg",
            new_callable=AsyncMock,
        ) as mock_pg,
        patch(
            "app.modules.shop_runner.service_manager.services.auto_updater_v3."
            "card_ab_hold.epoch_pipelines.sync_intent_to_wb",
            new_callable=AsyncMock,
        ) as mock_wb,
        patch(
            "app.modules.shop_runner.service_manager.services.auto_updater_v3."
            "card_ab_hold.epoch_pipelines.mark_wb_sync_status",
            new_callable=AsyncMock,
        ),
        patch(
            "app.modules.shop_runner.service_manager.services.auto_updater_v3."
            "card_ab_hold.epoch_pipelines.activate_after_successful_sync",
            new_callable=AsyncMock,
            return_value=True,
        ),
    ):
        await process_ab_epoch(
            adv,
            wb_shop_data_manager=MagicMock(),
            wb_manager_hub=MagicMock(),
            stats_fresh=True,
        )
    mock_pg.assert_awaited_once()
    mock_wb.assert_awaited_once()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_activate_exception_after_complete_keeps_complete() -> None:
    """CHILD-002: ошибка activation после COMPLETE не демоитит в PARTIAL."""
    adv = _sync_adv(intent=_INTENT)
    with (
        patch(
            "app.modules.shop_runner.service_manager.services.auto_updater_v3."
            "card_ab_hold.epoch_pipelines.apply_confirmed_intent_to_pg",
            new_callable=AsyncMock,
        ),
        patch(
            "app.modules.shop_runner.service_manager.services.auto_updater_v3."
            "card_ab_hold.epoch_pipelines.sync_intent_to_wb",
            new_callable=AsyncMock,
        ),
        patch(
            "app.modules.shop_runner.service_manager.services.auto_updater_v3."
            "card_ab_hold.epoch_pipelines.mark_wb_sync_status",
            new_callable=AsyncMock,
        ) as mock_mark,
        patch(
            "app.modules.shop_runner.service_manager.services.auto_updater_v3."
            "card_ab_hold.epoch_pipelines.activate_after_successful_sync",
            new_callable=AsyncMock,
            side_effect=RuntimeError("activate boom"),
        ),
    ):
        await process_ab_epoch(
            adv,
            wb_shop_data_manager=MagicMock(),
            wb_manager_hub=MagicMock(),
            stats_fresh=True,
        )
    mock_mark.assert_awaited_once_with(99, CardAbHoldSyncStatus.COMPLETE)
    assert (
        adv.adv_setting.card_ab_hold_sync_status
        == CardAbHoldSyncStatus.COMPLETE.value
    )
    assert adv.card_ab_hold_mode == CardAbHoldMode.PENDING_SETUP.value


@pytest.mark.unit
@pytest.mark.asyncio
async def test_next_tick_after_activate_boom_is_activate_only_no_wb_reentry() -> None:
    """Bugbot COMPLETE residual: после activate boom next tick не re-sync WB.

    На d999e49 suite покрывал только same-tick success (COMPLETE+activate в одном
    вызове). Residual ``COMPLETE`` + ``WB_SYNC`` + ``PENDING_SETUP`` на следующем
    тике оставался без теста → ``needs_sync`` снова гонял PG/WB apply.
    """
    adv = _sync_adv(intent=_INTENT)
    with (
        patch(
            "app.modules.shop_runner.service_manager.services.auto_updater_v3."
            "card_ab_hold.epoch_pipelines.apply_confirmed_intent_to_pg",
            new_callable=AsyncMock,
        ) as mock_pg,
        patch(
            "app.modules.shop_runner.service_manager.services.auto_updater_v3."
            "card_ab_hold.epoch_pipelines.sync_intent_to_wb",
            new_callable=AsyncMock,
        ) as mock_wb,
        patch(
            "app.modules.shop_runner.service_manager.services.auto_updater_v3."
            "card_ab_hold.epoch_pipelines.mark_wb_sync_status",
            new_callable=AsyncMock,
        ),
        patch(
            "app.modules.shop_runner.service_manager.services.auto_updater_v3."
            "card_ab_hold.epoch_pipelines.activate_after_successful_sync",
            new_callable=AsyncMock,
            side_effect=RuntimeError("activate boom"),
        ),
    ):
        await process_ab_epoch(
            adv,
            wb_shop_data_manager=MagicMock(),
            wb_manager_hub=MagicMock(),
            stats_fresh=True,
        )

    # Durable COMPLETE + phase всё ещё WB_SYNC (activation не сдвинула phase).
    adv.adv_setting.card_ab_hold_sync_status = CardAbHoldSyncStatus.COMPLETE.value
    adv.adv_setting.card_ab_hold_phase = CardAbHoldPhase.WB_SYNC.value
    assert adv.card_ab_hold_mode == CardAbHoldMode.PENDING_SETUP.value

    with (
        patch(
            "app.modules.shop_runner.service_manager.services.auto_updater_v3."
            "card_ab_hold.epoch_pipelines.apply_confirmed_intent_to_pg",
            new_callable=AsyncMock,
        ) as mock_pg2,
        patch(
            "app.modules.shop_runner.service_manager.services.auto_updater_v3."
            "card_ab_hold.epoch_pipelines.sync_intent_to_wb",
            new_callable=AsyncMock,
        ) as mock_wb2,
        patch(
            "app.modules.shop_runner.service_manager.services.auto_updater_v3."
            "card_ab_hold.epoch_pipelines.activate_after_successful_sync",
            new_callable=AsyncMock,
            return_value=True,
        ) as mock_activate2,
    ):
        await process_ab_epoch(
            adv,
            wb_shop_data_manager=MagicMock(),
            wb_manager_hub=MagicMock(),
            stats_fresh=True,
        )

    mock_pg.assert_awaited_once()
    mock_wb.assert_awaited_once()
    mock_pg2.assert_not_called()
    mock_wb2.assert_not_called()
    mock_activate2.assert_awaited_once_with(99)
    assert adv.card_ab_hold_mode == CardAbHoldMode.ACTIVE.value


@pytest.mark.unit
@pytest.mark.asyncio
async def test_epoch_cap_exceeded_persists_degraded_before_active() -> None:
    """PBH-001: при cap_exceeded epoch sync MUST durable-persist degraded до/на ACTIVE.

    Invariant (decision §8 / tasks 8.12–8.13): allowed-set enforcement с
    ``cap_exceeded`` не может завершать COMPLETE→ACTIVE с чистым
    ``card_ab_hold_degraded=false``. Legacy ``process_ab_hold`` персистит флаг;
    epoch ``sync_intent_to_wb`` не должен ограничиваться WARN-only.
    """
    adv = _sync_adv(intent=_INTENT)
    adv.adv_setting.card_ab_hold_degraded = False

    enforce_result = {
        "targets": 1,
        "written": 1,
        "cap_exceeded": [(5000, 10)],
    }
    mock_minus_mgr = MagicMock()
    mock_minus_mgr.enforce_frozen_allowed_set = AsyncMock(
        return_value=enforce_result
    )
    mock_container = MagicMock()
    mock_container.minus_phrase_manager.return_value = mock_minus_mgr

    wb_hub = MagicMock()
    wb_hub.wb_modifier.update_auto_adv_cpm = AsyncMock()

    with (
        patch(
            "app.modules.shop_runner.service_manager.services.auto_updater_v3."
            "card_ab_hold.epoch_pipelines.apply_confirmed_intent_to_pg",
            new_callable=AsyncMock,
        ),
        patch(
            "app.modules.shop_runner.service_manager.services.auto_updater_v3."
            "card_ab_hold.epoch_pipelines.MinusPhraseManagerContainer",
            return_value=mock_container,
        ),
        patch(
            "app.modules.shop_runner.service_manager.services.auto_updater_v3."
            "card_ab_hold.epoch_pipelines.mark_wb_sync_status",
            new_callable=AsyncMock,
        ) as mock_mark,
        patch(
            "app.modules.shop_runner.service_manager.services.auto_updater_v3."
            "card_ab_hold.epoch_pipelines.activate_after_successful_sync",
            new_callable=AsyncMock,
            return_value=True,
        ) as mock_activate,
        patch(
            "app.modules.shop_runner.service_manager.services.auto_updater_v3."
            "card_ab_hold.setup_apply.persist_ab_hold_degraded_flag",
            new_callable=AsyncMock,
        ) as mock_persist,
    ):
        await process_ab_epoch(
            adv,
            wb_shop_data_manager=MagicMock(),
            wb_manager_hub=wb_hub,
            stats_fresh=True,
        )

    mock_mark.assert_awaited_once_with(99, CardAbHoldSyncStatus.COMPLETE)
    mock_activate.assert_awaited_once_with(99)
    assert adv.card_ab_hold_mode == CardAbHoldMode.ACTIVE.value
    # Durable honest degradation SoT (decision §8): not WARN-only.
    if mock_persist.await_count > 0:
        mock_persist.assert_any_await(adv_setting_id=99, degraded=True)
    assert bool(getattr(adv.adv_setting, "card_ab_hold_degraded", False)) or (
        mock_persist.await_count > 0
    ), (
        "cap_exceeded on epoch WB sync activated ACTIVE without durable "
        "card_ab_hold_degraded=true (persist_ab_hold_degraded_flag not called "
        "and in-memory flag remained false)"
    )
