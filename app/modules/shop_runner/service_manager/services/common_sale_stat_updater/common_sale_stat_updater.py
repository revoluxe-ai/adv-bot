"""Сбор и запись common-sale stats в ClickHouse (shared E/U engine)."""

from __future__ import annotations

import logging
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from enum import StrEnum
from zoneinfo import ZoneInfo

from app.core.di.wb_manager_hub import WBManagerHub
from app.core.mp.wb.api.adapter.analitika_i_dannye_client.voronka_prodazh.post_sales_funnel_products_history.dto import (
    CommonSaleStatRow,
)
from app.core.mp.wb.api.excs import ApiForbiddenError as MpApiForbiddenError
from app.core.wb_api.exceptions import ApiForbiddenError as LegacyApiForbiddenError
from app.modules.shop_runner.service_manager.services.shop_wide_common_sales.collect_types import (
    CollectContext,
    CommonSaleCollectResult,
    nmids_with_full_window,
)
from app.modules.shop_runner.service_manager.services.shop_wide_common_sales.fact_validator import (
    validate_and_deduplicate_rows,
)
from app.modules.shop_runner.service_manager.wb_shop_data_manager.dto.complex_adv import (
    ComplexAdv,
)

from .clickhouse_common_stat_manager import ClickHouseCommonStatManager

logger = logging.getLogger(__name__)
MSK = ZoneInfo("Europe/Moscow")
BATCH_SIZE = 20
_API_FORBIDDEN_ERRORS = (LegacyApiForbiddenError, MpApiForbiddenError)


class _FunnelCollectPolicy(StrEnum):
    """Политика shared engine: legacy fail-fast vs strict bounded."""

    LEGACY_FAIL_FAST = "legacy_fail_fast"
    STRICT_BOUNDED = "strict_bounded"


@dataclass
class _FunnelEngineResult:
    """Внутренний результат shared chunk+API+validation engine."""

    rows: list[CommonSaleStatRow] = field(
        default_factory=lambda: list[CommonSaleStatRow]()
    )
    returned_pairs: set[tuple[int, date]] = field(
        default_factory=lambda: set[tuple[int, date]]()
    )
    persisted_pairs: set[tuple[int, date]] = field(
        default_factory=lambda: set[tuple[int, date]]()
    )
    rejected_count: int = 0
    failed_nmids: set[int] = field(default_factory=lambda: set[int]())
    ch_insert_failed: bool = False


class CommonSaleStatUpdater:
    """Движок collect+insert для legacy E и shop-wide U/E маршрутов."""

    def __init__(
        self,
        wb_manager_hub: WBManagerHub,
        clickhouse_manager: ClickHouseCommonStatManager,
    ) -> None:
        self._wb_manager_hub = wb_manager_hub
        self._clickhouse_manager = clickhouse_manager

    async def update_last_week_stats(
        self,
        complex_advs: list[ComplexAdv],
    ) -> set[int]:
        """
        Legacy public wrapper: ComplexAdv-only, fail-fast на API chunk, return set[int].

        Сохраняет контракт stage: raise до insert при ошибке chunk; insert всех rows.
        """
        if not complex_advs:
            return set()

        resolved_nmids = sorted({adv.main_nmid for adv in complex_advs})
        if not resolved_nmids:
            return set()

        today = datetime.now(MSK).date()
        window_start = today - timedelta(days=6)
        window_end = today

        engine = await self._run_funnel_collect_engine(
            resolved_nmids,
            window_start=window_start,
            window_end=window_end,
            policy=_FunnelCollectPolicy.LEGACY_FAIL_FAST,
        )
        if engine.rows:
            await self._clickhouse_manager.insert(engine.rows)
        return {row.nmid for row in engine.rows}

    async def collect_by_nmids(
        self,
        nmids: list[int],
        *,
        collect_context: CollectContext,
        before_first_api: Callable[[], Awaitable[None]] | None = None,
    ) -> CommonSaleCollectResult:
        """
        Strict shop-wide primitive: per-chunk validation, bounded partial API failures.

        updated_nmids — только nmIDs с полным окном (7 MSK-дней) после успешного insert.
        persisted_pairs — только пары, реально записанные в CH.
        ApiForbidden/credential errors пробрасываются без swallow.
        """
        resolved_nmids = sorted(set(nmids))
        if not resolved_nmids:
            return CommonSaleCollectResult()

        engine = await self._run_funnel_collect_engine(
            resolved_nmids,
            window_start=collect_context.window_start,
            window_end=collect_context.window_end,
            policy=_FunnelCollectPolicy.STRICT_BOUNDED,
            before_first_api=before_first_api,
        )

        route_nmids = frozenset(resolved_nmids)
        updated: set[int] = set()

        if engine.ch_insert_failed:
            failed = set(route_nmids)
        elif engine.persisted_pairs:
            complete = nmids_with_full_window(
                engine.persisted_pairs,
                route_nmids,
                collect_context.window_start,
                collect_context.window_end,
            )
            updated.update(complete)
            failed = set(route_nmids - complete)
        else:
            failed = set(route_nmids)

        return CommonSaleCollectResult(
            updated_nmids=frozenset(updated),
            failed_nmids=frozenset(failed),
            returned_pairs=frozenset(engine.returned_pairs),
            persisted_pairs=frozenset(engine.persisted_pairs),
            rejected_pair_count=engine.rejected_count,
            ch_insert_failed=engine.ch_insert_failed,
        )

    async def _run_funnel_collect_engine(
        self,
        nmids: list[int],
        *,
        window_start: date,
        window_end: date,
        policy: _FunnelCollectPolicy,
        before_first_api: Callable[[], Awaitable[None]] | None = None,
    ) -> _FunnelEngineResult:
        """
        Shared chunk+API engine для legacy и strict маршрутов.

        Legacy: без валидации, fail-fast raise на chunk error, insert снаружи.
        Strict: per-chunk validation, partial API failures, insert внутри engine.
        """
        result = _FunnelEngineResult()
        route_nmids = frozenset(nmids)
        api_started = False

        for chunk in _chunked(nmids, size=BATCH_SIZE):
            chunk_set = frozenset(chunk)
            if not chunk_set <= route_nmids:
                if policy == _FunnelCollectPolicy.STRICT_BOUNDED:
                    result.failed_nmids.update(chunk)
                continue

            if before_first_api is not None and not api_started:
                await before_first_api()
                api_started = True

            try:
                raw_rows = await self._wb_manager_hub.wb_data_manager.get_sales_funnel_products_history(
                    nmids=chunk,
                    start=window_start,
                    end=window_end,
                )
            except _API_FORBIDDEN_ERRORS:
                raise
            except Exception:
                logger.exception("Ошибка обновления общей воронки batch=%s", chunk)
                if policy == _FunnelCollectPolicy.LEGACY_FAIL_FAST:
                    raise
                result.failed_nmids.update(chunk)
                continue

            if policy == _FunnelCollectPolicy.LEGACY_FAIL_FAST:
                result.rows.extend(raw_rows)
                continue

            chunk_context = CollectContext(
                attempted_nmids=chunk_set,
                window_start=window_start,
                window_end=window_end,
            )
            validated = validate_and_deduplicate_rows(
                raw_rows,
                context=chunk_context,
            )
            result.rejected_count += validated.rejected_count
            result.returned_pairs.update(validated.returned_pairs)
            result.rows.extend(validated.rows)

        if policy == _FunnelCollectPolicy.LEGACY_FAIL_FAST:
            return result

        if result.rows:
            result.persisted_pairs = {(row.nmid, row.day) for row in result.rows}
            try:
                await self._clickhouse_manager.insert(result.rows)
            except Exception:
                logger.exception("CH insert failed for common sale stats")
                result.ch_insert_failed = True
                result.persisted_pairs.clear()
        else:
            result.failed_nmids.update(route_nmids)

        if result.ch_insert_failed:
            result.failed_nmids.update(route_nmids)

        return result


def _chunked(items: list[int], size: int) -> list[list[int]]:
    return [items[i : i + size] for i in range(0, len(items), size)]
