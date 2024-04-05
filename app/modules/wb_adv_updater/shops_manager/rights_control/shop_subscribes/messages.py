from app.client_bot.user_interface.message_templates import templates
from app.utils.suffixes import get_day_suffix



class TestPeriodExpire(templates.Text):

    def __init__(self, bot, chat_id, days):
        self._days = days
        super().__init__(bot, chat_id)


    @property
    def text(self):
        return (f'Срок действия вашего тестового периода закончится через {get_day_suffix(self._days)}.'
                f' Если вы оплачиваете тариф до конца тестового периода, то дополнительный месяц подписки мы вам подарим!')

