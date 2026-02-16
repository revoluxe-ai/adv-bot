from __future__ import annotations

import logging
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from app.modules.shop_runner.tasks_manager.tasks_manager import TasksManager
from .clickhouse_manager import ClickHouseManager
from ..while_decorator import while_coroutine_decorator
from ...corounines_manager.base_worker import BaseWorker

logger = logging.getLogger(__name__)


def _to_tz(dt: datetime, tz: str) -> datetime:
    tzinfo = ZoneInfo(tz)
    if dt.tzinfo is None:
        return dt.replace(tzinfo=tzinfo)
    return dt.astimezone(tzinfo)


class FillBidsByPositions(BaseWorker):
    def __init__(
        self,
        clickhouse_manager: ClickHouseManager,
        tasks_manager: TasksManager,
        update_time: int,
        step_minutes: int = 60,
        tz: str = "Europe/Moscow",
    ):
        self._clickhouse_manager = clickhouse_manager
        self._tasks_manager = tasks_manager
        self._update_time = update_time
        self._step_minutes = step_minutes
        self._tz = tz

    async def run(self):
        await while_coroutine_decorator(self._update_time, 60)(self._fill_bids_by_positions)()

    async def _fill_bids_by_positions(self) -> None:
        handler = lambda: self.__fill_bids_by_positions()
        future = await self._tasks_manager.add_task(handler)
        try:
            result = await future
        except Exception:
            logger.exception("Error while filling bids by positions")
        else:
            logger.debug("Fill bids task result: %s", result)

    async def __fill_bids_by_positions(self) -> str:

        last_ts = await self._clickhouse_manager.get_last_decision_time()
        min_ts, max_ts = await self._clickhouse_manager.get_minmax_timestamp()


        if not min_ts or not max_ts:
            return "no clusters_adv_stats data"

        # Do not start earlier than source table lower bound.
        start_ts = max(last_ts, min_ts) if last_ts is not None else min_ts
        start_ts = _to_tz(start_ts, self._tz)
        max_ts = _to_tz(max_ts, self._tz)
        if start_ts >= max_ts:
            return "no new range to fill"

        step = timedelta(minutes=self._step_minutes)
        current = start_ts
        batch_count = 0

        while current < max_ts:
            next_ts = min(current + step, max_ts)

            await self._clickhouse_manager.fill_bids_by_positions_step(
                current, next_ts, self._tz
            )
            batch_count += 1
            current = next_ts

        return f"filled {batch_count} batch(es) [{start_ts}..{max_ts})"












