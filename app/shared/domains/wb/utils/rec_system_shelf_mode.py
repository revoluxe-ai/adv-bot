"""Режим «полки» для авто-РК и правило предупреждения по балансу кликов."""

from __future__ import annotations

from typing import TYPE_CHECKING

from app.shared.domains.wb.utils.auto_campaign_cost_activity import (
    is_auto_campaign_active,
)

if TYPE_CHECKING:
    from app.modules.common_slaves.wildberries.models import AdvSetting
    from app.modules.shop_runner.service_manager.services.plan_fact_controller.plan_fact_reader import (
        PlanFactReader,
    )


async def is_rec_system_shelf_mode_operational(
    adv_setting: AdvSetting,
    *,
    plan_fact_reader: PlanFactReader | None = None,
    complex_adv: object | None = None,
) -> bool:
    """Полки операционны только при rec_system + started + cost-rule ``True``.

    ``complex_adv`` пробрасывается в cost-activity; без него overlay только
    если fraction уже пришит на ``adv_setting``.
    """
    if not adv_setting.rec_system_mode:
        return False
    if adv_setting.active_status != "started":
        return False
    active = await is_auto_campaign_active(
        adv_setting,
        plan_fact_reader=plan_fact_reader,
        complex_adv=complex_adv,
    )
    return active is True


def should_show_clicks_warning(
    *,
    shelves_operational: bool,
    adv_clicks: int,
    organic_clicks: int,
    shelf_clicks: int,
) -> bool:
    """Нужно ли показать предупреждение по перекосу рек. кликов относительно полки или органики."""
    if shelves_operational:
        return adv_clicks < shelf_clicks
    return adv_clicks < organic_clicks


def warning_suffix(show_warning: bool) -> str:
    """Суффикс строки в Telegram UI."""
    return " ⚠" if show_warning else ""
