from __future__ import annotations

from datetime import datetime

from app.core.clickhouse_manager.base_clickhouse_manager import BaseClickHouseManager
from app.utils.click_house.client import get_clickhouse_client as get_client

DT_FMT = "%Y-%m-%d %H:%M:%S"
GET_MINMAX_SQL = (
    "SELECT min(timestamp) AS ts_min, max(timestamp) AS ts_max " # noqa
    "FROM default_db.clusters_adv_stats"
)
TARGET_TABLE = "default_db.bid_decision_log"
SESSION_TZ = "Europe/Moscow"


def _fmt(dt: datetime) -> str:
    return dt.strftime(DT_FMT)


def _esc(value: str) -> str:
    return value.replace("\\", "\\\\").replace("'", "\\'")


class ClickHouseManager(BaseClickHouseManager):
    @staticmethod
    async def get_minmax_timestamp(
    ) -> tuple[datetime | None, datetime | None]:
        async with get_client() as client:
            _ = await client.query(f"SET session_timezone = '{SESSION_TZ}'")
            response = await client.query(GET_MINMAX_SQL)
        min_ts, max_ts = response.first_row
        return min_ts, max_ts

    @staticmethod
    async def get_last_decision_time() -> datetime | None:
        query = f"SELECT max(decision_time) FROM {TARGET_TABLE}" # noqa
        async with get_client() as client:
            _ = await client.query(f"SET session_timezone = '{SESSION_TZ}'")
            response = await client.query(query)
        (result,) = response.first_row
        return result

    async def fill_bids_by_positions_step(
        self, from_ts: datetime, to_ts: datetime, tz: str = "Europe/Moscow"
    ) -> None:
        from_s = _fmt(from_ts)
        to_s = _fmt(to_ts)
        sql = self._build_insert_sql(from_s, to_s, tz)
        async with get_client() as client:
            _ = await client.query(f"SET session_timezone = '{tz}'")
            _ = await client.query(sql)
        return None

    def _build_insert_sql(self, from_ts: str, to_ts: str, tz: str) -> str:
        template = self._get_query("fill_bids_by_positions")
        per_key_limit = 288
        return template.format(
            target_table=TARGET_TABLE,
            from_ts=_esc(from_ts),
            to_ts=_esc(to_ts),
            tz=_esc(tz),
            per_key_limit=per_key_limit,
        )
