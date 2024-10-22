from aiogram import Router, types
import aiogram
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from app.modules.common_slaves.wildberries.models import WBUserCabinet, WBToken, WBCabinet
from app.utils.db.models import User
from app.utils.db.session_maker import get_async_session_maker as sm
from app.client_bot.user_interface.views import callbacks, messages

router = Router()

@router.callback_query(callbacks.DeleteWbUserCabinet.filter())
async def delete_wb_user_cabinet(callback: types.CallbackQuery,
                                 callback_data: callbacks.DeleteWbUserCabinet,
                                 bot: aiogram.Bot,):
    wb_user_cabinet_original_id = callback_data.wb_user_cabinet_original_id
    chat_id = callback.message.chat.id
    async with sm() as session:
        wb_user_cabinet = await session.execute(select(WBUserCabinet)\
            .options(selectinload(WBUserCabinet.wb_cabinet))\
                                                .where(WBUserCabinet.id == wb_user_cabinet_original_id))
        wb_user_cabinet: WBUserCabinet = wb_user_cabinet.scalar()
        if wb_user_cabinet:
            await bot.send_message(chat_id, "Удаляю кабинет...")
            await session.delete(wb_user_cabinet)
            await bot.send_message(chat_id,'Кабинет удален, удаляю связанные токены')
            wb_cabinet: WBCabinet = wb_user_cabinet.wb_cabinet
            shop_id = wb_cabinet.shop_id
            stmt = select(WBToken).where(WBToken.user_id == wb_user_cabinet.user_id)
            tokens = await session.execute(stmt)
            tokens = tokens.scalars().all()
            for token in tokens:
                try:
                    shop_id = token.shop_id
                except AttributeError:
                    continue
                if shop_id == wb_user_cabinet.wb_cabinet.shop_id:
                    await session.delete(token)
            await bot.send_message(chat_id, 'Связанные токены удалены')
            await session.commit()
        else:
            await bot.send_message(chat_id, 'Кабинет не найден')

    await bot.send_message(chat_id, 'Отправляю список магазинов...')

    async with sm() as session:
        stmt = select(User.id)\
        .filter(User.user_telegram_id == chat_id)
        user_original_id = await session.execute(stmt)
        user_original_id = user_original_id.scalar_one()
        stmt = select(WBUserCabinet)\
        .filter(WBUserCabinet.user_id == user_original_id)
        all_shops = await session.execute(stmt)
        all_shops = all_shops.scalars().all()

    await messages.ShopChoice(bot, chat_id, all_shops)()
    return