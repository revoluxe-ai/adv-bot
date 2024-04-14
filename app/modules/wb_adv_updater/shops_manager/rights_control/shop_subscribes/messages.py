from sqlalchemy import select

from app.client_bot.user_interface.message_templates import templates
from app.client_bot.user_interface.views import keyboards
from app.modules.common_slaves.wildberries.models import WBUserCabinet
from app.utils.db.models import User
from app.utils.suffixes import get_day_suffix
from app.utils.db.session_maker import get_async_session_maker
from app.client_bot import const


_sm = get_async_session_maker()


class TestPeriodExpire(templates.TextWithKeyboard):

    def __init__(self, bot, chat_id, days, wb_user_cabinet):
        self._days = days
        self._wb_user_cabinet = wb_user_cabinet
        super().__init__(bot, chat_id,)


    async def __call__(self):
        async with _sm() as session:
            stmt = select(WBUserCabinet.name)\
                .filter(WBUserCabinet.id == self._wb_user_cabinet.id)
            result = await session.execute(stmt)
            self._wb_cabinet_name = result.scalar()




        await super().__call__()


    @property
    def text(self):
        return f"""
        📅 Внимание\\! Срок действия вашего тестового периода скоро закончится\\!

        🔹 Магазин: {self._wb_cabinet_name}
        🔹 До окончания тестового периода осталось: {get_day_suffix(self._days)} \\n
        Стоимость месячной подписки \\- {const.PRICE_FOR_ONE_MONTH} рублей\\. \\n

        💡 Специальное предложение: \\n
        При оплате тарифа до конца пробного периода мы компенсируем оставшийся демо\\-период в двойном размере,
        т\\.е\\. вы получите **\\+{get_day_suffix(self._days * 2 + 2)} подписки** в подарок\\!
        """



    @property
    def keyboard(self):
        keyboard =   keyboards.get_payment_keyboard(price_for_month = const.PRICE_FOR_ONE_MONTH,
                                                    period_days = 30,
                                                    bonus_days = self._days * 2 + 2)
        return keyboard