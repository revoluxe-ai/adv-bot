import typing

from sqlalchemy import select

from app.core.wb_api.exceptions import ApiForbiddenError
from app.exc import CardNotFoundInDB
from aiogram import Router
from aiogram.exceptions import TelegramForbiddenError, TelegramBadRequest
from aiogram.filters.exception import ExceptionTypeFilter
from aiogram.types.error_event import ErrorEvent
import aiogram
from app.utils.db.models import User
from app.utils.db.session_maker import get_async_session_maker as sm
import traceback
from aiogram.fsm.context import FSMContext
import logging
from app import client_bot as tb
from app.client_bot import const
from app.modules.wb_keywords_parser.wb_parser.parser import ErrorParsingPositions

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


@admin_router.errors(ExceptionTypeFilter(TelegramBadRequest))
async def error_handler_for_user(error_event: ErrorEvent, state: FSMContext, bot: aiogram.Bot):
    await state.set_state()
    message = error_event.update.message
    chat_id = message.chat.id
    await bot.send_message(chat_id=chat_id,
                           text='Кнопка устарела, нажмите на нее или другую еще раз. В случае регулярного повторения '
                                f'проблемы обратитесь в поддержку -> {const.SUPPORT_LINK}')



@admin_router.errors(ExceptionTypeFilter(TelegramForbiddenError))
async def forbidden_error_handler(error_event: ErrorEvent, state: FSMContext, bot: aiogram.Bot):
    logger.error('Юзер заблокировал бота')
    return


# @admin_router.errors(ExceptionTypeFilter(aiogram.exceptions.TelegramBadRequest))
# async def bad_request_error_handler(error_event: ErrorEvent, state: FSMContext, bot: aiogram.Bot):
#     message = error_event.update.message
#     if message is None:
#         chat_id = error_event.update.callback_query.message.chat.id
#     else:
#         chat_id = message.chat.id
#     await bot.send_message(chat_id=chat_id,
#                            text='Эта кнопка устарела. Нажмите на /start и начните сначала'
#                            'Если ошибка повторяется, обратитесь к администратору бота @skyline360_1')
#     return


@admin_router.errors(ExceptionTypeFilter(ErrorParsingPositions))
async def error_parsing_positions_handler(error_event: ErrorEvent, state: FSMContext, bot: aiogram.Bot):
    message = error_event.update.message
    exception = error_event.exception

    if message is None:
        chat_id = error_event.update.callback_query.message.chat.id
    else:
        chat_id = message.chat.id
    await bot.send_message(chat_id=chat_id,
                           text='Ошибка парсинга позиций. Попробуйте через время еще раз. '
                                'Если ошибка будет повторяться, то обратитесь в поддержку -> ')
    await bot.send_message(admin_telegram_id, str(exception))

    async with sm() as session:
        stmt = select(User.username).where(User.user_telegram_id == chat_id)
        user_name = await session.execute(stmt)
        user_name = user_name.scalar_one_or_none()


    await bot.send_message(admin_telegram_id, f'Ошибка парсинга у пользователя {user_name}')

    return



@admin_router.errors(ExceptionTypeFilter(ApiForbiddenError))
async def api_forbidden_error_handler(error_event: ErrorEvent, state: FSMContext, bot: aiogram.Bot):
    message = error_event.update.message
    exception = error_event.exception

    if message is None:
        chat_id = error_event.update.callback_query.message.chat.id
    else:
        chat_id = message.chat.id
    await bot.send_message(chat_id=chat_id,
                           text='Нет доступов к данному магазину.'
                                ' Получите или создайте новый токен с правами "Контент",'
                                ' "Продвижение" и "Аналитика" (галочку "Только для чтения" не ставить) \n\n'
                                'Затем добавьте этот магазин ЕЩЕ РАЗ под НОВЫМ именем и с новым токеном '
                                '(новый магазин создан не будет, токен добавиться к старому)')
    return





@admin_router.errors(ExceptionTypeFilter(CardNotFoundInDB))
async def not_found_wb_card_error_handler(error_event: ErrorEvent, state: FSMContext, bot: aiogram.Bot):
    message = error_event.update.message
    exception = error_event.exception
    exception = typing.cast(CardNotFoundInDB, exception)


    if message is None:
        chat_id = error_event.update.callback_query.message.chat.id
    else:
        chat_id = message.chat.id
    await bot.send_message(chat_id=chat_id,
                           text=f'Ошибка получения карточки, обратитесь в поддержку -> {const.SUPPORT_LINK}')
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
    await bot.send_message(chat_id=chat_id,
                           text='Произошла ошибка, но не волнуйтесь! Бот продолжает работать '
                                'и по прежнему выполняет свои функции. Проблема только в интерфейсе, а администратор'
                                ' уже уведомлен о ней. Попробуйте выполнить нужное вам действие еще раз или вернитесь'
                                ' в главное меню, через команду /start . Связаться с разработчиком вы можете по '
                                f'этому контакту: {const.SUPPORT_LINK}')
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


