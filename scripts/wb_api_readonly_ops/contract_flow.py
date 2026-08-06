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
) -> int:
    """Собрать COL-R03-009 primary RETURN.

    shop_id — только binding arg CLI/Job; в RETURN не пишется.

    Returns:
        0 если primary+sidecar на диске и sha совпал; иначе ≠0.
    """
    _ = shop_id
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
