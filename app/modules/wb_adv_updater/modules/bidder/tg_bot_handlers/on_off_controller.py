"""Telegram handlers for enabling and disabling CPM bidder mode."""

import aiogram
from aiogram import F, Router, types
from aiogram.fsm.context import FSMContext
from sqlalchemy.future import select

from app.client_bot.user_interface import states
from app.client_bot.user_interface.views import callbacks
from app.modules.common_slaves.wildberries.models import AdvSetting
from app.utils.db.session_maker import get_async_session_maker

sm = get_async_session_maker

router = Router()


@router.callback_query(callbacks.CPMSettingMenu.filter(F.action == "set_auto_cpm"))
async def get_min_position(
    callback: types.CallbackQuery,
    callback_data: callbacks.ChoiceAdvPaginator,
    bot: aiogram.Bot,
    state: FSMContext,
) -> None:
    """Enable bidder immediately or request only the missing CPM settings."""
    adv_original_id = callback_data.adv_original_id  # type: ignore[attr-defined]
    await state.update_data(last_adv_original_id=adv_original_id)
    async with sm(read_only=False) as session:
        result = await session.execute(
            select(AdvSetting).where(AdvSetting.id == adv_original_id)
        )
        adv = result.scalar_one()
        has_max_place = adv.max_place is not None and adv.max_place > 0
        has_max_cpm = adv.max_cpm is not None and adv.max_cpm > 0

        import app.client_bot.user_interface.views.messages as ui_messages

        if has_max_place and has_max_cpm:
            adv.bidder_active = True
            await session.commit()
            await ui_messages.CPMSetting(bot, callback.message.chat.id)(adv_original_id)  # pyright: ignore[arg-type]
            return

        if not has_max_place:
            await state.set_state(states.CPMSetting.waiting_for_min_position)
            await ui_messages.AutoCPMSettingGetMinPosition(bot, callback.message.chat.id)(  # pyright: ignore[arg-type]
                adv_original_id
            )
            return

        await state.set_state(states.CPMSetting.waiting_for_max_cpm)
        await ui_messages.AutoCPMSettingGetMaxCPM(bot, callback.message.chat.id)()


@router.callback_query(callbacks.CPMSettingMenu.filter(F.action == "off_auto_cpm"))
async def off_auto_cpm(
    callback: types.CallbackQuery,
    callback_data: callbacks.ChoiceAdvPaginator,
    bot: aiogram.Bot,
    state: FSMContext,
) -> None:
    """Disable bidder automation for the selected campaign."""
    adv_original_id: int = callback_data.adv_original_id  # type: ignore
    async with sm(read_only=False) as session:
        adv = await session.execute(
            select(AdvSetting).where(AdvSetting.id == adv_original_id)  # pyright: ignore
        )
        adv = adv.scalar()
        adv.bidder_active = False  # type: ignore[attr-defined]
        await session.commit()
        import app.client_bot.user_interface.views.messages as ui_messages

        await ui_messages.CPMSetting(bot, callback.message.chat.id)(adv_original_id)  # pyright: ignore
