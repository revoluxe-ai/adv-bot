"""Read-only orchestrator: PG scope + CH readers → manifest + payloads."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timezone

from app.modules.ai_package_v1.domain.campaign_stat import (
    assert_no_synthetic_merge,
    assert_observed_ids_are_physical,
    rows_for_shop,
)
from app.modules.ai_package_v1.domain.cards import (
    build_shop_product_orders_sales_card,
)
from app.modules.ai_package_v1.domain.export_inputs import validate_export_inputs
from app.modules.ai_package_v1.domain.export_period import ExportPeriod
from app.modules.ai_package_v1.domain.funnel_orders_boundary import (
    FunnelOrdersMetric,
    assert_funnel_orders_do_not_populate_shop_product_orders,
)
from app.modules.ai_package_v1.analysis.attribution_reader import (
    AnalysisAttributionReaderProtocol,
    ChAnalysisAttributionReader,
    collect_attribution_evidence,
)
from app.modules.ai_package_v1.analysis.aggregate import legs_from_scope
from app.modules.ai_package_v1.analysis.campaign_reader import (
    AnalysisCampaignReaderProtocol,
    ChAnalysisCampaignReader,
)
from app.modules.ai_package_v1.analysis.catalog import build_analysis_windows
from app.modules.ai_package_v1.analysis.models import AnalysisBuildRequest, CampaignDailyFact
from app.modules.ai_package_v1.analysis.service import (
    AnalysisAggregationService,
    annotate_data_map,
)
from app.modules.ai_package_v1.domain.manifest import (
    PACKAGE_SCHEMA_VERSION_WITH_ANALYSIS,
    DomainPayload,
    ExportManifest,
    build_file_descriptors,
)
from app.modules.ai_package_v1.export.campaign_settings_assembler import (
    CampaignSettingsAssembler,
)
from app.modules.ai_package_v1.export.dataset_cards import (
    CAMPAIGN_SETTINGS_JSON_LOGICAL,
    build_campaign_full_stat_card,
    build_complex_adv_funnel_card,
    build_detailed_campaign_settings_card,
    campaign_freshness_status,
)
from app.modules.ai_package_v1.export.manifest_cards import (
    serialize_campaign_settings_payload,
)
from app.modules.ai_package_v1.export.payload_encode import (
    encode_campaign_stat_csv,
    encode_funnel_stat_csv,
)
from app.modules.ai_package_v1.export.scope_collect import (
    collect_main_nmids,
    collect_scoped_adv_ids,
)
from app.modules.ai_package_v1.keyword_performance.domain.cutoff import PackageCutoff
from app.modules.ai_package_v1.keyword_performance.export.dataset_cards import (
    DATA_MAP_LOGICAL,
)
from app.modules.ai_package_v1.keyword_performance.export.keyword_assembler import (
    KeywordAssemblerProtocol,
    KeywordPerformanceAssembler,
)
from app.modules.ai_package_v1.keyword_performance.readers.pg_session_adapter import (
    default_pg_session_factory,
)
from app.modules.ai_package_v1.readers.ch_campaign_stat_reader import ChCampaignStatReader
from app.modules.ai_package_v1.readers.ch_funnel_reader import ChFunnelReader
from app.modules.ai_package_v1.readers.ch_freshness_reader import ChExportFreshnessReader
from app.modules.ai_package_v1.readers.pg_snapshot_reader import PgSnapshotReader
from app.modules.ai_package_v1.scope.dto import ExportScopeAdv
from app.modules.ai_package_v1.scope.pg_export_shop_scope_reader import (
    PgExportShopScopeReader,
)


@dataclass(frozen=True, slots=True)
class ExportResult:
    """Результат export без ZIP-транспорта (domain manifest + payloads).

    ``manifest.shop_id`` совпадает с входным PG ``WBCabinet.shop_id`` (str).
    """

    manifest: ExportManifest
    payloads: list[DomainPayload]


class ExportService:
    """
    Оркестратор §3.2: ``export(shop_id, period)`` read-only, без WB API.

    Зависимости инжектируются для unit-тестов (fake CH/PG readers).
    """

    def __init__(
        self,
        *,
        scope_reader: PgExportShopScopeReader | None = None,
        campaign_reader: ChCampaignStatReader | None = None,
        funnel_reader: ChFunnelReader | None = None,
        freshness_reader: ChExportFreshnessReader | None = None,
        pg_snapshot_reader: PgSnapshotReader | None = None,
        settings_assembler: CampaignSettingsAssembler | None = None,
        keyword_assembler: KeywordAssemblerProtocol | None = None,
        analysis_campaign_reader: AnalysisCampaignReaderProtocol | None = None,
        analysis_attribution_reader: AnalysisAttributionReaderProtocol | None = None,
    ) -> None:
        """Собирает read-only зависимости export.

        Settings inventory по умолчанию получает ``default_pg_session_factory``.
        Reader открывает сессию как ``session_maker(read_only=True)()``, поэтому
        фабрика возвращает ``async_sessionmaker``.
        """
        self._scope_reader = scope_reader or PgExportShopScopeReader()
        self._campaign_reader = campaign_reader or ChCampaignStatReader()
        self._funnel_reader = funnel_reader or ChFunnelReader()
        self._freshness_reader = freshness_reader or ChExportFreshnessReader()
        self._pg_snapshot_reader = pg_snapshot_reader or PgSnapshotReader(
            scope_reader=self._scope_reader
        )
        if settings_assembler is not None:
            self._settings_assembler = settings_assembler
        else:
            self._settings_assembler = CampaignSettingsAssembler(
                session_maker=default_pg_session_factory,
            )
        if keyword_assembler is not None:
            self._keyword_assembler = keyword_assembler
        else:
            self._keyword_assembler = KeywordPerformanceAssembler()
        self._analysis_reader = analysis_campaign_reader or ChAnalysisCampaignReader()
        self._analysis_attribution_reader = (
            analysis_attribution_reader or ChAnalysisAttributionReader()
        )
        self._analysis_service = AnalysisAggregationService()

    async def export(
        self,
        shop_id: str,
        period: ExportPeriod,
        *,
        generated_at: str | None = None,
    ) -> ExportResult:
        """
        Собирает manifest и payloads для магазина и периода.

        Args:
            shop_id: Authoritative ``WBCabinet.shop_id`` (str).
            period: Закрытый интервал дат export.
            generated_at: ISO timestamp для manifest (тестовый hook).

        Returns:
            ``ExportResult`` с карточками датасетов и CSV payloads.

        Raises:
            ValueError: при synthetic campaign_id, невалидном shop_id или period.
        """
        manifest_id = validate_export_inputs(shop_id, period)
        scope = await self._scope_reader.load_scope(shop_id)
        return await self._export_with_scope(
            shop_id=shop_id,
            manifest_shop_id=manifest_id,
            period=period,
            scope=scope,
            generated_at=generated_at,
        )

    async def export_with_scope(
        self,
        shop_id: str,
        period: ExportPeriod,
        scope: list[ExportScopeAdv],
        *,
        generated_at: str | None = None,
    ) -> ExportResult:
        """
        Export с уже загруженным scope (unit seam без PG).

        Args:
            shop_id: PG shop_id str.
            period: Период export.
            scope: Inventory DTO из ``PgExportShopScopeReader``.
            generated_at: ISO timestamp hook.

        Returns:
            ``ExportResult``.
        """
        manifest_id = validate_export_inputs(shop_id, period)
        return await self._export_with_scope(
            shop_id=shop_id,
            manifest_shop_id=manifest_id,
            period=period,
            scope=scope,
            generated_at=generated_at,
        )

    async def _export_with_scope(
        self,
        *,
        shop_id: str,
        manifest_shop_id: str,
        period: ExportPeriod,
        scope: list[ExportScopeAdv],
        generated_at: str | None,
    ) -> ExportResult:
        adv_ids = collect_scoped_adv_ids(scope)
        nmids = collect_main_nmids(scope)

        campaign_rows = await self._campaign_reader.fetch_rows(
            manifest_shop_id, adv_ids, period
        )
        campaign_rows = rows_for_shop(campaign_rows, manifest_shop_id)
        assert_observed_ids_are_physical(
            {row.campaign_id for row in campaign_rows},
            set(adv_ids),
        )
        for item in scope:
            if item.search_adv_id is not None and item.search_adv_id != item.auto_adv_id:
                leg_rows = [
                    row
                    for row in campaign_rows
                    if row.campaign_id in (item.auto_adv_id, item.search_adv_id)
                ]
                assert_no_synthetic_merge(
                    leg_rows, item.auto_adv_id, item.search_adv_id
                )

        funnel_rows = await self._funnel_reader.fetch_rows(
            manifest_shop_id, nmids, period
        )
        funnel_rows = [r for r in funnel_rows if r.shop_id == manifest_shop_id]

        adv_version = await self._freshness_reader.max_full_adv_version(adv_ids)
        nmid_version = await self._freshness_reader.max_common_stat_version(nmids)
        campaign_freshness = campaign_freshness_status(adv_version, period)
        funnel_freshness = campaign_freshness_status(nmid_version, period)

        shop_orders_card = build_shop_product_orders_sales_card(period)
        settings_snapshot = await self._settings_assembler.assemble(shop_id)
        settings_card = build_detailed_campaign_settings_card(
            period,
            payload=settings_snapshot,
        )
        settings_payload_content = serialize_campaign_settings_payload(
            settings_snapshot
        )
        observed_adv_ids = sorted({row.campaign_id for row in campaign_rows})
        campaign_card = build_campaign_full_stat_card(
            period,
            scoped_adv_ids=adv_ids,
            observed_adv_ids=observed_adv_ids,
            row_count=len(campaign_rows),
            freshness=campaign_freshness,
        )
        funnel_card = build_complex_adv_funnel_card(
            period,
            scoped_nmids=nmids,
            row_count=len(funnel_rows),
            freshness=funnel_freshness,
        )

        funnel_metrics = [
            FunnelOrdersMetric(nmid=row.nmid, orders=row.orders) for row in funnel_rows
        ]
        assert_funnel_orders_do_not_populate_shop_product_orders(
            funnel_metrics, shop_orders_card
        )

        timestamp = generated_at or datetime.now(timezone.utc).strftime(
            "%Y-%m-%dT%H:%M:%SZ"
        )
        keyword_result = await self._keyword_assembler.assemble(
            shop_id=shop_id,
            manifest_shop_id=manifest_shop_id,
            period=period,
            generated_at=timestamp,
        )

        cutoff = PackageCutoff.from_generated_at(timestamp)
        analysis_facts = await self._analysis_reader.fetch_daily_facts(
            shop_id=manifest_shop_id,
            adv_ids=adv_ids,
            end_date=cutoff.package_cutoff_date,
        )
        source_first, source_last = _campaign_fact_bounds(tuple(analysis_facts))
        windows = build_analysis_windows(
            cutoff,
            campaign_first=source_first,
            campaign_last=source_last,
            requested_period=period,
        )
        legs = legs_from_scope(tuple(scope))
        attribution_evidence = await collect_attribution_evidence(
            self._analysis_attribution_reader,
            shop_id=manifest_shop_id,
            windows=windows,
            legs=legs,
        )
        analysis = self._analysis_service.build(
            AnalysisBuildRequest(
                shop_id=manifest_shop_id,
                generated_at=timestamp,
                period=period,
                scope=tuple(scope),
                campaign_facts=tuple(analysis_facts),
                keyword_windows=tuple(keyword_result.windows),
                keyword_history_first=keyword_result.keyword_history_first,
                keyword_history_last=keyword_result.keyword_history_last,
                attribution_by_leg_window=attribution_evidence,
            )
        )
        payloads = [
            DomainPayload(
                logical_name="datasets/campaign_full_stat.csv",
                dataset_id="campaign_full_stat",
                content=encode_campaign_stat_csv(campaign_rows),
            ),
            DomainPayload(
                logical_name="datasets/complex_adv_funnel.csv",
                dataset_id="complex_adv_funnel",
                content=encode_funnel_stat_csv(funnel_rows),
            ),
            DomainPayload(
                logical_name=CAMPAIGN_SETTINGS_JSON_LOGICAL,
                dataset_id="campaign_settings_snapshot",
                content=settings_payload_content,
            ),
            *_with_analysis_data_map(keyword_result.payloads),
            *analysis.payloads,
        ]
        manifest = ExportManifest(
            package_schema_version=PACKAGE_SCHEMA_VERSION_WITH_ANALYSIS,
            shop_id=manifest_shop_id,
            period=period,
            generated_at=timestamp,
            datasets=[
                campaign_card,
                funnel_card,
                settings_card,
                shop_orders_card,
                *keyword_result.cards,
                *analysis.cards,
            ],
            files=build_file_descriptors(payloads),
        )
        return ExportResult(manifest=manifest, payloads=payloads)


def _campaign_fact_bounds(
    facts: tuple[CampaignDailyFact, ...],
) -> tuple[date | None, date | None]:
    if not facts:
        return None, None
    dates = [fact.stat_date for fact in facts]
    return min(dates), max(dates)


def _with_analysis_data_map(payloads: tuple[DomainPayload, ...]) -> list[DomainPayload]:
    """Вписывает зерно анализа в уже собранную карту данных."""
    annotated: list[DomainPayload] = []
    for payload in payloads:
        if payload.logical_name == DATA_MAP_LOGICAL:
            annotated.append(
                DomainPayload(
                    logical_name=payload.logical_name,
                    dataset_id=payload.dataset_id,
                    content=annotate_data_map(payload.content),
                )
            )
        else:
            annotated.append(payload)
    return annotated
