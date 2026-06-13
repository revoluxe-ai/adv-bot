from aiogram.types import InlineKeyboardButton

from app.client_bot.user_interface.views.messages.utils.sales_plan import get_plan_set_status
from app.modules.common_slaves.wildberries.models import AdvSetting
from app.modules.sales_plan_settings.telegram.main_callback import (
    SalesPlanSettingsMenu as SalesPlanSettingsMenuCallback,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.v3_max_cpo_raise import (
    v3_raised_max_display_label,
)


def get(adv_setting: AdvSetting, *, fact_pay_for_order: float | None = None) -> InlineKeyboardButton:
    """Кнопка «План продаж»; при активном Raise MAX — ``db → fact`` в подписи."""
    status = get_plan_set_status(adv_setting)
    prefix_status_str = "🎯" if status else "⛔"
    post_fix_status_str = "" if status else "Не установлен"
    raise_label = v3_raised_max_display_label(
        adv_setting,
        fact_pay_for_order=fact_pay_for_order,
    )
    raise_suffix = f" [{raise_label}]" if raise_label else ""
    button = InlineKeyboardButton(
        text=f"{prefix_status_str} План продаж {post_fix_status_str}{raise_suffix}",
        callback_data=SalesPlanSettingsMenuCallback(adv_id=adv_setting.adv_id).pack(),
    )
    return button



