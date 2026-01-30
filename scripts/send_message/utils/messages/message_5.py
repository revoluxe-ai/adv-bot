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
        # helpers (без изменений логики)

        def campaigns_text(count: int) -> str:
            if count == 1:
                return "1 кампания"
            if 2 <= count <= 4:
                return f"{count} кампании"
            return f"{count} кампаний"

        def money(amount: float) -> str:
            return f"{int(round(amount)):,}".replace(",", " ")

        def truncate(name: str, max_len: int = 40) -> str:
            if len(name) <= max_len:
                return name
            return name[: max_len - 1] + "…"

        cabinet_lines: list[str] = []

        for c in self._selected:
            name = truncate(c.cabinet_name.strip())
            monthly = float(c.tariff_total_per_month)
            p2_amount = round(monthly * 1.85)

            # ✅ ИЗМЕНЕНО ТОЛЬКО ЗДЕСЬ: добавили ₽/мес и “за 2 мес”
            cabinet_lines.append(
                f"{name}: {campaigns_text(c.active_campaigns)} на авто → "
                f"{money(monthly)} ₽/мес → {money(p2_amount)} ₽ за 2 мес"
            )

        cabinets_block = "\n".join(cabinet_lines)

        return (
            """📌 Пишу лично вам — у вас сейчас старый тариф WB Skyline.

⚙ На старом тарифе новые настройки и обновления не применяются:
вся работа с рекламой остаётся ручной, без автоматического контроля.

Что даёт новый авто-тариф:
— автоматическое управление лимитами и порогами;
— контроль отклонений по расходам без ручного хаоса.

👇 Если хотите перейти на авто-тариф — нажмите кнопку ниже.
Я сам переведу и напишу, что именно будет подключено."""
        )

    @property
    def keyboard(self):
        shop_ids_str = ', '.join(self._selected_shop_ids)

        # ✅ ИЗМЕНЕНО ТОЛЬКО ТЕКСТ: короткий маркер без “диалога”
        draft = f"Переход на авто-тариф: shop_id: {shop_ids_str}"

        url = f"https://t.me/{MY_USERNAME}?text={quote(draft)}"
        return InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="✅ Переход на авто-тариф", url=url)]
            ]
        )
