"""Оркестратор инкремента статистики полок Auto-РК (рекомендации минус поиск).

Паттерн как у increment_fact_data_manager: snapshot → prev → delta → interval в CH.
Формула метрик: recommendations_stat = total_auto_stat - keyword_stat.
Сегментация: nmid, bid_minor (recommendations_bid_kopecks), price_minor/currency, mode.
В текущей v1-итерации цена пишется как unknown (price_minor=None) намеренно.
"""

from __future__ import annotations

import logging
import socket
import uuid
from datetime import datetime
from zoneinfo import ZoneInfo

from app.core.di.wb_manager_hub import WBManagerHub
from app.core.redis_manager_v2.redis_client import RedisClient
from app.modules.shop_runner.service_manager.services.increment_fact_data_manager.bucket_calculator import (
    BucketCalculator,
)
from app.modules.shop_runner.service_manager.services.increment_fact_data_manager.redis_lock_manager import (
    RedisLockManager,
)
from app.modules.shop_runner.service_manager.services.increment_fact_data_manager.version_calculator import (
    VersionCalculator,
)
from app.modules.shop_runner.service_manager.wb_shop_data_manager.dto.complex_adv import (
    ComplexAdv,
)

from .auto_shelf_bid_repository import AutoShelfBidRepository
from .clickhouse_auto_shelf_bid_writer import ClickHouseAutoShelfBidWriter
from .dto import AutoShelfBidIntervalRow, AutoShelfBidSnapshot, AutoShelfRawStat
from .last_auto_shelf_bid_state_manager import LastAutoShelfBidStateManager
from .redis_auto_recommendations_bid_value_manager import (
    RedisAutoRecommendationsBidValueManager,
)

logger = logging.getLogger(__name__)

LOCK_TTL = 120


class AutoShelfBidIncrementManager:
    """Считает и пишет инкременты полок для одного nmid на ComplexAdv (v1: ровно один nmid)."""

    def __init__(
        self,
        redis_client: RedisClient,
        wb_manager_hub: WBManagerHub,
        bucket_calculator: BucketCalculator | None = None,
        version_calculator: VersionCalculator | None = None,
        repository: AutoShelfBidRepository | None = None,
        lock_manager: RedisLockManager | None = None,
        writer: ClickHouseAutoShelfBidWriter | None = None,
        auto_recommendations_bid_cache_manager: RedisAutoRecommendationsBidValueManager | None = None,
        lock_ttl: int = LOCK_TTL,
    ) -> None:
        """Собирает зависимости; lock_ttl ограничен диапазоном 60–180 с."""
        self._bucket_calculator = bucket_calculator or BucketCalculator()
        self._version_calculator = version_calculator or VersionCalculator()
        self._repository = repository or AutoShelfBidRepository(
            wb_manager_hub=wb_manager_hub,
            auto_recommendations_bid_cache_manager=auto_recommendations_bid_cache_manager,
        )
        self._writer = writer or ClickHouseAutoShelfBidWriter()
        self._last_state_manager = LastAutoShelfBidStateManager(
            redis_client=redis_client,
            repository=self._repository,
            writer=self._writer,
        )
        self._lock_manager = lock_manager or RedisLockManager(redis_client)
        self._lock_ttl = min(max(lock_ttl, 60), 180)
        self._tz = ZoneInfo("Europe/Moscow")
        hostname = socket.gethostname()
        self._writer_id = f"{hostname}:{uuid.uuid4().hex[:8]}"

    async def update(self, complex_adv: ComplexAdv) -> None:
        """Один проход инкремента: CH stat → snapshot → lock → delta/interval/prev.

        Побочные эффекты: ClickHouse (intervals, prev), Redis (lock, last state).
        Цена в v1 не вычисляется из внешнего источника: snapshot пишется с price_minor=None.
        """
        nmids = complex_adv.nmids
        if not nmids:
            self._log_contract_event(
                "auto_shelf_bid_single_nmid_guard_skip",
                reason="single_nmid_guard_empty",
                nmid=None,
                mode=None,
                bid_minor=None,
                currency=None,
                price_minor=None,
                price_currency=None,
                bucket_start=None,
                level=logging.WARNING,
            )
            return
        if len(nmids) > 1:
            self._log_contract_event(
                "auto_shelf_bid_single_nmid_guard_skip",
                reason="single_nmid_guard_multiple",
                nmid=None,
                mode=None,
                bid_minor=None,
                currency=None,
                price_minor=None,
                price_currency=None,
                bucket_start=None,
                level=logging.WARNING,
            )
            return
        nmid = nmids[0]
        auto_adv_id = complex_adv.auto_adv_id

        src_ts = datetime.now(self._tz)
        bucket_start = self._bucket_calculator.calc_bucket_start(src_ts)
        version = self._version_calculator.calc_version(src_ts)

        try:
            shop_uuid = uuid.UUID(complex_adv.shop_id)
        except Exception:
            logger.warning(
                "auto_shelf_bid_invalid_shop_id adv_id=%s shop_id=%s",
                complex_adv.adv_id,
                complex_adv.shop_id,
            )
            return

        lock_key = self._build_lock_key(shop_uuid, nmid, bucket_start)
        lock_value = f"{self._writer_id}:{uuid.uuid4().hex[:6]}"

        try:
            total_auto_stat = await self._repository.fetch_total_auto_stat(auto_adv_id)
        except Exception:
            logger.exception(
                "auto_shelf_bid_total_auto_stat_fetch_error nmid=%s auto_adv_id=%s",
                nmid,
                auto_adv_id,
            )
            return
        if total_auto_stat is None:
            self._log_contract_event(
                "auto_shelf_bid_total_auto_stat_not_found",
                reason="no_total_stat",
                nmid=nmid,
                mode=None,
                bid_minor=None,
                currency=None,
                price_minor=None,
                price_currency=None,
                bucket_start=bucket_start,
                level=logging.WARNING,
            )
            return

        try:
            keyword_stat = await self._repository.fetch_keyword_stat(auto_adv_id, nmid)
        except Exception:
            logger.exception(
                "auto_shelf_bid_keyword_stat_fetch_error nmid=%s auto_adv_id=%s",
                nmid,
                auto_adv_id,
            )
            return
        if keyword_stat is None:
            self._log_contract_event(
                "auto_shelf_bid_keyword_stat_not_found_use_zero",
                reason="keyword_stat_missing_use_zero",
                nmid=nmid,
                mode=None,
                bid_minor=None,
                currency=None,
                price_minor=None,
                price_currency=None,
                bucket_start=bucket_start,
            )
            keyword_stat = AutoShelfRawStat.zero()

        recommendations_stat = total_auto_stat.minus(keyword_stat)
        if recommendations_stat.has_negative_values():
            self._log_contract_event(
                "auto_shelf_bid_negative_recommendations",
                reason="negative_recommendations_skipped",
                nmid=nmid,
                mode=None,
                bid_minor=None,
                currency=None,
                price_minor=None,
                price_currency=None,
                bucket_start=bucket_start,
                level=logging.WARNING,
            )
            return

        bid_minor = await self._repository.fetch_current_auto_common_bid(complex_adv, nmid)
        if bid_minor is None:
            self._log_contract_event(
                "auto_shelf_bid_no_bid",
                reason="no_bid",
                nmid=nmid,
                mode=None,
                bid_minor=None,
                currency=None,
                price_minor=None,
                price_currency=None,
                bucket_start=bucket_start,
                level=logging.WARNING,
            )
            return

        mode = await self._repository.get_current_mode(nmid)
        if not mode:
            mode = "main"

        # В v1 цену намеренно не тянем: пишем unknown, чтобы не блокировать поток инкрементов.
        price_minor = None
        price_currency = "RUB"

        current_snapshot = AutoShelfBidSnapshot(
            nmid=nmid,
            src_ts=src_ts,
            mode=mode,
            bid_minor=bid_minor,
            currency="RUB",
            price_minor=price_minor,
            price_currency=price_currency,
            impressions=recommendations_stat.impressions,
            clicks=recommendations_stat.clicks,
            carts=recommendations_stat.carts,
            orders=recommendations_stat.orders,
            spend=recommendations_stat.spend,
            version=version,
            bucket_start=bucket_start,
        )

        lock_acquired = await self._lock_manager.acquire(
            lock_key, lock_value, self._lock_ttl
        )
        if not lock_acquired:
            logger.info(
                "auto_shelf_bid_lock_skipped nmid=%s bucket=%s writer_id=%s",
                nmid,
                bucket_start,
                self._writer_id,
            )
            return

        logger.info(
            "auto_shelf_bid_lock_acquired nmid=%s bucket=%s writer_id=%s",
            nmid,
            bucket_start,
            self._writer_id,
        )
        try:
            prev_snapshot, _ = await self._last_state_manager.get(nmid)
            if prev_snapshot is None:
                await self._last_state_manager.persist(current_snapshot)
                self._log_contract_event(
                    "auto_shelf_bid_prev_missing_initialized",
                    reason="prev_missing_initialized",
                    nmid=nmid,
                    mode=current_snapshot.mode,
                    bid_minor=current_snapshot.bid_minor,
                    currency=current_snapshot.currency,
                    price_minor=current_snapshot.price_minor,
                    price_currency=current_snapshot.price_currency,
                    bucket_start=bucket_start,
                )
                return

            context_changed, changed_fields = self._is_context_changed(
                prev_snapshot,
                current_snapshot,
            )
            if context_changed:
                await self._last_state_manager.persist(current_snapshot)
                self._log_contract_event(
                    "auto_shelf_bid_context_changed_resync",
                    reason="context_changed_resync",
                    nmid=nmid,
                    mode=current_snapshot.mode,
                    bid_minor=current_snapshot.bid_minor,
                    currency=current_snapshot.currency,
                    price_minor=current_snapshot.price_minor,
                    price_currency=current_snapshot.price_currency,
                    bucket_start=bucket_start,
                )
                if "price_minor" in changed_fields or "price_currency" in changed_fields:
                    self._log_contract_event(
                        "auto_shelf_bid_price_changed",
                        reason="price_changed_resync",
                        nmid=nmid,
                        mode=current_snapshot.mode,
                        bid_minor=current_snapshot.bid_minor,
                        currency=current_snapshot.currency,
                        price_minor=current_snapshot.price_minor,
                        price_currency=current_snapshot.price_currency,
                        bucket_start=bucket_start,
                    )
                return

            delta = current_snapshot.delta(prev_snapshot)
            if delta.has_negative_values():
                await self._last_state_manager.persist(current_snapshot)
                self._log_contract_event(
                    "auto_shelf_bid_negative_delta_skipped",
                    reason="negative_delta_skipped",
                    nmid=nmid,
                    mode=current_snapshot.mode,
                    bid_minor=current_snapshot.bid_minor,
                    currency=current_snapshot.currency,
                    price_minor=current_snapshot.price_minor,
                    price_currency=current_snapshot.price_currency,
                    bucket_start=bucket_start,
                    level=logging.WARNING,
                )
                return

            if delta.nonzero_count() == 0:
                await self._last_state_manager.persist(current_snapshot)
                self._log_contract_event(
                    "auto_shelf_bid_zero_delta_skipped",
                    reason="zero_delta_skipped",
                    nmid=nmid,
                    mode=current_snapshot.mode,
                    bid_minor=current_snapshot.bid_minor,
                    currency=current_snapshot.currency,
                    price_minor=current_snapshot.price_minor,
                    price_currency=current_snapshot.price_currency,
                    bucket_start=bucket_start,
                )
                return

            row = AutoShelfBidIntervalRow(
                event_date=current_snapshot.src_ts.date(),
                event_id=current_snapshot.event_id(),
                src_ts=current_snapshot.src_ts,
                bucket_start=current_snapshot.bucket_start,
                version=current_snapshot.version,
                nmid=current_snapshot.nmid,
                mode=current_snapshot.mode,
                bid_minor=current_snapshot.bid_minor,
                currency=current_snapshot.currency,
                price_minor=current_snapshot.price_minor,
                price_currency=current_snapshot.price_currency,
                delta_impressions=delta.delta_impressions,
                delta_clicks=delta.delta_clicks,
                delta_carts=delta.delta_carts,
                delta_orders=delta.delta_orders,
                delta_spend=delta.delta_spend,
            )
            await self._writer.insert_interval(row)
            await self._last_state_manager.persist(current_snapshot)
            self._log_contract_event(
                "auto_shelf_bid_insert_ok",
                reason="insert_ok",
                nmid=nmid,
                mode=current_snapshot.mode,
                bid_minor=current_snapshot.bid_minor,
                currency=current_snapshot.currency,
                price_minor=current_snapshot.price_minor,
                price_currency=current_snapshot.price_currency,
                bucket_start=bucket_start,
            )
        except Exception:
            logger.exception(
                "auto_shelf_bid_insert_error nmid=%s bucket=%s version=%s",
                nmid,
                bucket_start,
                version,
            )
        finally:
            await self._lock_manager.release(lock_key, lock_value)

    @staticmethod
    def _build_lock_key(shop_id: uuid.UUID, nmid: int, bucket_start: datetime) -> str:
        """Ключ Redis-lock на shop + nmid + 5-минутный bucket."""
        bucket_epoch = int(bucket_start.timestamp())
        return f"lock:auto_shelf_bid:{shop_id}:{nmid}:{bucket_epoch}"

    @staticmethod
    def _is_context_changed(
        prev_snapshot: AutoShelfBidSnapshot,
        current_snapshot: AutoShelfBidSnapshot,
    ) -> tuple[bool, list[str]]:
        """Проверить смену контекста наблюдения до расчета дельты."""
        fields = (
            "bid_minor",
            "currency",
            "mode",
            "price_minor",
            "price_currency",
        )
        changed_fields = [
            field
            for field in fields
            if getattr(prev_snapshot, field) != getattr(current_snapshot, field)
        ]
        return bool(changed_fields), changed_fields

    @staticmethod
    def _log_contract_event(
        event_name: str,
        *,
        reason: str,
        nmid: int | None,
        mode: str | None,
        bid_minor: int | None,
        currency: str | None,
        price_minor: int | None,
        price_currency: str | None,
        bucket_start: datetime | None,
        level: int = logging.INFO,
    ) -> None:
        """Structured-log событий data quality контракта."""
        logger.log(
            level,
            "%s reason=%s nmid=%s mode=%s bid_minor=%s currency=%s price_minor=%s price_currency=%s bucket_start=%s",
            event_name,
            reason,
            nmid,
            mode,
            bid_minor,
            currency,
            price_minor,
            price_currency,
            bucket_start,
        )
