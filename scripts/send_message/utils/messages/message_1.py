from aiogram.enums import ParseMode

from app.client_bot.user_interface.message_templates import Text




class Single_message(Text):
    def __init__(self, bot, chat_id: int):
        super().__init__(bot, chat_id)
        self.parse_mode: str = ParseMode.HTML



    text = """
Добрый день!

Возможно, вы добавляли магазин в боте давно, но реклама сейчас не запущена.

Если тема продвижения на Wildberries актуальна — могу предложить простой тест: я сам закину 1000 ₽ на баланс, помогу настроить рекламу и покажу, как сейчас работает автоматическое управление.

Никаких обязательств — просто тест, чтобы вы посмотрели результат и решили, нужно это вам или нет.

Если интересно — напишите мне в Telegram: @skyline360_1
    """.strip()
