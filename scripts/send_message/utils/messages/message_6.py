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
            """⚠️ Обновление по работе Wildberries

Сегодня у Wildberries наблюдается задержка данных по заказам и корзинам через API. Чтобы не принимать решения на некорректных данных, автоуправление временно приостановлено.

Что это значит на практике:
• бюджеты и ставки не усиливаются
• лишние действия не выполняются
• кампании не «режутся» из-за отсутствующих данных

🔧 При необходимости вы можете внести ручные корректировки в работу кампаний: добавить или удалить ключи в Белый список, а также изменить целевую позицию.

Как только данные стабилизируются, автоуправление будет возобновлено."""
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
