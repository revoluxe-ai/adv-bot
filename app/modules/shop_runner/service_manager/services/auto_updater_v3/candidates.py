"""Build MIN_CPA / OPTIMUM / MAX_CONVERSION candidates from a position profile."""

from __future__ import annotations

import math
from typing import TYPE_CHECKING

from app.modules.common_slaves.wildberries.models.enums import KeywordStrategyMode
from app.modules.shop_runner.service_manager.services.auto_updater_v3.dto import (
    AggressionTargetMode,
    ModeCandidate,
)

if TYPE_CHECKING:
    from app.modules.wb_adv_updater.calculated_keywords_manager.dto.calculated_keyword import (
        CalculatedKeyword,
    )
    from app.modules.wb_adv_updater.calculated_keywords_manager.dto.position_profile_point import (
        PositionProfilePoint,
    )


def _finite_pay(row: PositionProfilePoint) -> float | None:
    if row.pay_for_cart is None:
        return None
    if math.isinf(row.pay_for_cart):
        return None
    return float(row.pay_for_cart)


def build_mode_candidates(
    *,
    profile: list[PositionProfilePoint] | None,
    keyword_text: str,
) -> dict[AggressionTargetMode, ModeCandidate]:
    """Return three mode candidates; invalid if profile missing or unusable."""
    empty = {
        m: ModeCandidate(
            mode=m,
            is_valid=False,
            invalid_reason="no_position_profile",
        )
        for m in AggressionTargetMode
    }
    if not profile:
        return empty

    usable = [p for p in profile if p.predicted_conversion is not None and p.bid >= 0]
    if not usable:
        return {
            m: ModeCandidate(
                mode=m,
                is_valid=False,
                invalid_reason="no_conversion_points",
            )
            for m in AggressionTargetMode
        }

    # MIN_CPA: minimize pay_for_cart among finite rows
    finite_rows = [p for p in usable if _finite_pay(p) is not None]
    if not finite_rows:
        min_cpa = ModeCandidate(
            mode=AggressionTargetMode.MIN_CPA,
            is_valid=False,
            invalid_reason="no_finite_pay_for_cart",
        )
    else:
        best_min = min(finite_rows, key=lambda p: float(_finite_pay(p) or 0.0))
        min_cpa = ModeCandidate(
            mode=AggressionTargetMode.MIN_CPA,
            bid=float(best_min.bid),
            position=best_min.position,
            predicted_conversion=best_min.predicted_conversion,
            predicted_cpa=_finite_pay(best_min),
            economy_score=-float(_finite_pay(best_min) or 0.0),
            is_valid=True,
        )

    # MAX_CONVERSION
    best_conv = max(usable, key=lambda p: float(p.predicted_conversion or 0.0))
    max_conv = ModeCandidate(
        mode=AggressionTargetMode.MAX_CONVERSION,
        bid=float(best_conv.bid),
        position=best_conv.position,
        predicted_conversion=best_conv.predicted_conversion,
        predicted_cpa=_finite_pay(best_conv),
        conversion_score=float(best_conv.predicted_conversion or 0.0),
        is_valid=True,
    )

    # OPTIMUM: balance conv vs pay (simple heuristic)
    def optimum_score(p: PositionProfilePoint) -> float:
        conv = float(p.predicted_conversion or 0.0)
        pay = _finite_pay(p)
        if pay is None or pay <= 0:
            return -1.0
        return conv / (1.0 + pay)

    best_opt = max(usable, key=optimum_score)
    opt_score = optimum_score(best_opt)
    optimum = ModeCandidate(
        mode=AggressionTargetMode.OPTIMUM,
        bid=float(best_opt.bid),
        position=best_opt.position,
        predicted_conversion=best_opt.predicted_conversion,
        predicted_cpa=_finite_pay(best_opt),
        conversion_score=float(best_opt.predicted_conversion or 0.0),
        economy_score=opt_score,
        is_valid=opt_score > 0,
        invalid_reason=None if opt_score > 0 else "optimum_score_non_positive",
    )

    _ = keyword_text  # reserved for logging
    return {
        AggressionTargetMode.MIN_CPA: min_cpa,
        AggressionTargetMode.OPTIMUM: optimum,
        AggressionTargetMode.MAX_CONVERSION: max_conv,
    }

def stored_strategy_mode(kw: CalculatedKeyword) -> KeywordStrategyMode:
    return kw.keyword_setting.strategy_mode
