"""Telegram handlers for enabling and disabling CPM bidder mode."""

import aiogram
from aiogram import F, Router, types
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.client_bot.user_interface import states
from app.client_bot.user_interface.utils import (
    get_auto_target_place_manual_change_locked_text,
)
from app.client_bot.user_interface.views import callbacks
from app.modules.common_slaves.wildberries.models import AdvSetting
from app.utils.db.session_maker import get_async_session_maker

sm = get_async_session_maker

router = Router()


async def _load_adv_setting(session: AsyncSession, adv_original_id: int) -> AdvSetting | None:
    """Load CPM campaign settings for bidder toggle flow."""
    return await session.get(AdvSetting, adv_original_id)


async def off_auto_cpm_in_session(
    session: AsyncSession,
    adv_original_id: int,
) -> AdvSetting:
    """Выключить ``bidder_active`` через переданную WRITE-session.

    Parent ``off_auto_cpm`` открывает ``sm(read_only=False)`` и передаёт session
    сюда. После commit UI-меню перезагружается снаружи.

    Args:
        session: SQLAlchemy AsyncSession (WRITE).
        adv_original_id: PK ``AdvSetting.id``.

    Returns:
        Обновлённый ``AdvSetting``.

    Raises:
        RuntimeError: если кампания не найдена.
    """
    result = await session.execute(
        select(AdvSetting).where(AdvSetting.id == adv_original_id)
    )
    adv = result.scalar_one_or_none()
    if adv is None:
        raise RuntimeError("Не удалось найти кампанию для отключения авто-CPM.")
    adv.bidder_active = False
    await session.commit()
    return adv


@router.callback_query(callbacks.CPMSettingMenu.filter(F.action == "set_auto_cpm"))
async def get_min_position(
    callback: types.CallbackQuery,
    callback_data: callbacks.CPMSettingMenu,
    bot: aiogram.Bot,
    state: FSMContext,
) -> None:
    """Enable bidder immediately or request only the missing CPM settings."""
    if callback.message is None:
        raise RuntimeError("callback.message is None")
    adv_original_id = callback_data.adv_original_id
    _ = await state.update_data(last_adv_original_id=adv_original_id)
    async with sm(read_only=False) as session:
        adv = await _load_adv_setting(session, adv_original_id)
        if adv is None:
            await state.set_state(state=None)
            raise RuntimeError("Не удалось найти кампанию для настройки.")

        has_max_place = adv.max_place is not None and adv.max_place > 0
        has_max_cpm = adv.max_cpm is not None and adv.max_cpm > 0

        import app.client_bot.user_interface.views.messages as ui_messages

        chat_id = callback.message.chat.id
        if has_max_place and has_max_cpm:
            adv.bidder_active = True
            await session.commit()
            await ui_messages.CPMSetting(bot, chat_id)(adv_original_id)
            return

        if adv.auto_update_target_place and not has_max_place:
            await state.set_state(state=None)
            await bot.send_message(
                chat_id,
                get_auto_target_place_manual_change_locked_text(),
            )
            return

        if not has_max_place:
            await state.set_state(states.CPMSetting.waiting_for_min_position)
            await ui_messages.AutoCPMSettingGetMinPosition(bot, chat_id)(
                adv_original_id
            )
            return
        await state.set_state(states.CPMSetting.waiting_for_max_cpm)
        await ui_messages.AutoCPMSettingGetMaxCPM(bot, chat_id)()


@router.callback_query(callbacks.CPMSettingMenu.filter(F.action == "off_auto_cpm"))
async def off_auto_cpm(
    callback: types.CallbackQuery,
    callback_data: callbacks.CPMSettingMenu,
    bot: aiogram.Bot,
    state: FSMContext,
) -> None:
    """Disable bidder automation for the selected campaign."""
    if callback.message is None:
        raise RuntimeError("callback.message is None")
    adv_original_id = callback_data.adv_original_id
    async with sm(read_only=False) as session:
        await off_auto_cpm_in_session(session, adv_original_id)
        import app.client_bot.user_interface.views.messages as ui_messages

        await ui_messages.CPMSetting(bot, callback.message.chat.id)(adv_original_id)
