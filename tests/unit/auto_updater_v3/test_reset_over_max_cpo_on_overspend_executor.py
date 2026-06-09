"""Unit: ResetOverMaxCpoOnOverspendExecutor и cpo percent gate."""

from __future__ import annotations

from dataclasses import replace

import pytest

from app.modules.shop_runner.service_manager.services.auto_updater_v3.update_pipeline.executors.reset_over_max_cpo_on_overspend import (
    ResetOverMaxCpoOnOverspendExecutor,
)
from tests.unit.auto_updater_v3.test_pay_for_order_over_max_off_on_deep_overspend_executor import (
    _adv_state,
    _context,
    _dto,
)


@pytest.mark.unit
def test_skip_when_cpo_percent_is_85() -> None:
    ctx = _context([_dto()], _adv_state(fact=85.0, max_cpo=100.0))
    executor = ResetOverMaxCpoOnOverspendExecutor()
    executor.execute(ctx)
    assert executor.skip_reason == "cpo_percent_lt_100"
    assert ctx.keywords[0].next_state == []


@pytest.mark.unit
def test_skip_when_cpo_percent_is_95() -> None:
    ctx = _context([_dto()], _adv_state(fact=95.0, max_cpo=100.0))
    executor = ResetOverMaxCpoOnOverspendExecutor()
    executor.execute(ctx)
    assert executor.skip_reason == "cpo_percent_lt_100"
    assert ctx.keywords[0].next_state == []


@pytest.mark.unit
def test_skip_when_max_cpo_is_none() -> None:
    ctx = _context([_dto()], _adv_state(fact=95.0, max_cpo=100.0))
    ctx.adv_state = replace(ctx.adv_state, max_pay_for_order=None)
    executor = ResetOverMaxCpoOnOverspendExecutor()
    executor.execute(ctx)
    assert executor.skip_reason == "no_current_cpo_percent"
    assert ctx.keywords[0].next_state == []


@pytest.mark.unit
def test_not_skipped_when_cpo_percent_is_105() -> None:
    ctx = _context([_dto()], _adv_state(fact=105.0, max_cpo=100.0))
    executor = ResetOverMaxCpoOnOverspendExecutor()
    executor.execute(ctx)
    assert executor.skip_reason != "cpo_percent_lt_100"
