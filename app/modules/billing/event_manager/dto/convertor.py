from typing import Any

from app.modules.wb_adv_updater.modules.balance_exp_informer.dto import ReminderItem


def build_balance_reminder_payload(reminder_item: ReminderItem) -> dict[str, Any]:
    return {
        "reminder_id": reminder_item.reminder_id,
        "shop_name": reminder_item.shop_name,
        "level": reminder_item.level,
        "balance": reminder_item.balance,
        "avg_daily_spend": reminder_item.avg_daily_spend,
        "days_left": reminder_item.days_left,
    }
