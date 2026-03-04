



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
            """
📌 Вебинар — 24.02 в 12:00 МСК
Как управлять рекламой на полках Wildberries без слива бюджета

Разберём:
— почему при нормальном бюджете показы могут быть низкими
— как ставка влияет на распределение трафика в рекомендательных системах
— какие правила помогают держать экономику и не сливать

✅ Регистрация: https://clck.ru/3RtwNV
Запись получат только зарегистрированные.

⚡️ СРОЧНО: кому нужно включение режима “Полки” до вебинара — ответьте «СРОЧНО».
 Возьму 3–5 кабинетов (нужен бюджет от 1000 ₽/день и целевой CPO/ДРР). """
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
