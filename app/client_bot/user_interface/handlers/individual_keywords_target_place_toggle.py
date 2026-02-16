from collections.abc import Awaitable, Callable

from aiogram import Bot, Router
from aiogram.types import CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession

from app.client_bot.user_interface.views.callbacks import (
    IndividualKeywordsTargetPlaceToggle,
)
from app.modules.billing.paid_option_check import (
    format_insufficient_funds_message,
    get_adv_setting_and_check_funds_for_enabling,
)
from app.modules.billing.pricer import Pricer
from app.utils.db.session_maker import get_async_session_maker as sm

router = Router()


def _price_getter(
    pricer: Pricer,
) -> Callable[[AsyncSession, str, int], Awaitable[float]]:
    async def getter(
        session: AsyncSession, shop_id: str, adv_setting_id: int
    ) -> float:
        return await pricer.get_price_for_day_if_enabling_individual_mode(
            session, shop_id, adv_setting_id
        )

    return getter


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

    get_required_price = _price_getter(pricer) if new_status else None
    send_insufficient_funds: (
        Callable[[float, float], Awaitable[object]] | None
    ) = (
        (
            lambda req, av: bot.send_message(
                chat_id,
                format_insufficient_funds_message(req, av),
            )
        )
        if new_status
        else None
    )

    async with sm() as session:
        async with session.begin():
            adv_setting = await get_adv_setting_and_check_funds_for_enabling(
                session,
                adv_id=adv_id,
                send_adv_not_found=lambda: bot.send_message(
                    chat_id, "РК не найдена"
                ),
                send_no_cabinet=lambda: bot.send_message(
                    chat_id, "Не удалось найти кабинет для кампании"
                ),
                get_required_price=get_required_price,
                send_insufficient_funds=send_insufficient_funds,
            )
            if adv_setting is None:
                return

            adv_setting.individual_keywords_target_place_mode = new_status
            status_text = (
                "Инд. места КЗ включены"
                if new_status
                else "Инд. места КЗ выключены"
            )

    _ = await bot.send_message(chat_id, status_text)
