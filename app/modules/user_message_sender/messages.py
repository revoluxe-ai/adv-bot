from aiogram.types import InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

from app.client_bot.user_interface.message_templates import TextWithKeyboard
from app.client_bot.user_interface.views import callbacks


class NotAnyUsesAndNotMoneyOnBalance(TextWithKeyboard):
    text = """
Почти потерялись😳

Но все в порядке, я про тебя помню) И никогда не забуду растить ROI наших РК

Seller's Pub - уникальный сервис для ВБ✅

Просто отправляешь артикул, задаешь направление и забываешь про оптимизацию.

Всего за 299 рублей 💰

На ВБ выигрывает самый быстрый, чего ты ждешь? Попробуй.

Я в себе уверен, если не увидишь результат - деньги вернутся на счет

Остались вопросы или что-то не получается? Пиши мне по этому контакту -> https://t.me/Vadyanc

Твой список магазинов:👇
    """

    @property
    def keyboard(self):
        builder = InlineKeyboardBuilder()
        button = InlineKeyboardButton(
            text="Перейти в главное меню",
            callback_data=callbacks.Start().pack(),
        )

        builder.row(button)
        return builder.as_markup()
