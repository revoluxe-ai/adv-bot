import logging

from aiogram import Bot, Router
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from arq import create_pool
from sqlalchemy import select

from app.arq_workers.arq_redis_settings import arq_redis_settings
from app.client_bot.user_interface.handlers.start import start_registration
from app.core.wb_api.exceptions import ApiForbiddenError
from app.core.wb_api.mixins.excs import CardNotFoundInWB
from app.modules.balance_manager import balance_service
from app.modules.common_slaves.wildberries.models import WBUserCabinet
from app.modules.common_slaves.wildberries.models.wb_cabinet import WBCabinet
from app.modules.wb_adv_updater import data_manager as wb_data_manager
from app.utils.db.session_maker import get_async_session_maker as sm

from ..into_callback import (
    CreateNewAdvs as CreateNewAdvsCallbackData,
    ConfirmCreateComplexAdv,
)
from . import messages
from .states import CreateCompamyStates as states

logger = logging.getLogger(__name__)

router = Router()


def extract_nmid_list(input_text):
    """Извлекает список артикулов из текста."""
    return [
        int(nmid) for nmid in input_text.replace(",", " ").split() if nmid.isdigit()
    ]


def extract_nmid_from_file(file_content):
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
            WBCabinet.wb_user_cabinets.any(
                WBUserCabinet.id == wb_user_cabinet_original_id
            )
        )
        result = await session.execute(stmt)
        wb_cabinet_id = result.scalar_one()
    balance, bonus = await balance_service.get_cabinet_balance(wb_cabinet_id)
    sum_bot_balance = balance + bonus
    if sum_bot_balance <= 0:
        await messages.NotEnoughMoneyMessage(bot, callback.from_user.id)(
            wb_user_cabinet_original_id
        )
        return
    await state.update_data(wb_user_cabinet_original_id=wb_user_cabinet_original_id)
    await state.set_state(states.waiting_for_get_nmid)
    await bot.send_message(
        callback.from_user.id,
        "Отправьте артикулы WB товара через пробел, запятую, знак переноса строки или в текстовом файле:",
    )
    return


@router.message(StateFilter(states.waiting_for_get_nmid))
async def get_nmid(message: Message, state: FSMContext, bot: Bot):
    data = await state.get_data()
    wb_user_cabinet_original_id: int = data["wb_user_cabinet_original_id"]

    if message.document:
        # Обработка текстового файла
        file = await bot.get_file(message.document.file_id)
        file_content = await bot.download_file(file.file_path)
        nmid_list = extract_nmid_from_file(file_content.read())
    else:
        text = message.text
        if "/start" in text:
            await start_registration(message, bot, state)
        nmid_list = extract_nmid_list(text)

    if not nmid_list:
        await state.clear()
        await bot.send_message(
            message.from_user.id,
            "Не удалось извлечь артикулы. Проверьте формат (только числа через пробел или запятую, без лишних символов). "
            "Чтобы снова создать рекламу по артикулам, нажмите «Создать рекламу» в меню магазина.",
        )
        return

    await state.clear()

    stmt = select(WBCabinet.shop_id).where(
        WBCabinet.wb_user_cabinets.any(WBUserCabinet.id == wb_user_cabinet_original_id)
    )
    async with sm() as session:
        result = await session.execute(stmt)
        shop_id = result.scalar()
    shop_id_str = str(shop_id)

    await bot.send_message(
        message.from_user.id,
        "Проверяю наличие карточек в базе и догружаю отсутствующие...",
    )

    ready_nmids: list[int] = []
    failed_nmids: list[str] = []
    for nmid in nmid_list:
        try:
            is_ready = await wb_data_manager.ensure_card_in_db(shop_id_str, nmid)
        except CardNotFoundInWB:
            failed_nmids.append(f"{nmid}: карточка не найдена на WB")
            continue
        except ApiForbiddenError:
            failed_nmids.append(f"{nmid}: нет доступа к API WB")
            continue
        except Exception:
            logger.exception("create_new_adv: ensure_card_in_db failed for nmid=%s", nmid)
            failed_nmids.append(f"{nmid}: ошибка проверки/загрузки карточки")
            continue

        if is_ready:
            ready_nmids.append(nmid)
        else:
            failed_nmids.append(f"{nmid}: таймаут ожидания загрузки в БД")

    if not ready_nmids:
        lines = "\n".join(f"- {item}" for item in failed_nmids[:30])
        await bot.send_message(
            message.from_user.id,
            "Не удалось подготовить карточки для создания рекламы.\n" + lines,
        )
        return

    redis_task_pool = await create_pool(arq_redis_settings)
    for nmid in ready_nmids:
        try:
            await redis_task_pool.enqueue_job(
                "create_complex_advs", nmid, shop_id_str, False, message.from_user.id
            )
            logger.debug(f"Задача для артикула {nmid} успешно поставлена")
        except Exception as e:
            logger.error(f"Ошибка постановки задачи для артикула {nmid}: {e}")
            raise e
    summary_text = (
        f"Задачи на создание рекламы добавлены в очередь: {len(ready_nmids)} шт."
    )
    if failed_nmids:
        failed_lines = "\n".join(f"- {item}" for item in failed_nmids[:30])
        summary_text += "\nНе поставлены в очередь:\n" + failed_lines
    await bot.send_message(message.from_user.id, summary_text)


@router.callback_query(ConfirmCreateComplexAdv.filter())
async def confirm_create_complex_adv(
    callback: CallbackQuery,
    callback_data: ConfirmCreateComplexAdv,
    bot: Bot,
) -> None:
    await callback.answer()
    await callback.message.edit_reply_markup(reply_markup=None)  # убрать клавиатуру

    wb_cabinet_original_id = callback_data.wb_cabinet_original_id

    stmt = select(WBCabinet.shop_id).where(WBCabinet.id == wb_cabinet_original_id)
    async with sm(read_only=True) as session:
        result: str | None = await session.scalar(stmt)
    shop_id = result
    assert shop_id is not None, "shop_id не найден в базе"
    if callback_data.action == "continue":
        # Повторная постановка задачи с hard_mode=True
        redis_task_pool = await create_pool(arq_redis_settings)
        await redis_task_pool.enqueue_job(
            "create_complex_advs",
            callback_data.nmid,
            shop_id,
            True,  # hard_mode=True
            callback.from_user.id,
        )
        await bot.send_message(
            callback.from_user.id,
            f"Создание новой комплексной кампании для артикула {callback_data.nmid} начато...",
        )
    else:  # "cancel"
        await bot.send_message(
            callback.from_user.id,
            f"Создание комплексной кампании для артикула {callback_data.nmid} отменено.",
        )
