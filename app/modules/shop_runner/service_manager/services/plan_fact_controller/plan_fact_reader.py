"""Read latest plan/fact snapshots with Redis-first cache and bounded CH fallback."""

from __future__ import annotations

import json
import logging
import time
from collections.abc import Sequence
from dataclasses import asdict, dataclass
from datetime import UTC, datetime

from app.core.redis_manager_v2.redis_client import RedisClient
from app.modules.common_slaves.wildberries.models import AdvSetting
from app.modules.common_slaves.wildberries.models.fact_methods_enum import FactMethods
from app.modules.shop_runner.service_manager.old_modules.setting_auto_updater.data_classes import (
    FactData,
)
from app.utils.ch_semaphore import run_ch_with_timeout
from app.utils.click_house.client import get_clickhouse_client

logger = logging.getLogger(__name__)

# formatDateTime в CH: шаблон передаём через parameters (см. full_wb_adv_stat и др.),
# иначе символы % в литерале ломают bind_query clickhouse_connect (Python %).
# В CH с ~23.4 %M в formatDateTime — имя месяца (April), минуты — %i (не как в Python).
PLAN_FACT_CH_TS_FORMAT_MSK = "%d.%m.%Y %H:%i"
PLAN_FACT_CACHE_TTL_SECONDS = 15 * 60
PLAN_FACT_CH_FALLBACK_TIMEOUT_SECONDS = 15
_PLAN_FACT_CACHE_PREFIX = "adv_snapshot:v1:plan_fact:adv"


@dataclass
class PlanFactSummary:
    """Latest aggregated plan/fact row for one ``adv_id``."""

    adv_id: int
    fact_predict_orders: float | None
    fact_pay_for_order: float | None
    fact_original_orders: float | None = None
    fact_method: str | None = None
    # max(timestamp) по adv_id, строка уже в Europe/Moscow (как в консоли CH)
    plan_fact_ch_ts_msk: str | None = None
    plan_orders: int | None = None


class PlanFactCacheManager:
    """Redis cache for ``PlanFactSummary`` keyed by ``adv_id``."""

    def __init__(self, redis_client: RedisClient) -> None:
        self._client = redis_client

    @staticmethod
    def _get_key(adv_id: int) -> str:
        return f"{_PLAN_FACT_CACHE_PREFIX}:{adv_id}"

    @staticmethod
    def _serialize(summary: PlanFactSummary) -> str:
        payload = asdict(summary)
        payload["cached_at"] = datetime.now(tz=UTC).isoformat()
        return json.dumps(payload, ensure_ascii=False)

    @staticmethod
    def _deserialize(raw: str | bytes) -> PlanFactSummary:
        if isinstance(raw, bytes):
            raw = raw.decode()
        data = json.loads(raw)
        if not isinstance(data, dict):
            raise TypeError("plan_fact cache payload must be a JSON object")
        return PlanFactSummary(
            adv_id=PlanFactReader._as_int(data["adv_id"]), # pyright: ignore
            fact_predict_orders=PlanFactReader._as_float_or_none(  # pyright: ignore
                data.get("fact_predict_orders") # pyright: ignore
            ),
            fact_pay_for_order=PlanFactReader._as_float_or_none(  # pyright: ignore
                data.get("fact_pay_for_order") # pyright: ignore
            ),
            fact_original_orders=PlanFactReader._as_float_or_none( # pyright: ignore
                data.get("fact_original_orders")  # pyright: ignore
            ),
            fact_method=PlanFactReader._as_str_or_none(data.get("fact_method")), # pyright: ignore
            plan_fact_ch_ts_msk=PlanFactReader._as_str_or_none(  # pyright: ignore
                data.get("plan_fact_ch_ts_msk") # pyright: ignore
            ),
            plan_orders=(
                PlanFactReader._as_int(data["plan_orders"]) # pyright: ignore
                if data.get("plan_orders") is not None # pyright: ignore
                else None
            ),
        )

    async def get_many(
        self, adv_ids: Sequence[int]
    ) -> tuple[dict[int, PlanFactSummary], set[int]]:
        """Return cached summaries and invalid payload ids."""
        normalized_adv_ids = [int(adv_id) for adv_id in adv_ids]
        if not normalized_adv_ids:
            return {}, set()
        raw_list = await self._client.mget(
            [self._get_key(adv_id) for adv_id in normalized_adv_ids]
        )
        hits: dict[int, PlanFactSummary] = {}
        invalid_adv_ids: set[int] = set()
        for adv_id, raw in zip(normalized_adv_ids, raw_list, strict=True):
            if raw is None:
                continue
            try:
                hits[adv_id] = self._deserialize(raw)
            except (
                KeyError,
                TypeError,
                ValueError,
                json.JSONDecodeError,
            ):
                invalid_adv_ids.add(adv_id)
        return hits, invalid_adv_ids

    async def get_one(self, adv_id: int) -> tuple[PlanFactSummary | None, bool]:
        """Return cached summary and invalid-payload flag."""
        raw = await self._client.get(self._get_key(int(adv_id)))
        if raw is None:
            return None, False
        try:
            return self._deserialize(raw), False
        except (KeyError, TypeError, ValueError, json.JSONDecodeError):
            return None, True

    async def set_many(self, summaries: Sequence[PlanFactSummary]) -> int:
        """Persist summaries with the hard 15-minute TTL."""
        if not summaries:
            return 0
        async with self._client.write_pipeline() as pipe:
            for summary in summaries:
                pipe.set(
                    self._get_key(summary.adv_id),
                    self._serialize(summary),
                    ex=PLAN_FACT_CACHE_TTL_SECONDS,
                )
            await pipe.execute()
        return len(summaries)

    async def set_one(self, summary: PlanFactSummary) -> None:
        """Persist one summary with the hard 15-minute TTL."""
        await self._client.set(
            self._get_key(summary.adv_id),
            self._serialize(summary),
            ex=PLAN_FACT_CACHE_TTL_SECONDS,
        )

class PlanFactReader:
    """Redis-first latest plan/fact reader with bounded ClickHouse fallback."""

    def __init__(
        self,
        *,
        redis_client: RedisClient | None = None,
        cache_manager: PlanFactCacheManager | None = None,
    ) -> None:
        if cache_manager is not None:
            self._cache_manager = cache_manager
            return
        if redis_client is None:
            from app.modules.cluster_bids_redis.redis_client_provider import (
                get_redis_client,
            )

            redis_client = get_redis_client()
        self._cache_manager = PlanFactCacheManager(redis_client)

    @staticmethod
    def _load_query() -> str:
        from pathlib import Path

        sql_path = (
            Path(__file__)
            .parent
            .joinpath("sql", "get_latest_plan_fact.sql")
        )
        return sql_path.read_text(encoding="utf-8")

    @staticmethod
    def _as_int(value: object) -> int:
        if isinstance(value, bool):
            return int(value)
        if isinstance(value, int):
            return int(value)
        if isinstance(value, float):
            if not value.is_integer():
                raise TypeError(
                    f"Expected integer-like float value, got {value!r}"
                )
            return int(value)
        if isinstance(value, str):
            raw = value.strip()
            if raw.startswith(("+", "-")):
                sign, digits = raw[0], raw[1:]
                if digits.isdigit():
                    return int(f"{sign}{digits}")
            elif raw.isdigit():
                return int(raw)
            raise TypeError(f"Expected integer-like string value, got {value!r}")
        raise TypeError(f"Expected int-convertible value, got {type(value)!r}")

    @staticmethod
    def _as_float_or_none(value: object) -> float | None:
        if value is None:
            return None
        if isinstance(value, bool):
            return float(value)
        if isinstance(value, int | float | str):
            return float(value)
        raise TypeError(f"Expected float-convertible value, got {type(value)!r}")

    @staticmethod
    def _as_str_or_none(value: object) -> str | None:
        if value is None:
            return None
        if isinstance(value, str):
            stripped = value.strip()
            return stripped if stripped else None
        return str(value)

    @staticmethod
    def _row_to_summary(row: Sequence[object]) -> PlanFactSummary:
        ts_raw = row[5] if len(row) > 5 else None
        return PlanFactSummary(
            adv_id=PlanFactReader._as_int(row[0]),
            fact_predict_orders=PlanFactReader._as_float_or_none(row[1]),
            fact_pay_for_order=PlanFactReader._as_float_or_none(row[2]),
            fact_original_orders=PlanFactReader._as_float_or_none(row[3]),
            fact_method=PlanFactReader._as_str_or_none(row[4]),
            plan_fact_ch_ts_msk=PlanFactReader._as_str_or_none(ts_raw),
        )

    async def _query_latest_plan_fact_from_clickhouse(
        self,
        adv_id: int,
    ) -> PlanFactSummary | None:
        query = self._load_query()

        async def _run_query() -> PlanFactSummary | None:
            async with get_clickhouse_client() as client:
                result = await client.query(
                    query,
                    parameters={
                        "adv_id": adv_id,
                        "plan_fact_ts_format": PLAN_FACT_CH_TS_FORMAT_MSK,
                    },
                )
            row = next(iter(result.result_rows), None)
            if not row:
                return None
            return self._row_to_summary(row)

        return await run_ch_with_timeout(
            _run_query(),
            timeout=PLAN_FACT_CH_FALLBACK_TIMEOUT_SECONDS,
        )

    async def _query_latest_plan_facts_from_clickhouse(
        self,
        adv_ids: list[int],
    ) -> dict[int, PlanFactSummary]:
        if not adv_ids:
            return {}
        normalized_adv_ids = sorted({int(adv_id) for adv_id in adv_ids})
        query = """
        SELECT
            adv_id,
            argMax(fact_predict_orders, timestamp) AS fact_predict_orders,
            argMax(fact_pay_for_order, timestamp) AS fact_pay_for_order,
            argMax(fact_original_orders, timestamp) AS fact_original_orders,
            argMax(fact_method, timestamp) AS fact_method,
            formatDateTime(max(timestamp), %(plan_fact_ts_format)s, 'Europe/Moscow') AS plan_fact_ch_ts_msk
        FROM default_db.plan_fact_stats
        WHERE adv_id IN %(adv_ids)s
        GROUP BY adv_id
        """

        async def _run_query() -> dict[int, PlanFactSummary]:
            async with get_clickhouse_client() as client:
                result = await client.query(
                    query,
                    parameters={
                        "adv_ids": normalized_adv_ids,
                        "plan_fact_ts_format": PLAN_FACT_CH_TS_FORMAT_MSK,
                    },
                )
            summaries: dict[int, PlanFactSummary] = {}
            for row in result.result_rows:
                summary = self._row_to_summary(row)
                summaries[summary.adv_id] = summary
            return summaries

        return await run_ch_with_timeout(
            _run_query(),
            timeout=PLAN_FACT_CH_FALLBACK_TIMEOUT_SECONDS,
        )

    async def _write_cache_many(
        self,
        summaries: Sequence[PlanFactSummary],
    ) -> None:
        if not summaries:
            return
        try:
            written = await self._cache_manager.set_many(summaries)
        except Exception as exc:  # noqa: BLE001
            logger.error(
                "plan_fact_cache_write_error adv_count=%s ttl_sec=%s exc_type=%s",
                len(summaries),
                PLAN_FACT_CACHE_TTL_SECONDS,
                type(exc).__name__,
                exc_info=True,
            )
            return
        logger.debug(
            "plan_fact_cache_write_success adv_count=%s ttl_sec=%s",
            written,
            PLAN_FACT_CACHE_TTL_SECONDS,
        )

    async def _write_cache_one(
        self,
        summary: PlanFactSummary,
    ) -> None:
        await self._write_cache_many([summary])

    async def refresh_cache_from_clickhouse(
        self,
        adv_ids: list[int],
    ) -> dict[int, PlanFactSummary]:
        """Read latest plan/fact directly from CH, then refresh Redis cache."""
        if not adv_ids:
            return {}
        adv_count = len({int(adv_id) for adv_id in adv_ids})
        started = time.perf_counter()
        logger.debug(
            "plan_fact_warmup_start adv_count=%s timeout_sec=%s",
            adv_count,
            PLAN_FACT_CH_FALLBACK_TIMEOUT_SECONDS,
        )
        try:
            summaries_by_adv_id = await self._query_latest_plan_facts_from_clickhouse(
                adv_ids
            )
        except TimeoutError:
            duration_ms = (time.perf_counter() - started) * 1000
            logger.warning(
                "plan_fact_warmup_timeout adv_count=%s duration_ms=%.2f timeout_sec=%s",
                adv_count,
                duration_ms,
                PLAN_FACT_CH_FALLBACK_TIMEOUT_SECONDS,
                exc_info=True,
            )
            return {}
        except Exception as exc:  # noqa: BLE001
            duration_ms = (time.perf_counter() - started) * 1000
            logger.error(
                "plan_fact_warmup_error adv_count=%s duration_ms=%.2f timeout_sec=%s exc_type=%s",
                adv_count,
                duration_ms,
                PLAN_FACT_CH_FALLBACK_TIMEOUT_SECONDS,
                type(exc).__name__,
                exc_info=True,
            )
            return {}
        duration_ms = (time.perf_counter() - started) * 1000
        logger.debug(
            "plan_fact_warmup_success adv_count=%s duration_ms=%.2f result_count=%s",
            adv_count,
            duration_ms,
            len(summaries_by_adv_id),
        )
        await self._write_cache_many(list(summaries_by_adv_id.values()))
        return summaries_by_adv_id

    async def get_latest_plan_fact(
        self, adv_id: int
    ) -> PlanFactSummary | None:
        """Возвращает последнюю запись план-факт по adv_id из ClickHouse.

        Для бизнес-логики используйте только факт:
        fact_predict_orders, fact_pay_for_order, fact_original_orders, fact_method
        (при сборке FactData из кеша). Целевые значения (plan/target/max)
        должны приходить из текущих настроек AdvSetting/PlanData.
        plan_fact_ch_ts_msk — max(timestamp) по adv_id, отформатированный в CH в Europe/Moscow.
        """
        started = time.perf_counter()
        cached_summary, invalid_payload = await self._cache_manager.get_one(adv_id)
        if cached_summary is not None:
            duration_ms = (time.perf_counter() - started) * 1000
            logger.debug(
                "plan_fact_cache_hit adv_id=%s hit_count=1 miss_count=0 duration_ms=%.2f",
                adv_id,
                duration_ms,
            )
            return cached_summary
        if invalid_payload:
            logger.warning(
                "plan_fact_cache_invalid adv_id=%s adv_count=1 hit_count=0 miss_count=1",
                adv_id,
            )
        logger.debug(
            "plan_fact_cache_miss adv_id=%s adv_count=1 hit_count=0 miss_count=1",
            adv_id,
        )
        logger.debug(
            "plan_fact_clickhouse_fallback_start adv_id=%s adv_count=1 timeout_sec=%s",
            adv_id,
            PLAN_FACT_CH_FALLBACK_TIMEOUT_SECONDS,
        )
        try:
            summary = await self._query_latest_plan_fact_from_clickhouse(adv_id)
        except TimeoutError:
            duration_ms = (time.perf_counter() - started) * 1000
            logger.warning(
                "plan_fact_clickhouse_fallback_timeout adv_id=%s adv_count=1 duration_ms=%.2f timeout_sec=%s",
                adv_id,
                duration_ms,
                PLAN_FACT_CH_FALLBACK_TIMEOUT_SECONDS,
                exc_info=True,
            )
            return None
        except Exception as exc:  # noqa: BLE001
            duration_ms = (time.perf_counter() - started) * 1000
            logger.error(
                "plan_fact_clickhouse_fallback_error adv_id=%s adv_count=1 duration_ms=%.2f timeout_sec=%s exc_type=%s",
                adv_id,
                duration_ms,
                PLAN_FACT_CH_FALLBACK_TIMEOUT_SECONDS,
                type(exc).__name__,
                exc_info=True,
            )
            return None
        duration_ms = (time.perf_counter() - started) * 1000
        logger.debug(
            "plan_fact_clickhouse_fallback_success adv_id=%s adv_count=1 duration_ms=%.2f result_count=%s",
            adv_id,
            duration_ms,
            1 if summary is not None else 0,
        )
        if summary is not None:
            await self._write_cache_one(summary)
        return summary

    async def get_latest_plan_facts(
        self, adv_ids: list[int]
    ) -> dict[int, PlanFactSummary]:
        """Возвращает последние записи план-факт по списку adv_id из ClickHouse."""
        if not adv_ids:
            return {}
        normalized_adv_ids = sorted({int(adv_id) for adv_id in adv_ids})
        started = time.perf_counter()
        cached_hits, invalid_adv_ids = await self._cache_manager.get_many(
            normalized_adv_ids
        )
        if invalid_adv_ids:
            logger.warning(
                "plan_fact_cache_invalid adv_count=%s invalid_count=%s invalid_adv_ids=%s",
                len(normalized_adv_ids),
                len(invalid_adv_ids),
                sorted(invalid_adv_ids),
            )
        missing_adv_ids = [
            adv_id
            for adv_id in normalized_adv_ids
            if adv_id not in cached_hits or adv_id in invalid_adv_ids
        ]
        duration_ms = (time.perf_counter() - started) * 1000
        if not missing_adv_ids:
            logger.debug(
                "plan_fact_cache_hit adv_count=%s hit_count=%s miss_count=0 duration_ms=%.2f",
                len(normalized_adv_ids),
                len(cached_hits),
                duration_ms,
            )
            return cached_hits
        logger.debug(
            "plan_fact_cache_miss adv_count=%s hit_count=%s miss_count=%s duration_ms=%.2f",
            len(normalized_adv_ids),
            len(cached_hits),
            len(missing_adv_ids),
            duration_ms,
        )
        logger.debug(
            "plan_fact_clickhouse_fallback_start adv_count=%s hit_count=%s miss_count=%s timeout_sec=%s",
            len(normalized_adv_ids),
            len(cached_hits),
            len(missing_adv_ids),
            PLAN_FACT_CH_FALLBACK_TIMEOUT_SECONDS,
        )
        fallback_started = time.perf_counter()
        try:
            fallback_hits = await self._query_latest_plan_facts_from_clickhouse(
                missing_adv_ids
            )
        except TimeoutError:
            fallback_duration_ms = (time.perf_counter() - fallback_started) * 1000
            logger.warning(
                "plan_fact_clickhouse_fallback_timeout adv_count=%s hit_count=%s miss_count=%s duration_ms=%.2f timeout_sec=%s",
                len(normalized_adv_ids),
                len(cached_hits),
                len(missing_adv_ids),
                fallback_duration_ms,
                PLAN_FACT_CH_FALLBACK_TIMEOUT_SECONDS,
                exc_info=True,
            )
            return cached_hits
        except Exception as exc:  # noqa: BLE001
            fallback_duration_ms = (time.perf_counter() - fallback_started) * 1000
            logger.error(
                "plan_fact_clickhouse_fallback_error adv_count=%s hit_count=%s miss_count=%s duration_ms=%.2f timeout_sec=%s exc_type=%s",
                len(normalized_adv_ids),
                len(cached_hits),
                len(missing_adv_ids),
                fallback_duration_ms,
                PLAN_FACT_CH_FALLBACK_TIMEOUT_SECONDS,
                type(exc).__name__,
                exc_info=True,
            )
            return cached_hits
        fallback_duration_ms = (time.perf_counter() - fallback_started) * 1000
        logger.debug(
            "plan_fact_clickhouse_fallback_success adv_count=%s hit_count=%s miss_count=%s duration_ms=%.2f result_count=%s",
            len(normalized_adv_ids),
            len(cached_hits),
            len(missing_adv_ids),
            fallback_duration_ms,
            len(fallback_hits),
        )
        await self._write_cache_many(list(fallback_hits.values()))
        merged_hits = dict(cached_hits)
        merged_hits.update(fallback_hits)
        return merged_hits


def _resolve_fact_method_from_ch(
    method_str: str | None, adv_setting: AdvSetting
) -> FactMethods:
    if method_str:
        try:
            return FactMethods(method_str)
        except ValueError:
            logger.debug(
                "Неизвестный fact_method из plan_fact_stats: %s, берём из AdvSetting",
                method_str,
            )
    return adv_setting.sales_predict_method


def fact_data_from_plan_fact_summary(
    summary: PlanFactSummary | None,
    adv_setting: AdvSetting,
) -> FactData | None:
    """Собирает FactData из последнего снимка в ClickHouse (plan_fact_stats)."""
    if summary is None or summary.fact_predict_orders is None:
        return None
    predict = summary.fact_predict_orders
    original_src = (
        summary.fact_original_orders
        if summary.fact_original_orders is not None
        else predict
    )
    pay_for_order: float | None = None
    if summary.fact_pay_for_order is not None:
        pay_for_order = round(summary.fact_pay_for_order, 2)
    fact_method = _resolve_fact_method_from_ch(summary.fact_method, adv_setting)
    return FactData(
        predict_orders=round(predict, 2),
        original_orders=float(original_src),
        pay_for_order=pay_for_order,
        fact_method=fact_method,
    )
