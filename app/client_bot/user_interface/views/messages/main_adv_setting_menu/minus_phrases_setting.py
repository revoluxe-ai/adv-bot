"""Campaign-menu screen for configuring background minus-phrase updates."""

from __future__ import annotations

from aiogram import Bot
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from app.client_bot.user_interface.message_templates.templates import TextWithKeyboard
from app.client_bot.user_interface.views import callbacks
from app.modules.common_slaves.wildberries.models import AdvSetting, WBUserCabinet


class MinusPhrasesSettingScreen(TextWithKeyboard):
    """Explain and toggle the dedicated minus-phrase background sync flag."""

    parse_mode = "HTML"

    def __init__(
        self,
        bot: Bot,
        chat_id: int,
        wb_user_cabinet: WBUserCabinet,
        adv_setting: AdvSetting,
    ) -> None:
        self._wb_user_cabinet = wb_user_cabinet
        self._adv_setting = adv_setting
        super().__init__(bot, chat_id)

    @property
    def text(self) -> str:
        status = (
            "🟢 <b>Обновление минус-фраз включено</b>"
            if self._adv_setting.auto_update_minus_phrases
            else "🔴 <b>Обновление минус-фраз выключено</b>"
        )
        return (
            f"{status}\n\n"
            "Эта настройка управляет обновлением минус-фраз в кабинете WB.\n\n"
            "Если настройка включена, бот может менять минус-фразы в кампании.\n\n"
            "Для новых РК по умолчанию она выключена для безопасного старта.\n\n"
            "После активации данной функции в система обновит минус-фразы для этой РК в кабинете WB.\n"
            "Рекомендуется предварительно загрузить в бот"
            " Белый список на основе активных ключей и статистики"
            " скорректировать его, а затем включить данную функцию"
        )

    @property
    def keyboard(self) -> InlineKeyboardMarkup:
        toggle_text = (
            "⏸ Выключить обновление минус-фраз"
            if self._adv_setting.auto_update_minus_phrases
            else "✅ Включить обновление минус-фраз"
        )
        toggle_action = "off" if self._adv_setting.auto_update_minus_phrases else "on"
        return InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text=toggle_text,
                        callback_data=callbacks.MinusPhrasesSetting(
                            action=toggle_action,
                            adv_setting_original_id=self._adv_setting.id,
                            wb_user_cabinet_original_id=self._wb_user_cabinet.id,
                        ).pack(),
                    )
                ],
                [
                    InlineKeyboardButton(
                        text="⬅️ Назад",
                        callback_data=callbacks.MinusPhrasesSetting(
                            action="back",
                            adv_setting_original_id=self._adv_setting.id,
                            wb_user_cabinet_original_id=self._wb_user_cabinet.id,
                        ).pack(),
                    )
                ],
            ]
        )
