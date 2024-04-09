from sqlalchemy import select

from app.client_bot.user_interface.message_templates import templates
from app.modules.common_slaves.wildberries.models import WBUserCabinet
from app.utils.db.models import User
from app.utils.suffixes import get_day_suffix
from app.utils.db.session_maker import get_async_session_maker

_sm = get_async_session_maker()


class TestPeriodExpire(templates.Text):

    def __init__(self, bot, chat_id, days, wb_user_cabinet):
        self._days = days
        self._wb_user_cabinet = wb_user_cabinet
        super().__init__(bot, chat_id,)


    async def __call__(self):
        async with _sm() as session:
            stmt = select(WBUserCabinet)\




        super().__call__()


    @property
    def text(self):
        return (f'Срок действия вашего тестового периода закончится через {get_day_suffix(self._days)}.'
                f' Если вы оплачиваете тариф до конца тестового периода, то дополнительный месяц подписки мы вам подарим!')

