
from urllib.parse import quote

from aiogram.enums import ParseMode
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from app.client_bot.user_interface.message_templates import Text, TextWithKeyboard
from scripts.users_csv_exporter.dto import UserDTO


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
            """
🚨 Почему реклама на Wildberries иногда ухудшает продажи?

Многие сталкивались с этим парадоксом:

— добавили ключ → 📉 позиции в поиске упали
— отключили дорогую рекламу → 💸 исчезли дешёвые заказы
— ставки растут → 🚫 продажи стоят на месте

На первый взгляд это выглядит нелогично.

Но причина в том, что реклама на Wildberries влияет не только на трафик.
Она меняет ранжирование карточки, а через него — конверсию, органику и рекомендации.

В результате реклама начинает менять поведение всей системы.

Я подробно разобрал эту механику в большой статье и показал:

• ⚠️ почему возникает «парадокс рекламы»
• 📊 как реклама влияет на органический рост карточки
• 🎯 почему управление через план продаж работает лучше ручных ставок
• 🤖 как WB Sky использует эту логику для автоматического управления рекламой

Если работаете с внутренней рекламой Wildberries — рекомендую прочитать.

📖 Статья: https://clck.ru/3SS5Bq

"""
        )

    @property
    def keyboard(self):
        shop_ids_str = ', '.join(self._selected_shop_ids)

        # ✅ ИЗМЕНЕНО ТОЛЬКО ТЕКСТ: короткий маркер без “диалога”
        draft = f"У меня вопрос...: {shop_ids_str}"

        url = f"https://clck.ru/3SS5Bq"
        return InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="Читать статью на VC.ru", url=url)]
            ]
        )
