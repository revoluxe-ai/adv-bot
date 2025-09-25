from app.client_bot.user_interface.message_templates import TextWithImage, TextWithKeyboardAndImage
from app.client_bot.user_interface.views import keyboards
from aiogram import Bot
from aiogram.types import InlineKeyboardMarkup


class KeywordGraphicPart_1(TextWithImage):
    def __init__(self, bot: Bot, chat_id: int, image: object, adv_original_id: int) -> None:
        self._image: object = image
        self._adv_original_id: int = adv_original_id
        super().__init__(bot, chat_id)

    text = ""

    @property
    def image(self) -> object:
        return self._image

    @image.setter
    def image(self, value: object) -> None:
        self._image = value


class KeywordGraphicPart_2(TextWithKeyboardAndImage):
    def __init__(self, bot: Bot, chat_id: int, image: object, adv_original_id: int) -> None:
        self._image: object = image
        self._adv_original_id: int = adv_original_id
        super().__init__(bot, chat_id)

    text = ""

    @property
    def image(self) -> object:
        return self._image

    @image.setter
    def image(self, value: object) -> None:
        self._image = value

    @property
    def keyboard(self) -> InlineKeyboardMarkup:
        return keyboards.get_return_to_adv_setting_keyboard(self._adv_original_id)
