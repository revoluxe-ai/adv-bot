"""Внутренняя сборка ``KeywordsPreparedList`` и ``UpdateContext`` (не публичный API)."""

from __future__ import annotations

from typing import TYPE_CHECKING

from app.modules.common_slaves.wildberries.models.enums import KeywordStrategyMode
from app.modules.shop_runner.service_manager.services.auto_updater_v3.candidates import (
    stored_strategy_mode,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.dto import (
    AggressionTargetMode,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.keyword_v3_tier import (
    is_keyword_no_data,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.keyword_dto.dto import (
    AdvState,
    KeywordPreparedRow,
    KeywordV3LadderState,
    KeywordsPreparedList,
    UpdateContext,
    V3LadderStageKind,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.keyword_dto.dto.keyword_dto import (
    KeywordDTO,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.keyword_dto.dto.next_target_place import (
    NextTargetPlace,
)

if TYPE_CHECKING:
    from app.modules.shop_runner.service_manager.services.auto_updater_v3.keyword_v3_eligibility import (
        KeywordV3Eligibility,
    )
    from app.modules.shop_runner.service_manager.services.auto_updater_v3.keyword_v3_ladder_view import (
        LadderInputs,
    )
    from app.modules.shop_runner.service_manager.services.auto_updater_v3.selector import (
        KeywordV3Context,
    )


def _strategy_mode_for_stage(stage: V3LadderStageKind) -> KeywordStrategyMode:
    if stage == V3LadderStageKind.GAP:
        return KeywordStrategyMode.OFF
    return KeywordStrategyMode[stage.name]


def _stage_for_agg(mode: AggressionTargetMode) -> V3LadderStageKind:
    return V3LadderStageKind[mode.name]


def _is_gap_context(ctx: KeywordV3Context) -> bool:
    """GAP: нет операционного PFO и нет CH-профиля."""
    return is_keyword_no_data(ctx.keyword) and not bool(ctx.position_profile)


def _target_position_for_stage(
    *,
    stage: V3LadderStageKind,
    position: int | None,
    use_zero: bool,
) -> int:
    if stage in (V3LadderStageKind.OFF, V3LadderStageKind.GAP):
        return 0
    if use_zero or position is None or int(position) <= 0:
        return 0
    return max(0, int(position))


def _bootstrap_ladder_inputs(
    contexts: list[KeywordV3Context],
) -> LadderInputs:
    """Минимальный ``LadderInputs`` для сборки ladder states без рекурсии в ``prepared``."""
    from app.modules.shop_runner.service_manager.services.auto_updater_v3.keyword_v3_decision_data import (
        CampaignV3DecisionCache,
    )
    from app.modules.shop_runner.service_manager.services.auto_updater_v3.keyword_v3_ladder_view import (
        LadderInputs,
    )

    return LadderInputs(
        all_contexts=list(contexts),
        prepared=KeywordsPreparedList(keywords=[]),
        campaign_cache=CampaignV3DecisionCache.from_contexts(contexts),
    )


def build_ladder_states_for_context(
    ctx: KeywordV3Context,
    *,
    eligibility: KeywordV3Eligibility | None = None,
    ladder_inputs: LadderInputs | None = None,
    all_contexts: list[KeywordV3Context] | None = None,
) -> tuple[KeywordV3LadderState, ...]:
    """Ladder states одного ключа: OFF, GAP (если применимо), M/O/C через ``LadderInputs``."""
    ks_id = int(ctx.keyword.keyword_setting_original_id or 0)
    states: list[KeywordV3LadderState] = []

    states.append(
        KeywordV3LadderState(
            keyword_setting_id=ks_id,
            stage=V3LadderStageKind.OFF,
            strategy_mode=KeywordStrategyMode.OFF,
            target_position=0,
            cpo=None,
            is_valid=True,
        )
    )

    if _is_gap_context(ctx):
        states.append(
            KeywordV3LadderState(
                keyword_setting_id=ks_id,
                stage=V3LadderStageKind.GAP,
                strategy_mode=KeywordStrategyMode.OFF,
                target_position=0,
                cpo=None,
                is_valid=True,
            )
        )
        return tuple(states)

    if ladder_inputs is None:
        raise ValueError(
            "ladder_inputs is required for non-GAP ladder states; "
            "use _bootstrap_ladder_inputs(contexts) at the call site"
        )

    from app.modules.shop_runner.service_manager.services.auto_updater_v3.keyword_v3_ladder_view import (
        LadderCostSource,
        resolve_ladder_stage_display,
    )

    view = resolve_ladder_stage_display(
        ctx,
        ladder_inputs,
        eligibility=eligibility,
    )
    for agg_mode, stage_result in view.stages.items():
        stage_kind = _stage_for_agg(agg_mode)
        strategy_mode = _strategy_mode_for_stage(stage_kind)
        mc = stage_result.candidate
        position = mc.position if mc is not None else None
        use_zero = (
            stage_result.source == LadderCostSource.PAY_FOR_ORDER
            or (eligibility is not None and eligibility.target_place_fallback_zero)
        )
        states.append(
            KeywordV3LadderState(
                keyword_setting_id=ks_id,
                stage=stage_kind,
                strategy_mode=strategy_mode,
                target_position=_target_position_for_stage(
                    stage=stage_kind,
                    position=position,
                    use_zero=use_zero,
                ),
                cpo=stage_result.cost,
                is_valid=stage_result.is_valid,
                cost_imputed=stage_result.cost_imputed,
            )
        )
    return tuple(states)


def build_ladder_states_for_contexts(
    contexts: list[KeywordV3Context],
    *,
    eligibility_by_ks_id: dict[int, KeywordV3Eligibility] | None = None,
    ladder_inputs: LadderInputs | None = None,
) -> list[KeywordV3LadderState]:
    """Плоский список ladder states для каждого ключа."""
    if eligibility_by_ks_id is None and ladder_inputs is None:
        from app.modules.shop_runner.service_manager.services.auto_updater_v3.keyword_v3_eligibility import (
            build_eligibility_map,
        )

        eligibility_by_ks_id = build_eligibility_map(contexts)

    flat: list[KeywordV3LadderState] = []
    for ctx in contexts:
        ks_id = ctx.keyword.keyword_setting_original_id
        elig = (
            eligibility_by_ks_id.get(int(ks_id))
            if eligibility_by_ks_id is not None and ks_id is not None
            else None
        )
        flat.extend(
            build_ladder_states_for_context(
                ctx,
                eligibility=elig,
                ladder_inputs=ladder_inputs,
                all_contexts=contexts,
            )
        )
    return flat


def build_keyword_dto(
    ctx: KeywordV3Context,
    *,
    eligibility: KeywordV3Eligibility | None = None,
    ladder_inputs: LadderInputs | None = None,
    all_contexts: list[KeywordV3Context] | None = None,
) -> KeywordDTO:
    """Один ``KeywordDTO`` на ключ: stored/active + ``TargetPlaceMatrix``."""
    stored = stored_strategy_mode(ctx.keyword)
    states = build_ladder_states_for_context(
        ctx,
        eligibility=eligibility,
        ladder_inputs=ladder_inputs,
        all_contexts=all_contexts,
    )
    dto = KeywordDTO.from_context(ctx, ladder_states=states)
    place = ctx.keyword.target_place
    dto.current_target_place = NextTargetPlace(
        new_target_place=0 if place is None else int(place),
        executor_name="PrepareExecutor",
    )
    return dto


def build_keyword_prepared_row(
    ctx: KeywordV3Context,
    *,
    eligibility: KeywordV3Eligibility | None = None,
    ladder_inputs: LadderInputs | None = None,
    all_contexts: list[KeywordV3Context] | None = None,
) -> KeywordPreparedRow:
    """Legacy adapter поверх ``KeywordDTO``."""
    return build_keyword_dto(
        ctx,
        eligibility=eligibility,
        ladder_inputs=ladder_inputs,
        all_contexts=all_contexts,
    ).to_prepared_row()


def build_keywords_prepared_list(
    contexts: list[KeywordV3Context],
    *,
    eligibility_by_ks_id: dict[int, KeywordV3Eligibility] | None = None,
    ladder_inputs: LadderInputs | None = None,
) -> KeywordsPreparedList:
    """``KeywordsPreparedList`` на тик: stored == active, ladder states на ключ."""
    if eligibility_by_ks_id is None and ladder_inputs is None:
        from app.modules.shop_runner.service_manager.services.auto_updater_v3.keyword_v3_eligibility import (
            build_eligibility_map,
        )

        eligibility_by_ks_id = build_eligibility_map(contexts)

    if ladder_inputs is None:
        ladder_inputs = _bootstrap_ladder_inputs(contexts)

    dtos: list[KeywordDTO] = []
    for ctx in contexts:
        ks_id = ctx.keyword.keyword_setting_original_id
        elig = (
            eligibility_by_ks_id.get(int(ks_id))
            if eligibility_by_ks_id is not None and ks_id is not None
            else None
        )
        dtos.append(
            build_keyword_dto(
                ctx,
                eligibility=elig,
                ladder_inputs=ladder_inputs,
                all_contexts=contexts,
            )
        )
    return KeywordsPreparedList(keywords=dtos)


def assemble_update_context(
    contexts: list[KeywordV3Context],
    *,
    eligibility_by_ks_id: dict[int, KeywordV3Eligibility] | None = None,
    ladder_inputs: LadderInputs | None = None,
    adv_state: AdvState | None = None,
) -> UpdateContext:
    """Собрать ``UpdateContext``: ``prepared`` + ``adv_state``."""
    prepared = build_keywords_prepared_list(
        contexts,
        eligibility_by_ks_id=eligibility_by_ks_id,
        ladder_inputs=ladder_inputs,
    )
    state = adv_state if adv_state is not None else AdvState.empty()
    if adv_state is None and eligibility_by_ks_id is not None and ladder_inputs is not None:
        state = state.with_tick_inputs(
            eligibility_by_ks_id=eligibility_by_ks_id,
            ladder_inputs=ladder_inputs,
        )
    return UpdateContext(prepared=prepared, adv_state=state)


def update_context_from_prepared(
    prepared: KeywordsPreparedList | list[tuple["KeywordV3Context", KeywordStrategyMode]],
    *,
    adv_state: AdvState | None = None,
) -> UpdateContext:
    """Обернуть ``KeywordsPreparedList`` или legacy ``PreparedList`` в ``UpdateContext``."""
    state = adv_state if adv_state is not None else AdvState.empty()
    if not isinstance(prepared, KeywordsPreparedList):
        if isinstance(prepared, list):
            contexts = [ctx for ctx, _ in prepared]
            prepared = build_keywords_prepared_list(
                contexts,
                eligibility_by_ks_id=state.eligibility_by_ks_id,
                ladder_inputs=state.ladder_inputs,
            )
        else:
            raise TypeError(f"unsupported prepared type: {type(prepared)!r}")
    return UpdateContext(
        prepared=prepared,
        adv_state=state,
    )


def build_update_context(
    contexts: list[KeywordV3Context],
    *,
    eligibility_by_ks_id: dict[int, KeywordV3Eligibility] | None = None,
    ladder_inputs: LadderInputs | None = None,
    adv_state: AdvState | None = None,
) -> UpdateContext:
    """Legacy alias для ``assemble_update_context``."""
    return assemble_update_context(
        contexts,
        eligibility_by_ks_id=eligibility_by_ks_id,
        ladder_inputs=ladder_inputs,
        adv_state=adv_state,
    )
