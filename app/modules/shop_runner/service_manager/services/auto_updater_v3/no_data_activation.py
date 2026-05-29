"""Активация ключей без данных V3: MIN_CPA, ``target_place=0`` (мин. ставка WB), белый список.

N-state (preamble) — нет CH-матрицы **или** нельзя импутировать conv (см.
``keyword_v3_decision_data``). Недостаток только своей conv при наличии CH → агрегат РК /
max по соседним ключам, лестница M1/M2/M3.

На уровне **кампании** — ``SalesStates.NO_DATA`` (``detect_campaign_state``).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING

from app.modules.common_slaves.wildberries.models.enums import KeywordStrategyMode
from app.modules.shop_runner.service_manager.services.auto_updater_v3.ladder import (
    mode_level,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.dto import (
    V3Action,
    V3ActionType,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.keyword_v3_decision_data import (
    KeywordV3DecisionTier,
    keyword_lacks_v3_decision_data as _keyword_lacks_v3_decision_data,
    keyword_v2_pay_for_order_unavailable_with_conv,
    resolve_keyword_v2_pay_for_order_cost,
    resolve_keyword_v3_decision,
    tier_label_ru,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.transition_ranking import (
    PreparedList,
    build_prepared_from_contexts,
)
from app.modules.wb_adv_updater.calculated_keywords_manager.dto.calculated_keyword import (
    CalculatedKeyword,
)
from app.modules.wb_adv_updater.calculated_keywords_manager.dto.position_profile_point import (
    PositionProfilePoint,
)
from app.modules.wb_adv_updater.calculated_keywords_manager.orders_per_1000_rub import (
    calc_orders_per_1000_rub,
    calc_pay_for_order,
)

if TYPE_CHECKING:
    from app.modules.shop_runner.service_manager.services.auto_updater_v3.selector import (
        KeywordV3Context,
    )
    from app.modules.shop_runner.service_manager.wb_shop_data_manager import ComplexAdv

logger = logging.getLogger(__name__)

# 0 = «нет целевой позиции из CH, торговать на min bid» (см. UpdateClusterBidsManager).
NO_DATA_TARGET_PLACE_FALLBACK: int = 0

_HARD_STATUS_AUTO_MODE = 1
_HARD_STATUS_WHITE_LIST = 2

_DATA_BOOTSTRAP_REASON = "data_bootstrap_safe"
_NO_DATA_REASON = "no_data_min_bid"
_NO_CH_MIN_BOOTSTRAP_REASON = "no_ch_min_bootstrap"


@dataclass(frozen=True, slots=True)
class KeywordV3DataDiagnostic:
    """Что есть/нет для V3 по ключу (уровень данных + CH-матрица)."""

    has_v2_cpo: bool
    has_ch_position_profile: bool
    v2_cpo_gap: str | None = None
    decision_tier: KeywordV3DecisionTier | None = None
    imputed_conv: bool = False

    @property
    def n_state(self) -> bool:
        """N-state: нет данных для лестницы (INVALID / нет conv без импутации).

        NO_CH + own conv / V2 CPO — не n_state: tier MIN-only, ``target_place=0``.
        """
        if not self.has_ch_position_profile:
            return not self.has_v2_cpo
        if self.decision_tier in (
            KeywordV3DecisionTier.NO_CH_MATRIX,
            KeywordV3DecisionTier.NO_CONV,
        ):
            return True
        return not self.has_v2_cpo

    @property
    def no_ch_min_only(self) -> bool:
        """NO CH + V2 CPO: только MIN, target 0, bootstrap в БС (не полный N-state)."""
        return not self.has_ch_position_profile and self.has_v2_cpo

    def missing_labels_ru(self) -> tuple[str, ...]:
        """Человекочитаемый список пробелов для UI и логов."""
        labels: list[str] = []
        if self.decision_tier is not None and self.imputed_conv:
            labels.append(f"conv: {tier_label_ru(self.decision_tier)} (импутация)")
        elif not self.has_v2_cpo:
            labels.append(self.v2_cpo_gap or "нет V2 CPO (себес. заказа)")
        if not self.has_ch_position_profile:
            labels.append("нет матрицы CH (bid profile по ключу)")
        return tuple(labels)


def diagnose_v2_cpo_gap(keyword: CalculatedKeyword) -> str | None:
    """Причина отсутствия V2 CPO или ``None``, если CPO считается."""
    if not keyword_v2_pay_for_order_unavailable(keyword):
        return None
    cpm = keyword.cpm
    if cpm is None or cpm <= 0:
        return "нет CPM (каскад ставок ключа)"
    conv = keyword.conv_views_to_orders
    if conv is None or conv <= 0:
        return "нет conv показ→заказ"
    return "нет заказов на 1000₽ (CPO не считается)"


def diagnose_keyword_v3_data(
    keyword: CalculatedKeyword,
    position_profile: list[PositionProfilePoint] | None,
    *,
    peer_contexts: list["KeywordV3Context"] | None = None,
) -> KeywordV3DataDiagnostic:
    """Сводка: уровень данных V3, CH-матрица, CPO с учётом импутации conv."""
    has_ch = not keyword_missing_ch_position_profile(position_profile)
    if peer_contexts is not None and has_ch:
        from app.modules.shop_runner.service_manager.services.auto_updater_v3.selector import (
            KeywordV3Context,
        )

        ctx = KeywordV3Context(keyword=keyword, position_profile=position_profile)
        decision = resolve_keyword_v3_decision(ctx, peer_contexts)
        eff = decision.effective_conv_views_to_orders
        has_v2 = not keyword_v2_pay_for_order_unavailable_with_conv(
            keyword, conv_views_to_orders=eff
        )
        return KeywordV3DataDiagnostic(
            has_v2_cpo=has_v2,
            has_ch_position_profile=True,
            v2_cpo_gap=diagnose_v2_cpo_gap(keyword) if not has_v2 else None,
            decision_tier=decision.tier,
            imputed_conv=decision.imputed,
        )
    has_v2 = not keyword_v2_pay_for_order_unavailable(keyword)
    decision_tier: KeywordV3DecisionTier | None = None
    if not has_ch and has_v2:
        decision_tier = KeywordV3DecisionTier.NO_CH_MATRIX
    return KeywordV3DataDiagnostic(
        has_v2_cpo=has_v2,
        has_ch_position_profile=has_ch,
        v2_cpo_gap=diagnose_v2_cpo_gap(keyword) if not has_v2 else None,
        decision_tier=decision_tier,
    )


def _hard_status_allows_up(hard_status: int) -> bool:
    """Авто (1) или белый список (2): можно UP/DOWN в N-state preamble."""
    return int(hard_status) in (_HARD_STATUS_AUTO_MODE, _HARD_STATUS_WHITE_LIST)


def keyword_missing_ch_position_profile(
    position_profile: list[PositionProfilePoint] | None,
) -> bool:
    """Нет матрицы ставок/позиций из CH для ключа."""
    return not position_profile


def keyword_v2_pay_for_order_unavailable(keyword: CalculatedKeyword) -> bool:
    """Нет CPO: conv из CH + CPM set_bid/stats (как rating), не каскад с bid_log."""
    if not isinstance(keyword, CalculatedKeyword):
        raise TypeError(
            "keyword_v2_pay_for_order_unavailable expects CalculatedKeyword, "
            f"got {type(keyword).__name__}"
        )
    return resolve_keyword_v2_pay_for_order_cost(keyword) is None


def keyword_lacks_v3_decision_data(
    ctx: "KeywordV3Context",
    contexts: list["KeywordV3Context"],
) -> bool:
    """Ключ в N-state preamble: нет CH или нет conv даже после импутации РК."""
    return _keyword_lacks_v3_decision_data(ctx, contexts)


def rebalance_ladder_points(
    keyword: CalculatedKeyword,
    mode: KeywordStrategyMode,
    *,
    position_profile: list[PositionProfilePoint] | None = None,
    contexts: list["KeywordV3Context"] | None = None,
) -> int:
    """Баллы gap-rebalance: N-state = 1; без своего V2 CPO = 1; иначе ``mode_level``."""
    profile = (
        keyword.position_profile if position_profile is None else position_profile
    )
    if contexts is not None:
        from app.modules.shop_runner.service_manager.services.auto_updater_v3.selector import (
            KeywordV3Context,
        )

        ctx = KeywordV3Context(keyword=keyword, position_profile=profile)
        if keyword_lacks_v3_decision_data(ctx, contexts):
            return 1
        if keyword_v2_pay_for_order_unavailable(keyword):
            return 1
        return mode_level(mode)
    if keyword_v2_pay_for_order_unavailable(keyword):
        return 1
    if keyword_missing_ch_position_profile(profile):
        return 1
    return mode_level(mode)


def split_prepared_by_v2_cpo(
    prepared: PreparedList,
) -> tuple[PreparedList, PreparedList]:
    """Разделить prepared на ключи с полными данными V3 и без (N-state).

    Returns:
        (with_v3_data, without_v3_data) — оба списка в формате PreparedList.
    """
    peer_contexts = [ctx for ctx, _ in prepared]
    with_data: PreparedList = []
    without_data: PreparedList = []
    for entry in prepared:
        ctx, _mode = entry
        if keyword_lacks_v3_decision_data(ctx, peer_contexts):
            without_data.append(entry)
        else:
            with_data.append(entry)
    return with_data, without_data


def _append_min_cpa_up(
    actions: list[V3Action],
    *,
    ks_id: int,
    reason: str = _NO_DATA_REASON,
) -> None:
    actions.append(
        V3Action(
            action=V3ActionType.UP,
            keyword_setting_id=ks_id,
            target_strategy_mode=KeywordStrategyMode.MIN_CPA,
            reason=reason,
        )
    )


def _append_force_off_then_up(
    actions: list[V3Action],
    *,
    ks_id: int,
    target_strategy_mode: KeywordStrategyMode,
    reason: str = _NO_DATA_REASON,
) -> None:
    """Сброс в OFF и UP на ``target_strategy_mode``: ``hard_status`` → белый список (2)."""
    actions.append(
        V3Action(
            action=V3ActionType.FORCE_OFF,
            keyword_setting_id=ks_id,
            reason=reason,
        )
    )
    actions.append(
        V3Action(
            action=V3ActionType.UP,
            keyword_setting_id=ks_id,
            target_strategy_mode=target_strategy_mode,
            reason=reason,
        )
    )


def _append_force_off_then_min_cpa(
    actions: list[V3Action],
    *,
    ks_id: int,
    reason: str = _NO_DATA_REASON,
) -> None:
    """Сброс в OFF и UP на MIN_CPA: ``hard_status`` → белый список (2)."""
    _append_force_off_then_up(
        actions,
        ks_id=ks_id,
        target_strategy_mode=KeywordStrategyMode.MIN_CPA,
        reason=reason,
    )


def plan_campaign_no_data_bootstrap_safe(
    contexts: list["KeywordV3Context"],
) -> list[V3Action]:
    """CAMPAIGN_NO_DATA: управляемые ключи (auto/БС) строго → MIN_CPA, без O/C/M.

    Fixed/manual/protected (``hard_status`` 3/4+) не трогаем.
    """
    prepared = build_prepared_from_contexts(contexts)
    actions: list[V3Action] = []
    min_level = mode_level(KeywordStrategyMode.MIN_CPA)
    reason = _DATA_BOOTSTRAP_REASON

    for ctx, mode in prepared:
        ks_id = ctx.keyword.keyword_setting_original_id
        if ks_id is None:
            continue
        hard_status = int(ctx.keyword.hard_status)
        if not _hard_status_allows_up(hard_status):
            continue

        if mode == KeywordStrategyMode.OFF:
            _append_min_cpa_up(actions, ks_id=ks_id, reason=reason)
        elif mode_level(mode) > min_level:
            if hard_status == _HARD_STATUS_WHITE_LIST:
                actions.append(
                    V3Action(
                        action=V3ActionType.DOWN,
                        keyword_setting_id=ks_id,
                        target_strategy_mode=KeywordStrategyMode.MIN_CPA,
                        reason=reason,
                    )
                )
            elif hard_status == _HARD_STATUS_AUTO_MODE:
                _append_force_off_then_min_cpa(actions, ks_id=ks_id, reason=reason)
        elif mode == KeywordStrategyMode.MIN_CPA:
            if hard_status == _HARD_STATUS_AUTO_MODE:
                _append_force_off_then_min_cpa(actions, ks_id=ks_id, reason=reason)

    return actions


def _no_ch_bootstrap_allowed_by_pay_for_order(
    ctx: "KeywordV3Context",
    *,
    max_pay_for_order: float | None,
) -> bool:
    """NO CH: UP только если ``keyword.pay_for_order`` (как в карточке) ≤ max."""
    pfo = ctx.keyword.pay_for_order
    if pfo is None:
        return False
    if max_pay_for_order is None:
        return True
    return float(pfo) <= float(max_pay_for_order)


def plan_no_ch_min_bootstrap_actions(
    prepared: PreparedList,
    *,
    max_pay_for_order: float | None = None,
) -> list[V3Action]:
    """NO_CH + V2 CPO: MIN + target 0 + БС для auto (нет CH-лестницы O/C/M).

    Аналог N-state bootstrap, но только для tier ``KEYWORD_NO_CH_PROFILE_WITH_OWN_CONV``.
    OFF → UP MIN, если ``pay_for_order`` ≤ ``max_pay_for_order``; иначе без UP.
    """
    from app.modules.shop_runner.service_manager.services.auto_updater_v3.keyword_v3_eligibility import (
        KeywordDataTier,
        resolve_keyword_v3_eligibility,
    )

    actions: list[V3Action] = []
    min_level = mode_level(KeywordStrategyMode.MIN_CPA)
    reason = _NO_CH_MIN_BOOTSTRAP_REASON
    peer_contexts = [ctx for ctx, _ in prepared]

    for ctx, mode in prepared:
        elig = resolve_keyword_v3_eligibility(ctx, peer_contexts)
        if elig.data_tier != KeywordDataTier.KEYWORD_NO_CH_PROFILE_WITH_OWN_CONV:
            continue
        ks_id = ctx.keyword.keyword_setting_original_id
        if ks_id is None:
            continue
        hard_status = int(ctx.keyword.hard_status)
        if not _hard_status_allows_up(hard_status):
            continue
        if not _no_ch_bootstrap_allowed_by_pay_for_order(
            ctx, max_pay_for_order=max_pay_for_order
        ):
            continue

        if mode == KeywordStrategyMode.OFF:
            _append_min_cpa_up(actions, ks_id=ks_id, reason=reason)
        elif mode_level(mode) > min_level:
            if hard_status == _HARD_STATUS_WHITE_LIST:
                actions.append(
                    V3Action(
                        action=V3ActionType.DOWN,
                        keyword_setting_id=ks_id,
                        target_strategy_mode=KeywordStrategyMode.MIN_CPA,
                        reason=reason,
                    )
                )
            elif hard_status == _HARD_STATUS_AUTO_MODE:
                _append_force_off_then_min_cpa(actions, ks_id=ks_id, reason=reason)
        elif mode == KeywordStrategyMode.MIN_CPA:
            if hard_status == _HARD_STATUS_AUTO_MODE:
                _append_force_off_then_min_cpa(actions, ks_id=ks_id, reason=reason)

    return actions


def plan_data_bootstrap_v3(
    contexts: list["KeywordV3Context"],
    *,
    include_no_ch_min_bootstrap: bool = True,
) -> list[V3Action]:
    """CAMPAIGN_NORMAL: keyword-level bootstrap (INVALID + опционально NO_CH MIN-only) + caps."""
    prepared = build_prepared_from_contexts(contexts)
    peer_contexts = [ctx for ctx, _ in prepared]
    actions = plan_no_data_keyword_actions(prepared)
    if include_no_ch_min_bootstrap:
        actions.extend(
            plan_no_ch_min_bootstrap_actions(prepared, max_pay_for_order=None)
        )

    from app.modules.shop_runner.service_manager.services.auto_updater_v3.keyword_v3_eligibility import (
        KeywordDataTier,
        can_target_mode,
        clamp_target_mode,
        resolve_keyword_v3_eligibility,
    )
    from app.modules.shop_runner.service_manager.services.auto_updater_v3.ladder import (
        mode_level,
    )

    min_level = mode_level(KeywordStrategyMode.MIN_CPA)
    covered: set[int] = {
        int(a.keyword_setting_id)
        for a in actions
        if a.keyword_setting_id is not None
    }

    for ctx, mode in prepared:
        ks_id = ctx.keyword.keyword_setting_original_id
        if ks_id is None or int(ks_id) in covered:
            continue
        if not _hard_status_allows_up(int(ctx.keyword.hard_status)):
            continue
        elig = resolve_keyword_v3_eligibility(ctx, peer_contexts)
        if elig.data_tier == KeywordDataTier.KEYWORD_INVALID:
            continue
        if mode_level(mode) <= min_level:
            continue
        cap = clamp_target_mode(elig, mode)
        if mode_level(cap) >= mode_level(mode):
            continue
        if not can_target_mode(elig, cap):
            cap = KeywordStrategyMode.MIN_CPA
        hard_status = int(ctx.keyword.hard_status)
        if hard_status == _HARD_STATUS_WHITE_LIST:
            actions.append(
                V3Action(
                    action=V3ActionType.DOWN,
                    keyword_setting_id=ks_id,
                    target_strategy_mode=cap,
                    reason="data_bootstrap_down",
                )
            )
        elif hard_status == _HARD_STATUS_AUTO_MODE:
            _append_force_off_then_up(
                actions,
                ks_id=ks_id,
                target_strategy_mode=cap,
                reason="data_bootstrap_down",
            )

    return actions


def plan_no_data_keyword_actions(prepared: PreparedList) -> list[V3Action]:
    """N-state: MIN_CPA + min bid + белый список для ключей без V2 CPO / CH.

    - OFF (авто/БС) → UP MIN_CPA;
    - O/C на БС → DOWN MIN_CPA;
    - MIN_CPA/O/C на авто → FORCE_OFF + UP MIN_CPA (hard_status → БС).
    """
    actions: list[V3Action] = []
    min_level = mode_level(KeywordStrategyMode.MIN_CPA)

    peer_contexts = [ctx for ctx, _ in prepared]
    for ctx, mode in prepared:
        if not keyword_lacks_v3_decision_data(ctx, peer_contexts):
            continue
        ks_id = ctx.keyword.keyword_setting_original_id
        if ks_id is None:
            continue
        hard_status = int(ctx.keyword.hard_status)

        if mode == KeywordStrategyMode.OFF:
            if not _hard_status_allows_up(hard_status):
                continue
            _append_min_cpa_up(actions, ks_id=ks_id)
        elif mode_level(mode) > min_level:
            if hard_status == _HARD_STATUS_WHITE_LIST:
                actions.append(
                    V3Action(
                        action=V3ActionType.DOWN,
                        keyword_setting_id=ks_id,
                        target_strategy_mode=KeywordStrategyMode.MIN_CPA,
                        reason=_NO_DATA_REASON,
                    )
                )
            elif hard_status == _HARD_STATUS_AUTO_MODE:
                _append_force_off_then_min_cpa(actions, ks_id=ks_id)
        elif mode == KeywordStrategyMode.MIN_CPA:
            if hard_status == _HARD_STATUS_AUTO_MODE:
                _append_force_off_then_min_cpa(actions, ks_id=ks_id)
            # MIN_CPA + БС: режим уже верный, target_place=0 в sync

    return actions


def plan_no_data_min_up_actions(prepared: PreparedList) -> list[V3Action]:
    """OFF без V2 CPO/CH → UP MIN_CPA.

    Только ``V3ActionType.UP`` (OFF → MIN_CPA). Полный N-state (DOWN / FORCE_OFF) —
    ``plan_no_data_keyword_actions``.
    """
    actions: list[V3Action] = []
    peer_contexts = [ctx for ctx, _ in prepared]
    for ctx, mode in prepared:
        if mode != KeywordStrategyMode.OFF:
            continue
        if not keyword_lacks_v3_decision_data(ctx, peer_contexts):
            continue
        if not _hard_status_allows_up(int(ctx.keyword.hard_status)):
            continue
        ks_id = ctx.keyword.keyword_setting_original_id
        if ks_id is None:
            continue
        _append_min_cpa_up(actions, ks_id=ks_id)
    return actions


def plan_no_data_activation_v3(
    contexts: list["KeywordV3Context"],
) -> list[V3Action]:
    """Alias: keyword bootstrap для NORMAL (см. ``plan_data_bootstrap_v3``)."""
    return plan_data_bootstrap_v3(contexts)


async def run_no_data_activation_v3(
    complex_adv: "ComplexAdv",
    *,
    contexts: list["KeywordV3Context"],
) -> list[V3Action]:
    """Legacy: спланировать no-data activation (flush — в orchestrator)."""
    actions = plan_no_data_activation_v3(contexts)
    if actions:
        logger.info(
            "[adv_id=%s] v3 no_data activation planned: actions=%s",
            complex_adv.adv_id,
            len(actions),
        )
    return actions
