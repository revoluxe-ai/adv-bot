__all__ = ["router"]


from aiogram import Router

from .change_max_price_for_order import router as MaxPriceForOrderRourter
from .change_plan_for_sales_for_day import router as ChangePlanForSalesForDayRouter
from .change_target_price_for_order import router as ChangeTargetPriceForOrderRourter
from .toggle_v3_raise_max_cpo import router as ToggleV3RaiseMaxCpoRouter
from .toggle_raise_plan_on_promobonuses import router as ToggleRaisePlanOnPromobonusesRouter

router = Router()

router.include_routers(
    ChangePlanForSalesForDayRouter,
    ChangeTargetPriceForOrderRourter,
    MaxPriceForOrderRourter,
    ToggleV3RaiseMaxCpoRouter,
    ToggleRaisePlanOnPromobonusesRouter,
)
