import aiogram
from aiogram import Router, types
from sqlalchemy import delete, select

from app.client_bot.user_interface.views import callbacks, messages
from app.modules.common_slaves.wildberries.models import WBUserCabinet
from app.utils.db.models import User
from app.utils.db.session_maker import get_async_session_maker as sm

from app.client_bot.user_interface.handlers.shop_choice_message import ShopChoice
from ..views import callbacks

router = Router()


@router.callback_query(callbacks.DeleteWbUserCabinet.filter())
async def delete_wb_user_cabinet(
    callback: types.CallbackQuery,
    callback_data: callbacks.DeleteWbUserCabinet,
    bot: aiogram.Bot,
) -> None:
    if callback.message is None: return
    wb_user_cabinet_original_id = callback_data.wb_user_cabinet_original_id
    user_telegram_id = callback.from_user.id
    async with sm(read_only=False) as session:
        stmt_delete = delete(WBUserCabinet).filter(WBUserCabinet.id == wb_user_cabinet_original_id).returning(WBUserCabinet)
        result_deleted_wb_user_cabinet = await session.execute(stmt_delete)
        deleted_wb_user_cabinet: WBUserCabinet | None = result_deleted_wb_user_cabinet.scalars().first()
        if deleted_wb_user_cabinet is None: return
        stmt_wb_user_cabinets = select(WBUserCabinet).join(WBUserCabinet.user).filter(User.user_telegram_id == user_telegram_id)
        result_wb_user_cabinets = await session.execute(stmt_wb_user_cabinets)
        wb_user_cabinets: list[WBUserCabinet] = list(result_wb_user_cabinets.scalars().all())
        await session.commit()
    assert callback.message.chat is not None
    assert deleted_wb_user_cabinet is not None
    await bot.send_message(callback.message.chat.id, f"Кабинет {deleted_wb_user_cabinet.name} удален")
    assert callback.message.chat is not None
    await ShopChoice(bot, callback.message.chat.id, wb_user_cabinets)()

    return
