"""Клавиатура Telegram-меню настройки плана продаж.

Этот модуль строит только кнопки для редактирования sales-plan полей
кампании: план продаж в день, целевая себестоимость заказа и максимальная
себестоимость заказа.

Здесь намеренно нет логики ``normalize_automatic_version_ui`` и других
автоматических UI-преобразований: этот экран работает напрямую с текущими
значениями ``AdvSetting`` и не должен подменять или нормализовать версию UI.
"""

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from app.client_bot.user_interface.views.callbacks import Adv as ReturnToAdvCallback
from app.modules.common_slaves.wildberries.models import AdvSetting

from . import callbacks


class KeyboardsGetter:
    """Собирает кнопки для редактирования плана продаж кампании.

    Класс не делает никаких автоматических нормализаций UI-состояния. Его
    задача ограничена сборкой кнопок по уже загруженному ``AdvSetting``:
    текст кнопок зависит только от текущих sales-plan значений, а не от
    automatic version workflow.
    """

    def __set_data(
        self,
        adv: AdvSetting,
    ):
        self._adv = adv
        self._adv_id = adv.adv_id
        self._plan_for_sales_for_day = adv.plan_for_sales_for_day
        self._target_price_for_order = adv.target_price_for_order
        self._max_price_for_order = adv.max_price_for_order
        self._v3_substitute_fact_cpo_for_max = bool(
            getattr(adv, "substitute_fact_cpo_for_max", False)
        )
        self._raise_plan_on_promobonuses = bool(
            getattr(adv, "raise_plan_on_promobonuses", False)
        )

    def get_keyboard(
        self,
        adv: AdvSetting,
    ) -> InlineKeyboardMarkup:
        """Собрать inline-клавиатуру с текущими плановыми параметрами.

        Клавиатура строится напрямую из текущего ``AdvSetting``. Это важно:
        экран sales-plan settings не должен в этом месте нормализовать UI-
        версию, потому что такая логика относится к другому слою Telegram
        интерфейса и может менять поведение экранов, не связанных с плановыми
        параметрами.
        """
        self.__set_data(adv)
        builder = InlineKeyboardBuilder()

        setting_plan_for_sales_for_day_button = (
            self.get_setting_plan_for_sales_for_day_button()
        )
        builder.row(setting_plan_for_sales_for_day_button)

        target_price_for_order_button = self.get_setting_target_price_for_order_button()
        builder.row(target_price_for_order_button)

        setting_max_price_for_order = self.get_setting_max_price_for_order_button()
        builder.row(setting_max_price_for_order)

        builder.row(self.get_v3_raise_max_cpo_toggle_button())
        builder.row(self.get_raise_plan_on_promobonuses_toggle_button())

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

        callback = callbacks.ChangePlanSetting(
            target_point="change-plan-for-sales-for-day", adv_id=self._adv_id
        ).pack()

        button = InlineKeyboardButton(text=text, callback_data=callback)

        return button

    def get_setting_target_price_for_order_button(self):
        text = (
            "Задать Цел.Себес. Заказа"
            if not self._target_price_for_order
            else f"Изменить Цел.Себес. Заказа ({self._target_price_for_order})"
        )

        callback = callbacks.ChangePlanSetting(
            target_point="change-target-price-for-order", adv_id=self._adv_id
        ).pack()

        button = InlineKeyboardButton(text=text, callback_data=callback)

        return button

    def get_setting_max_price_for_order_button(self):
        base = (
            "Задать Макс.Себес. Заказа"
            if not self._max_price_for_order
            else f"Изменить Макс.Себес. Заказа ({self._max_price_for_order})"
        )
        text = base

        callback = callbacks.ChangePlanSetting(
            target_point="change-max-price-for-order", adv_id=self._adv_id
        ).pack()

        button = InlineKeyboardButton(text=text, callback_data=callback)

        return button

    def get_v3_raise_max_cpo_toggle_button(self) -> InlineKeyboardButton:
        """Тумблер V3 Raise MAX: поднятие operative max до fact CPO при overspend."""
        if self._v3_substitute_fact_cpo_for_max:
            text = "Выключить авто max CPO (V3 Raise)"
            new_status = False
        else:
            text = "Включить авто max CPO (V3 Raise)"
            new_status = True
        callback = callbacks.V3RaiseMaxCpoToggle(
            adv_id=self._adv_id,
            new_status=new_status,
        ).pack()
        return InlineKeyboardButton(text=text, callback_data=callback)

    def get_raise_plan_on_promobonuses_toggle_button(self) -> InlineKeyboardButton:
        """Тумблер RaisePlanOnPromobonuses: proportional overlay Plan/budget."""
        if self._raise_plan_on_promobonuses:
            text = "Выключить RaisePlanOnPromobonuses"
            new_status = False
        else:
            text = "Включить RaisePlanOnPromobonuses"
            new_status = True
        callback = callbacks.RaisePlanOnPromobonusesToggle(
            adv_id=self._adv_id,
            new_status=new_status,
        ).pack()
        return InlineKeyboardButton(text=text, callback_data=callback)
