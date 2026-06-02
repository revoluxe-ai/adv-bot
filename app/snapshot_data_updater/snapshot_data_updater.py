"""Точка входа процесса ``snapshot_data_updater`` (корневой ``updater.py``)."""

from __future__ import annotations

import asyncio
import logging

from app.snapshot_data_updater.config import get_snapshot_config, reload_snapshot_config
from app.snapshot_data_updater.factory import build_snapshot_updater

logger = logging.getLogger(__name__)

_SMOKE_DURATION_SEC: float = 0.05


def _ensure_config_loaded() -> None:
    """Перечитывает env, если entrypoint уже вызвал dotenv (идемпотентно)."""
    try:
        import dotenv

        dotenv.load_dotenv()
    except ImportError:
        pass
    reload_snapshot_config()


async def run() -> None:
    """Долгоживущий процесс: global tick + shop tasks."""
    from app.snapshot_data_updater.bootstrap import ensure_di_bootstrapped, shutdown_di

    _ensure_config_loaded()
    cfg = get_snapshot_config()
    if cfg.use_live_updater:
        await ensure_di_bootstrapped()
    stop_event = asyncio.Event()
    updater = build_snapshot_updater(config=cfg)
    mode = "live" if cfg.use_live_updater else "stub"
    logger.info(
        "Snapshot data updater started mode=%s interval_sec=%.0f tick_policy=%s",
        mode,
        cfg.refresh_interval_sec,
        cfg.tick_policy,
    )
    try:
        await updater.run(stop_event=stop_event)
    finally:
        if cfg.use_live_updater:
            await shutdown_di()
        logger.info("Snapshot data updater process stopped")


async def run_smoke() -> None:
    """Короткий stub smoke."""
    _ensure_config_loaded()
    stop_event = asyncio.Event()
    updater = build_snapshot_updater(shop_ids=["stub-shop"])

    async def _stop_after_delay() -> None:
        await asyncio.sleep(_SMOKE_DURATION_SEC)
        stop_event.set()

    stopper = asyncio.create_task(_stop_after_delay())
    try:
        await updater.run(stop_event=stop_event)
    finally:
        stopper.cancel()
        await asyncio.gather(stopper, return_exceptions=True)
    logger.info("snapshot_data_updater smoke finished")


def run_smoke_cli() -> None:
    """CLI: ``python -m app.snapshot_data_updater.snapshot_data_updater``."""
    asyncio.run(run_smoke())


if __name__ == "__main__":
    from app.snapshot_data_updater.cli import main

    raise SystemExit(main(["smoke"]))
