"""Проверка, что PROMOTION-heavy run_tasks используют shared tasks_manager."""

from __future__ import annotations

import re
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[6]
_MANAGER_PY = _REPO_ROOT / "app" / "modules" / "shop_runner" / "service_manager" / "manager.py"
_CLUSTER_BIDS_PY = (
    _REPO_ROOT
    / "app"
    / "modules"
    / "shop_runner"
    / "service_manager"
    / "services"
    / "update_cluster_bids_manager"
    / "update_cluster_bids_manager.py"
)

_PROMOTION_HEAVY_METHODS = (
    "adv_settings_auto_update",
    "update_minus_phrases_in_advs",
    "auto_budget_watchdog",
    # D3: update_individual_keyword_target_places is intentional v3-only no-op
    # (no run_tasks); do not parametrize obsolete V2 KeywordTargetPlaceUpdater path.
    "auto_shelf_bid_increment_stats",
    "auto_shelf_bid_control",
)


def _method_body(source: str, method_name: str) -> str:
    marker = f"async def {method_name}("
    start = source.find(marker)
    assert start != -1, f"method {method_name} not found"
    rest = source[start + len(marker) :]
    next_method = rest.find("\n    async def ")
    end = start + len(marker) + (next_method if next_method != -1 else len(rest))
    return source[start:end]


def _run_tasks_calls_in_block(block: str) -> list[str]:
    calls: list[str] = []
    for match in re.finditer(r"await run_tasks\(", block):
        calls.append(block[match.start() : match.start() + 500])
    return calls


@pytest.mark.unit
@pytest.mark.parametrize("method_name", _PROMOTION_HEAVY_METHODS)
def test_manager_promotion_methods_use_shared_tasks_manager(method_name: str) -> None:
    source = _MANAGER_PY.read_text(encoding="utf-8")
    block = _method_body(source, method_name)
    calls = _run_tasks_calls_in_block(block)
    assert calls, f"run_tasks not found in {method_name}"
    for call in calls:
        assert "tasks_manager=self._tasks_manager" in call


@pytest.mark.unit
def test_update_cluster_bids_manager_run_tasks_use_tasks_manager() -> None:
    source = _CLUSTER_BIDS_PY.read_text(encoding="utf-8")
    calls = _run_tasks_calls_in_block(source)
    assert calls
    for call in calls:
        assert "tasks_manager=self._tasks_manager" in call
