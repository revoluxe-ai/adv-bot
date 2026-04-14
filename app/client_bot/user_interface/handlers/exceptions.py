import logging
import traceback
import typing

import aiogram
from aiogram import Router
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError
from aiogram.filters.exception import ExceptionTypeFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import Update
from aiogram.types.error_event import ErrorEvent

from app import client_bot as tb
from app.client_bot import const
from app.core.wb_api.exceptions import ApiForbiddenError
from app.exc import CardNotFoundInDB

logger = logging.getLogger(__name__)


def _chat_id_from_error_update(update: Update) -> int:
    """User chat id from message or callback_query (shared error-handler resolution)."""
    message = update.message
    if message is None:
        assert update.callback_query
        assert update.callback_query.message
        assert update.callback_query.message.chat
        return int(update.callback_query.message.chat.id)
    return message.chat.id


async def _clear_fsm_and_get_chat_id(state: FSMContext, update: Update) -> int:
    """Reset FSM state and return the user chat id for this update (error handlers)."""
    await state.set_state()
    return _chat_id_from_error_update(update)


admin_telegram_id = 373435337

user_router = Router()


admin_router = Router()


@admin_router.errors(ExceptionTypeFilter(aiogram.exceptions.TelegramNetworkError))
async def network_error_handler(
    error_event: ErrorEvent, state: FSMContext, bot: aiogram.Bot
) -> None:
    await state.set_state()
    chat_id = _chat_id_from_error_update(error_event.update)
    await bot.send_message(
        chat_id=chat_id,
        text="Ошибка сети Телеграм. Попробуйте еще раз через несколько минут.",
    )


@admin_router.errors(ExceptionTypeFilter(TelegramBadRequest))
async def error_handler_for_telegram_bad_request_exception(
    error_event: ErrorEvent, state: FSMContext, bot: aiogram.Bot
) -> None:
    exc = error_event.exception
    logger.warning(
        "TelegramBadRequest: %s (message=%s)",
        exc,
        getattr(exc, "message", None),
        exc_info=True,
    )
    error_text = (getattr(exc, "message", None) or str(exc) or "").lower()
    update = error_event.update
    chat_id = await _clear_fsm_and_get_chat_id(state, update)
    if "caption is too long" in error_text:
        message = update.message
        if message is None:
            cq = update.callback_query
            assert cq is not None
            user_name = cq.from_user.username
            callback_data = getattr(cq, "data", None)
        else:
            assert message.from_user
            user_name = message.from_user.username
            callback_data = None

        admin_text = (
            "TelegramBadRequest: caption is too long\n"
            f"chat_id={chat_id}\n"
            f"user={user_name}\n"
            f"callback_data={callback_data}\n"
            f"exc={exc}"
        )
        for i in range(0, len(admin_text), const.MAX_MESSAGE_LENGTH):
            await bot.send_message(
                admin_telegram_id,
                admin_text[i : i + const.MAX_MESSAGE_LENGTH],
            )
        await bot.send_message(
            chat_id=chat_id,
            text=(
                "Сообщение получилось слишком длинным и было автоматически сокращено. "
                "Если проблема повторяется, обратитесь в поддержку -> "
                f"{const.SUPPORT_LINK}"
            ),
        )
        return
    await bot.send_message(
        chat_id=chat_id,
        text="Кнопка устарела, нажмите на нее или другую еще раз. В случае регулярного повторения "
        f"проблемы обратитесь в поддержку -> {const.SUPPORT_LINK}",
    )


@admin_router.errors(ExceptionTypeFilter(TelegramForbiddenError))
async def forbidden_error_handler(
    error_event: ErrorEvent, state: FSMContext, bot: aiogram.Bot
):
    logger.error("Юзер заблокировал бота")
    return


@admin_router.errors(ExceptionTypeFilter(ApiForbiddenError))
async def api_forbidden_error_handler(
    error_event: ErrorEvent, state: FSMContext, bot: aiogram.Bot
):
    message = error_event.update.message

    if message is None:
        chat_id = error_event.update.callback_query.message.chat.id
    else:
        chat_id = message.chat.id
    await bot.send_message(
        chat_id=chat_id,
        text="Нет доступов к данному магазину."
        ' Получите или создайте новый токен с правами "Контент",'
        ' "Продвижение" и "Аналитика" (галочку "Только для чтения" не ставить) \n\n'
        "Затем добавьте этот магазин ЕЩЕ РАЗ под НОВЫМ именем и с новым токеном "
        "(новый магазин создан не будет, токен добавиться к старому)",
    )
    return


@admin_router.errors(ExceptionTypeFilter(CardNotFoundInDB))
async def not_found_wb_card_error_handler(
    error_event: ErrorEvent, state: FSMContext, bot: aiogram.Bot
):
    message = error_event.update.message
    exception = error_event.exception
    exception = typing.cast(CardNotFoundInDB, exception)

    if message is None:
        assert error_event.update.callback_query
        chat_id = error_event.update.callback_query.message.chat.id
    else:
        chat_id = message.chat.id
    await bot.send_message(
        chat_id=chat_id,
        text=f"Ошибка получения карточки, обратитесь в поддержку -> {const.SUPPORT_LINK}",
    )
    await bot.send_message(admin_telegram_id, str(exception))
    return


@admin_router.errors(ExceptionTypeFilter(Exception))
async def error_handler(error_event: ErrorEvent, state: FSMContext, bot: aiogram.Bot):
    await state.set_state()
    message = error_event.update.message
    exception = error_event.exception
    if isinstance(exception, KeyboardInterrupt):
        raise exception
    if message is None:
        chat_id = error_event.update.callback_query.message.chat.id
        user_name = error_event.update.callback_query.from_user.username
    else:
        chat_id = message.chat.id
        user_name = message.from_user.username
    await bot.send_message(
        chat_id=chat_id,
        text="Произошла ошибка, но не волнуйтесь! Бот продолжает работать "
        "и по прежнему выполняет свои функции. Проблема только в интерфейсе, а администратор"
        " уже уведомлен о ней. Попробуйте выполнить нужное вам действие еще раз или вернитесь"
        " в главное меню, через команду /start . Связаться с разработчиком вы можете по "
        f"этому контакту: {const.SUPPORT_LINK}",
    )
    trace_error = traceback.format_exc()
    logger.error(trace_error)

    # Отправляем полный трейс администратору
    part_of_trace = trace_error
    while part_of_trace:
        chunk = part_of_trace[: tb.const.MAX_MESSAGE_LENGTH]
        await bot.send_message(admin_telegram_id, chunk)
        part_of_trace = part_of_trace[tb.const.MAX_MESSAGE_LENGTH :]

    # Фильтруем и отправляем строки с упоминанием пакета 'app' из уже полученного трейса
    lines_with_package_name = [
        line for line in trace_error.splitlines() if "app" in line
    ]
    if lines_with_package_name:
        brief_trace = "\n".join(lines_with_package_name)
        # Отправляем краткий трейс администратору частями, если он слишком длинный
        part_of_brief_trace = brief_trace
        while part_of_brief_trace:
            chunk = part_of_brief_trace[: tb.const.MAX_MESSAGE_LENGTH]
            await bot.send_message(admin_telegram_id, chunk)
            part_of_brief_trace = part_of_brief_trace[tb.const.MAX_MESSAGE_LENGTH :]
    else:
        # Если в трейсе нет упоминания пакета, информируем об этом
        await bot.send_message(
            admin_telegram_id, "Строки с названием пакета 'app' в трейсе не найдены."
        )

    await bot.send_message(admin_telegram_id, f"Ник пользователя: {user_name}")
