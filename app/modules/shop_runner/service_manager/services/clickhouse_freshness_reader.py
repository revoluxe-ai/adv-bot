"""Read last-update timestamps from ClickHouse tables for stats freshness guard."""

from __future__ import annotations

import logging
from datetime import date, datetime, timezone

from app.utils.ch_semaphore import anti_ch_crash_semaphore
from app.utils.click_house.client import get_clickhouse_client

from app.modules.shop_runner.service_manager.wb_shop_data_manager.dto.complex_adv import (
    ComplexAdv,
)

logger = logging.getLogger(__name__)


def _version_to_utc_dt(version: float) -> datetime:
    return datetime.fromtimestamp(version, tz=timezone.utc)


def _date_to_utc_eod(d: date) -> datetime:
    """Interpret date as end-of-day UTC for freshness comparison."""
    return datetime.combine(d, datetime.max.time().replace(microsecond=0), tzinfo=timezone.utc)


class ClickHouseStatsFreshnessReader:
    """Returns last-update datetimes from CH tables written by the three stats coroutines."""

    async def get_common_updated_at(self, complex_adv: ComplexAdv) -> datetime | None:
        """Last write to wb_common_stat for complex_adv.main_nmid (from update_common_sale_stat)."""
        nmid = complex_adv.main_nmid
        query = """
            SELECT max(version) AS mv
            FROM default_db.wb_common_stat
            WHERE nmid = %(nmid)s
        """
        try:
            async with anti_ch_crash_semaphore:
                async with get_clickhouse_client() as client:
                    result = await client.query(query, parameters={"nmid": nmid})
                    rows = result.result_rows
                    if not rows or rows[0][0] is None:
                        return None
                    return _version_to_utc_dt(float(rows[0][0]))
        except Exception:
            logger.exception("get_common_updated_at failed for nmid=%s", nmid)
            return None

    async def get_full_adv_updated_at(self, complex_adv: ComplexAdv) -> datetime | None:
        """Latest write among all_adv_ids in full_adv_wb_stat (from update_full_adv_stat).
        Fresh if at least one adv_id has data."""
        adv_ids = list(complex_adv.all_adv_ids)
        if not adv_ids:
            return None
        query = """
            SELECT max(max_version) AS max_mv
            FROM (
                SELECT adv_id, max(version) AS max_version
                FROM default_db.full_adv_wb_stat
                WHERE adv_id IN %(adv_ids)s
                GROUP BY adv_id
            )
        """
        try:
            async with anti_ch_crash_semaphore:
                async with get_clickhouse_client() as client:
                    result = await client.query(query, parameters={"adv_ids": adv_ids})
                    rows = result.result_rows
                    if not rows or rows[0][0] is None:
                        return None
                    return _version_to_utc_dt(float(rows[0][0]))
        except Exception:
            logger.exception("get_full_adv_updated_at failed for adv_ids=%s", adv_ids)
            return None

    async def get_cluster_updated_at(self, complex_adv: ComplexAdv) -> datetime | None:
        """Latest write (max date) among all_adv_ids in clusters_adv_stats.
        Table has no timestamp column, only date. Fresh if at least one adv_id has data."""
        adv_ids = list(complex_adv.all_adv_ids)
        if not adv_ids:
            return None
        query = """
            SELECT timestamp
                FROM default_db.clusters_adv_stats
      WHERE adv_id IN %(adv_ids)s
      ORDER BY timestamp DESC
      LIMIT 1


        """
        try:
            async with anti_ch_crash_semaphore:
                async with get_clickhouse_client() as client:
                    result = await client.query(query, parameters={"adv_ids": adv_ids})
                    rows = result.result_rows
                    if not rows or rows[0][0] is None:
                        return None
                    val = rows[0][0]
                    if isinstance(val, date) and not isinstance(val, datetime):
                        return _date_to_utc_eod(val)
                    if isinstance(val, datetime):
                        return val if val.tzinfo else val.replace(tzinfo=timezone.utc)
                    return None
        except Exception:
            logger.exception("get_cluster_updated_at failed for adv_ids=%s", adv_ids)
            return None
