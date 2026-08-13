"""RED regression: resolve_cpo_kind must not default to target when live threshold is Max.

Bug ROOT-001 / BUGCASE-ASEP-RESOLVE-CPO-KIND / PBH-GH-002:
``_resolve_cpo_from_adv`` looks for ``plan`` / ``fact_predict_orders`` /
``resolve_cpo_kind`` on ComplexAdv, which production objects do not expose.
They only carry ``resolve_cpo``. The fallback then records kind as ``target``
whenever kind is missing — including when the live threshold is Max.

Invariant: when ComplexAdv only exposes ``resolve_cpo`` and the live threshold
(from the same plan/fact inputs that produced that value) is Max, recorded
``resolve_cpo_kind`` MUST be ``max`` (latch / notify / PG SoT).
"""

from __future__ import annotations

# pyright: reportPrivateUsage=false

from types import SimpleNamespace
from typing import Any
from unittest.mock import AsyncMock

import pytest

from app.modules.shop_runner.service_manager.services.auto_shelf_bid_control_manager.exhausted_pause.apply_tick import (
    _resolve_cpo_from_adv,
)
from app.shared.domains.wb.utils.cost_resolver import (
    resolve_target_cost_and_threshold_kind,
)
from tests.unit.auto_shelf_exhausted_pause.asep_manager_tick_fixtures import (
    build_tick_fixture,
)

# Live Max case: fact_predict < plan_orders → max_pay is the resolve threshold.
_PLAN_ORDERS = 10
_PLAN_TARGET = 200.0
_PLAN_MAX = 350.0
_FACT_PREDICT_BELOW_PLAN = 3.0


def _max_threshold_oracle() -> tuple[float, str]:
    """Ground-truth (value, kind) from the shared cost resolver — not ComplexAdv."""
    pair = resolve_target_cost_and_threshold_kind(
        _PLAN_ORDERS,
        _PLAN_TARGET,
        _PLAN_MAX,
        _FACT_PREDICT_BELOW_PLAN,
    )
    assert pair is not None
    assert pair == (_PLAN_MAX, "max")
    return pair


def _complex_adv_resolve_cpo_only(resolve_cpo: float) -> Any:
    """Production ComplexAdv shape: resolved scalar only; no plan/kind attrs.

    Mirrors ``wb_shop_data_manager.get_complex_advs`` which sets ``resolve_cpo``
    and does not attach ``plan``, ``fact_predict_orders``, or ``resolve_cpo_kind``.
    """
    return SimpleNamespace(
        resolve_cpo=resolve_cpo,
        # Explicit absences — getattr(..., None) must hit the fallback path.
        plan=None,
        fact_predict_orders=None,
        resolved_fact_predict_orders=None,
        resolved_target_pay_for_order=None,
        # Deliberately omit resolve_cpo_kind (ComplexAdv has no such property).
    )


@pytest.mark.unit
def test_resolve_cpo_from_adv_kind_is_max_when_only_resolve_cpo_and_live_is_max() -> None:
    """Causal boundary: Max live threshold must not be mislabeled as target.

    RED on unrepaired code: fallback forces ``kind="target"`` when
    ``resolve_cpo_kind`` is missing on ComplexAdv.
    """
    value, expected_kind = _max_threshold_oracle()
    complex_adv = _complex_adv_resolve_cpo_only(value)

    assert not hasattr(complex_adv, "resolve_cpo_kind")
    assert getattr(complex_adv, "plan", None) is None
    assert getattr(complex_adv, "fact_predict_orders", None) is None

    result = _resolve_cpo_from_adv(complex_adv)

    assert result is not None
    got_value, got_kind = result
    assert float(got_value) == float(value)
    # Fail before fix: got_kind == "target" despite oracle Max.
    assert got_kind == expected_kind


@pytest.mark.unit
@pytest.mark.asyncio
async def test_apply_tick_latches_resolve_cpo_kind_max_when_complex_adv_omits_kind() -> None:
    """Manager tick latch must persist Max kind when ComplexAdv has only resolve_cpo."""
    value, expected_kind = _max_threshold_oracle()
    manager, repository, state, settings_obj, _unused_adv, snapshot = (
        build_tick_fixture(
            block_active=False,
            next_test_bid_minor=None,  # terminal empty epoch → latch
            plan_ranked=[{"bid": 15_000, "cpo_rub": 999.0}],  # no plan-fit
        )
    )
    complex_adv = _complex_adv_resolve_cpo_only(value)
    # Required tick fields from production ComplexAdv (fixture base).
    complex_adv.main_nmid = 30_369_094
    complex_adv.auto_adv_id = 35_018_182
    complex_adv.auto_shelf_bid_control_enabled = True
    complex_adv.auto_shelf_bid_control_strategy = (
        _unused_adv.auto_shelf_bid_control_strategy
    )
    repository.latch_shelf_exhausted_pause = AsyncMock()

    await manager._apply_shelf_exhausted_tick(
        complex_adv=complex_adv,  # type: ignore[arg-type]
        settings_obj=settings_obj,  # type: ignore[arg-type]
        state=state,  # type: ignore[arg-type]
        snapshot=snapshot,
    )

    repository.latch_shelf_exhausted_pause.assert_awaited_once()
    latch_kwargs = repository.latch_shelf_exhausted_pause.await_args.kwargs
    assert float(latch_kwargs["resolve_cpo_value"]) == float(value)
    # Fail before fix: resolve_cpo_kind == "target" despite live Max.
    assert latch_kwargs["resolve_cpo_kind"] == expected_kind
