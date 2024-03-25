from app.client_bot.user_interface import message_templates
from app.client_bot.user_interface.views import keyboards




class AddImageOnApi(message_templates.TextWithKeyboard):
    def __init__(self, bot, chat_id, all_shops):
        super().__init__(bot, chat_id)
        self.__all_shops = all_shops



    @property
    def text(self):
        return ('Привет 👋\n Установили подсказку с указанием какие права нужно выставить'
                ' в API для корректной работы бота. Теперь добавить новый магазин стало проще! \n'
                'Также создали канал и выложили на нем инструкцию по автоматизации рекламы на WB с помощью'
                ' нашего бота - @auto_wb_master')

    @property
    def keyboard(self):
        return keyboards.get_shop_keyboard(self.__all_shops)