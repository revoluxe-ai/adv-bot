"""Фабрики для генерации тестовых данных.

Основные фабрики:
- AdvSettingFactory, KeywordSettingFactory - ORM модели
- CalculatedKeywordFactory - DTO для расчётных ключевых слов
- GoodKeywordFactory, BadKeywordFactory, TestingKeywordFactory - специализированные фабрики
"""

from .adv_factory import AdvSettingFactory, KeywordSettingFactory
from .keyword_pipeline import (
    # Enum
    HardStatus,
    # Main factories
    CalculatedKeywordFactory,
    KeywordSettingDTOFactory,
    KeywordStatFactory,
    KeywordStateFactory,
    # Specialized factories
    GoodKeywordFactory,
    BadKeywordFactory,
    TestingKeywordFactory,
    BestKeywordFactory,
    # Legacy functions (для обратной совместимости)
    make_calculated_keyword,
    make_keyword_setting_dto,
    make_keyword_stat,
    make_keyword_state,
    # Generators
    generate_calculated_keywords,
    generate_keywords_with_best,
    KeywordsWithBest,
)
from .keyword_position_factory import KeywordStatFromJamFactory
from .clickhouse_factory import (
    ClustersAdvStatsFactory,
    ClustersAdvStatsDTO,
    CLUSTERS_ADV_STATS_COLUMNS,
    build_clusters_adv_stats_rows,
)

__all__ = [
    # ORM Factories
    "AdvSettingFactory",
    "KeywordSettingFactory",
    # DTO Factories
    "CalculatedKeywordFactory",
    "KeywordSettingDTOFactory",
    "KeywordStatFactory",
    "KeywordStateFactory",
    # Specialized Factories
    "GoodKeywordFactory",
    "BadKeywordFactory",
    "TestingKeywordFactory",
    "BestKeywordFactory",
    # Enum
    "HardStatus",
    # Legacy functions
    "make_calculated_keyword",
    "make_keyword_setting_dto",
    "make_keyword_stat",
    "make_keyword_state",
    # Generators
    "generate_calculated_keywords",
    "generate_keywords_with_best",
    "KeywordsWithBest",
    # Position factory
    "KeywordStatFromJamFactory",
    # ClickHouse factory
    "ClustersAdvStatsFactory",
    "ClustersAdvStatsDTO",
    "CLUSTERS_ADV_STATS_COLUMNS",
    "build_clusters_adv_stats_rows",
]
