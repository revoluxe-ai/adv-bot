from aiogram import Bot, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery
from sqlalchemy import select, update

from app.client_bot import utils
from app.client_bot.user_interface.views import messages
from app.modules.common_slaves.wildberries.models import AdvSetting
from app.modules.wb_adv_updater import data_manager
from app.utils.db.session_maker import get_async_session_maker as sm

from .callbacks import ChangeHideZeroViewsStatus

router = Router()


@router.callback_query(ChangeHideZeroViewsStatus.filter())
async def toggle_hide_zero_views(
    callback_query: CallbackQuery,
    callback_data: ChangeHideZeroViewsStatus,
    state: FSMContext,
    bot: Bot,
) -> None:
    new_status: bool = callback_data.new_status
    adv_id: int = callback_data.adv_id
    wb_user_cabinet_original_id: int = callback_data.wb_user_cabinet_original_id

    # Обновляем статус в БД
    async with sm(read_only=False) as session:
        stmt = (
            update(AdvSetting)
            .where(AdvSetting.adv_id == adv_id)
            .values({"hide_zero_views_keywords": new_status})
        )
        await session.execute(stmt)
        await session.commit()

    # Получаем обновленный AdvSetting
    async with sm(read_only=True) as session:
        query = select(AdvSetting).filter(AdvSetting.adv_id == adv_id)
        result = await session.execute(query)
        adv_setting: AdvSetting = result.scalar_one()

    # Отправляем подтверждение
    assert callback_query.message
    chat_id = callback_query.message.chat.id

    status_str = (
        "Скрытие ключей без рекламных просмотров включено"
        if new_status
        else "Скрытие ключей без рекламных просмотров отключено"
    )

    await bot.send_message(chat_id, status_str)

    # Перерисовываем страницу ключей
    keywords = await utils.get_keywords_for_keyboard(adv_setting)
    nmids = adv_setting.nmids
    adv_choice_last_page = 1

    main_photos = await data_manager.get_main_photos(nmids[:1])

    await messages.AdvKeywordsSetting(
        bot,
        chat_id,
        keywords,
        adv_setting,
        wb_user_cabinet_original_id,
        adv_choice_last_page,
        main_photos[0],
        page=1,
    )(state)

