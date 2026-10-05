"""Read-only orchestrator: PG scope + CH readers → manifest + payloads."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from app.modules.ai_package_v1.domain.campaign_stat import (
    assert_no_synthetic_merge,
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
from app.modules.ai_package_v1.domain.manifest import (
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
from app.utils.db.session_maker import get_async_session_maker
from app.modules.ai_package_v1.export.scope_collect import (
    collect_main_nmids,
    collect_scoped_adv_ids,
)
from app.modules.ai_package_v1.keyword_performance.export.keyword_assembler import (
    KeywordAssemblerProtocol,
    KeywordPerformanceAssembler,
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
    ) -> None:
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
                session_maker=get_async_session_maker,
            )
        if keyword_assembler is not None:
            self._keyword_assembler = keyword_assembler
        else:
            self._keyword_assembler = KeywordPerformanceAssembler()

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
            ValueError: при нарушении grain Auto/Search, невалидном shop_id или period.
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
        for item in scope:
            if item.search_adv_id is not None and item.search_adv_id != item.auto_adv_id:
                scoped_rows = [
                    r
                    for r in campaign_rows
                    if r.campaign_id in (item.auto_adv_id, item.search_adv_id)
                ]
                assert_no_synthetic_merge(
                    scoped_rows, item.auto_adv_id, item.search_adv_id
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
        campaign_card = build_campaign_full_stat_card(
            period,
            scoped_adv_ids=adv_ids,
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
            *keyword_result.payloads,
        ]
        manifest = ExportManifest(
            shop_id=manifest_shop_id,
            period=period,
            generated_at=timestamp,
            datasets=[
                campaign_card,
                funnel_card,
                settings_card,
                shop_orders_card,
                *keyword_result.cards,
            ],
            files=build_file_descriptors(payloads),
        )
        return ExportResult(manifest=manifest, payloads=payloads)
