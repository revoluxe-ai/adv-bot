from aiogram import Router

from .main_handler import router as MainRouter

router = Router()

_ = router.include_router(MainRouter)
