"""Регрессии bundle shape normalization (runtime t0055 family)."""

from __future__ import annotations

from datetime import date
from unittest.mock import patch

import pytest

from app.core.mp.wb.api.generated.promotion.v1.marketing_and_promotions_client.models.full_stats_item import (
    FullStatsItem,
)
from scripts.strict_single_nmid_audit import (
    AuditIdentity,
    AuditPeriod,
    StrictSingleNmidAudit,
    readers_from_owner_bot_plane,
)
from scripts.strict_single_nmid_audit_owner_bot_plane import (
    OwnerBotStrictSingleNmidReadOnlyPlane,
)
from scripts.wb_api_readonly_ops.collect import owner_bot_evidence

IDENTITY = AuditIdentity(
    shop_id="5586b2ff-449c-4151-9518-60f46d32b7d9",
    cabinet=573,
    nmid=186069402,
    size_id=305698863,
    timezone="Europe/Moscow",
)
PERIOD = AuditPeriod(
    start=date(2026, 9, 8),
    end=date(2026, 9, 21),
    timezone="Europe/Moscow",
)


@pytest.mark.unit
def test_normalize_evidence_dict_tree_full_stats_item() -> None:
    """``FullStatsItem`` → recursive plain dict (``days`` nodes dict-safe)."""
    item = FullStatsItem.from_dict(
        {
            "advertId": 31411431,
            "atbs": 0,
            "canceled": 0,
            "clicks": 0,
            "cpc": 0.0,
            "cr": 0.0,
            "ctr": 0.0,
            "days": [
                {
                    "date": "2026-09-08",
                    "sum": 562.01,
                    "apps": [{"nms": [{"nmId": 186069402, "orders": 2}]}],
                }
            ],
            "orders": 0,
            "shks": 0,
            "sum": 562.01,
            "sum_price": 0.0,
            "views": 0,
        }
    )
    normalized = owner_bot_evidence.normalize_evidence_dict_tree(item)
    assert isinstance(normalized["days"][0], dict)
    assert normalized["days"][0]["sum"] == 562.01


@pytest.mark.unit
def test_plane_readers_no_bare_attribute_error_on_fullstats_object() -> None:
    """Attrs fullstats object в bundle не даёт голый ``section: AttributeError``."""
    item = FullStatsItem.from_dict(
        {
            "advertId": 31411431,
            "atbs": 0,
            "canceled": 0,
            "clicks": 0,
            "cpc": 0.0,
            "cr": 0.0,
            "ctr": 0.0,
            "days": [
                {
                    "date": "2026-09-08",
                    "sum": 562.01,
                    "apps": [{"nms": [{"nmId": 186069402, "orders": 1}]}],
                }
            ],
            "orders": 0,
            "shks": 0,
            "sum": 562.01,
            "sum_price": 0.0,
            "views": 0,
        }
    )
    bundle = owner_bot_evidence.OwnerBotEvidenceBundle(
        pg_rows=[
            {
                "nmids": "186069402",
                "adv_id": 31411431,
                "_search_adv_id": 31411470,
                "type": 1,
                "active_status": "on",
                "bot_active": True,
                "target_price_for_order": 1,
                "max_price_for_order": 2,
                "auto_budget_daily_limit": 3,
                "search_auto_budget_daily_limit": 4,
                "common_budget_daily_limit": 5,
            }
        ],
        campaigns=[],
        fullstats=[item],
        orders=[
            {
                "nmId": 186069402,
                "date": "2026-09-08",
                "quantity": 1,
                "finishedPrice": 100,
                "isCancel": False,
            }
        ],
        memberships={31411431: {186069402}},
    )

    class _Audit(StrictSingleNmidAudit):
        def __init__(self) -> None:
            super().__init__(IDENTITY, days=14)
            self.period = PERIOD

    plane = OwnerBotStrictSingleNmidReadOnlyPlane()
    with patch.object(plane._runtime, "run", return_value=bundle):
        payload = _Audit().run(readers_from_owner_bot_plane(plane))

    bare = [g for g in payload["decision"]["gaps"] if g.endswith(": AttributeError")]
    assert bare == []
    assert payload["physical_spend"]["status"] == "confirmed"
    assert payload["physical_spend"]["value"] == "562.01"
    assert payload["write_budget"]["writes"] == 0
    plane.close()


@pytest.mark.unit
def test_orchestrator_marks_mapping_attribute_error_as_implementation_shape() -> None:
    """Голый ``AttributeError`` на ``.get()`` → ``implementation_shape`` marker."""

    class _Row:
        nmId = 1

    def _orders_fail(
        _identity: AuditIdentity, _period: AuditPeriod
    ) -> list[object]:
        _Row().get("nmId")
        return []

    audit = StrictSingleNmidAudit(IDENTITY)
    payload = audit.run({"orders": _orders_fail})
    gap = next(g for g in payload["decision"]["gaps"] if g.startswith("orders:"))
    assert "implementation_shape=1" in gap
    assert payload["write_budget"]["writes"] == 0
