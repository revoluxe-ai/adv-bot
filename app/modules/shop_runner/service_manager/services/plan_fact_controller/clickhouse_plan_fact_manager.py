import logging
from typing import Sequence

from app.modules.shop_runner.service_manager.services.plan_fact_controller.dto.plan_fact_stat_dto import (
    PlanFactStatDTO,
)
from app.utils.click_house.client import get_clickhouse_client

logger = logging.getLogger(__name__)


class ClickHousePlanFactManager:
    """Менеджер для записи данных план-факта в ClickHouse"""
    @staticmethod
    async def insert_plan_fact_stats(stats: Sequence[PlanFactStatDTO]) -> None:
        """
        Записывает данные план-факта в ClickHouse батчем.

        Args:
            stats: Список DTO объектов с данными план-факта
        """
        if not stats:
            return

        column_names = [
            "adv_id",
            "shop_id",
            "date",
            "timestamp",
            "plan_orders",
            "plan_target_pay_for_order",
            "plan_max_pay_for_order",
            "fact_predict_orders",
            "fact_original_orders",
            "fact_pay_for_order",
            "fact_method",
            "version",
        ]

        # Подготовка данных для вставки
        data = [
            [
                row.adv_id,
                row.shop_id,
                row.date,
                row.timestamp,
                row.plan_orders,
                row.plan_target_pay_for_order,
                row.plan_max_pay_for_order,
                row.fact_predict_orders,
                row.fact_original_orders,
                row.fact_pay_for_order,
                row.fact_method,
                row.version,
            ]
            for row in stats
        ]

        try:
            async with get_clickhouse_client() as client:
                await client.insert(
                    "default_db.plan_fact_stats", data, column_names=column_names
                )
            logger.debug(
                "Записано %d записей план-факта в ClickHouse", len(stats)
            )
        except Exception as exc:
            logger.error(
                "Ошибка записи данных план-факта в ClickHouse: %s",
                exc,
                exc_info=True,
            )
            raise

