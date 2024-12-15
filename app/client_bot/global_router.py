from aiogram import Router
from aiogram.utils import callback_answer
from app.modules import phone_getter

from . import middlewars
from .common_routers import common_router
from .user_interface.handlers import payments, ref_program, start, add_balance

global_router = Router()
global_router.callback_query.middleware(phone_getter.PhoneGetterMiddleWare())
global_router.callback_query.middleware(callback_answer.CallbackAnswerMiddleware(pre=True, text='Запрос в обработке'))
global_router.include_routers(common_router)
global_router.include_routers(add_balance.router)
global_router.include_routers(ref_program.router)
# global_router.message.middleware(middlewars.ThrottlingMiddleware())
global_router.include_routers(payments.router)
# global_router.callback_query.middleware(middlewars.ThrottlingMiddleware())

