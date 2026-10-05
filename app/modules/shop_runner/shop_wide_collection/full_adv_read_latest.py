"""Read-latest ``full_adv_wb_stat`` per ``(adv_id, date)`` (design §F.2–§F.3, task 6.2).

Spec: ``connected-shop-campaign-ad-data-collection`` (S12 read-side recovery).
Debt: ``openspec/architectural-debt/TEMPORARY_DUAL_CAMPAIGN_COLLECTION.md``.
Qualification: ``openspec/decisions/clickhouse-sql-database-qualification/decision.md``.

Узкий helper для shop-wide collection: ``argMax(metric, version)`` по grain
``(adv_id, date)``. Не analytics layer — только доказуемый read seam для
recovery после failed attempt. Успешная более ранняя версия остаётся
авторитетной, пока не появится более новая успешная запись.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Protocol

_SELECT_READ_LATEST = """
SELECT
    adv_id,
    date,
    argMax(views, version) AS views,
    argMax(clicks, version) AS clicks,
    argMax(spend, version) AS spend,
    argMax(orders, version) AS orders,
    max(toFloat64OrZero(toString(version))) AS latest_version_num
FROM default_db.full_adv_wb_stat
WHERE adv_id IN %(adv_ids)s
GROUP BY adv_id, date
"""


class _QueryRows(Protocol):
    """Минимальный ответ ``client.query``."""

    result_rows: Sequence[Sequence[object]]


class FullAdvReadLatestClickHouse(Protocol):
    """Узкий CH-клиент read-latest full_adv facts."""

    async def query(
        self,
        query: str,
        parameters: Mapping[str, object] | None = None,
    ) -> _QueryRows: ...


@dataclass(frozen=True, slots=True)
class FullAdvReadLatestRow:
    """Read-latest метрики одного ``(adv_id, date)`` grain."""

    adv_id: int
    date: str
    views: int
    clicks: int
    spend: float
    orders: int
    latest_version_num: float


def _as_int(value: object, field_name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError(f"{field_name} from full_adv read-latest must be int")
    return value


def _as_float(value: object, field_name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TypeError(f"{field_name} from full_adv read-latest must be numeric")
    return float(value)


def _as_date_text(value: object) -> str:
    if isinstance(value, str):
        return value
    if hasattr(value, "strftime"):
        return value.strftime("%Y-%m-%d")  # type: ignore[union-attr,no-any-return]
    raise TypeError("date from full_adv read-latest must be str or date-like")


def _row_from_result(row: Sequence[object]) -> FullAdvReadLatestRow:
    if len(row) != 7:
        raise TypeError("full_adv read-latest select must return 7 columns")
    return FullAdvReadLatestRow(
        adv_id=_as_int(row[0], "adv_id"),
        date=_as_date_text(row[1]),
        views=_as_int(row[2], "views"),
        clicks=_as_int(row[3], "clicks"),
        spend=_as_float(row[4], "spend"),
        orders=_as_int(row[5], "orders"),
        latest_version_num=_as_float(row[6], "latest_version_num"),
    )


async def load_read_latest_full_adv_facts(
    client: FullAdvReadLatestClickHouse,
    *,
    adv_ids: Sequence[int],
) -> tuple[FullAdvReadLatestRow, ...]:
    """Read-latest ``full_adv_wb_stat`` rows per ``(adv_id, date)``.

    После failed collection attempt более ранняя успешная версия остаётся
    видимой через ``argMax(..., version)`` — failed insert не затирает fact.

    Args:
        client: уже открытый CH-клиент.
        adv_ids: physical WB campaign ids. Пустой список не выполняет SQL.

    Returns:
        Кортеж read-latest grains для найденных ``(adv_id, date)``.
    """
    if not adv_ids:
        return ()
    result = await client.query(
        _SELECT_READ_LATEST,
        parameters={"adv_ids": list(adv_ids)},
    )
    return tuple(_row_from_result(row) for row in result.result_rows)
