import logging
import traceback
import typing

from app.modules.wb_adv_updater.exceptions import NotFoundWBCard
import aiogram
from aiogram import Router
from aiogram.exceptions import TelegramForbiddenError
from aiogram.filters.exception import ExceptionTypeFilter
from aiogram.fsm.context import FSMContext
from aiogram.types.error_event import ErrorEvent

from app import client_bot as tb
from app.client_bot import const

logger = logging.getLogger(__name__)



admin_telegram_id = 373435337

user_router = Router()
admin_router = Router()



@admin_router.errors(ExceptionTypeFilter(TelegramForbiddenError))
async def forbidden_error_handler(error_event: ErrorEvent, state: FSMContext, bot: aiogram.Bot):
    logger.error('Юзер заблокировал бота')
    return


@admin_router.errors(ExceptionTypeFilter(NotFoundWBCard))
async def not_found_wb_card_error_handler(error_event: ErrorEvent, state: FSMContext, bot: aiogram.Bot):
    message = error_event.update.message
    exception = error_event.exception
    exception = typing.cast(NotFoundWBCard, exception)


    if message is None:
        chat_id = error_event.update.callback_query.message.chat.id
    else:
        chat_id = message.chat.id
    await bot.send_message(chat_id=chat_id,
                           text='Ошибка получения карточки, обратитесь к администратору бота @skyline360_1')
    await bot.send_message(admin_telegram_id, str(exception))
    return




@admin_router.errors(ExceptionTypeFilter(Exception))
async def error_handler(error_event: ErrorEvent, state: FSMContext, bot: aiogram.Bot):
    await state.clear()
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
    await bot.send_message(chat_id=chat_id,
                           text='Произошла ошибка, но не волнуйтесь! Бот продолжает работать '
                                'и по прежнему выполняет свои функции. Проблема только в интерфейсе, а администратор'
                                ' уже уведомлен о ней. Попробуйте выполнить нужное вам действие еще раз или вернитесь'
                                ' в главное меню, через команду /start . Связаться с разработчиком вы можете по '
                                'этому контакту: @skyline360_1')
    trace_error = traceback.format_exc()
    logger.error(trace_error)

    # Отправляем полный трейс администратору
    part_of_trace = trace_error
    while part_of_trace:
        chunk = part_of_trace[:tb.const.MAX_MESSAGE_LENGTH]
        await bot.send_message(admin_telegram_id, chunk)
        part_of_trace = part_of_trace[tb.const.MAX_MESSAGE_LENGTH:]

    # Фильтруем и отправляем строки с упоминанием пакета 'app' из уже полученного трейса
    lines_with_package_name = [line for line in trace_error.splitlines() if 'app' in line]
    if lines_with_package_name:
        brief_trace = "\n".join(lines_with_package_name)
        # Отправляем краткий трейс администратору частями, если он слишком длинный
        part_of_brief_trace = brief_trace
        while part_of_brief_trace:
            chunk = part_of_brief_trace[:tb.const.MAX_MESSAGE_LENGTH]
            await bot.send_message(admin_telegram_id, chunk)
            part_of_brief_trace = part_of_brief_trace[tb.const.MAX_MESSAGE_LENGTH:]
    else:
        # Если в трейсе нет упоминания пакета, информируем об этом
        await bot.send_message(admin_telegram_id, "Строки с названием пакета 'app' в трейсе не найдены.")

    await bot.send_message(admin_telegram_id, 'Ник пользователя: %s' % user_name )






