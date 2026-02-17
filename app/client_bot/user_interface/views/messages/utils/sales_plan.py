from typing import Protocol


class AdvProtocol(Protocol):
    target_price_for_order: float | None
    max_price_for_order: float | None
    plan_for_sales_for_day: int | None

def get_plan_set_status(adv: AdvProtocol) -> bool:
    return all([
        adv.target_price_for_order,
        adv.max_price_for_order,
        adv.plan_for_sales_for_day
    ])

