from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from app.client_bot.ui_access import UiAccessMode
from app.client_bot.user_interface.views.callbacks import Adv as ReturnToAdvCallback
from app.modules.common_slaves.wildberries.models import AdvSetting
from app.modules.common_slaves.wildberries.models.white_list_mode import WhiteListMode
from .main_callback import WhiteListModeToggle

FREE_WHITE_LIST_MODES: tuple[WhiteListMode, ...] = (
    WhiteListMode.ACTIVE_ONLY_WHITE_LIST,
    WhiteListMode.ABOVE_MIN_RATING,
)


class WhiteListModeKeyboards:
    def __init__(
        self,
        adv_setting: AdvSetting,
        ui_access: UiAccessMode = UiAccessMode.PAID,
    ):
        self._adv_setting = adv_setting
        self._ui_access = ui_access

    def build_keyboard(self) -> InlineKeyboardMarkup:
        builder = InlineKeyboardBuilder()
        # TODO: "Срезание хвоста" - это доступно только для V2
        mode_rows = [
            (
                "Срезание хвоста",
                WhiteListMode.TAIL_TRIMMING,
            ),
            (
                "Срезание хвоста с Замещением (Для АвтоУправления)",
                WhiteListMode.REPLACE_ON_TRIM,
            ),
            (
                "Активация только ключей из БС (Рек для Ручной работы)",
                WhiteListMode.ACTIVE_ONLY_WHITE_LIST,
            ),
            (
                "Свободная активация ключей",
                WhiteListMode.ABOVE_MIN_RATING,
            ),
        ]
        if self._ui_access == UiAccessMode.FREE:
            mode_rows = [
                row for row in mode_rows if row[1] in FREE_WHITE_LIST_MODES
            ]

        current_mode = self._adv_setting.white_list_mode or WhiteListMode.ABOVE_MIN_RATING

        for label, mode in mode_rows:
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
