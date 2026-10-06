"""Контракт метрик и инструкция AI. Текст детерминированный, без вызова модели."""

from __future__ import annotations

from typing import Any

from app.modules.ai_package_v1.analysis.constants import (
    AI_GUIDE_LOGICAL,
    AI_GUIDE_VERSION,
    ANALYSIS_CONTRACT_LOGICAL,
    ANALYSIS_CONTRACT_VERSION,
    CAMPAIGNS_LOGICAL,
    COMPARISONS_LOGICAL,
    CUTOFF_NOT_COMPLETENESS,
    KEYWORD_PRODUCT_SCOPE_LOGICAL,
    KEYWORD_WINDOWS_LOGICAL,
    METRIC_DEFINITION_VERSION,
    MINIMUM_SAMPLE_ORDERS,
    PACKAGE_CAMPAIGN_SCOPE_LOGICAL,
)
from app.modules.ai_package_v1.domain.export_period import ExportPeriod
from app.modules.ai_package_v1.domain.manifest import PACKAGE_SCHEMA_VERSION_WITH_ANALYSIS
from app.modules.ai_package_v1.keyword_performance.domain.cutoff import PackageCutoff
from app.modules.ai_package_v1.keyword_performance.windows.engine import WindowSpec


def build_analysis_contract(
    *,
    cutoff: PackageCutoff,
    period: ExportPeriod,
    windows: list[WindowSpec],
    keyword_history_first: str | None,
    keyword_history_last: str | None,
    campaign_history_first: str | None,
    campaign_history_last: str | None,
    campaign_fact_count: int,
) -> dict[str, Any]:
    """Машинная семантика слоя. Инструкция на неё ссылается и сама формулы не задаёт."""
    return {
        "document_kind": "analysis_contract",
        "analysis_contract_version": ANALYSIS_CONTRACT_VERSION,
        "ai_guide_version": AI_GUIDE_VERSION,
        "package_schema_version": PACKAGE_SCHEMA_VERSION_WITH_ANALYSIS,
        "metric_definition_version": METRIC_DEFINITION_VERSION,
        "reporting_timezone": "UNKNOWN",
        "source_period_closure": "UNKNOWN",
        "generation_utc_date": cutoff.package_cutoff_date.isoformat(),
        "package_cutoff_date": cutoff.last_closed_calendar_day.isoformat(),
        "package_cutoff_statement": CUTOFF_NOT_COMPLETENESS,
        "requested_period": period.to_manifest_dict(),
        "analysis_windows": [
            {
                "window_id": spec.window_id,
                "window_start": spec.start.isoformat(),
                "window_end": spec.end.isoformat(),
                "requested_days": spec.requested_days,
            }
            for spec in windows
        ],
        "history_context": {
            "keyword_performance": {
                "first": keyword_history_first,
                "last": keyword_history_last,
                "clipped_by_requested_period": False,
            },
            "campaign_wb_stat": {
                "first": campaign_history_first,
                "last": campaign_history_last,
                "clipped_by_requested_period": False,
            },
        },
        "campaign_fact_row_count": campaign_fact_count,
        "minimum_sample_orders": MINIMUM_SAMPLE_ORDERS,
        "files": {
            "analysis_contract": ANALYSIS_CONTRACT_LOGICAL,
            "ai_guide": AI_GUIDE_LOGICAL,
            "package_campaign_scope": PACKAGE_CAMPAIGN_SCOPE_LOGICAL,
            "campaigns": CAMPAIGNS_LOGICAL,
            "keyword_product_scope": KEYWORD_PRODUCT_SCOPE_LOGICAL,
            "comparisons": COMPARISONS_LOGICAL,
            "keyword_windows": KEYWORD_WINDOWS_LOGICAL,
        },
        "scopes": {
            "PACKAGE_CAMPAIGN_SCOPE": "physical legs included in this package only",
            "CAMPAIGN_WB_STAT": "campaign stat orders and order sum, not DIRECT or LINKED",
            "KEYWORD_PERFORMANCE_PRODUCT_SCOPE": "keyword grain rolled to article and leg",
        },
        "metric_definitions": _metric_definitions(),
        "comparison_statuses": ["COMPARABLE", "PARTIAL", "NOT_COMPARABLE"],
        "nested_windows_are_not_independent_samples": True,
        "fixed_cpo_control_mode": "unchanged",
        "dynamic_cpo_control_enabled": False,
    }


def build_analysis_guide() -> str:
    """Инструкция чтения. Арифметика остаётся в контракте, не в этом тексте."""
    return "\n".join(
        [
            "# AI analysis guide",
            "",
            f"ai_guide_version: {AI_GUIDE_VERSION}",
            f"analysis_contract_version: {ANALYSIS_CONTRACT_VERSION}",
            "",
            "Read in this order:",
            "1. Package summary and coverage.",
            "2. Freshness and family gaps.",
            "3. Analysis windows.",
            "4. Problem entities only.",
            "5. Settings history only when that family is present.",
            "6. Raw facts only for a named entity.",
            "7. Separate facts from hypotheses.",
            "8. Propose an action only from supported facts.",
            "",
            CUTOFF_NOT_COMPLETENESS,
            "",
            "The LLM is a consumer of this package. It is not a factual authority.",
            "Formulas live in analysis/ANALYSIS_CONTRACT.json.",
            "",
            "Do not treat GAP, unknown, or a missing row as zero.",
            "Do not merge Auto and Search.",
            "Do not treat package campaign scope as whole-shop spend.",
            "Do not calculate SHOP_DRR from package scope.",
            "Do not treat keyword-product scope as total SKU economics.",
            "Do not silently fall LINKED back to DIRECT.",
            "Do not invent attribution.",
            "Do not invent causality.",
            "Do not assume a nominal window is complete without evidence.",
            "Do not compare two numbers that have no comparison status.",
            "Nested windows are nested horizons, not independent samples.",
            "Do not invent order ids or article ids.",
            "One complete family does not make the package complete.",
            "Package campaign spend must not be substituted into shop DRR.",
            "Campaign order sum must not be substituted for factual shop GMV.",
            "SHOP_DRR is a capacity signal only when both whole-shop ad spend",
            "and factual whole-shop GMV are proven. It does not replace leg economics.",
            "",
        ]
    )


def _metric_definitions() -> list[dict[str, Any]]:
    version = METRIC_DEFINITION_VERSION
    return [
        _ready(
            "CAMPAIGN_WB_STAT_VIEWS",
            "sum of observed campaign views",
            "CAMPAIGN_WB_STAT",
            version,
        ),
        _ready(
            "CAMPAIGN_WB_STAT_CLICKS",
            "sum of observed campaign clicks",
            "CAMPAIGN_WB_STAT",
            version,
        ),
        _ready(
            "CAMPAIGN_WB_STAT_SPEND_RUB",
            "sum of observed campaign spend",
            "CAMPAIGN_WB_STAT",
            version,
        ),
        _ready(
            "CAMPAIGN_WB_STAT_ORDERS",
            "sum of observed campaign-stat orders",
            "CAMPAIGN_WB_STAT",
            version,
        ),
        _ready(
            "CAMPAIGN_WB_STAT_ORDER_SUM",
            "sum of observed campaign-stat order sum",
            "CAMPAIGN_WB_STAT",
            version,
        ),
        _ready(
            "CAMPAIGN_WB_STAT_CTR",
            "clicks / views when views are not zero",
            "CAMPAIGN_WB_STAT",
            version,
        ),
        _ready(
            "CAMPAIGN_WB_STAT_CPC",
            "spend / clicks when clicks are not zero",
            "CAMPAIGN_WB_STAT",
            version,
        ),
        _ready(
            "CAMPAIGN_WB_STAT_CPO",
            "spend / campaign-stat orders when orders are not zero",
            "CAMPAIGN_WB_STAT",
            version,
        ),
        _ready("KEYWORD_VIEWS", "sum of keyword-window views", "KEYWORD_PERFORMANCE_PRODUCT_SCOPE", version),
        _ready("KEYWORD_CLICKS", "sum of keyword-window clicks", "KEYWORD_PERFORMANCE_PRODUCT_SCOPE", version),
        _ready("KEYWORD_ORDERS", "sum of keyword-window orders", "KEYWORD_PERFORMANCE_PRODUCT_SCOPE", version),
        _ready(
            "KEYWORD_SPEND_RUB",
            "sum of factual keyword spend only",
            "KEYWORD_PERFORMANCE_PRODUCT_SCOPE",
            version,
        ),
        _blocked(
            "CPO_FACT_DIRECT",
            "Spend / Orders of direct attribution",
            "DIRECT",
            ["BLOCKED_BY_ATTRIBUTION_FACTS"],
        ),
        _blocked(
            "DRR_FACT_DIRECT",
            "Spend / GMV of direct attribution",
            "DIRECT",
            ["BLOCKED_BY_ATTRIBUTION_FACTS"],
        ),
        _blocked(
            "CPO_FACT_LINKED",
            "Spend / Orders of linked attribution",
            "LINKED",
            ["BLOCKED_BY_ATTRIBUTION_FACTS"],
        ),
        _blocked(
            "DRR_FACT_LINKED",
            "Spend / GMV of linked attribution",
            "LINKED",
            ["BLOCKED_BY_ATTRIBUTION_FACTS"],
        ),
        _blocked(
            "SHOP_DRR",
            "whole-shop ad spend / factual whole-shop GMV",
            "SHOP",
            [
                "BLOCKED_BY_SHOP_WIDE_CAMPAIGN_COVERAGE",
                "BLOCKED_BY_COMMON_SALES",
                "BLOCKED_BY_SHOP_DRR_SOURCE",
            ],
        ),
        _blocked(
            "ALL_SHOP_AD_SPEND",
            "all shop advertising spend",
            "SHOP",
            ["BLOCKED_BY_SHOP_WIDE_CAMPAIGN_COVERAGE"],
        ),
        _blocked(
            "SHOP_AD_SPEND",
            "shop advertising spend",
            "SHOP",
            ["BLOCKED_BY_SHOP_WIDE_CAMPAIGN_COVERAGE"],
        ),
        _blocked(
            "SKU_GMV",
            "all sales value of the article",
            "SKU",
            ["BLOCKED_BY_COMMON_SALES", "KEYWORD_SCOPE_IS_NOT_TOTAL_SKU_ECONOMICS"],
        ),
        _blocked(
            "SKU_DRR",
            "article DRR",
            "SKU",
            ["BLOCKED_BY_COMMON_SALES", "KEYWORD_SCOPE_IS_NOT_TOTAL_SKU_ECONOMICS"],
        ),
        _blocked(
            "SKU_ORDERS",
            "all orders of the article",
            "SKU",
            ["BLOCKED_BY_COMMON_SALES", "KEYWORD_SCOPE_IS_NOT_TOTAL_SKU_ECONOMICS"],
        ),
        {
            "metric_id": "TARGET_CPO_IDENTITY",
            "metric_definition_version": version,
            "formula": "reference revenue per order * target DRR",
            "computable": False,
            "control_mode": False,
            "notes": "identity only; fixed CPO is not rewritten",
        },
    ]


def _ready(metric_id: str, formula: str, scope: str, version: str) -> dict[str, Any]:
    return {
        "metric_id": metric_id,
        "metric_definition_version": version,
        "formula": formula,
        "scope": scope,
        "computable": True,
        "unit": "as_formula",
    }


def _blocked(
    metric_id: str,
    formula: str,
    scope: str,
    blockers: list[str],
) -> dict[str, Any]:
    return {
        "metric_id": metric_id,
        "metric_definition_version": METRIC_DEFINITION_VERSION,
        "formula": formula,
        "scope": scope,
        "computable": False,
        "value": None,
        "blocked_by": blockers,
    }
