"""COL-R04-003B orders-family preflight fix flow (Job runtime only)."""

from __future__ import annotations

import hashlib
import json
import logging
from pathlib import Path

from scripts.wb_api_readonly_ops.contract_flow import write_operator_report
from scripts.wb_api_readonly_ops.models import (
    ArtifactClass,
    Mode,
    OverallStatus,
    RunReport,
)
from scripts.wb_api_readonly_ops.r04_003b_constants import (
    CONTRACT_ID_R04_003B,
    MODE_R04_003B,
    PRIMARY_RETURN_BASENAME_R04_003B,
)
from scripts.wb_api_readonly_ops.r04_003b_packager import (
    R04_003bPackagerError,
    package_col_r04_003b_return,
)
from scripts.wb_api_readonly_ops.r04_003b_probe import run_orders_sales_flag1_probe

logger = logging.getLogger(__name__)


async def run_r04_003b_orders_preflight_fix(
    *,
    shop_id: str,
    output_dir: Path,
    wb_data_manager: object,
) -> int:
    """Live flag=1 probe + COL-R04-003B RETURN (orders family only).

    shop_id не пишется в RETURN. Local Cursor must not call production HTTP.
    """
    _ = shop_id
    evidence = await run_orders_sales_flag1_probe(wb_data_manager)

    try:
        packaged = package_col_r04_003b_return(output_dir, evidence)
    except R04_003bPackagerError as exc:
        logger.error("r04_003b packager failed: %s", exc)
        report = RunReport(
            mode=Mode.PREFLIGHT,
            shop_id=shop_id,
            overall_status=OverallStatus.FAILED,
            families=[],
            ceiling_max_seconds=0.0,
            ceiling_max_calls=0,
            ceiling_calls_used=0,
            ceiling_exhausted=False,
            label="r04_003b_preflight_failed",
            artifact_class=ArtifactClass.CONTRACT_PREFLIGHT.value,
            contract_id=CONTRACT_ID_R04_003B,
            primary_artifact=None,
            primary_sha256=None,
            l0_side_artifact="NONE",
            web_collector_handoff=False,
        )
        write_operator_report(report, output_dir)
        return 1

    on_disk = hashlib.sha256(packaged.primary_path.read_bytes()).hexdigest()
    digest_ok = (
        on_disk == packaged.primary_sha256
        and packaged.primary_path.name == PRIMARY_RETURN_BASENAME_R04_003B
    )

    overall = (
        OverallStatus.OK
        if packaged.orders_family_status == "PASS"
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
        label="r04_003b_orders_preflight_return",
        artifact_class=ArtifactClass.CONTRACT_PREFLIGHT.value,
        contract_id=CONTRACT_ID_R04_003B,
        primary_artifact=packaged.primary_path.name,
        primary_sha256=packaged.primary_sha256,
        l0_side_artifact="NONE",
        web_collector_handoff=digest_ok,
    )
    write_operator_report(report, output_dir)
    print(json.dumps(report.to_dict(), ensure_ascii=False, indent=2))
    print(f"PRIMARY_ARTIFACT={packaged.primary_path.resolve()}")
    print(f"PRIMARY_SHA256={packaged.primary_sha256}")
    print(f"MODE={MODE_R04_003B}")
    print(f"ORDERS_OR_SALES_REPORTS_READ={packaged.orders_family_status}")
    print(f"MANDATORY_PASS={packaged.mandatory_pass_count}/3")
    print(f"GLOBAL_READ_ONLY_PREFLIGHT_PASS=NO")
    print(f"GLOBAL_READ_ONLY_PREFLIGHT_ELIGIBILITY={packaged.global_eligibility}")
    print(f"READ_ONLY_COLLECTION_AUTHORIZED=NO")
    print(f"BLOCKERS={','.join(packaged.blockers)}")
    print(f"EXTERNAL_HANDOFF_READY={'YES' if digest_ok else 'NO'}")
    return 0 if digest_ok else 1
