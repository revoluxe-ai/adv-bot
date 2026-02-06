from __future__ import annotations

import logging
import socket
import time
import uuid
from datetime import date, datetime, timezone
from uuid import UUID
from zoneinfo import ZoneInfo

from app.core.redis_manager_v2.redis_client import RedisClient
from app.modules.shop_runner.service_manager.wb_shop_data_manager import ComplexAdv

from .bucket_calculator import BucketCalculator
from .clickhouse_fact_stat_writer import ClickHouseFactStatWriter
from .dto import FactStatRow
from .dto.fact_stat_snapshot import FactStatSnapshot
from .fact_stat_repository import FactStatRepository
from .last_state_manager import LastStateManager
from .redis_lock_manager import RedisLockManager
from .version_calculator import VersionCalculator

logger = logging.getLogger(__name__)

LOCK_TTL = 120


class IncrementFactDataManager:
    def __init__(
        self,
        redis_client: RedisClient,
        bucket_calculator: BucketCalculator | None = None,
        version_calculator: VersionCalculator | None = None,
        stat_repository: FactStatRepository | None = None,
        lock_manager: RedisLockManager | None = None,
        writer: ClickHouseFactStatWriter | None = None,
        lock_ttl: int = LOCK_TTL,
    ) -> None:
        self._bucket_calculator = bucket_calculator or BucketCalculator()
        self._version_calculator = version_calculator or VersionCalculator()
        self._stat_repository = stat_repository or FactStatRepository()
        self._lock_manager = lock_manager or RedisLockManager(redis_client)
        self._writer = writer or ClickHouseFactStatWriter()
        self._tz = ZoneInfo("Europe/Moscow")
        self._last_state_manager = LastStateManager(redis_client, self._stat_repository)
        self._lock_ttl = min(max(lock_ttl, 60), 180)
        hostname = socket.gethostname()
        self._writer_id = f"{hostname}:{uuid.uuid4().hex[:8]}"

    async def update(self, complex_adv: ComplexAdv) -> None:
        shop_id = complex_adv.shop_id
        shop_uuid = uuid.UUID(shop_id)
        complex_adv_id = complex_adv.adv_id
        nmids = complex_adv.nmids
        adv_ids = list(complex_adv.all_adv_ids)

        src_ts = datetime.now(ZoneInfo("Europe/Moscow"))
        bucket_start = self._bucket_calculator.calc_bucket_start(src_ts)
        version = self._version_calculator.calc_version(src_ts)
        lock_key = self._build_lock_key(shop_uuid, complex_adv_id, bucket_start)
        lock_value = f"{self._writer_id}:{uuid.uuid4().hex[:6]}"

        try:
            current_snapshot: FactStatSnapshot | None = await self._stat_repository.fetch_current_snapshot(
                shop_uuid,
                complex_adv_id,
                bucket_start,
                src_ts,
                version,
                nmids,
                adv_ids,
            )
        except Exception:
            logger.exception(
                "fact15m_wb_fetch_error shop_id=%s complex_adv_id=%s",
                shop_id,
                complex_adv_id,
            )
            return None

        if current_snapshot is None:
            logger.info(
                "fact15m_no_data shop_id=%s complex_adv_id=%s bucket=%s",
                shop_id,
                complex_adv_id,
                bucket_start,
            )
            return None

        lock_acquired = await self._lock_manager.acquire(
            lock_key, lock_value, self._lock_ttl
        )
        if not lock_acquired:
            logger.info(
                "fact15m_lock_skipped shop_id=%s complex_adv_id=%s bucket=%s writer_id=%s",
                shop_id,
                complex_adv_id,
                bucket_start,
                self._writer_id,
            )
            return None

        logger.info(
            "fact15m_lock_acquired shop_id=%s complex_adv_id=%s bucket=%s writer_id=%s",
            shop_id,
            complex_adv_id,
            bucket_start,
            self._writer_id,
        )

        try:
            prev_snapshot, prev_source = await self._last_state_manager.get(
                str(shop_uuid), complex_adv_id
            )

            if prev_snapshot is None:
                await self._last_state_manager.persist(current_snapshot)
                logger.info(
                    "fact15m_init_state shop_id=%s complex_adv_id=%s bucket=%s prev_source=%s",
                    shop_id,
                    complex_adv_id,
                    bucket_start,
                    prev_source,
                )
                return None

            if prev_snapshot.src_ts.date() != current_snapshot.src_ts.date():
                await self._last_state_manager.persist(current_snapshot)
                await self._ensure_zero_interval_recorded(
                    shop_uuid, complex_adv_id, current_snapshot
                )
                logger.info(
                    "fact15m_reset_day shop_id=%s complex_adv_id=%s bucket=%s prev_source=%s reset_day=true",
                    shop_id,
                    complex_adv_id,
                    bucket_start,
                    prev_source,
                )
                return None

            delta = current_snapshot.delta(prev_snapshot)
            delta_nonzero = current_snapshot.delta_nonzero_count(prev_snapshot)
            if delta_nonzero == 0:
                await self._last_state_manager.persist(current_snapshot)
                logger.info(
                    "fact15m_insert_skip shop_id=%s complex_adv_id=%s bucket=%s prev_source=%s delta_nonzero_count=0",
                    shop_id,
                    complex_adv_id,
                    bucket_start,
                    prev_source,
                )
                return None

            row = FactStatRow(
                bucket_start=bucket_start,
                shop_id=shop_uuid,
                complex_adv_id=complex_adv_id,
                views_adv_sum=delta["views_adv_sum"],
                clicks_adv_sum=delta["clicks_adv_sum"],
                carts_adv_sum=delta["carts_adv_sum"],
                orders_adv_sum=delta["orders_adv_sum"],
                spend_adv_sum_rub=delta["spend_adv_sum_rub"],
                orders_sum_adv_rub=delta["orders_sum_adv_rub"],
                open_card_sum=delta["open_card_sum"],
                carts_card_sum=delta["carts_card_sum"],
                orders_card_sum=delta["orders_card_sum"],
                orders_sum_card_rub=delta["orders_sum_card_rub"],
                buy_outs_sum=delta["buy_outs_sum"],
                src_ts=current_snapshot.src_ts,
                version=current_snapshot.version,
                event_date=current_snapshot.src_ts.date(),
                event_id=current_snapshot.event_id,
            )

            start = time.perf_counter()
            await self._writer.insert(row)
            latency = time.perf_counter() - start
            await self._last_state_manager.persist(current_snapshot)
            logger.info(
                "fact15m_ch_insert_ok shop_id=%s complex_adv_id=%s bucket=%s version=%s latency=%.03f prev_source=%s delta_nonzero_count=%d",
                shop_id,
                complex_adv_id,
                bucket_start,
                version,
                latency,
                prev_source,
                delta_nonzero,
            )
        except Exception:
            logger.exception(
                "fact15m_ch_insert_error shop_id=%s complex_adv_id=%s bucket=%s version=%s",
                shop_id,
                complex_adv_id,
                bucket_start,
                version,
            )
        finally:
            await self._lock_manager.release(lock_key, lock_value)

    @staticmethod
    def _build_lock_key(shop_id: uuid.UUID, complex_adv_id: int, bucket_start: datetime
    ) -> str:
        bucket_epoch = int(bucket_start.timestamp())
        return f"lock:fact:{shop_id}:{complex_adv_id}:{bucket_epoch}"

    def _to_moscow_time(self, src_ts: datetime) -> datetime:
        if src_ts.tzinfo is None:
            src_ts = src_ts.replace(tzinfo=timezone.utc)
        return src_ts.astimezone(self._tz)

    def _snapshot_date(self, snapshot: FactStatSnapshot) -> date:
        return self._to_moscow_time(snapshot.src_ts).date()

    def _start_of_day(self, src_ts: datetime) -> datetime:
        localized = self._to_moscow_time(src_ts)
        return localized.replace(hour=0, minute=0, second=0, microsecond=0)

    @staticmethod
    def _build_zero_interval_row(
        bucket_start: datetime, snapshot: FactStatSnapshot
    ) -> FactStatRow:
        return FactStatRow(
            bucket_start=bucket_start,
            shop_id=snapshot.shop_id,
            complex_adv_id=snapshot.complex_adv_id,
            views_adv_sum=snapshot.views_adv_sum,
            clicks_adv_sum=snapshot.clicks_adv_sum,
            carts_adv_sum=snapshot.carts_adv_sum,
            orders_adv_sum=snapshot.orders_adv_sum,
            spend_adv_sum_rub=snapshot.spend_adv_sum_rub,
            orders_sum_adv_rub=snapshot.orders_sum_adv_rub,
            open_card_sum=snapshot.open_card_sum,
            carts_card_sum=snapshot.carts_card_sum,
            orders_card_sum=snapshot.orders_card_sum,
            orders_sum_card_rub=snapshot.orders_sum_card_rub,
            buy_outs_sum=snapshot.buy_outs_sum,
            src_ts=snapshot.src_ts,
            version=snapshot.version,
        )

    async def _ensure_zero_interval_recorded(
        self, shop_id: UUID, complex_adv_id: int, snapshot: FactStatSnapshot
    ) -> None:
        current_date = self._snapshot_date(snapshot)
        shop_key = str(shop_id)
        if await self._last_state_manager.is_zero_interval_recorded(
            shop_key, complex_adv_id, current_date
        ):
            return
        bucket_start = self._start_of_day(snapshot.src_ts)
        if await self._stat_repository.has_zero_interval_record(
            shop_id, complex_adv_id, bucket_start
        ):
            await self._last_state_manager.set_zero_interval_recorded(
                shop_key, complex_adv_id, current_date
            )
            return
        row = self._build_zero_interval_row(bucket_start, snapshot)
        try:
            await self._writer.insert(row)
        except Exception:
            logger.exception(
                "fact15m_zero_interval_insert_error shop_id=%s complex_adv_id=%s bucket=%s version=%s",
                shop_id,
                complex_adv_id,
                bucket_start,
                snapshot.version,
            )
            return
        await self._last_state_manager.set_zero_interval_recorded(
            shop_key, complex_adv_id, current_date
        )
        logger.info(
            "fact15m_zero_interval_insert_ok shop_id=%s complex_adv_id=%s bucket=%s version=%s",
            shop_id,
            complex_adv_id,
            bucket_start,
            snapshot.version,
        )







