
from urllib.parse import quote

from aiogram.enums import ParseMode
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from app.client_bot.user_interface.message_templates import Text, TextWithKeyboard
from scripts.users_csv_exporter.dto import UserDTO


MY_USERNAME = 'skyline360_1'


class Message(TextWithKeyboard):
    def __init__(self, bot, user: UserDTO):
        chat_id = user.telegram_id
        super().__init__(bot, chat_id)
        self.parse_mode: str = ParseMode.HTML

        self._user = user
        cabinets = list(user.cabinets or [])

        # сортировка по текущему тарифу (макс расходы)
        cabinets.sort(
            key=lambda c: c.tariff_total_per_month,
            reverse=True,
        )

        # берём максимум 2 кабинета
        selected = cabinets[:2]
        self._selected = selected
        self._selected_shop_ids = [cab.shop_id for cab in selected]

    @property
    def text(self) -> str | None:
        return (
            """📌 У вас активен тариф «Автоматика» в сервисе WB Skyline.
Я добавил функцию: автоматический расчёт целевого места отдельно для каждого ключа.

Это нужно, потому что ключи ведут себя по-разному: одному нужно быть выше, другой нормально работает ниже. Когда всем ставят одно место — получается перекос: где-то переплата, где-то недобор.

✅ Сейчас функция включена по умолчанию на «Автоматике». При желании можно отключить и сравнить “до/после”.

⚠️ Без баланса «Автоматика» не работает.

✅ Зайдите в бот → нажмите Старт → выберите магазин → Пополнить баланс
📌 Минимальная сумма пополнения — 5 000 ₽

Подробности — в посте на канале -> https://t.me/skyline_project/812 """
        )

    @property
    def keyboard(self):
        shop_ids_str = ', '.join(self._selected_shop_ids)

        # ✅ ИЗМЕНЕНО ТОЛЬКО ТЕКСТ: короткий маркер без “диалога”
        draft = f"У меня вопрос...: {shop_ids_str}"

        url = f"https://t.me/{MY_USERNAME}?text={quote(draft)}"
        return InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="Написать в поддержку", url=url)]
            ]
        )
