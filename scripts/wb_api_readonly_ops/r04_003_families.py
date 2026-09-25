"""Family runners для COL-R04-003 mandatory API preflight (live Job only).

Маппинг r04 family_id → existing WB stack; без invent URL / raw HTTP.
"""

from __future__ import annotations

import datetime as dt
import hashlib
import json
from typing import Any, cast

from scripts.wb_api_readonly_ops.families import HubFamilyRunners, _jsonable
from scripts.wb_api_readonly_ops.models import (
    FamilyName,
    FamilyResult,
    FamilyStatus,
    Mode,
)
from scripts.wb_api_readonly_ops.mutation_guard import assert_read_only_op
from scripts.wb_api_readonly_ops.r04_003_constants import (
    FAMILY_CAMPAIGNS,
    FAMILY_CARDS,
    FAMILY_ORDERS,
    FAMILY_STATISTICS,
    DEFAULT_PERIOD_END,
    DEFAULT_PERIOD_START,
)

R04_003_FAMILY_ORDER: tuple[str, ...] = (
    FAMILY_ORDERS,
    FAMILY_CAMPAIGNS,
    FAMILY_STATISTICS,
    FAMILY_CARDS,
)


def _moscow_period_dates() -> tuple[dt.date, dt.date]:
    """Europe/Moscow calendar bounds из locked scope."""
    start = dt.date.fromisoformat(DEFAULT_PERIOD_START)
    end = dt.date.fromisoformat(DEFAULT_PERIOD_END)
    return start, end


def _payload_fingerprint(payload: object) -> str:
    """Schema fingerprint без raw rows в RETURN (структура + counts)."""
    if payload is None:
        return "EMPTY_PAYLOAD_V1"
    meta: dict[str, object] = {}
    if isinstance(payload, dict):
        mapping = cast(dict[str, object], payload)
        for key, val in mapping.items():
            if key in ("rows", "cards", "campaigns_sample", "stats_sample"):
                if isinstance(val, list):
                    meta[key] = {"list_len": len(val)}
                else:
                    meta[key] = type(val).__name__
            elif key == "adv_ids":
                meta[key] = {"count": len(val) if isinstance(val, list) else 0}
            else:
                meta[key] = val
    else:
        meta["repr"] = type(payload).__name__
    blob = json.dumps(meta, sort_keys=True, ensure_ascii=False)
    return f"fp_v1_{hashlib.sha256(blob.encode()).hexdigest()[:16]}"


class R04_003FamilyRunners:
    """Три mandatory + optional CONTENT_CARDS через HubFamilyRunners."""

    def __init__(self, wb_data_manager: object) -> None:
        self._hub = HubFamilyRunners(wb_data_manager)
        self._dm = wb_data_manager

    async def run_orders(
        self, mode: Mode, ctx: dict[str, Any]
    ) -> FamilyResult:
        """ORDERS_OR_SALES_REPORTS_READ — statistics-api supplier orders+sales."""
        result = await self._hub.run_orders_or_sales_reports_read(mode, ctx)
        gaps = list(result.gaps)
        blockers: list[str] = []
        if result.status != FamilyStatus.OK:
            if result.status == FamilyStatus.FAILED:
                blockers.append("NO_OWNER_LOCAL_MAPPING_FOR_REQUIRED_DATASET")
            gaps.append("PERIOD_SEMANTICS_UNRESOLVED_FOR_ORDERS_FAMILY")
        payload = result.payload if isinstance(result.payload, dict) else {}
        if payload.get("next_page_followed") == "NO":
            gaps.append("locked_period_full_window_not_traversed")
            blockers.append("PERIOD_SEMANTICS_UNRESOLVED_FOR_ORDERS_FAMILY")
        payload = dict(payload)
        payload["contract_blockers"] = blockers
        status = result.status
        if blockers and status == FamilyStatus.OK:
            status = FamilyStatus.PARTIAL
        return FamilyResult(
            family=result.family,
            status=status,
            gaps=gaps,
            error=result.error,
            payload={
                **payload,
                "r04_003_family_id": FAMILY_ORDERS,
                "schema_fingerprint": _payload_fingerprint(payload),
            },
            notes=list(result.notes) + [
                "r04_003: DATE_FROM_CURSOR Stage A; full locked period not claimed",
            ],
        )

    async def run_campaigns(
        self, mode: Mode, ctx: dict[str, Any]
    ) -> FamilyResult:
        """PROMOTION_CAMPAIGNS_READ — promotion count + sample v2 adverts."""
        assert_read_only_op("get_cabinet_adv_ids")
        pm = cast(Any, self._dm).promotion_manager
        gaps: list[str] = []
        blockers: list[str] = []
        try:
            adv_ids_raw = await pm._client.promotion_count_adapter.get_cabinet_adv_ids()
            adv_ids = cast(list[int], list(adv_ids_raw))
        except Exception as exc:  # noqa: BLE001
            return FamilyResult(
                family=FamilyName.ADS,
                status=FamilyStatus.FAILED,
                gaps=["promotion_count get_cabinet_adv_ids failed"],
                error=f"{type(exc).__name__}: {exc}",
                payload={
                    "r04_003_family_id": FAMILY_CAMPAIGNS,
                    "endpoint_or_report_alias": "/adv/v1/promotion/count",
                    "method_class": "GET_READ",
                    "contract_blockers": [
                        "NO_OWNER_LOCAL_MAPPING_FOR_REQUIRED_DATASET",
                    ],
                },
            )

        ctx["adv_ids"] = list(adv_ids)
        adv_count = len(adv_ids)
        id_binding_hash = hashlib.sha256(
            f"adv_count={adv_count}|alias=PROMOTION_CAMPAIGNS_READ".encode()
        ).hexdigest()[:16]

        payload: dict[str, object] = {
            "r04_003_family_id": FAMILY_CAMPAIGNS,
            "endpoint_or_report_alias": "/adv/v1/promotion/count",
            "method_class": "GET_READ",
            "authoritative_read_semantics_reference": (
                "local_adapter:promotion_count→get_cabinet_adv_ids"
            ),
            "adv_ids_count": adv_count,
            "identifier_binding_alias_or_hash": f"ADV_COUNT_COMMIT_{id_binding_hash}",
            "http_attempt_count": 1,
        }

        campaigns_sample: object = None
        if adv_ids:
            assert_read_only_op("get_adverts_v2_by_ids")
            sample = adv_ids[:5]
            try:
                campaigns_sample = await pm.get_adverts_v2_by_ids(sample)
                payload["http_attempt_count"] = 2
                payload["secondary_endpoint"] = "/adv/v2/adverts"
            except Exception as exc:  # noqa: BLE001
                gaps.append("get_adverts_v2_by_ids partial failure")
                payload["secondary_error"] = f"{type(exc).__name__}: {exc}"

        payload["campaigns_sample_meta"] = {
            "present": campaigns_sample is not None,
            "sample_size": min(5, adv_count),
        }
        payload["schema_fingerprint"] = _payload_fingerprint(payload)

        status = FamilyStatus.OK if adv_count > 0 and not gaps else FamilyStatus.PARTIAL
        if adv_count == 0:
            status = FamilyStatus.PARTIAL
            gaps.append("promotion_count returned zero adv ids")
            blockers.append("READ_ONLY_ENDPOINT_SEMANTICS_UNRESOLVED")

        payload["contract_blockers"] = blockers
        return FamilyResult(
            family=FamilyName.ADS,
            status=status,
            gaps=gaps,
            payload=payload,
            notes=["r04_003 PROMOTION_CAMPAIGNS_READ; no raw adv id list in RETURN"],
        )

    async def run_statistics(
        self, mode: Mode, ctx: dict[str, Any]
    ) -> FamilyResult:
        """PROMOTION_STATISTICS_READ — GET /adv/v3/fullstats (pre-bound advert)."""
        adv_ids_obj = ctx.get("adv_ids")
        adv_ids: list[int] = []
        if isinstance(adv_ids_obj, list):
            for item in cast(list[object], adv_ids_obj):
                if isinstance(item, int):
                    adv_ids.append(item)

        blockers: list[str] = []
        gaps: list[str] = []
        if not adv_ids:
            blockers.append("PREBOUND_ADVERT_ID_REQUIRED")
            return FamilyResult(
                family=FamilyName.ANALYTICS,
                status=FamilyStatus.FAILED,
                gaps=["no adv_ids from campaigns family"],
                payload={
                    "r04_003_family_id": FAMILY_STATISTICS,
                    "endpoint_or_report_alias": "/adv/v3/fullstats",
                    "method_class": "GET_READ",
                    "contract_blockers": blockers,
                    "http_attempt_count": 0,
                },
                notes=["r04_003: statistics requires pre-bound advertId"],
            )

        start, end = _moscow_period_dates()
        sample_id = adv_ids[0]
        id_binding_hash = hashlib.sha256(
            f"single_adv_probe|hash={sample_id}|family=STATS".encode()
        ).hexdigest()[:16]

        assert_read_only_op("get_full_adv_stat")
        pm = cast(Any, self._dm).promotion_manager
        try:
            stats = await pm.get_full_adv_stat(
                adv_ids=[sample_id],
                dates=[start, end],
            )
        except Exception as exc:  # noqa: BLE001
            blockers.extend(
                [
                    "READ_ONLY_ENDPOINT_SEMANTICS_UNRESOLVED",
                    "NO_OWNER_LOCAL_MAPPING_FOR_REQUIRED_DATASET",
                ]
            )
            return FamilyResult(
                family=FamilyName.ANALYTICS,
                status=FamilyStatus.FAILED,
                gaps=["get_full_adv_stat failed"],
                error=f"{type(exc).__name__}: {exc}",
                payload={
                    "r04_003_family_id": FAMILY_STATISTICS,
                    "endpoint_or_report_alias": "/adv/v3/fullstats",
                    "method_class": "GET_READ",
                    "contract_blockers": blockers,
                    "http_attempt_count": 1,
                    "period_semantics": f"{start.isoformat()}..{end.isoformat()}",
                },
            )

        stats_list = list(stats or [])
        payload: dict[str, object] = {
            "r04_003_family_id": FAMILY_STATISTICS,
            "endpoint_or_report_alias": "/adv/v3/fullstats",
            "method_class": "GET_READ",
            "authoritative_read_semantics_reference": (
                "local_adapter:fullstats→get_full_adv_stat"
            ),
            "period_semantics": f"{start.isoformat()}..{end.isoformat()}",
            "identifier_binding_alias_or_hash": (
                f"SINGLE_ADV_PROBE_COMMIT_{id_binding_hash}"
            ),
            "stats_rows_count": len(stats_list),
            "http_attempt_count": 1,
            "pagination_or_partition_rule": "31d_window_single_adv_probe",
            "completeness_limit": "single_advert_locked_period_probe",
        }
        payload["schema_fingerprint"] = _payload_fingerprint(payload)

        status = FamilyStatus.OK if stats_list else FamilyStatus.PARTIAL
        if not stats_list:
            gaps.append("fullstats returned empty for probe advert + period")
            blockers.append("READ_ONLY_ENDPOINT_SEMANTICS_UNRESOLVED")

        payload["contract_blockers"] = blockers
        return FamilyResult(
            family=FamilyName.ANALYTICS,
            status=status,
            gaps=gaps,
            payload=payload,
            notes=[
                "r04_003 PROMOTION_STATISTICS_READ; single-advert period probe",
                "no raw stats rows in RETURN",
            ],
        )

    async def run_cards_optional(
        self, mode: Mode, ctx: dict[str, Any]
    ) -> FamilyResult:
        """CONTENT_CARDS_READ — optional disclosed gap."""
        result = await self._hub.run_cards(mode, ctx)
        payload = dict(cast(dict[str, object], result.payload or {}))
        payload["r04_003_family_id"] = FAMILY_CARDS
        payload["disposition"] = "OPTIONAL_DISCLOSED_GAP"
        payload["schema_fingerprint"] = _payload_fingerprint(result.payload)
        gaps = list(result.gaps) + ["CONTENT_CARDS_OPTIONAL_DISCLOSED_GAP"]
        return FamilyResult(
            family=result.family,
            status=result.status,
            gaps=gaps,
            error=result.error,
            payload=payload,
            notes=list(result.notes) + ["optional family; gap disclosure allowed"],
        )

    async def run_all(
        self, mode: Mode, ctx: dict[str, Any]
    ) -> dict[str, FamilyResult]:
        """Прогнать mandatory + optional в фиксированном порядке."""
        results: dict[str, FamilyResult] = {}
        results[FAMILY_ORDERS] = await self.run_orders(mode, ctx)
        results[FAMILY_CAMPAIGNS] = await self.run_campaigns(mode, ctx)
        results[FAMILY_STATISTICS] = await self.run_statistics(mode, ctx)
        results[FAMILY_CARDS] = await self.run_cards_optional(mode, ctx)
        return results
