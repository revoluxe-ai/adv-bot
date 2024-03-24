from app import message_templates
from app import keyboards




class AddImageOnApi(message_templates.TextWithKeyboarAndImage):
    def __init__(self, bot, chat_id, all_shops):
        super().__init__(bot, chat_id)
        self.__all_shops = all_shops



    @property
    def text(self):
        return ('Привет 👋\n Установили подсказку с указанием какие права нужно выставить'
                'в API для корректной работы бота. Теперь добавить новый магазин стало проще! \n'
                'Также начинаем работу канала, на котором в ближайшее время выложим больше информации '
                'по работе с ботом и его функционалу - @auto_wb_master'
            )

    @property
    def keyboard(self):
        return keyboards.get_shop_keyboard(self.__all_shops)