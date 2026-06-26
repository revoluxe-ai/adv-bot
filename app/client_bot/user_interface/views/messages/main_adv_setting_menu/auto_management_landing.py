"""Paid-landing автоуправления рекламой для меню кампании."""

from __future__ import annotations

from aiogram import Bot
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from app.client_bot import const
from app.client_bot.user_interface.message_templates.templates import TextWithKeyboard
from app.client_bot.user_interface.views import callbacks
from app.modules.common_slaves.wildberries.models import AdvSetting, WBUserCabinet


class AutoManagementLanding(TextWithKeyboard):
    """Короткий landing-экран автоуправления рекламой по выбранной кампании."""

    parse_mode = "HTML"

    def __init__(
        self,
        bot: Bot,
        chat_id: int,
        wb_user_cabinet: WBUserCabinet,
        adv_setting: AdvSetting,
    ) -> None:
        self._wb_user_cabinet = wb_user_cabinet
        self._adv_setting: AdvSetting = adv_setting
        super().__init__(bot, chat_id)

    @property
    def text(self) -> str:
        status = (
            "🟢 <b>Автоуправление включено</b>"
            if self._adv_setting.bot_active
            else "🔴 <b>Автоуправление выключено</b>"
        )
        return (
            f"{status}\n\n"
            "Бесплатный режим уже позволяет вручную управлять рекламой: "
            "смотреть кампании, менять ставки, ключевые фразы, бюджеты, поддерживать позиции"
            " и работать через Excel.\n\n"
            "Платный режим включает <b>автоуправление рекламой</b>: бот сам управляет "
            "ставками и стратегией ключевых запросов по настройкам кампании.\n\n"
            "Если для Auto, поиска и полок настроены доступные режимы автоуправления, "
            "бот будет использовать их после включения.\n\n"
            "Для запуска нужен <b>токен с возможностью изменений в кабинете</b> и "
            "<b>нужные права токена</b>. Если у вас <b>токен только для чтения</b>, "
            "включение будет заблокировано.\n\n"
            "Также нужен баланс и доступный тариф. После включения бот начнёт "
            "управлять рекламой по текущим настройкам кампании. \n\n"
            f"В платный тариф входит профессиональная поддержка и обучение ведению РК, подробности: {const.SUPPORT_LINK}"
        )

    @property
    def keyboard(self) -> InlineKeyboardMarkup:
        toggle_text = (
            "⏸ Выключить автоуправление"
            if self._adv_setting.bot_active
            else "✅ Включить автоуправление"
        )
        toggle_action = "off" if self._adv_setting.bot_active else "on"
        return InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text=toggle_text,
                        callback_data=callbacks.TurnBot(
                            action=toggle_action,
                            adv_original_id=self._adv_setting.id,
                            wb_user_cabinet_original_id=self._wb_user_cabinet.id,
                        ).pack(),
                    )
                ],
                [
                    InlineKeyboardButton(
                        text="💳 Пополнить баланс",
                        callback_data=callbacks.AddBalance(
                            wb_cabinet_original_id=self._wb_user_cabinet.wb_cabinet_id
                        ).pack(),
                    )
                ],
                [
                    InlineKeyboardButton(
                        text="❓ Как работает автоуправление",
                        callback_data=callbacks.AutoManagementLanding(
                            action="how",
                            adv_setting_original_id=self._adv_setting.id,
                            wb_user_cabinet_original_id=self._wb_user_cabinet.id,
                        ).pack(),
                    )
                ],
                [
                    InlineKeyboardButton(
                        text="⬅️ Назад",
                        callback_data=callbacks.AutoManagementLanding(
                            action="back",
                            adv_setting_original_id=self._adv_setting.id,
                            wb_user_cabinet_original_id=self._wb_user_cabinet.id,
                        ).pack(),
                    )
                ],
            ]
        )


class AutoManagementHowItWorks(TextWithKeyboard):
    """Подробное объяснение различий бесплатного и платного режимов."""

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
        return (
            "<b>Как работает автоуправление рекламой</b>\n\n"
            "Бесплатный режим: пользователь сам смотрит кампании, ставки, ключевые фразы, "
            "бюджеты, Excel и вручную меняет настройки.\n\n"
            "Платный режим: бот сам ведёт рекламу.\n\n"
            "В поисковой кампании бот может управлять общей ставкой и стратегией ключевых запросов.\n"
            "По ключевым запросам бот определяет стратегию, целевое место и ставку для достижения цели.\n"
            "В Auto бот может подбирать тестовые и основные ставки.\n"
            "Для полок и рекомендательных мест используются отдельные настройки, если они доступны и включены.\n\n"
            "Автоуправление не заменяет экономику товара: карточка, цена, остатки, конверсия "
            "и план продаж всё равно важны.\n\n"
            "Для старта нужны корректные настройки кампании, токен с возможностью изменений "
            "в кабинете, нужные права токена и баланс."
        )

    @property
    def keyboard(self) -> InlineKeyboardMarkup:
        return InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="⬅️ Назад",
                        callback_data=callbacks.AutoManagementLanding(
                            action="open",
                            adv_setting_original_id=self._adv_setting.id,
                            wb_user_cabinet_original_id=self._wb_user_cabinet.id,
                        ).pack(),
                    )
                ]
            ]
        )
