"""Legacy alias: ``keywords_prepared._prepared_builder`` → ``keyword_dto._prepared_builder``."""

from app.modules.shop_runner.service_manager.services.auto_updater_v3.keyword_dto._prepared_builder import (
    _bootstrap_ladder_inputs,
    _is_gap_context,
    _stage_for_agg,
    _strategy_mode_for_stage,
    _target_position_for_stage,
    assemble_update_context,
    build_keyword_dto,
    build_keyword_prepared_row,
    build_keywords_prepared_list,
    build_ladder_states_for_context,
    build_ladder_states_for_contexts,
    build_update_context,
    update_context_from_prepared,
)

__all__ = (
    "_bootstrap_ladder_inputs",
    "_is_gap_context",
    "_stage_for_agg",
    "_strategy_mode_for_stage",
    "_target_position_for_stage",
    "assemble_update_context",
    "build_keyword_dto",
    "build_keyword_prepared_row",
    "build_keywords_prepared_list",
    "build_ladder_states_for_context",
    "build_ladder_states_for_contexts",
    "build_update_context",
    "update_context_from_prepared",
)
