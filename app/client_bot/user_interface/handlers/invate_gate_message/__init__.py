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
                    "Введите инвайт и получите бесплатный доступ к нашей системе "
                    "управления рекламой и продажами на WB.\n\n"
                    f"Если нет инвайт-кода, то можете попросить его в любом популярном "
                    f"чате для селлеров, например, здесь -> {CHAT_FOR_INVITES}" )

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
