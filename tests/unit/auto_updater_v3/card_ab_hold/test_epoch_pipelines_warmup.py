"""Unit-тесты epoch tick: WARM_UP elapsed → AWAITING_TP_CONFIRM (§19)."""

from __future__ import annotations

import datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.modules.shop_runner.service_manager.services.auto_updater_v3.card_ab_hold.epoch_pipelines import (
    process_ab_epoch,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.card_ab_hold.mode import (
    CardAbHoldMode,
    CardAbHoldPhase,
)


@pytest.fixture(autouse=True)
def _stub_enter_common_bid_reset() -> None:
    """Изолировать warmup-тесты от §19 ENTER common-bid Redis/WB path.

    ``process_ab_epoch`` always calls ``ensure_search_common_bid_reset_on_enter``;
    without a stub, AdvSettingRedisCache hits DI Redis ``Provide`` before WARM_UP body.
    """
    with patch(
        "app.modules.shop_runner.service_manager.services.auto_updater_v3."
        "card_ab_hold.epoch_pipelines.ensure_search_common_bid_reset_on_enter",
        new_callable=AsyncMock,
    ):
        yield


def _epoch_adv(*, phase: str, started_hours_ago: int = 25) -> SimpleNamespace:
    started = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(
        hours=started_hours_ago
    )
    adv_setting = SimpleNamespace(
        id=42,
        adv_id=9001,  # AdvSettingRedisCache key (ENTER common-bid reset)
        card_ab_hold_phase=phase,
        card_ab_hold_warmup_started_at=started,
        card_ab_hold_warmup_duration_hours=24,
        card_ab_hold_sync_status="none",
        card_ab_hold_pending_intent_json=None,
    )
    return SimpleNamespace(
        adv_id=9001,
        shop_id=1,
        card_ab_hold_mode=CardAbHoldMode.PENDING_SETUP.value,
        adv_setting=adv_setting,
        nmids=[111],
    )


@pytest.mark.unit
@pytest.mark.asyncio
async def test_warmup_elapsed_transitions_to_awaiting_tp_confirm() -> None:
    """Elapsed WARM_UP → advance_warmup_to_tp_confirm, без WB sync."""
    adv = _epoch_adv(phase=CardAbHoldPhase.WARM_UP.value)
    with patch(
        "app.modules.shop_runner.service_manager.services.auto_updater_v3."
        "card_ab_hold.epoch_pipelines.advance_warmup_to_tp_confirm",
        new_callable=AsyncMock,
        return_value=True,
    ) as mock_advance:
        await process_ab_epoch(
            adv,
            wb_shop_data_manager=MagicMock(),
            wb_manager_hub=MagicMock(),
            stats_fresh=True,
        )
    mock_advance.assert_awaited_once_with(42)
    assert adv.adv_setting.card_ab_hold_phase == (
        CardAbHoldPhase.AWAITING_TP_CONFIRM.value
    )


@pytest.mark.unit
@pytest.mark.asyncio
async def test_warmup_not_elapsed_no_transition() -> None:
    """WARM_UP ещё не истёк — phase не меняется."""
    adv = _epoch_adv(phase=CardAbHoldPhase.WARM_UP.value, started_hours_ago=2)
    with patch(
        "app.modules.shop_runner.service_manager.services.auto_updater_v3."
        "card_ab_hold.epoch_pipelines.advance_warmup_to_tp_confirm",
        new_callable=AsyncMock,
    ) as mock_advance:
        await process_ab_epoch(
            adv,
            wb_shop_data_manager=MagicMock(),
            wb_manager_hub=MagicMock(),
        )
    mock_advance.assert_not_called()
    assert adv.adv_setting.card_ab_hold_phase == CardAbHoldPhase.WARM_UP.value


@pytest.mark.unit
@pytest.mark.asyncio
async def test_legacy_null_phase_skips_epoch_tick() -> None:
    """phase NULL → process_ab_epoch no-op (legacy MVP-1 path)."""
    adv_setting = SimpleNamespace(
        id=1,
        card_ab_hold_phase=None,
    )
    adv = SimpleNamespace(
        adv_id=100,
        card_ab_hold_mode=CardAbHoldMode.PENDING_SETUP.value,
        adv_setting=adv_setting,
    )
    with patch(
        "app.modules.shop_runner.service_manager.services.auto_updater_v3."
        "card_ab_hold.epoch_pipelines.advance_warmup_to_tp_confirm",
        new_callable=AsyncMock,
    ) as mock_advance:
        await process_ab_epoch(
            adv,
            wb_shop_data_manager=MagicMock(),
            wb_manager_hub=MagicMock(),
        )
    mock_advance.assert_not_called()
