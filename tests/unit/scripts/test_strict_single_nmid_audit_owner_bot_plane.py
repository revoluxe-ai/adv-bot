"""Регрессии Job-runtime plane: один event loop, без asyncio.run на каждый reader."""

from __future__ import annotations

from datetime import date
from unittest.mock import AsyncMock, patch

import pytest

from scripts.strict_single_nmid_audit import AuditIdentity, AuditPeriod
from scripts.strict_single_nmid_audit_owner_bot_plane import (
    OwnerBotStrictSingleNmidReadOnlyPlane,
    _Bundle,
)


IDENTITY = AuditIdentity(
    shop_id="5339e9ad-cbfe-50fc-8d77-b9f337a80417",
    cabinet=401,
    nmid=7974113,
    size_id=1895360146,
    timezone="Europe/Moscow",
)

PERIOD = AuditPeriod(
    start=date(2026, 9, 7),
    end=date(2026, 9, 20),
    timezone="Europe/Moscow",
)


@pytest.mark.unit
def test_plane_reuses_single_loop_across_readers() -> None:
    """Несколько sync readers делают один async load (cache), без asyncio.run."""
    bundle = _Bundle(pg_rows=[], campaigns=[], fullstats=[], orders=[])
    plane = OwnerBotStrictSingleNmidReadOnlyPlane()
    with patch.object(plane, "_run_coroutine", return_value=bundle) as run_coro:
        with patch("asyncio.run") as mocked_run:
            list(plane.read_current_contour(IDENTITY, PERIOD))
            list(plane.read_orders(IDENTITY, PERIOD))
            list(plane.read_attribution(IDENTITY, PERIOD))
            mocked_run.assert_not_called()
    run_coro.assert_called_once()
    plane.close()


@pytest.mark.unit
def test_ensure_bundle_prefetches_before_readers() -> None:
    """ensure_bundle загружает данные один раз до section readers."""
    plane = OwnerBotStrictSingleNmidReadOnlyPlane()
    bundle = _Bundle(
        pg_rows=[
            {
                "nmids": "[7974113]",
                "adv_id": 17728892,
                "_search_adv_id": 21027713,
                "active_status": "on",
                "bot_active": True,
                "target_price_for_order": 100,
                "max_price_for_order": 574,
                "auto_budget_daily_limit": 200,
                "search_auto_budget_daily_limit": 150,
            }
        ],
        campaigns=[],
        fullstats=[],
        orders=[],
    )

    async def _fake_load_all() -> _Bundle:
        return bundle

    with patch.object(
        plane,
        "_run_coroutine",
        side_effect=lambda coro: plane._loop.run_until_complete(_fake_load_all()),
    ):
        plane.ensure_bundle(IDENTITY, PERIOD)
        contour = list(plane.read_current_contour(IDENTITY, PERIOD))
    assert all(hasattr(item, "field") for item in contour)
    plane.close()
    assert contour
    assert any(item.field == "limits" for item in contour)


@pytest.mark.unit
def test_close_disposes_engines_on_job_loop() -> None:
    """close() вызывает dispose async engines на том же loop."""
    plane = OwnerBotStrictSingleNmidReadOnlyPlane()
    dispose = AsyncMock()

    with patch(
        "app.utils.db.session_maker.read_only_engine",
        dispose=dispose,
    ):
        with patch(
            "app.utils.db.session_maker.read_write_engine",
            dispose=dispose,
        ):
            plane.close()
    assert plane._loop.is_closed()
