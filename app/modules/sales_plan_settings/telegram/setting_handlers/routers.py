
__all__ = ['router']


from aiogram import Router

from . change_plan_for_sales_for_day import router as ChangePlanForSalesForDayRouter
from .change_target_price_for_order import router as ChangeTargetPriceForOrderRourter
from .change_max_price_for_order import router as MaxPriceForOrderRourter

router = Router()

router.include_routers(ChangePlanForSalesForDayRouter,
                       ChangeTargetPriceForOrderRourter,
                       MaxPriceForOrderRourter)
