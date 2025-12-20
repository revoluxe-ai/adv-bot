import aiogram
from aiogram import Router, types
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from sqlalchemy import delete, select, update

from app.client_bot.user_interface import states
from app.client_bot.user_interface.views import callbacks, messages
from app.modules.common_slaves.wildberries.models import WBCabinet, WBUserCabinet
from app.modules.shop_menu.message import ShopMenu
from app.utils.db.models import User
from app.utils.db.session_maker import get_async_session_maker as sm

router = Router()


@router.callback_query(callbacks.DeleteWbUserCabinet.filter())
async def delete_wb_user_cabinet(
    callback: types.CallbackQuery,
    callback_data: callbacks.DeleteWbUserCabinet,
    bot: aiogram.Bot,
):
    wb_user_cabinet_original_id = callback_data.wb_user_cabinet_original_id
    user_telegram_id = callback.from_user.id
    async with sm(read_only=False) as session:
        stmt = (
            delete(WBUserCabinet)
            .filter(WBUserCabinet.id == wb_user_cabinet_original_id)
            .returning(WBUserCabinet)
        )
        deleted_wb_user_cabinet = await session.execute(stmt)
        deleted_wb_user_cabinet = deleted_wb_user_cabinet.scalars().first()
        stmt = (
            select(WBUserCabinet)
            .join(WBUserCabinet.user)
            .filter(User.user_telegram_id == user_telegram_id)
        )
        wb_user_cabinets = await session.execute(stmt)
        wb_user_cabinets = wb_user_cabinets.scalars().all()
        await session.commit()
    await bot.send_message(
        callback.message.chat.id, f"Кабинет {deleted_wb_user_cabinet.name} удален"  # type: ignore[attr-defined]
    )

    await messages.ShopChoice(bot, callback.message.chat.id, wb_user_cabinets)()  # type: ignore[attr-defined]

    return


@router.callback_query(callbacks.ChangeShopDefaultMaxCPM.filter())
async def change_shop_default_max_cpm(
    callback: types.CallbackQuery,
    callback_data: callbacks.ChangeShopDefaultMaxCPM,
    bot: aiogram.Bot,
    state: FSMContext,
) -> None:
    if callback.message is None:
        raise ValueError("Нет сообщения")
    chat_id = callback.message.chat.id
    wb_user_cabinet_original_id = callback_data.wb_user_cabinet_original_id

    stmt = (
        select(WBCabinet)
        .where(WBCabinet.wb_user_cabinets.any(WBUserCabinet.id == wb_user_cabinet_original_id))
    )
    async with sm(read_only=True) as session:
        result = await session.execute(stmt)
        wb_cabinet = result.scalar_one()
    
    await state.update_data(last_wb_user_cabinet_original_id=wb_user_cabinet_original_id)
    await state.set_state(states.ShopDefaultMaxCPM.waiting_for_new_default_max_cpm)
    await messages.ChangeShopDefaultMaxCPMMessage(bot, chat_id, wb_cabinet.default_max_cpm)()


@router.message(StateFilter(states.ShopDefaultMaxCPM.waiting_for_new_default_max_cpm))
async def set_shop_default_max_cpm(
    message: types.Message,
    bot: aiogram.Bot,
    state: FSMContext,
) -> None:
    if message.text is None:
        await message.answer("Некорректное значение. Попробуйте еще раз.")
        return
    chat_id = message.chat.id
    data = await state.get_data()
    wb_user_cabinet_original_id = data["last_wb_user_cabinet_original_id"]

    try:
        new_cpm = int(message.text.strip())
        if new_cpm < 100:
            await bot.send_message(chat_id, "Минимальное значение CPM - 100. Попробуйте еще раз.")
            return
    except ValueError:
        await bot.send_message(chat_id, "Некорректное значение. Введите целое число.")
        return

    async with sm(read_only=False) as session:
        stmt = (
            update(WBCabinet)
            .where(WBCabinet.wb_user_cabinets.any(WBUserCabinet.id == wb_user_cabinet_original_id))
            .values(default_max_cpm=new_cpm)
        )
        await session.execute(stmt)
        await session.commit()

    await state.set_state(state=None) # Сбрасываем состояние
    await ShopMenu(bot, chat_id, state, wb_user_cabinet_original_id)()
    return
