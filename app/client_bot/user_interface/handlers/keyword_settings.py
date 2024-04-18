import aiogram
from aiogram import Router, types, F
from aiogram.fsm.context import FSMContext
from sqlalchemy import and_
from sqlalchemy.orm import selectinload
from app.modules.common_slaves.wildberries.models import WBUserCabinet, WBCabinet, AdvSetting, KeywordSetting, \
    WBCategory
from sqlalchemy.future import select

from app.modules.wb_adv_updater.models import GlobalCategorySetting
from app.utils.db.session_maker import get_async_session_maker
from ..views import messages
from ..views import callbacks
from app.utils.db.models import User
from app.modules.wb_adv_updater import data_managers
from app.client_bot import utils
from app.utils import redis_manager

router = Router()


_sm = get_async_session_maker()


@router.callback_query(callbacks.SettingKeywords.filter(F.type == 'by_adv'))
async def setting_keywords_by_adv(callback: types.CallbackQuery,
                                  callback_data: callbacks.SettingKeywords,
                                  bot: aiogram.Bot,
                                  state: FSMContext,):
    await callback.answer()
    adv_original_id: int = callback_data.adv_original_id

    async with _sm() as session:
        stmt = select(AdvSetting) \
            .where(AdvSetting.id == adv_original_id)
        result = await session.execute(stmt)
        adv_setting: AdvSetting = result.scalar()

    keywords = await utils.get_keywords_for_keyboard(adv_setting)
    page = callback_data.page
    await state.update_data(last_keyword_setting_page=page)
    state_data = await state.get_data()
    adv_choice_last_page = state_data.get('adv_choice_last_page', 1)
    async with _sm() as session:
        stmt = select(WBUserCabinet) \
            .join(User, User.id == WBUserCabinet.user_id) \
            .join(WBCabinet,
                  WBCabinet.id == WBUserCabinet.wb_cabinet_id) \
            .options(selectinload(WBUserCabinet.user),
                     selectinload(WBUserCabinet.wb_cabinet).selectinload(WBCabinet.adv_settings)) \
            .where(and_(User.user_telegram_id == callback.from_user.id,
                        WBCabinet.id == adv_setting.wb_cabinet_id))
        wb_user_cabinet = await session.execute(stmt)
    wb_user_cabinet = wb_user_cabinet.scalar_one_or_none()
    wb_user_cabinet_original_id = wb_user_cabinet.id
    nmids = adv_setting.nmids
    if nmids:
        main_photos = await data_managers.get_main_photos(nmids[:1])
    else:
        await messages.NoMainPhotos(bot, callback.message.chat.id)()
        return

    chat_id = callback.message.chat.id
    await redis_manager.set_check_last_24_hours(adv_original_id)
    await messages.AdvKeywordsSetting(bot, chat_id,
                                      keywords,
                                      adv_setting,
                                      wb_user_cabinet_original_id,
                                      adv_choice_last_page,
                                      main_photos[0],
                                      page)()

    return




@router.callback_query(callbacks.SettingKeywords.filter())
async def setting_keywords(callback: types.CallbackQuery, callback_data: callbacks.SettingKeyword, bot: aiogram.Bot,
                           state: FSMContext):
    keyword_original_id: int = callback_data.keyword_original_id
    async with _sm() as session:
       stmt = select(KeywordSetting
                     .options(selectinload(KeywordSetting.adv_setting))
                     ).where(KeywordSetting.id == keyword_original_id)
       result = await session.execute(stmt)
       keyword_setting: KeywordSetting = result.scalars().one()
    adv_setting: AdvSetting = keyword_setting.adv_setting
    chat_id = callback.message.chat.id

    data = await state.get_data()
    page = data.get('last_keyword_setting_page', 1)
    await messages.KeywordSettingMessage(bot, chat_id, keyword_setting,
     adv_setting, page)()

    return


@router.callback_query(callbacks.SettingKeyword.filter())
async def setting_keyword(callback: types.CallbackQuery,
                          callback_data: callbacks.SettingKeyword,
                          bot: aiogram.Bot, state: FSMContext):

    await callback.answer()

    keyword_setting_original_id: int = callback_data.keyword_setting_original_id

    async with _sm() as session:
        keyword_setting = await session.execute(select(KeywordSetting)
         .options(selectinload(KeywordSetting.adv_setting))
                                               .where(KeywordSetting.id == keyword_setting_original_id))
        keyword_setting = keyword_setting.scalar()

    data = await state.get_data()
    page = data.get('last_keyword_setting_page', 1)

    adv_setting = keyword_setting.adv_setting
    chat_id = callback.message.chat.id
    await messages.KeywordSettingMessage(bot, chat_id, keyword_setting,
                                                                      adv_setting, page)()

    return




@router.callback_query(callbacks.ChangeKeywordHardStatus.filter())
async def change_keyword_hard_status(callback: types.CallbackQuery,
                                     callback_data: callbacks.ChangeKeywordHardStatus,
                                     bot: aiogram.Bot, state: FSMContext):

    await callback.answer()
    await messages.LongTimeOperation(bot, callback.message.chat.id)()
    new_hard_status = callback_data.new_hard_status
    keyword_setting_original_id = callback_data.keyword_setting_original_id
    async with _sm() as session:
        keyword_setting = await session.execute(select(KeywordSetting)
         .options(selectinload(KeywordSetting.adv_setting))
                                               .where(KeywordSetting.id == keyword_setting_original_id))
        keyword_setting: KeywordSetting = keyword_setting.scalar()
        adv_setting = keyword_setting.adv_setting
        if new_hard_status >= 0:
           keyword_setting.hard_status = new_hard_status

        elif new_hard_status == -1:
            category: WBCategory = await data_managers.get_wb_category(adv_setting)
            smtp = select(GlobalCategorySetting.min_ctr) \
                .where(GlobalCategorySetting.category_name == category.wb_category_name)
            min_ctr = await session.execute(smtp)
            min_ctr = min_ctr.scalar()
            clicks, views, _ = await data_managers.get_keyword_statistic(keyword_setting)
            if keyword_setting.added_clicks:
                clicks += keyword_setting.added_clicks
            if keyword_setting.added_views:
                views += keyword_setting.added_views

            n = 10 # Процент увеличения CTR, который вы хотите достичь

            # Расчет нового CTR
            new_ctr = min_ctr * (1 + n / 100)

            # Вычисление необходимого количества дополнительных кликов
            add_clicks = max([int(round(new_ctr * views - clicks)), 1])

            # Добавление кликов без изменения показов
            if not keyword_setting.added_clicks:
                keyword_setting.added_clicks = 0
            keyword_setting.added_clicks += add_clicks

            keyword_setting.auto_block = False

        await session.commit()
    data = await state.get_data()
    page = data.get('last_keyword_setting_page', 1)

    chat_id = callback.message.chat.id
    await messages.KeywordSettingMessage(bot, chat_id, keyword_setting, adv_setting, page)()

    return

