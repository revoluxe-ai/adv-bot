"""Periodic updater for campaign settings history.

Spec: campaign-settings-history.
Disabled by caller/config by default; default cadence is 300 seconds.
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from time import monotonic

from .domain import CabinetCollectResult
from .runtime import collect_one_locked_cabinet, discover_history_cabinet_ids

DEFAULT_INTERVAL_SECONDS = 300

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class HistoryTickResult:
    code: str
    cabinets_discovered: int
    cabinets_ok: int
    lock_contended: int
    campaigns_read: int
    unchanged: int
    inserted: int
    invalid: int
    failures: int
    duration_seconds: float


class CampaignSettingsHistoryUpdater:
    """Single-process tick guard plus cross-process cabinet xact locks."""

    def __init__(
        self,
        *,
        interval_seconds: int = DEFAULT_INTERVAL_SECONDS,
        enabled: bool = False,
    ) -> None:
        if interval_seconds <= 0:
            raise ValueError("interval_seconds must be positive")
        self.interval_seconds = interval_seconds
        self.enabled = enabled
        self._tick_lock = asyncio.Lock()

    async def run_once(self) -> HistoryTickResult:
        started = monotonic()
        if not self.enabled:
            return HistoryTickResult(
                code="disabled",
                cabinets_discovered=0,
                cabinets_ok=0,
                lock_contended=0,
                campaigns_read=0,
                unchanged=0,
                inserted=0,
                invalid=0,
                failures=0,
                duration_seconds=monotonic() - started,
            )
        if self._tick_lock.locked():
            return HistoryTickResult(
                code="overlap_skipped",
                cabinets_discovered=0,
                cabinets_ok=0,
                lock_contended=0,
                campaigns_read=0,
                unchanged=0,
                inserted=0,
                invalid=0,
                failures=0,
                duration_seconds=monotonic() - started,
            )

        async with self._tick_lock:
            cabinet_ids = await discover_history_cabinet_ids()
            # Lazy import is intentional: disabled mode MUST NOT initialize
            # ClickHouse settings/client state or open any external connection.
            from app.utils.click_house.client import get_clickhouse_client

            results: list[CabinetCollectResult] = []
            async with get_clickhouse_client() as clickhouse_client:
                for wb_cabinet_id in cabinet_ids:
                    try:
                        result = await collect_one_locked_cabinet(
                            wb_cabinet_id=wb_cabinet_id,
                            clickhouse_client=clickhouse_client,
                        )
                    except Exception:
                        logger.exception(
                            "campaign settings history cabinet collection failed",
                            extra={"wb_cabinet_id": wb_cabinet_id},
                        )
                        results.append(
                            CabinetCollectResult(
                                wb_cabinet_id=wb_cabinet_id,
                                code="failure",
                            )
                        )
                    else:
                        results.append(result)

            lock_contended = sum(r.code == "lock_contended" for r in results)
            failures = sum(
                r.code not in {"ok", "partial_invalid", "lock_contended"}
                for r in results
            )
            tick_result = HistoryTickResult(
                code="ok" if failures == 0 else "degraded",
                cabinets_discovered=len(cabinet_ids),
                cabinets_ok=sum(
                    r.code in {"ok", "partial_invalid"} for r in results
                ),
                lock_contended=lock_contended,
                campaigns_read=sum(r.campaigns_read for r in results),
                unchanged=sum(r.unchanged for r in results),
                inserted=sum(r.inserted for r in results),
                invalid=sum(r.invalid for r in results),
                failures=failures,
                duration_seconds=monotonic() - started,
            )
            logger.info(
                "campaign settings history tick finished",
                extra={
                    "history_code": tick_result.code,
                    "cabinets_discovered": tick_result.cabinets_discovered,
                    "cabinets_ok": tick_result.cabinets_ok,
                    "lock_contended": tick_result.lock_contended,
                    "campaigns_read": tick_result.campaigns_read,
                    "unchanged": tick_result.unchanged,
                    "inserted": tick_result.inserted,
                    "invalid": tick_result.invalid,
                    "failures": tick_result.failures,
                    "duration_seconds": tick_result.duration_seconds,
                },
            )
            return tick_result

    async def run_forever(self) -> None:
        """Run periodic ticks; cancellation propagates normally."""
        while True:
            await self.run_once()
            await asyncio.sleep(self.interval_seconds)
