from typing import Union
from . import messages
from aiogram import Bot
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from sqlalchemy import select
from app.client_bot.user_interface.handlers.start import start_registration
from app.client_bot import const
from app.modules.wb_adv_updater import data_manager
from app.utils.db.session_maker import get_async_session_maker as sm
from app import ao
from app.modules.common_slaves.wildberries.models import WBCabinet, WBUserCabinet
from ..into_callback import CreateNewAdvs as CreateNewAdvsCallbackData
from .states import CreateCompamyStates as states
import logging
from ...backend.tasks import create_complex_advs_task

logger = logging.getLogger(__name__)

router = ao.Router()


def extract_nmid_list(input_text):
    """Извлекает список артикулов из текста."""
    return [int(nmid) for nmid in input_text.replace(',', ' ').split() if nmid.isdigit()]


def extract_nmid_from_file(file_content):
    """Извлекает список артикулов из содержимого текстового файла."""
    return extract_nmid_list(file_content.decode('utf-8'))


@router.callback_query(CreateNewAdvsCallbackData.filter())
async def create_new_adv(callback: ao.CallbackQuery,
                         callback_data: CreateNewAdvsCallbackData,
                         bot: ao.Bot,
                         state: ao.FSMContext):
    wb_user_cabinet_original_id = callback_data.wb_user_cabinet_original_id

    stmt = select(WBCabinet.shop_id)\
    .join(WBCabinet.wb_user_cabinets)\
    .where(WBUserCabinet.id == wb_user_cabinet_original_id)
    async with sm() as session:
        result = await session.execute(stmt)
        shop_id = result.scalar()
    sum_bot_balance: Union[int, float] \
        = await data_manager.\
        get_sum_bot_balance_from_wb_wb_user_cabinet_original_id(shop_id)
    if sum_bot_balance <= 0:
        await messages.NotEnoughMoneyMessage(bot, callback.from_user.id)(wb_user_cabinet_original_id)
        return
    await state.update_data(wb_user_cabinet_original_id=wb_user_cabinet_original_id)
    await state.set_state(states.waiting_for_get_nmid)
    await bot.send_message(callback.from_user.id, 'Отправьте артикулы WB товара через пробел, запятую, знак переноса строки или в текстовом файле:')


@router.message(StateFilter(states.waiting_for_get_nmid))
async def get_nmid(message: Message,
                   state: FSMContext,
                   bot: Bot):
    data = await state.get_data()
    wb_user_cabinet_original_id: int = data['wb_user_cabinet_original_id']

    if message.document:
        # Обработка текстового файла
        file = await bot.get_file(message.document.file_id)
        file_content = await bot.download_file(file.file_path)
        nmid_list = extract_nmid_from_file(file_content.read())
    else:
        text = message.text
        if '/start' in text:
            await start_registration(message, bot, state)
        nmid_list = extract_nmid_list(text)

    if not nmid_list:
        await bot.send_message(message.from_user.id, 'Не удалось извлечь артикулы. Проверьте формат данных и попробуйте еще раз.')
        return

    await state.clear()

    stmt = select(WBCabinet.shop_id)\
        .where(WBCabinet.wb_user_cabinets.any(WBUserCabinet.id == wb_user_cabinet_original_id))
    async with sm() as session:
        result = await session.execute(stmt)
        shop_id = result.scalar()

    for nmid in nmid_list:
        try:
            create_complex_advs_task.apply_async((nmid,
                                                  shop_id,
                                                  False,
                                                  message.from_user.id))
            logger.debug(f'Задача для артикула {nmid} успешно поставлена')
        except Exception as e:
            logger.error(f'Ошибка постановки задачи для артикула {nmid}: {e}')

    await bot.send_message(message.from_user.id, 'Задачи на создание рекламы добавлены в очередь. Ждите.')
