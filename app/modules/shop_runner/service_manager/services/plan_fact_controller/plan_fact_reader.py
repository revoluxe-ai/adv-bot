from dataclasses import dataclass

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

    async def get_latest_plan_fact(
        self, adv_id: int
    ) -> PlanFactSummary | None:

        query = self._load_query()

        async with get_clickhouse_client() as client:
            result = await client.query(
                query,
                parameters={"adv_id": adv_id},
            )
    
        row = next(iter(result.result_rows), None)
        if not row:
            return None

        return PlanFactSummary(
            adv_id=int(row[0]),
            plan_orders=row[1],
            plan_target_pay_for_order=row[2],
            plan_max_pay_for_order=row[3],
            fact_predict_orders=row[4],
            fact_pay_for_order=row[5],
        )
