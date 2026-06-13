"""SSOT сравнений с max CPO плана (производные ``max_price_for_order``).

Строгие границы: overspend / over — ``>``, within / below — ``<`` (без равенства на max).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.modules.common_slaves.wildberries.models import AdvSetting


def _is_real_number(value: object) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def cmp_over_max(value: float, max_cpo: float) -> bool:
    """Значение строго выше потолка max CPO (было ``>=`` → ``>``)."""
    if not (_is_real_number(value) and _is_real_number(max_cpo)):
        return False
    return float(value) > float(max_cpo)


def cmp_within_max(value: float, max_cpo: float) -> bool:
    """Значение строго ниже потолка max CPO (было ``<=`` → ``<``)."""
    if not (_is_real_number(value) and _is_real_number(max_cpo)):
        return False
    return float(value) < float(max_cpo)


def cmp_over_threshold(value: float, threshold: float) -> bool:
    """Строго выше порога, производного от max (headroom floor и т.п.)."""
    if not (_is_real_number(value) and _is_real_number(threshold)):
        return False
    return float(value) > float(threshold)


def campaign_cpo_over_max(
    fact_pay_for_order: float | None,
    max_pay_for_order: float,
) -> bool:
    """OVERSPEND кампании: ``fact_pay_for_order > max_pay_for_order``."""
    if fact_pay_for_order is None:
        return False
    return cmp_over_max(float(fact_pay_for_order), float(max_pay_for_order))


def keyword_pfo_over_max(pfo: float | None, max_pay: float) -> bool:
    """``keyword.pay_for_order`` строго выше max CPO плана."""
    if pfo is None:
        return False
    return cmp_over_max(float(pfo), float(max_pay))


def keyword_pfo_within_max(pfo: float | None, max_pay_for_order: float | None) -> bool:
    """Keyword PFO строго ниже max CPO плана."""
    if pfo is None or max_pay_for_order is None:
        return False
    return cmp_within_max(float(pfo), float(max_pay_for_order))


def ladder_cpo_within_ceiling(cpo: float, ceiling: float) -> bool:
    """CPO ступени лестницы строго ниже ceiling (= max CPO плана)."""
    return cmp_within_max(float(cpo), float(ceiling))


def campaign_db_max_for_overspend_gate(adv: AdvSetting) -> float | None:
    """Db max для overspend-gate (до in-memory Raise)."""
    db_max = getattr(adv, "v3_max_price_for_order_db", None)
    if db_max is not None:
        return float(db_max)
    raw = adv.max_price_for_order
    if raw is None:
        return None
    return float(raw)
