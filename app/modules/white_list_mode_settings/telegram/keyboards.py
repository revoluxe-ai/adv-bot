from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from app.client_bot.user_interface.views.callbacks import Adv as ReturnToAdvCallback
from app.modules.common_slaves.wildberries.models import AdvSetting
from app.modules.common_slaves.wildberries.models.white_list_mode import WhiteListMode
from .main_callback import WhiteListModeToggle


class WhiteListModeKeyboards:
    def __init__(self, adv_setting: AdvSetting):
        self._adv_setting = adv_setting

    def build_keyboard(self) -> InlineKeyboardMarkup:
        builder = InlineKeyboardBuilder()

        labels = [
            "Срезание хвоста (Рек. для АвтоУправления)",
            "Активация только ключей из БС (Рек для Ручной работы)",
            "Свободная активация ключей (Устарело)",
        ]

        modes = [
            WhiteListMode.TAIL_TRIMMING,
            WhiteListMode.ACTIVE_ONLY_WHITE_LIST,
            WhiteListMode.ABOVE_MIN_RATING,
        ]

        current_mode = self._adv_setting.white_list_mode or WhiteListMode.TAIL_TRIMMING

        for label, mode in zip(labels, modes):
            prefix = "✅ " if mode == current_mode else ""
            builder.row(
                InlineKeyboardButton(
                    text=f"{prefix}{label}",
                    callback_data=WhiteListModeToggle(
                        new_mode=mode.name,
                        adv_setting_original_id=self._adv_setting.id,
                    ).pack(),
                )
            )

        builder.row(
            InlineKeyboardButton(
                text="Назад к настройкам АРК",
                callback_data=ReturnToAdvCallback(
                    adv_original_id=self._adv_setting.id,
                ).pack(),
            )
        )

        return builder.as_markup()
