"""RED regression: clear our-block MUST reset notify latch for next enter.

Bug ROOT-001 / BUGCASE-ASEP-NOTIFY: ``clear_shelf_exhausted_pause`` keeps
``shelf_exhausted_notify_sent_at``. Activity-control STARTED path notifies only
when ``notify_sent_at is None`` → second enter after clear/calendar/button is
silent.

Invariant: after clear, ``notify_sent_at`` is None; clear → re-latch → STARTED
MUST call paid notify / ``mark_shelf_exhausted_notify_sent``.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.modules.shop_runner.service_manager.services.auto_adv_active_control import (
    AutoAdvActiveControlService,
)
from app.modules.shop_runner.service_manager.services.auto_shelf_bid_control_manager.auto_shelf_bid_control_repository import (
    AutoShelfBidControlRepository,
)
from app.shared.enums.wb_adv_active_status import WBAdvActiveStatus

_REPO_GSM = (
    "app.modules.shop_runner.service_manager.services.auto_shelf_bid_control_manager."
    "auto_shelf_bid_control_repository.get_session_maker"
)

_NMID = 9001
_NOW = datetime(2026, 8, 12, 12, 0, 0, tzinfo=UTC)
_DUE = _NOW + timedelta(days=7)
_FIRST_NOTIFY_AT = _NOW - timedelta(hours=2)


def _make_async_cm(session: AsyncMock) -> MagicMock:
    """Async context manager stub for ``get_session_maker``."""
    ctx = MagicMock()
    ctx.__aenter__ = AsyncMock(return_value=session)
    ctx.__aexit__ = AsyncMock(return_value=None)
    return ctx


def _active_notified_state() -> SimpleNamespace:
    """PG our-block active with first-enter notify already latched."""
    return SimpleNamespace(
        shelf_exhausted_pause_active=True,
        shelf_exhausted_paused_at=_NOW - timedelta(days=1),
        shelf_exhausted_due_at=_DUE,
        shelf_exhausted_notify_sent_at=_FIRST_NOTIFY_AT,
        shelf_exhausted_resolve_cpo_kind="max",
        shelf_exhausted_resolve_cpo_value=250.0,
        shelf_exhausted_epoch_pending=False,
        shelf_exhausted_epoch_start=None,
    )


@pytest.mark.asyncio
@patch(_REPO_GSM)
async def test_clear_shelf_exhausted_pause_resets_notify_sent_at(
    mock_get_session_maker: MagicMock,
) -> None:
    """Clear our-block MUST null ``shelf_exhausted_notify_sent_at`` (dedupe latch)."""
    state = _active_notified_state()
    execute_result = MagicMock()
    execute_result.scalar_one_or_none.return_value = state
    session = AsyncMock()
    session.execute = AsyncMock(return_value=execute_result)
    session.flush = AsyncMock()
    session.commit = AsyncMock()
    session.refresh = AsyncMock()
    mock_get_session_maker.return_value = _make_async_cm(session)

    repository = AutoShelfBidControlRepository()
    cleared = await repository.clear_shelf_exhausted_pause(_NMID)

    assert cleared is True
    assert state.shelf_exhausted_pause_active is False
    # Causal claim ROOT-001: notify latch must not survive clear.
    assert state.shelf_exhausted_notify_sent_at is None


@pytest.mark.asyncio
@patch(_REPO_GSM)
async def test_clear_relatch_started_path_notifies_again(
    mock_get_session_maker: MagicMock,
) -> None:
    """clear → re-latch → STARTED MUST call notify (second enter not silent)."""
    state = _active_notified_state()
    execute_result = MagicMock()
    execute_result.scalar_one_or_none.return_value = state
    session = AsyncMock()
    session.execute = AsyncMock(return_value=execute_result)
    session.flush = AsyncMock()
    session.commit = AsyncMock()
    session.refresh = AsyncMock()
    mock_get_session_maker.return_value = _make_async_cm(session)

    repository = AutoShelfBidControlRepository()
    assert await repository.clear_shelf_exhausted_pause(_NMID) is True
    await repository.latch_shelf_exhausted_pause(
        _NMID,
        now=_NOW,
        due_at=_DUE,
        resolve_cpo_kind="max",
        resolve_cpo_value=250.0,
    )
    assert state.shelf_exhausted_pause_active is True

    adv = SimpleNamespace(
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
    service = AutoAdvActiveControlService(
        wb_modifier=MagicMock(),
        tasks_manager=MagicMock(),
        plan_fact_reader=MagicMock(),
        redis_campaign_activity_reason_manager=MagicMock(),
        shelf_bid_control_repository=repository,
    )
    notify_spy = AsyncMock()
    service._notify_shelf_exhausted_enter = notify_spy  # type: ignore[method-assign]
    service._wb_modifier.pause_auto_campaign = AsyncMock()  # type: ignore[method-assign]
    service._set_auto_reason = AsyncMock()  # type: ignore[method-assign]

    blocked = await service._maybe_apply_shelf_exhausted_pause(
        adv,  # type: ignore[arg-type]
        auto_adv_id=501,
        auto_status=WBAdvActiveStatus.STARTED,
    )

    assert blocked is True
    service._wb_modifier.pause_auto_campaign.assert_awaited_once()
    # Second enter after clear MUST notify; sticky latch makes this fail today.
    notify_spy.assert_awaited_once()
