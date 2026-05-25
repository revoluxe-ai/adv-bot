"""Фильтрация shop_id при постановке магазинов в shop-runner.

Whitelist (SHOP_FILTER_LIST) и blacklist (SHOP_EXCLUDE_LIST) из settings
применяются к SQL Select по колонке WBCabinet.shop_id.
Используется legacy-раннером (run_process_func) и наполнением Redis для воркеров.
"""

from sqlalchemy import Select
from sqlalchemy.orm import InstrumentedAttribute
from sqlalchemy.sql.elements import ColumnElement

from app.settings import settings


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
