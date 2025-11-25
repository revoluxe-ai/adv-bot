import app.my_types
from app.client_bot.user_interface import message_templates as mt

from ..views import keyboards


class UnknownInnerError(mt.Text):
    text = (
        "Произошла неизвестная ошибка. Администратор уже уведомлен. Попробуйте позже."
    )
