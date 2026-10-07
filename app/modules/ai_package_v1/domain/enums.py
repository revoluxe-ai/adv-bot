"""Перечисления доменного контракта AI Package v1 (стабильные строковые токены)."""

from enum import StrEnum


class CollectionOutcome(StrEnum):
    """Результат попытки получения данных (независимо от coverage)."""

    SUCCESS = "SUCCESS"
    FAILURE = "FAILURE"
    PARTIAL = "PARTIAL"
    UNKNOWN = "UNKNOWN"


class Coverage(StrEnum):
    """Полнота покрытия сущностей и периода (независимо от collection_outcome)."""

    FULL = "FULL"
    PARTIAL = "PARTIAL"
    NONE = "NONE"
    UNKNOWN = "UNKNOWN"


class FreshnessStatus(StrEnum):
    """Актуальность накопления (не подменяет coverage)."""

    FRESH = "FRESH"
    STALE = "STALE"
    UNKNOWN = "UNKNOWN"


class ReasonCode(StrEnum):
    """Машинно-читаемые причины неполноты или отсутствия источника."""

    NO_DATA = "NO_DATA"
    UNKNOWN = "UNKNOWN"
    SOURCE_NOT_ASSIGNED = "SOURCE_NOT_ASSIGNED"
    INSUFFICIENT_PERMISSIONS = "INSUFFICIENT_PERMISSIONS"
    PARTIAL_COLLECTION = "PARTIAL_COLLECTION"
    SOURCE_ERROR = "SOURCE_ERROR"
    PARTIAL_PG_WB_SYNC = "PARTIAL_PG_WB_SYNC"


class PrimarySource(StrEnum):
    """Идентичность первичного источника датасета в manifest."""

    SOURCE_NOT_ASSIGNED = "SOURCE_NOT_ASSIGNED"
    CLICKHOUSE_FULL_ADV_WB_STAT = "default_db.full_adv_wb_stat"
    CLICKHOUSE_WB_COMMON_STAT = "default_db.wb_common_stat"
    CLICKHOUSE_CLUSTERS_ADV_STATS = "default_db.clusters_adv_stats"
    CLICKHOUSE_KEYWORD_POSITION_API = "default_db.keyword_position_from_api"
    DERIVED_KEYWORD_DAILY = "derived:keyword_daily"
    DERIVED_KEYWORD_WINDOWS = "derived:keyword_windows"
    DERIVED_ANALYSIS = "derived:analysis_aggregation"
    DERIVED_KEYWORD_POSITION_WINDOWS = "derived:keyword_position_windows"
    CLICKHOUSE_BID_DECISION_LOG = "default_db.bid_decision_log"
    EXPORT_DATA_MAP = "export:DATA_MAP_builder"
    EXPORT_KEYWORD_COVERAGE = "export:coverage_assembler"
    POSTGRES_INVENTORY = "postgresql.adv_setting_inventory"
    POSTGRES_CAMPAIGN_SETTINGS = "postgresql.adv_setting_detailed_settings"
    UNKNOWN = "UNKNOWN"


class FamilyStatus(StrEnum):
    """
    Канонический статус семейства данных в PACKAGE_SUMMARY и PACKAGE_FAMILY_GAPS.

    Не подменяет ``CollectionOutcome`` / ``Coverage`` в dataset cards; сводится
    из них (и явных GAP-каталогов) одной функцией ``derive_family_status``.
    """

    COMPLETE = "COMPLETE"
    PARTIAL = "PARTIAL"
    GAP = "GAP"
    UNSUPPORTED = "UNSUPPORTED"
    FAILED = "FAILED"


class DatasetId(StrEnum):
    """Логические идентификаторы датасетов v1."""

    CAMPAIGN_FULL_STAT = "campaign_full_stat"
    COMPLEX_ADV_FUNNEL = "complex_adv_funnel"
    CAMPAIGN_SETTINGS_SNAPSHOT = "campaign_settings_snapshot"
    SHOP_PRODUCT_ORDERS_SALES = "shop_product_orders_sales"
    KEYWORD_DAILY = "keyword_daily"
    KEYWORD_WINDOWS = "keyword_windows"
    KEYWORD_CURRENT_STATE = "keyword_current_state"
    KEYWORD_CHANGES = "keyword_changes"
    KEYWORD_POSITIONS = "keyword_positions"
    KEYWORD_POSITION_WINDOWS = "keyword_position_windows"
    KEYWORD_POSITION_CURRENT = "keyword_position_current"
    KEYWORD_DECISIONS = "keyword_decisions"
    DATA_MAP = "DATA_MAP"
    KEYWORD_COVERAGE = "keyword_coverage"
    PACKAGE_FAMILY_GAPS = "package_family_gaps"
    PACKAGE_SUMMARY = "package_summary"
    ANALYSIS_CONTRACT = "analysis_contract"
    AI_ANALYSIS_GUIDE = "ai_analysis_guide"
    ANALYSIS_PACKAGE_CAMPAIGN_SCOPE = "analysis_package_campaign_scope"
    ANALYSIS_CAMPAIGNS = "analysis_campaigns"
    ANALYSIS_KEYWORD_PRODUCT_SCOPE = "analysis_keyword_product_scope"
    ANALYSIS_COMPARISONS = "analysis_comparisons"
