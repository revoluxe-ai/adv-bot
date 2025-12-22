from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel

from app.modules.common_slaves.wildberries.models.fact_methods_enum import FactMethods
from app.modules.shop_runner.service_manager.old_modules.setting_auto_updater.data_classes import (
    FactData,
    PlanData,
)


class PlanFactStatDTO(BaseModel):
    """DTO для записи данных план-факта в ClickHouse"""

    adv_id: int
    shop_id: str
    date: date
    timestamp: datetime
    # План данные
    plan_orders: Optional[int] = None
    plan_target_pay_for_order: Optional[int] = None
    plan_max_pay_for_order: Optional[int] = None
    # Факт данные
    fact_predict_orders: Optional[float] = None
    fact_original_orders: Optional[float] = None
    fact_pay_for_order: Optional[float] = None
    fact_method: Optional[str] = None
    # Версия для дедупликации
    version: float

    @classmethod
    def create(
        cls,
        adv_id: int,
        shop_id: str,
        plan: Optional[PlanData],
        fact: Optional[FactData],
        version: float,
    ) -> "PlanFactStatDTO":
        """Создает DTO из PlanData и FactData"""
        now = datetime.now()
        return cls(
            adv_id=adv_id,
            shop_id=shop_id,
            date=now.date(),
            timestamp=now,
            plan_orders=plan.orders if plan else None,
            plan_target_pay_for_order=plan.target_pay_for_order if plan else None,
            plan_max_pay_for_order=plan.max_pay_for_order if plan else None,
            fact_predict_orders=fact.predict_orders if fact else None,
            fact_original_orders=fact.original_orders if fact else None,
            fact_pay_for_order=fact.pay_for_order if fact else None,
            fact_method=(
                str(fact.fact_method.value)
                if fact
                and fact.fact_method
                and isinstance(fact.fact_method, FactMethods)
                else str(fact.fact_method)
                if fact and fact.fact_method
                else None
            ),
            version=version,
        )


