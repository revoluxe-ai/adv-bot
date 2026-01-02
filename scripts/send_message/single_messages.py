from aiogram.enums import ParseMode

from app.client_bot.user_interface.message_templates import Text


class Single_message(Text):
    def __init__(self, bot, chat_id: int):
        super().__init__(bot, chat_id)
        self.parse_mode: str = ParseMode.HTML



    text = """
<b>Андрей на связи.</b>

Вижу, что реклама у вас сейчас работает,
но баланс подходит к концу.

В текущей логике Wildberries остановка рекламы —
это откат по позициям и накопленным метрикам.

Я сейчас перевожу <b>активные кабинеты</b>
в формат полной автоматизации с сопровождением,
где я сам слежу за отклонением от плана продаж
и вмешиваюсь, если что-то идёт не так.

Если хотите продолжать работу в таком формате —
<b>напишите мне 👉 @skyline360_1</b>
посмотрим ваш кабинет и решим, как лучше действовать дальше.
    """.strip()
