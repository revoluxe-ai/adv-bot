"""Подготовленные ключи кампании V3: ``UpdateContextManager``, DTO, legacy helpers."""

from app.modules.shop_runner.service_manager.services.auto_updater_v3.keywords_prepared._prepared_builder import (
    build_keyword_dto,
    build_keyword_prepared_row,
    build_keywords_prepared_list,
    build_ladder_states_for_context,
    build_ladder_states_for_contexts,
    build_update_context,
    update_context_from_prepared,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.keywords_prepared.context_manager import (
    UpdateContextManager,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.keywords_prepared.dto import (
    AdvState,
    KeywordDTO,
    KeywordPreparedRow,
    KeywordV3LadderState,
    KeywordsPreparedList,
    NextState,
    TargetPlaceMatrix,
    UpdateContext,
    UpdateContextInput,
    UpdateContextRuntime,
    V3LadderStageKind,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.keywords_prepared.keyword_batch import (
    KeywordBatch,
)

__all__ = (
    "AdvState",
    "KeywordBatch",
    "KeywordDTO",
    "KeywordPreparedRow",
    "KeywordV3LadderState",
    "KeywordsPreparedList",
    "NextState",
    "UpdateContext",
    "UpdateContextInput",
    "TargetPlaceMatrix",
    "UpdateContextRuntime",
    "UpdateContextManager",
    "V3LadderStageKind",
    "build_keyword_dto",
    "build_keyword_prepared_row",
    "build_keywords_prepared_list",
    "build_ladder_states_for_context",
    "build_ladder_states_for_contexts",
    "build_update_context",
    "update_context_from_prepared",
)
