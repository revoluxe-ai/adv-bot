from aiogram.types import InlineKeyboardButton

from app.client_bot.user_interface.views.messages.utils.sales_plan import get_plan_set_status
from app.modules.common_slaves.wildberries.models import AdvSetting
from app.modules.sales_plan_settings.telegram.main_callback import (
    SalesPlanSettingsMenu as SalesPlanSettingsMenuCallback,
)

def get(adv_setting: AdvSetting) -> InlineKeyboardButton:

    status = get_plan_set_status(adv_setting)
    prefix_status_str = '🎯' if status else '⛔'
    post_fix_status_str = '' if status else 'Не установлен'
    button = InlineKeyboardButton(
        text=f"{prefix_status_str} План продаж {post_fix_status_str}",
        callback_data=SalesPlanSettingsMenuCallback(adv_id=adv_setting.adv_id).pack(),
    )
    return button



