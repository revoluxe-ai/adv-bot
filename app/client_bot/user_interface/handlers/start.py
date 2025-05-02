import asyncio
import logging
from operator import and_
from typing import Union

import aiogram
from aiogram import Router, types
from aiogram.filters import StateFilter, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery
from sqlalchemy import Select
from sqlalchemy.future import select
from sqlalchemy.orm import joinedload

from app.client_bot import const
from app.core.wb_api.exceptions import ApiForbiddenError
from app.core.wb_api.exceptions import NotValidTokenError
from app.modules.common_slaves.wildberries import (
    models as wb_models,
    super_cabinet_manager,
)
from app.modules.common_slaves.wildberries.models import WBCabinet
from app.modules.common_slaves.wildberries.models import (
    WBUserCabinet,
    WBToken,
    AdvSetting,
)
from app.modules.common_slaves.wildberries.shops_data_updater import ShopDataUpdater
from app.modules.common_slaves.wildberries.super_cabinet_manager import WBCabinetAccess
from app.modules.shop_menu.message import ShopMenu
from app.utils.db.models import User
from app.utils.db.session_maker import get_async_session_maker
from .shop_choice_message import ShopChoice
from .start_registration_func import start_registration
from .. import states
from ..views import callbacks, messages
from ..views.callbacks import Action
from ...redis_manager import RedisManager

logger = logging.getLogger(__name__)

sm = get_async_session_maker

router = Router()

redis_manager = RedisManager()


async def callback_start_registration(
    callback: CallbackQuery, bot: aiogram.Bot, state: FSMContext
) -> None:
    await state.clear()
    async with sm() as session:
        user_id = callback.from_user.id

        stmt = (
            select(User)
            .options(
                joinedload(User.wb_user_cabinets).joinedload(WBUserCabinet.wb_cabinet)
            )
            .where(User.user_telegram_id == user_id)
        )
        result = await session.execute(stmt)
        user: User = result.scalar()

        wb_user_cabinets = user.wb_user_cabinets
        chat_id = callback.message.chat.id
        await ShopChoice(bot, chat_id, wb_user_cabinets)()
    return


@router.callback_query(callbacks.ShopNew.filter())
async def add_shop(
    callback_query: types.CallbackQuery, bot: aiogram.Bot, state: FSMContext
):
    await bot.send_message(
        callback_query.message.chat.id, "Добавление нового магазина (кабинета)"
    )
    await state.set_state(states.CabinetRegistration.cabinet_name)
    chat_id: int = callback_query.message.chat.id
    await messages.ShopNameGet(bot, chat_id)()


@router.message(StateFilter(states.CabinetRegistration.cabinet_name))
async def process_cabinet_name(message: Message, bot: aiogram.Bot, state: FSMContext):
    catch_cab: Union[WBUserCabinet, None] = None
    cabinet_name = message.text
    chat_id = message.chat.id
    if len(cabinet_name) > 50:
        await messages.CabinetNameTooLong(bot, chat_id)()
        return
    async with sm() as session:
        stmt = (
            select(User)
            .options(
                joinedload(User.wb_user_cabinets).joinedload(WBUserCabinet.wb_cabinet)
            )
            .where(User.user_telegram_id == message.from_user.id)
        )
        result = await session.execute(stmt)
        user = result.scalar()
    for cabinet in user.wb_user_cabinets:
        if cabinet.name == cabinet_name:
            catch_cab: WBUserCabinet = cabinet
            break
    if catch_cab:
        await state.set_state()
        await state.set_state(states.CabinetRegistration.cabinet_name)
        await messages.CabinetNameExists(bot, chat_id)()

    else:
        cabinet_name = message.text
        await state.update_data(cabinet_name=cabinet_name)
        await state.set_state(states.CabinetRegistration.api)
        await messages.AddNewTokenGet(bot, chat_id, cabinet_name)()


@router.message(StateFilter(states.CabinetRegistration.api))
async def process_cabinet_api(message: Message, bot: aiogram.Bot, state: FSMContext):
    """
    Юзер вводит токен, который проверяется на валидность.
    Если токен не валиден, то юзеру отправляется сообщение об этом.
    Если токен валиден, то проверяется естть ли он у другого юзера
    Если токен есть у другого юзера, то юзеру отправляется сообщение об этом. return
    Если нет, то проверяется есть ли у пользователя WBUSerCabinet с таким же shop_id, как у токена
    Если есть, то юзеру отправляется сообщение об этом и предлагается выбрать рекламную кампанию
    Если нет, то проверяется есть ли в системе WBCabinet с таким же shop_id, как у токена
    Если нет, то создается новый WBCabinet и WBUSerCabinet
    Если есть, то создается новый WBUSerCabinet


    @param message: Message
    @param bot: Bot
    @param state: FSMContext
    @return: None
    """
    text = message.text
    if not text:
        return
    if "/start" in text:
        await start_registration(message, bot, state)
        return

    user_telegram_id = message.from_user.id
    wb_token = wb_models.WBToken(api_key=text)
    try:
        shop_id = wb_token.get_shop_id_from_token()
    except NotValidTokenError:
        await bot.send_message(
            message.chat.id, "Токен не валиден, попробуйте еще раз: "
        )
        return

    wb_token.shop_id = shop_id
    access = WBCabinetAccess(tokens=[wb_token], wb_user_cabinet=None, wb_cabinet=None)
    chat_id = message.chat.id
    await messages.ShopUpdateInfo(bot, chat_id)()

    data_state = await state.get_data()
    cabinet_name = data_state["cabinet_name"].strip()

    async with sm() as session:
        # Получаем ID пользователя
        stmt_for_select_user_id: Select = select(User.id).where(
            User.user_telegram_id == user_telegram_id
        )
        result = await session.execute(stmt_for_select_user_id)
        user_id = result.scalar()
        if user_id is None:
            await bot.send_message(chat_id, "Ошибка: пользователь не найден.")
            return

        # Проверка, что токен не используется другим пользователем
        stmt_for_wb_token = select(WBToken).where(
            WBToken.api_key == wb_token.api_key,
            WBToken.user_id != user_id,
        )
        result = await session.execute(stmt_for_wb_token)
        existing_token = result.scalar()
        if existing_token:
            await bot.send_message(
                chat_id, "Этот токен уже используется другим пользователем."
            )
            return

        # Проверка существования кабинета по shop_id
        stmt_for_cabinet = select(WBCabinet).where(
            WBCabinet.shop_id == wb_token.shop_id
        )
        result = await session.execute(stmt_for_cabinet)
        wb_cabinet: WBCabinet | None = result.scalar()

        if wb_cabinet:
            await messages.CabinetExistsForUser(bot, chat_id)()
            stmt_for_select_user_id = select(WBUserCabinet).where(
                and_(
                    WBUserCabinet.wb_cabinet_id == wb_cabinet.id,
                    WBUserCabinet.user_id == user_id,
                )
            )
            result = await session.execute(stmt_for_select_user_id)
            wb_user_cabinet: WBUserCabinet | None = result.scalar_one_or_none()
            stmt_for_adv_setting = select(AdvSetting).where(
                AdvSetting.wb_cabinet_id == wb_cabinet.id
            )
            result = await session.execute(stmt_for_adv_setting)
            adv_settings = result.scalars().all()
            if not wb_user_cabinet:
                wb_user_cabinet = WBUserCabinet(
                    name=cabinet_name, user_id=user_id, wb_cabinet=wb_cabinet
                )
                session.add(wb_user_cabinet)
                await session.flush()
                await session.commit()
            wb_user_cabinet_original_id = wb_user_cabinet.id
            adv_settings = list(adv_settings)
            await messages.AdvCompanyChoicing(
                bot, chat_id, wb_user_cabinet_original_id, adv_settings, state
            )()
            return
        else:
            # Если нет вб - кабинета, то Создаем новый кабинет и привязку к пользователю
            wb_cabinet: WBCabinet = WBCabinet()
            wb_cabinet.shop_id = shop_id
            wb_cabinet.balance = 0
            wb_cabinet.bonus = 0
            session.add(wb_cabinet)
            await session.flush()  # получаем wb_cabinet.id
            wb_user_cabinet = WBUserCabinet()
            wb_user_cabinet.name = cabinet_name
            wb_user_cabinet.wb_cabinet_id = wb_cabinet.id
            wb_user_cabinet.user_id = user_id
            session.add(wb_user_cabinet)
            await session.flush()
            wb_token.user_id = user_id
            await session.commit()
            await session.refresh(wb_user_cabinet)

        await messages.ShopAddedSuccess(bot, chat_id, cabinet_name)()
        access.wb_cabinet = wb_cabinet
        access.wb_user_cabinet = wb_user_cabinet
        # Обновляем данные
        shop_updater = ShopDataUpdater(access)
        await shop_updater.update_advs_data()

        # Показываем список кабинетов пользователя
        async with sm() as session:
            stmt_for_wb_user_cabinet = (
                select(WBUserCabinet)
                .join(WBUserCabinet.user)
                .where(User.user_telegram_id == user_telegram_id)
            )
            result = await session.execute(stmt_for_wb_user_cabinet)
            wb_user_cabinets: list[WBUserCabinet] = result.scalars().all()

        await ShopChoice(bot, chat_id, wb_user_cabinets)()


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
async def add_app_token(
    callback_query: types.CallbackQuery,
    callback_data: callbacks.AddNewToken,
    bot: aiogram.Bot,
    state: FSMContext,
):
    logger.debug("Текущее состояние: %s", await state.get_state())
    wb_user_cabinet_original_id = callback_data.wb_user_cabinet_original_id
    async with sm() as session:
        stmt = select(WBUserCabinet).where(
            WBUserCabinet.id == wb_user_cabinet_original_id
        )
        result = await session.execute(stmt)
        wb_user_cabinet = result.scalars().first()
    await state.update_data(wb_user_cabinet_original_id=wb_user_cabinet_original_id)
    await state.set_state(states.AddNewToken.token)
    chat_id = callback_query.message.chat.id
    cabinet_name = wb_user_cabinet.name
    await messages.AddNewTokenGet(bot, chat_id, cabinet_name)()


#
# @router.message(StateFilter(states.AddNewToken.token))
# async def process_app_token(message: Message, bot: aiogram.Bot, state: FSMContext):
#     wb_user_cabinet_original_id: int = (await state.get_data())['wb_user_cabinet_original_id']
#     message: Message = message
#     if not message:
#         return
#     if '/start' in message.text:
#         await start_registration(message, bot, state)
#         return
#
#     api = message.text
#     api = api.strip()
#     wb_token = wb_models.WBToken(api_key=api)
#     user.wb_tokens.append(wb_token)
#     chat_id = message.chat.id
#     async with sm(read_only=False) as session:
#         user.wb_tokens.append(wb_token)
#         session.add(user)
#         await session.commit()
#         await session.refresh(user)
#     await messages. \
#         ShopAddedSuccess(bot, chat_id, wb_user_cabinet.name)()
#     all_shops = wb_user_cabinet.user.wb_user_cabinets
#     await ShopChoice(bot, chat_id, all_shops)()
#     await state.set_state()
#     return


@router.callback_query(callbacks.ChoiceAdvPaginator.filter())
async def select_shop(
    callback_query: types.CallbackQuery,
    callback_data: callbacks.Shop,
    bot: aiogram.Bot,
    state: FSMContext,
):
    reset_filter = callback_data.reset_filter
    if reset_filter:
        await state.update_data(filter_advs=None)
    wb_user_cabinet_original_id = callback_data.wb_user_cabinet_original_id
    await state.update_data(
        last_wb_user_cabinet_original_id=wb_user_cabinet_original_id
    )
    message = callback_query.message

    chat_id = message.chat.id
    # await state.update_data(chat_id = chat_id)
    # Получаем список рекламных кампаний
    async with sm() as session:
        stmt = (
            select(AdvSetting)
            .join(AdvSetting.wb_cabinet)
            .join(WBCabinet.wb_user_cabinets)
            .where(WBUserCabinet.id == wb_user_cabinet_original_id)
            .order_by(AdvSetting.name)
        )
        result = await session.execute(stmt)
        adv_settings = result.scalars().all()

    await messages.AdvCompanyChoicing(
        bot, chat_id, wb_user_cabinet_original_id, adv_settings, state
    )()
    return


@router.callback_query(callbacks.Shop.filter(aiogram.F.action == Action.select))
async def shop_menu_process(
    callback: types.CallbackQuery,
    callback_data: callbacks.Shop,
    bot: aiogram.Bot,
    state: FSMContext,
):
    await state.update_data(
        last_wb_user_cabinet_original_id=callback_data.wb_user_cabinet_original_id
    )
    logger.debug("Текущее состояние: %s", await state.get_data())
    wb_user_cabinet_original_id = callback_data.wb_user_cabinet_original_id
    await ShopMenu(bot, callback.message.chat.id, state, wb_user_cabinet_original_id)()
    pass


@router.callback_query(callbacks.UpdateCompanyFromWB.filter())
async def update_company_from_wb(
    callback_query: types.CallbackQuery,
    bot: aiogram.Bot,
    callback_data: callbacks.UpdateCompanyFromWB,
    state: FSMContext,
):
    await messages.LongTimeOperation(bot, callback_query.message.chat.id)()
    wb_user_cabinet_original_id = callback_data.wb_user_cabinet_original_id
    async with sm() as session:
        stmt = (
            select(WBUserCabinet)
            .options(
                joinedload(WBUserCabinet.user).joinedload(User.wb_tokens),
                joinedload(WBUserCabinet.wb_cabinet),
            )
            .where(WBUserCabinet.id == wb_user_cabinet_original_id)
        )
        result = await session.execute(stmt)
        wb_user_cabinet: WBUserCabinet = result.scalar()
    wb_cabinet = wb_user_cabinet.wb_cabinet
    access = await super_cabinet_manager.get_access_for_wb_cabinet(wb_cabinet.id)
    shop_updater = ShopDataUpdater(access)
    chat_id = callback_query.message.chat.id
    try:
        await bot.send_message(
            chat_id, "Начинаю обновление РК, процесс может занять длительное время."
        )
        try:
            await asyncio.wait_for(shop_updater.update_advs_data(), timeout=10 * 60)
        except ApiForbiddenError:
            await bot.send_message(
                chat_id,
                f"Нет прав для доступа в РК, обновите токен,"
                f" в случае проблем обратитесь в поддержку -> ",
            )
            return
        except TimeoutError:
            await bot.send_message(
                chat_id,
                f"Тайм-аут обновления кампаний,"
                f" обратитесь в поддержку: {const.SUPPORT_LINK}",
            )
            return

        await bot.send_message(
            chat_id,
            "Загрузка кампаний завершена."
            " Начинаю обновление карточек,"
            " процесс может занять длительное время.",
        )
        try:
            await asyncio.wait_for(shop_updater.update_cards_data(), timeout=10 * 60)
        except ApiForbiddenError:
            await bot.send_message(
                chat_id,
                f"Нет прав для доступа в РК,"
                f" обновите токен,"
                f" в случае проблем обратитесь в поддержку -> ",
            )
            return
        except TimeoutError:
            await bot.send_message(
                chat_id,
                f"Тайм-аут обновления кампаний, обратитесь в поддержку: {const.SUPPORT_LINK}",
            )
            return
        except Exception:
            logger.error("Ошибка обновления карточек", exc_info=True)
            pass
        await bot.send_message(chat_id, "Загрузка карточек завершена завершена")
    except:
        await bot.send_message(
            chat_id,
            f"Ошибка при обновлении данных, обратитесь в поддержку {const.SUPPORT_LINK}",
        )

    # Получаем список рекламных кампаний
    async with sm() as session:
        stmt = (
            select(AdvSetting)
            .join(AdvSetting.wb_cabinet)
            .join(WBCabinet.wb_user_cabinets)
            .where(WBUserCabinet.id == wb_user_cabinet_original_id)
            .order_by(AdvSetting.name)
        )
        result = await session.execute(stmt)
        adv_settings = result.scalars().all()

    await messages.AdvCompanyChoicing(
        bot,
        callback_query.message.chat.id,
        wb_user_cabinet_original_id,
        adv_settings,
        state,
    )()


router.callback_query.register(callback_start_registration, callbacks.Start.filter())
router.message.register(start_registration, CommandStart())
