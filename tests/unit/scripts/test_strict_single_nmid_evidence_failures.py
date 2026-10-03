"""Typed failure mapping в StrictSingleNmidAudit orchestrator."""

from __future__ import annotations

from datetime import date
from unittest.mock import MagicMock

import pytest

from scripts.strict_single_nmid_audit import (
    AuditIdentity,
    AuditPeriod,
    StrictSingleNmidAudit,
)
from scripts.wb_api_readonly_ops.collect.owner_bot_evidence import EvidenceReaderFailure


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
def test_orchestrator_maps_evidence_reader_failure_to_gap_provenance() -> None:
    """EvidenceReaderFailure → GAP gap line с source/phase, не голый type name."""

    def _failing_reader(
        _identity: AuditIdentity, _period: AuditPeriod
    ) -> list[object]:
        raise EvidenceReaderFailure(
            section="orders",
            source="owner-bot-wb-evidence",
            phase="wb_load",
            error_class="RuntimeError",
            message="simulated",
        )

    audit = StrictSingleNmidAudit(IDENTITY)
    payload = audit.run({"orders": _failing_reader})
    gap_line = next(
        line for line in payload["decision"]["gaps"] if line.startswith("orders:")
    )
    assert "source=owner-bot-wb-evidence" in gap_line
    assert "phase=wb_load" in gap_line
    assert "RuntimeError" in gap_line
    assert payload["write_budget"]["writes"] == 0


@pytest.mark.unit
def test_orchestrator_identity_reader_failure_blocks_identity() -> None:
    """Failure с section=identity помечает identity BLOCKED."""

    def _identity_fail(
        _identity: AuditIdentity, _period: AuditPeriod
    ) -> list[object]:
        raise EvidenceReaderFailure(
            section="identity",
            source="owner-bot-pg-wbcabinet",
            phase="pg_identity",
            error_class="StrictAuditError",
            message="mismatch",
        )

    audit = StrictSingleNmidAudit(IDENTITY)
    payload = audit.run({"current_contour": _identity_fail})
    assert payload["section_statuses"]["identity"] == "BLOCKED"
    assert payload["write_budget"]["writes"] == 0
