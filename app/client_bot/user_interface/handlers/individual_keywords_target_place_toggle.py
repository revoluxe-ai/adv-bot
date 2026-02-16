from aiogram import Bot, Router
from aiogram.types import CallbackQuery
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.client_bot.user_interface.views.callbacks import IndividualKeywordsTargetPlaceToggle
from app.modules import balance_manager
from app.modules.billing.pricer import Pricer
from app.modules.common_slaves.wildberries.models import AdvSetting
from app.utils.db.session_maker import get_async_session_maker as sm

router = Router()

@router.callback_query(IndividualKeywordsTargetPlaceToggle.filter())
async def toggle_individual_keywords_target_place(
    callback_query: CallbackQuery,
    callback_data: IndividualKeywordsTargetPlaceToggle,
    bot: Bot,
) -> None:
    new_status = callback_data.new_status
    adv_id = callback_data.adv_id
    pricer = Pricer()

    assert callback_query.message
    chat_id = callback_query.message.chat.id

    async with sm() as session:
        async with session.begin():
            stmt = (
                select(AdvSetting)
                .options(selectinload(AdvSetting.wb_cabinet))
                .where(AdvSetting.adv_id == adv_id)
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

            if new_status:
                balance, bonus = await balance_manager.get_cabinet_balance_and_bonuses(
                    adv_setting.wb_cabinet.id
                )
                available = balance + bonus
                required_price = (
                    await pricer.get_price_for_day_if_enabling_individual_mode(
                        session,
                        adv_setting.wb_cabinet.shop_id or "",
                        adv_setting.id,
                    )
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

            adv_setting.individual_keywords_target_place_mode = new_status
            status_text = (
                "Инд. места КЗ включены"
                if new_status
                else "Инд. места КЗ выключены"
            )

    await bot.send_message(chat_id, status_text)
