"""Хендлеры start / shop menu: регистрация, выбор магазина, mass-ops.

``_get_wb_user_cabinet_for_shop_menu`` eager-load'ит ``user`` вместе с
``wb_cabinet``, чтобы restore главной клавиатуры после mass-ops не
упирался в lazy-load вне DB-сессии.
"""

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
from sqlalchemy import Select
from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload, load_only
from sqlalchemy.exc import IntegrityError

from app.client_bot import const
from app.client_bot.admin_access import is_bot_admin, use_minimal_presentation_ui
from app.client_bot.ui_access import UiAccessMode
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
from app.client_bot.user_interface.utils import format_required_wb_token_scopes
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


def _build_token_invalid_format_message() -> str:
    """Вернуть подсказку при невалидном формате WB-токена."""
    return (
        "Токен не принят. Проверьте, что токен скопирован полностью и не содержит "
        "лишних пробелов.\n\n"
        "Если нужен безопасный первый вход, создайте токен только для чтения в кабинете WB."
    )


def _build_token_read_only_rejected_message() -> str:
    """Вернуть подсказку, когда в add-token flow пришёл read-only токен."""
    return (
        "Обнаружен токен только для чтения. Такой токен подходит для просмотра аналитики, "
        "магазинов и кампаний.\n"
        "Бот не будет менять рекламу с таким токеном.\n"
        "Для управления ставками нужен токен с возможностью изменений в кабинете.\n"
        f"{format_required_wb_token_scopes()}"
    )


def _build_token_read_only_added_message() -> str:
    """Вернуть уведомление после сохранения read-only токена."""
    return (
        'ВНИМАНИЕ! Добавлен токен с правами "Только для чтения".\n\n'
        "Этот токен только для чтения подходит для просмотра аналитики, магазинов и кампаний.\n"
        "Бот не будет менять рекламу с таким токеном.\n"
        "Для управления ставками нужен токен с возможностью изменений в кабинете.\n"
        f"{format_required_wb_token_scopes()}"
    )


def _build_token_success_added_message(shop_name: str) -> str:
    """Вернуть сообщение об успешном добавлении WB-токена."""
    return (
        f"Токен успешно добавлен для магазина {shop_name}.\n\n"
        "Теперь откройте «Мои магазины», выберите магазин и рекламную кампанию."
    )


async def __get_wb_user_cabinet(
    *,
    session: AsyncSession,
    user_id: int,
    shop_id: str):
    stmt = (
        select(WBUserCabinet)
        .join(WBUserCabinet.wb_cabinet)
        .where(
            WBUserCabinet.user_id == user_id,
            WBCabinet.shop_id == shop_id,
        )
    )
    result_ = await session.execute(stmt)
    wb_user_cabinet_ = result_.scalar_one()
    return wb_user_cabinet_



async def _open_existing_user_cabinet_by_shop_id(
    *,
    bot: aiogram.Bot,
    chat_id: int,
    state: FSMContext,
    user_id: int,
    shop_id: str,
) -> bool:
    """Open an existing user cabinet by shop_id when it is already linked to the user."""
    async with sm(read_only=True) as session:
        wb_user_cabinet = await __get_wb_user_cabinet(
            session=session, user_id=user_id, shop_id=shop_id
        )

    await state.update_data(last_wb_user_cabinet_original_id=wb_user_cabinet.id)
    await ShopMenu(bot, chat_id, state, wb_user_cabinet.id)()
    return True


sm = get_async_session_maker

router = Router()

redis_manager = RedisManager()


async def _load_user_with_wb_cabinets_in_session(
    session: AsyncSession, user_telegram_id: int
) -> User | None:
    """Загрузить пользователя вместе с WB-кабинетами."""
    stmt: Select[tuple[User]] = (
        select(User)
        .options(
            joinedload(User.wb_user_cabinets).joinedload(WBUserCabinet.wb_cabinet)
        )
        .where(User.user_telegram_id == user_telegram_id)
    )
    result = await session.execute(stmt)
    return result.unique().scalar_one_or_none()



async def _load_user_id_in_session(
    session: AsyncSession, user_telegram_id: int
) -> int | None:
    """Получить PK пользователя по Telegram ID."""
    stmt: Select[tuple[int]] = select(User.id).where(User.user_telegram_id == user_telegram_id)
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def _load_existing_wb_token_in_session(
    session: AsyncSession, api_key: str, shop_id: str
) -> WBToken | None:
    """Загрузить существующий токен по ключу и shop_id."""
    stmt: Select[tuple[WBToken]] = (
        select(WBToken)
        .options(load_only(WBToken.user_id))
        .where(WBToken.api_key == api_key, WBToken.shop_id == shop_id)
    )
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def _load_wb_user_cabinet_in_session(
    session: AsyncSession, wb_user_cabinet_original_id: int
) -> WBUserCabinet | None:
    """Загрузить WBUserCabinet вместе с WBCabinet."""
    stmt: Select[tuple[WBUserCabinet]] = (
        select(WBUserCabinet)
        .options(joinedload(WBUserCabinet.wb_cabinet))
        .where(WBUserCabinet.id == wb_user_cabinet_original_id)
    )
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def _load_wb_user_cabinet_for_owner_in_session(
    session: AsyncSession,
    wb_user_cabinet_original_id: int,
    user_telegram_id: int,
) -> WBUserCabinet | None:
    """Загрузить кабинет пользователя с проверкой владельца."""
    stmt: Select[tuple[WBUserCabinet]] = (
        select(WBUserCabinet)
        .join(WBUserCabinet.user)
        .options(joinedload(WBUserCabinet.wb_cabinet))
        .where(
            WBUserCabinet.id == wb_user_cabinet_original_id,
            User.user_telegram_id == user_telegram_id,
        )
    )
    result = await session.execute(stmt)
    return result.unique().scalar_one_or_none()


async def _load_wb_user_cabinet_for_menu_in_session(
    session: AsyncSession, wb_user_cabinet_original_id: int
) -> WBUserCabinet | None:
    """Загрузить кабинет и связанные user / tokens / adv_settings для меню."""
    stmt: Select[tuple[WBUserCabinet]] = (
        select(WBUserCabinet)
        .options(
            joinedload(WBUserCabinet.user).joinedload(User.wb_tokens),
            joinedload(WBUserCabinet.wb_cabinet).joinedload(WBCabinet.adv_settings),
        )
        .where(WBUserCabinet.id == wb_user_cabinet_original_id)
    )
    result = await session.execute(stmt)
    return result.unique().scalar_one_or_none()


async def _load_wb_cabinet_by_shop_id_in_session(
    session: AsyncSession, shop_id: str
) -> WBCabinet | None:
    """Загрузить WBCabinet по shop_id."""
    stmt: Select[tuple[WBCabinet]] = select(WBCabinet).where(WBCabinet.shop_id == shop_id)
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def _load_user_cabinet_for_user_in_session(
    session: AsyncSession,
    wb_cabinet_id: int,
    user_id: int,
) -> WBUserCabinet | None:
    """Загрузить кабинет пользователя по pair (wb_cabinet_id, user_id)."""
    stmt: Select[tuple[WBUserCabinet]] = select(WBUserCabinet).where(
        WBUserCabinet.wb_cabinet_id == wb_cabinet_id,
        WBUserCabinet.user_id == user_id,
    )
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def _load_user_cabinets_for_user_in_session(
    session: AsyncSession, user_telegram_id: int
) -> Sequence[WBUserCabinet]:
    """Загрузить все кабинеты пользователя вместе с WBCabinet."""
    stmt: Select[tuple[WBUserCabinet]] = (
        select(WBUserCabinet)
        .options(joinedload(WBUserCabinet.wb_cabinet))
        .join(WBUserCabinet.user)
        .where(User.user_telegram_id == user_telegram_id)
    )
    result = await session.execute(stmt)
    return result.scalars().all()


async def persist_wb_token_in_session(
    session: AsyncSession, wb_token: WBToken
) -> None:
    """Persist a new ``WBToken`` (caller already verified uniqueness).

    WRITE child: parent opens ``sm(read_only=False)`` and passes session here.
    """
    session.add(wb_token)
    await session.flush()
    await session.commit()


async def ensure_wb_user_cabinet_binding_in_session(
    session: AsyncSession,
    *,
    wb_cabinet: WBCabinet,
    user_id: int,
    cabinet_name: str,
) -> WBUserCabinet:
    """Return existing user↔cabinet binding or create and commit a new one.

    WRITE child for ``process_cabinet_api`` when shop already exists.
    """
    wb_user_cabinet = await _load_user_cabinet_for_user_in_session(
        session, wb_cabinet.id, user_id
    )
    if wb_user_cabinet is not None:
        return wb_user_cabinet
    wb_user_cabinet = WBUserCabinet(
        name=cabinet_name, user_id=user_id, wb_cabinet=wb_cabinet
    )
    session.add(wb_user_cabinet)
    await session.flush()
    await session.commit()
    return wb_user_cabinet


async def create_wb_cabinet_and_user_binding_in_session(
    session: AsyncSession,
    *,
    shop_id: str,
    user_id: int,
    cabinet_name: str,
) -> tuple[WBCabinet, WBUserCabinet]:
    """Create ``WBCabinet`` + ``WBUserCabinet`` binding and commit.

    WRITE child for ``process_cabinet_api`` when shop is new.
    """
    new_wb_cabinet = WBCabinet()
    new_wb_cabinet.shop_id = shop_id
    new_wb_cabinet.active = True
    new_wb_cabinet.default_max_cpm = settings.DEFAULT_MAX_CPM
    session.add(new_wb_cabinet)
    await session.flush()
    wb_user_cabinet = WBUserCabinet()
    wb_user_cabinet.name = cabinet_name
    wb_user_cabinet.wb_cabinet_id = new_wb_cabinet.id
    wb_user_cabinet.user_id = user_id
    session.add(wb_user_cabinet)
    await session.commit()
    return new_wb_cabinet, wb_user_cabinet


async def commit_new_wb_token_in_session(
    session: AsyncSession, wb_token: WBToken
) -> None:
    """Insert ``WBToken`` and commit (IntegrityError handled by caller).

    WRITE child for ``process_add_new_token``.
    """
    session.add(wb_token)
    await session.commit()


async def _load_adv_settings_for_wb_user_cabinet_in_session(
    session: AsyncSession, wb_user_cabinet_original_id: int
) -> list[AdvSetting]:
    """Загрузить рекламные кампании кабинета."""
    stmt: Select[tuple[AdvSetting]] = (
        select(AdvSetting)
        .join(AdvSetting.wb_cabinet)
        .join(WBCabinet.wb_user_cabinets)
        .where(WBUserCabinet.id == wb_user_cabinet_original_id)
        .order_by(AdvSetting.name)
    )
    result = await session.execute(stmt)
    return list(result.scalars().all())


async def callback_start_registration(
    callback: CallbackQuery, bot: aiogram.Bot, state: FSMContext
) -> None:
    """Вернуть в меню существующего User (menu-return); без ``create_user``.

    PURE_READ: ``sm(read_only=True)``. Creation User остаётся на message
    ``/start`` / write middleware. Missing User → gate при ``invite_gate``,
    иначе early return без MainMenu.
    """

    logger.debug(
        "callback_start_registration: enter user=%s data=%r message_chat=%s",
        callback.from_user.id,
        callback.data,
        callback.message.chat.id if callback.message is not None else None,
    )

    await state.clear()
    async with sm(read_only=True) as session:
        user_id = callback.from_user.id
        user = await _load_user_with_wb_cabinets_in_session(session, user_id)

        logger.debug(
            "callback_start_registration: user loaded user=%s exists=%s passed_gate=%s",
            user_id,
            user is not None,
            user.passed_gate if user is not None else None,
        )
        if callback.message is None:
            logger.debug("callback_start_registration: no callback.message user=%s", user_id)
            return
        chat_id = callback.message.chat.id
        if user is None:
            logger.debug(
                "callback_start_registration: missing user non-write user=%s invite_gate=%s",
                user_id,
                settings.invite_gate,
            )
            if settings.invite_gate:
                _ = await bot.send_message(
                    chat_id,
                    get_gate_message_text(),
                    reply_markup=get_gate_keyboard(),
                )
            return

        minimal = use_minimal_presentation_ui(user_id, user.passed_gate)
        logger.debug(
            "callback_start_registration: decision user=%s minimal=%s passed_gate=%s invite_gate=%s",
            user_id,
            minimal,
            user.passed_gate,
            settings.invite_gate,
        )
        if minimal:
            logger.debug("callback_start_registration: sending minimal MainMenu user=%s", user_id)
            await MainMenu(bot, chat_id, full_client_ui=False)()
            return

        if (
            settings.invite_gate
            and not user.passed_gate
            and not is_bot_admin(user_id)
        ):
            logger.debug("callback_start_registration: sending gate screen user=%s", user_id)
            await state.set_state(states.GateInvite.waiting_code)
            _ = await bot.send_message(
                chat_id,
                get_gate_message_text(),
                reply_markup=get_gate_keyboard(),
            )
            return
        logger.debug("callback_start_registration: sending full MainMenu user=%s", user_id)
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
    async with sm(read_only=True) as session:
        user = await _load_user_with_wb_cabinets_in_session(session, user_id)
        if user is None:
            if settings.invite_gate:
                _ = await bot.send_message(
                    chat_id,
                    get_gate_message_text(),
                    reply_markup=get_gate_keyboard(),
                )
            return
        if settings.invite_gate and not user.passed_gate:
            _ = await bot.send_message(
                chat_id,
                get_gate_message_text(),
                reply_markup=get_gate_keyboard(),
            )
            return
        wb_user_cabinets = user.wb_user_cabinets
        shop_ids: list[str] = []
        for user_cabinet in wb_user_cabinets:
            wb_cabinet = user_cabinet.wb_cabinet
            shop_ids.append(wb_cabinet.shop_id)
        shop_ids_with_active_tokens = await get_shop_ids_with_complete_token_status(
            shop_ids
        )
        await ShopsListPage(
            bot, chat_id, wb_user_cabinets, shop_ids_with_active_tokens
        )()
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
    async with sm(read_only=True) as session:
        user = await _load_user_with_wb_cabinets_in_session(session, user_id)
        if user is None:
            return
        if not user.passed_gate and settings.invite_gate:
            _ = await bot.send_message(
                chat_id,
                get_gate_message_text(),
                reply_markup=get_gate_keyboard(),
            )
            return
        wb_user_cabinets = user.wb_user_cabinets
        shop_ids: list[str] = []
        for user_cabinet in wb_user_cabinets:
            wb_cabinet = user_cabinet.wb_cabinet
            shop_ids.append(wb_cabinet.shop_id)
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
async def process_cabinet_name(
    message: Message, bot: aiogram.Bot, state: FSMContext
) -> None:
    """Обработать ввод имени магазина и перейти к вводу токена."""
    matched_cabinet: WBUserCabinet | None = None
    cabinet_name = message.text
    if cabinet_name is None or not cabinet_name.strip():
        _= await bot.send_message(
            message.chat.id,
            "Имя магазина (кабинета) не может быть пустым, отправьте название еще раз:",
        )
        return
    cabinet_name = cabinet_name.strip()
    chat_id = message.chat.id
    if len(cabinet_name) > 50:
        await messages.CabinetNameTooLong(bot, chat_id)()
        return
    from_user = message.from_user
    if from_user is None:
        return
    async with sm(read_only=True) as session:
        user = await _load_user_with_wb_cabinets_in_session(session, from_user.id)
        if user is None:
            raise ValueError("User not found")
    for cabinet in user.wb_user_cabinets:
        if cabinet.name == cabinet_name:
            matched_cabinet = cabinet
            break
    if matched_cabinet is not None:
        await state.set_state()
        await state.set_state(states.CabinetRegistration.cabinet_name)
        await messages.CabinetNameExists(bot, chat_id)()

    else:
        _= await state.update_data(cabinet_name=cabinet_name)
        await state.set_state(states.CabinetRegistration.api)
        await messages.AddNewTokenGet(bot, chat_id, cabinet_name)()


@router.message(StateFilter(states.CabinetRegistration.api))
async def process_cabinet_api(
    message: Message, bot: aiogram.Bot, state: FSMContext, client_session: ClientSession
) -> None:
    """
    Юзер вводит токен, который проверяется на валидность.

    Parent WRITE seam: ``sm(read_only=False)`` →
    :func:`persist_wb_token_in_session` /
    :func:`ensure_wb_user_cabinet_binding_in_session` /
    :func:`create_wb_cabinet_and_user_binding_in_session`.

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
    from_user = message.from_user
    if from_user is None:
        return None
    if "/start" in text:
        await start_registration(message, bot, state)
        return None

    user_telegram_id = from_user.id
    chat_id = message.chat.id

    # Предварительная простая валидация формата токена: отсекаем явно мусорные строки
    token_text = text.strip() # есть очистка токен от лишних пробелов
    if len(token_text) < 24:  # эвристика: валидные токены заметно длиннее
        _= await bot.send_message(
            chat_id,
            _build_token_invalid_format_message(),
        )
        return None

    # Validate token using centralized validator
    validator = TokenPermissionsValidator(http_session=client_session)
    validation_result = await validator.validate(text, mode="claims_plus_api")
    if validation_result is None:
        return None

    if not validation_result.is_valid_jwt:
        logger.info("Invalid token (JWT decode failed) for user %s", user_telegram_id)
        _= await bot.send_message(chat_id, _build_token_invalid_format_message())
        return None

    if not validation_result.is_personal:
        logger.info("Token is not personal for user %s", user_telegram_id)
        _ = await bot.send_message(
            chat_id,
            "Этот токен не персональный. Нужен персональный токен WB.",
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

    if not validation_result.can_be_used_for_free:
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
    async with sm(read_only=False) as session:
        user_id = await _load_user_id_in_session(session, user_telegram_id)
        if user_id is None:
            raise ValueError("User not found")

    # Create WBToken object for database storage
    wb_token = wb_models.WBToken(api_key=text)
    wb_token.shop_id = shop_id
    wb_token.user_id = user_id
    access = WBCabinetAccess(tokens=[wb_token], wb_user_cabinet=None, wb_cabinet=None)
    chat_id = message.chat.id
    _ = await messages.ShopUpdateInfo(bot, chat_id)()

    data_state = await state.get_data()
    cabinet_name = str(data_state.get("cabinet_name") or "").strip()

    async with sm(read_only=False) as session:
        # Проверка, что токен не используется другим пользователем
        existing_token = await _load_existing_wb_token_in_session(
            session, wb_token.api_key, shop_id
        )
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
                opened_existing_cabinet = await _open_existing_user_cabinet_by_shop_id(
                    bot=bot,
                    chat_id=chat_id,
                    state=state,
                    user_id=user_id,
                    shop_id=shop_id,
                )
                if not opened_existing_cabinet:
                    logger.warning(
                        "Duplicate token for same user but no linked cabinet found: "
                        "user_id=%s shop_id=%s",
                        user_id,
                        shop_id,
                    )
                return None
            else:
                # Token belongs to another user — users must have unique tokens.
                _= await bot.send_message(
                    chat_id, "Ошибка: этот токен используется другим пользователем."
                )
                return None
        await persist_wb_token_in_session(session, wb_token)
        # Проверка существования кабинета по shop_id
        wb_cabinet = await _load_wb_cabinet_by_shop_id_in_session(session, shop_id)
        current_wb_cabinet: WBCabinet
        if wb_cabinet is not None:
            existing_wb_user_cabinet = await _load_user_cabinet_for_user_in_session(
                session, wb_cabinet.id, user_id
            )
            if existing_wb_user_cabinet is not None:
                _ = await messages.CabinetExistsForUser(bot, chat_id)()
                await state.update_data(
                    last_wb_user_cabinet_original_id=existing_wb_user_cabinet.id
                )
                await ShopMenu(
                    bot, chat_id, state, int(existing_wb_user_cabinet.id)
                )()
                return None
            if wb_cabinet.active is not True:
                wb_cabinet.active = True
            wb_user_cabinet = await ensure_wb_user_cabinet_binding_in_session(
                session,
                wb_cabinet=wb_cabinet,
                user_id=user_id,
                cabinet_name=cabinet_name,
            )
            adv_settings = await _load_adv_settings_for_wb_user_cabinet_in_session(
                session, wb_cabinet.id
            )
            wb_user_cabinet_original_id = wb_user_cabinet.id
            adv_settings = list(adv_settings)
            await session.commit()
            current_wb_cabinet = wb_cabinet
            await messages.AdvCompanyChoicing(
                bot, chat_id, int(wb_user_cabinet_original_id), adv_settings, state # noqa
            )()
            return None
        else:
            # Если нет вб - кабинета, то Создаем новый кабинет и привязку к пользователю
            current_wb_cabinet, wb_user_cabinet = (
                await create_wb_cabinet_and_user_binding_in_session(
                    session,
                    shop_id=shop_id,
                    user_id=user_id,
                    cabinet_name=cabinet_name,
                )
            )

        _ = await messages.ShopAddedSuccess(bot, chat_id, cabinet_name)()
        access.wb_cabinet = current_wb_cabinet
        access.wb_user_cabinet = wb_user_cabinet
        # Обновляем данные магазина
        # Показываем список кабинетов пользователя
        wb_user_cabinets = await _load_user_cabinets_for_user_in_session(
            session, user_telegram_id
        )
        shop_ids: list[str] = []
        for user_cabinet in wb_user_cabinets:
            wb_cabinet = user_cabinet.wb_cabinet
            shop_ids.append(wb_cabinet.shop_id)
        shop_ids_with_active_tokens = await get_shop_ids_with_complete_token_status(
            shop_ids
        )

        if validation_result.is_read_only:
            _ = await bot.send_message(
                chat_id,
                _build_token_read_only_added_message(),
            )
            await asyncio.sleep(3)

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
) -> None:
    """Подготовить состояние к вводу нового токена для кабинета."""
    logger.debug("Текущее состояние: %s", await state.get_state())
    if callback_query.message is None:
        return None
    message = cast(types.Message, callback_query.message)
    wb_user_cabinet_original_id = callback_data.wb_user_cabinet_original_id
    async with sm(read_only=True) as session:
        wb_user_cabinet = await _load_wb_user_cabinet_in_session(
            session, wb_user_cabinet_original_id
        )
    if wb_user_cabinet is None:
        return None
    _ = await state.update_data(wb_user_cabinet_original_id=wb_user_cabinet_original_id)
    # Сохраняем имя кабинета, чтобы при ошибке можно было повторно показать форму ввода токена
    _ = await state.update_data(cabinet_name=wb_user_cabinet.name or "")
    await state.set_state(states.AddNewToken.token)
    # Логируем текущее состояние для диагностики проблем с маршрутизацией
    try:
        current_state = await state.get_state()
    except Exception:
        current_state = None
    logger.debug(
        "AddNewToken callback: set state=%s for user=%s chat=%s",
        current_state,
        callback_query.from_user.id,
        message.chat.id,
    )
    chat_id = message.chat.id
    cabinet_name = wb_user_cabinet.name or ""
    _ = await messages.AddNewTokenGet(bot, chat_id, cabinet_name)()


@router.message(StateFilter(states.AddNewToken.token))
async def process_add_new_token(
    message: Message, bot: aiogram.Bot, state: FSMContext, client_session: ClientSession
) -> None:
    """Обработчик добавления нового токена для существующего магазина.

    Parent WRITE seam: ``sm(read_only=False)`` →
    :func:`commit_new_wb_token_in_session`.

    После успешного добавления токена резолвит все старые уведомления
    для этого магазина (об истечении срока и деактивации).
    """
    text = message.text
    if not text:
        return None
    from_user = message.from_user
    if from_user is None:
        return None

    # Проверка на команду /start для рестарта
    if "/start" in text:
        await start_registration(message, bot, state)
        return None

    user_telegram_id: int = from_user.id
    chat_id = message.chat.id

    # Предварительная простая валидация формата токена: отсекаем явно мусорные строки
    token_text = text.strip()
    if len(token_text) < 24:
        _ = await bot.send_message(
            chat_id,
            _build_token_invalid_format_message(),
        )
        return None

    # Получение данных из состояния
    data_state = await state.get_data()
    wb_user_cabinet_original_id = data_state.get("wb_user_cabinet_original_id")

    if not wb_user_cabinet_original_id:
        _ = await bot.send_message(
            chat_id, "Ошибка: магазин не найден. Начните процесс заново."
        )
        await state.clear()
        return None

    # Validate token using centralized validator
    validator = TokenPermissionsValidator(http_session=client_session)
    validation_result = await validator.validate(text, mode="claims_plus_api")
    if validation_result is None:
        return None

    if not validation_result.is_valid_jwt:
        logger.info("Invalid token (JWT decode failed) for user %s", user_telegram_id)
        _ = await bot.send_message(chat_id, _build_token_invalid_format_message())
        return None

    if not validation_result.is_personal:
        logger.info("Token is not personal for user %s", user_telegram_id)
        _ = await bot.send_message(
            chat_id,
            "Этот токен не персональный. Нужен персональный токен WB.",
        )
        await state.set_state(states.AddNewToken.token)
        return None

    if validation_result.is_read_only:
        logger.info("Token is read-only for user %s", user_telegram_id)
        _ = await bot.send_message(
            chat_id,
            _build_token_read_only_rejected_message(),
        )
        await state.set_state(states.AddNewToken.token)
        return None

    if validation_result.is_expired:
        logger.info("Token is expired for user %s", user_telegram_id)
        _ = await bot.send_message(
            chat_id,
            "Токен истёк. Пожалуйста, создайте новый токен в личном кабинете Wildberries.",
        )
        await state.set_state(states.AddNewToken.token)
        return None

    if not validation_result.can_be_used_for_free:
        missing_str = ", ".join(sorted(validation_result.missing_required))
        logger.info(
            "Token missing required permissions for user %s: %s",
            user_telegram_id,
            missing_str,
        )
        _ = await bot.send_message(
            chat_id,
            f"Токен не имеет необходимых прав: {missing_str}.\n\n"
            "Создайте токен с правами: Контент, Статистика, Аналитика, Продвижение.",
        )
        await state.set_state(states.AddNewToken.token)
        return None

    shop_id = validation_result.shop_id
    if not shop_id:
        logger.warning("Valid token but no shop_id for user %s", user_telegram_id)
        _ = await bot.send_message(
            chat_id,
            "Не удалось получить идентификатор магазина из токена. Попробуйте еще раз.",
        )
        return None
    shop_id = str(shop_id)
    # Получение user_id из БД
    async with sm(read_only=False) as session:
        user_id = await _load_user_id_in_session(session, user_telegram_id)

    if user_id is None:
        raise ValueError("Пользователь не найден в системе.")

    # Получение WBUserCabinet
    async with sm(read_only=False) as session:
        wb_user_cabinet = await _load_wb_user_cabinet_in_session(
            session, wb_user_cabinet_original_id
        )

    if wb_user_cabinet is None:
        raise ValueError("Магазин не найден в системе.")

    # Проверка соответствия shop_id
    if wb_user_cabinet.wb_cabinet.shop_id != shop_id:
        _ = await bot.send_message(
            chat_id, "Ошибка: токен принадлежит другому магазину. Попробуйте еще раз:"
        )
        return None

    # Create WBToken object for database storage
    wb_token = wb_models.WBToken(api_key=text)
    wb_token.shop_id = shop_id
    wb_token.user_id = user_id

    # Проверка дубликата токена и сохранение
    async with sm(read_only=False) as session:
        # TODO: Вместо явного SELECT для проверки существования токена
        # рассмотрите атомарную вставку с перехватом IntegrityError и
        # добавлением UNIQUE(api_key, shop_id) в модель WBToken.
        # Это устранит гонки и лишний SELECT.
        # Проверка существующего токена
        # Для этого надо удалить дубли и добавить UNIQUE(api_key, shop_id) в модель WBToken.
        existing_token = await _load_existing_wb_token_in_session(
            session, wb_token.api_key, shop_id
        )

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
                _ = await bot.send_message(chat_id, "Этот токен уже есть в системе.")
                await state.clear()
                opened_existing_cabinet = await _open_existing_user_cabinet_by_shop_id(
                    bot=bot,
                    chat_id=chat_id,
                    state=state,
                    user_id=user_id,
                    shop_id=shop_id,
                )
                if not opened_existing_cabinet:
                    logger.warning(
                        "Duplicate add-token request for same user but no linked cabinet "
                        "found: user_id=%s shop_id=%s",
                        user_id,
                        shop_id,
                    )
                return None
            else:
                # Token belongs to another user — users must have unique tokens.
                _ = await bot.send_message(
                    chat_id, "Ошибка: этот токен используется другим пользователем."
                )
                return None

        # Сохранение токена. Пытаемся атомарно вставить — при гонке может быть
        # IntegrityError (уникальность токена на уровне БД). В этом случае
        # делаем rollback и корректно информируем пользователя.
        try:
            await commit_new_wb_token_in_session(session, wb_token)
        except IntegrityError:
            await session.rollback()
            # Получаем существующий токен, чтобы понять чей он
            existing_token = await _load_existing_wb_token_in_session(
                session, wb_token.api_key, shop_id
            )

            if existing_token:
                existing_user_id = getattr(existing_token, "user_id", None)
                try:
                    normalized_existing_user_id = (
                        int(existing_user_id) if existing_user_id is not None else None
                    )
                except Exception:
                    normalized_existing_user_id = existing_user_id

                if normalized_existing_user_id == user_id:
                    _ = await bot.send_message(chat_id, "Этот токен уже есть в системе.")
                    await state.clear()
                    opened_existing_cabinet = await _open_existing_user_cabinet_by_shop_id(
                        bot=bot,
                        chat_id=chat_id,
                        state=state,
                        user_id=user_id,
                        shop_id=shop_id,
                    )
                    if not opened_existing_cabinet:
                        logger.warning(
                            "Duplicate add-token IntegrityError for same user but no linked "
                            "cabinet found: user_id=%s shop_id=%s",
                            user_id,
                            shop_id,
                        )
                    return None
                else:
                    _ = await bot.send_message(
                        chat_id, "Ошибка: этот токен используется другим пользователем."
                    )
                    return None
            # Если по какой-то причине existing_token не найден — сообщаем об общей ошибке
            _ = await bot.send_message(
                chat_id, "Ошибка при добавлении токена. Попробуйте снова."
            )
            return None

        logger.info(
            "Новый токен успешно добавлен для shop_id=%s, user_id=%s",
            shop_id,
            user_id,
        )

    async with sm(read_only=False) as session:
        wb_cabinet = await _load_wb_cabinet_by_shop_id_in_session(session, shop_id)
        if wb_cabinet is not None and wb_cabinet.active is not True:
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
    _ = await bot.send_message(chat_id, "Токен проверяется...")

    _ = await bot.send_message(
        chat_id,
        _build_token_success_added_message(wb_user_cabinet.name or ""),
    )

    # Очистка состояния
    await state.clear()

    # Переход в меню магазина
    _ = await ShopMenu(bot, chat_id, state, wb_user_cabinet_original_id)()
    return None


@router.callback_query(callbacks.ToggleCabinetActive.filter())
async def toggle_cabinet_active_handler(
    callback: CallbackQuery,
    callback_data: callbacks.ToggleCabinetActive,
    bot: aiogram.Bot,
    state: FSMContext,
) -> None:
    """Переключить активность кабинета и вернуть меню магазина."""
    if callback.message is None:
        return None
    chat_id = int(callback.message.chat.id)
    user_telegram_id = callback.from_user.id
    wb_user_cabinet_original_id = callback_data.wb_user_cabinet_original_id

    async with sm(read_only=True) as session:
        wb_user_cabinet = await _load_wb_user_cabinet_for_owner_in_session(
            session, wb_user_cabinet_original_id, user_telegram_id
        )

    if wb_user_cabinet is None:
        _ = await bot.send_message(chat_id, "Магазин не найден или нет доступа.")
        return None

    wb_cabinet = wb_user_cabinet.wb_cabinet
    shop_id = str(wb_cabinet.shop_id)
    if wb_cabinet.active is True:
        deactivated = await deactivate_cabinet_atomic_with_user_trackers(
            shop_id,
            notification_type=CABINET_DEACTIVATED_NOTIFICATION_TYPE,
        )
        if not deactivated:
            _ = await bot.send_message(chat_id, "Не удалось деактивировать магазин.")
            return None
    else:
        activated = await activate_cabinet(shop_id)
        if not activated:
            _ = await bot.send_message(chat_id, "Не удалось активировать магазин.")
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
    """Показать список рекламных кампаний для выбранного кабинета."""
    # TODO: Тут какая-то ошибка, reset_filter нет в модели callbacks.Shop
    reset_filter = callback_data.reset_filter  # type: ignore[attr-defined]
    if reset_filter:
        _ = await state.update_data(filter_advs=None)
    wb_user_cabinet_original_id = callback_data.wb_user_cabinet_original_id
    page = callback_data.page
    _ = await state.update_data(
        last_wb_user_cabinet_original_id=wb_user_cabinet_original_id
    )
    if callback_query.message is None:
        return
    message = cast(types.Message, callback_query.message)
    chat_id = int(message.chat.id)
    # Получаем список рекламных кампаний
    async with sm(read_only=True) as session:
        adv_settings = await _load_adv_settings_for_wb_user_cabinet_in_session(
            session, wb_user_cabinet_original_id
        )

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
    """Открыть главное меню магазина из callback-кнопки."""
    _ = await state.update_data(
        last_wb_user_cabinet_original_id=callback_data.wb_user_cabinet_original_id
    )
    logger.debug("Текущее состояние: %s", await state.get_data())
    wb_user_cabinet_original_id = callback_data.wb_user_cabinet_original_id
    if callback.message is None:
        return
    message = cast(types.Message, callback.message)
    _ = await ShopMenu(
        bot, int(message.chat.id), state, wb_user_cabinet_original_id
    )()
    pass


async def _get_wb_user_cabinet_for_shop_menu(
    wb_user_cabinet_original_id: int,
) -> WBUserCabinet | None:
    """Загрузить WBUserCabinet для сборки shop-menu keyboard.

    Вместе с ``wb_cabinet`` eager-load'ит ``user``, чтобы
    ``build_shop_main_keyboard`` / ``close_shop_mass_adv_ops_menu``
    не делали lazy-load ``user`` вне живой DB-сессии.

    Args:
        wb_user_cabinet_original_id: PK ``WBUserCabinet``.

    Returns:
        Кабинет с загруженными ``wb_cabinet`` и ``user``, либо ``None``.
    """
    async with sm(read_only=True) as session:
        return await _load_wb_user_cabinet_for_menu_in_session(
            session, wb_user_cabinet_original_id
        )


def _resolve_shop_keyboard_access(wb_user_cabinet: WBUserCabinet) -> UiAccessMode:
    """Infer free/paid access for restoring the shop keyboard after nested menus."""
    user = getattr(wb_user_cabinet, "user", None)
    telegram_id = getattr(user, "user_telegram_id", None)
    if isinstance(telegram_id, int) and is_bot_admin(telegram_id):
        return UiAccessMode.PAID

    adv_settings = getattr(wb_user_cabinet.wb_cabinet, "adv_settings", [])
    has_paid_adv = any(getattr(adv, "bot_active", False) for adv in adv_settings)
    return UiAccessMode.PAID if has_paid_adv else UiAccessMode.FREE


@router.callback_query(callbacks.ShopMassAdvOpsMenu.filter())
async def open_shop_mass_adv_ops_menu(
    callback: types.CallbackQuery,
    callback_data: callbacks.ShopMassAdvOpsMenu,
) -> None:
    """Показать подменю массовых операций с рекламными кампаниями."""
    if callback.message is None:
        return
    message = cast(types.Message, callback.message)

    wb_user_cabinet = await _get_wb_user_cabinet_for_shop_menu(
        callback_data.wb_user_cabinet_original_id
    )
    if wb_user_cabinet is None:
        return

    wb_cabinet = wb_user_cabinet.wb_cabinet

    _ = await message.edit_reply_markup(
        reply_markup=build_shop_mass_adv_ops_keyboard(
            wb_user_cabinet,
            wb_cabinet,
        )
    )


@router.callback_query(callbacks.ShopMassAdvOpsBack.filter())
async def close_shop_mass_adv_ops_menu(
    callback: types.CallbackQuery,
    callback_data: callbacks.ShopMassAdvOpsBack,
) -> None:
    """Вернуть главную клавиатуру магазина после меню массовых операций.

    Подменю массовых операций доступно только в PAID UI, поэтому restore
    использует ``UiAccessMode.PAID``, чтобы кнопка «Массовые операции с РК»
    снова появилась на главной клавиатуре.
    """
    if callback.message is None:
        return
    message = cast(types.Message, callback.message)

    wb_user_cabinet = await _get_wb_user_cabinet_for_shop_menu(
        callback_data.wb_user_cabinet_original_id
    )
    if wb_user_cabinet is None:
        return

    wb_cabinet = wb_user_cabinet.wb_cabinet

    _ = await message.edit_reply_markup(
        reply_markup=build_shop_main_keyboard(
            wb_user_cabinet,
            wb_cabinet,
            ui_access=_resolve_shop_keyboard_access(wb_user_cabinet),
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
    """Обновить данные кампаний и карточек магазина из WB API."""
    if callback_query.message is None:
        return
    message = cast(types.Message, callback_query.message)
    _ = await messages.LongTimeOperation(bot, int(message.chat.id))()
    wb_user_cabinet_original_id = callback_data.wb_user_cabinet_original_id
    async with sm(read_only=True) as session:
        wb_user_cabinet = await _load_wb_user_cabinet_for_menu_in_session(
            session, wb_user_cabinet_original_id
        )
    if wb_user_cabinet is None:
        raise ValueError("Магазин не найден в системе.")
    wb_cabinet = wb_user_cabinet.wb_cabinet
    access = await super_cabinet_manager.get_access_for_wb_cabinet(wb_cabinet.id)
    if access is None:
        raise ValueError("Не удалось получить доступ к кабинету.")
    wb_api = WBApi(access, client_session)
    shop_updater = ShopDataUpdater(wb_api)
    chat_id = int(message.chat.id)
    timeout_min = settings.SHOP_UPDATE_TIMEOUT_MINUTES
    timeout_sec = timeout_min * 60
    try:
        _ = await bot.send_message(
            chat_id, "Начинаю обновление РК, процесс может занять длительное время."
        )
        try:
            _ = await asyncio.wait_for(
                shop_updater.update_advs_data(), timeout=timeout_sec
            )
        except ApiForbiddenError:
            _ = await bot.send_message(
                chat_id,
                "Нет прав для доступа в РК, обновите токен,"
                " в случае проблем обратитесь в поддержку -> ",
            )
            return
        except TimeoutError:
            _ = await bot.send_message(
                chat_id,
                f"Тайм-аут обновления кампаний, обратитесь в поддержку: {const.SUPPORT_LINK}",
            )
            return

        _ = await bot.send_message(
            chat_id,
            "Загрузка кампаний завершена."
            " Начинаю обновление карточек,"
            " процесс может занять длительное время.",
        )
        try:
            _ = await asyncio.wait_for(
                shop_updater.update_cards_data(), timeout=timeout_sec
            )
        except ApiForbiddenError:
            _ = await bot.send_message(
                chat_id,
                "Нет прав для доступа в РК,"
                " обновите токен,"
                " в случае проблем обратитесь в поддержку -> ",
            )
            return
        except TimeoutError:
            _ = await bot.send_message(
                chat_id,
                f"Тайм-аут обновления кампаний, обратитесь в поддержку: {const.SUPPORT_LINK}",
            )
            return
        except Exception:
            logger.error("Ошибка обновления карточек", exc_info=True)
            pass
        _ = await bot.send_message(chat_id, "Загрузка карточек завершена завершена")
    except Exception as exc:
        logger.error("Ошибка: %s при обновлении данных", exc, exc_info=True)
        _ = await bot.send_message(
            chat_id,
            f"Ошибка при обновлении данных, обратитесь в поддержку {const.SUPPORT_LINK}",
        )
        exc.__traceback__ = None
        del exc

    # Получаем список рекламных кампаний
    async with sm(read_only=True) as session:
        adv_settings = await _load_adv_settings_for_wb_user_cabinet_in_session(
            session, wb_user_cabinet_original_id
        )
    await messages.AdvCompanyChoicing(
        bot,
        int(message.chat.id),
        wb_user_cabinet_original_id,
        adv_settings,
        state,
    )()

_ = router.callback_query.register(callback_start_registration, callbacks.Start.filter())
_ = router.message.register(start_registration, CommandStart())
