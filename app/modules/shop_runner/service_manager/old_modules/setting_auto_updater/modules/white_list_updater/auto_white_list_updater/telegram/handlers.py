from aiogram import Bot, Router
from aiogram.types import CallbackQuery
from sqlalchemy import select, update
from sqlalchemy.orm import selectinload

from app.modules import balance_manager
from app.modules.billing.pricer import Pricer
from app.modules.common_slaves.wildberries.models import AdvSetting
from app.utils.db.session_maker import get_async_session_maker as sm

from .callbacks import AutoUpdateWhiteListSetting

router = Router()


@router.callback_query(AutoUpdateWhiteListSetting.filter())
async def set_new_status_for_auto_update_list_setting(
    callback_query: CallbackQuery,
    callback_data: AutoUpdateWhiteListSetting,
    bot: Bot,
) -> None:
    new_status = callback_data.new_status
    adv_setting_original_id: int = callback_data.adv_setting_original_id

    assert callback_query.message
    chat_id = callback_query.message.chat.id

    async with sm() as session:
        if new_status:
            stmt = (
                select(AdvSetting)
                .options(selectinload(AdvSetting.wb_cabinet))
                .where(AdvSetting.id == adv_setting_original_id)
            )
            adv_setting = await session.scalar(stmt)
            if adv_setting is None:
                await bot.send_message(chat_id, "РК не найдена")
                return
            if adv_setting.wb_cabinet is None:
                await bot.send_message(
                    chat_id, "Не удалось найти кабинет для кампании"
                )
                return
            balance, bonus = await balance_manager.get_cabinet_balance_and_bonuses(
                adv_setting.wb_cabinet.id
            )
            available = balance + bonus
            pricer = Pricer()
            required_price = await pricer.get_price_for_day_if_enabling_auto_option(
                session,
                adv_setting.wb_cabinet.shop_id or "",
                adv_setting.id,
                override_white_list=True,
            )
            if available < required_price:
                await bot.send_message(
                    chat_id,
                    (
                        f"Недостаточно средств для включения настройки: "
                        f"нужно {required_price:.2f} ₽, доступно {available:.2f} ₽.\n"
                        "Пополните баланс и попробуйте снова."
                    ),
                )
                return

        stmt = (
            update(AdvSetting)
            .where(AdvSetting.id == adv_setting_original_id)
            .values({"auto_update_white_list": new_status})
        )
        await session.execute(stmt)
        await session.commit()

    new_status_str: str = "Включено" if new_status else "Выключено"
    await bot.send_message(
        chat_id, f"Автообновление белого списка в кампании {new_status_str}"
    )
