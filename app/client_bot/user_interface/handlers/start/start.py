import asyncio
import logging
from collections.abc import Sequence
from typing import cast

import aiogram
from aiogram import Router, types
from aiogram.filters import CommandStart, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from aiohttp import ClientSession
from sqlalchemy import Result, Select
from sqlalchemy.future import select
from sqlalchemy.orm import joinedload, load_only
from sqlalchemy.exc import IntegrityError

from app.client_bot import const
from app.client_bot.admin_access import is_bot_admin, use_minimal_presentation_ui
from app.client_bot.utils import create_user
from app.client_bot.redis_manager import RedisManager
from app.client_bot.user_interface import states
from app.client_bot.user_interface.handlers.shop_choice_message import (
    MainMenu,
    ShopsListPage,
    ShopChoice,
)
from app.client_bot.user_interface.handlers.start_registration_func import (
    start_registration,
)
from app.client_bot.user_interface.views import callbacks, messages
from app.client_bot.user_interface.views.gate import get_gate_keyboard, get_gate_message_text
from app.client_bot.user_interface.views.callbacks import Action
from app.core.wb_api.exceptions import ApiForbiddenError
from app.modules.common_slaves.wildberries import (
    models as wb_models,
    super_cabinet_manager,
)
from app.modules.common_slaves.wildberries.models import (
    AdvSetting,
    WBToken,
    WBUserCabinet,
)
from app.modules.common_slaves.wildberries.models.wb_cabinet import WBCabinet
from app.modules.common_slaves.wildberries.shops_data_updater import ShopDataUpdater
from app.modules.common_slaves.wildberries.super_cabinet_manager import WBCabinetAccess
from app.modules.token_monitoring.services import get_shop_ids_with_complete_token_status
from app.modules.shop_menu.message import (
    ShopMenu,
    build_shop_main_keyboard,
    build_shop_mass_adv_ops_keyboard,
)
from app.modules.shop_runner.modules.wb_api import WBApi
from app.modules.token_permissions import TokenPermissionsValidator
from app.settings import settings
from app.utils.db.models import User
from app.utils.db.session_maker import get_async_session_maker
from app.modules.token_monitoring.services.cabinet_status_service import (
    activate_cabinet,
    deactivate_cabinet_atomic_with_user_trackers,
)
from app.modules.token_monitoring.services.notification_manager import (
    NotificationManager,
)
from app.modules.token_monitoring.models import (
    CABINET_DEACTIVATED_NOTIFICATION_TYPE,
    NotificationType,
)

logger = logging.getLogger(__name__)

sm = get_async_session_maker

router = Router()

redis_manager = RedisManager()

DUPLICATE_TOKEN_MESSAGE = "Этот токен уже есть в системе."


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
        user: User | None = result.unique().scalar_one_or_none()
        if callback.message is None:
            return
        chat_id = callback.message.chat.id
        if user is None:
            user = await create_user(
                session,
                user_id,
                username=callback.from_user.username if callback.from_user else None,
                adv_updater_user_chat_id=chat_id,
            )

        minimal = use_minimal_presentation_ui(user_id, user.passed_gate)
        if minimal:
            await MainMenu(bot, chat_id, full_client_ui=False)()
            return

        if (
            settings.invite_gate
            and not user.passed_gate
            and not is_bot_admin(user_id)
        ):
            _= await bot.send_message(
                chat_id,
                get_gate_message_text(),
                reply_markup=get_gate_keyboard(),
            )
            return
        await MainMenu(bot, chat_id, full_client_ui=True)()
    return


@router.callback_query(callbacks.ShowShopsList.filter())
async def show_shops_list(
    callback: CallbackQuery, bot: aiogram.Bot, state: FSMContext
) -> None:
    """Показать страницу «Мои магазины»: Добавить магазин + список магазинов."""
    await state.clear()
    if callback.message is None:
        return
    chat_id = callback.message.chat.id
    user_id = callback.from_user.id
    async with sm() as session:
        stmt = (
            select(User)
            .options(
                joinedload(User.wb_user_cabinets).joinedload(WBUserCabinet.wb_cabinet)
            )
            .where(User.user_telegram_id == user_id)
        )
        result = await session.execute(stmt)
        user: User | None = result.unique().scalar()
        if user is None or (settings.invite_gate and not user.passed_gate):
            pass
        else:
            wb_user_cabinets = user.wb_user_cabinets
            shop_ids = [uc.wb_cabinet.shop_id for uc in wb_user_cabinets]
            shop_ids_with_active_tokens = await get_shop_ids_with_complete_token_status(
                shop_ids
            )
            await ShopsListPage(
                bot, chat_id, wb_user_cabinets, shop_ids_with_active_tokens
            )()
            return
    if (user is None or not user.passed_gate) and settings.invite_gate:
        _ = await bot.send_message(
            chat_id,
            get_gate_message_text(),
            reply_markup=get_gate_keyboard(),
        )
    return


@router.callback_query(callbacks.ShopsListPaginator.filter())
async def shops_list_paginator(
    callback: CallbackQuery,
    callback_data: callbacks.ShopsListPaginator,
    bot: aiogram.Bot,
    state: FSMContext,
) -> None:
    """Переключение страницы списка «Мои магазины»."""
    await state.clear()
    if callback.message is None:
        return
    chat_id = callback.message.chat.id
    user_id = callback.from_user.id
    page = callback_data.page if callback_data.page >= 1 else 1
    async with sm() as session:
        stmt = (
            select(User)
            .options(
                joinedload(User.wb_user_cabinets).joinedload(WBUserCabinet.wb_cabinet)
            )
            .where(User.user_telegram_id == user_id)
        )
        result = await session.execute(stmt)
        user: User = result.unique().scalar()
        if not user.passed_gate and settings.invite_gate:
            _ = await bot.send_message(
                chat_id,
                get_gate_message_text(),
                reply_markup=get_gate_keyboard(),
            )
            return
        wb_user_cabinets = user.wb_user_cabinets
        shop_ids = [uc.wb_cabinet.shop_id for uc in wb_user_cabinets]
        shop_ids_with_active_tokens = await get_shop_ids_with_complete_token_status(
            shop_ids
        )
        await ShopsListPage(
            bot, chat_id, wb_user_cabinets, shop_ids_with_active_tokens, page=page
        )()


@router.callback_query(callbacks.ShopNew.filter())
async def add_shop(
    callback_query: types.CallbackQuery, bot: aiogram.Bot, state: FSMContext
) -> None:
    if callback_query.message is None:
        return
    _= await bot.send_message(
        callback_query.message.chat.id, "Добавление нового магазина (кабинета)"
    )
    await state.set_state(states.CabinetRegistration.cabinet_name)
    chat_id: int = callback_query.message.chat.id
    await messages.ShopNameGet(bot, chat_id)()


@router.message(StateFilter(states.CabinetRegistration.cabinet_name))
async def process_cabinet_name(message: Message, bot: aiogram.Bot, state: FSMContext):
    catch_cab: WBUserCabinet | None = None # type: ignore
    cabinet_name = message.text
    if cabinet_name is None or not cabinet_name.strip():
        _= await bot.send_message(
            message.chat.id,
            "Имя магазина (кабинета) не может быть пустым, отправьте название еще раз:",
        )
        return
    assert cabinet_name is not None
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
        if not user:
            raise ValueError("User not found")
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
        _= await state.update_data(cabinet_name=cabinet_name)
        await state.set_state(states.CabinetRegistration.api)
        await messages.AddNewTokenGet(bot, chat_id, cabinet_name)()


@router.message(StateFilter(states.CabinetRegistration.api))
async def process_cabinet_api(
    message: Message, bot: aiogram.Bot, state: FSMContext, client_session: ClientSession
) -> None:
    """
    Юзер вводит токен, который проверяется на валидность.
    Если токен не валиден, то юзеру отправляется сообщение об этом.
    Если токен валиден, то проверяется есть ли он у другого юзера
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
        return  None
    if "/start" in text:
        await start_registration(message, bot, state)
        return None

    user_telegram_id = message.from_user.id
    chat_id = message.chat.id

    # Предварительная простая валидация формата токена: отсекаем явно мусорные строки
    token_text = text.strip()
    if len(token_text) < 24:  # эвристика: валидные токены заметно длиннее
        _= await bot.send_message(
            chat_id,
            "Токен слишком короткий или имеет неверный формат. Отправьте корректный токен.",
        )
        return None

    # Validate token using centralized validator
    validator = TokenPermissionsValidator(http_session=client_session)
    validation_result = await validator.validate(text, mode="claims_plus_api")

    if not validation_result.is_valid_jwt:
        logger.info("Invalid token (JWT decode failed) for user %s", user_telegram_id)
        _= await bot.send_message(chat_id, "Токен не валиден, попробуйте еще раз:")
        return None

    if not validation_result.is_personal:
        logger.info("Token is not personal for user %s", user_telegram_id)
        _ = await bot.send_message(
            chat_id,
            "Этот токен не персональный. Нужен персональный токен WB.",
        )
        await state.set_state(states.CabinetRegistration.api)
        return None

    if validation_result.is_read_only:
        logger.info("Token is read-only for user %s", user_telegram_id)
        _= await bot.send_message(
            chat_id,
            "Этот токен предназначен только для чтения и не может быть использован для добавления. Пожалуйста, предоставьте токен с полными правами.",
        )
        await state.set_state(states.CabinetRegistration.api)
        return None

    if validation_result.is_expired:
        logger.info("Token is expired for user %s", user_telegram_id)
        _= await bot.send_message(
            chat_id,
            "Токен истёк. Пожалуйста, создайте новый токен в личном кабинете Wildberries.",
        )
        await state.set_state(states.CabinetRegistration.api)
        return None

    if not validation_result.can_be_used:
        missing_str = ", ".join(sorted(validation_result.missing_required))
        logger.info(
            "Token missing required permissions for user %s: %s",
            user_telegram_id,
            missing_str,
        )
        _= await bot.send_message(
            chat_id,
            f"Токен не имеет необходимых прав: {missing_str}.\n\n"
            "Создайте токен с правами: Контент, Статистика, Аналитика, Продвижение.",
        )
        await state.set_state(states.CabinetRegistration.api)
        return None

    shop_id = validation_result.shop_id
    if not shop_id:
        logger.warning("Valid token but no shop_id for user %s", user_telegram_id)
        _= await bot.send_message(
            chat_id,
            "Не удалось получить идентификатор магазина из токена. Попробуйте еще раз.",
        )
        return None
    async with sm() as session:
        # TODO: Тут попала ошибка в код с проверкой существования токена.
        # Получаем ID пользователя
        stmt_for_select_user_id: Select[tuple[int]] = select(User.id).where(
            User.user_telegram_id == user_telegram_id
        )
        result: Result[tuple[int]] = await session.execute(stmt_for_select_user_id)
        user_id: int = result.scalar() # type: ignore

    # Create WBToken object for database storage
    wb_token = wb_models.WBToken(api_key=text)
    wb_token.shop_id = shop_id
    wb_token.user_id = user_id
    access = WBCabinetAccess(tokens=[wb_token], wb_user_cabinet=None, wb_cabinet=None)
    chat_id = message.chat.id
    await messages.ShopUpdateInfo(bot, chat_id)()

    data_state = await state.get_data()
    cabinet_name = data_state["cabinet_name"].strip()

    async with sm() as session:
        # Проверка, что токен не используется другим пользователем
        stmt_for_wb_token = (
            select(WBToken)
            .options(load_only(WBToken.user_id))
            .where(
                WBToken.api_key == wb_token.api_key,
                WBToken.shop_id == wb_token.shop_id,
            )
        )
        result: Result[tuple[WBToken]] = await session.execute(stmt_for_wb_token)
        existing_token = result.scalar()
        if existing_token:
            # If token already exists, check ownership.
            existing_user_id = getattr(existing_token, "user_id", None)

            # Normalize simple numeric/string ids
            try:
                normalized_existing_user_id = (
                    int(existing_user_id) if existing_user_id is not None else None
                )
            except Exception:
                normalized_existing_user_id = existing_user_id

            if normalized_existing_user_id == user_id:
                # Token already saved for the same user — nothing to change.
                _= await bot.send_message(chat_id, "Этот токен уже есть в системе.")
                await state.clear()
                return None
            else:
                # Token belongs to another user — users must have unique tokens.
                _= await bot.send_message(
                    chat_id, "Ошибка: этот токен используется другим пользователем."
                )
                return None
        session.add(wb_token)
        await session.flush()
        await session.commit()
        # Проверка существования кабинета по shop_id
        stmt_for_cabinet = select(WBCabinet).where(
            WBCabinet.shop_id == wb_token.shop_id
        )
        result: Result[tuple[WBCabinet]] = await session.execute(stmt_for_cabinet)
        wb_cabinet: WBCabinet = result.scalar()
        if wb_cabinet:
            await messages.CabinetExistsForUser(bot, chat_id)()
            if wb_cabinet.active is not True:
                wb_cabinet.active = True
            stmt_for_select_user_id: Select[tuple[WBUserCabinet]] = select(WBUserCabinet).where(
                WBUserCabinet.wb_cabinet_id == wb_cabinet.id,
                WBUserCabinet.user_id == user_id,
            )
            result: Result[tuple[WBUserCabinet]] = await session.execute(stmt_for_select_user_id)
            wb_user_cabinet: WBUserCabinet | None = result.scalar_one_or_none()
            stmt_for_adv_setting = select(AdvSetting).where(
                AdvSetting.wb_cabinet_id == wb_cabinet.id
            )
            result: Result[tuple[AdvSetting]] = await session.execute(stmt_for_adv_setting)
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
            await session.commit()
            await messages.AdvCompanyChoicing(
                bot, chat_id, int(wb_user_cabinet_original_id), adv_settings, state # noqa
            )()
            return None
        else:
            # Если нет вб - кабинета, то Создаем новый кабинет и привязку к пользователю
            wb_cabinet: WBCabinet = WBCabinet()
            wb_cabinet.shop_id = shop_id
            wb_cabinet.active = True
            wb_cabinet.default_max_cpm = settings.DEFAULT_MAX_CPM
            session.add(wb_cabinet)
            await session.flush()  # получаем wb_cabinet.id
            wb_user_cabinet = WBUserCabinet()
            wb_user_cabinet.name = cabinet_name
            wb_user_cabinet.wb_cabinet_id = wb_cabinet.id
            wb_user_cabinet.user_id = user_id
            session.add(wb_user_cabinet)
            await session.commit()

        await messages.ShopAddedSuccess(bot, chat_id, cabinet_name)()
        access.wb_cabinet = wb_cabinet
        access.wb_user_cabinet = wb_user_cabinet
        # Обновляем данные магазина
        wb_api = WBApi(access, client_session)

        shop_updater = ShopDataUpdater(wb_api)
        _ = await shop_updater.update_advs_data()

        # Показываем список кабинетов пользователя
        stmt_for_wb_user_cabinet = (
            select(WBUserCabinet)
            .options(joinedload(WBUserCabinet.wb_cabinet))
            .join(WBUserCabinet.user)
            .where(User.user_telegram_id == user_telegram_id)
        )
        result_for_wb_user_cabinet = await session.execute(stmt_for_wb_user_cabinet)
        wb_user_cabinets: Sequence[WBUserCabinet] = result_for_wb_user_cabinet.scalars().all()
        shop_ids = [uc.wb_cabinet.shop_id for uc in wb_user_cabinets]
        shop_ids_with_active_tokens = await get_shop_ids_with_complete_token_status(
            shop_ids
        )

        await ShopChoice(
            bot, chat_id, list(wb_user_cabinets), shop_ids_with_active_tokens
        )()
        return None


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
    # Сохраняем имя кабинета, чтобы при ошибке можно было повторно показать форму ввода токена
    await state.update_data(cabinet_name=wb_user_cabinet.name)
    await state.set_state(states.AddNewToken.token)
    # Логируем текущее состояние для диагностики проблем с маршрутизацией
    try:
        current_state = await state.get_state()
    except Exception:
        current_state = None
    logger.debug(
        "AddNewToken callback: set state=%s for user=%s chat=%s",
        current_state,
        callback_query.from_user.id if callback_query.from_user else None,
        (
            callback_query.message.chat.id
            if callback_query.message and callback_query.message.chat
            else None
        ),
    )
    chat_id = callback_query.message.chat.id
    cabinet_name = wb_user_cabinet.name
    await messages.AddNewTokenGet(bot, chat_id, cabinet_name)()


def _normalize_token_user_id(raw_user_id: object) -> int | object | None:
    """Normalize persisted token owner ids for safe equality checks."""
    try:
        return int(raw_user_id) if raw_user_id is not None else None
    except Exception:
        return raw_user_id


def _can_show_shop_for_duplicate_token(
    *,
    existing_token: WBToken,
    current_user_id: int,
    current_user_telegram_id: int,
) -> bool:
    """Allow shop reveal only for the token owner or a bot admin."""
    token_owner_id = _normalize_token_user_id(getattr(existing_token, "user_id", None))
    return token_owner_id == current_user_id or is_bot_admin(current_user_telegram_id)


async def _handle_duplicate_token_for_existing_shop(
    *,
    bot: aiogram.Bot,
    state: FSMContext,
    chat_id: int,
    current_user_id: int,
    current_user_telegram_id: int,
    existing_token: WBToken,
    wb_user_cabinet_original_id: int,
) -> None:
    """Send duplicate-token UX response and show the shop only when access is safe."""
    await bot.send_message(chat_id, DUPLICATE_TOKEN_MESSAGE)
    if not _can_show_shop_for_duplicate_token(
        existing_token=existing_token,
        current_user_id=current_user_id,
        current_user_telegram_id=current_user_telegram_id,
    ):
        return
    await state.clear()
    await ShopMenu(bot, chat_id, state, wb_user_cabinet_original_id)()


@router.message(StateFilter(states.AddNewToken.token))
async def process_add_new_token(
    message: Message, bot: aiogram.Bot, state: FSMContext, client_session: ClientSession
) -> None:
    """
    Обработчик добавления нов��го токена для существующего магазина.

    После успешного добавления токена резолвит все старые уведомления
    для этого магазина (об истечении срока и деактивации).
    """
    text = message.text
    if not text:
        return None

    # Проверка на команду /start для рестарта
    if "/start" in text:
        await start_registration(message, bot, state)
        return None

    user_telegram_id: int = message.from_user.id
    assert user_telegram_id is not None
    chat_id = message.chat.id

    # Предварительная простая валидация формата токена: отсекаем явно мусорные строки
    token_text = text.strip()
    if len(token_text) < 24:
        await bot.send_message(
            chat_id,
            "Токен слишком короткий или имеет неверный формат. Отправьте корректный токен.",
        )
        return None

    # Получение данных из состояния
    data_state = await state.get_data()
    wb_user_cabinet_original_id = data_state.get("wb_user_cabinet_original_id")

    if not wb_user_cabinet_original_id:
        await bot.send_message(
            chat_id, "Ошибка: магазин не найден. Начните процесс заново."
        )
        await state.clear()
        return None

    # Validate token using centralized validator
    validator = TokenPermissionsValidator(http_session=client_session)
    validation_result = await validator.validate(text, mode="claims_plus_api")

    if not validation_result.is_valid_jwt:
        logger.info("Invalid token (JWT decode failed) for user %s", user_telegram_id)
        await bot.send_message(chat_id, "Токен не валиден, попробуйте еще раз:")
        return None

    if not validation_result.is_personal:
        logger.info("Token is not personal for user %s", user_telegram_id)
        await bot.send_message(
            chat_id,
            "Этот токен не персональный. Нужен персональный токен WB.",
        )
        await state.set_state(states.AddNewToken.token)
        return None

    if validation_result.is_read_only:
        logger.info("Token is read-only for user %s", user_telegram_id)
        await bot.send_message(
            chat_id,
            "Этот токен предназначен только для чтения и не может быть использован для добавления. Пожалуйста, предоставьте токен с полными правами.",
        )
        await state.set_state(states.AddNewToken.token)
        return None

    if validation_result.is_expired:
        logger.info("Token is expired for user %s", user_telegram_id)
        await bot.send_message(
            chat_id,
            "Токен истёк. Пожалуйста, создайте новый токен в личном кабинете Wildberries.",
        )
        await state.set_state(states.AddNewToken.token)
        return None

    if not validation_result.can_be_used:
        missing_str = ", ".join(sorted(validation_result.missing_required))
        logger.info(
            "Token missing required permissions for user %s: %s",
            user_telegram_id,
            missing_str,
        )
        await bot.send_message(
            chat_id,
            f"Токен не имеет необходимых прав: {missing_str}.\n\n"
            "Создайте токен с правами: Контент, Статистика, Аналитика, Продвижение.",
        )
        await state.set_state(states.AddNewToken.token)
        return None

    shop_id = validation_result.shop_id
    if not shop_id:
        logger.warning("Valid token but no shop_id for user %s", user_telegram_id)
        await bot.send_message(
            chat_id,
            "Не удалось получить идентификатор магазина из токена. Попробуйте еще раз.",
        )
        return None
    # Получение user_id из БД
    async with sm() as session:
        stmt_for_select_user_id: Select = select(User.id).where(
            User.user_telegram_id == user_telegram_id
        )
        result = await session.execute(stmt_for_select_user_id)
        user_id = result.scalar()

    if not user_id:
        raise ValueError("Пользователь не найден в системе.")

    # Получение WBUserCabinet
    async with sm() as session:
        stmt_for_select_wb_user_cabinet: Select = (
            select(WBUserCabinet)
            .options(joinedload(WBUserCabinet.wb_cabinet))
            .where(WBUserCabinet.id == wb_user_cabinet_original_id)
        )
        result = await session.execute(stmt_for_select_wb_user_cabinet)
        wb_user_cabinet = result.scalar()

    if not wb_user_cabinet:
        raise ValueError("Магазин не найден в системе.")

    # Проверка соответствия shop_id
    if wb_user_cabinet.wb_cabinet.shop_id != shop_id:
        await bot.send_message(
            chat_id, "Ошибка: токен принадлежит другому магазину. Попробуйте еще раз:"
        )
        return None

    # Create WBToken object for database storage
    wb_token = wb_models.WBToken(api_key=text)
    wb_token.shop_id = shop_id
    wb_token.user_id = user_id

    # Проверка дубликата токена и сохранение
    async with sm() as session:
        # TODO: Вместо явного SELECT для проверки существования токена
        # рассмотрите атомарную вставку с перехватом IntegrityError и
        # добавлением UNIQUE(api_key, shop_id) в модель WBToken.
        # Это устранит гонки и лишний SELECT.
        # Проверка существующего токена
        # Для этого надо удалить дубли и добавить UNIQUE(api_key, shop_id) в модель WBToken.
        stmt_check = select(WBToken).where(
            WBToken.api_key == wb_token.api_key, WBToken.shop_id == shop_id
        )
        result = await session.execute(stmt_check)
        existing_token = result.scalar()

        if existing_token:
            await _handle_duplicate_token_for_existing_shop(
                bot=bot,
                state=state,
                chat_id=chat_id,
                current_user_id=user_id,
                current_user_telegram_id=user_telegram_id,
                existing_token=existing_token,
                wb_user_cabinet_original_id=wb_user_cabinet_original_id,
            )
            return None

        # Сохранение токена. Пытаемся атомарно вставить — при гонке может быть
        # IntegrityError (уникальность токена на уровне БД). В этом случае
        # делаем rollback и корректно информируем пользователя.
        session.add(wb_token)
        try:
            await session.commit()
        except IntegrityError:
            await session.rollback()
            # Получаем существующий токен, чтобы понять чей он
            stmt_existing = (
                select(WBToken)
                .options(load_only(WBToken.user_id))
                .where(
                    WBToken.api_key == wb_token.api_key,
                    WBToken.shop_id == wb_token.shop_id,
                )
            )
            result_existing = await session.execute(stmt_existing)
            existing_token = result_existing.scalar()

            if existing_token:
                await _handle_duplicate_token_for_existing_shop(
                    bot=bot,
                    state=state,
                    chat_id=chat_id,
                    current_user_id=user_id,
                    current_user_telegram_id=user_telegram_id,
                    existing_token=existing_token,
                    wb_user_cabinet_original_id=wb_user_cabinet_original_id,
                )
                return None
            # Если по какой-то причине existing_token не найден — сообщаем об общей ошибке
            await bot.send_message(
                chat_id, "Ошибка при добавлении токена. Попробуйте снова."
            )
            return None

        logger.info(
            "Новый токен успешно добавлен для shop_id=%s, user_id=%s",
            shop_id,
            user_id,
        )

    async with sm() as session:
        stmt_activate = select(WBCabinet).where(WBCabinet.shop_id == shop_id)
        result_activate = await session.execute(stmt_activate)
        wb_cabinet = result_activate.scalar()
        if wb_cabinet and wb_cabinet.active is not True:
            wb_cabinet.active = True
            await session.commit()

    # Резолв всех уведомлений для этого магазина
    try:
        notification_manager = NotificationManager()
        total_resolved = 0

        notification_types = [
            NotificationType.TOKEN_EXPIRING_14_DAYS.value,
            NotificationType.TOKEN_EXPIRING_3_DAYS.value,
            NotificationType.TOKEN_EXPIRING_1_DAY.value,
            NotificationType.TOKEN_DEACTIVATED.value,
            CABINET_DEACTIVATED_NOTIFICATION_TYPE,
        ]

        for notif_type in notification_types:
            resolved_count = await notification_manager.mark_notifications_resolved(
                shop_id=shop_id, notification_type=notif_type
            )
            total_resolved += resolved_count

        if total_resolved > 0:
            logger.info(
                "Зарезолвлено %s уведомлений для shop_id=%s после добавления нового токена",
                total_resolved,
                shop_id,
            )
    except Exception as e:
        # Не прерываем процесс, если не удалось зарезолвить уведомления
        logger.error(
            "Ошибка при резолве уведомлений для shop_id=%s: %s",
            shop_id,
            e,
            exc_info=True,
        )

    # Отправка сообщений об успехе
    await bot.send_message(chat_id, "Токен проверяется...")

    await bot.send_message(
        chat_id, f"Токен успешно добавлен для магазина {wb_user_cabinet.name}!"
    )

    # Очистка состояния
    await state.clear()

    # Переход в меню магазина
    await ShopMenu(bot, chat_id, state, wb_user_cabinet_original_id)()
    return None


@router.callback_query(callbacks.ToggleCabinetActive.filter())
async def toggle_cabinet_active_handler(
    callback: CallbackQuery,
    callback_data: callbacks.ToggleCabinetActive,
    bot: aiogram.Bot,
    state: FSMContext,
) -> None:
    if callback.message is None or callback.from_user is None:
        return None
    chat_id = int(callback.message.chat.id)
    user_telegram_id = callback.from_user.id
    wb_user_cabinet_original_id = callback_data.wb_user_cabinet_original_id

    async with sm(read_only=True) as session:
        stmt = (
            select(WBUserCabinet)
            .join(WBUserCabinet.user)
            .options(joinedload(WBUserCabinet.wb_cabinet))
            .where(
                WBUserCabinet.id == wb_user_cabinet_original_id,
                User.user_telegram_id == user_telegram_id,
            )
        )
        result = await session.execute(stmt)
        wb_user_cabinet = result.unique().scalar_one_or_none()

    if wb_user_cabinet is None:
        await bot.send_message(chat_id, "Магазин не найден или нет доступа.")
        return None

    shop_id = str(wb_user_cabinet.wb_cabinet.shop_id)
    if wb_user_cabinet.wb_cabinet.active is True:
        deactivated = await deactivate_cabinet_atomic_with_user_trackers(
            shop_id,
            notification_type=CABINET_DEACTIVATED_NOTIFICATION_TYPE,
        )
        if not deactivated:
            await bot.send_message(chat_id, "Не удалось деактивировать магазин.")
            return None
    else:
        activated = await activate_cabinet(shop_id)
        if not activated:
            await bot.send_message(chat_id, "Не удалось активировать магазин.")
            return None

    await ShopMenu(bot, chat_id, state, wb_user_cabinet_original_id)()
    return None


@router.callback_query(callbacks.ChoiceAdvPaginator.filter())
async def select_shop(
    callback_query: types.CallbackQuery,
    callback_data: callbacks.ChoiceAdvPaginator,
    bot: aiogram.Bot,
    state: FSMContext,
) -> None:
    # TODO: Тут какая-то ошибка, reset_filter нет в модели callbacks.Shop
    reset_filter = callback_data.reset_filter  # type: ignore[attr-defined]
    if reset_filter:
        await state.update_data(filter_advs=None)
    wb_user_cabinet_original_id = callback_data.wb_user_cabinet_original_id
    page = callback_data.page
    await state.update_data(
        last_wb_user_cabinet_original_id=wb_user_cabinet_original_id
    )
    message = callback_query.message
    assert message.chat is not None
    chat_id = int(message.chat.id)
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
        adv_settings: list[AdvSetting] | None = result.scalars().all()
    if not adv_settings:
        adv_settings = []

    await messages.AdvCompanyChoicing(
        bot,
        chat_id,
        wb_user_cabinet_original_id,
        adv_settings,
        state,
        page=page,
    )()
    return


@router.callback_query(callbacks.Shop.filter(aiogram.F.action == Action.select)) # noqa
async def shop_menu_process(
    callback: types.CallbackQuery,
    callback_data: callbacks.Shop,
    bot: aiogram.Bot,
    state: FSMContext,
) -> None:
    await state.update_data(
        last_wb_user_cabinet_original_id=callback_data.wb_user_cabinet_original_id
    )
    logger.debug("Текущее состояние: %s", await state.get_data())
    wb_user_cabinet_original_id = callback_data.wb_user_cabinet_original_id
    await ShopMenu(
        bot, int(callback.message.chat.id), state, wb_user_cabinet_original_id
    )()
    pass


async def _get_wb_user_cabinet_for_shop_menu(
    wb_user_cabinet_original_id: int,
) -> WBUserCabinet | None:
    async with sm(read_only=True) as session:
        stmt = (
            select(WBUserCabinet)
            .options(joinedload(WBUserCabinet.wb_cabinet))
            .where(WBUserCabinet.id == wb_user_cabinet_original_id)
        )
        result = await session.execute(stmt)
        return result.scalar_one_or_none()


@router.callback_query(callbacks.ShopMassAdvOpsMenu.filter())
async def open_shop_mass_adv_ops_menu(
    callback: types.CallbackQuery,
    callback_data: callbacks.ShopMassAdvOpsMenu,
) -> None:
    if callback.message is None:
        return
    message = cast(types.Message, callback.message)

    wb_user_cabinet = await _get_wb_user_cabinet_for_shop_menu(
        callback_data.wb_user_cabinet_original_id
    )
    if wb_user_cabinet is None:
        return

    _ = await message.edit_reply_markup(
        reply_markup=build_shop_mass_adv_ops_keyboard(
            wb_user_cabinet,
            wb_user_cabinet.wb_cabinet,
        )
    )


@router.callback_query(callbacks.ShopMassAdvOpsBack.filter())
async def close_shop_mass_adv_ops_menu(
    callback: types.CallbackQuery,
    callback_data: callbacks.ShopMassAdvOpsBack,
) -> None:
    if callback.message is None:
        return
    message = cast(types.Message, callback.message)

    wb_user_cabinet = await _get_wb_user_cabinet_for_shop_menu(
        callback_data.wb_user_cabinet_original_id
    )
    if wb_user_cabinet is None:
        return

    _ = await message.edit_reply_markup(
        reply_markup=build_shop_main_keyboard(
            wb_user_cabinet,
            wb_user_cabinet.wb_cabinet,
        )
    )


@router.callback_query(callbacks.UpdateCompanyFromWB.filter())
async def update_company_from_wb(
    callback_query: types.CallbackQuery,
    bot: aiogram.Bot,
    callback_data: callbacks.UpdateCompanyFromWB,
    state: FSMContext,
    client_session: ClientSession,
) -> None:
    await messages.LongTimeOperation(bot, int(callback_query.message.chat.id))()
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
        wb_user_cabinet: WBUserCabinet | None = result.scalar()
    if not wb_user_cabinet:
        raise ValueError("Магазин не найден в системе.")
    wb_cabinet = wb_user_cabinet.wb_cabinet
    access = await super_cabinet_manager.get_access_for_wb_cabinet(wb_cabinet.id)
    wb_api = WBApi(access, client_session)
    shop_updater = ShopDataUpdater(wb_api)
    chat_id = int(callback_query.message.chat.id)
    timeout_min = settings.SHOP_UPDATE_TIMEOUT_MINUTES
    timeout_sec = timeout_min * 60
    try:
        await bot.send_message(
            chat_id, "Начинаю обновление РК, процесс может занять длительное время."
        )
        try:
            await asyncio.wait_for(shop_updater.update_advs_data(), timeout=timeout_sec)
        except ApiForbiddenError:
            await bot.send_message(
                chat_id,
                "Нет прав для доступа в РК, обновите токен,"
                " в случае проблем обратитесь в поддержку -> ",
            )
            return
        except TimeoutError:
            await bot.send_message(
                chat_id,
                f"Тайм-аут обновления кампаний, обрат��тесь в поддержку: {const.SUPPORT_LINK}",
            )
            return

        await bot.send_message(
            chat_id,
            "Загрузка кампаний завершена."
            " Начинаю обновление карточек,"
            " процесс может занять длительное время.",
        )
        try:
            await asyncio.wait_for(
                shop_updater.update_cards_data(), timeout=timeout_sec
            )
        except ApiForbiddenError:
            await bot.send_message(
                chat_id,
                "Нет прав для доступа в РК,"
                " обновите токен,"
                " в случае проблем обратитесь в поддержку -> ",
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
    except Exception as exc:
        logger.error("Ошибка: %s при обновлении данных", exc, exc_info=True)
        await bot.send_message(
            chat_id,
            f"Ошибка при обновлении данных, обратитесь в поддержку {const.SUPPORT_LINK}",
        )
        exc.__traceback__ = None
        del exc

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
    if not adv_settings:
        adv_settings = []
    await messages.AdvCompanyChoicing(
        bot,
        int(callback_query.message.chat.id),
        wb_user_cabinet_original_id,
        adv_settings,
        state,
    )()


router.callback_query.register(callback_start_registration, callbacks.Start.filter())
router.message.register(start_registration, CommandStart())
