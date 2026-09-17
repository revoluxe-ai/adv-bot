"""
Entrypoint: WB API read-only preflight/collect → L0 and/or COL-R03-009 RETURN.

Job examples:
  # Stage A Web COLLECTOR primary (Owner-bot; not Cursor→prod)
  python scripts/wb_api_readonly_ops/run.py \\
    --shop-id <uuid> --mode preflight \\
    --contract COL-R03-009 --artifact-class contract_preflight \\
    --bound-alias WB-TEST-CABINET-001 \\
    --period-start 2026-07-04 --period-end 2026-08-02 \\
    --output-dir <run_outputs>

  # L0 research (Owner-local only; not Web handoff)
  python scripts/wb_api_readonly_ops/run.py --shop-id <uuid> --mode collect

Known outputs (/opsx-scripts):
  PRIMARY (contract_preflight):
    …_COL-R03-009_RETURN.zip + .sha256
  SIDE / L0:
    wb_readonly_research.zip, report.json, archive.sha256

Decision: wb-readonly-contract-return-vs-l0 — L0 MUST NOT be primary under
COL-R03-009. Spec: wb-readonly-contract-preflight-return.
"""

from __future__ import annotations

import asyncio
import json
import logging
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

# When Python runs this file by path, only the file directory is added to
# sys.path. Resolve both repository import roots from __file__ so the
# compatibility entrypoint is independent of the caller's CWD.
_PACKAGE_ROOT = Path(__file__).resolve().parents[1]
_REPOSITORY_ROOT = _PACKAGE_ROOT.parent
for _path in (str(_REPOSITORY_ROOT), str(_PACKAGE_ROOT)):
    if _path not in sys.path:
        sys.path.insert(0, _path)

try:
    from set_path import add_project_root_to_path
except ImportError:
    from scripts.set_path import add_project_root_to_path

add_project_root_to_path()

import dotenv

dotenv.load_dotenv(dotenv_path=_PACKAGE_ROOT / ".env", override=False)

from redis.asyncio import Redis

from app.configs.app_config import AppConfig
from app.core.di.wb_manager_hub.wb_manager_hub_factory import WBManagerHubFactory
from app.core.mp.wb.api.httpx_client_handler import HttpxClientHandler
from app.core.redis_manager_v2.redis_client import RedisClient
from app.modules.common_slaves.wildberries.super_cabinet_manager import (
    get_access_for_wb_cabinet,
)
from scripts.wb_api_readonly_ops.accept_gate import (
    PreflightPassRequiredError,
    require_preflight_pass_or_raise,
)
from scripts.wb_api_readonly_ops.archive import (
    ARCHIVE_NAME,
    DEFAULT_OUTPUT_DIR,
    write_l0_archive,
)
from scripts.wb_api_readonly_ops.ceiling import RunCeiling
from scripts.wb_api_readonly_ops.cli import parse_args, resolve_artifact_class
from scripts.wb_api_readonly_ops.r04_003_constants import CONTRACT_ID_R04_003
from scripts.wb_api_readonly_ops.r04_003_flow import run_r04_003_api_preflight
from scripts.wb_api_readonly_ops.r04_003b_constants import CONTRACT_ID_R04_003B
from scripts.wb_api_readonly_ops.r04_003b_flow import run_r04_003b_orders_preflight_fix
from scripts.wb_api_readonly_ops.contract_constants import CONTRACT_ID
from scripts.wb_api_readonly_ops.contract_flow import (
    run_contract_preflight_sync,
    write_operator_report,
)
from scripts.wb_api_readonly_ops.families import HubFamilyRunners
from scripts.wb_api_readonly_ops.models import (
    ArtifactClass,
    Mode,
    OverallStatus,
    RunReport,
)
from scripts.wb_api_readonly_ops.cli import DEFAULT_COLLECT_MAX_SECONDS
from scripts.wb_api_readonly_ops.collect.runner import run_full_collect
from scripts.wb_api_readonly_ops.orchestrator import run_ops

logger = logging.getLogger(__name__)


async def _async_main(argv: list[str] | None = None) -> int:
    """Bootstrap: accept-gate → contract RETURN или L0 archive. Exit code."""
    args = parse_args(argv)
    mode = Mode(args.mode)
    shop_id = str(args.shop_id)
    output_dir = Path(args.output_dir) if args.output_dir else DEFAULT_OUTPUT_DIR
    artifact_class = resolve_artifact_class(args)
    require_pass_path = (
        Path(args.require_preflight_pass) if args.require_preflight_pass else None
    )

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )

    # Fail-closed BEFORE any API / redis (spec: Clean dump without pass).
    needs_pass = (
        artifact_class == ArtifactClass.CLEAN_DUMP or require_pass_path is not None
    )
    if needs_pass:
        try:
            require_preflight_pass_or_raise(require_pass_path)
        except PreflightPassRequiredError as exc:
            logger.error("%s", exc)
            report = RunReport(
                mode=mode,
                shop_id=shop_id,
                overall_status=OverallStatus.FAILED,
                families=[],
                ceiling_max_seconds=0.0,
                ceiling_max_calls=0,
                ceiling_calls_used=0,
                ceiling_exhausted=False,
                label="preflight_pass_required",
                artifact_class=(artifact_class.value if artifact_class else None),
                contract_id=args.contract,
                web_collector_handoff=False,
            )
            write_operator_report(report, output_dir)
            print(json.dumps(report.to_dict(), ensure_ascii=False, indent=2))
            return 1

    # Contract primary RETURN path.
    if artifact_class == ArtifactClass.CONTRACT_PREFLIGHT:
        contract_id = str(args.contract) if args.contract else CONTRACT_ID
        if contract_id in (CONTRACT_ID_R04_003, CONTRACT_ID_R04_003B):
            # COL-R04-003 / 003B: live credentialed API in Job runtime only.
            app_config = AppConfig.create()
            redis_config = app_config.infrastructure.redis
            redis_client_raw: Redis[str] = Redis(
                host=redis_config.host,
                port=redis_config.port,
                db=redis_config.db,
                password=redis_config.password,
                decode_responses=True,
            )
            await redis_client_raw.ping()
            redis_client_wrapper = RedisClient(redis_client=redis_client_raw)
            httpx_client_handler = HttpxClientHandler()
            await httpx_client_handler.init()
            wb_manager_hub_factory = WBManagerHubFactory(
                httpx_client_handler=httpx_client_handler,
                redis_client_wrapper=redis_client_wrapper,
            )
            try:
                access = await get_access_for_wb_cabinet(shop_id)
                _ = access
                hub = wb_manager_hub_factory.get_wb_manager_hub(shop_id)
                if contract_id == CONTRACT_ID_R04_003B:
                    return await run_r04_003b_orders_preflight_fix(
                        shop_id=shop_id,
                        output_dir=output_dir,
                        wb_data_manager=hub.wb_data_manager,
                    )
                return await run_r04_003_api_preflight(
                    shop_id=shop_id,
                    output_dir=output_dir,
                    bound_alias=str(args.bound_alias),
                    period_start=str(args.period_start),
                    period_end=str(args.period_end),
                    mode=mode,
                    wb_data_manager=hub.wb_data_manager,
                )
            finally:
                await httpx_client_handler.shutdown()
                await redis_client_raw.close()

        return run_contract_preflight_sync(
            shop_id=shop_id,
            output_dir=output_dir,
            bound_alias=str(args.bound_alias),
            period_start=str(args.period_start),
            period_end=str(args.period_end),
            mode=mode,
            emit_l0_side=bool(args.emit_l0_side),
            contract_id=contract_id,
        )

    # Legacy / explicit L0 research path (and clean_dump after accept → L0 collect).
    app_config = AppConfig.create()
    redis_config = app_config.infrastructure.redis
    redis_client_raw: Redis[str] = Redis(
        host=redis_config.host,
        port=redis_config.port,
        db=redis_config.db,
        password=redis_config.password,
        decode_responses=True,
    )
    await redis_client_raw.ping()
    redis_client_wrapper = RedisClient(redis_client=redis_client_raw)
    httpx_client_handler = HttpxClientHandler()
    await httpx_client_handler.init()

    wb_manager_hub_factory = WBManagerHubFactory(
        httpx_client_handler=httpx_client_handler,
        redis_client_wrapper=redis_client_wrapper,
    )

    try:
        access = await get_access_for_wb_cabinet(shop_id)
        _ = access

        hub = wb_manager_hub_factory.get_wb_manager_hub(shop_id)

        if mode == Mode.COLLECT:
            collect_seconds = float(args.max_seconds)
            if collect_seconds == 180.0:
                collect_seconds = DEFAULT_COLLECT_MAX_SECONDS
            collect_report = await run_full_collect(
                shop_id=shop_id,
                wb_data_manager=hub.wb_data_manager,
                output_dir=output_dir,
                orders_date_from=str(args.orders_date_from),
                max_seconds=collect_seconds,
                max_api_calls=int(args.max_api_calls),
                ads_date_from=args.ads_date_from,
                ads_date_to=args.ads_date_to,
                funnel_nmid_batch_size=int(args.funnel_nmid_batch_size),
                cards_page_limit=int(args.cards_page_limit),
            )
            logger.info(
                "wb_api_readonly_ops collect done shop_id=%s overall=%s sha256=%s",
                shop_id,
                collect_report.overall_status,
                collect_report.archive_sha256,
            )
            print(json.dumps(collect_report.to_dict(), ensure_ascii=False, indent=2))
            print(f"ARCHIVE_PATH={(output_dir / ARCHIVE_NAME).resolve()}")
            print(f"ARCHIVE_SHA256={collect_report.archive_sha256}")
            print("WEB_COLLECTOR_HANDOFF=NO")
            if collect_report.overall_status == OverallStatus.FAILED.value:
                return 1
            return 0

        runners = HubFamilyRunners(hub.wb_data_manager).as_dict()
        ceiling = RunCeiling(
            max_seconds=float(args.max_seconds),
            max_calls=int(args.max_calls),
        )
        shared = {"orders_date_from": str(args.orders_date_from)}
        report = await run_ops(
            shop_id=shop_id,
            mode=mode,
            runners=runners,
            ceiling=ceiling,
            shared=shared,
        )
        report.artifact_class = (
            artifact_class.value
            if artifact_class
            else ArtifactClass.L0_RESEARCH.value
        )
        report.contract_id = None
        report.web_collector_handoff = False
        report.primary_artifact = None
        report.primary_sha256 = None

        report.archive_sha256 = None
        archive_path, digest = write_l0_archive(report, output_dir=output_dir)
        report.archive_sha256 = digest
        report.l0_side_artifact = ARCHIVE_NAME
        # Re-write so archive_sha256 inside report matches on-disk zip.
        archive_path, digest = write_l0_archive(report, output_dir=output_dir)
        report.archive_sha256 = digest

        logger.info(
            "wb_api_readonly_ops done mode=%s shop_id=%s overall=%s archive=%s sha256=%s",
            mode.value,
            shop_id,
            report.overall_status.value,
            archive_path,
            digest,
        )
        print(json.dumps(report.to_dict(), ensure_ascii=False, indent=2))
        print(f"ARCHIVE_PATH={archive_path.resolve()}")
        print(f"ARCHIVE_SHA256={digest}")
        print("WEB_COLLECTOR_HANDOFF=NO")

        if report.overall_status == OverallStatus.FAILED:
            return 1
        return 0
    finally:
        await httpx_client_handler.shutdown()
        await redis_client_raw.close()


def main(argv: list[str] | None = None) -> None:
    """Sync entry for `python scripts/wb_api_readonly_ops/run.py`."""
    raise SystemExit(asyncio.run(_async_main(argv)))


if __name__ == "__main__":
    main(sys.argv[1:])
