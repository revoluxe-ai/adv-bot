"""Unit tests for Owner-bot Job entrypoint wiring strict single-NMID audit."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from scripts import strict_single_nmid_audit as audit_mod
from scripts.strict_single_nmid_audit import (
    ACTIONABLE,
    AuditIdentity,
    Evidence,
    evidence,
    readers_from_owner_bot_plane,
)
from scripts.wb_api_readonly_ops.mutation_guard import MUTATION_WRITE_OPS


IDENTITY = AuditIdentity(
    shop_id="5586b2ff-449c-4151-9518-60f46d32b7d9",
    cabinet=573,
    nmid=186069402,
    size_id=305698863,
    timezone="Europe/Moscow",
)


class _StubPlane:
    """Minimal read-only plane for entrypoint wiring tests."""

    def read_current_contour(self, identity: AuditIdentity, period) -> list[Evidence]:
        return [
            evidence(
                identity,
                "current_contour",
                "nmid_offer",
                {"nmid": identity.nmid},
                source="stub-contour",
                period=period,
            )
        ]

    def read_orders(self, identity: AuditIdentity, period) -> list[Evidence]:
        return [
            evidence(
                identity,
                "orders",
                "orders",
                1,
                source="statistics-reports",
                provenance={
                    "family": "ORDERS_OR_SALES_REPORTS_READ",
                    "endpoint": "GET /api/v1/supplier/orders",
                    "period_attestation": period.as_dict(),
                },
                period=period,
            )
        ]

    def read_attribution(self, identity: AuditIdentity, period) -> list[Evidence]:
        return []

    def read_topology(self, identity: AuditIdentity, period) -> list[Evidence]:
        return []

    def read_stock(self, identity: AuditIdentity, period) -> list[Evidence]:
        return []

    def read_physical_spend(self, identity: AuditIdentity, period):
        from scripts.strict_single_nmid_audit import SpendEvidence

        return [
            SpendEvidence(
                10,
                "stub-spend",
                "physical:1",
                identity,
                period,
            )
        ]


def test_local_execution_fail_closed_without_kubernetes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Bare local CLI refuses without Owner-bot Job runtime."""
    monkeypatch.delenv("KUBERNETES_SERVICE_HOST", raising=False)
    code = audit_mod.main(
        [
            "--shop-id",
            IDENTITY.shop_id,
            "--cabinet",
            str(IDENTITY.cabinet),
            "--nmid",
            str(IDENTITY.nmid),
            "--size-id",
            str(IDENTITY.size_id),
            "--output",
            "out.json",
        ]
    )
    assert code == 1


def test_run_owner_bot_job_wires_injected_readers(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Job entrypoint passes Owner-bot plane readers into StrictSingleNmidAudit.run()."""
    monkeypatch.setattr(
        "scripts.set_path.add_project_root_to_path",
        lambda: tmp_path,
    )
    output = tmp_path / "STRICT-SINGLE-NMID-AUDIT.json"
    args = SimpleNamespace(
        shop_id=IDENTITY.shop_id,
        cabinet=IDENTITY.cabinet,
        nmid=IDENTITY.nmid,
        size_id=IDENTITY.size_id,
        timezone=IDENTITY.timezone,
        output=output,
    )
    stub = _StubPlane()
    stub.ensure_bundle = MagicMock()  # type: ignore[attr-defined]
    stub.close = MagicMock()  # type: ignore[attr-defined]
    with patch(
        "scripts.strict_single_nmid_audit_owner_bot_plane.build_owner_bot_read_only_plane",
        return_value=stub,
    ):
        with patch(
            "scripts.strict_single_nmid_audit.readers_from_owner_bot_plane",
            wraps=readers_from_owner_bot_plane,
        ) as wired:
            payload = audit_mod.run_owner_bot_job(args)
            wired.assert_called_once_with(stub)
            stub.ensure_bundle.assert_called_once()  # type: ignore[attr-defined]
            stub.close.assert_called_once()  # type: ignore[attr-defined]
    assert output.is_file()
    assert payload["decision"]["status"] in {ACTIONABLE, "PARTIAL", "BLOCKED"}


def test_injected_read_only_plane_passes_mutation_guard() -> None:
    """Plane module never invokes mutation denylist operations."""
    from scripts import strict_single_nmid_audit_owner_bot_plane as plane_mod

    source = Path(plane_mod.__file__).read_text(encoding="utf-8")
    for op in MUTATION_WRITE_OPS:
        assert f'assert_read_only_op("{op}")' not in source


def test_owner_bot_plane_does_not_import_write_capable_collectors() -> None:
    """Job plane must not depend on A1 or unrelated write collectors."""
    from scripts import strict_single_nmid_audit_owner_bot_plane as plane_mod
    from scripts.wb_api_readonly_ops.collect import owner_bot_evidence

    plane_source = Path(plane_mod.__file__).read_text(encoding="utf-8").lower()
    shared_source = Path(owner_bot_evidence.__file__).read_text(encoding="utf-8").lower()
    assert "a1_strict_read_only_contract_collect" not in plane_source
    assert "prokraft_14d_entry_economics" not in plane_source
    assert "owner_bot_evidence" in plane_source
    assert "get_async_session_maker(read_only=true)" in shared_source.replace(" ", "")


def test_main_success_in_kubernetes_runtime(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Kubernetes-detected runtime executes wired Job path."""
    monkeypatch.setenv("KUBERNETES_SERVICE_HOST", "10.0.0.1")
    output = tmp_path / "STRICT-SINGLE-NMID-AUDIT.json"
    with patch(
        "scripts.strict_single_nmid_audit.run_owner_bot_job",
        return_value={"primary_artifact_sha256": "abc", "decision": {"status": ACTIONABLE}},
    ):
        code = audit_mod.main(
            [
                "--shop-id",
                IDENTITY.shop_id,
                "--cabinet",
                str(IDENTITY.cabinet),
                "--nmid",
                str(IDENTITY.nmid),
                "--size-id",
                str(IDENTITY.size_id),
                "--output",
                str(output),
            ]
        )
    assert code == 0
