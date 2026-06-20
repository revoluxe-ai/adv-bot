"""V3 Raise MAX: side-effects при изменении max себестоимости заказа в плане продаж."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class MaxCpoDecreaseSideEffect:
    """Событие авто-выключения V3 Raise MAX из-за уменьшения max CPO."""

    adv_id: int
    old_max: int
    new_max: int


def resolve_flag_after_max_cpo_decrease(
    *,
    old_max: int | None,
    new_max: int | None,
    current_flag: bool,
    adv_id: int,
) -> tuple[bool, MaxCpoDecreaseSideEffect | None]:
    """Вернуть новое значение флага и side-effect, если max CPO уменьшен при включённом флаге.

    Args:
        old_max: Текущее ``max_price_for_order`` до изменения.
        new_max: Новое ``max_price_for_order``.
        current_flag: Текущее ``substitute_fact_cpo_for_max``.
        adv_id: ``AdvSetting.adv_id`` для уведомления.

    Returns:
        (новый флаг, side_effect или None).
    """
    if not current_flag:
        return current_flag, None
    if old_max is None or new_max is None:
        return current_flag, None
    if int(new_max) >= int(old_max):
        return current_flag, None
    return False, MaxCpoDecreaseSideEffect(
        adv_id=int(adv_id),
        old_max=int(old_max),
        new_max=int(new_max),
    )


def format_v3_raise_max_auto_disable_message(effect: MaxCpoDecreaseSideEffect) -> str:
    """Текст уведомления об авто-выключении V3 Raise MAX."""
    return (
        "Авто max CPO (V3 Raise) отключено: макс. себестоимость заказа уменьшена "
        f"с {effect.old_max} до {effect.new_max} (РК {effect.adv_id})."
    )


def format_v3_raise_max_toggle_message(*, enabled: bool) -> str:
    """Текст уведомления при ручном переключении тумблера."""
    if enabled:
        return "Авто max CPO (V3 Raise) включено."
    return "Авто max CPO (V3 Raise) отключено."


def skip_excel_substitute_fact_cpo_for_max(
    *,
    field: str,
    raise_max_auto_disabled: bool,
) -> bool:
    """Пропустить EDIT ``substitute_fact_cpo_for_max``, если max CPO уже сбросил флаг.

    Excel import применяет колонки в sorted-порядке: ``max_price_for_order`` идёт
    раньше ``substitute_fact_cpo_for_max``. Без skip ячейка TRUE из выгрузки
    повторно включит V3 Raise после авто-выключения при уменьшении max.
    """
    return raise_max_auto_disabled and field == "substitute_fact_cpo_for_max"
