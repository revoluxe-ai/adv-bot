"""Unit: COL-R04-003 packager + CLI (без live WB / без secrets)."""

from __future__ import annotations

import hashlib
import zipfile
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

from scripts.wb_api_readonly_ops.cli import parse_args, resolve_artifact_class
from scripts.wb_api_readonly_ops.models import ArtifactClass, FamilyName, FamilyResult, FamilyStatus
from scripts.wb_api_readonly_ops.r04_003_constants import (
    AUTHORITY_PACKAGE_SHA256,
    CONTRACT_ID_R04_003,
    PRIMARY_RETURN_BASENAME_R04_003,
    REQUIRED_ZIP_ENTRIES_R04_003,
)
from scripts.wb_api_readonly_ops.r04_003_packager import (
    R04_003PackagerInput,
    package_col_r04_003_return,
)


def _ok_payload(family_id: str) -> dict[str, object]:
    return {
        "r04_003_family_id": family_id,
        "endpoint_or_report_alias": "/probe",
        "method_class": "GET_READ",
        "authoritative_read_semantics_reference": "local_adapter:probe",
        "identifier_binding_alias_or_hash": f"ALIAS_{family_id}",
        "schema_fingerprint": "fp_test",
        "http_attempt_count": 1,
        "contract_blockers": [],
    }


def test_cli_accepts_col_r04_003_contract() -> None:
    """CLI: --contract COL-R04-003 → contract_preflight."""
    ns = parse_args(
        [
            "--shop-id",
            "placeholder-local-only",
            "--mode",
            "preflight",
            "--contract",
            CONTRACT_ID_R04_003,
            "--artifact-class",
            "contract_preflight",
        ]
    )
    assert ns.contract == CONTRACT_ID_R04_003
    assert resolve_artifact_class(ns) == ArtifactClass.CONTRACT_PREFLIGHT


def test_r04_003_packager_membership_and_no_secrets(tmp_path: Path) -> None:
    """Primary ZIP membership + sha; authority sha present; no bearer tokens."""
    family_results = {
        "ORDERS_OR_SALES_REPORTS_READ": FamilyResult(
            family=FamilyName.ORDERS_OR_SALES_REPORTS_READ,
            status=FamilyStatus.PARTIAL,
            gaps=["PERIOD_SEMANTICS_UNRESOLVED_FOR_ORDERS_FAMILY"],
            payload={
                **_ok_payload("ORDERS_OR_SALES_REPORTS_READ"),
                "contract_blockers": ["PERIOD_SEMANTICS_UNRESOLVED_FOR_ORDERS_FAMILY"],
            },
        ),
        "PROMOTION_CAMPAIGNS_READ": FamilyResult(
            family=FamilyName.ADS,
            status=FamilyStatus.OK,
            payload=_ok_payload("PROMOTION_CAMPAIGNS_READ"),
        ),
        "PROMOTION_STATISTICS_READ": FamilyResult(
            family=FamilyName.ANALYTICS,
            status=FamilyStatus.OK,
            payload=_ok_payload("PROMOTION_STATISTICS_READ"),
        ),
        "CONTENT_CARDS_READ": FamilyResult(
            family=FamilyName.CARDS,
            status=FamilyStatus.PARTIAL,
            gaps=["CONTENT_CARDS_OPTIONAL_DISCLOSED_GAP"],
            payload=_ok_payload("CONTENT_CARDS_READ"),
        ),
    }
    result = package_col_r04_003_return(
        tmp_path,
        R04_003PackagerInput(family_results=family_results),
    )
    assert result.primary_path.name == PRIMARY_RETURN_BASENAME_R04_003
    assert result.primary_sha256 == hashlib.sha256(
        result.primary_path.read_bytes()
    ).hexdigest()
    assert result.mandatory_pass_count == 2
    assert result.api_preflight_status == "REFUSED"
    assert result.global_eligibility == "NO"
    with zipfile.ZipFile(result.primary_path) as zf:
        names = sorted(n for n in zf.namelist() if not n.endswith("/"))
        assert names == sorted(REQUIRED_ZIP_ENTRIES_R04_003)
        blob = b"".join(zf.read(n) for n in names)
    text = blob.decode("utf-8", errors="replace")
    assert AUTHORITY_PACKAGE_SHA256 in text
    assert "GLOBAL_READ_ONLY_PREFLIGHT_PASS" in text
    assert "Bearer " not in text
    assert "bab6bc8e" not in text
