"""Сбор строк для Excel по активным РК кабинета."""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import joinedload

from app.client_bot.user_interface.services.adv_excel_roundtrip.deviation import (
    compute_deviation_metrics,
)
from app.client_bot.user_interface.services.adv_excel_roundtrip.schema import (
    EXCEL_TEMPLATE_VERSION,
    column_header,
    edit_header,
    serialize_cell_value,
)
from app.modules.common_slaves.wildberries.models import AdvSetting, WBUserCabinet
from app.utils.db.session_maker import get_async_session_maker

logger = logging.getLogger(__name__)
_sm = get_async_session_maker


def _is_active_adv(a: AdvSetting) -> bool:
    """Совпадает с сортировкой в списке кампаний: активная + бот включён."""
    return bool(a.active_status and a.bot_active)


def _first_nmid(adv: AdvSetting) -> int | None:
    if not adv.nmids:
        return None
    return int(adv.nmids[0])


def _first_offer_id(adv: AdvSetting) -> str:
    for card in adv.wb_cards or []:
        if card.offer_id:
            return str(card.offer_id)
    return ""


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
    from app.client_bot.user_interface.services.adv_excel_roundtrip import schema as _schema

    return sorted(_schema.EDITABLE_ADV_SETTING_COLUMNS)


def _base_ro_columns() -> list[str]:
    return [
        column_header("RO", "excel_template_version"),
        column_header("RO", "snapshot_at"),
        column_header("RO", "adv_setting_id"),
        column_header("RO", "adv_id"),
        column_header("RO", "search_adv_id"),
        column_header("RO", "nmid"),
        column_header("RO", "offer_id"),
        column_header("RO", "fact_orders_per_day"),
        column_header("RO", "fact_cost_per_order"),
        column_header("RO", "plan_orders_per_day"),
        column_header("RO", "plan_target_cost"),
        column_header("RO", "plan_max_cost"),
        column_header("RO", "orders_dev_pct"),
        column_header("RO", "cost_dev_pct"),
        column_header("RO", "deviation_score"),
    ]


async def build_adv_excel_export(
    *,
    wb_user_cabinet_id: int,
) -> tuple[list[str], list[dict[str, Any]]]:
    """Вернуть (headers, rows) для выгрузки активных РК кабинета пользователя."""
    async with _sm(read_only=True) as session:
        stmt = (
            select(WBUserCabinet)
            .options(joinedload(WBUserCabinet.wb_cabinet))
            .where(WBUserCabinet.id == wb_user_cabinet_id)
        )
        wuc = (await session.execute(stmt)).scalar_one_or_none()
        if not wuc:
            raise ValueError("WBUserCabinet not found")
        cab_id = wuc.wb_cabinet_id

        stmt_adv = (
            select(AdvSetting)
            .options(joinedload(AdvSetting.wb_cards))
            .where(AdvSetting.wb_cabinet_id == cab_id)
        )
        advs = list((await session.execute(stmt_adv)).scalars().unique().all())

    active = [a for a in advs if _is_active_adv(a)]
    headers = _base_ro_columns() + [edit_header(f) for f in _ordered_edit_fields()]

    rows: list[dict[str, Any]] = []
    now = datetime.now(UTC).isoformat()
    for adv in active:
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
        row: dict[str, Any] = {
            column_header("RO", "excel_template_version"): EXCEL_TEMPLATE_VERSION,
            column_header("RO", "snapshot_at"): now,
            column_header("RO", "adv_setting_id"): adv.id,
            column_header("RO", "adv_id"): adv.adv_id if adv.adv_id is not None else "",
            column_header("RO", "search_adv_id"): adv.search_adv_id or "",
            column_header("RO", "nmid"): nmid if nmid is not None else "",
            column_header("RO", "offer_id"): _first_offer_id(adv),
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
            row[edit_header(field)] = serialize_cell_value(field, getattr(adv, field))
        rows.append(row)

    return headers, rows
