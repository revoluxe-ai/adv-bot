"""``AdvDataSnapshotAssembler`` — чистая сборка DTO без I/O.

Вход — уже загруженные batch-части из collector; выход — ``AdvDataSnapshotDTO``
с ``section_completeness``, ``partial``, диагностикой warmup.
"""

from __future__ import annotations

from datetime import UTC, datetime

from app.snapshot_data_updater.dto import (
    AdvDataSnapshotDTO,
    AdvSettingsSnapshotDTO,
    CalculatedKeywordSnapshotDTO,
    ClusterTextsSnapshotDTO,
    MinBidsSnapshotDTO,
    PlanFactSnapshotDTO,
    SnapshotDiagnostics,
)
from app.snapshot_data_updater.services.calculated_keywords_warmup import (
    CalculatedKeywordsWarmupResult,
    CalculatedKeywordsWarmupService,
)


class AdvDataSnapshotAssembler:
    """Склеивает settings, plan/fact, keywords, min_bids, cluster_texts."""

    def assemble_adv_snapshot(
        self,
        *,
        settings: AdvSettingsSnapshotDTO,
        plan_fact: PlanFactSnapshotDTO | None,
        keywords: list[CalculatedKeywordSnapshotDTO],
        min_bids: MinBidsSnapshotDTO | None,
        cluster_texts: ClusterTextsSnapshotDTO | None = None,
        collected_at: datetime | None = None,
        expires_at: datetime | None = None,
        schema_version: int = 1,
        diagnostics: SnapshotDiagnostics | None = None,
        warmup_result: CalculatedKeywordsWarmupResult | None = None,
    ) -> AdvDataSnapshotDTO:
        """Собирает один adv-снимок из shop-level batch данных.

        Args:
            settings: PG snapshot настроек.
            plan_fact: CH агрегат или None.
            keywords: slim keywords (из warmup или Redis read).
            min_bids: batch min_bids или None.
            cluster_texts: CH norm_queries для search adv.
            collected_at: метка сбора UTC.
            expires_at: collected_at + TTL snapshot.
            schema_version: версия для consumer cutover.
            diagnostics: опционально; иначе строится из warmup_result.
            warmup_result: диагностика ``CalculatedKeywordsWarmupService``.

        Returns:
            Готовый ``AdvDataSnapshotDTO`` без дополнительного I/O.
        """
        ts = collected_at or datetime.now(tz=UTC)
        diag = diagnostics or SnapshotDiagnostics()
        if warmup_result is not None:
            kw_diag = CalculatedKeywordsWarmupService.to_diagnostics(warmup_result)
            diag = diag.model_copy(
                update={
                    "keywords": kw_diag,
                    "keywords_cache_hit": kw_diag.keywords_cache_hit,
                }
            )
        elif keywords:
            diag = diag.model_copy(update={"keywords_cache_hit": True})

        keywords_complete = self._keywords_section_complete(
            keywords=keywords,
            warmup_result=warmup_result,
            diagnostics=diag,
        )
        section_completeness = {
            "settings": True,
            "keywords": keywords_complete,
            "min_bids": min_bids is not None and (min_bids.coverage_ratio or 0) > 0,
            "plan_fact": plan_fact is not None,
            "cluster_texts": cluster_texts is not None and bool(cluster_texts.texts),
        }
        partial = not all(section_completeness.values())

        return AdvDataSnapshotDTO(
            adv_id=settings.adv_id,
            shop_id=settings.shop_id,
            collected_at=ts,
            expires_at=expires_at,
            schema_version=schema_version,
            partial=partial,
            section_completeness=section_completeness,
            settings=settings,
            plan_fact=plan_fact,
            keywords=keywords,
            min_bids=min_bids,
            cluster_texts=cluster_texts,
            diagnostics=diag,
        )

    @classmethod
    def keywords_section_complete_from_snapshot(
        cls, snapshot: AdvDataSnapshotDTO
    ) -> bool:
        """Проверка keywords по сохранённому DTO (Redis); warmup_result не сериализуется."""
        return cls._keywords_section_complete(
            keywords=snapshot.keywords,
            warmup_result=None,
            diagnostics=snapshot.diagnostics,
        )

    @staticmethod
    def _keywords_section_complete(
        *,
        keywords: list[CalculatedKeywordSnapshotDTO],
        warmup_result: CalculatedKeywordsWarmupResult | None,
        diagnostics: SnapshotDiagnostics,
    ) -> bool:
        """Секция keywords полна при успешном warmup/read; пустой список допустим."""
        if warmup_result is not None:
            return warmup_result.source not in {"error", "missing"}
        if keywords:
            return True
        kw = diagnostics.keywords
        return kw.keywords_cache_hit and kw.keywords_source not in {
            "error",
            "missing",
        }
