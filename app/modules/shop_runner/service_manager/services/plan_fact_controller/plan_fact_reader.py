import logging
from collections.abc import Sequence
from dataclasses import dataclass

from app.modules.common_slaves.wildberries.models import AdvSetting
from app.modules.common_slaves.wildberries.models.fact_methods_enum import FactMethods
from app.modules.shop_runner.service_manager.old_modules.setting_auto_updater.data_classes import (
    FactData,
)
from app.utils.click_house.client import get_clickhouse_client

logger = logging.getLogger(__name__)


@dataclass
class PlanFactSummary:
    adv_id: int
    plan_orders: int | None
    plan_target_pay_for_order: int | None
    plan_max_pay_for_order: int | None
    fact_predict_orders: float | None
    fact_pay_for_order: float | None
    fact_original_orders: float | None = None
    fact_method: str | None = None


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
        if isinstance(value, int):
            return int(value)
        if isinstance(value, float):
            if not value.is_integer():
                raise TypeError(
                    f"Expected integer-like float value, got {value!r}"
                )
            return int(value)
        if isinstance(value, str):
            raw = value.strip()
            if raw.startswith(("+", "-")):
                sign, digits = raw[0], raw[1:]
                if digits.isdigit():
                    return int(f"{sign}{digits}")
            elif raw.isdigit():
                return int(raw)
            raise TypeError(f"Expected integer-like string value, got {value!r}")
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
    def _as_str_or_none(value: object) -> str | None:
        if value is None:
            return None
        if isinstance(value, str):
            stripped = value.strip()
            return stripped if stripped else None
        return str(value)

    @staticmethod
    def _row_to_summary(row: Sequence[object]) -> PlanFactSummary:
        return PlanFactSummary(
            adv_id=PlanFactReader._as_int(row[0]),
            plan_orders=PlanFactReader._as_int_or_none(row[1]),
            plan_target_pay_for_order=PlanFactReader._as_int_or_none(row[2]),
            plan_max_pay_for_order=PlanFactReader._as_int_or_none(row[3]),
            fact_predict_orders=PlanFactReader._as_float_or_none(row[4]),
            fact_pay_for_order=PlanFactReader._as_float_or_none(row[5]),
            fact_original_orders=PlanFactReader._as_float_or_none(row[6]),
            fact_method=PlanFactReader._as_str_or_none(row[7]),
        )

    async def get_latest_plan_fact(
        self, adv_id: int
    ) -> PlanFactSummary | None:
        """Возвращает последнюю запись план-факт по adv_id из ClickHouse.

        Поля plan_* — снимок на момент записи в кеш; для расчёта целевой
        себестоимости и иной бизнес-логики по плану используйте текущие
        настройки AdvSetting (PlanFactProvider.get_plan_data). Из данного
        метода для логики берите факт: fact_predict_orders, fact_pay_for_order,
        fact_original_orders, fact_method (при сборке FactData из кеша).
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
        query = """
        SELECT
            adv_id,
            argMax(plan_orders, timestamp) AS plan_orders,
            argMax(plan_target_pay_for_order, timestamp) AS plan_target_pay_for_order,
            argMax(plan_max_pay_for_order, timestamp) AS plan_max_pay_for_order,
            argMax(fact_predict_orders, timestamp) AS fact_predict_orders,
            argMax(fact_pay_for_order, timestamp) AS fact_pay_for_order,
            argMax(fact_original_orders, timestamp) AS fact_original_orders,
            argMax(fact_method, timestamp) AS fact_method
        FROM default_db.plan_fact_stats
        WHERE adv_id IN %(adv_ids)s
        GROUP BY adv_id
        """
        async with get_clickhouse_client() as client:
            result = await client.query(
                query,
                parameters={"adv_ids": normalized_adv_ids},
            )
        summaries: dict[int, PlanFactSummary] = {}
        for row in result.result_rows:
            summary = self._row_to_summary(row)
            summaries[summary.adv_id] = summary
        return summaries


def _resolve_fact_method_from_ch(
    method_str: str | None, adv_setting: AdvSetting
) -> FactMethods:
    if method_str:
        try:
            return FactMethods(method_str)
        except ValueError:
            logger.debug(
                "Неизвестный fact_method из plan_fact_stats: %s, берём из AdvSetting",
                method_str,
            )
    return adv_setting.sales_predict_method


def fact_data_from_plan_fact_summary(
    summary: PlanFactSummary | None,
    adv_setting: AdvSetting,
) -> FactData | None:
    """Собирает FactData из последнего снимка в ClickHouse (plan_fact_stats)."""
    if summary is None or summary.fact_predict_orders is None:
        return None
    predict = summary.fact_predict_orders
    original_src = (
        summary.fact_original_orders
        if summary.fact_original_orders is not None
        else predict
    )
    pay_for_order: float | None = None
    if summary.fact_pay_for_order is not None:
        pay_for_order = round(summary.fact_pay_for_order, 2)
    fact_method = _resolve_fact_method_from_ch(summary.fact_method, adv_setting)
    return FactData(
        predict_orders=round(predict, 2),
        original_orders=float(original_src),
        pay_for_order=pay_for_order,
        fact_method=fact_method,
    )
