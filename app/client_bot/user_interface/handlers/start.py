import asyncio
from operator import and_
from typing import Union
from app.modules import wb_adv_updater
import aiogram
from aiogram import Router, types
from aiogram.fsm.context import FSMContext
from sqlalchemy.orm import joinedload, selectinload
from app.modules.common_slaves.wildberries.models import WBUserCabinet, WBCabinet, WBToken
from app.modules.common_slaves.wildberries.exceptions import NotValidTokenError, ApiForbiddenError
from sqlalchemy.future import select
from app.modules.common_slaves.wildberries.models import AdvSetting, WBCabinet
from app.modules.common_slaves.wildberries.super_cabinet_manager import WBCabinetAccess
from app.utils.db.session_maker import get_async_session_maker
from   .. import states
from ..views import messages
from aiogram.filters import StateFilter, CommandStart
from aiogram.types import Message
from ...redis_manager import RedisManager
import logging
from ..views import callbacks
from app.my_types import User
from app.client_bot.wb_user_cabinet_manager import CabinetManager
from app.modules.common_slaves.wildberries import models as wb_models
from app.modules.common_slaves.wildberries import super_cabinet_manager as scm
from app.modules.common_slaves.wildberries.shops_data_updater import ShopDataUpdater


logger = logging.getLogger(__name__)





sm = get_async_session_maker()

router = Router()
# router.message.middleware(middlewars.UserDataMiddleware())
# router.callback_query.middleware(middlewars.UserDataMiddleware())



redis_manager = RedisManager()


@router.message(CommandStart())
async def start_registration(message: types.Message, bot: aiogram.Bot):
    user_id = message.from_user.id
    async with sm() as session:
        stmt = select(User)\
            .options(joinedload(User.wb_user_cabinets).joinedload(
            WBUserCabinet.wb_cabinet)) \
            .where(User.user_telegram_id == user_id)
        result = await session.execute(stmt)
        user = result.scalar()
        if not user:
            user = User(user_telegram_id=user_id,
                        username=message.from_user.username,
                        adv_updater_user_chat_id = message.chat.id,
                        wb_tokens=[])
            session.add(user)
            await session.commit()
            await session.refresh(user)
            wb_user_cabinets = []
        else:
            wb_user_cabinets = user.wb_user_cabinets
        chat_id = message.chat.id
        await messages. \
                ShopChoice(bot, chat_id, wb_user_cabinets)()
    return

@router.callback_query(callbacks.Shop.filter(aiogram.F.action == callbacks.Action.new))
async def add_shop(callback_query: types.CallbackQuery,
                   bot: aiogram.Bot, state: FSMContext):
    await callback_query.answer('Добавление нового магазина (кабинета)')
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
        await state.clear()
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
    api = message.text
    api = api.strip()
    user_telegram_id = message.from_user.id
    wb_token = wb_models.WBToken(api_key=api)
    access = WBCabinetAccess(tokens=[wb_token], wb_user_cabinet=None, wb_cabinet=None)
    chat_id = message.chat.id
    try:
        await CabinetManager.check_access(wb_token)
    except NotValidTokenError:
        await messages. \
            NotValideToken(bot, chat_id)()
        return
    except ApiForbiddenError:
        await messages. \
            GetApiForrbidenError(bot, chat_id)()
        return
    await messages.ShopUpdateInfo(bot, chat_id)()
    data_state: dict = await state.get_data()
    cabinet_name = data_state['cabinet_name'].strip()
    user_id = message.from_user.id
    #получаем юзера
    async with sm() as session:
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
    async with sm() as session:
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
            wb_cabinet = wb_user_cabinet.wb_cabinet
            async with sm() as session:
                 stmt = select(AdvSetting)\
                      .join(AdvSetting.wb_cabinet)\
                     .where(WBCabinet.id ==  wb_cabinet.id)
                 result = await session.execute(stmt)
                 adv_settings = result.unique().scalars().all()
            await messages. \
                    AdvCompanyChoicing(bot, chat_id, wb_user_cabinet.id, adv_settings, page=1)(state)
            return
        else: #если кабинета у юзера нет
            #проверяем есть ли такой кабинет вообще
            stmt = select(WBCabinet).\
                where(WBCabinet.shop_id == wb_token.shop_id)
            result = await session.execute(stmt)
            wb_cabinet = result.scalar()
            if not wb_cabinet: #если кабинета нет, то создаем кабинет
                wb_cabinet = WBCabinet(shop_id=wb_token.shop_id)
                session.add(wb_cabinet)
            access.wb_cabinet = wb_cabinet
            wb_user_cabinet = WBUserCabinet(name=cabinet_name)
            wb_user_cabinet.user = user
            user.wb_tokens.append(wb_token)
            wb_user_cabinet.wb_cabinet = wb_cabinet
            session.add(wb_user_cabinet)
            await session.commit()
            await session.refresh(wb_user_cabinet)
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




@router.callback_query(callbacks.DeleteWbUserCabinet.filter())
async def delete_shop(callback_query: types.CallbackQuery,
                      callback_data : callbacks.DeleteWbUserCabinet,
                      bot: aiogram.Bot,
                      state: FSMContext):
    await callback_query.answer('Удаление магазина (кабинета)')
    wb_cabinet_original_id = callback_data.wb_cabinet_original_id

    async with sm() as session:
        stmt = select(WBUserCabinet).options(
            joinedload(WBUserCabinet.user),

        ).where(WBUserCabinet.wb_cabinet_id == wb_cabinet_original_id)
        result = await session.execute(stmt)
        wb_user_cabinet = result.scalars().first()
        session.delete(wb_user_cabinet)
        await session.commit()
        user = wb_user_cabinet.user
        await session.refresh(user)
    all_shops = user.wb_user_cabinets
    chat_id = callback_query.message.chat.id
    await messages. \
        ShopChoice(bot, chat_id, all_shops)()
    return


@router.callback_query(callbacks.AddNewToken.filter())
async def add_app_token(callback_query: types.CallbackQuery,
                  callback_data: callbacks.AddNewToken,
                  bot: aiogram.Bot, state: FSMContext):
    await callback_query.answer()
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
         check_right = await CabinetManager.check_access(wb_user_cabinet)
    except NotValidTokenError:
         await messages. \
            NotValideToken(bot, chat_id)()
         return
    if not check_right:
        await messages. \
            GetApiForrbidenError(bot, chat_id)()
        return
    else:
        async with sm() as session:
            user.wb_tokens.append(wb_token)
            session.add(user)
            await session.commit()
            await session.refresh(user)
        await messages. \
            ShopAddedSuccess(bot, chat_id, wb_user_cabinet.name)()
        all_shops = wb_user_cabinet.user.wb_user_cabinets
        await messages. \
            ShopChoice(bot, chat_id, all_shops)()
        await state.clear()
        return


@router.callback_query(callbacks.Shop.filter(aiogram.F.action == callbacks.Action.select))
async def select_shop(callback_query: types.CallbackQuery,
                      callback_data: callbacks.Shop,
                      bot: aiogram.Bot, state: FSMContext):
    wb_user_cabinet_original_id = callback_data.wb_user_cabinet_original_id
    await state.update_data(last_wb_user_cabinet_original_id = wb_user_cabinet_original_id)
    await callback_query.answer('Выбор магазина (кабинета)')
    message = callback_query.message

    chat_id = message.chat.id
    await state.update_data(chat_id = chat_id)
    # async with sm() as session:
    #     stmt = select(WBUserCabinet).options(
    #         selectinload(WBUserCabinet.wb_cabinet),
    #         selectinload(WBUserCabinet.user).
    #          selectinload(User.wb_tokens))\
    #     .where(WBUserCabinet.id == wb_user_cabinet_original_id)
    #     result = await session.execute(stmt)
    #     wb_user_cabinet = result.scalar()
    # wb_api = WBApi(wb_user_cabinet)
    # # updater = ShopDataUpdater(wb_api, wb_user_cabinet)
    # # await updater.update_all_data()

    async with sm() as session:
        stmt = select(AdvSetting
                      )\
            .join(AdvSetting.wb_cabinet) \
            .join(WBCabinet.wb_user_cabinets) \
            .filter(WBUserCabinet.id == wb_user_cabinet_original_id)
        result = await session.execute(stmt)
        adv_settings = result.unique().scalars().all()


    await messages.AdvCompanyChoicing \
        (bot, chat_id, wb_user_cabinet_original_id, adv_settings, page=1)()
    return
