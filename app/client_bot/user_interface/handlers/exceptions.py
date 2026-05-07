import logging
import traceback
import typing
from typing import Any

import aiogram
from aiogram import Router
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError
from aiogram.dispatcher.event.bases import SkipHandler
from aiogram.filters.exception import ExceptionTypeFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import Update
from aiogram.types.error_event import ErrorEvent

from app import client_bot as tb
from app.client_bot import const
from app.core.wb_api.exceptions import ApiForbiddenError
from app.exc import CardNotFoundInDB

logger = logging.getLogger(__name__)

_SECTION_EXTRA = "\n\n--- extra ---\n\n"
_SECTION_APP_LINES = "\n\n--- app lines ---\n\n"
_SECTION_FULL_TRACEBACK = "\n\n--- full traceback ---\n\n"
_SECTION_FOOTER = "\n\n--- footer ---\n\n"

admin_telegram_id = 373435337


async def _send_text_chunks(
    bot: aiogram.Bot,
    chat_id: int,
    full_text: str,
) -> None:
    """Send long text in Telegram-sized chunks; per-chunk failures are logged only."""
    max_len = tb.const.MAX_MESSAGE_LENGTH
    remaining = full_text
    while remaining:
        chunk = remaining[:max_len]
        remaining = remaining[max_len:]
        try:
            _ = await bot.send_message(chat_id=chat_id, text=chunk)
        except Exception:
            logger.exception(
                "Failed to send chunked message (chat_id=%s, chunk_len=%s)",
                chat_id,
                len(chunk),
            )


async def send_admin_error_report(
    bot: aiogram.Bot,
    *,
    headline: str,
    traceback_text: str | None = None,
    extra: str | None = None,
    brief_trace_app_lines: str | None = None,
    footer: str | None = None,
) -> None:
    """Build one admin report (headline → extra → app lines → full traceback → footer) and chunk-send."""
    parts: list[str] = [headline.strip()]
    if extra is not None and extra.strip():
        parts.append(_SECTION_EXTRA + extra.strip())
    if brief_trace_app_lines is not None and brief_trace_app_lines.strip():
        parts.append(_SECTION_APP_LINES + brief_trace_app_lines.strip())
    if traceback_text is not None and traceback_text.strip():
        parts.append(_SECTION_FULL_TRACEBACK + traceback_text.strip())
    if footer is not None and footer.strip():
        parts.append(_SECTION_FOOTER + footer.strip())
    report = "".join(parts)
    await _send_text_chunks(bot, admin_telegram_id, report)


def is_telegram_message_too_long(exc: BaseException) -> bool:
    """Detect Telegram API response for over-limit message length."""
    if not isinstance(exc, TelegramBadRequest):
        return False
    error_text = (getattr(exc, "message", None) or str(exc)).lower()
    return "message is too long" in error_text


def extract_telegram_method_payload(method: Any) -> str | None:
    """Extract text-like payload from TelegramMethod for diagnostics."""
    for attr in ("text", "caption"):
        value = getattr(method, attr, None)
        if isinstance(value, str) and value:
            return value
    return None


def describe_telegram_method(method: Any) -> str:
    """Fallback representation if no text/caption payload exists."""
    return f"{type(method).__name__}: {method!r}"


def _chat_id_from_error_update(update: Update) -> int:
    """User chat id from message or callback_query (shared error-handler resolution)."""
    message = update.message
    if message is None:
        assert update.callback_query
        assert update.callback_query.message
        assert update.callback_query.message.chat
        return int(update.callback_query.message.chat.id)
    return message.chat.id


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
    exception = error_event.exception
    if not isinstance(exception, TelegramBadRequest):
        raise SkipHandler()
    if not is_telegram_message_too_long(exception):
        raise SkipHandler()

    method = exception.method
    method_name = type(method).__name__
    chat_from_method = getattr(method, "chat_id", None)
    payload = extract_telegram_method_payload(method)
    payload_len = len(payload) if payload is not None else 0

    logger.warning(
        "Telegram message too long: method=%s chat_id=%s payload_chars=%s",
        method_name,
        chat_from_method,
        payload_len,
    )

    meta = (
        "TelegramBadRequest: message is too long\n"
        f"method={method_name}\n"
        f"chat_id={chat_from_method}\n"
        f"payload_chars={payload_len}"
    )
    await send_admin_error_report(
        bot,
        headline="Telegram send_message overflow",
        extra=meta
        + "\n\n--- payload ---\n\n"
        + (payload if payload is not None else describe_telegram_method(method)),
    )

    try:
        user_chat_id = _chat_id_from_error_update(error_event.update)
        await bot.send_message(
            chat_id=user_chat_id,
            text=(
                "Сообщение слишком длинное для Telegram (лимит символов). "
                f"Обратитесь в поддержку: {const.SUPPORT_LINK}"
            ),
        )
    except Exception:
        logger.exception("Failed to notify user after message-too-long error")

    return


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
    await send_admin_error_report(
        bot,
        headline="CardNotFoundInDB",
        extra=str(exception),
    )
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

    lines_with_package_name = [
        line for line in trace_error.splitlines() if "app" in line
    ]
    if lines_with_package_name:
        brief_trace_app_lines = "\n".join(lines_with_package_name)
        extra_for_admin: str | None = None
    else:
        brief_trace_app_lines = None
        extra_for_admin = (
            "Строки с названием пакета 'app' в трейсе не найдены."
        )

    await send_admin_error_report(
        bot,
        headline="Unhandled exception in client bot handler",
        traceback_text=trace_error,
        extra=extra_for_admin,
        brief_trace_app_lines=brief_trace_app_lines,
        footer=f"Ник пользователя: {user_name}",
    )
