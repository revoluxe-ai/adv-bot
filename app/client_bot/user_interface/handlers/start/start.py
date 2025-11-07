import asyncio
import logging

import aiogram
from aiogram import Router, types
from aiogram.filters import CommandStart, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from aiohttp import ClientSession
from sqlalchemy import Select
from sqlalchemy.future import select
from sqlalchemy.orm import joinedload, load_only
from sqlalchemy.exc import IntegrityError

from app.client_bot import const
from app.client_bot.redis_manager import RedisManager
from app.client_bot.user_interface import states
from app.client_bot.user_interface.handlers.shop_choice_message import ShopChoice
from app.client_bot.user_interface.handlers.start_registration_func import (
    start_registration,
)
from app.client_bot.user_interface.views import callbacks, messages
from app.client_bot.user_interface.views.callbacks import Action
from app.core.wb_api.exceptions import ApiForbiddenError, NotValidTokenError
from app.modules.common_slaves.wildberries import (
    models as wb_models,
    super_cabinet_manager,
)
from app.modules.common_slaves.wildberries.models import (
    AdvSetting,
    WBCabinet,
    WBToken,
    WBUserCabinet,
)
from app.modules.common_slaves.wildberries.shops_data_updater import ShopDataUpdater
from app.modules.common_slaves.wildberries.super_cabinet_manager import WBCabinetAccess
from app.modules.shop_menu.message import ShopMenu
from app.modules.shop_runner.modules.wb_api import WBApi
from app.settings import settings
from app.utils.db.models import User
from app.utils.db.session_maker import get_async_session_maker
from app.modules.token_monitoring.services.notification_manager import (
    NotificationManager,
)
from app.modules.token_monitoring.models import NotificationType

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
) -> None:
    await bot.send_message(
        callback_query.message.chat.id, "Добавление нового магазина (кабинета)"
    )
    await state.set_state(states.CabinetRegistration.cabinet_name)
    chat_id: int = callback_query.message.chat.id
    await messages.ShopNameGet(bot, chat_id)()


@router.message(StateFilter(states.CabinetRegistration.cabinet_name))
async def process_cabinet_name(message: Message, bot: aiogram.Bot, state: FSMContext):
    catch_cab: WBUserCabinet | None = None
    cabinet_name = message.text
    if cabinet_name is None or not cabinet_name.strip():
        await bot.send_message(
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
        return True
    if "/start" in text:
        await start_registration(message, bot, state)
        return True

    user_telegram_id = message.from_user.id
    chat_id = message.chat.id

    # Предварительная простая валидация формата токена: отсекаем явно мусорные строки
    token_text = text.strip()
    if len(token_text) < 24:  # эвристика: валидные токены заметно длиннее
        await bot.send_message(
            chat_id,
            "Токен слишком короткий или имеет неверный формат. Отправьте корректный токен.",
        )
        return True

    wb_token = wb_models.WBToken(
        api_key=text,
    )
    if wb_token.read_only:
        logger.info("Token is read-only for user %s", user_telegram_id)
        await bot.send_message(
            chat_id,
            "Этот токен предназначен только для чтения и не может быть использован для добавления. Пожалуйста, предоставьте токен с полными правами.",
        )
        await state.set_state(
            states.CabinetRegistration.api
        )  # Возвращаем пользователя в состояние ввода токена
        return True
    try:
        shop_id = wb_token.get_shop_id_from_token()
    except NotValidTokenError:
        logger.info("Invalid token (NotValidTokenError) for user %s", user_telegram_id)
        await bot.send_message(chat_id, "Токен не валиден, попробуйте еще раз:")
        # Не сбрасываем state — пользователь остаётся в состоянии ввода токена
        logger.info(
            "Sent invalid token message to user %s, keeping state", user_telegram_id
        )
        return True
    except Exception as e:
        # Catch all unexpected exceptions from token parsing to avoid silent failures
        logger.warning(
            "Unexpected error while validating token for user %s in AddNewToken flow: %s",
            user_telegram_id,
            e,
            exc_info=True,
        )
        await bot.send_message(
            chat_id,
            "Токен не валиден или произошла ошибка при его обработке. Попробуйте ввести токен еще раз.",
        )
        # Не сбрасываем state — пользователь остаётся в состоянии ввода
        logger.info(
            "Sent error message to user %s after token parse exception, returning",
            user_telegram_id,
        )
        return True
    async with sm() as session:
        # TODO: Тут попала ошибка в код с проверкой существования токена.
        # Получаем ID пользователя
        stmt_for_select_user_id: Select = select(User.id).where(
            User.user_telegram_id == user_telegram_id
        )
        result = await session.execute(stmt_for_select_user_id)
        user_id = result.scalar()
        if user_id is None:
            await bot.send_message(chat_id, "Ошибка: пользователей не найден.")
            return True

    wb_token.shop_id = shop_id
    wb_token.user_id = user_id
    access = WBCabinetAccess(tokens=[wb_token], wb_user_cabinet=None, wb_cabinet=None)
    chat_id = message.chat.id
    await messages.ShopUpdateInfo(bot, chat_id)()

    data_state = await state.get_data()
    cabinet_name = data_state["cabinet_name"].strip()

    async with sm() as session:
        # Проверка, что токен не используется другим поль��ователем
        stmt_for_wb_token = (
            select(WBToken)
            .options(load_only(WBToken.user_id))
            .where(
                WBToken.api_key == wb_token.api_key,
                WBToken.shop_id == wb_token.shop_id,
            )
        )
        result = await session.execute(stmt_for_wb_token)
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
                await bot.send_message(chat_id, "Этот токен уже есть в системе.")
                await state.clear()
                return True
            else:
                # Token belongs to another user — users must have unique tokens.
                await bot.send_message(
                    chat_id, "Ошибка: этот токен используется другим пользователем."
                )
                return True
        session.add(wb_token)
        await session.flush()
        await session.commit()
        # Проверка существования кабинета по shop_id
        stmt_for_cabinet = select(WBCabinet).where(
            WBCabinet.shop_id == wb_token.shop_id
        )
        result = await session.execute(stmt_for_cabinet)
        wb_cabinet: WBCabinet | None = result.scalar()

        if wb_cabinet:
            await messages.CabinetExistsForUser(bot, chat_id)()
            stmt_for_select_user_id = select(WBUserCabinet).where(
                WBUserCabinet.wb_cabinet_id == wb_cabinet.id,
                WBUserCabinet.user_id == user_id,
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
            await session.commit()
            await messages.AdvCompanyChoicing(
                bot, chat_id, wb_user_cabinet_original_id, adv_settings, state
            )()
            return True
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
            await session.commit()

        await messages.ShopAddedSuccess(bot, chat_id, cabinet_name)()
        access.wb_cabinet = wb_cabinet
        access.wb_user_cabinet = wb_user_cabinet
        # Обновляем данные магазина
        wb_api = WBApi(access, client_session)

        shop_updater = ShopDataUpdater(wb_api)
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
        return True


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


@router.message(StateFilter(states.AddNewToken.token))
async def process_add_new_token(
    message: Message, bot: aiogram.Bot, state: FSMContext
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

    # Создание и валидация токена
    wb_token = wb_models.WBToken(api_key=text)

    if wb_token.read_only:
        logger.info("Token is read-only for user %s", user_telegram_id)
        await bot.send_message(
            chat_id,
            "Этот токен предназначен только для чтения и не может быть использован для добавления. Пожалуйста, предоставьте токен с полными правами.",
        )
        await state.set_state(
            states.AddNewToken.token
        )  # Возвращаем пользователя в состояние ввода токена
        return None

    try:
        shop_id = wb_token.get_shop_id_from_token()
    except NotValidTokenError:
        await bot.send_message(chat_id, "Токен не валиден, попробуйте еще раз:")
        # Не сбрасываем state — пользователь остаётся в состоянии ввода токена
        return None
    except Exception as e:
        # Catch all unexpected exceptions from token parsing to avoid silent failures
        logger.warning(
            "Unexpected error while validating token for user %s in AddNewToken flow: %s",
            user_telegram_id,
            e,
            exc_info=True,
        )
        await bot.send_message(
            chat_id,
            "Токен не валиден или при его проверке произошла ошибка. Попробуйте ещё раз или свяжитесь с поддержкой.",
        )
        # Не сбрасываем state — пользователь остаётся в состоянии ввода
        logger.info(
            "Sent error message to user %s after token parse exception, returning",
            user_telegram_id,
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

    # Установка атрибутов токена
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
                await bot.send_message(chat_id, "Этот токен уже есть в системе.")
                await state.clear()
                return True
            else:
                # Token belongs to another user — users must have unique tokens.
                await bot.send_message(
                    chat_id, "Ошибка: этот токен используется другим пользователем."
                )
                return True

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
                existing_user_id = getattr(existing_token, "user_id", None)
                try:
                    normalized_existing_user_id = (
                        int(existing_user_id) if existing_user_id is not None else None
                    )
                except Exception:
                    normalized_existing_user_id = existing_user_id

                if normalized_existing_user_id == user_id:
                    await bot.send_message(chat_id, "Этот токен уже есть в системе.")
                    await state.clear()
                    return True
                else:
                    await bot.send_message(
                        chat_id, "Ошибка: этот токен используется другим пользователем."
                    )
                    return True
            # Если по какой-то причине existing_token не найден — сообщаем об общей ошибке
            await bot.send_message(
                chat_id, "Ошибка при добавлении токена. Попробуйте снова."
            )
            return True

        logger.info(
            "Новый токен успешно добавлен для shop_id=%s, user_id=%s",
            shop_id,
            user_id,
        )

    # Резолв всех уведомлений для этого магазина
    try:
        notification_manager = NotificationManager()
        total_resolved = 0

        notification_types = [
            NotificationType.TOKEN_EXPIRING_14_DAYS.value,
            NotificationType.TOKEN_EXPIRING_3_DAYS.value,
            NotificationType.TOKEN_EXPIRING_1_DAY.value,
            NotificationType.TOKEN_DEACTIVATED.value,
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
            "Ошибка при резолве уведомлений для shop_id=%s: %s", shop_id, e, exc_info=True
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
    return True


@router.callback_query(callbacks.ChoiceAdvPaginator.filter())
async def select_shop(
    callback_query: types.CallbackQuery,
    callback_data: callbacks.Shop,
    bot: aiogram.Bot,
    state: FSMContext,
) -> None:
    # TODO: Тут какая-то ошибка, reset_filter нет в модели callbacks.Shop
    reset_filter = callback_data.reset_filter  # type: ignore[attr-defined]
    if reset_filter:
        await state.update_data(filter_advs=None)
    wb_user_cabinet_original_id = callback_data.wb_user_cabinet_original_id
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
        bot, chat_id, wb_user_cabinet_original_id, adv_settings, state
    )()
    return


@router.callback_query(callbacks.Shop.filter(aiogram.F.action == Action.select))
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
            "Загрузк�� кампаний завершена."
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
