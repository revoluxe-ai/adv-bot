from aiogram import Bot, Router
from aiogram.types import CallbackQuery
from sqlalchemy import update

from app.modules.billing.paid_option_check import (
    format_insufficient_funds_message,
    get_adv_setting_and_check_funds_for_enabling,
)
from app.modules.billing.pricer import Pricer
from app.modules.common_slaves.wildberries.models import AdvSetting
from app.utils.db.session_maker import get_async_session_maker as sm

from .callbacks import AutoUpdateTargetPlaceSetting

router = Router()


@router.callback_query(AutoUpdateTargetPlaceSetting.filter())
async def set_new_status_for_auto_update_target_place_setting(
    callback_query: CallbackQuery,
    callback_data: AutoUpdateTargetPlaceSetting,
    bot: Bot,
) -> None:
    new_status = callback_data.new_status
    adv_setting_original_id: int = callback_data.adv_setting_original_id

    assert callback_query.message
    chat_id = callback_query.message.chat.id
    pricer = Pricer()

    async with sm() as session:
        if new_status:
            _ = await get_adv_setting_and_check_funds_for_enabling(
                session,
                adv_setting_id=adv_setting_original_id,
                send_adv_not_found=lambda: bot.send_message(
                    chat_id, "РК не найдена"
                ),
                send_no_cabinet=lambda: bot.send_message(
                    chat_id, "Не удалось найти кабинет для кампании"
                ),
                get_required_price=lambda s, sid, aid: pricer.get_price_for_day_if_enabling_auto_option(
                    s, sid, aid, override_target_place=True
                ),
                send_insufficient_funds=lambda req, av: bot.send_message(
                    chat_id,
                    format_insufficient_funds_message(req, av),
                ),
            )
            if _ is None:
                return

        stmt = (
            update(AdvSetting)
            .where(AdvSetting.id == adv_setting_original_id)
            .values({"auto_update_target_place": new_status})
        )
        await session.execute(stmt)
        await session.commit()

    new_status_str: str = "Включено" if new_status else "Выключено"
    await bot.send_message(
        chat_id, f"Автообновление целевой позиции в кампании {new_status_str}"
    )
