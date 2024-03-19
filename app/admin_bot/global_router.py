from aiogram import Router
from .handlers import router as admin_bot_handlers


global_router = Router()


global_router.include_router(admin_bot_handlers)