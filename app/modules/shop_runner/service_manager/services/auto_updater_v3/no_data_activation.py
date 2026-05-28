"""Активация ключей без данных V3: MIN_CPA, ``target_place=0`` (мин. ставка WB), белый список.

«Нет данных» на уровне **ключа** — нет V2 CPO **или** нет матрицы CH (``position_profile``):
это **разные источники** (статистика ключа vs bid profile nmid в CH). N-state, если не хватает
хотя бы одного; ``KeywordV3DataDiagnostic`` показывает, чего именно нет.

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
from app.modules.shop_runner.service_manager.services.auto_updater_v3.candidates import (
    stored_strategy_mode,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.dto import (
    V3Action,
    V3ActionType,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.transition_ranking import (
    PreparedList,
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

_NO_DATA_REASON = "no_data_min_bid"


@dataclass(frozen=True, slots=True)
class KeywordV3DataDiagnostic:
    """Что есть/нет для V3 по ключу (статистика V2 CPO и матрица CH — независимо)."""

    has_v2_cpo: bool
    has_ch_position_profile: bool
    v2_cpo_gap: str | None = None

    @property
    def n_state(self) -> bool:
        """N-state: нельзя построить решение по лестнице M/O/C."""
        return not self.has_v2_cpo or not self.has_ch_position_profile

    def missing_labels_ru(self) -> tuple[str, ...]:
        """Человекочитаемый список пробелов для UI и логов."""
        labels: list[str] = []
        if not self.has_v2_cpo:
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
) -> KeywordV3DataDiagnostic:
    """Сводка: V2 CPO из статистики и CH-матрица — отдельные проверки."""
    has_v2 = not keyword_v2_pay_for_order_unavailable(keyword)
    has_ch = not keyword_missing_ch_position_profile(position_profile)
    return KeywordV3DataDiagnostic(
        has_v2_cpo=has_v2,
        has_ch_position_profile=has_ch,
        v2_cpo_gap=diagnose_v2_cpo_gap(keyword) if not has_v2 else None,
    )


def _hard_status_allows_up(hard_status: int) -> bool:
    return int(hard_status) in (_HARD_STATUS_AUTO_MODE, _HARD_STATUS_WHITE_LIST)


def _hard_status_allows_force_off(hard_status: int) -> bool:
    return int(hard_status) in (_HARD_STATUS_AUTO_MODE, _HARD_STATUS_WHITE_LIST)


def keyword_missing_ch_position_profile(
    position_profile: list[PositionProfilePoint] | None,
) -> bool:
    """Нет матрицы ставок/позиций из CH для ключа."""
    return not position_profile


def keyword_v2_pay_for_order_unavailable(keyword: CalculatedKeyword) -> bool:
    """Нет CPO ключа по той же цепочке, что V2 (рейтинг / ``pay_for_order``).

    ``orders_per_1000_rub = conv_views_to_orders × 1_000_000 / CPM``;
    CPO = ``1000 / orders_per_1000_rub``. Если CPM неизвестен или заказов на 1000₽ нет —
    данных для экономического решения по ключу нет.

    Args:
        keyword: Рассчитанный ключ (CPM из каскада, conv из CH).

    Returns:
        True, если ``pay_for_order`` в V2 был бы ``None``.

    Raises:
        TypeError: если передан не ``CalculatedKeyword`` (например ORM ``KeywordSetting``).
    """
    if not isinstance(keyword, CalculatedKeyword):
        raise TypeError(
            "keyword_v2_pay_for_order_unavailable expects CalculatedKeyword, "
            f"got {type(keyword).__name__}"
        )
    if keyword.pay_for_order is not None:
        return False
    orders = calc_orders_per_1000_rub(
        keyword.conv_views_to_orders,
        keyword.cpm,
    )
    if orders is None:
        return True
    return calc_pay_for_order(orders) is None


def keyword_lacks_v3_decision_data(ctx: "KeywordV3Context") -> bool:
    """Ключ без данных для V3: нет V2 CPO или нет матрицы CH."""
    return diagnose_keyword_v3_data(ctx.keyword, ctx.position_profile).n_state


def rebalance_ladder_points(
    keyword: CalculatedKeyword,
    mode: KeywordStrategyMode,
    *,
    position_profile: list[PositionProfilePoint] | None = None,
) -> int:
    """Баллы gap-rebalance: ключ без V2 CPO / CH = 1, иначе ``mode_level``."""
    if keyword_v2_pay_for_order_unavailable(keyword):
        return 1
    profile = (
        keyword.position_profile if position_profile is None else position_profile
    )
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
    with_data: PreparedList = []
    without_data: PreparedList = []
    for entry in prepared:
        ctx, _mode = entry
        if keyword_lacks_v3_decision_data(ctx):
            without_data.append(entry)
        else:
            with_data.append(entry)
    return with_data, without_data


def _append_min_cpa_up(actions: list[V3Action], *, ks_id: int) -> None:
    actions.append(
        V3Action(
            action=V3ActionType.UP,
            keyword_setting_id=ks_id,
            target_strategy_mode=KeywordStrategyMode.MIN_CPA,
            reason=_NO_DATA_REASON,
        )
    )


def _append_force_off_then_min_cpa(
    actions: list[V3Action],
    *,
    ks_id: int,
) -> None:
    """Сброс в OFF и UP на MIN_CPA: ``hard_status`` → белый список (2)."""
    actions.append(
        V3Action(
            action=V3ActionType.FORCE_OFF,
            keyword_setting_id=ks_id,
            reason=_NO_DATA_REASON,
        )
    )
    _append_min_cpa_up(actions, ks_id=ks_id)


def plan_no_data_keyword_actions(prepared: PreparedList) -> list[V3Action]:
    """N-state: MIN_CPA + min bid + белый список для ключей без V2 CPO / CH.

    - OFF (авто/БС) → UP MIN_CPA;
    - O/C на БС → DOWN MIN_CPA;
    - MIN_CPA/O/C на авто → FORCE_OFF + UP MIN_CPA (hard_status → БС).
    """
    actions: list[V3Action] = []
    min_level = mode_level(KeywordStrategyMode.MIN_CPA)

    for ctx, mode in prepared:
        if not keyword_lacks_v3_decision_data(ctx):
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
            elif _hard_status_allows_force_off(hard_status):
                _append_force_off_then_min_cpa(actions, ks_id=ks_id)
        elif mode == KeywordStrategyMode.MIN_CPA:
            if hard_status == _HARD_STATUS_AUTO_MODE:
                _append_force_off_then_min_cpa(actions, ks_id=ks_id)
            # MIN_CPA + БС: режим уже верный, target_place=0 в sync

    return actions


# Обратная совместимость имён в тестах и selector.
plan_no_data_min_up_actions = plan_no_data_keyword_actions


def _build_prepared(
    contexts: list["KeywordV3Context"],
) -> PreparedList:
    prepared: PreparedList = []
    for ctx in contexts:
        prepared.append((ctx, stored_strategy_mode(ctx.keyword)))
    return prepared


def plan_no_data_activation_v3(
    contexts: list["KeywordV3Context"],
) -> list[V3Action]:
    """Спланировать N-state для ключей без V2 CPO / CH (без записи в БД)."""
    prepared = _build_prepared(contexts)
    return plan_no_data_keyword_actions(prepared)


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
