"""Default family runners поверх existing WBManagerHub managers (без новых URL).

INC-RO-06/07: ORDERS_OR_SALES_REPORTS_READ → statistics-api GET supplier
orders + sales через ReportsManager (Stage A first page); не подменять
funnel/fullstats/FBS (decision orders-or-sales-reports-read-identity).
"""

from __future__ import annotations

import datetime as dt
from typing import Any, cast

from scripts.wb_api_readonly_ops.models import (
    ORDERS_PERIOD_DATE_FROM_DEFAULT,
    FamilyName,
    FamilyResult,
    FamilyStatus,
    Mode,
)
from scripts.wb_api_readonly_ops.mutation_guard import assert_read_only_op
from scripts.wb_api_readonly_ops.orchestrator import FamilyRunner


def _jsonable(value: object) -> object:
    """Грубое приведение ответа менеджера к JSON-safe структуре."""
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, list):
        return [_jsonable(v) for v in cast(list[object], value)]
    if isinstance(value, tuple):
        return [_jsonable(v) for v in cast(tuple[object, ...], value)]
    if isinstance(value, dict):
        mapping = cast(dict[object, object], value)
        return {str(k): _jsonable(v) for k, v in mapping.items()}
    to_dict = getattr(value, "to_dict", None)
    if callable(to_dict):
        try:
            return _jsonable(to_dict())
        except Exception:  # noqa: BLE001
            return str(value)
    raw_dict = getattr(value, "__dict__", None)
    if isinstance(raw_dict, dict):
        mapping2 = cast(dict[str, object], raw_dict)
        return {
            k: _jsonable(v) for k, v in mapping2.items() if not k.startswith("_")
        }
    return str(value)


class HubFamilyRunners:
    """Runners ORDERS/ads/cards/analytics/norms через WBDataManager stack."""

    def __init__(self, wb_data_manager: object) -> None:
        """Args: wb_data_manager — hub.wb_data_manager (existing stack)."""
        self._dm = wb_data_manager

    def as_dict(self) -> dict[FamilyName, FamilyRunner]:
        """Словарь runners для orchestrator (ORDERS первым в FAMILY_ORDER)."""
        return {
            FamilyName.ORDERS_OR_SALES_REPORTS_READ: (
                self.run_orders_or_sales_reports_read
            ),
            FamilyName.ADS: self.run_ads,
            FamilyName.CARDS: self.run_cards,
            FamilyName.ANALYTICS: self.run_analytics,
            FamilyName.NORMS: self.run_norms,
        }

    async def run_orders_or_sales_reports_read(
        self, mode: Mode, ctx: dict[str, Any]
    ) -> FamilyResult:
        """GET statistics-api supplier orders + sales (Stage A: dateFrom, one page each).

        Spec delta wb-api-read-only-preflight / INC-RO-07: оба GET обязательны;
        sales fail при OK orders → PARTIAL; orders fail → FAILED.
        Identity: только reports_manager get_supplier_orders/sales.
        Не funnel / fullstats / FBS (decision orders-or-sales-reports-read-identity).
        """
        assert_read_only_op("get_supplier_orders")
        assert_read_only_op("get_supplier_sales")
        _ = mode  # preflight и collect Stage A: одна first page на каждый GET
        date_from_raw = ctx.get("orders_date_from")
        if isinstance(date_from_raw, str) and date_from_raw.strip():
            date_from = date_from_raw.strip()
        else:
            date_from = ORDERS_PERIOD_DATE_FROM_DEFAULT.isoformat()

        dm = cast(Any, self._dm)
        reports_manager = getattr(dm, "reports_manager", None)
        attestation = {
            "date_from": date_from,
            "next_page_followed": "NO",
            "period_parameter_model": "DATE_FROM_CURSOR",
        }

        try:
            if reports_manager is not None:
                orders_raw = await reports_manager.get_supplier_orders(
                    date_from=date_from,
                    flag=0,
                )
            else:
                orders_raw = await dm.get_supplier_orders(
                    date_from=date_from, flag=0
                )
        except Exception as exc:  # noqa: BLE001
            return FamilyResult(
                family=FamilyName.ORDERS_OR_SALES_REPORTS_READ,
                status=FamilyStatus.FAILED,
                gaps=["get_supplier_orders failed"],
                error=f"{type(exc).__name__}: {exc}",
                payload={
                    "source": "statistics-api.supplier.orders_and_sales",
                    **attestation,
                    "orders": {
                        "source": "statistics-api.supplier.orders",
                        "rows_count": 0,
                        "rows": [],
                    },
                },
            )

        orders_list = list(orders_raw or [])
        gaps: list[str] = []
        if not orders_list:
            gaps.append("supplier orders first page empty for dateFrom window")

        sales_list: list[object] = []
        sales_error: str | None = None
        try:
            if reports_manager is not None:
                sales_raw = await reports_manager.get_supplier_sales(
                    date_from=date_from,
                    flag=0,
                )
            else:
                sales_raw = await dm.get_supplier_sales(
                    date_from=date_from, flag=0
                )
            sales_list = list(sales_raw or [])
        except Exception as exc:  # noqa: BLE001
            sales_error = f"{type(exc).__name__}: {exc}"
            gaps.append("get_supplier_sales failed")

        if not sales_error and not sales_list:
            gaps.append("supplier sales first page empty for dateFrom window")

        if sales_error:
            status = FamilyStatus.PARTIAL
        elif not orders_list or not sales_list:
            status = FamilyStatus.PARTIAL
        else:
            status = FamilyStatus.OK

        return FamilyResult(
            family=FamilyName.ORDERS_OR_SALES_REPORTS_READ,
            status=status,
            gaps=gaps,
            error=sales_error,
            payload={
                "source": "statistics-api.supplier.orders_and_sales",
                **attestation,
                "orders": {
                    "source": "statistics-api.supplier.orders",
                    "rows_count": len(orders_list),
                    "rows": _jsonable(orders_list[:20]),
                },
                "sales": {
                    "source": "statistics-api.supplier.sales",
                    "rows_count": len(sales_list),
                    "rows": _jsonable(sales_list[:20]),
                    **({"error": sales_error} if sales_error else {}),
                },
            },
            notes=[
                "Stage A: no lastChangeDate cursor follow",
                "funnel/fullstats/FBS MUST NOT satisfy this family",
                "INC-RO-07: orders+sales Stage A both required",
            ],
        )

    async def run_ads(self, mode: Mode, ctx: dict[str, Any]) -> FamilyResult:
        """Probe/collect рекламных кампаний (promotion count + optional v2 adverts)."""
        assert_read_only_op("get_cabinet_adv_ids")
        pm = cast(Any, self._dm).promotion_manager
        try:
            adv_ids_raw = await pm._client.promotion_count_adapter.get_cabinet_adv_ids()
            adv_ids = cast(list[int], list(adv_ids_raw))
        except Exception as exc:  # noqa: BLE001
            return FamilyResult(
                family=FamilyName.ADS,
                status=FamilyStatus.FAILED,
                gaps=["promotion_count get_cabinet_adv_ids failed"],
                error=f"{type(exc).__name__}: {exc}",
            )
        ctx["adv_ids"] = list(adv_ids)
        payload: dict[str, object] = {
            "adv_ids_count": len(adv_ids),
            "adv_ids": adv_ids[:50],
        }
        if mode == Mode.COLLECT and adv_ids:
            assert_read_only_op("get_adverts_v2_by_ids")
            sample = adv_ids[:20]
            try:
                campaigns = await pm.get_adverts_v2_by_ids(sample)
                payload["campaigns_sample"] = _jsonable(campaigns)
            except Exception as exc:  # noqa: BLE001
                return FamilyResult(
                    family=FamilyName.ADS,
                    status=FamilyStatus.PARTIAL,
                    gaps=["get_adverts_v2_by_ids partial failure"],
                    error=f"{type(exc).__name__}: {exc}",
                    payload=payload,
                )
        return FamilyResult(
            family=FamilyName.ADS,
            status=FamilyStatus.OK,
            payload=payload,
        )

    async def run_cards(self, mode: Mode, ctx: dict[str, Any]) -> FamilyResult:
        """Probe/collect карточек Content API."""
        assert_read_only_op("get_cards_list")
        from app.core.mp.wb.api.generated.products.v1.content_products_client.models import (
            PostContentV2GetCardsListBody,
            PostContentV2GetCardsListBodySettings,
            PostContentV2GetCardsListBodySettingsCursor,
            PostContentV2GetCardsListBodySettingsFilter,
            PostContentV2GetCardsListBodySettingsSort,
        )

        limit = 1 if mode == Mode.PREFLIGHT else 100
        filter_ = PostContentV2GetCardsListBodySettingsFilter(with_photo=-1)
        cursor = PostContentV2GetCardsListBodySettingsCursor(limit=limit)
        sort = PostContentV2GetCardsListBodySettingsSort(ascending=False)
        settings = PostContentV2GetCardsListBodySettings(
            filter_=filter_,
            cursor=cursor,
            sort=sort,
        )
        body = PostContentV2GetCardsListBody(settings=settings)
        products_manager = cast(Any, self._dm).products_manager
        try:
            response = await products_manager.get_cards_list(body=body)
        except Exception as exc:  # noqa: BLE001
            return FamilyResult(
                family=FamilyName.CARDS,
                status=FamilyStatus.FAILED,
                gaps=["get_cards_list failed"],
                error=f"{type(exc).__name__}: {exc}",
            )
        if response is None:
            return FamilyResult(
                family=FamilyName.CARDS,
                status=FamilyStatus.FAILED,
                gaps=["get_cards_list returned None"],
            )
        cards_obj = getattr(response, "cards", None)
        cards_list: list[object] = (
            list(cast(list[object], cards_obj)) if cards_obj else []
        )
        nmids: list[int] = []
        for card in cards_list:
            nmid = getattr(card, "nm_id", None)
            if nmid is None:
                nmid = getattr(card, "nmID", None)
            if nmid is not None:
                try:
                    nmids.append(int(nmid))
                except (TypeError, ValueError):
                    pass
        ctx["nmids"] = nmids
        sample_cards = cards_list[:10] if mode == Mode.COLLECT else cards_list[:1]
        return FamilyResult(
            family=FamilyName.CARDS,
            status=FamilyStatus.OK,
            payload={
                "cards_count": len(cards_list),
                "nmids": nmids,
                "cards": _jsonable(sample_cards),
            },
        )

    async def run_analytics(self, mode: Mode, ctx: dict[str, Any]) -> FamilyResult:
        """Funnel history read; требует nmid из cards (иначе PARTIAL/GAP)."""
        nmids_obj = ctx.get("nmids")
        nmids: list[int] = []
        if isinstance(nmids_obj, list):
            for item in cast(list[object], nmids_obj):
                if isinstance(item, int):
                    nmids.append(item)
                elif isinstance(item, str) and item.isdigit():
                    nmids.append(int(item))
        if not nmids:
            return FamilyResult(
                family=FamilyName.ANALYTICS,
                status=FamilyStatus.PARTIAL,
                gaps=["no nmids from cards — analytics probe skipped"],
                notes=["depends on cards family"],
            )
        assert_read_only_op("get_sales_funnel_products_history")
        end = dt.date.today()
        start = end - dt.timedelta(days=1)
        sample = nmids[:1] if mode == Mode.PREFLIGHT else nmids[:10]
        dm = cast(Any, self._dm)
        try:
            rows = await dm.get_sales_funnel_products_history(
                nmids=sample, start=start, end=end
            )
        except Exception as exc:  # noqa: BLE001
            return FamilyResult(
                family=FamilyName.ANALYTICS,
                status=FamilyStatus.FAILED,
                gaps=["get_sales_funnel_products_history failed"],
                error=f"{type(exc).__name__}: {exc}",
            )
        return FamilyResult(
            family=FamilyName.ANALYTICS,
            status=FamilyStatus.OK,
            payload={
                "nmids": sample,
                "start": start.isoformat(),
                "end": end.isoformat(),
                "rows": _jsonable(rows),
            },
        )

    async def run_norms(self, mode: Mode, ctx: dict[str, Any]) -> FamilyResult:
        """Subjects via promotion adapter; GAP for config/directories без адаптера."""
        assert_read_only_op("get_supplier_subjects")
        gaps = [
            "no domain adapter for GET /adv/v0/config (norms&limits)",
            "no domain adapter for content directories",
        ]
        pm = cast(Any, self._dm).promotion_manager
        try:
            subjects = await pm.get_supplier_subjects(payment_type="cpm")
        except Exception as exc:  # noqa: BLE001
            return FamilyResult(
                family=FamilyName.NORMS,
                status=FamilyStatus.FAILED,
                gaps=gaps + ["get_supplier_subjects failed"],
                error=f"{type(exc).__name__}: {exc}",
            )
        subjects_list = list(subjects or [])
        payload: dict[str, object] = {
            "subjects": _jsonable(subjects_list),
            "subjects_count": len(subjects_list),
        }
        _ = mode  # collect currently same probe depth for norms
        return FamilyResult(
            family=FamilyName.NORMS,
            status=FamilyStatus.PARTIAL,
            gaps=gaps,
            payload=payload,
            notes=["subjects OK; config/directories remain GAP"],
        )
