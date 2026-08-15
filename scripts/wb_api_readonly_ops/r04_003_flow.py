"""COL-R04-003 live API preflight flow (Job runtime only).

Запускает credentialed WB probes для mandatory families и упаковывает RETURN.
Local Cursor must not call this path against production.
"""

from __future__ import annotations

import hashlib
import json
import logging
from pathlib import Path

from scripts.wb_api_readonly_ops.models import (
    ArtifactClass,
    Mode,
    OverallStatus,
    RunReport,
)
from scripts.wb_api_readonly_ops.r04_003_constants import (
    CONTRACT_ID_R04_003,
    MODE_R04_003,
    PRIMARY_RETURN_BASENAME_R04_003,
)
from scripts.wb_api_readonly_ops.r04_003_families import R04_003FamilyRunners
from scripts.wb_api_readonly_ops.r04_003_packager import (
    R04_003PackagerError,
    R04_003PackagerInput,
    package_col_r04_003_return,
)
from scripts.wb_api_readonly_ops.contract_flow import write_operator_report

logger = logging.getLogger(__name__)


async def run_r04_003_api_preflight(
    *,
    shop_id: str,
    output_dir: Path,
    bound_alias: str,
    period_start: str,
    period_end: str,
    mode: Mode,
    wb_data_manager: object,
) -> int:
    """Live API preflight + COL-R04-003 RETURN packaging.

    Args:
        shop_id: cabinet binding (не пишется в RETURN).
        output_dir: каталог для primary ZIP + report.json.
        bound_alias: ACCOUNT_SCOPE_ALIAS.
        period_start: YYYY-MM-DD или RFC3339.
        period_end: YYYY-MM-DD или RFC3339.
        mode: preflight (collect не авторизован для COL-R04-003).
        wb_data_manager: hub.wb_data_manager из Job.

    Returns:
        0 если primary на диске и digest совпал; иначе ≠0.
    """
    _ = shop_id
    _ = mode
    period_start_rfc = (
        period_start if "T" in period_start else f"{period_start}T00:00:00+03:00"
    )
    period_end_rfc = (
        period_end if "T" in period_end else f"{period_end}T23:59:59+03:00"
    )

    runners = R04_003FamilyRunners(wb_data_manager)
    ctx: dict[str, object] = {}
    family_results = await runners.run_all(Mode.PREFLIGHT, ctx)

    try:
        packaged = package_col_r04_003_return(
            output_dir,
            R04_003PackagerInput(
                bound_alias=bound_alias,
                period_start_rfc3339=period_start_rfc,
                period_end_rfc3339=period_end_rfc,
                family_results=family_results,
            ),
        )
    except R04_003PackagerError as exc:
        logger.error("r04_003 packager failed: %s", exc)
        report = RunReport(
            mode=Mode.PREFLIGHT,
            shop_id=shop_id,
            overall_status=OverallStatus.FAILED,
            families=[],
            ceiling_max_seconds=0.0,
            ceiling_max_calls=0,
            ceiling_calls_used=0,
            ceiling_exhausted=False,
            label="r04_003_preflight_failed",
            artifact_class=ArtifactClass.CONTRACT_PREFLIGHT.value,
            contract_id=CONTRACT_ID_R04_003,
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
        and packaged.primary_path.name == PRIMARY_RETURN_BASENAME_R04_003
    )

    overall = (
        OverallStatus.OK
        if packaged.api_preflight_status == "PASS"
        else OverallStatus.PARTIAL
    )

    report = RunReport(
        mode=Mode.PREFLIGHT,
        shop_id=shop_id,
        overall_status=overall,
        families=[],
        ceiling_max_seconds=0.0,
        ceiling_max_calls=0,
        ceiling_calls_used=0,
        ceiling_exhausted=False,
        archive_sha256=packaged.primary_sha256,
        label="r04_003_api_preflight_return",
        artifact_class=ArtifactClass.CONTRACT_PREFLIGHT.value,
        contract_id=CONTRACT_ID_R04_003,
        primary_artifact=packaged.primary_path.name,
        primary_sha256=packaged.primary_sha256,
        l0_side_artifact="NONE",
        web_collector_handoff=digest_ok,
    )
    write_operator_report(report, output_dir)
    print(json.dumps(report.to_dict(), ensure_ascii=False, indent=2))
    print(f"PRIMARY_ARTIFACT={packaged.primary_path.resolve()}")
    print(f"PRIMARY_SHA256={packaged.primary_sha256}")
    print(f"MODE={MODE_R04_003}")
    print(f"API_PREFLIGHT_STATUS={packaged.api_preflight_status}")
    print(f"MANDATORY_PASS={packaged.mandatory_pass_count}/3")
    print(f"GLOBAL_READ_ONLY_PREFLIGHT_PASS=NO")
    print(f"GLOBAL_READ_ONLY_PREFLIGHT_ELIGIBILITY={packaged.global_eligibility}")
    print(f"READ_ONLY_COLLECTION_AUTHORIZED=NO")
    print(f"BLOCKERS={','.join(packaged.blockers)}")
    print(f"EXTERNAL_HANDOFF_READY={'YES' if digest_ok else 'NO'}")
    if not digest_ok:
        return 1
    return 0
