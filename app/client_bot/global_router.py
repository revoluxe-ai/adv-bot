from aiogram import Router
from . import middlewars
from .user_interface.handlers import start
from .user_interface.handlers.ref_program import router as ref_program_router
from .common_routers import common_router


global_router = Router()
global_router.include_routers(common_router)
global_router.include_routers(start.router)
global_router.include_routers(ref_program_router)
global_router.message.middleware(middlewars.ThrottlingMiddleware())
global_router.callback_query.middleware(middlewars.ThrottlingMiddleware())







