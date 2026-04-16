"""Схема колонок Excel и whitelist редактируемых полей AdvSetting."""

from __future__ import annotations

from enum import Enum
from typing import Any, Literal

from sqlalchemy import Boolean, Enum as SAEnumColumn, Float, Integer, String
from sqlalchemy.dialects.postgresql import JSONB
from app.modules.common_slaves.wildberries.models.enums import (
    OrdersSourceForAutoMode,
    TargetPositionMode,
)
from app.modules.common_slaves.wildberries.models.fact_methods_enum import FactMethods
from app.modules.common_slaves.wildberries.models.models import (
    AdvSetting,
    BidderCoroutineType,
    BidderMode,
    PredictCTRMode,
    Strategy,
    WhiteListMode,
)

ExcelColumnKind = Literal["RO", "EDIT"]

# Версия шаблона: при несовпадении импорт отклоняется
EXCEL_TEMPLATE_VERSION = 1

# Поля, которые нельзя менять через Excel (идентификаторы, синхронизация WB, JSON-списки)
READ_ONLY_ADV_COLUMNS: frozenset[str] = frozenset(
    {
        "id",
        "wb_cabinet_id",
        "adv_id",
        "_search_adv_id",
        "name",
        "active_status",
        "nmids",
        "black_phrases",
        "relevant_phrases",
        "last_update",
        "hard_min_ctr",
        "cpm",
        "type",
    }
)

# Поля AdvSetting, доступные для правки из интерфейса РК (скаляры; без cpm — только через WB API)
EDITABLE_ADV_SETTING_COLUMNS: frozenset[str] = frozenset(
    {
        "bot_active",
        "parsing_active",
        "pass_days",
        "boost",
        "max_cpc",
        "max_cpm",
        "min_views_for_ml_predict",
        "clusters_mode",
        "target_ctr_mode",
        "hide_small_query_keywords",
        "bidder_coroutine_type",
        "target_ctr_mode_strategy",
        "new_auto_min_ctr_mode",
        "reset_place",
        "exponent_predict_ctr",
        "bidder_step",
        "auction_boost_all_phrase_mode",
        "plan_for_sales_for_day",
        "target_price_for_order",
        "max_price_for_order",
        "bidder_for_auto",
        "auto_update_white_list",
        "auto_budget_watchdog_enabled",
        "auto_update_target_place",
        "auto_update_exponent",
        "rec_system_mode",
        "hide_zero_views_keywords",
        "max_balance_adding_for_day",
        "auto_budget_daily_limit",
        "search_auto_budget_daily_limit",
        "use_common_budget",
        "common_budget_daily_limit",
        "auto_adv_target_status",
        "auction_adv_target_status",
        "auto_add_only_relevant_phrase",
        "orders_source_for_auto_mode",
        "predict_ctr_mode",
        "sales_predict_method",
        "automatic_version",
        "white_list_mode",
        "individual_keywords_target_place_mode",
        "min_target_position",
        "target_position_mode",
        "strategy",
        "auto_update_strategy",
        "updater_common_bid_in_search_adv_active_status",
        "bidder_mode",
        "use_incremental_stats",
        "min_block_position",
        "max_place",
    }
)


def column_header(kind: ExcelColumnKind, field: str, suffix: str = "") -> str:
    if suffix:
        return f"{kind}__{field}__{suffix}"
    return f"{kind}__{field}"


def header_type_suffix(field: str) -> str:
    """Суффикс типа для заголовка EDIT (BOOL|INT|FLOAT|ENUM)."""
    py_t = python_type_for_column(field)
    ec = enum_class_for_field(field)
    if ec is not None:
        return "ENUM"
    if py_t is bool:
        return "BOOL"
    if py_t is int:
        return "INT"
    if py_t is float:
        return "FLOAT"
    return "STR"


def edit_header(field: str) -> str:
    return column_header("EDIT", field, header_type_suffix(field))


def parse_header(name: str) -> tuple[ExcelColumnKind | None, str, str]:
    """Разбор заголовка RO__field или EDIT__field__TYPE."""
    parts = name.split("__")
    if len(parts) < 2:
        return None, "", ""
    kind_raw = parts[0].upper()
    if kind_raw not in ("RO", "EDIT"):
        return None, "", ""
    field = parts[1]
    suffix = "__".join(parts[2:]) if len(parts) > 2 else ""
    return kind_raw, field, suffix  # type: ignore[return-value]


def python_type_for_column(field: str) -> type | None:
    """Ожидаемый Python-тип значения колонки (для сериализации/валидации)."""
    mapper = AdvSetting.__mapper__
    col = mapper.columns.get(field)
    if col is None:
        return None
    t = col.type
    if isinstance(t, Boolean):
        return bool
    if isinstance(t, Integer):
        return int
    if isinstance(t, Float):
        return float
    if isinstance(t, SAEnumColumn):
        return str  # имя enum
    if isinstance(t, String):
        return str
    if isinstance(t, JSONB):
        return None
    return str


def enum_class_for_field(field: str) -> type[Enum] | None:
    mapping: dict[str, type[Enum]] = {
        "orders_source_for_auto_mode": OrdersSourceForAutoMode,
        "predict_ctr_mode": PredictCTRMode,
        "sales_predict_method": FactMethods,
        "white_list_mode": WhiteListMode,
        "target_position_mode": TargetPositionMode,
        "strategy": Strategy,
        "bidder_mode": BidderMode,
        "bidder_coroutine_type": BidderCoroutineType,
    }
    return mapping.get(field)


def serialize_cell_value(field: str, value: Any) -> Any:
    if value is None:
        return ""
    ec = enum_class_for_field(field)
    if ec is not None and isinstance(value, Enum):
        return value.name
    if isinstance(value, bool):
        return "TRUE" if value else "FALSE"
    return value


def parse_bool_cell(raw: Any) -> bool:
    if isinstance(raw, bool):
        return raw
    s = str(raw).strip().upper()
    if s == "TRUE":
        return True
    if s == "FALSE":
        return False
    raise ValueError(f"Ожидалось TRUE или FALSE, получено: {raw!r}")


def parse_edit_value(field: str, raw: Any) -> Any:
    if raw is None or (isinstance(raw, float) and str(raw) == "nan"):
        raise ValueError("Пустая ячейка")
    py_t = python_type_for_column(field)
    ec = enum_class_for_field(field)
    if ec is not None:
        s = str(raw).strip()
        try:
            return ec[s]  # by name
        except KeyError as e:
            valid = ", ".join(sorted(x.name for x in ec))
            raise ValueError(f"Недопустимое значение enum {field}: {raw!r}. Допустимо: {valid}") from e

    if py_t is bool:
        return parse_bool_cell(raw)

    if py_t is int:
        if isinstance(raw, bool):
            raise ValueError("Некорректное целое")
        if isinstance(raw, int | float):
            return int(raw)
        s = str(raw).strip().replace(",", ".")
        if not s:
            raise ValueError("Пустое значение")
        return int(float(s))

    if py_t is float:
        if isinstance(raw, bool):
            raise ValueError("Некорректное число")
        if isinstance(raw, int | float):
            return float(raw)
        s = str(raw).strip().replace(",", ".")
        if not s:
            raise ValueError("Пустое значение")
        return float(s)

    return str(raw).strip()
