"""CLI snapshot_data_updater: stub smoke, live once, live daemon.

Примеры::

    poetry run python -m app.snapshot_data_updater.cli smoke
    poetry run python -m app.snapshot_data_updater.cli live-once --shop-id MY_SHOP
    poetry run python -m app.snapshot_data_updater.cli daemon
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import sys

import dotenv

logger = logging.getLogger(__name__)


def _bootstrap_env() -> None:
    """Загружает .env и перечитывает SNAPSHOT_* конфиг."""
    dotenv.load_dotenv()
    from app.snapshot_data_updater.config import reload_snapshot_config

    cfg = reload_snapshot_config()
    logger.info(
        "snapshot config: use_live=%s interval_sec=%.0f tick_policy=%s",
        cfg.use_live_updater,
        cfg.refresh_interval_sec,
        cfg.tick_policy,
    )


async def _cmd_smoke() -> None:
    from app.snapshot_data_updater.snapshot_data_updater import run_smoke

    await run_smoke()


async def _cmd_live_once(shop_id: str) -> None:
    from app.snapshot_data_updater.bootstrap import ensure_di_bootstrapped, shutdown_di
    from app.snapshot_data_updater.config import get_snapshot_config
    from app.snapshot_data_updater.factory import build_snapshot_updater_live

    await ensure_di_bootstrapped()
    try:
        cfg = get_snapshot_config()
        if not cfg.use_live_updater:
            logger.warning(
                "SNAPSHOT_UPDATER_USE_LIVE=0 — принудительно live-once для shop_id=%s",
                shop_id,
            )
        updater = build_snapshot_updater_live(shop_ids=[shop_id], config=cfg)
        batch = await updater.refresh_shop(shop_id)
        logger.info(
            "live-once done shop_id=%s snapshots=%d collected_at=%s",
            batch.shop_id,
            len(batch.snapshots),
            batch.collected_at.isoformat(),
        )
        for snap in batch.snapshots[:5]:
            logger.info(
                "  adv_id=%s keywords=%d partial=%s completeness=%s",
                snap.adv_id,
                len(snap.keywords),
                snap.partial,
                snap.section_completeness,
            )
        if len(batch.snapshots) > 5:
            logger.info("  ... and %d more adv snapshots", len(batch.snapshots) - 5)
    finally:
        await shutdown_di()


async def _cmd_daemon() -> None:
    from app.snapshot_data_updater.snapshot_data_updater import run

    await run()


def main(argv: list[str] | None = None) -> int:
    """Точка входа CLI."""
    parser = argparse.ArgumentParser(
        description="Snapshot data updater: smoke / live-once / daemon"
    )
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("smoke", help="Stub smoke (~50ms), без БД")

    p_once = sub.add_parser("live-once", help="Один shop: collect + save в Redis")
    p_once.add_argument(
        "--shop-id",
        required=True,
        help="shop_id WB (обязательный)",
    )

    sub.add_parser("daemon", help="Бесконечный tick (как updater.py процесс)")

    args = parser.parse_args(argv)

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    _bootstrap_env()

    try:
        if args.command == "smoke":
            asyncio.run(_cmd_smoke())
        elif args.command == "live-once":
            asyncio.run(_cmd_live_once(args.shop_id))
        elif args.command == "daemon":
            asyncio.run(_cmd_daemon())
        else:
            parser.print_help()
            return 2
    except KeyboardInterrupt:
        logger.info("Interrupted")
        return 130
    except Exception:
        logger.exception("snapshot CLI failed")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
