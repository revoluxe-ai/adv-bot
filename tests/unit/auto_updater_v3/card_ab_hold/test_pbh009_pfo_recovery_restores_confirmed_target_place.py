"""PBH-009 RED: PFO recovery_on MUST restore confirmed target_place.

Bug (hold_guards.py ~151):
- ``apply_ab_hold_overspend_offs`` sets ``KeywordSetting.target_place=None``.
- ``apply_ab_hold_pfo_recovery_ons`` / ``*_in_session`` restores MIN_CPA
  ``hard_status`` / ``strategy_mode`` only — does NOT restore confirmed
  ``target_place`` from epoch confirmed JSON SoT.
- Bidder then ``snap_to_min`` when TP is None.

This module encodes the desired restore contract so pytest FAILS on
current production (RED_CONFIRMED). No production fix here.
Do not reopen CLOSED PBH-004 / EPOCHCAPDEG / SA-ZLPR.
"""

from __future__ import annotations

import inspect
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.modules.common_slaves.wildberries.models.enums import KeywordStrategyMode
from app.modules.shop_runner.service_manager.services.auto_updater_v3.card_ab_hold.hold_guards import (
    apply_ab_hold_overspend_offs,
    apply_ab_hold_pfo_recovery_ons_in_session,
)

_HOLD_GUARDS = (
    "app.modules.shop_runner.service_manager.services.auto_updater_v3."
    "card_ab_hold.hold_guards"
)

_CONFIRMED_KS_ID = 101
_CONFIRMED_TARGET_PLACE = 7
_CONFIRMED_TP_PARAM_CANDIDATES = (
    "confirmed_target_places",
    "target_places_by_id",
    "confirmed_target_places_by_id",
)


def _stmt_values(stmt: Any) -> dict[str, Any]:
    """Normalize SQLAlchemy Update ``_values`` keys to plain names."""
    raw = getattr(stmt, "_values", None) or {}
    out: dict[str, Any] = {}
    for key, value in raw.items():
        key_name = str(getattr(key, "key", None) or getattr(key, "name", None) or key)
        out[key_name] = getattr(value, "value", value)
    return out


def _stmt_target_place(stmt: Any) -> Any:
    """Return ``target_place`` from Update values, or ``_MISSING`` sentinel."""
    values = _stmt_values(stmt)
    if "target_place" not in values:
        return _MISSING
    return values["target_place"]


class _Missing:
    """Sentinel: Update did not write ``target_place`` at all."""

    def __repr__(self) -> str:
        return "<MISSING target_place write>"


_MISSING = _Missing()


def _recovery_confirmed_tp_param_name() -> str | None:
    """Name of confirmed-TP SoT map parameter on recovery_on seam, if any."""
    params = inspect.signature(apply_ab_hold_pfo_recovery_ons_in_session).parameters
    for name in _CONFIRMED_TP_PARAM_CANDIDATES:
        if name in params:
            return name
    return None


@pytest.mark.unit
@pytest.mark.asyncio
async def test_pbh009_overspend_offs_clears_target_place() -> None:
    """Precondition: ACTIVE PFO-off / overspend OFF writes ``target_place=None``."""
    mock_session = AsyncMock()
    mock_session.execute = AsyncMock()
    mock_session.commit = AsyncMock()
    mock_cm = MagicMock()
    mock_cm.__aenter__ = AsyncMock(return_value=mock_session)
    mock_cm.__aexit__ = AsyncMock(return_value=None)

    with patch(f"{_HOLD_GUARDS}.sm", return_value=mock_cm):
        updated = await apply_ab_hold_overspend_offs(
            adv_id=10,
            keyword_ids=[_CONFIRMED_KS_ID],
        )

    assert updated == 1
    assert mock_session.execute.await_count == 1
    stmt = mock_session.execute.await_args.args[0]
    assert _stmt_target_place(stmt) is None


@pytest.mark.unit
@pytest.mark.asyncio
async def test_pbh009_pfo_recovery_restores_confirmed_target_place() -> None:
    """PFO recovery_on MUST restore confirmed ``target_place`` from epoch SoT.

    After overspend OFF cleared TP to None, ``*_in_session`` must accept the
    confirmed id→TP map and write ``target_place`` back to the confirmed value
    (not leave it absent/None while only restoring MIN_CPA).
    """
    param_name = _recovery_confirmed_tp_param_name()
    assert param_name is not None, (
        "PBH-009: apply_ab_hold_pfo_recovery_ons_in_session MUST accept a "
        "confirmed target_place SoT map parameter "
        f"(one of {_CONFIRMED_TP_PARAM_CANDIDATES}); "
        "overspend OFF clears TP and recovery currently restores MIN_CPA only"
    )

    mock_session = AsyncMock()
    mock_session.execute = AsyncMock()
    mock_session.commit = AsyncMock()

    call_kwargs: dict[str, Any] = {
        "keyword_ids": [_CONFIRMED_KS_ID],
        param_name: {_CONFIRMED_KS_ID: _CONFIRMED_TARGET_PLACE},
    }
    updated = await apply_ab_hold_pfo_recovery_ons_in_session(
        mock_session,
        **call_kwargs,
    )

    assert updated == 1
    assert mock_session.execute.await_count >= 1
    # Prefer the Update that restores operable strategy (return_on / recovery_on).
    restored_tp: Any = _MISSING
    saw_min_cpa = False
    for call in mock_session.execute.await_args_list:
        if not call.args:
            continue
        stmt = call.args[0]
        values = _stmt_values(stmt)
        mode = values.get("strategy_mode")
        if mode is not None and mode is not KeywordStrategyMode.OFF:
            try:
                if int(mode) == int(KeywordStrategyMode.MIN_CPA):
                    saw_min_cpa = True
            except (TypeError, ValueError):
                if mode is KeywordStrategyMode.MIN_CPA:
                    saw_min_cpa = True
        tp = _stmt_target_place(stmt)
        if tp is not _MISSING:
            restored_tp = tp

    assert saw_min_cpa or restored_tp is not _MISSING, (
        "PBH-009: recovery_on must persist return-ON / MIN_CPA and/or TP restore"
    )
    assert restored_tp == _CONFIRMED_TARGET_PLACE, (
        "PBH-009: apply_ab_hold_pfo_recovery_ons_in_session MUST restore "
        f"KeywordSetting.target_place={_CONFIRMED_TARGET_PLACE} from confirmed "
        f"epoch JSON SoT after overspend OFF cleared it; got {restored_tp!r}. "
        "Leaving TP None causes bidder snap_to_min."
    )
