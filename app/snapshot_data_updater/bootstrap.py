"""Bootstrap DI для процесса ``snapshot_data_updater`` (отдельный от ``updater.py``).

Warmup keywords вызывает ``get_good_bad_phrases`` → ``WBManager`` / ``CpmSourcesResolver``,
которым нужен ``DIManager`` + wiring (как в ``new_wb_shop_update_run.py``).
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.core.di.di_manager import DIManager
    from app.core.di.app_container import AppContainer

logger = logging.getLogger(__name__)

_di_manager: DIManager[AppContainer] | None = None


async def ensure_di_bootstrapped() -> None:
    """Один раз на процесс: ``AppContainer`` + wire ``wb_base_manager`` и др."""
    global _di_manager
    if _di_manager is not None:
        return
    from app.core.di.app_container import AppContainer
    from app.core.di.di_manager import DIManager

    _di_manager = await DIManager.create(AppContainer)  # type: ignore[attr-defined]
    logger.info("snapshot_data_updater: DI bootstrap completed")


async def shutdown_di() -> None:
    """Освобождение ресурсов DI при остановке процесса."""
    global _di_manager
    if _di_manager is None:
        return
    await _di_manager.__aexit__(None, None, None)
    _di_manager = None
    logger.info("snapshot_data_updater: DI shutdown completed")
