import aiogram
from aiogram import F, Router, types
from aiogram.fsm.context import FSMContext
from sqlalchemy.future import select
from sqlalchemy.orm import joinedload
import logging
from app import utils
from app.client_bot import const
from app.modules.common_slaves.wildberries.models import (
    AdvSetting,
    WBCabinet,
    WBUserCabinet,
)
from app.modules.wb_adv_updater.models import AdvPayment
from app.utils.db.session_maker import get_async_session_maker
from app.client_bot.user_interface.views import messages, callbacks
import datetime


logger = logging.getLogger(__name__)

router = Router()


_sm = get_async_session_maker



@router.callback_query(callbacks.KeywordPositionHistory.filter())
async def keyword_position_history(callback: types.CallbackQuery,
                                   callback_data: callbacks.KeywordPositionHistory,
                                   bot: aiogram.Bot,
                                   state: FSMContext):
    await state.set_state(state = None)
    adv_original_id: int = callback_data.adv_original_id
    try:
          graphic, legend = (await utils.get_keyword_history_graphic(adv_original_id))
    except Exception as e:
        logger.error(e, exc_info=True)
        await messages.NotKeywordHistoryPositions(bot, callback.message.chat.id)()
        return
    if legend:
        await messages.KeywordGraphicPart_1(bot, callback.message.chat.id, graphic, adv_original_id)()
        await messages.KeywordGraphicPart_2(bot, callback.message.chat.id, legend, adv_original_id)()
    else:
        await messages.KeywordGraphicPart_2(bot, callback.message.chat.id, graphic, adv_original_id)()


@router.callback_query(callbacks.TurnParsing.filter(F.action == 'on'))
async def turn_parsing_on(callback: types.CallbackQuery,
                            callback_data: callbacks.TurnParsing,
                            bot: aiogram.Bot):

        adv_setting_original_id = callback_data.adv_original_id
        wb_user_cabinet_original_id = callback_data.wb_user_cabinet_original_id
        async with _sm(read_only=False) as session:
            stmt = select(AdvSetting)\
                .options(joinedload(AdvSetting.payments))\
                .where(AdvSetting.id == adv_setting_original_id)
            result = await session.execute(stmt)
            adv_setting = result.scalar()
            payment_dates = [payment.date for payment in adv_setting.payments if payment.type == 'parsing']
            stmt = select(WBUserCabinet) \
                .join(WBUserCabinet.wb_cabinet) \
            .options(joinedload(WBUserCabinet.wb_cabinet))\
                .where(WBUserCabinet.id == wb_user_cabinet_original_id)
            wb_user_cabinet = await session.execute(stmt)
            wb_user_cabinet = wb_user_cabinet.scalar()
            wb_cabinet: WBCabinet = wb_user_cabinet.wb_cabinet
            today = datetime.datetime.now().date()
            if today in payment_dates:
                adv_setting.parsing_active = True
                await messages.AdvSettingMenu(bot, callback.message.chat.id, wb_user_cabinet, adv_setting)()
                await session.commit()
                return
            else:
                if not (bonus := wb_cabinet.bonus):
                    bonus = 0
                if not (balance := wb_cabinet.balance):
                    balance = 0
                if bonus >= const.PARSING_PRICE:
                    bonus -= const.PARSING_PRICE
                elif balance > 0:
                    balance -= const.PARSING_PRICE
                else:
                    await messages.NotEnoughMoneyForParsing(bot, callback.message.chat.id, wb_user_cabinet.id)()
                    return
                wb_cabinet.balance = balance
                payment = AdvPayment()
                payment.type = 'parsing'
                payment.date = datetime.datetime.now().date()
                payment.adv_setting = adv_setting
                adv_setting.parsing_active = True
                session.add(payment)
                await session.commit()

        await messages.AdvSettingMenu(bot, callback.message.chat.id,wb_user_cabinet, adv_setting)()


@router.callback_query(callbacks.TurnParsing.filter(F.action == 'off'))
async def turn_parsing_off(callback: types.CallbackQuery,
                            callback_data: callbacks.TurnParsing,
                            bot: aiogram.Bot):
        adv_setting_original_id = callback_data.adv_original_id
        wb_user_cabinet_original_id = callback_data.wb_user_cabinet_original_id
        async with _sm() as session:
            stmt = select(AdvSetting).where(AdvSetting.id == adv_setting_original_id)
            result = await session.execute(stmt)
            adv_setting = result.scalar()
            stmt = select(WBUserCabinet)\
                .join(WBUserCabinet.wb_cabinet)\
                .where(WBUserCabinet.id == wb_user_cabinet_original_id)
            wb_user_cabinet = await session.execute(stmt)
            wb_user_cabinet = wb_user_cabinet.scalar()
            payment = AdvPayment()
            payment.type = 'parsing'
            payment.date = datetime.datetime.now().date()
            payment.adv_setting = adv_setting
            adv_setting.parsing_active = False
            await session.commit()

        await messages.AdvSettingMenu(bot, callback.message.chat.id, wb_user_cabinet, adv_setting)()