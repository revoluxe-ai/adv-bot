from aiogram.enums import ParseMode
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from app.client_bot.const import OFFERTA_URL, CHAT_FOR_INVITES
from app.client_bot.user_interface.message_templates import Text, TextWithKeyboard
from app.client_bot.user_interface.views.callbacks import Gate


class InviteGateMessage(TextWithKeyboard):
    parse_mode = ParseMode.HTML
    def __init__(self, bot, chat_id):
        self._user_id = chat_id
        super().__init__(bot, chat_id)


    @property
    def text(self):
        return  (f"Ваш Telegram ID: <code>{self._user_id}</code>\n\n"
                     "🚀 Бесплатный бот для рекламы Wildberries с возможностью полного автоуправления\n\n"
                "Подключите токен WB и управляйте рекламой из бота: кампании, ставки, ключи, бюджеты, "
                "ручные настройки и Excel — бесплатно.\n\n"
                "Бесплатный режим — если хотите управлять рекламой сами, но быстрее и удобнее.\n\n"
                "Платный режим — если хотите, чтобы рекламу вёл бот: он сам работает со ставками, "
                "стратегией ключевых запросов и настройками кампаний по заданным целям.\n\n"
                "Чтобы войти, нажмите «Ввести инвайт» и отправьте инвайт-код.\n\n"
                f"Нет инвайта? Запросите его в чате селлеров: {CHAT_FOR_INVITES}\n"
                "Напишите там: «Нужен инвайт в бот МаркетОпс»." )

    @property
    def keyboard(self) -> InlineKeyboardMarkup:
        """Клавиатура экрана гейта: по одной кнопке на строке."""
        return InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="Ввести инвайт",
                        callback_data=Gate(action="invite_enter").pack(),
                    )
                ],
            ]
        )
