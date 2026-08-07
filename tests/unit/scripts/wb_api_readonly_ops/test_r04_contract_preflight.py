"""Unit: COL-R04-001 packager + CLI (без live WB / без secrets)."""

from __future__ import annotations

import hashlib
import zipfile
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

from scripts.wb_api_readonly_ops.cli import parse_args, resolve_artifact_class
from scripts.wb_api_readonly_ops.contract_flow import run_contract_preflight_sync
from scripts.wb_api_readonly_ops.models import ArtifactClass, Mode
from scripts.wb_api_readonly_ops.r04_constants import (
    CONTRACT_ID_R04,
    INSTALL_PACKAGE_SHA256,
    PRIMARY_RETURN_BASENAME_R04,
    REQUIRED_ZIP_ENTRIES_R04,
)
from scripts.wb_api_readonly_ops.r04_mapping import build_r04_mapping_gate
from scripts.wb_api_readonly_ops.r04_packager import package_col_r04_001_return


def test_cli_accepts_col_r04_001_contract() -> None:
    """CLI: --contract COL-R04-001 → contract_preflight."""
    ns = parse_args(
        [
            "--shop-id",
            "placeholder-local-only",
            "--mode",
            "preflight",
            "--contract",
            CONTRACT_ID_R04,
            "--artifact-class",
            "contract_preflight",
        ]
    )
    assert ns.contract == CONTRACT_ID_R04
    assert resolve_artifact_class(ns) == ArtifactClass.CONTRACT_PREFLIGHT


def test_r04_mapping_mandatory_incomplete_refuses_api() -> None:
    """3 mandatory families; only campaigns PASS_MAP → API REFUSED."""
    gate = build_r04_mapping_gate()
    assert gate.mandatory_pass_count == 1
    assert gate.api_preflight == "REFUSED"
    assert any(
        f.disposition == "OPTIONAL_DISCLOSED_GAP" for f in gate.families
    )


def test_r04_packager_writes_primary_without_secrets(tmp_path: Path) -> None:
    """Primary ZIP membership + sha; no shop_id/token strings."""
    result = package_col_r04_001_return(tmp_path)
    assert result.primary_path.name == PRIMARY_RETURN_BASENAME_R04
    assert result.primary_sha256 == hashlib.sha256(
        result.primary_path.read_bytes()
    ).hexdigest()
    assert result.read_only_preflight_pass is False
    assert "CABINET_B1_NEW_PREFLIGHT_NOT_PERFORMED_IN_API_JOB_CONTOUR" in (
        result.blockers
    )
    with zipfile.ZipFile(result.primary_path) as zf:
        names = sorted(n for n in zf.namelist() if not n.endswith("/"))
        assert names == sorted(REQUIRED_ZIP_ENTRIES_R04)
        blob = b"".join(zf.read(n) for n in names)
    text = blob.decode("utf-8", errors="replace")
    assert "shop_id" not in text.lower() or "SHOP_ID_IN_RETURN=FORBIDDEN" in text
    assert "Bearer " not in text
    assert INSTALL_PACKAGE_SHA256 in text
    # raw uuid-like shop ids must not appear as values
    assert "bab6bc8e" not in text


def test_r04_contract_flow_sync(tmp_path: Path) -> None:
    """contract_flow COL-R04-001 writes primary + report.json."""
    code = run_contract_preflight_sync(
        shop_id="placeholder-local-only",
        output_dir=tmp_path,
        bound_alias="WB-TEST-CABINET-001",
        period_start="2026-07-04",
        period_end="2026-08-02",
        mode=Mode.PREFLIGHT,
        contract_id=CONTRACT_ID_R04,
    )
    assert code == 0
    assert (tmp_path / PRIMARY_RETURN_BASENAME_R04).is_file()
    assert (tmp_path / f"{PRIMARY_RETURN_BASENAME_R04}.sha256").is_file()
    assert (tmp_path / "report.json").is_file()
