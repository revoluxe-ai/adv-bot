"""Версии и имена аналитического слоя AI Package.

Смысл версий зафиксирован в design change ``ai-package-multi-window-analysis``.
"""

from __future__ import annotations

ANALYSIS_CONTRACT_VERSION = "1.0.0"
AI_GUIDE_VERSION = "1.0.0"
METRIC_DEFINITION_VERSION = "1.0.0"
MINIMUM_SAMPLE_ORDERS = 5

ANALYSIS_CONTRACT_LOGICAL = "analysis/ANALYSIS_CONTRACT.json"
AI_GUIDE_LOGICAL = "analysis/AI_ANALYSIS_GUIDE.md"
PACKAGE_CAMPAIGN_SCOPE_LOGICAL = "analysis/windows/package_campaign_scope.jsonl"
CAMPAIGNS_LOGICAL = "analysis/windows/campaigns.jsonl"
KEYWORD_PRODUCT_SCOPE_LOGICAL = "analysis/windows/keyword_product_scope.jsonl"
COMPARISONS_LOGICAL = "analysis/comparisons.jsonl"
KEYWORD_WINDOWS_LOGICAL = "keyword_performance/keyword_windows.jsonl"

CUTOFF_NOT_COMPLETENESS = (
    "package_cutoff_date is not evidence of source completeness"
)

SHOP_DRR_BLOCKERS: tuple[str, ...] = (
    "BLOCKED_BY_SHOP_WIDE_CAMPAIGN_COVERAGE",
    "BLOCKED_BY_COMMON_SALES",
    "BLOCKED_BY_SHOP_DRR_SOURCE",
)
ATTRIBUTION_BLOCKERS: tuple[str, ...] = ("BLOCKED_BY_ATTRIBUTION_FACTS",)
CAMPAIGN_SPEND_INCOMPLETE: str = "CAMPAIGN_SPEND_INCOMPLETE"
SHOP_SPEND_BLOCKERS: tuple[str, ...] = ("BLOCKED_BY_SHOP_WIDE_CAMPAIGN_COVERAGE",)
SKU_ECONOMICS_BLOCKERS: tuple[str, ...] = (
    "BLOCKED_BY_COMMON_SALES",
    "KEYWORD_SCOPE_IS_NOT_TOTAL_SKU_ECONOMICS",
)

FORBIDDEN_NUMERIC_METRICS: frozenset[str] = frozenset(
    {
        # Campaign/keyword fold must not invent shop/SKU economics or attribution.
        # Attribution CPO/DRR are emitted only via AttributionFactsReader path.
        "SHOP_DRR",
        "ALL_SHOP_AD_SPEND",
        "SHOP_AD_SPEND",
        "SKU_GMV",
        "SKU_DRR",
        "SKU_ORDERS",
    }
)

CAMPAIGN_ORDERS_METRIC = "CAMPAIGN_WB_STAT_ORDERS"
CAMPAIGN_CPO_METRIC = "CAMPAIGN_WB_STAT_CPO"
KEYWORD_ORDERS_METRIC = "KEYWORD_ORDERS"
KEYWORD_CPO_METRIC = "KEYWORD_CPO"
