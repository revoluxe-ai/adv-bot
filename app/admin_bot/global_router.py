from aiogram import Router
from . import catch_chat_id

global_router = Router()


global_router.include_router(catch_chat_id.router)