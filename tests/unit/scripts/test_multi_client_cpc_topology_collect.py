"""Unit tests for the generic strict read-only CPC topology collector."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts import multi_client_cpc_topology_collect as collector

pytestmark = pytest.mark.unit


def _identity() -> collector.RunIdentity:
    """Создать identity из declared CPC topology contract."""
    return collector.RunIdentity(
        shop_id="5586b2ff-449c-4151-9518-60f46d32b7d9",
        cabinet=573,
        target_nmid=1285392243,
        adv_id=40235423,
    )


def test_foreign_identity_payload_is_rejected(tmp_path: Path) -> None:
    """Payload с чужим cabinet не может попасть в artifact."""
    (tmp_path / "payload.json").write_text(
        json.dumps({"wb_cabinet_id": 401}), encoding="utf-8"
    )
    assert collector.reconcile_identity(tmp_path, _identity()) == [
        "wb_cabinet_id: expected=573, got=401"
    ]


def test_foreign_campaign_is_rejected(tmp_path: Path) -> None:
    """Payload с чужой campaign identity отклоняется fail-closed."""
    (tmp_path / "payload.json").write_text(
        json.dumps({"adv_id": 99999999}), encoding="utf-8"
    )
    assert collector.reconcile_identity(tmp_path, _identity()) == [
        "adv_id: expected=40235423, got=99999999"
    ]


def test_write_gate_is_zero() -> None:
    """Collector declares no production writes on any protected surface."""
    assert collector.validate_write_gate() == []
    assert collector.WRITE_COUNTS["ALL_PRODUCTION_WRITES"] == 0


def test_collector_has_no_client_specific_identity_constants() -> None:
    """Identity is supplied only through the explicit runtime contract."""
    source = Path(collector.__file__).read_text(encoding="utf-8")
    assert "PROKRAFT" not in source
    assert "A1" not in source
    assert "401" not in source
