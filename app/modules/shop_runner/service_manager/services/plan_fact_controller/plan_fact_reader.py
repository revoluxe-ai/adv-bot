from dataclasses import dataclass
from typing import Sequence

from app.utils.click_house.client import get_clickhouse_client


@dataclass
class PlanFactSummary:
    adv_id: int
    plan_orders: int | None
    plan_target_pay_for_order: int | None
    plan_max_pay_for_order: int | None
    fact_predict_orders: float | None
    fact_pay_for_order: float | None


class PlanFactReader:
    @staticmethod
    def _load_query() -> str:
        from pathlib import Path

        sql_path = (
            Path(__file__)
            .parent
            .joinpath("sql", "get_latest_plan_fact.sql")
        )
        return sql_path.read_text(encoding="utf-8")

    @staticmethod
    def _as_int(value: object) -> int:
        if isinstance(value, bool):
            return int(value)
        if isinstance(value, int | float | str):
            return int(value)
        raise TypeError(f"Expected int-convertible value, got {type(value)!r}")

    @staticmethod
    def _as_int_or_none(value: object) -> int | None:
        if value is None:
            return None
        return PlanFactReader._as_int(value)

    @staticmethod
    def _as_float_or_none(value: object) -> float | None:
        if value is None:
            return None
        if isinstance(value, bool):
            return float(value)
        if isinstance(value, int | float | str):
            return float(value)
        raise TypeError(f"Expected float-convertible value, got {type(value)!r}")

    @staticmethod
    def _row_to_summary(row: Sequence[object]) -> PlanFactSummary:
        return PlanFactSummary(
            adv_id=PlanFactReader._as_int(row[0]),
            plan_orders=PlanFactReader._as_int_or_none(row[1]),
            plan_target_pay_for_order=PlanFactReader._as_int_or_none(row[2]),
            plan_max_pay_for_order=PlanFactReader._as_int_or_none(row[3]),
            fact_predict_orders=PlanFactReader._as_float_or_none(row[4]),
            fact_pay_for_order=PlanFactReader._as_float_or_none(row[5]),
        )

    async def get_latest_plan_fact(
        self, adv_id: int
    ) -> PlanFactSummary | None:
        """Возвращает последнюю запись план-факт по adv_id из ClickHouse.

        Поля plan_* — снимок на момент записи в кеш; для расчёта целевой
        себестоимости и иной бизнес-логики по плану используйте текущие
        настройки AdvSetting (PlanFactProvider.get_plan_data). Из данного
        метода для логики берите только факт: fact_predict_orders,
        fact_pay_for_order.
        """
        query = self._load_query()

        async with get_clickhouse_client() as client:
            result = await client.query(
                query,
                parameters={"adv_id": adv_id},
            )
    
        row = next(iter(result.result_rows), None)
        if not row:
            return None

        return self._row_to_summary(row)

    async def get_latest_plan_facts(
        self, adv_ids: list[int]
    ) -> dict[int, PlanFactSummary]:
        """Возвращает последние записи план-факт по списку adv_id из ClickHouse."""
        if not adv_ids:
            return {}
        normalized_adv_ids = sorted({int(adv_id) for adv_id in adv_ids})
        adv_ids_sql = ", ".join(str(adv_id) for adv_id in normalized_adv_ids)
        query = f"""
        SELECT
            adv_id,
            argMax(plan_orders, timestamp) AS plan_orders,
            argMax(plan_target_pay_for_order, timestamp) AS plan_target_pay_for_order,
            argMax(plan_max_pay_for_order, timestamp) AS plan_max_pay_for_order,
            argMax(fact_predict_orders, timestamp) AS fact_predict_orders,
            argMax(fact_pay_for_order, timestamp) AS fact_pay_for_order
        FROM default_db.plan_fact_stats
        WHERE adv_id IN ({adv_ids_sql})
        GROUP BY adv_id
        """
        async with get_clickhouse_client() as client:
            result = await client.query(query)
        summaries: dict[int, PlanFactSummary] = {}
        for row in result.result_rows:
            summary = self._row_to_summary(row)
            summaries[summary.adv_id] = summary
        return summaries
