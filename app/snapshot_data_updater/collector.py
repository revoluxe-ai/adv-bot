"""``AdvDataSnapshotCollector`` — batch-сбор snapshot на уровне магазина.

Принцип granularity
-------------------
**Не** запускается отдельный «полный pipeline» на каждую adv, если данные можно
получить одним batch на shop:

1. **Postgres (1×)** — все active adv/settings + ``ComplexAdv`` для warmup.
2. **Параллельно** (через ``ResourceQueue`` + ``asyncio.gather``):
   - ClickHouse: plan/fact по всем ``adv_ids``;
   - ClickHouse: cluster texts по всем ``auction_adv_id`` (search-кампании);
   - Redis: min_bids v2 batch по всем ячейкам магазина;
   - ``CalculatedKeywordsWarmupService.warmup_shop`` (только в live-стеке).
3. **Assembler** — для каждой adv только склейка уже загруженных maps (без I/O).

В stub-стеке warmup отсутствует; keywords читаются из ``StubRedisSnapshotProvider``.
"""

from __future__ import annotations

import asyncio
import logging
import time
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime, timedelta
from typing import TypeVar

from app.snapshot_data_updater.assembler import AdvDataSnapshotAssembler
from app.snapshot_data_updater.dto import (
    AdvDataSnapshotDTO,
    AdvSettingsSnapshotDTO,
    CalculatedKeywordSnapshotDTO,
    ClusterTextsSnapshotDTO,
    MinBidsSnapshotDTO,
    PlanFactSnapshotDTO,
    ShopAdvSnapshotBatchDTO,
    SnapshotDiagnostics,
)
from app.snapshot_data_updater.protocols import (
    ClickHouseSnapshotProvider,
    PostgresSnapshotProvider,
    RedisSnapshotProvider,
)
from app.snapshot_data_updater.providers.postgres_shop_load import (
    PostgresShopSnapshotLoad,
)
from app.snapshot_data_updater.resource_queue import (
    ResourceKind,
    ResourceQueueManager,
    ResourceTask,
)
from app.snapshot_data_updater.services.calculated_keywords_warmup import (
    CalculatedKeywordsWarmupResult,
    CalculatedKeywordsWarmupService,
)

logger = logging.getLogger(__name__)

T = TypeVar("T")


class AdvDataSnapshotCollector:
    """Собирает ``ShopAdvSnapshotBatchDTO`` одним shop-level pipeline."""

    def __init__(
        self,
        *,
        postgres: PostgresSnapshotProvider,
        clickhouse: ClickHouseSnapshotProvider,
        redis: RedisSnapshotProvider,
        assembler: AdvDataSnapshotAssembler | None = None,
        resource_queues: ResourceQueueManager | None = None,
        keywords_warmup: CalculatedKeywordsWarmupService | None = None,
        schema_version: int = 1,
        snapshot_ttl_sec: int = 3600,
    ) -> None:
        """Args:
            postgres: stub или live PG (active adv).
            clickhouse: stub или live CH (plan/fact, cluster texts).
            redis: stub или live Redis (keywords, min_bids).
            assembler: чистая сборка DTO; по умолчанию ``AdvDataSnapshotAssembler``.
            resource_queues: лимиты параллелизма PG/CH/Redis/warmup.
            keywords_warmup: в live — централизованный прогрев ключей; в stub — ``None``.
            schema_version: пишется в каждый ``AdvDataSnapshotDTO``.
            snapshot_ttl_sec: ``expires_at = collected_at + ttl``.
        """
        self._postgres = postgres
        self._clickhouse = clickhouse
        self._redis = redis
        self._assembler = assembler or AdvDataSnapshotAssembler()
        from app.snapshot_data_updater.resource_queue import (
            build_resource_queue_manager,
        )

        self._queues = resource_queues or build_resource_queue_manager()
        self._keywords_warmup = keywords_warmup
        self._schema_version = schema_version
        self._snapshot_ttl_sec = snapshot_ttl_sec

    @property
    def resource_queues(self) -> ResourceQueueManager:
        """Очереди ресурсов (для ``SnapshotUpdater`` shutdown)."""
        return self._queues

    async def collect_shop(self, shop_id: str) -> ShopAdvSnapshotBatchDTO:
        """Главный метод: один batch на магазин → пакет снимков по всем active adv.

        Args:
            shop_id: идентификатор магазина WB.

        Returns:
            ``ShopAdvSnapshotBatchDTO`` с ``AdvDataSnapshotDTO`` на каждую РК.

        Side effects:
            Read-only I/O через провайдеры (и warmup write в legacy Redis hash в live).
        """
        collected_at = datetime.now(tz=UTC)
        expires_at = collected_at + timedelta(seconds=self._snapshot_ttl_sec)
        shop_errors: dict[str, str] = {}
        t_shop = time.perf_counter()

        shop_load, pg_err = await self._run_phase(
            "postgres",
            shop_id,
            lambda: self._fetch_shop_load(shop_id),
        )
        if pg_err:
            shop_errors["postgres"] = pg_err
            logger.error(
                "collect_shop aborted shop_id=%s: postgres failed", shop_id
            )
            return ShopAdvSnapshotBatchDTO(
                shop_id=shop_id,
                collected_at=collected_at,
                schema_version=self._schema_version,
                snapshots=[],
            )

        settings_list = shop_load.settings
        if not settings_list:
            logger.info(
                "collect_shop empty shop_id=%s (no active adv) ms=%.1f",
                shop_id,
                (time.perf_counter() - t_shop) * 1000,
            )
            return ShopAdvSnapshotBatchDTO(
                shop_id=shop_id,
                collected_at=collected_at,
                schema_version=self._schema_version,
                snapshots=[],
            )

        adv_ids = [s.adv_id for s in settings_list]
        auction_adv_ids = sorted(
            {
                s.search_adv_id
                for s in settings_list
                if s.search_adv_id is not None
            }
        )

        (
            (plan_facts, pf_err),
            (cluster_texts_by_auction, ct_err),
            (min_bids_by_adv, mb_err),
            (warmup_by_adv, wu_err),
        ) = await asyncio.gather(
            self._run_phase(
                "clickhouse_plan_fact",
                shop_id,
                lambda: self._fetch_plan_facts(shop_id, adv_ids),
            ),
            self._run_phase(
                "clickhouse_cluster_texts",
                shop_id,
                lambda: self._fetch_cluster_texts(auction_adv_ids),
            ),
            self._run_phase(
                "redis_min_bids",
                shop_id,
                lambda: self._fetch_min_bids_batch(settings_list),
            ),
            self._run_phase(
                "keywords_warmup",
                shop_id,
                lambda: self._warmup_keywords(shop_id, shop_load),
            ),
        )
        for key, err in (
            ("clickhouse_plan_fact", pf_err),
            ("clickhouse_cluster_texts", ct_err),
            ("redis_min_bids", mb_err),
            ("keywords_warmup", wu_err),
        ):
            if err:
                shop_errors[key] = err

        snapshots: list[AdvDataSnapshotDTO] = []
        partial_count = 0
        warmup_recalculated = 0
        for settings in settings_list:
            warmup_result = warmup_by_adv.get(settings.adv_id)
            if warmup_result is None and self._keywords_warmup is not None:
                complex_adv = shop_load.complex_advs_by_id.get(settings.adv_id)
                if complex_adv is not None:
                    warmup_result = await self._keywords_warmup.warmup_adv(
                        complex_adv
                    )
            if warmup_result is not None and warmup_result.source == "recalculated":
                warmup_recalculated += 1
            keywords = (
                warmup_result.keywords
                if warmup_result is not None
                else await self._fetch_keywords_fallback(settings.adv_id)
            )
            cluster_texts: ClusterTextsSnapshotDTO | None = None
            if settings.search_adv_id is not None:
                texts = cluster_texts_by_auction.get(settings.search_adv_id, set())
                cluster_texts = ClusterTextsSnapshotDTO(
                    auction_adv_id=settings.search_adv_id,
                    texts=set(texts),
                )
            diag = SnapshotDiagnostics(errors_by_section=dict(shop_errors))
            snapshot = self._assembler.assemble_adv_snapshot(
                settings=settings,
                plan_fact=plan_facts.get(settings.adv_id),
                keywords=keywords,
                min_bids=min_bids_by_adv.get(settings.adv_id),
                cluster_texts=cluster_texts,
                collected_at=collected_at,
                expires_at=expires_at,
                schema_version=self._schema_version,
                warmup_result=warmup_result,
                diagnostics=diag,
            )
            if snapshot.partial:
                partial_count += 1
            snapshots.append(snapshot)

        logger.info(
            "collect_shop done shop_id=%s adv_count=%d partial=%d "
            "warmup_recalculated=%d errors=%s ms=%.1f",
            shop_id,
            len(snapshots),
            partial_count,
            warmup_recalculated,
            list(shop_errors.keys()) or "none",
            (time.perf_counter() - t_shop) * 1000,
        )
        return ShopAdvSnapshotBatchDTO(
            shop_id=shop_id,
            collected_at=collected_at,
            schema_version=self._schema_version,
            snapshots=snapshots,
        )

    async def _run_phase(
        self,
        phase: str,
        shop_id: str,
        coro_factory: Callable[[], Awaitable[T]],
    ) -> tuple[T, str | None]:
        """Выполняет фазу сбора; при ошибке логирует и возвращает (default, err)."""
        started = time.perf_counter()
        try:
            result = await coro_factory()
            logger.debug(
                "collect phase %s ok shop_id=%s ms=%.1f",
                phase,
                shop_id,
                (time.perf_counter() - started) * 1000,
            )
            return result, None
        except Exception as exc:
            logger.exception(
                "collect phase %s failed shop_id=%s",
                phase,
                shop_id,
            )
            return self._default_for_phase(phase), str(exc)[:500]

    def _default_for_phase(self, phase: str) -> object:
        if phase == "postgres":
            return PostgresShopSnapshotLoad(shop_id="")
        if phase == "clickhouse_plan_fact":
            return {}
        if phase == "clickhouse_cluster_texts":
            return {}
        if phase == "redis_min_bids":
            return {}
        if phase == "keywords_warmup":
            return {}
        return {}

    async def _fetch_shop_load(self, shop_id: str) -> PostgresShopSnapshotLoad:
        """Один запрос PG: settings + optional ``ComplexAdv`` для warmup (live)."""
        fetch_load = getattr(self._postgres, "fetch_shop_collect_load", None)
        if callable(fetch_load):
            future = self._queues.submit(
                ResourceTask(
                    kind=ResourceKind.POSTGRES,
                    name=f"pg:shop_load:{shop_id}",
                    coro_factory=lambda: fetch_load(shop_id),
                )
            )
            return await future

        future = self._queues.submit(
            ResourceTask(
                kind=ResourceKind.POSTGRES,
                name=f"pg:settings:{shop_id}",
                coro_factory=lambda: self._postgres.fetch_active_adv_settings(
                    shop_id
                ),
            )
        )
        settings = await future
        return PostgresShopSnapshotLoad(shop_id=shop_id, settings=settings)

    async def _fetch_plan_facts(
        self, shop_id: str, adv_ids: list[int]
    ) -> dict[int, PlanFactSnapshotDTO]:
        """Batch CH: plan/fact по всем adv_id магазина."""
        if not adv_ids:
            return {}
        future = self._queues.submit(
            ResourceTask(
                kind=ResourceKind.CLICKHOUSE,
                name=f"ch:plan_fact:{shop_id}",
                coro_factory=lambda: self._clickhouse.fetch_plan_facts(
                    shop_id, adv_ids
                ),
            )
        )
        return await future

    async def _fetch_cluster_texts(
        self, auction_adv_ids: list[int]
    ) -> dict[int, set[str]]:
        """Batch CH: norm_query кластеров (если провайдер поддерживает метод)."""
        fetch_fn = getattr(
            self._clickhouse, "fetch_cluster_texts_by_auction_adv", None
        )
        if not callable(fetch_fn) or not auction_adv_ids:
            return {}
        future = self._queues.submit(
            ResourceTask(
                kind=ResourceKind.CLICKHOUSE,
                name=f"ch:cluster_texts:{len(auction_adv_ids)}",
                coro_factory=lambda: fetch_fn(auction_adv_ids),
            )
        )
        return await future

    async def _fetch_min_bids_batch(
        self, settings_list: list[AdvSettingsSnapshotDTO]
    ) -> dict[int, MinBidsSnapshotDTO]:
        """Batch Redis min_bids v2 или fallback по одной adv."""
        batch_fn = getattr(self._redis, "fetch_min_bids_for_settings", None)
        if callable(batch_fn):
            future = self._queues.submit(
                ResourceTask(
                    kind=ResourceKind.REDIS,
                    name=f"redis:min_bids_batch:{len(settings_list)}",
                    coro_factory=lambda: batch_fn(settings_list),
                )
            )
            return await future

        result: dict[int, MinBidsSnapshotDTO] = {}
        for settings in settings_list:
            mb = await self._fetch_min_bids_single(settings.adv_id)
            if mb is not None:
                result[settings.adv_id] = mb
        return result

    async def _fetch_min_bids_single(self, adv_id: int) -> MinBidsSnapshotDTO | None:
        """Fallback: min_bids для одной adv (stub без batch-метода)."""
        future = self._queues.submit(
            ResourceTask(
                kind=ResourceKind.REDIS,
                name=f"redis:min_bids:{adv_id}",
                coro_factory=lambda: self._redis.fetch_min_bids(adv_id),
            )
        )
        return await future

    async def _warmup_keywords(
        self,
        shop_id: str,
        shop_load: PostgresShopSnapshotLoad,
    ) -> dict[int, CalculatedKeywordsWarmupResult]:
        """Прогрев calculated_keywords (live); в stub возвращает пустой dict."""
        if self._keywords_warmup is None:
            return {}
        if not shop_load.complex_advs_by_id:
            return {}
        return await self._keywords_warmup.warmup_shop(
            shop_id,
            shop_load.complex_advs_by_id,
        )

    async def _fetch_keywords_fallback(
        self, adv_id: int
    ) -> list[CalculatedKeywordSnapshotDTO]:
        """Чтение keywords из Redis без warmup (stub path)."""
        future = self._queues.submit(
            ResourceTask(
                kind=ResourceKind.REDIS,
                name=f"redis:keywords:{adv_id}",
                coro_factory=lambda: self._redis.fetch_keywords(adv_id),
            )
        )
        return await future
