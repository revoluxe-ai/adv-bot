from aiogram import Router
from aiogram.exceptions import TelegramForbiddenError
from aiogram.filters.exception import ExceptionTypeFilter

from aiogram.types.error_event import ErrorEvent
# from app.telegram_bot.redis_manager import RedisManager
import app
import aiogram
import traceback
# redis_manager = app.telegram_bot.redis_manager.RedisManager()
from aiogram.fsm.context import FSMContext
import logging
from app import client_bot as tb
from app.client_bot import const

logger = logging.getLogger(__name__)



admin_telegram_id = 373435337

user_router = Router()


#
#
# @user_router.errors(ExceptionTypeFilter(my_exc.ApiForbiddenError))
# async def error_handler(error_event: ErrorEvent, state: FSMContext, bot: aiogram.Bot):
#     await state.clear()
#     logger.debug( 'Текущее состояние: %s', await state.get_state())
#     chat_id = error_event.update.message.chat.id
#
#     wb_user_cabinet: app.my_types.WBUserCabinet = error_event.exception.__dict__['wb_user_cabinet']
#     await errors_message.AddNewToken(bot, chat_id, wb_user_cabinet)()
#     return
#

admin_router = Router()



@admin_router.errors(ExceptionTypeFilter(TelegramForbiddenError))
async def forbidden_error_handler(error_event: ErrorEvent, state: FSMContext, bot: aiogram.Bot):
    logger.error('Юзер заблокировал бота')
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
                           text='Произошла ошибка, но вы не волнуйте! Бот продолжает работать '
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








