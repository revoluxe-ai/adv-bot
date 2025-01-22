from aiogram import Bot, Router
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy import select

from app.client_bot import const
from app.utils.db.session_maker import get_async_session_maker as sm
from app.modules.common_slaves.wildberries.models import WBCabinet, WBUserCabinet
from ..into_callback import CreateNewAdv as CreateNewAdvCallbackData
from .states import CreateCompamyStates as states
import logging
from ...backend.tasks import create_complex_advs_task

logger = logging.getLogger(__name__)


router = Router()




@router.callback_query(CreateNewAdvCallbackData.filter())
async def create_new_adv(callback: CallbackQuery,
                         callback_data: CreateNewAdvCallbackData,
                         bot: Bot,
                         state: FSMContext):
    wb_user_cabinet_original_id = callback_data.wb_user_cabinet_original_id
    await state.update_data(wb_user_cabinet_original_id=wb_user_cabinet_original_id)
    await state.set_state(states.waiting_for_get_nmid)
    await bot.send_message(callback.from_user.id, 'Отправьте артикул WB товара (1234567):')


@router.message(StateFilter(states.waiting_for_get_nmid))
async def get_nmid(message: Message,
                     state: FSMContext,
                     bot: Bot):
     data = await state.get_data()
     wb_user_cabinet_original_id: int = data['wb_user_cabinet_original_id']
     nmid = message.text
     if not nmid.isdigit():
         await bot.send_message(message.from_user.id, 'Некорректный артикул. Артикул должен быть числом. Попробуйте еще раз.')
         return
     nmid = int(nmid)
     await state.clear()

     stmt = select(WBCabinet.shop_id)\
         .where(WBCabinet.wb_user_cabinets.any(WBUserCabinet.id == wb_user_cabinet_original_id))
     async with sm() as session:
        result = await session.execute(stmt)
        shop_id = result.scalar()
     try:
         create_complex_advs_task.apply_acync((nmid, shop_id, message.from_user.id, const.ADMINS[0]))
         logger.debug('Задача успешно поставлена')
         return await bot.send_message(message.from_user.id, 'Задача создания рекламы добавлена в очередь. Ждите.')
     except:
         logger.error('Ошибка постановки задачи создания комплекса РК')
         await bot.send_message(message.from_user.id, 'Ошибка поставновки задачи на создание РК')

