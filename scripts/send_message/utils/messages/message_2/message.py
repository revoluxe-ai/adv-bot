from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from app.client_bot.user_interface.message_templates import TextWithKeyboard
from urllib.parse import quote

MY_USERNAME = 'skyline360_1'

class Message(TextWithKeyboard):

    text = """
    Привет! Вижу, вы запускали рекламу через бота, но потом остановились.

За последние недели на Wildberries менялась открутка, и “старая” настройка у многих стала работать хуже. Я обновил логику перезапуска и могу быстро подсказать, как лучше перезапуститься (без созвонов).

Нажмите «Написать мне» — откроется чат со мной с готовым шаблоном.
Если решим делать тест — могу дать тестовый кредит до 1000₽ на 1 артикул (внутри сервиса), чтобы безопасно проверить схему.

    """

    @property
    def keyboard(self):
        draft = "Привет! Хочу консультацию по перезапуску рекламы."
        url = f"https://t.me/{MY_USERNAME}?text={quote(draft)}"
        return InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="✍️ Написать мне", url=url)]
        ])
