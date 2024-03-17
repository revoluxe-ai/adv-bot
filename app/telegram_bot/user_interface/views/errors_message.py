import app.my_types
from app.telegram_bot.user_interface import message_templates as mt
from app.my_types import LastMessage
from ..views import keyboards



class UnknownInnerError(mt.Text):

    text = "Произошла неизвестная ошибка. Администратор уже уведомлен. Попробуйте позже."


class AddNewToken(mt.TextWithKeyboard):
    def __init__(self, bot, chat_id: int,
                 wb_user_cabinet: app.my_types.WBUserCabinet,
):
        super().__init__(bot, chat_id)
        self.wb_user_cabinet = wb_user_cabinet

    text = ("Произошла ошибка, необходимо добавить новый токен для магазина или, если хотите, "
            "вы можете удалить магазин из аккаунта.")

    @property
    def keyboard(self):
        return keyboards.add_app_token_or_delete_wb_user_cabinet(self.wb_user_cabinet)


