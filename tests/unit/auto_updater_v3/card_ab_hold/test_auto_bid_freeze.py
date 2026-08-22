"""Unit-тесты A/B Hold Auto bid freeze (spec §21 / decision epoch parameters)."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.client_bot.user_interface.handlers.change_auto_bid import (
    open_change_auto_bid,
    set_auto_bid,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.card_ab_hold.auto_bid_freeze import (
    AB_HOLD_MANUAL_AUTO_BID_BLOCKED_MSG,
    is_ab_hold_auto_bid_manual_blocked,
    should_freeze_auto_bid_mutations,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.card_ab_hold.mode import (
    CardAbHoldMode,
)

_HANDLER = "app.client_bot.user_interface.handlers.change_auto_bid"


@pytest.mark.unit
@pytest.mark.parametrize(
    ("mode", "expected"),
    [
        (CardAbHoldMode.OFF, False),
        ("off", False),
        # One-arg PENDING_SETUP: conservative freeze (callers must pass phase
        # to keep pre-confirm AutoReset eligible — FINDING-PBH-003).
        (CardAbHoldMode.PENDING_SETUP, True),
        ("pending_setup", True),
        (CardAbHoldMode.ACTIVE, True),
        ("active", True),
        (None, False),
    ],
)
def test_should_freeze_auto_bid_mutations_mode_only(
    mode: CardAbHoldMode | str | None,
    expected: bool,
) -> None:
    """One-arg freeze: ACTIVE and PENDING_SETUP (phase omitted); not OFF."""
    assert should_freeze_auto_bid_mutations(mode) is expected


@pytest.mark.unit
@pytest.mark.parametrize(
    ("mode", "phase", "expected"),
    [
        (CardAbHoldMode.PENDING_SETUP, "awaiting_auto_bid_confirm", False),
        (CardAbHoldMode.PENDING_SETUP, "awaiting_keyword_confirm", False),
        (CardAbHoldMode.PENDING_SETUP, "warm_up", False),
        (CardAbHoldMode.PENDING_SETUP, None, False),
        (CardAbHoldMode.PENDING_SETUP, "pending_intent", True),
        (CardAbHoldMode.PENDING_SETUP, "wb_sync", True),
        (CardAbHoldMode.PENDING_SETUP, "ready_active", True),
        (CardAbHoldMode.ACTIVE, "ready_active", True),
        (CardAbHoldMode.OFF, "pending_intent", False),
    ],
)
def test_should_freeze_auto_bid_mutations_phase_aware(
    mode: CardAbHoldMode,
    phase: str | None,
    expected: bool,
) -> None:
    """Phase-aware freeze: post-confirm PENDING_SETUP only; pre-confirm allowed."""
    assert should_freeze_auto_bid_mutations(mode, phase) is expected


@pytest.mark.unit
@pytest.mark.parametrize(
    ("mode", "expected"),
    [
        (CardAbHoldMode.OFF, False),
        (CardAbHoldMode.PENDING_SETUP, True),
        (CardAbHoldMode.ACTIVE, True),
    ],
)
def test_is_ab_hold_auto_bid_manual_blocked_structural_freeze(
    mode: CardAbHoldMode,
    expected: bool,
) -> None:
    """Ручной change_auto_bid blocked в PENDING_SETUP и ACTIVE."""
    assert is_ab_hold_auto_bid_manual_blocked(mode) is expected


def _adv_setting(*, mode: str, adv_id: int = 501) -> SimpleNamespace:
    return SimpleNamespace(
        id=1,
        adv_id=adv_id,
        nmids=[10],
        cpm=900,
        card_ab_hold_mode=mode,
        wb_cabinet=SimpleNamespace(shop_id="shop-1"),
    )


def _session_with_adv(adv: SimpleNamespace) -> AsyncMock:
    session = AsyncMock()
    session.execute = AsyncMock(
        return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=adv))
    )
    return session


@pytest.mark.unit
@pytest.mark.asyncio
@pytest.mark.parametrize("mode", ["pending_setup", "active"])
async def test_open_change_auto_bid_blocked_on_ab_hold(mode: str) -> None:
    """open_change_auto_bid → explain и без FSM/min_bids при freeze."""
    adv = _adv_setting(mode=mode)
    session = _session_with_adv(adv)
    mock_sm = MagicMock()
    mock_sm.return_value.__aenter__ = AsyncMock(return_value=session)
    mock_sm.return_value.__aexit__ = AsyncMock(return_value=None)

    callback = SimpleNamespace(
        message=SimpleNamespace(chat=SimpleNamespace(id=42)),
        from_user=SimpleNamespace(id=7),
        bot=AsyncMock(),
    )
    callback_data = SimpleNamespace(adv_original_id=1, action="open")
    state = AsyncMock()

    with patch(f"{_HANDLER}.sm", mock_sm):
        await open_change_auto_bid(callback, callback_data, state)

    callback.bot.send_message.assert_awaited_once_with(
        42, AB_HOLD_MANUAL_AUTO_BID_BLOCKED_MSG
    )
    state.set_state.assert_not_called()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_set_auto_bid_blocked_on_ab_hold_active() -> None:
    """set_auto_bid → без WB write при ACTIVE hold."""
    adv = _adv_setting(mode="active")
    session = _session_with_adv(adv)
    mock_sm = MagicMock()
    mock_sm.return_value.__aenter__ = AsyncMock(return_value=session)
    mock_sm.return_value.__aexit__ = AsyncMock(return_value=None)

    message = SimpleNamespace(
        chat=SimpleNamespace(id=42),
        text="500",
        from_user=SimpleNamespace(id=7),
        bot=AsyncMock(),
    )
    state = AsyncMock()
    state.get_data = AsyncMock(
        return_value={
            "effective_min": 150,
            "adv_original_id": 1,
            "auto_adv_id": 501,
            "nmids": [10],
        }
    )

    with patch(f"{_HANDLER}.sm", mock_sm), patch(
        f"{_HANDLER}.DIManager.create", AsyncMock()
    ):
        await set_auto_bid(message, state)

    message.bot.send_message.assert_awaited_once_with(
        42, AB_HOLD_MANUAL_AUTO_BID_BLOCKED_MSG
    )
    state.clear.assert_awaited_once()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_set_auto_bid_calls_wb_write_on_off_mode() -> None:
    """set_auto_bid в OFF режиме доходит до WB write boundary."""
    adv = _adv_setting(mode="off")
    lookup_session = _session_with_adv(adv)

    commit_adv = SimpleNamespace(cpm=900)
    commit_session = AsyncMock()
    commit_session.get = AsyncMock(return_value=commit_adv)
    commit_session.commit = AsyncMock()

    menu_session = AsyncMock()
    menu_session.execute = AsyncMock(
        return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=None))
    )

    def _ctx(session: AsyncMock) -> MagicMock:
        ctx = MagicMock()
        ctx.__aenter__ = AsyncMock(return_value=session)
        ctx.__aexit__ = AsyncMock(return_value=None)
        return ctx

    mock_sm = MagicMock(side_effect=[_ctx(lookup_session), _ctx(commit_session), _ctx(menu_session)])

    update_auto_adv_cpm = AsyncMock()
    hub = SimpleNamespace(wb_modifier=SimpleNamespace(update_auto_adv_cpm=update_auto_adv_cpm))
    factory = MagicMock()
    factory.get_wb_manager_hub.return_value = hub
    factory_container = SimpleNamespace(wb_manager_hub_factory=MagicMock(return_value=factory))
    container = SimpleNamespace(
        module_resources=SimpleNamespace(
            wb_manager_hub_factory_container=factory_container
        )
    )
    container_ctx = MagicMock()
    container_ctx.__aenter__ = AsyncMock(return_value=container)
    container_ctx.__aexit__ = AsyncMock(return_value=None)

    message = SimpleNamespace(
        chat=SimpleNamespace(id=42),
        text="500",
        from_user=SimpleNamespace(id=7),
        bot=AsyncMock(),
    )
    state = AsyncMock()
    state.get_data = AsyncMock(
        return_value={
            "effective_min": 150,
            "adv_original_id": 1,
            "auto_adv_id": 501,
            "nmids": [10, 11],
        }
    )

    with patch(f"{_HANDLER}.sm", mock_sm), patch(
        f"{_HANDLER}.DIManager.create", AsyncMock(return_value=container_ctx)
    ):
        await set_auto_bid(message, state)

    update_auto_adv_cpm.assert_awaited_once_with(501, {10: 500, 11: 500})
    commit_session.get.assert_awaited_once()
    commit_session.commit.assert_awaited_once()
    state.clear.assert_awaited_once()
    message.bot.send_message.assert_awaited_once_with(
        42, "Ставка в автокампании обновлена: 500 руб."
    )
