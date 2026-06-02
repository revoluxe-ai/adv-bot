"""Фильтрация shop_id при постановке магазинов в shop-runner.

Whitelist (``SHOP_FILTER_LIST``) и blacklist (``SHOP_EXCLUDE_LIST``) из settings:

- SQL: ``apply_shop_id_filters`` — PG при наполнении ``active_shops`` и legacy ``run_process_func``;
- Python: ``is_shop_id_allowed`` / ``filter_shop_ids`` — воркер ``ShopWorker``, ``run_shop_task``,
  snapshot ``RedisActiveShopIdDiscovery``.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence

from sqlalchemy import Select
from sqlalchemy.orm import InstrumentedAttribute
from sqlalchemy.sql.elements import ColumnElement

from app.settings import settings


def is_shop_id_allowed(shop_id: str) -> bool:
    """``True``, если магазин не отфильтрован whitelist/blacklist."""
    shop_filter_list = settings.SHOP_FILTER_LIST
    if shop_filter_list and shop_id not in shop_filter_list:
        return False
    shop_exclude_list = settings.SHOP_EXCLUDE_LIST
    if shop_exclude_list and shop_id in shop_exclude_list:
        return False
    return True


def filter_shop_ids(shop_ids: Iterable[str]) -> list[str]:
    """Оставляет только shop_id, проходящие ``is_shop_id_allowed``."""
    return [sid for sid in shop_ids if is_shop_id_allowed(sid)]


def apply_shop_id_filters(
    stmt: Select,
    shop_id_column: InstrumentedAttribute[str] | ColumnElement[str],
) -> Select:
    """Добавляет условия whitelist/blacklist к запросу shop_id.

    Args:
        stmt: SQLAlchemy Select с WBCabinet.shop_id.
        shop_id_column: Колонка shop_id (например, WBCabinet.shop_id).

    Returns:
        Тот же Select с дополнительными WHERE при непустых списках в settings.
    """
    shop_filter_list = settings.SHOP_FILTER_LIST
    if shop_filter_list:
        stmt = stmt.where(shop_id_column.in_(shop_filter_list))

    shop_exclude_list = settings.SHOP_EXCLUDE_LIST
    if shop_exclude_list:
        stmt = stmt.where(shop_id_column.not_in(shop_exclude_list))

    return stmt
