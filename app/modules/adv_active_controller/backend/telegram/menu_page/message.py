from aiogram import Bot
from aiogram.types import InlineKeyboardButton as _InlineKeyboardButton
from aiogram.types import InlineKeyboardMarkup as _InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder as _InlineKeyboardBuilder

from app.client_bot.user_interface.message_templates import (
    TextWithKeyboard as _TextWithKeyboard,
)
from app.modules.common_slaves.wildberries.models import AdvSetting as _AdvSetting
from .callbacks import NewAutoAdvStatus as _NewAutoAdvStatus
from .inner_modules.change_adding_balance_days_sum.callbacks import (
    ChangeAddingBalanceSum as _ChangeAddingBalanceSum,
)

__all__ = ["AdvActiveControllerMenu"]


class AdvActiveControllerMenu(_TextWithKeyboard):

    def __init__(self, adv: _AdvSetting, bot: Bot, chat_id: int) -> None:
        self._adv = adv
        super().__init__(bot, chat_id)

    @property
    def text(self) -> str:
        adv: _AdvSetting = self._adv

        if adv.auto_adv_target_status is None:
            auto_adv_status = "Не задан"
        elif adv.auto_adv_target_status:
            auto_adv_status = "Включать"
        else:
            auto_adv_status = "Выключать"

        if adv.auction_adv_target_status is None:
            auction_adv_status = "Не задан"
        elif adv.auction_adv_target_status:
            auction_adv_status = "Включать"
        else:
            auction_adv_status = "Выключать"

        text = (
            f"Название РК: {adv.name}"
            f"Активность Комплексной кампании кампании: {'Активна' if adv.bot_active else 'Неактивна'}\n"
            f"Артикул: {adv.nmids[0]}\n"
            f"ID Авто: {adv.adv_id}\n"
            f"ID Поиск: {adv.search_adv_id}\n"
            f"Поддерживать активность для Авто: {auto_adv_status}\n"
            f"Поддерживать активность для Аукциона: {auction_adv_status}\n"
            f"Максимальная сумма автопополнений в сутки: {adv.max_balance_adding_for_day} ₽"
        )
        return text

    @property
    def keyboard(self) -> _InlineKeyboardMarkup:
        adv: _AdvSetting = self._adv
        builder = _InlineKeyboardBuilder()

        target_adv = "auto"
        if not adv.auto_adv_target_status:
            text = "Включать Автокампанию"
            new_status = True
        else:
            text = "Выключать Автокампанию"
            new_status = False
        button = _InlineKeyboardButton(
            text=text,
            callback_data=_NewAutoAdvStatus(
                adv_setting_original_id=adv.adv_id,
                target_adv=target_adv,
                new_status=new_status,
            ).pack(),
        )
        builder.row(button)

        target_adv = "auction"
        if not adv.auction_adv_target_status:
            text = "Включать Аукцион"
            new_status = True
        else:
            text = "Выключать Аукцион"
            new_status = False

        button = _InlineKeyboardButton(
            text=text,
            callback_data=_NewAutoAdvStatus(
                adv_setting_original_id=adv.adv_id,
                target_adv=target_adv,
                new_status=new_status,
            ).pack(),
        )

        builder.row(button)

        adding_setting_sum = adv.max_balance_adding_for_day or 0

        button = _InlineKeyboardButton(
            text=f"Изменить максимальную сумму автопополнений в сутки ({adding_setting_sum})",
            callback_data=_ChangeAddingBalanceSum(
                adv_setting_original_id=adv.adv_id,
            ).pack(),
        )

        builder.row(button)

        return builder.as_markup()
