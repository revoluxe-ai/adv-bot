from aiogram import Router

from .main_handler import router as MainRouter
from .setting_handlers import SettingHandlersRouter

router = Router()

router.include_routers(MainRouter)
router.include_routers(SettingHandlersRouter)
