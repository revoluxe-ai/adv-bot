"""Unit: COL-R04-003B packager + probe helpers (без live WB)."""

from __future__ import annotations

import hashlib
import zipfile
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

from scripts.wb_api_readonly_ops.cli import parse_args, resolve_artifact_class
from scripts.wb_api_readonly_ops.models import ArtifactClass
from scripts.wb_api_readonly_ops.r04_003b_constants import (
    AUTHORITY_PACKAGE_SHA256,
    CONTRACT_ID_R04_003B,
    PRIMARY_RETURN_BASENAME_R04_003B,
    REQUIRED_ZIP_ENTRIES_R04_003B,
)
from scripts.wb_api_readonly_ops.r04_003b_packager import package_col_r04_003b_return
from scripts.wb_api_readonly_ops.r04_003b_probe import (
    OrdersSalesProbeEvidence,
    orders_family_pass,
)


def test_cli_accepts_col_r04_003b() -> None:
    ns = parse_args(
        [
            "--shop-id",
            "placeholder-local-only",
            "--mode",
            "preflight",
            "--contract",
            CONTRACT_ID_R04_003B,
            "--artifact-class",
            "contract_preflight",
        ]
    )
    assert ns.contract == CONTRACT_ID_R04_003B
    assert resolve_artifact_class(ns) == ArtifactClass.CONTRACT_PREFLIGHT


def test_orders_pass_empty_lists_admissible() -> None:
    ev = OrdersSalesProbeEvidence(
        orders_status="PASS",
        sales_status="PASS",
        orders_http_attempts=1,
        sales_http_attempts=1,
        orders_rows_count=0,
        sales_rows_count=0,
        orders_http_status_class="HTTP_200",
        sales_http_status_class="HTTP_200",
    )
    assert orders_family_pass(ev)


def test_packager_membership_and_eligibility(tmp_path: Path) -> None:
    ev = OrdersSalesProbeEvidence(
        orders_status="PASS",
        sales_status="PASS",
        orders_http_attempts=1,
        sales_http_attempts=1,
        orders_rows_count=12,
        sales_rows_count=0,
        orders_http_status_class="HTTP_200",
        sales_http_status_class="HTTP_200",
    )
    result = package_col_r04_003b_return(tmp_path, ev)
    assert result.primary_path.name == PRIMARY_RETURN_BASENAME_R04_003B
    assert result.mandatory_pass_count == 3
    assert result.global_eligibility == "CANDIDATE_YES"
    assert result.orders_family_status == "PASS"
    digest = hashlib.sha256(result.primary_path.read_bytes()).hexdigest()
    assert digest == result.primary_sha256
    with zipfile.ZipFile(result.primary_path) as zf:
        names = sorted(n for n in zf.namelist() if not n.endswith("/"))
        assert names == sorted(REQUIRED_ZIP_ENTRIES_R04_003B)
        blob = b"".join(zf.read(n) for n in names)
    text = blob.decode("utf-8", errors="replace")
    assert AUTHORITY_PACKAGE_SHA256 in text
    assert "RECLASSIFIED_AS_COLLECTION_STAGE_NOT_PREFLIGHT_BLOCKER" in text
    assert "OPTIONAL_GAP" in text
    assert "bab6bc8e" not in text
