"""Query-count / serialization regressions for PERF-001..003 AB-hold fixes."""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.modules.shop_runner.service_manager.services.auto_updater_v3.card_ab_hold.epoch_pipelines import (
    apply_confirmed_intent_to_pg_in_session,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.card_ab_hold.keyword_tp_bulk import (
    bulk_update_keyword_target_places,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.card_ab_hold.mode import (
    CardAbHoldMode,
    CardAbHoldPhase,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.card_ab_hold.pipelines import (
    process_ab_setup_then_epoch,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.card_ab_hold.setup_apply import (
    apply_ab_hold_setup_mutations_in_session,
)


def _kw_row(*, ks_id: int, text: str) -> SimpleNamespace:
    """Минимальный KeywordSetting-like row для intent apply."""
    return SimpleNamespace(id=ks_id, text=text)


class _ExecuteCounter:
    """Счётчик ``session.execute`` для query-count assertions."""

    def __init__(self) -> None:
        self.count = 0
        self.calls: list[Any] = []

    async def execute(self, stmt: Any, *args: Any, **kwargs: Any) -> MagicMock:
        self.count += 1
        self.calls.append(stmt)
        result = MagicMock()
        result.scalars.return_value.all.return_value = []
        return result


@pytest.mark.unit
@pytest.mark.asyncio
async def test_bulk_update_keyword_target_places_noop_on_empty() -> None:
    """Пустой updates — без execute."""
    session = AsyncMock()
    session.execute = AsyncMock()
    await bulk_update_keyword_target_places(session, [])
    session.execute.assert_not_awaited()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_bulk_update_keyword_target_places_single_execute() -> None:
    """N пар → ровно один execute (не N)."""
    session = AsyncMock()
    session.execute = AsyncMock()
    updates = [(i, 10 + i) for i in range(1, 8)]
    await bulk_update_keyword_target_places(session, updates)
    assert session.execute.await_count == 1


@pytest.mark.unit
@pytest.mark.asyncio
async def test_apply_confirmed_intent_execute_count_flat_vs_keyword_n() -> None:
    """PERF-001: execute count не растёт как base+N при росте target_places."""

    async def _run(n_keywords: int) -> int:
        rows = [_kw_row(ks_id=i, text=f"kw-{i}") for i in range(1, n_keywords + 1)]
        target_places = {f"kw-{i}": 5 + i for i in range(1, n_keywords + 1)}
        counter = _ExecuteCounter()

        async def _execute(stmt: Any, *args: Any, **kwargs: Any) -> MagicMock:
            counter.count += 1
            counter.calls.append(stmt)
            result = MagicMock()
            result.scalars.return_value.all.return_value = rows
            return result

        session = AsyncMock()
        session.execute = _execute
        session.commit = AsyncMock()
        await apply_confirmed_intent_to_pg_in_session(
            session,
            adv_setting_id=42,
            intent={"target_places": target_places, "keywords": list(target_places)},
        )
        return counter.count

    count_1 = await _run(1)
    count_5 = await _run(5)
    # select + bulk TP + adv update (+ commit is separate)
    assert count_1 == 3
    assert count_5 == 3
    assert count_5 == count_1


@pytest.mark.unit
@pytest.mark.asyncio
async def test_legacy_setup_tp_execute_count_flat_vs_pass_n() -> None:
    """PERF-002: legacy pass_updates — O(1) executes, не base+N."""

    async def _run(n_pass: int) -> int:
        counter = _ExecuteCounter()
        session = AsyncMock()
        session.execute = counter.execute
        session.commit = AsyncMock()
        pass_updates = [(i, 10 + i) for i in range(1, n_pass + 1)]
        await apply_ab_hold_setup_mutations_in_session(
            session,
            adv_setting_id=7,
            fail_ids=[],
            pass_updates=pass_updates,
            snapshot=["a"],
            degraded=False,
            epoch_managed=False,
        )
        return counter.count

    count_1 = await _run(1)
    count_6 = await _run(6)
    # bulk TP + AdvSetting mode update
    assert count_1 == 2
    assert count_6 == 2
    assert count_6 == count_1


@pytest.mark.unit
@pytest.mark.asyncio
async def test_process_ab_setup_then_epoch_serial_order() -> None:
    """PERF-003: setup awaited before epoch; same adv; no parallel fan-out."""
    order: list[str] = []
    adv = SimpleNamespace(
        adv_id=99,
        shop_id=1,
        card_ab_hold_mode=CardAbHoldMode.PENDING_SETUP.value,
        adv_setting=SimpleNamespace(
            id=1,
            card_ab_hold_phase=CardAbHoldPhase.WARM_UP.value,
        ),
    )

    async def _setup(*_a: Any, **_k: Any) -> None:
        order.append("setup")

    async def _epoch(*_a: Any, **_k: Any) -> None:
        order.append("epoch")

    with (
        patch(
            "app.modules.shop_runner.service_manager.services.auto_updater_v3."
            "card_ab_hold.pipelines.process_ab_setup",
            new=_setup,
        ),
        patch(
            "app.modules.shop_runner.service_manager.services.auto_updater_v3."
            "card_ab_hold.epoch_pipelines.process_ab_epoch",
            new=_epoch,
        ),
    ):
        await process_ab_setup_then_epoch(
            adv,
            wb_shop_data_manager=MagicMock(),
            wb_manager_hub=MagicMock(),
            stats_fresh=True,
        )

    assert order == ["setup", "epoch"]
