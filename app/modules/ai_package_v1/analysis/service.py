"""Сборка доменных payload аналитического слоя."""

from __future__ import annotations

import json
from datetime import date
from typing import Any, cast

from app.modules.ai_package_v1.analysis.aggregate import (
    fold_campaign_windows,
    fold_keyword_products,
    fold_package_scope,
    legs_from_scope,
)
from app.modules.ai_package_v1.analysis.catalog import (
    build_analysis_windows,
    custom_period_includes_watermark,
)
from app.modules.ai_package_v1.analysis.comparisons import build_comparisons
from app.modules.ai_package_v1.analysis.constants import (
    AI_GUIDE_LOGICAL,
    ANALYSIS_CONTRACT_LOGICAL,
    CAMPAIGNS_LOGICAL,
    COMPARISONS_LOGICAL,
    KEYWORD_PRODUCT_SCOPE_LOGICAL,
    PACKAGE_CAMPAIGN_SCOPE_LOGICAL,
)
from app.modules.ai_package_v1.analysis.documents import (
    build_analysis_contract,
    build_analysis_guide,
)
from app.modules.ai_package_v1.analysis.models import AnalysisBuildRequest, CampaignDailyFact
from app.modules.ai_package_v1.domain.dataset_card import DatasetCard, Provenance
from app.modules.ai_package_v1.domain.enums import (
    CollectionOutcome,
    Coverage,
    DatasetId,
    FreshnessStatus,
    PrimarySource,
    ReasonCode,
)
from app.modules.ai_package_v1.domain.manifest import (
    PACKAGE_SCHEMA_VERSION_WITH_ANALYSIS,
    DomainPayload,
)
from app.modules.ai_package_v1.domain.serialization import canonical_json_bytes
from app.modules.ai_package_v1.keyword_performance.domain.cutoff import PackageCutoff


class AnalysisBuildResult:
    """Доменный результат, который транспорт только кодирует."""

    def __init__(
        self,
        *,
        contract: dict[str, Any],
        guide_text: str,
        campaign_rows: list[dict[str, object]],
        package_rows: list[dict[str, object]],
        keyword_rows: list[dict[str, object]],
        comparison_rows: list[dict[str, object]],
        payloads: list[DomainPayload],
        cards: list[DatasetCard],
        campaign_fact_count: int,
        package_schema_version: str,
    ) -> None:
        self.contract = contract
        self.guide_text = guide_text
        self.campaign_rows = campaign_rows
        self.package_rows = package_rows
        self.keyword_rows = keyword_rows
        self.comparison_rows = comparison_rows
        self.payloads = payloads
        self.cards = cards
        self.campaign_fact_count = campaign_fact_count
        self.package_schema_version = package_schema_version


class AnalysisAggregationService:
    """Единственный владелец формул окон магазинного пакета.

    Сервис read-only: он не открывает WB, не пишет в БД и не кодирует ZIP.
    """

    def build(self, request: AnalysisBuildRequest) -> AnalysisBuildResult:
        """Считает витрины на уже прочитанных фактах и готовых ключевых окнах."""
        cutoff = PackageCutoff.from_generated_at(request.generated_at)
        facts = tuple(sorted(request.campaign_facts, key=_fact_sort))
        source_first, source_last = _fact_bounds(facts)
        windows = build_analysis_windows(
            cutoff,
            campaign_first=source_first,
            campaign_last=source_last,
            requested_period=request.period,
        )
        legs = legs_from_scope(tuple(request.scope))
        forced = custom_period_includes_watermark(request.period, cutoff)
        campaign_rows = fold_campaign_windows(
            shop_id=request.shop_id,
            cutoff=cutoff,
            windows=windows,
            legs=legs,
            facts=facts,
            source_complete_through=request.campaign_source_complete_through,
            source_first=source_first,
            source_last=source_last,
            custom_forced_partial=forced,
        )
        package_rows = fold_package_scope(
            campaign_rows,
            shop_id=request.shop_id,
            cutoff=cutoff,
            windows=windows,
            source_complete_through=request.campaign_source_complete_through,
            source_first=source_first,
            source_last=source_last,
        )
        keyword_rows = fold_keyword_products(
            request.keyword_windows,
            shop_id=request.shop_id,
            cutoff=cutoff,
            source_complete_through=request.keyword_source_complete_through,
            source_first=request.keyword_history_first,
            source_last=request.keyword_history_last,
        )
        ordered_campaigns = _sort_rows(campaign_rows)
        ordered_package = _sort_rows(package_rows)
        ordered_keyword = _sort_rows(keyword_rows)
        comparisons = build_comparisons(
            [*ordered_package, *ordered_campaigns, *ordered_keyword]
        )
        contract = build_analysis_contract(
            cutoff=cutoff,
            period=request.period,
            windows=windows,
            keyword_history_first=_iso(request.keyword_history_first),
            keyword_history_last=_iso(request.keyword_history_last),
            campaign_history_first=_iso(source_first),
            campaign_history_last=_iso(source_last),
            campaign_fact_count=len(facts),
        )
        guide = build_analysis_guide()
        payloads = [
            DomainPayload(
                ANALYSIS_CONTRACT_LOGICAL,
                str(DatasetId.ANALYSIS_CONTRACT),
                canonical_json_bytes(contract),
            ),
            DomainPayload(
                AI_GUIDE_LOGICAL,
                str(DatasetId.AI_ANALYSIS_GUIDE),
                guide.encode("utf-8"),
            ),
            DomainPayload(
                PACKAGE_CAMPAIGN_SCOPE_LOGICAL,
                str(DatasetId.ANALYSIS_PACKAGE_CAMPAIGN_SCOPE),
                _encode_jsonl(ordered_package),
            ),
            DomainPayload(
                CAMPAIGNS_LOGICAL,
                str(DatasetId.ANALYSIS_CAMPAIGNS),
                _encode_jsonl(ordered_campaigns),
            ),
            DomainPayload(
                KEYWORD_PRODUCT_SCOPE_LOGICAL,
                str(DatasetId.ANALYSIS_KEYWORD_PRODUCT_SCOPE),
                _encode_jsonl(ordered_keyword),
            ),
            DomainPayload(
                COMPARISONS_LOGICAL,
                str(DatasetId.ANALYSIS_COMPARISONS),
                _encode_jsonl(comparisons),
            ),
        ]
        cards = _cards(request, payloads)
        return AnalysisBuildResult(
            contract=contract,
            guide_text=guide,
            campaign_rows=ordered_campaigns,
            package_rows=ordered_package,
            keyword_rows=ordered_keyword,
            comparison_rows=comparisons,
            payloads=payloads,
            cards=cards,
            campaign_fact_count=len(facts),
            package_schema_version=PACKAGE_SCHEMA_VERSION_WITH_ANALYSIS,
        )


def project_transport_view(result: AnalysisBuildResult, transport: str) -> dict[str, object]:
    """Один и тот же доменный срез для ZIP, API или MCP.

    Транспорт не пересчитывает метрики. ``transport`` только метка потребителя.
    """
    return {
        "transport": transport,
        "package_schema_version": result.package_schema_version,
        "campaign_rows": result.campaign_rows,
        "package_rows": result.package_rows,
        "keyword_rows": result.keyword_rows,
        "comparison_rows": result.comparison_rows,
        "analysis_contract_version": result.contract["analysis_contract_version"],
    }


def annotate_data_map(content: bytes) -> bytes:
    """Добавляет в карту данных зерно аналитических файлов, не меняя ключевые поля."""
    parsed_object = cast(object, json.loads(content.decode("utf-8")))
    if not isinstance(parsed_object, dict):
        raise ValueError("DATA_MAP must be an object")
    document = cast(dict[str, Any], parsed_object)
    document["analysis_layer"] = {
        "owner": "AnalysisAggregationService",
        "package_cutoff_date_semantics": (
            "UTC generation date minus one calendar day; not source completeness"
        ),
        "datasets": {
            PACKAGE_CAMPAIGN_SCOPE_LOGICAL: {
                "grain": "shop × window",
                "scope": "PACKAGE_CAMPAIGN_SCOPE",
                "provenance": "sum of included physical legs; not whole-shop spend",
            },
            CAMPAIGNS_LOGICAL: {
                "grain": "physical adv_id × leg_role × window",
                "scope": "CAMPAIGN_WB_STAT",
                "provenance": "default_db.full_adv_wb_stat latest version per leg and day",
            },
            KEYWORD_PRODUCT_SCOPE_LOGICAL: {
                "grain": "adv_id × leg_role × nmid × window",
                "scope": "KEYWORD_PERFORMANCE_PRODUCT_SCOPE",
                "provenance": "fold of keyword_performance/keyword_windows.jsonl",
            },
            COMPARISONS_LOGICAL: {
                "grain": "entity × window pair",
                "scope": "comparison status",
                "provenance": "domain comparison of the same analysis rows",
            },
        },
    }
    return canonical_json_bytes(document)


def _cards(request: AnalysisBuildRequest, payloads: list[DomainPayload]) -> list[DatasetCard]:
    specs = (
        (
            DatasetId.ANALYSIS_CONTRACT,
            PrimarySource.DERIVED_ANALYSIS,
            "analysis contract",
            ANALYSIS_CONTRACT_LOGICAL,
        ),
        (
            DatasetId.AI_ANALYSIS_GUIDE,
            PrimarySource.DERIVED_ANALYSIS,
            "analysis guide",
            AI_GUIDE_LOGICAL,
        ),
        (
            DatasetId.ANALYSIS_PACKAGE_CAMPAIGN_SCOPE,
            PrimarySource.CLICKHOUSE_FULL_ADV_WB_STAT,
            "shop × window package campaign scope",
            PACKAGE_CAMPAIGN_SCOPE_LOGICAL,
        ),
        (
            DatasetId.ANALYSIS_CAMPAIGNS,
            PrimarySource.CLICKHOUSE_FULL_ADV_WB_STAT,
            "physical leg × window",
            CAMPAIGNS_LOGICAL,
        ),
        (
            DatasetId.ANALYSIS_KEYWORD_PRODUCT_SCOPE,
            PrimarySource.DERIVED_KEYWORD_WINDOWS,
            "keyword article × leg × window",
            KEYWORD_PRODUCT_SCOPE_LOGICAL,
        ),
        (
            DatasetId.ANALYSIS_COMPARISONS,
            PrimarySource.DERIVED_ANALYSIS,
            "entity × window pair",
            COMPARISONS_LOGICAL,
        ),
    )
    by_name = {payload.logical_name: payload.content for payload in payloads}
    cards: list[DatasetCard] = []
    for dataset_id, source, grain, logical_name in specs:
        content = by_name[logical_name]
        row_count = _row_count(logical_name, content)
        cards.append(
            DatasetCard(
                dataset_id=dataset_id,
                provenance=Provenance(
                    primary_source=source,
                    grain=grain,
                    notes="analysis layer; not clipped to caller export period",
                ),
                period=request.period,
                collection_outcome=CollectionOutcome.PARTIAL,
                coverage=Coverage.UNKNOWN,
                reason_codes=[ReasonCode.UNKNOWN],
                freshness=FreshnessStatus.UNKNOWN,
                row_file=logical_name,
                row_count=row_count,
            )
        )
    return cards


def _row_count(logical_name: str, content: bytes) -> int:
    if logical_name.endswith(".json") or logical_name.endswith(".md"):
        return 1 if content else 0
    if not content:
        return 0
    return content.decode("utf-8").count("\n")


def _encode_jsonl(rows: list[dict[str, object]]) -> bytes:
    if not rows:
        return b""
    lines = [
        json.dumps(row, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        for row in rows
    ]
    return ("\n".join(lines) + "\n").encode("utf-8")


def _sort_rows(rows: list[dict[str, object]]) -> list[dict[str, object]]:
    return sorted(rows, key=_row_sort_key)


def _row_sort_key(row: dict[str, object]) -> tuple[str, int, int, int, int]:
    adv = row.get("adv_id")
    nmid = row.get("nmid")
    return (
        str(row.get("entity_kind")),
        -1 if adv is None else int(str(adv)),
        -1 if nmid is None else int(str(nmid)),
        int(str(row.get("catalog_index", 0))),
        0,
    )


def _fact_sort(fact: CampaignDailyFact) -> tuple[int, str]:
    return fact.adv_id, fact.stat_date.isoformat()


def _fact_bounds(
    facts: tuple[CampaignDailyFact, ...],
) -> tuple[date | None, date | None]:
    if not facts:
        return None, None
    dates = [fact.stat_date for fact in facts]
    return min(dates), max(dates)


def _iso(value: object) -> str | None:
    if value is None:
        return None
    isoformat = getattr(value, "isoformat", None)
    if callable(isoformat):
        rendered = isoformat()
        if isinstance(rendered, str):
            return rendered
    return None
