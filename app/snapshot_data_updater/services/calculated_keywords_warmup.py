"""``CalculatedKeywordsWarmupService`` — централизованный прогрев keywords.

Задача
------
Снизить ``cache_only`` miss в ``update_cluster_bids`` и других consumer'ах:
snapshot updater **сам** обеспечивает актуальный Redis hash
``calculated_keywords:{adv_id}`` до записи snapshot.

Жёсткие ограничения (roadmap)
-----------------------------
- **Не** менять business logic ``CalculatedKeywordsManager``.
- **Не** менять формат legacy hash (только ``RedisCalculatedKeywordsCacheManager``).
- Пересчёт — через существующий ``get_good_bad_phrases`` (пишет hash как раньше).
- Freshness — отдельный ключ ``adv_snapshot:v1:keywords_meta:adv:{id}`` (новый namespace).
- Тяжёлый пересчёт CH лимитируется ``anti_ch_crash_semaphore`` / ``CLICKHOUSE_QUERY_CONCURRENCY``.
"""

from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass
from datetime import UTC, datetime

from app.modules.calculated_keywords_redis_cache_manager.redis_manager import (
    RedisCalculatedKeywordsCacheManager,
)
from app.modules.shop_runner.service_manager.wb_shop_data_manager.dto.complex_adv import (
    ComplexAdv,
)
from app.modules.wb_adv_updater.calculated_keywords_manager.dto.calculated_keyword import (
    CalculatedKeyword,
)
from app.snapshot_data_updater.cache_freshness import (
    CacheStaleError,
    load_keywords_meta,
    parse_warmed_at,
)
from app.snapshot_data_updater.freshness_policy import (
    enforce_cache_stale,
    should_skip_refresh,
)
from app.snapshot_data_updater.config import (
    SnapshotUpdaterConfig,
    resolve_snapshot_config,
)
from app.snapshot_data_updater.dto import (
    CalculatedKeywordSnapshotDTO,
    FreshnessSnapshotDTO,
    KeywordsSource,
    KeywordsWarmupDiagnostics,
)
from app.snapshot_data_updater.keys import keywords_meta_key
from app.snapshot_data_updater.mappers.keyword_mapper import (
    calculated_keywords_to_snapshots,
)
from app.snapshot_data_updater.resource_queue import ResourceQueueManager

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class CalculatedKeywordsWarmupResult:
    """Результат warmup одной РК для assembler и diagnostics."""

    adv_id: int
    keywords: list[CalculatedKeywordSnapshotDTO]
    source: KeywordsSource
    cache_hit: bool
    cache_stale: bool
    duration_ms: float
    error: str | None = None


class CalculatedKeywordsWarmupService:
    """Прогрев ``calculated_keywords:{adv_id}`` с проверкой freshness metadata."""

    def __init__(
        self,
        *,
        config: SnapshotUpdaterConfig | None = None,
        resource_queues: ResourceQueueManager | None = None,
        keywords_cache: RedisCalculatedKeywordsCacheManager | None = None,
    ) -> None:
        """Args:
            config: окно freshness и strict mode (см. ``keywords_freshness_sec``).
            resource_queues: если задан — каждый adv warmup через CALCULATED_KEYWORDS_WARMUP.
            keywords_cache: Redis client для legacy hash и metadata.
        """
        self._config = resolve_snapshot_config(config)
        self._queues = resource_queues
        self._keywords_cache = keywords_cache or RedisCalculatedKeywordsCacheManager()

    async def warmup_shop(
        self,
        shop_id: str,
        complex_advs_by_id: dict[int, ComplexAdv],
        *,
        adv_ids_needing_warmup: set[int] | None = None,
    ) -> dict[int, CalculatedKeywordsWarmupResult]:
        """Прогревает все (или выбранные) adv магазина.

        Args:
            shop_id: для логов и имён задач в ResourceQueue.
            complex_advs_by_id: из ``PostgresSnapshotProviderLive.fetch_shop_collect_load``.
            adv_ids_needing_warmup: подмножество adv; по умолчанию все ключи map.

        Returns:
            adv_id → результат warmup (keywords уже в slim DTO).
        """
        results: dict[int, CalculatedKeywordsWarmupResult] = {}
        targets = adv_ids_needing_warmup or set(complex_advs_by_id.keys())
        for adv_id in targets:
            complex_adv = complex_advs_by_id.get(adv_id)
            if complex_adv is None:
                continue
            results[adv_id] = await self.warmup_adv(complex_adv)
        return results

    async def warmup_adv(self, complex_adv: ComplexAdv) -> CalculatedKeywordsWarmupResult:
        """Один adv: fresh cache → read; stale/miss → ``get_good_bad_phrases``."""
        adv_id = complex_adv.adv_id
        started = time.perf_counter()
        try:
            cached = await self._keywords_cache.get_all_calculated_keywords_for_adv(
                adv_id
            )
            meta = await self._read_meta(adv_id)
            fresh, stale, source = self._classify_cache(cached, meta)
            if fresh and cached is not None:
                self._enforce_read_cache_age(meta, adv_id=adv_id)
                keywords = calculated_keywords_to_snapshots(cached)
                duration_ms = (time.perf_counter() - started) * 1000
                return CalculatedKeywordsWarmupResult(
                    adv_id=adv_id,
                    keywords=keywords,
                    source=source,
                    cache_hit=True,
                    cache_stale=False,
                    duration_ms=duration_ms,
                )
            if (
                not stale
                and cached is not None
                and source == "redis_unknown_freshness"
                and not self._config.keywords_strict_freshness
            ):
                self._enforce_read_cache_age(meta, adv_id=adv_id)
                keywords = calculated_keywords_to_snapshots(cached)
                duration_ms = (time.perf_counter() - started) * 1000
                return CalculatedKeywordsWarmupResult(
                    adv_id=adv_id,
                    keywords=keywords,
                    source=source,
                    cache_hit=True,
                    cache_stale=False,
                    duration_ms=duration_ms,
                )
            recalculated = await self._recalculate(complex_adv)
            keywords = calculated_keywords_to_snapshots(recalculated)
            await self._write_meta(
                adv_id,
                source="recalculated",
                keywords_count=len(keywords),
            )
            duration_ms = (time.perf_counter() - started) * 1000
            logger.info(
                "snapshot keywords warmup recalculated adv_id=%s count=%d ms=%.1f",
                adv_id,
                len(keywords),
                duration_ms,
            )
            return CalculatedKeywordsWarmupResult(
                adv_id=adv_id,
                keywords=keywords,
                source="recalculated",
                cache_hit=False,
                cache_stale=stale,
                duration_ms=duration_ms,
            )
        except CacheStaleError:
            raise
        except Exception as exc:
            duration_ms = (time.perf_counter() - started) * 1000
            logger.exception("snapshot keywords warmup failed adv_id=%s", adv_id)
            await self._write_meta(adv_id, source="error", error=str(exc))
            return CalculatedKeywordsWarmupResult(
                adv_id=adv_id,
                keywords=[],
                source="error",
                cache_hit=False,
                cache_stale=True,
                duration_ms=duration_ms,
                error=str(exc),
            )

    async def _recalculate(
        self, complex_adv: ComplexAdv
    ) -> list[CalculatedKeyword]:
        """Вызывает существующий pipeline (CH/PG внутри manager + write legacy hash)."""
        from app.core.di.wb_manager_hub import WBManagerHubFactory
        from app.modules.wb_adv_updater.calculated_keywords_manager.calculated_keywords_manager import (
            CalculatedKeywordsManager,
        )
        from app.modules.wb_adv_updater.phrases_processor import get_good_bad_phrases
        from app.snapshot_data_updater.bootstrap import ensure_di_bootstrapped

        await ensure_di_bootstrapped()
        hub = await CalculatedKeywordsManager._get_wb_manager_hub(complex_adv)
        token = WBManagerHubFactory._wb_manager_hub_context_var.set(hub)
        try:
            return await get_good_bad_phrases(complex_adv)
        finally:
            WBManagerHubFactory._wb_manager_hub_context_var.reset(token)

    def _classify_cache(
        self,
        cached: list[CalculatedKeyword] | None,
        meta: dict[str, str] | None,
    ) -> tuple[bool, bool, KeywordsSource]:
        """Определяет fresh / stale / unknown по hash + metadata."""
        if cached is None:
            return False, True, "missing"
        if meta is None:
            return False, False, "redis_unknown_freshness"
        warmed_at = parse_warmed_at(meta)
        if warmed_at is None:
            return False, False, "redis_unknown_freshness"
        age_sec = (datetime.now(tz=UTC) - warmed_at).total_seconds()
        policy = self._config.keywords_policy
        if should_skip_refresh(age_sec, policy):
            return True, False, "redis_hit"
        if policy.stale_sec > 0 and age_sec > policy.stale_sec:
            return False, True, "redis_stale"
        if cached is not None:
            return True, False, "redis_hit"
        return False, True, "redis_stale"

    async def _read_meta(self, adv_id: int) -> dict[str, str] | None:
        """Читает ``adv_snapshot:v1:keywords_meta:adv:{adv_id}``."""
        return await load_keywords_meta(self._keywords_cache.client, adv_id)

    def _enforce_read_cache_age(
        self, meta: dict[str, str] | None, *, adv_id: int
    ) -> None:
        """Жёсткая проверка возраста (``SNAPSHOT_KEYWORDS_STALE_SEC``) при наличии metadata."""
        if meta is None:
            return
        warmed_at = parse_warmed_at(meta)
        enforce_cache_stale(
            warmed_at,
            self._config.keywords_policy,
            context=f"keywords cache adv_id={adv_id}",
            require_timestamp=True,
        )

    async def _write_meta(
        self,
        adv_id: int,
        *,
        source: str,
        keywords_count: int = 0,
        error: str | None = None,
    ) -> None:
        """Пишет metadata после recalculate/error (не трогает legacy hash TTL)."""
        payload = {
            "warmed_at": datetime.now(tz=UTC).isoformat(),
            "source": source,
            "schema_version": str(self._config.snapshot_schema_version),
            "keywords_count": str(keywords_count),
        }
        if error:
            payload["error"] = error[:500]
        await self._keywords_cache.client.set(
            keywords_meta_key(adv_id),
            json.dumps(payload),
            ex=int(max(self._config.keywords_policy.stale_sec, 300.0) * 4),
        )

    @staticmethod
    def to_diagnostics(result: CalculatedKeywordsWarmupResult) -> KeywordsWarmupDiagnostics:
        """Преобразует результат warmup в ``KeywordsWarmupDiagnostics`` для DTO."""
        is_fresh = result.source == "redis_hit"
        return KeywordsWarmupDiagnostics(
            keywords_freshness=FreshnessSnapshotDTO(
                is_fresh=is_fresh,
                age_sec=None,
                warmed_at=None,
                source=result.source,
            ),
            keywords_cache_hit=result.cache_hit,
            keywords_cache_stale=result.cache_stale,
            keywords_warmed_by_snapshot_updater=result.source == "recalculated",
            keywords_warmup_duration_ms=result.duration_ms,
            keywords_count=len(result.keywords),
            keywords_error=result.error,
            keywords_source=result.source,
        )
