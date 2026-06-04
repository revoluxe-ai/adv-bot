"""Публичный API keyword_dto (канонический пакет DTO V3)."""

from app.modules.shop_runner.service_manager.services.auto_updater_v3.keyword_dto._prepared_builder import (
    assemble_update_context,
    build_keyword_dto,
    build_keywords_prepared_list,
    build_ladder_states_for_context,
    build_ladder_states_for_contexts,
    build_update_context,
    update_context_from_prepared,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.keyword_dto.context_manager import (
    UpdateContextManager,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.keyword_dto.dto import (
    AdvState,
    KeywordDTO,
    KeywordMode,
    KeywordPreparedRow,
    KeywordV3LadderState,
    KeywordsPreparedList,
    NextState,
    NextTargetPlace,
    TargetPlaceMatrix,
    UpdateContext,
    UpdateContextInput,
    UpdateContextRuntime,
    V3LadderStageKind,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.keyword_dto.keyword_batch import (
    KeywordBatch,
)

__all__ = (
    "AdvState",
    "KeywordBatch",
    "KeywordDTO",
    "KeywordMode",
    "KeywordPreparedRow",
    "KeywordV3LadderState",
    "KeywordsPreparedList",
    "NextState",
    "NextTargetPlace",
    "TargetPlaceMatrix",
    "UpdateContext",
    "UpdateContextInput",
    "UpdateContextManager",
    "UpdateContextRuntime",
    "V3LadderStageKind",
    "assemble_update_context",
    "build_keyword_dto",
    "build_keywords_prepared_list",
    "build_ladder_states_for_context",
    "build_ladder_states_for_contexts",
    "build_update_context",
    "update_context_from_prepared",
)
