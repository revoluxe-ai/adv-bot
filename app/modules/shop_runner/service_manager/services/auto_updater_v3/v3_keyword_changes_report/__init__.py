"""Post-hoc анализ ``KeywordDTO`` для отчёта «Последние действия с ключами» (V3).

Строит статистику по executor из ``next_state`` / ``history_target_place``,
мерджит в ``V3TickReportSnapshot`` и кеширует полный audit в Redis.
"""

from app.modules.shop_runner.service_manager.services.auto_updater_v3.v3_keyword_changes_report.builder import (
    build_keyword_changes_snapshot,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.v3_keyword_changes_report.merge import (
    merge_keyword_changes_into_tick_snapshot,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.v3_keyword_changes_report.models import (
    V3ExecutorPhaseBreakdown,
    V3KeywordChangeEntry,
    V3KeywordChangesSnapshot,
    V3KeywordStepRecord,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.v3_keyword_changes_report.no_data_builder import (
    build_from_applied_actions,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.v3_keyword_changes_report.redis import (
    V3KeywordChangesRedisCache,
    persist_v3_keyword_changes,
)

__all__ = [
    "V3ExecutorPhaseBreakdown",
    "V3KeywordChangeEntry",
    "V3KeywordChangesRedisCache",
    "V3KeywordChangesSnapshot",
    "V3KeywordStepRecord",
    "build_from_applied_actions",
    "build_keyword_changes_snapshot",
    "merge_keyword_changes_into_tick_snapshot",
    "persist_v3_keyword_changes",
]
