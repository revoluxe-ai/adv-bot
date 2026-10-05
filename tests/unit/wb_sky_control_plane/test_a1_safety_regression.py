"""A1 safety regression: zero ORM DML/flush/commit and zero WB mutation imports."""

from __future__ import annotations

import ast
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.modules.wb_sky_control_plane.kernel.pipeline import dry_run
from app.modules.wb_sky_control_plane.models.changeset import (
    BudgetPolicyPayload,
    CampaignResourceRef,
    ChangeSetV1,
    LogicalScopeV1,
    SetBudgetPolicyOperation,
)
from app.modules.wb_sky_control_plane.registry.model import WbSkyCampaignResourceRegistry

pytestmark = pytest.mark.unit

_REPO = Path(__file__).resolve().parents[3]
_PACKAGE = _REPO / "app" / "modules" / "wb_sky_control_plane"

_FORBIDDEN_IMPORT_PREFIXES = (
    "app.core.mp.wb.api.managers.wb_promotion_manager",
    "app.modules.shop_runner",
    "app.client_bot.user_interface.services.adv_excel_roundtrip.writer",
)


class _RecordingWbReader:
    mutation_methods_called: list[str] = []

    async def fetch_adverts_raw_by_ids(
        self, adv_ids: list[int]
    ) -> list[dict[str, object]]:
        return [
            {
                "id": adv_ids[0],
                "bid_type": "unified",
                "status": 9,
                "settings": {
                    "payment_type": "cpm",
                    "placements": {"search": False, "recommendations": True},
                },
                "nm_settings": [{"nm_id": 1}],
            }
        ]


@pytest.mark.asyncio
async def test_dry_run_performs_zero_orm_dml_flush_commit() -> None:
    """dry_run must not call session add/delete/flush/commit (read-only ORM)."""
    registry_row = WbSkyCampaignResourceRegistry(
        resource_id="cmp_safe001",
        wb_cabinet_id=1,
        adv_setting_id=50,
        auto_adv_id=101,
        search_adv_id=None,
        anchor_fingerprint="af",
    )
    adv_row = SimpleNamespace(
        auto_budget_watchdog_enabled=False,
        auto_budget_daily_limit=0,
        search_auto_budget_daily_limit=0,
        use_common_budget=True,
        common_budget_daily_limit=0,
        auto_budget_total_limit=500,
        search_auto_budget_total_limit=500,
        common_budget_total_limit=500,
        orders_source_for_auto_mode=SimpleNamespace(value="COMMON_STATISTIC"),
        plan_for_sales_for_day=None,
        target_price_for_order=None,
        max_price_for_order=None,
        sales_predict_method=SimpleNamespace(value="FACT"),
        strategy=SimpleNamespace(value="MIN_CPO"),
        auto_update_strategy=False,
        auto_shelf_bid_control_enabled=False,
        auto_shelf_bid_control_strategy=None,
    )
    cabinet_result = MagicMock()
    cabinet_result.scalar_one_or_none.return_value = 1
    registry_result = MagicMock()
    registry_result.scalars.return_value.all.return_value = [registry_row]
    session = MagicMock()
    session.execute = AsyncMock(side_effect=[cabinet_result, registry_result])
    session.get = AsyncMock(return_value=adv_row)
    session.add = MagicMock()
    session.delete = MagicMock()
    session.flush = AsyncMock()
    session.commit = AsyncMock()

    changeset = ChangeSetV1(
        changeset_id="cs-safe",
        scope=LogicalScopeV1(shop_id="shop-safe"),
        operations=[
            SetBudgetPolicyOperation(
                operation_id="op-safe-1",
                resource=CampaignResourceRef(resource_id="cmp_safe001"),
                payload=BudgetPolicyPayload(auto_budget_daily_limit=10),
            )
        ],
    )
    _ = await dry_run(
        changeset,
        session=session,
        wb_reader=_RecordingWbReader(),
    )

    session.add.assert_not_called()
    session.delete.assert_not_called()
    session.flush.assert_not_called()
    session.commit.assert_not_called()


def test_control_plane_import_graph_excludes_forbidden_mutation_adapters() -> None:
    """Kernel package must not import production mutation write adapters."""
    imported: set[str] = set()
    for path in sorted(_PACKAGE.rglob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported.update(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module is not None:
                imported.add(node.module)

    for prefix in _FORBIDDEN_IMPORT_PREFIXES:
        assert not any(name.startswith(prefix) for name in imported)


@pytest.mark.asyncio
async def test_wb_reader_port_is_get_only_surface() -> None:
    """Fake reader records only fetch_adverts_raw_by_ids — no mutation methods."""
    reader = _RecordingWbReader()
    _ = await reader.fetch_adverts_raw_by_ids([101])
    assert _RecordingWbReader.mutation_methods_called == []
