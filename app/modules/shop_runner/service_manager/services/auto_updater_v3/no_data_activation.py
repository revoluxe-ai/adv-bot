"""Активация ключей без данных V3: MIN_CPA, ``target_place=0`` (мин. ставка WB), белый список.

N-state (preamble) — нет CH-матрицы **или** нельзя импутировать conv (см.
``keyword_v3_decision_data``). Недостаток только своей conv при наличии CH → агрегат РК /
max по соседним ключам, лестница M1/M2/M3.

**NO CH при NORMAL-кампании** (нет bid profile, но есть свой V2 CPO на ключе):

- tier ``KEYWORD_NO_CH_PROFILE_WITH_OWN_CONV`` — только MIN, ``target_place=0``;
- UP/trim/OVERSPEND: граница ``keyword.pay_for_order`` vs ``plan.max_pay_for_order``
  (как в UI), см. ``_no_ch_bootstrap_allowed_by_pay_for_order``,
  ``plan_no_ch_min_bootstrap_actions``, ``rollout_planner.plan_campaign_trim_by_max_state_cost``;
- ``resolve_keyword_v2_pay_for_order_cost`` — отдельная консервативная метрика (rating CPM),
  не подменяет ``pay_for_order`` в гейтах.

На уровне **кампании** — ``SalesStates.NO_DATA`` (``detect_campaign_state``): force MIN + target 0
для всех управляемых ключей **без** проверки ``pay_for_order`` на bootstrap.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
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
    """Что есть/нет для V3 по ключу (уровень данных + CH-матрица).

    ``has_v2_cpo`` — наличие **своего** V2 CPO (conv ключа + rating CPM), не imputed conv.
    Для CH+``RK_AGGREGATE``/``PEER_MAX`` updater использует ``effective_conv_for_v3``;
    ``has_v2_cpo=False`` при imputed conv не означает INVALID tier.
    """

    has_v2_cpo: bool
    has_ch_position_profile: bool
    v2_cpo_gap: str | None = None
    decision_tier: KeywordV3DecisionTier | None = None
    imputed_conv: bool = False

    @property
    def n_state(self) -> bool:
        """N-state: ``NO_CONV`` или нет CH без V2 CPO (bootstrap OFF→MIN).

        NO CH + V2 CPO — ``no_ch_min_only``, не n_state. CH + imputed / FULL / RK / PEER — лестница.
        """
        if self.no_ch_min_only:
            return False
        if self.decision_tier == KeywordV3DecisionTier.NO_CONV:
            return not self.has_ch_position_profile
        if not self.has_ch_position_profile:
            return not self.has_v2_cpo
        if self.imputed_conv:
            return False
        if self.decision_tier in (
            KeywordV3DecisionTier.FULL,
            KeywordV3DecisionTier.RK_AGGREGATE,
            KeywordV3DecisionTier.PEER_MAX,
        ):
            return False
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
        elif (
            self.has_ch_position_profile
            and self.decision_tier == KeywordV3DecisionTier.NO_CONV
        ):
            labels.append("conv: max CPO по РК (без имп. conv)")
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
    """Сводка для UI: CH-матрица, tier decision, флаг **своего** V2 CPO.

    Ветка ``peer_contexts is not None`` — для диагностики с контекстом РК; в prod loader
    пока вызывает без peers (один ключ). ``keyword_v2_pay_for_order_unavailable_with_conv``
    намеренно не пересчитывает V2 CPO с imputed conv — см. docstring там и module
    ``keyword_v3_decision_data``.
    """
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
    """Нет CPO для операционных guard'ов (N-state, ``target_place``).

    Доступен, если есть ``keyword.pay_for_order`` (полный CPM-каскад, в т.ч. bid_log)
    **или** ``resolve_keyword_v2_pay_for_order_cost`` (rating CPM без bid_log).

    Строгий «свой V2 CPO» для NO CH tier — ``keyword_has_v2_cpo`` /
    ``resolve_keyword_v2_pay_for_order_cost`` (без подстановки ``pay_for_order``).
    """
    if not isinstance(keyword, CalculatedKeyword):
        raise TypeError(
            "keyword_v2_pay_for_order_unavailable expects CalculatedKeyword, "
            f"got {type(keyword).__name__}"
        )
    if keyword.pay_for_order is not None:
        return False
    return resolve_keyword_v2_pay_for_order_cost(keyword) is None


def keyword_lacks_v3_decision_data(
    ctx: "KeywordV3Context",
    contexts: list["KeywordV3Context"],
) -> bool:
    """Ключ в N-state preamble: ``KEYWORD_INVALID`` (нет CH и нет V2 CPO для MIN).

    ``NO_CONV`` с CH — pessimistic ladder, не bootstrap здесь.
    """
    return _keyword_lacks_v3_decision_data(ctx, contexts)


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


def _plan_min_cpa_bootstrap_for_prepared(
    prepared: PreparedList,
    *,
    reason: str,
    include_entry: Callable[["KeywordV3Context", KeywordStrategyMode], bool],
) -> list[V3Action]:
    """Общий цикл bootstrap → MIN_CPA: OFF→UP; WL DOWN; auto FORCE_OFF+UP MIN.

    Args:
        prepared: контексты с текущим ``strategy_mode``.
        reason: код причины в ``V3Action``.
        include_entry: фильтр строк prepared (tier / campaign gate).
    """
    actions: list[V3Action] = []
    min_level = mode_level(KeywordStrategyMode.MIN_CPA)

    for ctx, mode in prepared:
        if not include_entry(ctx, mode):
            continue
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


def plan_campaign_no_data_bootstrap_safe(
    contexts: list["KeywordV3Context"],
) -> list[V3Action]:
    """CAMPAIGN_NO_DATA: управляемые ключи (auto/БС) строго → MIN_CPA, без O/C/M.

    Fixed/manual/protected (``hard_status`` 3/4+) не трогаем.
    """
    prepared = build_prepared_from_contexts(contexts)
    return _plan_min_cpa_bootstrap_for_prepared(
        prepared,
        reason=_DATA_BOOTSTRAP_REASON,
        include_entry=lambda _ctx, _mode: True,
    )


def _no_ch_bootstrap_allowed_by_pay_for_order(
    ctx: "KeywordV3Context",
    *,
    max_pay_for_order: float | None,
) -> bool:
    """NO CH: UP только если ``keyword.pay_for_order`` (как в карточке) ≤ max.

    Основная операционная граница для ``KEYWORD_NO_CH_PROFILE_WITH_OWN_CONV``;
    не путать с ``resolve_keyword_v2_pay_for_order_cost`` (rating CPM без bid_log).
    """
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
    """Safe-start helper: NO_CH + V2 CPO OFF → UP MIN (не вызывается из NORMAL orchestrator).

    В ``CAMPAIGN_NORMAL`` OFF→MIN для NO_CH — только ``plan_profitable_expansion``
    (V2 CPO ≤ resolve). Здесь — для ``CAMPAIGN_NO_DATA``-подобных сценариев и unit-тестов.
    """
    from app.modules.shop_runner.service_manager.services.auto_updater_v3.keyword_v3_eligibility import (
        KeywordDataTier,
        resolve_keyword_v3_eligibility,
    )

    peer_contexts = [ctx for ctx, _ in prepared]

    def _include_no_ch_entry(
        ctx: "KeywordV3Context",
        _mode: KeywordStrategyMode,
    ) -> bool:
        elig = resolve_keyword_v3_eligibility(ctx, peer_contexts)
        if elig.data_tier != KeywordDataTier.KEYWORD_NO_CH_PROFILE_WITH_OWN_CONV:
            return False
        return _no_ch_bootstrap_allowed_by_pay_for_order(
            ctx, max_pay_for_order=max_pay_for_order
        )

    return _plan_min_cpa_bootstrap_for_prepared(
        prepared,
        reason=_NO_CH_MIN_BOOTSTRAP_REASON,
        include_entry=_include_no_ch_entry,
    )


def plan_data_bootstrap_v3(
    contexts: list["KeywordV3Context"],
) -> list[V3Action]:
    """CAMPAIGN_NORMAL: INVALID bootstrap + опускание O/C/M до MIN (без NO_CH OFF→MIN)."""
    from app.modules.shop_runner.service_manager.services.auto_updater_v3.keyword_v3_eligibility import (
        KeywordDataTier,
        build_eligibility_map,
        can_target_mode,
        clamp_target_mode,
    )

    prepared = build_prepared_from_contexts(contexts)
    peer_contexts = [ctx for ctx, _ in prepared]
    eligibility_by_ks_id = build_eligibility_map(peer_contexts)
    actions = plan_no_data_keyword_actions(
        prepared, eligibility_by_ks_id=eligibility_by_ks_id
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
        elig = eligibility_by_ks_id.get(int(ks_id))
        if elig is None or elig.data_tier == KeywordDataTier.KEYWORD_INVALID:
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


def plan_no_data_keyword_actions(
    prepared: PreparedList,
    *,
    eligibility_by_ks_id: dict[int, "KeywordV3Eligibility"] | None = None,
) -> list[V3Action]:
    """N-state: MIN_CPA + min bid + белый список для ключей без V2 CPO / CH.

    - OFF (авто/БС) → UP MIN_CPA;
    - O/C на БС → DOWN MIN_CPA;
    - MIN_CPA/O/C на авто → FORCE_OFF + UP MIN_CPA (hard_status → БС).

    Args:
        eligibility_by_ks_id: если передан, INVALID tier без повторного resolve.
    """
    from app.modules.shop_runner.service_manager.services.auto_updater_v3.keyword_v3_eligibility import (
        KeywordDataTier,
    )

    actions: list[V3Action] = []
    min_level = mode_level(KeywordStrategyMode.MIN_CPA)

    peer_contexts = [ctx for ctx, _ in prepared]
    for ctx, mode in prepared:
        ks_id = ctx.keyword.keyword_setting_original_id
        if eligibility_by_ks_id is not None:
            if ks_id is None:
                continue
            elig = eligibility_by_ks_id.get(int(ks_id))
            if elig is None or elig.data_tier != KeywordDataTier.KEYWORD_INVALID:
                continue
        elif not keyword_lacks_v3_decision_data(ctx, peer_contexts):
            continue
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
