"""Read-only шов AttributionFactsReader для AI Package analysis."""

from __future__ import annotations

from datetime import date
from typing import Protocol

from app.modules.attribution_facts.domain.models import (
    AttributionCoverage,
    AttributionQueryResult,
    AttributionScope,
    DateWindow,
)
from app.modules.attribution_facts.domain.enums import (
    AttributionCoverageStatus,
    AttributionReasonCode,
)
from app.modules.attribution_facts.ports.reader import AttributionFactsReader
from app.modules.ai_package_v1.analysis.models import AnalysisAttributionLegEvidence


class AnalysisAttributionReaderProtocol(Protocol):
    """Узкий async read-only порт без прямого SQL к observation tables."""

    async def query_leg_window(
        self,
        *,
        shop_id: str,
        physical_adv_id: int,
        window_start: date,
        window_end: date,
    ) -> AttributionQueryResult:
        """Attribution facts для одной physical leg и календарного окна."""
        ...


class EmptyAnalysisAttributionReader:
    """Тестовый шов: fail-closed NO_DATA без сети."""

    async def query_leg_window(
        self,
        *,
        shop_id: str,
        physical_adv_id: int,
        window_start: date,
        window_end: date,
    ) -> AttributionQueryResult:
        _ = (shop_id, physical_adv_id, window_start, window_end)
        return AttributionQueryResult(
            facts=(),
            coverage=AttributionCoverage(
                status=AttributionCoverageStatus.NO_DATA,
                reason_codes=(AttributionReasonCode.ATTRIBUTION_SOURCE_MISSING,),
            ),
        )


class PortAnalysisAttributionReader:
    """Делегирует в AttributionFactsReader (CH reader или in-memory fake)."""

    def __init__(self, reader: AttributionFactsReader) -> None:
        self._reader = reader

    async def query_leg_window(
        self,
        *,
        shop_id: str,
        physical_adv_id: int,
        window_start: date,
        window_end: date,
    ) -> AttributionQueryResult:
        scope = AttributionScope(
            shop_id=shop_id,
            physical_adv_ids=frozenset({physical_adv_id}),
        )
        window = DateWindow(window_start, window_end)
        return await self._reader.query(scope, window)


async def collect_attribution_evidence(
    reader: AnalysisAttributionReaderProtocol,
    *,
    shop_id: str,
    windows: list[object],
    legs: list[tuple[int, str]],
) -> tuple[AnalysisAttributionLegEvidence, ...]:
    """Pre-fetch attribution для каждой physical leg × analysis window."""
    evidence: list[AnalysisAttributionLegEvidence] = []
    for spec in windows:
        window_id = str(getattr(spec, "window_id"))
        start = getattr(spec, "start")
        end = getattr(spec, "end")
        for adv_id, _role in legs:
            query = await reader.query_leg_window(
                shop_id=shop_id,
                physical_adv_id=adv_id,
                window_start=start,
                window_end=end,
            )
            evidence.append(
                AnalysisAttributionLegEvidence(
                    window_id=window_id,
                    physical_adv_id=adv_id,
                    query_result=query,
                )
            )
    return tuple(evidence)


class ChAnalysisAttributionReader:
    """ClickHouse-backed reader через ``ChAttributionFactsReader`` (no direct table SQL)."""

    async def query_leg_window(
        self,
        *,
        shop_id: str,
        physical_adv_id: int,
        window_start: date,
        window_end: date,
    ) -> AttributionQueryResult:
        from app.modules.attribution_facts.readers.ch_attribution_facts_reader import (
            ChAttributionFactsReader,
        )
        from app.utils.ch_semaphore import anti_ch_crash_semaphore
        from app.utils.click_house.client import get_clickhouse_client

        async with anti_ch_crash_semaphore:
            async with get_clickhouse_client() as client:
                port_reader = PortAnalysisAttributionReader(
                    ChAttributionFactsReader(client)
                )
                return await port_reader.query_leg_window(
                    shop_id=shop_id,
                    physical_adv_id=physical_adv_id,
                    window_start=window_start,
                    window_end=window_end,
                )


__all__ = [
    "AnalysisAttributionReaderProtocol",
    "ChAnalysisAttributionReader",
    "EmptyAnalysisAttributionReader",
    "PortAnalysisAttributionReader",
    "collect_attribution_evidence",
]
