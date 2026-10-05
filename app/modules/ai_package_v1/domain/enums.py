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
    POSTGRES_INVENTORY = "postgresql.adv_setting_inventory"
    POSTGRES_CAMPAIGN_SETTINGS = "postgresql.adv_setting_detailed_settings"
    UNKNOWN = "UNKNOWN"


class DatasetId(StrEnum):
    """Логические идентификаторы датасетов v1."""

    CAMPAIGN_FULL_STAT = "campaign_full_stat"
    COMPLEX_ADV_FUNNEL = "complex_adv_funnel"
    CAMPAIGN_SETTINGS_SNAPSHOT = "campaign_settings_snapshot"
    SHOP_PRODUCT_ORDERS_SALES = "shop_product_orders_sales"
