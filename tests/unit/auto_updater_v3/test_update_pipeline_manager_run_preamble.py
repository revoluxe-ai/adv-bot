"""Unit: ``UpdatePipelineManager.run_preamble`` — счётчики фаз на ``PreamblePipelineRunResult``."""

from __future__ import annotations

from dataclasses import fields, replace
from unittest.mock import MagicMock, patch

import pytest

from app.modules.common_slaves.wildberries.models.enums import KeywordStrategyMode
from app.modules.shop_runner.service_manager.services.auto_updater_v3.keyword_dto.dto.update_context import (
    UpdateContext,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.keyword_dto.dto.update_context_runtime import (
    UpdateContextRuntime,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.update_pipeline.executors.pay_for_order_over_max_off_on_deep_overspend import (
    PayForOrderOverMaxOffOnDeepOverspendExecutor,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.update_pipeline.manager import (
    UpdatePipelineManager,
    _PHASE_LOG,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.update_pipeline.runner import (
    PreamblePipelineRunResult,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.v3_tick_report import (
    V3TickReportCollector,
)
from tests.unit.auto_updater_v3.test_pay_for_order_over_max_off_on_deep_overspend_executor import (
    _adv_state,
    _context,
    _dto,
)

_MANAGER_MODULE = (
    "app.modules.shop_runner.service_manager.services.auto_updater_v3"
    ".update_pipeline.manager"
)


def _with_runtime(ctx: UpdateContext) -> UpdateContext:
    """Минимальный ``UpdateContext.runtime`` для ``run_preamble``."""
    return replace(
        ctx,
        runtime=UpdateContextRuntime(
            adv_id=99,
            tick_input=MagicMock(),
            ledger=MagicMock(),
            raw_profiles={},
            tick_report=V3TickReportCollector(),
        ),
    )


@pytest.mark.unit
def test_preamble_run_result_has_all_phase_log_stat_fields() -> None:
    """Каждый stat_field из ``_PHASE_LOG`` объявлен на ``PreamblePipelineRunResult``."""
    stat_fields = {name for _, name in _PHASE_LOG.values() if name}
    result_fields = {f.name for f in fields(PreamblePipelineRunResult)}
    missing = stat_fields - result_fields
    assert missing == set(), (
        "PreamblePipelineRunResult missing counters used by run_preamble: "
        f"{sorted(missing)}"
    )


@pytest.mark.unit
def test_run_preamble_increments_pfo_off_count_when_phase_produces_actions() -> None:
    """Regression prod: setattr(pfo_off_count) не падает, счётчик = числу V3Action фазы."""
    dto = _dto(pfo_target=600.0)
    ctx = _with_runtime(_context([dto], _adv_state(fact=610.0, max_cpo=550.0)))
    with patch(
        f"{_MANAGER_MODULE}.build_normal_preamble_executors",
        return_value=[PayForOrderOverMaxOffOnDeepOverspendExecutor()],
    ):
        result = UpdatePipelineManager().run_preamble(ctx)

    assert isinstance(result, PreamblePipelineRunResult)
    assert result.pfo_off_count == 1
    assert dto.current_mode == KeywordStrategyMode.OFF


@pytest.mark.unit
def test_run_preamble_pfo_off_count_zero_when_phase_skipped() -> None:
    """При skip фазы счётчик не трогаем (нет actions → нет setattr)."""
    dto = _dto()
    max_cpo = 100.0
    fact = 110.0  # граница: не deep overspend
    ctx = _with_runtime(_context([dto], _adv_state(fact=fact, max_cpo=max_cpo)))
    with patch(
        f"{_MANAGER_MODULE}.build_normal_preamble_executors",
        return_value=[PayForOrderOverMaxOffOnDeepOverspendExecutor()],
    ):
        result = UpdatePipelineManager().run_preamble(ctx)

    assert result.pfo_off_count == 0
    assert dto.next_state == []
