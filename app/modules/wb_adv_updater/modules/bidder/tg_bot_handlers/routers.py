from aiogram import Router
from . import on_off_controller

router = Router()

router.include_routers(on_off_controller.router)