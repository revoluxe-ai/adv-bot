import aiogram
from aiogram import Router, types
from sqlalchemy import delete, select

from app.client_bot.user_interface.views import callbacks, messages
from app.modules.common_slaves.wildberries.models import (
    WBUserCabinet,
)
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
