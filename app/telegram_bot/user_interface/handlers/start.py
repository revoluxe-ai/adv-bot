import asyncio
import aiogram
from aiogram import Router, types
from aiogram.fsm.context import FSMContext
from sqlalchemy.orm import joinedload

from app.db.associations import WBUserCabinet
from app.wildberries.exceptions import NotValidTokenError, ApiForbiddenError
from app.wildberries import models
from sqlalchemy.future import select
from session_maker import get_async_session_maker
from app.telegram_bot.user_interface import states
from app.telegram_bot.user_interface.views import messages
from aiogram.filters import StateFilter, CommandStart
from aiogram.types import Message
from app.my_types import LastMessage
from ...redis_manager import RedisManager
import logging
from ..views import callbacks
from app.telegram_bot import middlewars
from app.telegram_bot.models import User
from app.telegram_bot.wb_user_cabinet_manager import CabinetManager
from app.wildberries import models as wb_models
import app



logger = logging.getLogger(__name__)





sm = get_async_session_maker()

router = Router()
router.message.middleware(middlewars.UserDataMiddleware())
router.callback_query.middleware(middlewars.UserDataMiddleware())


redis_manager = RedisManager()


@router.message(CommandStart())
async def start_registration(message: types.Message, bot: aiogram.Bot, state: FSMContext,
                             last_message: types.Message, user: User):
        wb_user_cabinets: list[WBUserCabinet] = user.wb_user_cabinets
        if wb_user_cabinets:
            last_message, message_type = await messages. \
                ShopChoice(bot, last_message, wb_user_cabinets)()
            return last_message, message_type
        else:
            await state.set_state(states.CabinetRegistration.cabinet_name)
            last_message, message_type = await messages.ShopNameGet(bot, last_message, message.chat.id)()
            return last_message, message_type

@router.callback_query(callbacks.Shop.filter(aiogram.F.action == callbacks.Action.new))
async def app_shop(callback_query: types.CallbackQuery,
                   bot: aiogram.Bot, state: FSMContext, last_message: LastMessage):
    await callback_query.answer('Добавление нового магазина (кабинета)')
    await state.set_state(states.CabinetRegistration.cabinet_name)
    last_message, message_type = await messages.ShopNameGet(bot, last_message, callback_query.message.chat.id)()
    return last_message, message_type



@router.message(StateFilter(states.CabinetRegistration.cabinet_name))
async def process_cabinet_name(message: Message, bot: aiogram.Bot, state: FSMContext, last_message: LastMessage,
                               user: User):
    catch_cab = None
    cabinet_name = message.text
    if len(cabinet_name) > 50:
        last_message, message_type = await messages. \
            CabinetNameTooLong(bot, last_message, message.chat.id)()
        return last_message, message_type
    for cabinet in user.wb_user_cabinets:
        if cabinet.name == cabinet_name:
            catch_cab: WBUserCabinet = cabinet
            break
    if catch_cab:
        await state.clear()
        last_message, message_type = await messages. \
            CabinetExistsForUser(bot, last_message, message.chat.id)()
        await asyncio.sleep(1)
        await redis_manager.set_last_message(last_message, message_type)

        wb_cabinet_original_id = catch_cab.id
        last_message, message_type = await app.telegram_bot.user_interface \
            .views.to_shop(bot, last_message, wb_cabinet_original_id, state)
        await redis_manager.set_last_message(last_message, message_type)
        return last_message, message_type

    else:
        await state.update_data(cabinet_name=message.text)
        await state.set_state(states.CabinetRegistration.api)
        last_message, message_type = await messages.ShopApiGet(bot, last_message,
                                                               chat_id=message.chat.id)()
        return last_message, message_type


@router.message(StateFilter(states.CabinetRegistration.api))
async def process_cabinet_api( message: Message, bot: aiogram.Bot, state: FSMContext, last_message: LastMessage,
                               user: User):
    try:
         await bot.delete_message(message.chat.id, message.message_id)
    except:
        pass
    last_message, message_type = await messages.ShopUpdateInfo(bot,
                                                               last_message,
                                                               message.chat.id)()
    await redis_manager.set_last_message(last_message, message_type)
    last_message = await redis_manager.get_last_message(message.chat.id)
    api = message.text
    api = api.strip()

    wb_token = wb_models.WBToken(api_key=api)
    fake_user:User = User()
    fake_user.wb_tokens.append(wb_token)
    fake_wb_user_cabinet = WBUserCabinet(name=(await state.get_data())['cabinet_name'])
    fake_wb_user_cabinet.user = fake_user
    try:
         check_right = await CabinetManager.check_token_for_adv(fake_wb_user_cabinet)
    except NotValidTokenError:
        last_message, message_type = await messages. \
            NotValideToken(bot, last_message, message.chat.id)()
        return last_message, message_type
    except ApiForbiddenError:
        last_message, message_type = await messages. \
            GetApiForrbidenError(bot, last_message, message.chat.id)()
        return last_message, message_type
    if not check_right:
        last_message, message_type = await messages. \
            GetApiForrbidenError(bot, last_message, message.chat.id)()
        return last_message, message_type
    else:
        """API введено, права проверены"""
        data_state: dict = await state.get_data()
        cabinet_name = data_state['cabinet_name'].strip()
        shop_id = wb_token.shop_id
        if user.wb_user_cabinets:
            shop_ids = [wb_user_cabinet.wb_cabinet.shop_id \
                        for wb_user_cabinet in user.wb_user_cabinets]
        else:
            shop_ids = []
        if shop_ids and shop_id in shop_ids:
            last_message, message_type = await messages. \
                CabinetExistsForUser(bot, last_message, message.chat.id)()
            await asyncio.sleep(1)
            await redis_manager.set_last_message(last_message, message_type)
            """
            Если кабинет существует, то отправляем самоколбек на него
            """
            await state.clear()
            last_message = await app.telegram_bot.user_interface\
                .views.to_shop(bot, last_message, shop_id, state)
            await redis_manager.set_last_message(last_message, message_type)
            return last_message, message_type
        else:
            async with sm() as session:
                wb_user_cabinet = WBUserCabinet()
                wb_user_cabinet.name = cabinet_name
                stmt = select(wb_models.WBCabinet)\
                    .where(wb_models.WBCabinet.shop_id == shop_id)
                result = await session.execute(stmt)
                wb_cabinet = result.scalars().first()
                if not wb_cabinet:
                    wb_cabinet = wb_models.WBCabinet()
                    wb_cabinet.shop_id = shop_id
                else:
                    last_message, message_type = await messages. \
                        CabinetExistsInSystem(bot, last_message, message.chat.id)()
                wb_user_cabinet.wb_cabinet = wb_cabinet
                user.wb_user_cabinets.append(wb_user_cabinet)
                user.wb_tokens.append(wb_token)
                session.add(user)
                await session.commit()
                await session.refresh(user)
                cabinet_manager = CabinetManager(wb_user_cabinet)
                await cabinet_manager.update_all_data()
                last_message, message_type = await messages. \
                    ShopAddedSuccess(bot, last_message, message.chat.id, cabinet_name)()
                await state.clear()
                await redis_manager.set_last_message(last_message, message_type)
                all_shops:list[WBUserCabinet] = [cabinet for cabinet in user.wb_user_cabinets]
                last_message, message_type = await messages. \
                    ShopChoice(bot, last_message, all_shops)()
                return last_message, message_type


@router.callback_query(callbacks.DeleteWbUserCabinet.filter())
async def delete_shop(callback_query: types.CallbackQuery,
                      callback_data : callbacks.DeleteWbUserCabinet,
                      bot: aiogram.Bot,
                      state: FSMContext, last_message: LastMessage,
                      user: User):
    await callback_query.answer('Удаление магазина (кабинета)')
    wb_cabinet_original_id = callback_data.wb_cabinet_original_id
    async with sm() as session:
        stmt = select(WBUserCabinet).where(WBUserCabinet.wb_cabinet_id == wb_cabinet_original_id)
        result = await session.execute(stmt)
        wb_user_cabinet = result.scalars().first()
        session.delete(wb_user_cabinet)
        await session.commit()
        await session.refresh(user)
    all_shops = user.wb_user_cabinets
    last_message, message_type = await messages. \
        ShopChoice(bot, last_message, all_shops)()
    return last_message, message_type



@router.callback_query(callbacks.AddNewToken.filter())
async def add_app_token(callback_query: types.CallbackQuery,
                  callback_data: callbacks.AddNewToken,
                  bot: aiogram.Bot, state: FSMContext, last_message: LastMessage):
    await callback_query.answer('Добавление нового токена')
    logger.debug('Текущее состояние: %s', await state.get_state())
    wb_user_cabinet_original_id = callback_data.wb_user_cabinet_original_id
    async with sm() as session:
        stmt = select(WBUserCabinet).where(WBUserCabinet.id == wb_user_cabinet_original_id)
        result = await session.execute(stmt)
        wb_user_cabinet = result.scalars().first()
    await state.update_data(wb_user_cabinet_original_id=wb_user_cabinet_original_id)
    await state.set_state(states.AddNewToken.token)
    last_message, message_type = await messages. \
        AddNewTokenGet(bot, last_message, callback_query.message.chat.id, wb_user_cabinet)()
    return last_message, message_type


@router.message(StateFilter(states.AddNewToken.token))
async def process_app_token(message: Message, bot: aiogram.Bot, state: FSMContext, last_message: LastMessage,
                            user: User):
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
    try:
         check_right = await CabinetManager.check_token_for_adv(wb_user_cabinet)
    except NotValidTokenError:
        last_message, message_type = await messages. \
            NotValideToken(bot, last_message, message.chat.id)()
        return last_message, message_type
    if not check_right:
        last_message, message_type = await messages. \
            GetApiForrbidenError(bot, last_message, message.chat.id)()
        return last_message, message_type
    else:
        async with sm() as session:
            session.add(user)
            await session.commit()
            await session.refresh(user)
        last_message, message_type = await messages. \
            ShopAddedSuccess(bot, last_message, message.chat.id, wb_user_cabinet.name)()
        all_shops = wb_user_cabinet.user.wb_user_cabinets
        last_message, message_type = await messages. \
            ShopChoice(bot, last_message, all_shops)()
        await state.clear()
        return last_message, message_type


@router.callback_query(callbacks.Shop.filter(aiogram.F.action == callbacks.Action.select))
async def select_shop(callback_query: types.CallbackQuery,
                      callback_data: callbacks.Shop,
                      bot: aiogram.Bot, state: FSMContext, last_message: LastMessage):
    await callback_query.answer('Выбор магазина (кабинета)')
    wb_user_cabinet_original_id = callback_data.wb_user_cabinet_original_id
    last_message, message_type = await app.telegram_bot.user_interface.views\
        .to_shop(bot, last_message, wb_user_cabinet_original_id, state)
    return last_message, message_type