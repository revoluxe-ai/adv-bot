from aiogram import Bot, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery

from app.modules.common_slaves.wildberries.data_classes.keywordstat_from_db import CalculatedKeyword, KeywordStatus
from app.modules.common_slaves.wildberries.models import AdvSetting
from app.modules.wb_adv_updater import data_manager
from app.modules.wb_keywords_parser.wb_parser import parser
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

    keywords = await data_manager.get_good_bad_phrases(adv_setting)

    target = callback_data.target

    def filter_func(kw: CalculatedKeyword) -> bool:
        if target == "white_list":
            return kw.hard_status == 2
        elif target == "active_phrases":
            return kw.status == KeywordStatus.GOOD
        else:
            raise ValueError("Неизвестная цель проверки позиций")

    active_keywords = filter(filter_func, keywords)

    await bot.send_message(
        chat_id,
        (
            "Начинаю перепроверку позиций. По завершению перепроверки пришлю новую версию страницы с ключами."
            " Вы можете продолжить работу с ботом, решая другие задачи"
        ),
    )

    assert adv_setting.nmids

    nmids = set(adv_setting.nmids[:1])

    for kw in active_keywords:
        await parser.add_wb_positions(kw.text, nmids, delay=1)
    adv_id = adv_setting.adv_id
    await bot.send_message(
        chat_id,
        (f"Перепроверка позиций для РК с adv id {adv_id} завершена. Отправляю эту РК..."),
    )
    nmid = adv_setting.nmids[0]
    main_photos = await data_manager.get_main_photos([nmid])
    adv_choice_last_page = 1
    page = 1

    from importlib import import_module

    AdvKeywordsSetting = import_module(
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
