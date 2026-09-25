"""Unit: COL-R03-009 contract_preflight packager + gates (без live WB).

Specs:
  - wb-readonly-contract-preflight-return
  - wb-api-read-only-preflight (contract CLI surface)
Decision: wb-readonly-contract-return-vs-l0
"""

from __future__ import annotations

import hashlib
import json
import zipfile
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

from scripts.wb_api_readonly_ops.accept_gate import (
    PreflightPassRequiredError,
    read_preflight_pass_accepted,
    require_preflight_pass_or_raise,
)
from scripts.wb_api_readonly_ops.archive import ARCHIVE_NAME, write_l0_archive
from scripts.wb_api_readonly_ops.cli import parse_args, resolve_artifact_class
from scripts.wb_api_readonly_ops.contract_constants import (
    CONTRACT_ID,
    PRIMARY_RETURN_BASENAME,
    PRIMARY_RETURN_SHA_BASENAME,
    REQUIRED_ZIP_ENTRIES,
)
from scripts.wb_api_readonly_ops.contract_mapping import build_default_mapping_gate
from scripts.wb_api_readonly_ops.contract_packager import (
    ContractPackagerError,
    ContractPackagerInput,
    package_col_r03_009_return,
)
from scripts.wb_api_readonly_ops.contract_flow import run_contract_preflight_sync
from scripts.wb_api_readonly_ops.models import (
    ArtifactClass,
    FamilyName,
    FamilyResult,
    FamilyStatus,
    Mode,
    OverallStatus,
    RunReport,
)


def test_cli_baseline_without_contract_flags() -> None:
    """Characterization 1.1: legacy CLI без contract остаётся валидным.

    Spec: Default L0 research remains available without contract.
    """
    ns = parse_args(["--shop-id", "abc", "--mode", "preflight"])
    assert ns.contract is None
    assert ns.artifact_class is None
    assert resolve_artifact_class(ns) is None
    assert ns.mode == "preflight"
    assert ns.orders_date_from == "2026-07-04"


def test_cli_contract_preflight_flags() -> None:
    """CLI surface: --contract / --artifact-class / period / bound-alias.

    Spec: Explicit contract and artifact-class CLI surface.
    """
    ns = parse_args(
        [
            "--shop-id",
            "abc",
            "--mode",
            "preflight",
            "--contract",
            CONTRACT_ID,
            "--artifact-class",
            "contract_preflight",
            "--bound-alias",
            "WB-TEST-CABINET-001",
            "--period-start",
            "2026-07-04",
            "--period-end",
            "2026-08-02",
        ]
    )
    assert ns.contract == CONTRACT_ID
    assert resolve_artifact_class(ns) == ArtifactClass.CONTRACT_PREFLIGHT
    assert ns.bound_alias == "WB-TEST-CABINET-001"
    assert ns.period_start == "2026-07-04"
    assert ns.period_end == "2026-08-02"

    ns2 = parse_args(
        ["--shop-id", "abc", "--mode", "preflight", "--contract", CONTRACT_ID]
    )
    assert resolve_artifact_class(ns2) == ArtifactClass.CONTRACT_PREFLIGHT


def test_packager_writes_exact_primary_and_membership(tmp_path: Path) -> None:
    """1.2: primary RETURN + sidecar + exact COL-R03-009 file list.

    Spec: Contract preflight emits primary RETURN and sidecar.
    """
    result = package_col_r03_009_return(tmp_path)
    assert result.primary_path.name == PRIMARY_RETURN_BASENAME
    assert result.sidecar_path.name == PRIMARY_RETURN_SHA_BASENAME
    assert result.primary_path.is_file()
    assert result.sidecar_path.is_file()
    on_disk = hashlib.sha256(result.primary_path.read_bytes()).hexdigest()
    assert on_disk == result.primary_sha256
    sidecar = result.sidecar_path.read_text(encoding="utf-8")
    assert result.primary_sha256 in sidecar
    with zipfile.ZipFile(result.primary_path, "r") as zf:
        names = set(zf.namelist())
    assert set(REQUIRED_ZIP_ENTRIES) == names


def test_contract_run_exit_nonzero_without_primary(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """1.3: contract mode без primary → exit ≠ 0.

    Spec: Contract preflight produces COL-R03-009 primary RETURN.
    """

    def _boom(*_a: object, **_k: object) -> object:
        raise ContractPackagerError("forced missing primary")

    monkeypatch.setattr(
        "scripts.wb_api_readonly_ops.contract_flow.package_col_r03_009_return",
        _boom,
    )
    code = run_contract_preflight_sync(
        shop_id="shop-should-not-appear-in-zip",
        output_dir=tmp_path,
        bound_alias="WB-TEST-CABINET-001",
        period_start="2026-07-04",
        period_end="2026-08-02",
    )
    assert code != 0
    assert not (tmp_path / PRIMARY_RETURN_BASENAME).exists()


def test_honest_refused_still_packages_return(tmp_path: Path) -> None:
    """1.4: REFUSED mapping всё равно собирает RETURN; не PASS retrofit.

    Spec: Honest REFUSED still packages RETURN.
    """
    mapping = build_default_mapping_gate()
    assert mapping.api_preflight == "REFUSED"
    assert mapping.pass_map_count == 1  # campaigns only
    result = package_col_r03_009_return(
        tmp_path, ContractPackagerInput(mapping=mapping)
    )
    assert result.api_preflight == "REFUSED"
    assert result.blockers
    with zipfile.ZipFile(result.primary_path, "r") as zf:
        status = zf.read("00_STATUS.yaml").decode("utf-8")
    assert "api_preflight: REFUSED" in status
    assert "PASS_CANDIDATE" not in status.split("api_preflight:", 1)[1].split(
        "\n", 1
    )[0]


def test_l0_alone_not_web_handoff(tmp_path: Path) -> None:
    """1.5: L0 alone при contract semantics → handoff NO.

    Spec: L0 cannot satisfy Web handoff.
    """
    report = RunReport(
        mode=Mode.COLLECT,
        shop_id="abc",
        overall_status=OverallStatus.PARTIAL,
        families=[
            FamilyResult(family=FamilyName.ADS, status=FamilyStatus.OK),
        ],
        ceiling_max_seconds=1.0,
        ceiling_max_calls=1,
        ceiling_calls_used=1,
        ceiling_exhausted=False,
        artifact_class=ArtifactClass.CONTRACT_PREFLIGHT.value,
        contract_id=CONTRACT_ID,
        primary_artifact=None,
        primary_sha256=None,
        l0_side_artifact=ARCHIVE_NAME,
        web_collector_handoff=False,
    )
    write_l0_archive(report, output_dir=tmp_path)
    assert (tmp_path / ARCHIVE_NAME).is_file()
    assert not (tmp_path / PRIMARY_RETURN_BASENAME).exists()
    payload = report.to_dict()
    assert payload["WEB_COLLECTOR_HANDOFF"] == "NO"
    assert payload["EXTERNAL_HANDOFF_READY"] == "NO"
    assert payload["PRIMARY_ARTIFACT"] is None


def test_clean_dump_without_pass_fails_closed(tmp_path: Path) -> None:
    """1.6: clean_dump / require-pass без YES → error; 0 API implied.

    Spec: Clean dump without pass fails closed.
    """
    assert read_preflight_pass_accepted(None) is False
    missing = tmp_path / "nope.txt"
    assert read_preflight_pass_accepted(missing) is False
    with pytest.raises(PreflightPassRequiredError):
        require_preflight_pass_or_raise(None)

    bad = tmp_path / "accept.txt"
    bad.write_text("READ_ONLY_PREFLIGHT_PASS=NO\n", encoding="utf-8")
    with pytest.raises(PreflightPassRequiredError):
        require_preflight_pass_or_raise(bad)

    good = tmp_path / "ok.txt"
    good.write_text("READ_ONLY_PREFLIGHT_PASS=YES\n", encoding="utf-8")
    require_preflight_pass_or_raise(good)

    ns = parse_args(
        [
            "--shop-id",
            "abc",
            "--mode",
            "collect",
            "--artifact-class",
            "clean_dump",
        ]
    )
    assert resolve_artifact_class(ns) == ArtifactClass.CLEAN_DUMP


def test_sha_sidecar_and_report_match_primary(tmp_path: Path) -> None:
    """1.7: sidecar + report PRIMARY_SHA256 == digest zip.

    Spec: Archive digest matches primary zip.
    """
    code = run_contract_preflight_sync(
        shop_id="abc",
        output_dir=tmp_path,
        bound_alias="WB-TEST-CABINET-001",
        period_start="2026-07-04",
        period_end="2026-08-02",
    )
    assert code == 0
    primary = tmp_path / PRIMARY_RETURN_BASENAME
    digest = hashlib.sha256(primary.read_bytes()).hexdigest()
    sidecar = (tmp_path / PRIMARY_RETURN_SHA_BASENAME).read_text(encoding="utf-8")
    assert digest in sidecar
    report = json.loads((tmp_path / "report.json").read_text(encoding="utf-8"))
    assert report["PRIMARY_SHA256"] == digest
    assert report["archive_sha256"] == digest
    assert report["ARTIFACT_CLASS"] == "contract_preflight"
    assert report["CONTRACT_ID"] == CONTRACT_ID
    assert report["WEB_COLLECTOR_HANDOFF"] == "YES"
    assert report["EXTERNAL_HANDOFF_READY"] == "YES"
    assert report["PRIMARY_ARTIFACT"] == PRIMARY_RETURN_BASENAME


def test_return_excludes_shop_id_token_raw_rows(tmp_path: Path) -> None:
    """1.8: RETURN без shop_id / token / raw rows.

    Spec: RETURN has no shop_id or token material.
    """
    shop = "bab6bc8e-8123-4559-862e-5da3a8ed5b69"
    code = run_contract_preflight_sync(
        shop_id=shop,
        output_dir=tmp_path,
        bound_alias="WB-TEST-CABINET-001",
        period_start="2026-07-04",
        period_end="2026-08-02",
    )
    assert code == 0
    primary = tmp_path / PRIMARY_RETURN_BASENAME
    with zipfile.ZipFile(primary, "r") as zf:
        blob = b"".join(zf.read(n) for n in zf.namelist()).decode(
            "utf-8", errors="replace"
        )
    assert shop not in blob
    assert "Bearer " not in blob
    assert "Authorization" not in blob
    assert "raw_response_body: NOT_INCLUDED" in blob
    assert "rows_count" not in blob
    with zipfile.ZipFile(primary, "r") as zf2:
        assert "payload.json" not in zf2.namelist()
        assert "report.json" not in zf2.namelist()


def test_l0_research_mode_still_writes_research_zip(tmp_path: Path) -> None:
    """1.9 Paired: L0 path без contract всё ещё пишет research zip.

    Spec: Default L0 research remains available without contract.
    """
    report = RunReport(
        mode=Mode.COLLECT,
        shop_id="abc",
        overall_status=OverallStatus.OK,
        families=[
            FamilyResult(family=FamilyName.ADS, status=FamilyStatus.OK),
        ],
        ceiling_max_seconds=1.0,
        ceiling_max_calls=1,
        ceiling_calls_used=1,
        ceiling_exhausted=False,
        artifact_class=ArtifactClass.L0_RESEARCH.value,
    )
    path, digest = write_l0_archive(report, output_dir=tmp_path)
    assert path.name == ARCHIVE_NAME
    assert path.is_file()
    assert hashlib.sha256(path.read_bytes()).hexdigest() == digest
    assert (tmp_path / "report.json").is_file()
