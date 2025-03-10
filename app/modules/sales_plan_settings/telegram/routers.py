from aiogram import Router
from .setting_handlers import SettingHandlersRouter
from .main_handler import router as MainRouter

router = Router()

router.include_routers(MainRouter)
router.include_routers(SettingHandlersRouter)