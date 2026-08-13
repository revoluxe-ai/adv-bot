"""RED regression: shelf-exhausted enter MUST notify when Auto already not STARTED.

Bug ROOT-001 / BUGCASE-ASEP-ENTER-NOTIFY: ``_maybe_apply_shelf_exhausted_pause``
notifies paid Telegram only on ``auto_status==STARTED``. When Auto is already
PAUSE / READY (budget/schedule/balance paused first), it re-asserts Redis reason
and returns without notify — first shelf-exhausted enter is silent despite PG
``shelf_exhausted_pause_active`` and ``notify_sent_at is None``.

Fingerprint: ``shelf_exhausted_enter_notify_only_on_started_transition``.
Distinct from sticky ``notify_sent_at`` after clear (BUGCASE-ASEP-NOTIFY).
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.modules.shop_runner.service_manager.services.auto_adv_active_control import (
    AutoAdvActiveControlService,
)
from app.shared.enums.wb_adv_active_status import WBAdvActiveStatus

_NMID = 9001
_NOW = datetime(2026, 8, 13, 3, 0, 0, tzinfo=UTC)
_DUE = _NOW + timedelta(days=7)


def _pg_our_block_awaiting_first_notify() -> SimpleNamespace:
    """Active PG our-block with notify latch unset (first enter)."""
    return SimpleNamespace(
        shelf_exhausted_pause_active=True,
        shelf_exhausted_notify_sent_at=None,
        shelf_exhausted_resolve_cpo_kind="max",
        shelf_exhausted_resolve_cpo_value=250.0,
        shelf_exhausted_due_at=_DUE,
        shelf_exhausted_epoch_pending=False,
    )


def _adv() -> SimpleNamespace:
    return SimpleNamespace(
        bot_active=True,
        auto_budget_watchdog_enabled=True,
        auto_adv_id=501,
        shop_id="shop-x",
        shop_name="Shop",
        main_nmid=_NMID,
        nmids=[_NMID],
        adv_setting=SimpleNamespace(
            id=77,
            name="Camp",
            auto_shelf_bid_control_enabled=True,
        ),
    )


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "auto_status",
    [
        WBAdvActiveStatus.PAUSE,
        WBAdvActiveStatus.READY_FOR_START,
    ],
)
async def test_shelf_exhausted_enter_notifies_when_auto_already_not_started(
    auto_status: str,
) -> None:
    """PG our-block enter + notify_sent_at None MUST notify even if Auto not STARTED.

    Protects: first shelf-exhausted enter after budget/schedule/balance pause
    must still deliver paid Telegram notify (dedup latch still applies).
    """
    state = _pg_our_block_awaiting_first_notify()
    repo = MagicMock()
    repo.get_state = AsyncMock(return_value=state)
    reason_manager = MagicMock()
    reason_manager.set = AsyncMock()

    service = AutoAdvActiveControlService(
        wb_modifier=MagicMock(),
        tasks_manager=MagicMock(),
        plan_fact_reader=MagicMock(),
        redis_campaign_activity_reason_manager=reason_manager,
        shelf_bid_control_repository=repo,
    )
    notify_spy = AsyncMock()
    service._notify_shelf_exhausted_enter = notify_spy  # type: ignore[method-assign]
    service._wb_modifier.pause_auto_campaign = AsyncMock()  # type: ignore[method-assign]
    service._set_auto_reason = AsyncMock()  # type: ignore[method-assign]

    blocked = await service._maybe_apply_shelf_exhausted_pause(
        _adv(),  # type: ignore[arg-type]
        auto_adv_id=501,
        auto_status=auto_status,
    )

    assert blocked is True
    # Already not STARTED: must not re-pause WB; Redis re-assert still ok.
    service._wb_modifier.pause_auto_campaign.assert_not_awaited()
    service._set_auto_reason.assert_awaited_once()
    # Causal claim ROOT-001: paid notify MUST fire on enter when latch unset.
    notify_spy.assert_awaited_once()
