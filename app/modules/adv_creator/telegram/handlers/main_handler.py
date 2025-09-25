import logging

from aiogram import Bot, Router
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from arq import create_pool
from sqlalchemy import select

from app.arq_workers.arq_redis_settings import arq_redis_settings
from app.client_bot.user_interface.handlers.start_registration_func import start_registration
from app.modules.balance_manager import balance_service
from app.modules.common_slaves.wildberries.models import WBCabinet, WBUserCabinet
from app.utils.db.session_maker import get_async_session_maker as sm

from ..into_callback import CreateNewAdvs as CreateNewAdvsCallbackData
from . import messages
from .states import CreateCompamyStates as states

logger = logging.getLogger(__name__)

router = Router()


def extract_nmid_list(input_text: str) -> list[int]:
    """Извлекает список артикулов из текста."""
    return [int(nmid) for nmid in input_text.replace(",", " ").split() if nmid.isdigit()]


def extract_nmid_from_file(file_content: bytes) -> list[int]:
    """Извлекает список артикулов из содержимого текстового файла."""
    return extract_nmid_list(file_content.decode("utf-8"))


@router.callback_query(CreateNewAdvsCallbackData.filter())
async def create_new_adv(
    callback: CallbackQuery,
    callback_data: CreateNewAdvsCallbackData,
    bot: Bot,
    state: FSMContext,
) -> None:
    wb_user_cabinet_original_id = callback_data.wb_user_cabinet_original_id
    async with sm() as session:
        stmt = select(WBCabinet.id).where(
            WBCabinet.wb_user_cabinets.any(WBUserCabinet.id == wb_user_cabinet_original_id)
        )
        result = await session.execute(stmt)
        wb_cabinet_id = result.scalar_one()
    balance, bonus = await balance_service.get_cabinet_balance(wb_cabinet_id)
    sum_bot_balance = balance + bonus
    if sum_bot_balance <= 0:
        await messages.NotEnoughMoneyMessage(bot, callback.from_user.id)(wb_user_cabinet_original_id)
        return
    await state.update_data(wb_user_cabinet_original_id=wb_user_cabinet_original_id)
    await state.set_state(states.waiting_for_get_nmid)
    await bot.send_message(
        callback.from_user.id,
        "Отправьте артикулы WB товара через пробел, запятую, знак переноса строки или в текстовом файле:",
    )
    return


@router.message(StateFilter(states.waiting_for_get_nmid))
async def get_nmid(message: Message, state: FSMContext, bot: Bot) -> None:
    data = await state.get_data()
    wb_user_cabinet_original_id: int = data["wb_user_cabinet_original_id"]

    if message.document:
        # Обработка текстового файла
        file = await bot.get_file(message.document.file_id)
        file_content = await bot.download_file(file.file_path)
        if file_content is None:
            await bot.send_message(message.from_user.id, "Не удалось скачать файл. Попробуйте снова.")
            return
        nmid_list = extract_nmid_from_file(file_content.read())
    else:
        text = message.text
        if text is not None and "/start" in text:
            await start_registration(message, bot, state)
        nmid_list = extract_nmid_list(text or "")

    if not nmid_list:
        await bot.send_message(
            message.from_user.id,
            "Не удалось извлечь артикулы. Проверьте формат данных и попробуйте еще раз.",
        )
        return

    await state.clear()

    stmt = select(WBCabinet.shop_id).where(
        WBCabinet.wb_user_cabinets.any(WBUserCabinet.id == wb_user_cabinet_original_id)
    )
    async with sm() as session:
        result = await session.execute(stmt)
        shop_id = result.scalar()
    redis_task_pool = await create_pool(arq_redis_settings)
    for nmid in nmid_list:
        try:
            await redis_task_pool.enqueue_job("create_complex_advs", nmid, shop_id, False, message.from_user.id)
            logger.debug(f"Задача для артикула {nmid} успешно поставлена")
        except Exception as e:
            logger.error(f"Ошибка постановки задачи для артикула {nmid}: {e}")
            raise e
    await bot.send_message(message.from_user.id, "Задачи на создание рекламы добавлены в очередь. Ждите.")
