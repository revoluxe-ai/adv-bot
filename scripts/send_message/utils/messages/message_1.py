from aiogram.enums import ParseMode

from app.client_bot.user_interface.message_templates import Text




class Single_message(Text):
    def __init__(self, bot, chat_id: int):
        super().__init__(bot, chat_id)
        self.parse_mode: str = ParseMode.HTML



    text = """


    """.strip()
