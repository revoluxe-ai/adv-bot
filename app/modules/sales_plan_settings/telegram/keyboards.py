from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from app.client_bot.user_interface.views.callbacks import Adv as ReturnToAdvCallback
from app.modules.common_slaves.wildberries.models import AdvSetting

from . import callbacks


class KeyboardsGetter:
    def __set_data(self, adv: AdvSetting):
        self._adv_id = adv.adv_id
        self._plan_for_sales_for_day = adv.plan_for_sales_for_day
        self._target_price_for_order = adv.target_price_for_order
        self._max_price_for_order = adv.max_price_for_order

    def get_keyboard(self, adv: AdvSetting) -> InlineKeyboardMarkup:
        self.__set_data(adv)
        builder = InlineKeyboardBuilder()

        setting_plan_for_sales_for_day_button = self.get_setting_plan_for_sales_for_day_button()
        builder.row(setting_plan_for_sales_for_day_button)

        target_price_for_order_button = self.get_setting_target_price_for_order_button()
        builder.row(target_price_for_order_button)

        setting_max_price_for_order = self.get_setting_max_price_for_order_button()
        builder.row(setting_max_price_for_order)

        builder.row(
            InlineKeyboardButton(
                text="К настройкам АРК",
                callback_data=ReturnToAdvCallback(adv_original_id=int(adv.id)).pack(),
            )
        )

        return builder.as_markup()

    def get_setting_plan_for_sales_for_day_button(self):
        text = (
            "Задать продажи в день"
            if not self._plan_for_sales_for_day
            else f"Изменить план продаж в день ({self._plan_for_sales_for_day})"
        )

        callback = callbacks.ChangePlanSetting(target_point="change-plan-for-sales-for-day", adv_id=self._adv_id).pack()

        button = InlineKeyboardButton(text=text, callback_data=callback)

        return button

    def get_setting_target_price_for_order_button(self):
        text = (
            "Задать Цел.Себес. Заказа"
            if not self._target_price_for_order
            else f"Изменить Цел.Себес. Заказа ({self._target_price_for_order})"
        )

        callback = callbacks.ChangePlanSetting(target_point="change-target-price-for-order", adv_id=self._adv_id).pack()

        button = InlineKeyboardButton(text=text, callback_data=callback)

        return button

    def get_setting_max_price_for_order_button(self):
        text = (
            "Задать Макс.Себес. Заказа"
            if not self._max_price_for_order
            else f"Изменить Макс.Себес. Заказа ({self._max_price_for_order})"
        )

        callback = callbacks.ChangePlanSetting(target_point="change-max-price-for-order", adv_id=self._adv_id).pack()

        button = InlineKeyboardButton(text=text, callback_data=callback)

        return button
