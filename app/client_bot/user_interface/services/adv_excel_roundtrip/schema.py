"""Схема колонок Excel и whitelist редактируемых полей AdvSetting."""

from __future__ import annotations

from enum import Enum
import re
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
TECH_HEADER_RE = re.compile(r"(RO|EDIT)__([A-Za-z0-9_]+?)(?:__([^()]+))?$")

# Версия шаблона: при несовпадении импорт отклоняется.
# v2: EDIT-колонка агрессивности V3 — техключ ``aggressiveness`` (ранее ``v3_rollout_aggressiveness``).
# v3: добавлена EDIT-колонка для cap шагов калибратора V3 — ``keyword_calibration_max_step``.
# v4: добавлены колонки биддера полок ``auto_shelf_bid_control``.
# v5: EDIT-колонка ``substitute_fact_cpo_for_max`` (V3 Raise MAX).
# v7: ``automatic_version`` исключена из Excel (legacy DB-колонка; SoT — ``bot_active``).
EXCEL_TEMPLATE_VERSION = 7

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
        "max_cpc",
        "type",
    }
)

# Поля AdvSetting, доступные для правки из интерфейса РК (скаляры; без cpm — только через WB API)
EDITABLE_ADV_SETTING_COLUMNS: frozenset[str] = frozenset(
    {
        "bot_active",
        "auto_shelf_bid_control_enabled",
        "max_cpm",
        "min_views_for_ml_predict",
        "clusters_mode",
        "target_ctr_mode",
        "hide_small_query_keywords",
        "bidder_coroutine_type",
        "target_ctr_mode_strategy",
        "reset_place",
        "exponent_predict_ctr",
        "bidder_step",
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
        "auto_budget_daily_limit",
        "search_auto_budget_daily_limit",
        "use_common_budget",
        "common_budget_daily_limit",
        "auto_common_budget",
        "auto_add_only_relevant_phrase",
        "orders_source_for_auto_mode",
        "predict_ctr_mode",
        "sales_predict_method",
        "aggressiveness",
        "keyword_calibration_max_step",
        "white_list_mode",
        "individual_keywords_target_place_mode",
        "target_position_mode",
        "strategy",
        "auto_update_strategy",
        "updater_common_bid_in_search_adv_active_status",
        "use_incremental_stats",
        "max_place",
        "substitute_fact_cpo_for_max",
    }
)


EDITABLE_SHELF_BID_CONTROL_COLUMNS: tuple[str, ...] = (
    "auto_shelf_max_bid_rub",
    "auto_shelf_test_share",
    "auto_shelf_target_test_impressions",
    "auto_shelf_target_test_observation_minutes",
    "auto_shelf_min_bid_distance_rub",
)


def ordered_edit_fields() -> list[str]:
    """Порядок EDIT-колонок в Excel: AdvSetting, затем биддер полок."""
    return sorted(EDITABLE_ADV_SETTING_COLUMNS) + list(EDITABLE_SHELF_BID_CONTROL_COLUMNS)


def column_header(kind: ExcelColumnKind, field: str, suffix: str = "") -> str:
    tech = f"{kind}__{field}__{suffix}" if suffix else f"{kind}__{field}"
    title = display_name_for_field(field)
    return f"{title} ({tech})"


def technical_column_header(kind: ExcelColumnKind, field: str, suffix: str = "") -> str:
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
    m = TECH_HEADER_RE.search(name.strip())
    if m is None and name.strip().endswith(")"):
        left = name.rfind("(")
        if left >= 0:
            m = TECH_HEADER_RE.fullmatch(name[left + 1 : -1].strip())
    if m is None:
        return None, "", ""
    kind_raw = m.group(1).upper()
    field = m.group(2)
    suffix = (m.group(3) or "").strip()
    return kind_raw, field, suffix  # type: ignore[return-value]


def python_type_for_column(field: str) -> type | None:
    """Ожидаемый Python-тип значения колонки (для сериализации/валидации)."""
    shelf_types: dict[str, type] = {
        "auto_shelf_max_bid_rub": int,
        "auto_shelf_test_share": float,
        "auto_shelf_target_test_impressions": int,
        "auto_shelf_target_test_observation_minutes": int,
        "auto_shelf_min_bid_distance_rub": int,
    }
    if field in shelf_types:
        return shelf_types[field]
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


def enum_names_for_field(field: str) -> list[str]:
    ec = enum_class_for_field(field)
    if ec is None:
        return []
    return [x.name for x in ec]


_FIELD_DISPLAY_NAMES: dict[str, str] = {
    "excel_template_version": "Версия шаблона",
    "snapshot_at": "Дата снимка",
    "adv_setting_id": "Внутренний ID кампании",
    "adv_id": "ID единой ставки",
    "search_adv_id": "ID ручной ставки (поиск)",
    "nmid": "NMID",
    "offer_id": "Артикул продавца",
    "export_issue": "Проблема данных РК (выгрузка)",
    "fact_orders_per_day": "Факт заказов в день",
    "fact_cost_per_order": "Фактическая себестоимость заказа",
    "plan_orders_per_day": "План заказов в день",
    "plan_target_cost": "Плановая целевая себестоимость заказа",
    "plan_max_cost": "Плановая максимальная себестоимость заказа",
    "orders_dev_pct": "Отклонение по заказам, %",
    "cost_dev_pct": "Отклонение по себестоимости заказа, %",
    "deviation_score": "Итоговое отклонение, п.п.",
    "plan_for_sales_for_day": "План продаж в день",
    "target_price_for_order": "Целевая себестоимость",
    "max_price_for_order": "Максимальная себестоимость",
    "strategy": "Стратегия",
    "bot_active": "Бот включен",
    "auto_shelf_bid_control_enabled": "Управление ставкой полок",
    "auto_shelf_max_bid_rub": "Максимальная ставка полок, ₽",
    "auto_shelf_test_share": "Доля теста полок",
    "auto_shelf_target_test_impressions": "Показов на тест полок",
    "auto_shelf_target_test_observation_minutes": "Мин. минут теста полок",
    "auto_shelf_min_bid_distance_rub": "Шаг между тестовыми ставками полок, ₽",
    "max_cpm": "Максимальный CPM",
    "min_views_for_ml_predict": "Мин. просмотров для ML-прогноза",
    "clusters_mode": "Кластерный режим",
    "target_ctr_mode": "Режим целевого CTR",
    "hide_small_query_keywords": "Скрывать низкочастотные ключи",
    "bidder_coroutine_type": "Тип корутины биддера",
    "target_ctr_mode_strategy": "Стратегия режима целевого CTR",
    "reset_place": "Сброс позиции",
    "exponent_predict_ctr": "Экспонента прогноза CTR",
    "bidder_step": "Шаг биддера",
    "bidder_for_auto": "Биддер для авто",
    "auto_update_white_list": "Автообновление белого списка",
    "auto_budget_watchdog_enabled": "Контроль автобюджета",
    "auto_update_target_place": "Автообновление целевой позиции",
    "auto_update_exponent": "Автообновление экспоненты",
    "rec_system_mode": "Режим рекомендательной системы",
    "hide_zero_views_keywords": "Скрывать ключи без просмотров",
    "auto_budget_daily_limit": "Дневной лимит автобюджета",
    "search_auto_budget_daily_limit": "Дневной лимит автобюджета (поиск)",
    "use_common_budget": "Использовать общий бюджет",
    "common_budget_daily_limit": "Дневной лимит общего бюджета",
    "auto_common_budget": "Авторасчёт общего бюджета",
    "auto_add_only_relevant_phrase": "Добавлять только релевантные фразы",
    "orders_source_for_auto_mode": "Источник заказов для авто-режима",
    "predict_ctr_mode": "Режим прогноза CTR",
    "sales_predict_method": "Метод прогноза продаж",
    "aggressiveness": "V3: агрессивность раскрутки (1–3, вне полок)",
    "keyword_calibration_max_step": "V3: макс. шаг калибратора",
    "white_list_mode": "Режим белого списка",
    "individual_keywords_target_place_mode": "Режим целевой позиции по ключам",
    "target_position_mode": "Режим целевой позиции",
    "auto_update_strategy": "Автообновление стратегии",
    "updater_common_bid_in_search_adv_active_status": "Обновление общей ставки в поиске",
    "use_incremental_stats": "Использовать инкрементальную статистику",
    "max_place": "Максимальная позиция",
    "substitute_fact_cpo_for_max": "Авто max CPO (V3 Raise)",
}


def display_name_for_field(field: str) -> str:
    return _FIELD_DISPLAY_NAMES.get(field, field)


def serialize_cell_value(field: str, value: Any) -> Any:
    if value is None:
        return ""
    if field in EDITABLE_SHELF_BID_CONTROL_COLUMNS:
        return serialize_shelf_bid_control_cell(field, value)
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
    if field in EDITABLE_SHELF_BID_CONTROL_COLUMNS:
        return parse_shelf_bid_control_edit_value(field, raw)
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


def parse_shelf_bid_control_edit_value(field: str, raw: Any) -> Any:
    """Разобрать EDIT-значение для биддера полок."""
    if field not in EDITABLE_SHELF_BID_CONTROL_COLUMNS:
        raise ValueError(f"Неизвестное поле биддера полок: {field}")

    def _parse_positive_number(text_value: Any, *, integer_only: bool) -> int | float:
        if isinstance(text_value, bool):
            raise ValueError("Некорректное число")
        if isinstance(text_value, int | float):
            parsed_value = float(text_value)
        else:
            text = str(text_value).strip().replace(",", ".")
            if not text:
                raise ValueError("Пустое значение")
            parsed_value = float(text)
        if integer_only:
            value = int(parsed_value)
            if value <= 0:
                raise ValueError("Значение должно быть больше 0")
            return value
        if parsed_value <= 0:
            raise ValueError("Значение должно быть больше 0")
        return parsed_value

    if field in {"auto_shelf_max_bid_rub", "auto_shelf_min_bid_distance_rub"}:
        return int(_parse_positive_number(raw, integer_only=True)) * 100
    if field == "auto_shelf_target_test_impressions":
        return int(_parse_positive_number(raw, integer_only=True))
    if field == "auto_shelf_target_test_observation_minutes":
        value = int(_parse_positive_number(raw, integer_only=True))
        if value < 60:
            raise ValueError("Минимальное время теста должно быть не меньше 60 минут.")
        return value
    if field == "auto_shelf_test_share":
        parsed = _parse_positive_number(raw, integer_only=False)
        assert isinstance(parsed, float)
        if parsed > 1:
            parsed = parsed / 100
        if parsed <= 0 or parsed > 0.49:
            raise ValueError("Доля теста должна быть больше 0 и не больше 49%.")
        return float(parsed)
    raise ValueError(f"Неизвестное поле биддера полок: {field}")


def serialize_shelf_bid_control_cell(field: str, value: Any) -> Any:
    """Сериализовать значение биддера полок для Excel."""
    if value is None:
        return ""
    if field in {"auto_shelf_max_bid_rub", "auto_shelf_min_bid_distance_rub"}:
        return int(value) / 100
    if field == "auto_shelf_test_share":
        return float(value)
    return value
