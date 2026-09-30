"""Сбор строк для Excel по активным РК кабинета."""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any, Awaitable, Callable

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.client_bot.user_interface.services.adv_excel_roundtrip.active_adv import (
    is_active_adv,
)
from app.client_bot.user_interface.services.adv_excel_roundtrip.deviation import (
    compute_deviation_metrics,
)
from app.client_bot.user_interface.services.adv_excel_roundtrip.schema import (
    EXCEL_TEMPLATE_VERSION,
    EDITABLE_SHELF_BID_CONTROL_COLUMNS,
    column_header,
    edit_header,
    ordered_edit_fields,
    serialize_cell_value,
    serialize_shelf_bid_control_cell,
)
from app.client_bot.user_interface.services.total_spend_snapshot import (
    TotalSpendSnapshot,
    load_total_spend_snapshot,
    spend_excel_cell_value,
)
from app.modules.common_slaves.wildberries.models import AdvSetting, WBCard, WBUserCabinet
from app.modules.common_slaves.wildberries.models.auto_shelf_bid_control import (
    AutoShelfBidControlSettings,
)
from app.utils.db.session_maker import get_async_session_maker

logger = logging.getLogger(__name__)
_sm = get_async_session_maker
ProgressCallback = Callable[[int, int], Awaitable[None] | None]


def _first_nmid(adv: AdvSetting) -> int | None:
    if not adv.nmids:
        return None
    return int(adv.nmids[0])


def _offer_id_and_export_issue(
    adv: AdvSetting, *, first_nmid: int | None, offer_by_nmid: dict[int, str]
) -> tuple[str, str]:
    """Возвращает offer_id и текст проблемы для экспорта (если есть).

    Важно: экспорт не должен падать из-за одной РК с неполными данными.
    """
    if first_nmid is None:
        issue = "Нет NMID: offer_id недоступен"
        logger.warning("adv excel: missing first NMID adv_setting_id=%s", adv.id)
        return "", issue
    offer_id = offer_by_nmid.get(int(first_nmid))
    if not offer_id:
        issue = f"Нет WBCard.offer_id по NMID={first_nmid}"
        logger.warning(
            "adv excel: missing offer_id adv_setting_id=%s nmid=%s", adv.id, first_nmid
        )
        return "", issue
    return offer_id, ""


def _first_offer_id_from_nmid(
    adv: AdvSetting, *, first_nmid: int | None, offer_by_nmid: dict[int, str]
) -> str:
    """Backward-compatible helper used by unit tests.

    Historical contract: return offer_id or raise ValueError when it's unavailable.
    """
    offer_id, _issue = _offer_id_and_export_issue(
        adv, first_nmid=first_nmid, offer_by_nmid=offer_by_nmid
    )
    if not offer_id:
        raise ValueError("offer_id is unavailable for the provided NMID")
    return offer_id


# Имя удерживается для unit-import; сам helper вызывается только из tests/.
_UNIT_TEST_EXPORTS = (_first_offer_id_from_nmid,)


async def _fact_snapshot(adv: AdvSetting) -> tuple[float | None, float | None]:
    """Факт: прогноз заказов/день и себестоимость заказа (как в PlanFact)."""
    if not adv.nmids:
        return None, None
    try:
        # Ленивый импорт — избегаем циклических зависимостей при загрузке пакета
        from app.modules.common_advs_stat.data_manager import CommonAdvsStatDataManager
        from app.modules.plan_fact.provider import PlanFactProvider

        mgr = CommonAdvsStatDataManager()
        stat = await mgr.get_data(adv, [], last_days=2)
        provider = PlanFactProvider(adv)
        fact = await provider.get_fact_data(stat)
        return fact.predict_orders, fact.pay_for_order
    except Exception:
        logger.exception("adv excel: fact snapshot failed adv_setting_id=%s", adv.id)
        return None, None


def _ordered_edit_fields() -> list[str]:
    return ordered_edit_fields()


def _base_ro_columns() -> list[str]:
    return [
        column_header("RO", "excel_template_version"),
        column_header("RO", "snapshot_at"),
        column_header("RO", "adv_setting_id"),
        column_header("RO", "adv_id"),
        column_header("RO", "search_adv_id"),
        column_header("RO", "nmid"),
        column_header("RO", "offer_id"),
        column_header("RO", "export_issue"),
        column_header("RO", "fact_orders_per_day"),
        column_header("RO", "fact_cost_per_order"),
        column_header("RO", "plan_orders_per_day"),
        column_header("RO", "plan_target_cost"),
        column_header("RO", "plan_max_cost"),
        column_header("RO", "orders_dev_pct"),
        column_header("RO", "cost_dev_pct"),
        column_header("RO", "deviation_score"),
    ]


_TOTAL_SPEND_RO_AFTER_EDIT: dict[str, str] = {
    "auto_budget_total_limit": "total_spend_auto",
    "search_auto_budget_total_limit": "total_spend_search",
    "common_budget_total_limit": "total_spend_common",
}


def _export_headers() -> list[str]:
    """RO-колонки и EDIT с RO расхода сразу после абсолютных лимитов."""
    headers: list[str] = _base_ro_columns()
    for field in _ordered_edit_fields():
        headers.append(edit_header(field))
        ro_field = _TOTAL_SPEND_RO_AFTER_EDIT.get(field)
        if ro_field is not None:
            headers.append(column_header("RO", ro_field))
    return headers


def _total_spend_for_ro_field(
    ro_field: str, snapshot: TotalSpendSnapshot
) -> int | str:
    if ro_field == "total_spend_auto":
        return spend_excel_cell_value(snapshot.auto)
    if ro_field == "total_spend_search":
        return spend_excel_cell_value(snapshot.search)
    if ro_field == "total_spend_common":
        return spend_excel_cell_value(snapshot.common)
    return ""


async def build_adv_excel_export(
    *,
    wb_user_cabinet_id: int,
    progress_callback: ProgressCallback | None = None,
) -> tuple[list[str], list[dict[str, Any]]]:
    """Открыть read-only PG-сессию и собрать выгрузку активных РК кабинета."""
    async with _sm(read_only=True) as session:
        return await build_adv_excel_export_in_session(
            session,
            wb_user_cabinet_id=wb_user_cabinet_id,
            progress_callback=progress_callback,
        )


async def build_adv_excel_export_in_session(
    session: AsyncSession,
    *,
    wb_user_cabinet_id: int,
    progress_callback: ProgressCallback | None = None,
) -> tuple[list[str], list[dict[str, Any]]]:
    """Собрать export rows из уже открытой PG-сессии без создания own session."""
    stmt = (
        select(WBUserCabinet)
        .options(joinedload(WBUserCabinet.wb_cabinet))
        .where(WBUserCabinet.id == wb_user_cabinet_id)
    )
    wuc = (await session.execute(stmt)).scalar_one_or_none()
    if not wuc:
        raise ValueError("WBUserCabinet not found")
    cab_id = wuc.wb_cabinet_id

    stmt_adv = select(AdvSetting).where(AdvSetting.wb_cabinet_id == cab_id)
    advs = list((await session.execute(stmt_adv)).scalars().unique().all())
    nmids_for_lookup: set[int] = set()
    for adv in advs:
        nmid = _first_nmid(adv)
        if nmid is not None:
            nmids_for_lookup.add(int(nmid))

    offer_by_nmid: dict[int, str] = {}
    if nmids_for_lookup:
        stmt_cards = select(WBCard.nmid, WBCard.offer_id).where(
            WBCard.nmid.in_(nmids_for_lookup)
        )
        for nmid, offer_id in (await session.execute(stmt_cards)).all():
            if offer_id:
                offer_by_nmid[int(nmid)] = str(offer_id)

    shelf_settings_by_nmid: dict[int, AutoShelfBidControlSettings] = {}
    if nmids_for_lookup:
        stmt_shelf = select(AutoShelfBidControlSettings).where(
            AutoShelfBidControlSettings.nmid.in_(nmids_for_lookup)
        )
        for settings in (await session.execute(stmt_shelf)).scalars().all():
            shelf_settings_by_nmid[int(settings.nmid)] = settings

    active = [a for a in advs if is_active_adv(a)]
    headers = _export_headers()

    rows: list[dict[str, Any]] = []
    now = datetime.now(UTC).isoformat()
    total = len(active)
    for idx, adv in enumerate(active, start=1):
        fact_o, fact_cost = await _fact_snapshot(adv)
        plan_orders = adv.plan_for_sales_for_day
        target_c = adv.target_price_for_order
        max_c = adv.max_price_for_order
        dev = compute_deviation_metrics(
            fact_orders_per_day=fact_o,
            plan_orders_per_day=plan_orders,
            fact_cost_per_order=fact_cost,
            target_cost_per_order=target_c,
        )
        nmid = _first_nmid(adv)
        offer_id, export_issue = _offer_id_and_export_issue(
            adv, first_nmid=nmid, offer_by_nmid=offer_by_nmid
        )
        shelf_settings: AutoShelfBidControlSettings | None = None
        if nmid is not None and len(adv.nmids or []) == 1:
            shelf_settings = shelf_settings_by_nmid.get(int(nmid))
        total_spend = await load_total_spend_snapshot(adv)
        row: dict[str, Any] = {
            column_header("RO", "excel_template_version"): EXCEL_TEMPLATE_VERSION,
            column_header("RO", "snapshot_at"): now,
            column_header("RO", "adv_setting_id"): adv.id,
            column_header("RO", "adv_id"): adv.adv_id,
            column_header("RO", "search_adv_id"): adv.search_adv_id or "",
            column_header("RO", "nmid"): nmid if nmid is not None else "",
            column_header("RO", "offer_id"): offer_id,
            column_header("RO", "export_issue"): export_issue,
            column_header("RO", "fact_orders_per_day"): fact_o if fact_o is not None else "",
            column_header("RO", "fact_cost_per_order"): fact_cost if fact_cost is not None else "",
            column_header("RO", "plan_orders_per_day"): plan_orders if plan_orders is not None else "",
            column_header("RO", "plan_target_cost"): target_c if target_c is not None else "",
            column_header("RO", "plan_max_cost"): max_c if max_c is not None else "",
            column_header("RO", "orders_dev_pct"): dev.orders_dev_pct
            if dev.orders_dev_pct is not None
            else "",
            column_header("RO", "cost_dev_pct"): dev.cost_dev_pct
            if dev.cost_dev_pct is not None
            else "",
            column_header("RO", "deviation_score"): dev.deviation_score
            if dev.deviation_score is not None
            else "",
        }
        for field in _ordered_edit_fields():
            if field in EDITABLE_SHELF_BID_CONTROL_COLUMNS:
                if shelf_settings is None:
                    row[edit_header(field)] = ""
                    continue
                value_by_field = {
                    "auto_shelf_max_bid_rub": shelf_settings.max_bid_minor,
                    "auto_shelf_test_share": shelf_settings.test_share,
                    "auto_shelf_target_test_impressions": shelf_settings.target_test_impressions,
                    "auto_shelf_target_test_observation_minutes": shelf_settings.target_test_observation_minutes,
                    "auto_shelf_min_bid_distance_rub": shelf_settings.min_bid_distance_minor,
                }
                row[edit_header(field)] = serialize_shelf_bid_control_cell(
                    field, value_by_field[field]
                )
                continue
            row[edit_header(field)] = serialize_cell_value(field, getattr(adv, field))
            ro_field = _TOTAL_SPEND_RO_AFTER_EDIT.get(field)
            if ro_field is not None:
                row[column_header("RO", ro_field)] = _total_spend_for_ro_field(
                    ro_field, total_spend
                )
        rows.append(row)
        if progress_callback is not None:
            awaitable = progress_callback(idx, total)
            if awaitable is not None:
                await awaitable

    return headers, rows
