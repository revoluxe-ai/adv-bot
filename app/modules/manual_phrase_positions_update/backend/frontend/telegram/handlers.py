from aiogram import Bot, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery

from app.modules.common_slaves.wildberries.models import AdvSetting
from app.modules.wb_adv_updater import data_manager
from app.modules.wb_adv_updater.phrases_processor import get_good_bad_phrases
from app.utils.db.session_maker import get_async_session_maker as sm

from .buttons import UpdatePositionsForActivePhrase

router = Router()


@router.callback_query(UpdatePositionsForActivePhrase.filter())
async def update_positions_for_active_phrase(
    callback_query: CallbackQuery,
    callback_data: UpdatePositionsForActivePhrase,
    bot: Bot,
    state: FSMContext,
) -> None:
    adv_setting_original_id = callback_data.adv_setting_original_id
    wb_user_cabinet_original_id = callback_data.wb_user_cabinet_original_id

    assert callback_query.message
    chat_id = callback_query.message.chat.id

    async with sm() as session:
        adv_setting: AdvSetting = await session.get(AdvSetting, adv_setting_original_id)

    assert adv_setting

    keywords = await get_good_bad_phrases(adv_setting)


    await bot.send_message(
        chat_id,
        (
           "Данная функция больше не поддерживается со стороны Wildberries"
        ),
    )

    assert adv_setting.nmids


    adv_id = adv_setting.adv_id
    await bot.send_message(
        chat_id,
        (
            f"Перепроверка позиций для РК с adv id {adv_id} завершена. Отправляю эту РК..."
        ),
    )
    nmid = adv_setting.nmids[0]
    main_photos = await data_manager.get_main_photos([nmid])
    adv_choice_last_page = 1
    page = 1

    from importlib import import_module

    AdvKeywordsSetting = import_module( # noqa
        "app.client_bot.user_interface.views.messages.adv_keyword_messages.adv_keyword_messages"
    ).AdvKeywordsSetting
    await AdvKeywordsSetting(
        bot,
        chat_id,
        keywords,
        adv_setting,
        wb_user_cabinet_original_id,
        adv_choice_last_page,
        main_photos[0],
        page,
    )(state)
