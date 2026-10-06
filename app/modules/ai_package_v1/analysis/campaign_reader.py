"""Read-only чтение дневных фактов кампании на диапазоне окон."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import date, datetime
from typing import Any, Protocol

from app.modules.ai_package_v1.analysis.models import CampaignDailyFact
from app.modules.ai_package_v1.readers.sql_loader import load_sql
from app.utils.ch_semaphore import anti_ch_crash_semaphore
from app.utils.click_house.client import get_clickhouse_client

_QUERY = load_sql("analysis_campaign_daily_by_adv_ids")


class AnalysisCampaignReaderProtocol(Protocol):
    """Узкий read-only шов дневных фактов анализа."""

    async def fetch_daily_facts(
        self,
        *,
        shop_id: int,
        adv_ids: Sequence[int],
        end_date: date,
    ) -> list[CampaignDailyFact]:
        """Факты ног до ``end_date`` включительно, одним проходом."""
        ...


class EmptyAnalysisCampaignReader:
    """Пустой шов для тестов экспорта, которым не нужен ClickHouse."""

    async def fetch_daily_facts(
        self,
        *,
        shop_id: int,
        adv_ids: Sequence[int],
        end_date: date,
    ) -> list[CampaignDailyFact]:
        """Не открывает сеть и не подменяет пропуск нулём."""
        _ = (shop_id, adv_ids, end_date)
        return []


class ChAnalysisCampaignReader:
    """Одно чтение ``default_db.full_adv_wb_stat`` до границы анализа."""

    @property
    def query_text(self) -> str:
        """Текст SQL для проверки квалификации базы."""
        return _QUERY

    async def fetch_daily_facts(
        self,
        *,
        shop_id: int,
        adv_ids: Sequence[int],
        end_date: date,
    ) -> list[CampaignDailyFact]:
        """Читает дневные факты. ``shop_id`` в таблицу не пишется: его нет в зерне CH."""
        if not adv_ids:
            return []
        async with anti_ch_crash_semaphore:
            async with get_clickhouse_client() as client:
                return await self.fetch_daily_facts_with_client(
                    client,
                    shop_id=shop_id,
                    adv_ids=adv_ids,
                    end_date=end_date,
                )

    async def fetch_daily_facts_with_client(
        self,
        client: Any,
        *,
        shop_id: int,
        adv_ids: Sequence[int],
        end_date: date,
    ) -> list[CampaignDailyFact]:
        """То же чтение с переданным клиентом. Период вызывающей стороны не режет запрос."""
        _ = shop_id
        if not adv_ids:
            return []
        result = await client.query(
            _QUERY,
            parameters={
                "end_date": end_date.isoformat(),
                "adv_ids": list(adv_ids),
            },
        )
        facts: list[CampaignDailyFact] = []
        for row in result.result_rows:
            facts.append(
                CampaignDailyFact(
                    adv_id=int(row[0]),
                    stat_date=_coerce_date(row[1]),
                    views=_optional_int(row[2]),
                    clicks=_optional_int(row[3]),
                    spend_rub=_optional_float(row[4]),
                    added_to_cart=_optional_int(row[5]),
                    orders=_optional_int(row[6]),
                    order_sum_rub=_optional_float(row[7]),
                )
            )
        return facts


def _optional_int(value: object) -> int | None:
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    return int(str(value))


def _optional_float(value: object) -> float | None:
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    return float(str(value))


def _coerce_date(value: object) -> date:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    return date.fromisoformat(str(value)[:10])
