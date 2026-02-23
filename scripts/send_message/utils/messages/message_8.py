
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
            """📌 Завтра, 24.02 в 12:00 МСК — вебинар
Как управлять рекламой в “полках” Wildberries без слива бюджета

В рекомендательных местах часто одно и то же:
бюджет есть, ставка стоит — а показов мало / трафик “не тот”.

Разберу по шагам:
— как устроены “полки” и рекомендации на Wildberries
— почему показы могут проседать даже при нормальном бюджете
— как ставка реально распределяет трафик
— какие правила помогают держать экономику и не сливать

✅ Регистрация: https://clck.ru/3RtwNV

Запись получат только зарегистрированные.

Если рекламу ведёте, но ощущение «контроль утекает» — приходите."""
        )

    @property
    def keyboard(self):
        shop_ids_str = ', '.join(self._selected_shop_ids)

        # ✅ ИЗМЕНЕНО ТОЛЬКО ТЕКСТ: короткий маркер без “диалога”
        draft = f"У меня вопрос...: {shop_ids_str}"

        url = f"https://clck.ru/3RtwNV"
        return InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="Регистрация", url=url)]
            ]
        )
