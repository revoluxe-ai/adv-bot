from operator import and_
from typing import Union
import aiogram
from aiogram import Router, types
from aiogram.filters import StateFilter, CommandStart
from aiogram.fsm.context import FSMContext
from sqlalchemy.orm import joinedload, selectinload
from app.modules.common_slaves.wildberries.models import WBUserCabinet, WBToken
from app.modules.common_slaves.wildberries.exceptions import NotValidTokenError, ApiForbiddenError
from sqlalchemy.future import select
from app.modules.common_slaves.wildberries.models import WBCabinet
from app.modules.common_slaves.wildberries.super_cabinet_manager import WBCabinetAccess
from app.utils.db.models import RefLink
from app.utils.db.session_maker import get_async_session_maker
from   .. import states
from app.modules.wb_adv_updater.right_checker import RightChecker
from aiogram.types import Message, CallbackQuery
from ..views.callbacks import Action
from ... import const
from ...redis_manager import RedisManager
import logging
from ..views import callbacks, messages
from app.utils.db.models import User
from app.modules.common_slaves.wildberries import models as wb_models, super_cabinet_manager
from app.modules.common_slaves.wildberries.shops_data_updater import ShopDataUpdater
from app.client_bot import const

logger = logging.getLogger(__name__)

sm = get_async_session_maker

router = Router()


redis_manager = RedisManager()




async def start_registration(message: types.Message, bot: aiogram.Bot, state: FSMContext):
    await state.clear()
    referral_link  = None
    async with sm(read_only=False) as session:
        user_id = message.from_user.id
        if isinstance(message, types.Message) and message.text:
            text = message.text.split(' ')
            if len(text) > 1 and text[1].isdigit():
                referral_link_id = int(text[1])
                stmt = select(RefLink) \
                    .options(selectinload(RefLink.referred_users)) \
                    .where(RefLink.id == referral_link_id)
                referral_link = (await session.execute(stmt)).scalar()

        stmt = select(User)\
            .options(joinedload(User.wb_user_cabinets).joinedload(
            WBUserCabinet.wb_cabinet)) \
            .where(User.user_telegram_id == user_id)
        result = await session.execute(stmt)
        user: User = result.scalar()
        if not user:
            user = User(user_telegram_id=user_id,
                        username=message.from_user.username,
                        adv_updater_user_chat_id = message.chat.id,
                        wb_tokens=[])
            session.add(user)
            if referral_link:
                referral_link.referred_users.append(user)
            await session.commit()
            await session.refresh(user)
            wb_user_cabinets = []
        else:
            wb_user_cabinets = user.wb_user_cabinets
        if isinstance(message, types.Message):
            chat_id = message.chat.id
        else:
            chat_id = message.message.chat.id

        await messages. \
                ShopChoice(bot, chat_id, wb_user_cabinets)()
    return



async def callback_start_registration(callback: CallbackQuery,
                                      callback_data: callbacks.Start,
                                      bot: aiogram.Bot, state: FSMContext):
    await state.clear()
    async with sm() as session:
        user_id = callback.from_user.id

        stmt = select(User)\
            .options(joinedload(User.wb_user_cabinets).joinedload(
            WBUserCabinet.wb_cabinet)) \
            .where(User.user_telegram_id == user_id)
        result = await session.execute(stmt)
        user: User = result.scalar()

        wb_user_cabinets = user.wb_user_cabinets
        chat_id = callback.message.chat.id
        await messages. \
                ShopChoice(bot, chat_id, wb_user_cabinets)()
    return




@router.callback_query(callbacks.ShopNew.filter())
async def add_shop(callback_query: types.CallbackQuery,
                   bot: aiogram.Bot, state: FSMContext):
    await bot.send_message(callback_query.message.chat.id, 'Добавление нового магазина (кабинета)')
    await state.set_state(states.CabinetRegistration.cabinet_name)
    chat_id: int = callback_query.message.chat.id
    await messages.ShopNameGet(bot, chat_id)()



@router.message(StateFilter(states.CabinetRegistration.cabinet_name))
async def process_cabinet_name(message: Message, bot: aiogram.Bot, state: FSMContext):
    catch_cab: Union[WBUserCabinet, None] = None
    cabinet_name = message.text
    chat_id = message.chat.id
    if len(cabinet_name) > 50:
        await messages. \
            CabinetNameTooLong(bot, chat_id)()
        return
    async with sm() as session:
        stmt = select(User).options(joinedload(User.wb_user_cabinets).joinedload(
            WBUserCabinet.wb_cabinet)) \
            .where(User.user_telegram_id == message.from_user.id)
        result = await session.execute(stmt)
        user = result.scalar()
    for cabinet in user.wb_user_cabinets:
        if cabinet.name == cabinet_name:
            catch_cab: WBUserCabinet = cabinet
            break
    if catch_cab:
        await state.set_state(state=None)
        await state.set_state(states.CabinetRegistration.cabinet_name)
        await messages. \
            CabinetNameExists(bot, chat_id)()

    else:
        cabinet_name = message.text
        await state.update_data(cabinet_name=cabinet_name)
        await state.set_state(states.CabinetRegistration.api)
        await messages.AddNewTokenGet(bot, chat_id, cabinet_name)()



@router.message(StateFilter(states.CabinetRegistration.api))
async def process_cabinet_api( message: Message, bot: aiogram.Bot, state: FSMContext):
    text = message.text
    if '/start' in text:
        await start_registration(message, bot, state)
        return
    api = message.text
    api = api.strip()
    user_telegram_id = message.from_user.id
    wb_token = wb_models.WBToken(api_key=api)
    access = WBCabinetAccess(tokens=[wb_token], wb_user_cabinet=None, wb_cabinet=None)
    chat_id = message.chat.id
    try:
        await RightChecker.check_access(wb_token)
    except NotValidTokenError:
        await messages. \
            NotValideToken(bot, chat_id)()
        return
    except ApiForbiddenError:
        await messages. \
            GetApiForrbidenError(bot, chat_id)()
        return
    except Exception as e:
        logger.error('Ошибка при проверке токена, токен пропускаем: %s', e)
    await messages.ShopUpdateInfo(bot, chat_id)()
    data_state: dict = await state.get_data()
    cabinet_name = data_state['cabinet_name'].strip()
    user_id = message.from_user.id
    #получаем юзера
    async with sm(read_only=False) as session:
        stmt = select(User).\
        options(joinedload(User.wb_tokens))\
        .where(User.user_telegram_id == user_id)
        result = await session.execute(stmt)
        user = result.scalar()
        wb_tokens: list[WBToken] = user.wb_tokens
        if wb_token.api_key not in [token.api_key for token in wb_tokens]:
            wb_tokens.append(wb_token)
            await session.commit()

    #проверяем есть ли кабинет именно у этого юзера
    async with sm(read_only=False) as session:
        stmt = select(WBCabinet)\
        .join(WBCabinet.wb_user_cabinets)\
        .join(WBUserCabinet.user)\
        .where(and_(WBCabinet.shop_id == wb_token.shop_id,
                    WBUserCabinet.user_id == user.id))
        result = await session.execute(stmt)
        wb_cabinet = result.scalar()
        if wb_cabinet:#если кабинет у юзера есть
            stmt = select(WBUserCabinet).where(and_(WBUserCabinet.wb_cabinet_id == wb_cabinet.id,
                                                    WBUserCabinet.user_id == user.id))
            result = await session.execute(stmt)
            wb_user_cabinet = result.scalar()

            await messages. \
                CabinetExistsForUser(bot, chat_id)()

            await messages. \
                    AdvCompanyChoicing(bot, state, chat_id, wb_user_cabinet.id, page=1)()
            return
        else: #если кабинета у юзера нет
            #проверяем есть ли такой кабинет вообще
            stmt = select(WBCabinet).\
                where(WBCabinet.shop_id == wb_token.shop_id)
            result = await session.execute(stmt)
            wb_cabinet = result.scalar()
            if not wb_cabinet: #если кабинета нет, то создаем кабинет
                wb_cabinet = WBCabinet(shop_id=wb_token.shop_id)
                wb_cabinet.bonus = 0
                session.add(wb_cabinet)
            access.wb_cabinet = wb_cabinet
            wb_user_cabinet = WBUserCabinet(name=cabinet_name)
            wb_user_cabinet.user = user
            wb_user_cabinet.wb_cabinet = wb_cabinet
            session.add(wb_user_cabinet)
            await session.commit()
            await session.refresh(wb_user_cabinet)
            stmt = select(WBToken).where(
                WBToken.api_key == wb_token.api_key,
                WBToken.user_id == wb_token.user_id
            )
            existing_token = (await session.execute(stmt)).scalar()

            if not existing_token:
                # Если токен не найден, добавляем новый
                user.wb_tokens.append(wb_token)
            await messages. \
                ShopAddedSuccess(bot, chat_id, cabinet_name)()

    shop_updater = ShopDataUpdater(access)
    await shop_updater.quick_update_all_data()
    async with sm() as session:
        stmt = select(WBUserCabinet)\
            .join(WBUserCabinet.user)\
        .where(User.user_telegram_id == user_telegram_id )
        result = await session.execute(stmt)
        wb_user_cabinets = result.scalars().all()

    await messages. \
        ShopChoice(bot, chat_id, wb_user_cabinets)()
    return


#
#
# @router.callback_query(callbacks.DeleteWbUserCabinet.filter())
# async def delete_shop(callback_query: types.CallbackQuery,
#                       callback_data : callbacks.DeleteWbUserCabinet,
#                       bot: aiogram.Bot,
#                       state: FSMContext):
#     await bot.send_message(callback_query.message.chat.id, 'Удаление магазина (кабинета)')
#     wb_cabinet_original_id = callback_data.wb_cabinet_original_id
#     async with sm() as session:
#         stmt = select(WBUserCabinet).options(
#             joinedload(WBUserCabinet.user),
#
#         ).where(WBUserCabinet.wb_cabinet_id == wb_cabinet_original_id)
#         result = await session.execute(stmt)
#         wb_user_cabinet = result.scalars().first()
#         session.delete(wb_user_cabinet)
#         await session.commit()
#         user = wb_user_cabinet.user
#         await session.refresh(user)
#     all_shops = user.wb_user_cabinets
#     chat_id = callback_query.message.chat.id
#     await messages. \
#         ShopChoice(bot, chat_id, all_shops)()
#     return
#

@router.callback_query(callbacks.AddNewToken.filter())
async def add_app_token(callback_query: types.CallbackQuery,
                  callback_data: callbacks.AddNewToken,
                  bot: aiogram.Bot, state: FSMContext):
    logger.debug('Текущее состояние: %s', await state.get_state())
    wb_user_cabinet_original_id = callback_data.wb_user_cabinet_original_id
    async with sm() as session:
        stmt = select(WBUserCabinet).where(WBUserCabinet.id == wb_user_cabinet_original_id)
        result = await session.execute(stmt)
        wb_user_cabinet = result.scalars().first()
    await state.update_data(wb_user_cabinet_original_id=wb_user_cabinet_original_id)
    await state.set_state(states.AddNewToken.token)
    chat_id = callback_query.message.chat.id
    cabinet_name = wb_user_cabinet.name
    await messages. \
        AddNewTokenGet(bot, chat_id, cabinet_name)()



@router.message(StateFilter(states.AddNewToken.token))
async def process_app_token(message: Message, bot: aiogram.Bot, state: FSMContext):
    wb_user_cabinet_original_id: int = (await state.get_data())['wb_user_cabinet_original_id']
    async with sm() as session:
        stmt = select(WBUserCabinet).options(joinedload(WBUserCabinet.user),
                                             joinedload(WBUserCabinet.wb_cabinet)) \
            .where(WBUserCabinet.id == wb_user_cabinet_original_id)
        result = await session.execute(stmt)
        wb_user_cabinet = result.scalars().first()
    user: User = wb_user_cabinet.user
    api = message.text
    api = api.strip()
    wb_token = wb_models.WBToken(api_key=api)
    user.wb_tokens.append(wb_token)
    chat_id = message.chat.id
    try:
         check_right = await RightChecker.check_access(wb_user_cabinet)
    except NotValidTokenError:
         await messages. \
            NotValideToken(bot, chat_id)()
         return
    if not check_right:
        await messages. \
            GetApiForrbidenError(bot, chat_id)()
        return
    else:
        async with sm(read_only=False) as session:
            user.wb_tokens.append(wb_token)
            session.add(user)
            await session.commit()
            await session.refresh(user)
        await messages. \
            ShopAddedSuccess(bot, chat_id, wb_user_cabinet.name)()
        all_shops = wb_user_cabinet.user.wb_user_cabinets
        await messages. \
            ShopChoice(bot, chat_id, all_shops)()
        await state.set_state(state=None)
        return


@router.callback_query(callbacks.ChoiceAdvPaginator.filter())
async def select_shop(callback_query: types.CallbackQuery,
                      callback_data: callbacks.Shop,
                      bot: aiogram.Bot, state: FSMContext):
    reset_filter = callback_data.reset_filter
    if reset_filter:
        await state.update_data(filter_advs=None)
    wb_user_cabinet_original_id = callback_data.wb_user_cabinet_original_id
    await state.update_data(last_wb_user_cabinet_original_id = wb_user_cabinet_original_id)
    message = callback_query.message

    chat_id = message.chat.id
    # await state.update_data(chat_id = chat_id)


    await messages.AdvCompanyChoicing \
        (bot, state, chat_id, wb_user_cabinet_original_id, page=1)()
    return


@router.callback_query(callbacks.Shop.filter(aiogram.F.action == Action.select))
async def shop_menu_process(
    callback: types.CallbackQuery,
    callback_data: callbacks.Shop,
    bot: aiogram.Bot,
    state: FSMContext,
):
    await state.update_data(last_wb_user_cabinet_original_id = callback_data.wb_user_cabinet_original_id)
    logger.debug('Текущее состояние: %s', await state.get_data())
    wb_user_cabinet_original_id = callback_data.wb_user_cabinet_original_id
    await messages.ShopMenu(bot, callback.message.chat.id, state, wb_user_cabinet_original_id)()



@router.callback_query(callbacks.UpdateCompanyFromWB.filter())
async def update_company_from_wb(callback_query: types.CallbackQuery,
                                    bot: aiogram.Bot,
                                    callback_data: callbacks.UpdateCompanyFromWB,
                                   state: FSMContext):
    await messages.LongTimeOperation(bot, callback_query.message.chat.id)()
    wb_user_cabinet_original_id = callback_data.wb_user_cabinet_original_id
    async with sm() as session:
        stmt = select(WBUserCabinet) \
            .options(
            joinedload(WBUserCabinet.user)\
                .joinedload(User.wb_tokens),
            joinedload(WBUserCabinet.wb_cabinet)
        ) \
            .where(WBUserCabinet.id == wb_user_cabinet_original_id)
        result = await session.execute(stmt)
        wb_user_cabinet: WBUserCabinet = result.scalar()
    wb_cabinet = wb_user_cabinet.wb_cabinet
    access = await super_cabinet_manager.get_access_for_wb_cabinet(wb_cabinet.id)
    shop_updater = ShopDataUpdater(access)
    try:
        await shop_updater.quick_update_all_data()
    except:
        await bot.send_message(callback_query.message.chat.id,
                               f'Ошибка при обновлении данных, обратитесь в поддержку {const.SUPPORT_LINK}')

    await messages.AdvCompanyChoicing(bot,
                                      state,
                                      callback_query.message.chat.id,
                                      wb_user_cabinet_original_id, page=1)()









router.callback_query.register(callback_start_registration, callbacks.Start.filter())
router.message.register(start_registration, CommandStart())
