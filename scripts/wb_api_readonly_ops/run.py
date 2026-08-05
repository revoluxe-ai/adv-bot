"""
Entrypoint: WB API read-only preflight/collect → Owner-local L0 archive.

Job example:
  python scripts/wb_api_readonly_ops/run.py --shop-id <uuid> --mode collect

Known outputs (for /opsx-scripts kubectl cp):
  scripts/wb_api_readonly_ops/outputs/wb_readonly_research.zip
  scripts/wb_api_readonly_ops/outputs/report.json
  scripts/wb_api_readonly_ops/outputs/archive.sha256
"""

from __future__ import annotations

import asyncio
import json
import logging
import sys
from pathlib import Path

try:
    from set_path import add_project_root_to_path
except ImportError:
    from scripts.set_path import add_project_root_to_path

add_project_root_to_path()

import dotenv

dotenv.load_dotenv()

from redis.asyncio import Redis

from app.configs.app_config import AppConfig
from app.core.di.wb_manager_hub.wb_manager_hub_factory import WBManagerHubFactory
from app.core.mp.wb.api.httpx_client_handler import HttpxClientHandler
from app.core.redis_manager_v2.redis_client import RedisClient
from app.modules.common_slaves.wildberries.super_cabinet_manager import (
    get_access_for_wb_cabinet,
)
from scripts.wb_api_readonly_ops.archive import DEFAULT_OUTPUT_DIR, write_l0_archive
from scripts.wb_api_readonly_ops.ceiling import RunCeiling
from scripts.wb_api_readonly_ops.cli import parse_args
from scripts.wb_api_readonly_ops.families import HubFamilyRunners
from scripts.wb_api_readonly_ops.models import Mode, OverallStatus
from scripts.wb_api_readonly_ops.orchestrator import run_ops

logger = logging.getLogger(__name__)


async def _async_main(argv: list[str] | None = None) -> int:
    """Bootstrap hub, run ops, write L0 archive. Returns process exit code."""
    args = parse_args(argv)
    mode = Mode(args.mode)
    shop_id = str(args.shop_id)
    output_dir = Path(args.output_dir) if args.output_dir else DEFAULT_OUTPUT_DIR

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )

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
        # Access-plane proof; hub AuthClientHandler re-fetches tokens per call.
        access = await get_access_for_wb_cabinet(shop_id)
        _ = access

        hub = wb_manager_hub_factory.get_wb_manager_hub(shop_id)
        runners = HubFamilyRunners(hub.wb_data_manager).as_dict()
        ceiling = RunCeiling(
            max_seconds=float(args.max_seconds),
            max_calls=int(args.max_calls),
        )
        # ORDERS: pilot dateFrom from CLI (default 2026-07-04), not yesterday→today.
        shared = {"orders_date_from": str(args.orders_date_from)}
        report = await run_ops(
            shop_id=shop_id,
            mode=mode,
            runners=runners,
            ceiling=ceiling,
            shared=shared,
        )
        # placeholder sha then rewrite once with digest in report body
        report.archive_sha256 = None
        archive_path, digest = write_l0_archive(report, output_dir=output_dir)
        report.archive_sha256 = digest
        archive_path, digest = write_l0_archive(report, output_dir=output_dir)

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
