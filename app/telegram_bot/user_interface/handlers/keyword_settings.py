import aiogram
from aiogram import Router, types, F
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from sqlalchemy.orm import joinedload, selectinload
from app.db.associations import WBUserCabinet
from app.wildberries.models import WBCabinet, AdvSetting, KeywordSetting
from sqlalchemy.future import select
from session_maker import get_async_session_maker
from ..views import messages
from app.my_types import LastMessage
from ..views import callbacks
from .. import states
from ...redis_manager import RedisManager
from app import data_managers
from app.telegram_bot.wb_user_cabinet_manager import CabinetManager
from app.telegram_bot import utils


router = Router()


_sm = get_async_session_maker()


@router.callback_query(callbacks.SettingKeywords.filter(F.type == 'by_adv'))
async def setting_keywords_by_adv(callback: types.CallbackQuery,
                                  callback_data: callbacks.SettingKeywords,
                                  bot: aiogram.Bot,
                                  state: FSMContext,
                                  last_message:LastMessage):
    if callback.id != 'fake_id':
        await callback.answer()
    adv_original_id: int = callback_data.adv_original_id

    async with (_sm() as session):
       stmt = select(AdvSetting
                     ).options(selectinload(AdvSetting.keyword_settings))\
       .where(AdvSetting.id == adv_original_id)
       result = await session.execute(stmt)
       adv_setting: AdvSetting = result.unique().scalars().one()
       keywords = await utils.get_keywords_for_keyboard(session, adv_setting)
       chat_id = callback.message.chat.id
       page = callback_data.page
       state_data = await state.get_data()
       adv_choice_last_page = state_data.get('adv_choice_last_page', 1)
       wb_user_cabinet_original_id = state_data.get('wb_user_cabinet_original_id')
       last_message, message_type = await messages.AdvKeywordsSetting(bot,
                                                                      last_message,
                                                                      chat_id,
                                                                      keywords,
                                                                      adv_setting,
                                                                      wb_user_cabinet_original_id,
                                                                      adv_choice_last_page,
                                                                      page)()


       return last_message, message_type




@router.callback_query(callbacks.SettingKeywords.filter())
async def setting_keywords(callback: types.CallbackQuery, callback_data: callbacks.SettingKeyword, bot: aiogram.Bot, last_message:LastMessage):
    if callback.id != 'fake_id':
        await callback.answer()
    keyword_original_id: int = callback_data.keyword_original_id
    async with _sm() as session:
       stmt = select(KeywordSetting
                     .options(selectinload(KeywordSetting.adv_setting))
                     ).where(KeywordSetting.id == keyword_original_id)
       result = await session.execute(stmt)
       keyword_setting: KeywordSetting = result.scalars().one()
       adv_setting: AdvSetting = keyword_setting.adv_setting
       chat_id = last_message.chat.id
       last_message, message_type = await messages.KeywordSettingMessage(bot, last_message,
                                                                         chat_id, keyword_setting,
                                                                         adv_setting)()

       return last_message, message_type





@router.callback_query(callbacks.SettingKeyword.filter())
async def setting_keyword(callback: types.CallbackQuery,
                          callback_data: callbacks.SettingKeyword,
                          bot: aiogram.Bot,
                          last_message:LastMessage):

    if callback.id != 'fake_id':
        await callback.answer()

    keyword_setting_original_id: int = callback_data.keyword_setting_original_id

    async with _sm() as session:
        keyword_setting = await session.execute(select(KeywordSetting)
         .options(selectinload(KeywordSetting.adv_setting))
                                               .where(KeywordSetting.id == keyword_setting_original_id))
        keyword_setting = keyword_setting.scalar()

    chat_id = last_message.chat.id
    adv_setting = keyword_setting.adv_setting
    last_message, message_type = await messages.KeywordSettingMessage(bot, last_message,
                                                                      chat_id, keyword_setting,
                                                                      adv_setting)()

    return last_message, message_type




@router.callback_query(callbacks.ChangeKeywordHardStatus.filter())
async def change_keyword_hard_status(callback: types.CallbackQuery,
                                     callback_data: callbacks.ChangeKeywordHardStatus,
                                     bot: aiogram.Bot,
                                     last_message:LastMessage):
    if callback.id != 'fake_id':
        await callback.answer()
    new_hard_status = callback_data.new_hard_status
    keyword_setting_original_id = callback_data.keyword_setting_original_id
    async with _sm() as session:
        keyword_setting = await session.execute(select(KeywordSetting)
         .options(selectinload(KeywordSetting.adv_setting))
                                               .where(KeywordSetting.id == keyword_setting_original_id))
        keyword_setting = keyword_setting.scalar()
        keyword_setting.hard_status = new_hard_status
        await session.commit()
    chat_id = last_message.chat.id
    adv_setting = keyword_setting.adv_setting
    last_message, message_type = await messages.KeywordSettingMessage(bot, last_message,
                                                                      chat_id, keyword_setting,
                                                                      adv_setting)()

    return last_message, message_type

