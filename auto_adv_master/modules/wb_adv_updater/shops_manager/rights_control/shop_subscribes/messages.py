from sqlalchemy import select
from sqlalchemy.orm import joinedload

from auto_adv_master.client_bot import const
from auto_adv_master.client_bot.user_interface.message_templates import templates
from auto_adv_master.client_bot.user_interface.views import keyboards
from auto_adv_master.modules.common_slaves.wildberries.models import WBUserCabinet
from auto_adv_master.utils.db.models import User
from auto_adv_master.utils.db.session_maker import get_async_session_maker
from auto_adv_master.utils.suffixes import get_day_suffix

_sm = get_async_session_maker()


class TestPeriodExpire(templates.TextWithKeyboard):

    def __init__(self, bot, chat_id, days, wb_user_cabinet):
        self._days = days
        self._wb_user_cabinet = wb_user_cabinet
        super().__init__(bot, chat_id,)


    async def __call__(self):
        async with _sm() as session:
            stmt = select(WBUserCabinet)\
                .options(joinedload (WBUserCabinet.wb_cabinet))\
                .filter(WBUserCabinet.id == self._wb_user_cabinet.id)
            result = await session.execute(stmt)
            self._wb_user_cabinet = result.scalar()
            self._wb_user_cabinet_name = self._wb_user_cabinet.name
            self._wb_cabinet = self._wb_user_cabinet.wb_cabinet
        await super().__call__()


    @property
    def text(self):
        return f"""
        📅 Внимание! Срок действия вашего тестового периода скоро закончится!

        🔹 Магазин: {self._wb_user_cabinet_name}
        🔹 До окончания тестового периода осталось: {get_day_suffix(self._days)} \n
        Стоимость месячной подписки - {const.PRICE_PER_MONTH} рублей. \n

        💡 Специальное предложение: \n
        При оплате тарифа до конца пробного периода мы компенсируем оставшийся демо-период в двойном размере,
        т.е. вы получите +{get_day_suffix(self._days * 2 + 2)} подписки в подарок!
        """

    @property
    def keyboard(self):
        return keyboards.get_payment_keyboard(
            price_for_month=const.PRICE_PER_MONTH,
            period_days=30,
            bonus_days=self._days * 2 + 2,
            wb_cabinet_original_id=self._wb_cabinet.id,
        )
