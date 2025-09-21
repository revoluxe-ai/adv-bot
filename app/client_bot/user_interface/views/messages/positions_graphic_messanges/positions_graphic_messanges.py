from app.client_bot.user_interface.message_templates import TextWithImage, TextWithKeyboardAndImage
from app.client_bot.user_interface.views import keyboards


class KeywordGraphicPart_1(TextWithImage):
    def __init__(self, bot, chat_id, image, adv_original_id):
        self._image = image
        self._adv_original_id = adv_original_id
        super().__init__(bot, chat_id)

    text = ""

    @property
    def image(self):
        return self._image

    @image.setter
    def image(self, value):
        self._image = value


class KeywordGraphicPart_2(TextWithKeyboardAndImage):
    def __init__(self, bot, chat_id, image, adv_original_id):
        self._image = image
        self._adv_original_id = adv_original_id
        super().__init__(bot, chat_id)

    text = ""

    @property
    def image(self):
        return self._image

    @image.setter
    def image(self, value):
        self._image = value

    @property
    def keyboard(self):
        return keyboards.get_return_to_adv_setting_keyboard(self._adv_original_id)
