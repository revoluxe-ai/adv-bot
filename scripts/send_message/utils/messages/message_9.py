
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
            """📌 Сегодня в 12:00 МСК — вебинар
Как управлять рекламой в “полках” Wildberries без слива бюджета

Если в рекомендательных местах:

— бюджет есть, а показов мало
— трафик идёт, но ощущение, что он распределяется странно
— ставка меняется, а поведение почти не меняется

Сегодня разберём, почему так происходит и как этим управлять.

Покажу:

— как реально работают “полки” и рекомендации на Wildberries
— как ставка влияет на распределение трафика
— какие правила помогают раскручивать рекомендательные места и при этом держать экономику

Без “волшебных кнопок”. Только логика и практика.

✅ Регистрация: https://clck.ru/3RtwNV

📌 Запись гарантированно получат только зарегистрированные.
Если планируете подключиться — лучше зарегистрироваться заранее."""
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
