from aiogram import Bot
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup
from sqlalchemy import select

from app.modules.common_slaves.wildberries.models import AdvSetting
from app.utils.db.session_maker import get_async_session_maker as sm
from app.client_bot.user_interface.message_templates import TextWithKeyboard
from app.modules.predict_ctr_exponent_settings.telegram.callbacks import SalesPlanSettingsMenu


class SalesPlanSettingsMenuMessage:

    def init(self,
             bot: Bot,
             callback: CallbackQuery,
             callback_data: SalesPlanSettingsMenu,
             state: FSMContext):
        self._adv_id = callback_data.adv_id


    async def __call_(self):
        adv: AdvSetting = await self._get_adv(self._adv_id)
        plan_for_sales_for_day = adv.









    @property
    def keyboard(self) ->  InlineKeyboardMarkup:
        if self.



        button = InlineKeyboardButton(text     ,
                                  callback_data=callbacks.BudgetForCreatingAdv(type='balance').pack())







        buttons = [
            [],
            [InlineKeyboardButton(text=f'Баланс: {balances.net} руб.',
                                  callback_data=BudgetForCreatingAdv(type='net').pack())],
            [InlineKeyboardButton(text=f'Бонусы: {balances.bonus} руб.',
                                  callback_data=BudgetForCreatingAdv(type='bonus').pack())]
        ]

        keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)

        return keyboard







        return

    @staticmethod
    async def _get_adv(adv_id: int):
        stmt = select(AdvSetting)\
        .filter(AdvSetting.adv_id == adv_id)
        async with sm() as session:
            result = await session.execute(stmt)
            adv: AdvSetting = result.scalar_one()
        return adv