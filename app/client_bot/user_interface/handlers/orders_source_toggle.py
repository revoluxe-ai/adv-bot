from aiogram import Bot, Router
from aiogram.types import CallbackQuery
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.client_bot.user_interface.views.callbacks import OrdersSourceToggle
from app.client_bot.user_interface.views.keyboards import get_adv_setting_keyboard
from app.modules.common_slaves.wildberries.models import AdvSetting, WBUserCabinet
from app.modules.common_slaves.wildberries.models.enums import OrdersSourceForAutoMode
from app.modules.wb_adv_updater import data_manager
from app.utils.db.models import User
from app.utils.db.session_maker import get_async_session_maker as sm

router = Router()


@router.callback_query(OrdersSourceToggle.filter())
async def toggle_orders_source(
    callback_query: CallbackQuery,
    callback_data: OrdersSourceToggle,
    _bot: Bot,
) -> None:
    adv_setting_original_id: int = callback_data.adv_setting_original_id

    async with sm(read_only=False) as session:
        stmt = (
            select(AdvSetting)
            .options(selectinload(AdvSetting.wb_cabinet))
            .where(AdvSetting.id == adv_setting_original_id)
        )
        result = await session.execute(stmt)
        adv_setting: AdvSetting | None = result.scalar_one_or_none()

        if adv_setting is None:
            await callback_query.answer("Настройки не найдены", show_alert=True)
            return

        current_source = (
            adv_setting.orders_source_for_auto_mode
            or OrdersSourceForAutoMode.COMMON_STATISTIC
        )
        if current_source == OrdersSourceForAutoMode.ADV_SUM:
            new_source = OrdersSourceForAutoMode.COMMON_STATISTIC
        else:
            new_source = OrdersSourceForAutoMode.ADV_SUM

        adv_setting.orders_source_for_auto_mode = new_source

        user_stmt = select(User).where(
            User.user_telegram_id == callback_query.from_user.id
        )
        user_result = await session.execute(user_stmt)
        user: User | None = user_result.scalar_one_or_none()
        if user is None:
            await session.commit()
            await callback_query.answer("Пользователь не найден", show_alert=True)
            return

        wb_user_cabinet_stmt = (
            select(WBUserCabinet)
            .options(selectinload(WBUserCabinet.wb_cabinet))
            .where(
                WBUserCabinet.user_id == user.id,
                WBUserCabinet.wb_cabinet_id == adv_setting.wb_cabinet_id,
            )
        )
        wb_user_cabinet_result = await session.execute(wb_user_cabinet_stmt)
        wb_user_cabinet: WBUserCabinet | None = (
            wb_user_cabinet_result.scalar_one_or_none()
        )

        await session.commit()
        await session.refresh(adv_setting)

    assert callback_query.message

    if wb_user_cabinet is None:
        await callback_query.answer("Кабинет пользователя не найден", show_alert=True)
        return

    in_favorites = await data_manager.is_adv_in_favorites(
        adv_setting.id, wb_user_cabinet.user_id
    )

    keyboard = get_adv_setting_keyboard(
        callback_query.message.chat.id,
        wb_user_cabinet,
        adv_setting,
        in_favorites,
    )

    await callback_query.message.edit_reply_markup(reply_markup=keyboard)

    if new_source == OrdersSourceForAutoMode.ADV_SUM:
        status_str = "Включен режим анализа только рекламных заказов"
    else:
        status_str = "Включен режим анализа общей статистики заказов"

    await callback_query.answer(status_str)
