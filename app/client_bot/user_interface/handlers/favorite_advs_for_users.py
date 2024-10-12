import aiogram
from aiogram import F, Router, types
from aiogram.fsm.context import FSMContext
from sqlalchemy.future import select
from app.modules.common_slaves.wildberries.models import AdvSetting
from app.utils.db.models import User
from app.utils.db.session_maker import get_async_session_maker
from ..views import callbacks

sm = get_async_session_maker



router = Router()




@router.callback_query(callbacks.AddToFavorites.filter())
async def add_to_favorites(callback: types.CallbackQuery,
                            callback_data: callbacks.AddToFavorites,
                            bot: aiogram.Bot,
                            state: FSMContext):
     await callback.answer()
     adv_original_id = callback_data.adv_setting_original_id
     user_telegram_id = callback.from_user.id
     async with sm() as session:
         stmt = select(User).where(User.user_telegram_id == user_telegram_id)
         user = await session.execute(stmt)
         user = user.scalar()
         adv = await session.execute(select(AdvSetting).where(AdvSetting.id == adv_original_id))
         adv = adv.scalar()
         user.favorites_advs.append(adv)
         await session.commit()
         await bot.send_message(callback.message.chat.id, "Кампания в избранное")
     return


@router.callback_query(callbacks.RemoveFromFavorites.filter())
async def remove_from_favorites(callback: types.CallbackQuery,
                            callback_data: callbacks.RemoveFromFavorites,
                            bot: aiogram.Bot,
                            state: FSMContext):
     await callback.answer()
     adv_original_id = callback_data.adv_setting_original_id
     user_telegram_id = callback.from_user.id
     async with sm() as session:
         stmt = select(User).where(User.user_telegram_id == user_telegram_id)
         user = await session.execute(stmt)
         user = user.scalar()
         adv = await session.execute(select(AdvSetting).where(AdvSetting.id == adv_original_id))
         adv = adv.scalar()
         user.favorites_advs.remove(adv)
         await session.commit()
         await bot.send_message(callback.message.chat.id, "Кампания удалена из избранного")
     return