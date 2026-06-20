"""Тумблер V3 Raise MAX в экране «План продаж»."""

from __future__ import annotations

from aiogram import Bot, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery
from sqlalchemy import update

from app.modules.common_slaves.wildberries.models import AdvSetting
from app.modules.sales_plan_settings.v3_raise_max_cpo import (
    format_v3_raise_max_toggle_message,
)
from app.utils.db.session_maker import get_async_session_maker as sm

from .. import callbacks, main_message

router = Router()


@router.callback_query(callbacks.V3RaiseMaxCpoToggle.filter())
async def toggle_v3_raise_max_cpo_handler(
    callback: CallbackQuery,
    callback_data: callbacks.V3RaiseMaxCpoToggle,
    bot: Bot,
    state: FSMContext,
) -> None:
    """Включить/выключить V3 Raise MAX для кампании."""
    adv_id = callback_data.adv_id
    new_status = bool(callback_data.new_status)

    stmt = (
        update(AdvSetting)
        .where(AdvSetting.adv_id == adv_id)
        .values({AdvSetting.substitute_fact_cpo_for_max: new_status})
    )
    async with sm() as session:
        await session.execute(stmt)
        await session.commit()

    assert callback.from_user is not None
    chat_id = callback.from_user.id
    await bot.send_message(
        chat_id,
        format_v3_raise_max_toggle_message(enabled=new_status),
    )
    await main_message.SalesPlanSettingsMenuMessage(bot, chat_id, adv_id, state)()
