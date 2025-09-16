from aiogram.enums import ParseMode

from app.client_bot.user_interface.message_templates import Text


class Single_message(Text):

    def __init__(self, bot, chat_id: int):
        super().__init__(bot, chat_id)
        self.parse_mode: str = ParseMode.MARKDOWN_V2

    r"""
    Нужно экранировать:
    \ — обратный слэш

_ — подчёркивание

* — звёздочка

[ — левая квадратная скобка

] — правая квадратная скобка

( — левая круглая скобка

) — правая круглая скобка

~ — тильда

> — знак больше

# — решётка

+ — плюс

- — минус

= — знак равенства

| — вертикальная черта

{ — левая фигурная скобка

} — правая фигурная скобка

. — точка

! — восклицательный знак
    
    
    """

    text = """""".strip()
