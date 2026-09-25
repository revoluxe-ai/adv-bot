"""Синхронный contract_preflight flow (primary RETURN, без live WB по умолчанию).

Spec: Contract preflight produces COL-R03-009 primary RETURN;
Operator report exposes contract artifact fields.
Decision: wb-readonly-contract-return-vs-l0.
"""

from __future__ import annotations

import hashlib
import json
import logging
from pathlib import Path

from scripts.wb_api_readonly_ops.contract_constants import (
    CONTRACT_ID,
    PRIMARY_RETURN_BASENAME,
)
from scripts.wb_api_readonly_ops.contract_mapping import build_default_mapping_gate
from scripts.wb_api_readonly_ops.contract_packager import (
    ContractPackagerError,
    ContractPackagerInput,
    package_col_r03_009_return,
)
from scripts.wb_api_readonly_ops.models import (
    ArtifactClass,
    Mode,
    OverallStatus,
    RunReport,
)
from scripts.wb_api_readonly_ops.r04_constants import (
    CONTRACT_ID_R04,
    PRIMARY_RETURN_BASENAME_R04,
)
from scripts.wb_api_readonly_ops.r04_mapping import build_r04_mapping_gate
from scripts.wb_api_readonly_ops.r04_packager import (
    R04PackagerError,
    R04PackagerInput,
    package_col_r04_001_return,
)

logger = logging.getLogger(__name__)


def write_operator_report(report: RunReport, output_dir: Path) -> Path:
    """Записать report.json для kubectl cp / SCRIPTS_REPORT."""
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / "report.json"
    path.write_text(
        json.dumps(report.to_dict(), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return path


def run_contract_preflight_sync(
    *,
    shop_id: str,
    output_dir: Path,
    bound_alias: str,
    period_start: str,
    period_end: str,
    mode: Mode = Mode.PREFLIGHT,
    emit_l0_side: bool = False,
    campaigns_live_ok: bool | None = None,
    api_request_attempt_count: int = 0,
    contract_id: str = CONTRACT_ID,
) -> int:
    """Собрать COL-R03-009 или COL-R04-001 primary RETURN.

    shop_id — только binding arg CLI/Job; в RETURN не пишется.
    Local Cursor must not invoke this path against production HTTP.

    Returns:
        0 если primary+sidecar на диске и sha совпал; иначе ≠0.
    """
    _ = shop_id
    if contract_id == CONTRACT_ID_R04:
        return _run_r04_contract_preflight_sync(
            shop_id=shop_id,
            output_dir=output_dir,
            bound_alias=bound_alias,
            period_start=period_start,
            period_end=period_end,
            mode=mode,
            campaigns_live_ok=campaigns_live_ok,
            api_request_attempt_count=api_request_attempt_count,
        )

    mapping = build_default_mapping_gate(campaigns_live_ok=campaigns_live_ok)
    try:
        packaged = package_col_r03_009_return(
            output_dir,
            ContractPackagerInput(
                bound_alias=bound_alias,
                period_start=period_start,
                period_end=period_end,
                mapping=mapping,
                api_request_attempt_count=api_request_attempt_count,
            ),
        )
    except ContractPackagerError as exc:
        logger.error("contract packager failed: %s", exc)
        report = RunReport(
            mode=mode,
            shop_id=shop_id,
            overall_status=OverallStatus.FAILED,
            families=[],
            ceiling_max_seconds=0.0,
            ceiling_max_calls=0,
            ceiling_calls_used=0,
            ceiling_exhausted=False,
            label="contract_preflight_failed",
            artifact_class=ArtifactClass.CONTRACT_PREFLIGHT.value,
            contract_id=CONTRACT_ID,
            primary_artifact=None,
            primary_sha256=None,
            l0_side_artifact="NONE",
            web_collector_handoff=False,
        )
        write_operator_report(report, output_dir)
        return 1

    on_disk_digest = hashlib.sha256(packaged.primary_path.read_bytes()).hexdigest()
    digest_ok = (
        on_disk_digest == packaged.primary_sha256
        and packaged.primary_path.name == PRIMARY_RETURN_BASENAME
    )
    l0_side = "NONE"
    if emit_l0_side:
        l0_side = "NONE"

    report = RunReport(
        mode=mode,
        shop_id=shop_id,
        overall_status=OverallStatus.PARTIAL
        if mapping.api_preflight == "REFUSED"
        else OverallStatus.OK,
        families=[],
        ceiling_max_seconds=0.0,
        ceiling_max_calls=0,
        ceiling_calls_used=0,
        ceiling_exhausted=False,
        archive_sha256=packaged.primary_sha256,
        label="contract_preflight_return",
        artifact_class=ArtifactClass.CONTRACT_PREFLIGHT.value,
        contract_id=CONTRACT_ID,
        primary_artifact=packaged.primary_path.name,
        primary_sha256=packaged.primary_sha256,
        l0_side_artifact=l0_side,
        web_collector_handoff=digest_ok,
    )
    write_operator_report(report, output_dir)
    print(json.dumps(report.to_dict(), ensure_ascii=False, indent=2))
    print(f"PRIMARY_ARTIFACT={packaged.primary_path.resolve()}")
    print(f"PRIMARY_SHA256={packaged.primary_sha256}")
    print(f"WEB_COLLECTOR_HANDOFF={'YES' if digest_ok else 'NO'}")
    if not digest_ok:
        return 1
    return 0


def _run_r04_contract_preflight_sync(
    *,
    shop_id: str,
    output_dir: Path,
    bound_alias: str,
    period_start: str,
    period_end: str,
    mode: Mode,
    campaigns_live_ok: bool | None,
    api_request_attempt_count: int,
) -> int:
    """Собрать COL-R04-001_OWNER_LOCAL_READ_ONLY_PREFLIGHT_R04.zip.

    Без live WB в этом sync-пути; cabinet B1 fail-closed если не выполнен.
    shop_id не пишется в RETURN.
    """
    _ = shop_id
    mapping = build_r04_mapping_gate(campaigns_live_ok=campaigns_live_ok)
    period_start_rfc = (
        period_start
        if "T" in period_start
        else f"{period_start}T00:00:00+03:00"
    )
    period_end_rfc = (
        period_end if "T" in period_end else f"{period_end}T23:59:59+03:00"
    )
    try:
        packaged = package_col_r04_001_return(
            output_dir,
            R04PackagerInput(
                bound_alias=bound_alias,
                period_start_rfc3339=period_start_rfc,
                period_end_rfc3339=period_end_rfc,
                mapping=mapping,
                cabinet_preflight="NOT_PERFORMED",
                api_request_attempt_count=api_request_attempt_count,
            ),
        )
    except R04PackagerError as exc:
        logger.error("r04 packager failed: %s", exc)
        report = RunReport(
            mode=mode,
            shop_id=shop_id,
            overall_status=OverallStatus.FAILED,
            families=[],
            ceiling_max_seconds=0.0,
            ceiling_max_calls=0,
            ceiling_calls_used=0,
            ceiling_exhausted=False,
            label="r04_contract_preflight_failed",
            artifact_class=ArtifactClass.CONTRACT_PREFLIGHT.value,
            contract_id=CONTRACT_ID_R04,
            primary_artifact=None,
            primary_sha256=None,
            l0_side_artifact="NONE",
            web_collector_handoff=False,
        )
        write_operator_report(report, output_dir)
        return 1

    on_disk_digest = hashlib.sha256(packaged.primary_path.read_bytes()).hexdigest()
    digest_ok = (
        on_disk_digest == packaged.primary_sha256
        and packaged.primary_path.name == PRIMARY_RETURN_BASENAME_R04
    )
    report = RunReport(
        mode=mode,
        shop_id=shop_id,
        overall_status=OverallStatus.OK
        if packaged.read_only_preflight_pass
        else OverallStatus.PARTIAL,
        families=[],
        ceiling_max_seconds=0.0,
        ceiling_max_calls=0,
        ceiling_calls_used=0,
        ceiling_exhausted=False,
        archive_sha256=packaged.primary_sha256,
        label="r04_contract_preflight_return",
        artifact_class=ArtifactClass.CONTRACT_PREFLIGHT.value,
        contract_id=CONTRACT_ID_R04,
        primary_artifact=packaged.primary_path.name,
        primary_sha256=packaged.primary_sha256,
        l0_side_artifact="NONE",
        web_collector_handoff=digest_ok,
    )
    write_operator_report(report, output_dir)
    print(json.dumps(report.to_dict(), ensure_ascii=False, indent=2))
    print(f"PRIMARY_ARTIFACT={packaged.primary_path.resolve()}")
    print(f"PRIMARY_SHA256={packaged.primary_sha256}")
    print(f"READ_ONLY_PREFLIGHT_PASS={'YES' if packaged.read_only_preflight_pass else 'NO'}")
    print(f"VERDICT={packaged.verdict}")
    print(f"BLOCKERS={','.join(packaged.blockers)}")
    print(f"EXTERNAL_HANDOFF_READY={'YES' if digest_ok else 'NO'}")
    if not digest_ok:
        return 1
    return 0
