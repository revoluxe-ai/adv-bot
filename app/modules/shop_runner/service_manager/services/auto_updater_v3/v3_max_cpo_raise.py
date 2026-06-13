"""In-memory Raise MAX CPO для V3: рабочий max = fact CPO при toggle ON.

Только текущий тик/итерация: ORM не коммитится, колонки для snapshot max нет.
На следующем тике ``AdvSetting.max_price_for_order`` снова приходит из БД.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from app.modules.shop_runner.service_manager.services.auto_updater_v3.cpo_max_boundary import (
    cmp_over_max,
)

if TYPE_CHECKING:
    from app.modules.common_slaves.wildberries.models import AdvSetting

# In-memory атрибут AdvSetting (не ORM): исходный max из БД до Raise.
V3_MAX_PRICE_FOR_ORDER_DB_ATTR = "v3_max_price_for_order_db"


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
        ``True``, если max переписан in-memory; db max сохранён в
        ``v3_max_price_for_order_db`` (runtime snapshot, не ORM-колонка).
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
    raised = max(fact, db)
    setattr(adv, V3_MAX_PRICE_FOR_ORDER_DB_ATTR, db)
    adv.max_price_for_order = int(round(raised, 0))
    return True


def v3_max_raise_db_value(adv: AdvSetting) -> float | None:
    """Runtime snapshot db max на текущем тике после Raise; иначе ``None``."""
    raw = getattr(adv, V3_MAX_PRICE_FOR_ORDER_DB_ATTR, None)
    if raw is None:
        return None
    return float(raw)


def v3_raised_max_display_label(
    adv: AdvSetting,
    *,
    fact_pay_for_order: float | None,
) -> str | None:
    """Подпись ``db_max → raised_max`` для UI, если Raise активен на текущем fact."""
    if not bool(getattr(adv, "v3_substitute_fact_cpo_for_max", False)):
        return None
    db_max = adv.max_price_for_order
    if db_max is None or fact_pay_for_order is None:
        return None
    fact = float(fact_pay_for_order)
    db = float(db_max)
    if not cmp_over_max(fact, db):
        return None
    return f"{db:g} → {fact:g}"
