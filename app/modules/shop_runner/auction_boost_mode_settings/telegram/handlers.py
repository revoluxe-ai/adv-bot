from aiogram import Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery
from sqlalchemy import update

from app.modules.common_slaves.wildberries.models import AdvSetting
from app.utils.db.session_maker import get_async_session_maker as sm

from . import callbacks

router = Router()


@router.callback_query(callbacks.SettingAuctionBoostMode.filter())
async def setting_auction_boost_mode(
    callback: CallbackQuery,
    callback_data: callbacks.SettingAuctionBoostMode,
    state: FSMContext,
):
    adv_id: int = callback_data.adv_id
    new_mode: bool = callback_data.new_mode
    await state.update_data(adv_original_id=adv_id)

    stmt = (
        update(AdvSetting)
        .filter(AdvSetting.adv_id == adv_id)
        .values({AdvSetting.auction_boost_all_phrase_mode: new_mode})
    )
    async with sm(read_only=False) as session:
        await session.execute(stmt)
        await session.commit()

    native_status = "Фикс.фразы" if not new_mode else "Все фразы"
    message = callback.message
    await message.answer(f"Новый режим Аукциона: {native_status}")
