"""Unit: audit/tick report классификация pfo_off (debug session b5c941)."""

from __future__ import annotations

import pytest

from app.modules.common_slaves.wildberries.models.enums import KeywordStrategyMode
from app.modules.shop_runner.service_manager.services.auto_updater_v3.update_pipeline.executors.pay_for_order_over_max_off_on_deep_overspend import (
    PayForOrderOverMaxOffOnDeepOverspendExecutor,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.v3_keyword_changes_report.builder import (
    build_keyword_changes_snapshot,
)
from tests.unit.auto_updater_v3.test_pay_for_order_over_max_off_on_deep_overspend_executor import (
    _adv_state,
    _context,
    _dto,
)

_EXECUTOR = "PayForOrderOverMaxOffOnDeepOverspendExecutor"


@pytest.mark.unit
def test_pfo_off_audit_counts_force_off_not_down_for_max_to_off() -> None:
    """MAX + PFO>max → OFF: в audit ``force_off``, не ``down``."""
    max_cpo = 550.0
    dto = _dto(ks_id=1, mode=KeywordStrategyMode.MAX_CONVERSION, pfo_target=750.0)
    ctx = _context([dto], _adv_state(fact=705.0, max_cpo=max_cpo))
    PayForOrderOverMaxOffOnDeepOverspendExecutor().execute(ctx)
    assert dto.current_mode == KeywordStrategyMode.OFF

    audit = build_keyword_changes_snapshot(ctx.keywords, adv_id=1)
    pfo_rows = [x for x in audit.by_phase if x.executor_name == _EXECUTOR]
    assert len(pfo_rows) == 1
    row = pfo_rows[0]
    assert row.force_off == 1
    assert row.down == 0
    assert row.ended_off == 1


@pytest.mark.unit
def test_pfo_off_mass_off_matches_prod_shape() -> None:
    """95 ключей MAX→OFF: net_force_off=95, без net_down."""
    max_cpo = 550.0
    keywords = [
        _dto(ks_id=i, mode=KeywordStrategyMode.MAX_CONVERSION, pfo_target=750.0)
        for i in range(1, 96)
    ]
    ctx = _context(keywords, _adv_state(fact=705.0, max_cpo=max_cpo))
    PayForOrderOverMaxOffOnDeepOverspendExecutor().execute(ctx)
    audit = build_keyword_changes_snapshot(ctx.keywords, adv_id=10749810)
    pfo_rows = [x for x in audit.by_phase if x.executor_name == _EXECUTOR]
    assert len(pfo_rows) == 1
    row = pfo_rows[0]
    assert row.planned == 95
    assert row.force_off == 95
    assert row.down == 0
    assert row.ended_off == 95
    assert audit.net_force_off == 95
    assert audit.net_down == 0
