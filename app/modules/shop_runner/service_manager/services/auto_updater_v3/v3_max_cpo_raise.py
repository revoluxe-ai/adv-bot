"""In-memory Raise MAX CPO для V3: рабочий max = fact CPO при toggle ON.

Только текущий тик/итерация: ORM не коммитится. Исходный max из настроек РК
до Raise живёт в ``PreComplexAdv.original_max_cpo`` / ``ComplexAdv.original_max_cpo``
(сборка в ``WBShopDataManager.get_pre_complex_advs``), не в runtime-атрибуте ``adv``.

На следующем тике ``AdvSetting.max_price_for_order`` снова приходит из БД.
"""

from __future__ import annotations

import math

from typing import TYPE_CHECKING

from app.modules.shop_runner.service_manager.services.auto_updater_v3.cpo_max_boundary import (
    cmp_over_max,
)

if TYPE_CHECKING:
    from app.modules.common_slaves.wildberries.models import AdvSetting


def operative_max_cpo_after_raise(fact: float, db_max: float) -> int:
    """Operative max (int) после Raise: ``ceil(fact)`` vs db, чтобы fact float не был ``>`` max.

    ``max_price_for_order`` в ORM — целое; fact CPO из CH — float. ``round`` мог опустить
    потолок ниже fact (150.4 → 150) и ложно включить overspend-gate.
    """
    return max(int(math.ceil(float(fact))), int(db_max))


def apply_v3_max_cpo_raise_if_needed(
    adv: AdvSetting,
    *,
    fact_pay_for_order: float | None,
    toggle_enabled: bool,
) -> bool:
    """Поднять ``max_price_for_order`` in-memory на текущий тик, если toggle ON и ``fact > db_max``.

    Args:
        adv: ORM-объект кампании (без commit в БД).
        fact_pay_for_order: fact CPO из plan-fact.
        toggle_enabled: ``AdvSetting.v3_substitute_fact_cpo_for_max``.

    Returns:
        ``True``, если operative max переписан in-memory для текущего тика V3.
    """
    if not toggle_enabled or fact_pay_for_order is None:
        return False
    db_max = adv.max_price_for_order
    if db_max is None:
        return False
    fact = fact_pay_for_order
    db = db_max
    if not cmp_over_max(fact, db):
        return False
    adv.max_price_for_order = operative_max_cpo_after_raise(fact, float(db))
    return True


def v3_raised_max_display_label(
    adv: AdvSetting,
    *,
    fact_pay_for_order: float | None,
    original_max_cpo: float | None = None,
) -> str | None:
    """Подпись ``db_max → fact`` для UI, если Raise активен и fact выше db max.

    ``original_max_cpo`` — исходный max из ``PreComplexAdv`` / ``ComplexAdv``;
    если не передан, используется ``adv.max_price_for_order`` (типично UI бота до Raise).
    """
    if not bool(getattr(adv, "v3_substitute_fact_cpo_for_max", False)):
        return None
    if fact_pay_for_order is None:
        return None
    db_max = (
        original_max_cpo if original_max_cpo is not None else adv.max_price_for_order
    )
    if db_max is None:
        return None
    fact = float(fact_pay_for_order)
    db = float(db_max)
    if not cmp_over_max(fact, db):
        return None
    return f"{db:g} → {fact:g}"
