"""Diagnostic trace для ``update_cluster_bids`` (exact cell only).

Включается ``DEBUG_CLUSTER_BID_TRACE=1`` и env-фильтры по shop/adv/search_adv/nmid/ks/key.
При выключенном флаге или несовпадении ids — no-op. Бизнес-логику не меняет.
"""

from __future__ import annotations

import logging
import os
import re
from typing import Any

logger = logging.getLogger(__name__)

_TRACE_CONFIG: dict[str, Any] | None = None

_SENSITIVE_FIELD_RE = re.compile(
    r"(token|secret|password|authorization|api[_-]?key|bearer)",
    re.IGNORECASE,
)


def reset_trace_config_for_tests() -> None:
    """Сброс кеша env (только для unit-тестов)."""
    global _TRACE_CONFIG
    _TRACE_CONFIG = None


def _is_enabled() -> bool:
    return os.environ.get("DEBUG_CLUSTER_BID_TRACE", "").strip() == "1"


def _opt_int(name: str) -> int | None:
    raw = os.environ.get(name, "").strip()
    return int(raw) if raw.isdigit() else None


def _opt_str(name: str) -> str | None:
    raw = os.environ.get(name, "").strip()
    return raw if raw else None


def _load_config() -> dict[str, Any]:
    global _TRACE_CONFIG
    if _TRACE_CONFIG is not None:
        return _TRACE_CONFIG
    _TRACE_CONFIG = {
        "enabled": _is_enabled(),
        "shop_id": _opt_str("DEBUG_CLUSTER_BID_TRACE_SHOP_ID"),
        "adv_id": _opt_int("DEBUG_CLUSTER_BID_TRACE_ADV_ID"),
        "search_adv_id": _opt_int("DEBUG_CLUSTER_BID_TRACE_SEARCH_ADV_ID"),
        "nmid": _opt_int("DEBUG_CLUSTER_BID_TRACE_NMID"),
        "ks_id": _opt_int("DEBUG_CLUSTER_BID_TRACE_KS_ID"),
        "key": _opt_str("DEBUG_CLUSTER_BID_TRACE_KEY"),
    }
    return _TRACE_CONFIG


def is_trace_enabled() -> bool:
    """Быстрая проверка флага без сравнения ids (hot-path guard)."""
    return _load_config()["enabled"]


def trace_target_defaults() -> dict[str, Any]:
    """Значения env-фильтра для подстановки в trace-вызовы."""
    cfg = _load_config()
    if not cfg["enabled"]:
        return {}
    out: dict[str, Any] = {}
    for field in (
        "shop_id",
        "adv_id",
        "search_adv_id",
        "nmid",
        "ks_id",
        "key",
    ):
        value = cfg[field]
        if value is not None:
            out[field] = value
    return out


def is_trace_cell(
    *,
    shop_id: str | None = None,
    adv_id: int | None = None,
    search_adv_id: int | None = None,
    nmid: int | None = None,
    ks_id: int | None = None,
    key: str | None = None,
) -> bool:
    """True, если trace включён и все заданные в env поля совпали с аргументами."""
    cfg = _load_config()
    if not cfg["enabled"]:
        return False
    checks: list[tuple[str, Any, Any]] = [
        ("shop_id", cfg["shop_id"], shop_id),
        ("adv_id", cfg["adv_id"], adv_id),
        ("search_adv_id", cfg["search_adv_id"], search_adv_id),
        ("nmid", cfg["nmid"], nmid),
        ("ks_id", cfg["ks_id"], ks_id),
        ("key", cfg["key"], key.strip() if isinstance(key, str) else key),
    ]
    for _name, expected, actual in checks:
        if expected is None:
            continue
        if actual is None:
            return False
        if actual != expected:
            return False
    return True


def is_trace_bid_cell(
    *,
    shop_id: str | None,
    search_adv_id: int,
    nmid: int,
    key: str,
) -> bool:
    """Сопоставление CalculationInput/NewBid с env-фильтром exact cell.

    У DTO нет auto ``adv_id`` / ``ks_id`` — берём из env при проверке search/nmid/key.
    """
    defaults = trace_target_defaults()
    if not defaults:
        return False
    return is_trace_cell(
        shop_id=shop_id,
        adv_id=defaults.get("adv_id"),
        search_adv_id=search_adv_id,
        nmid=nmid,
        ks_id=defaults.get("ks_id"),
        key=key,
    )


def _sanitize_field(name: str, value: Any) -> str:
    if value is None:
        return "null"
    if _SENSITIVE_FIELD_RE.search(name):
        return "<redacted>"
    text = str(value)
    text = re.sub(
        r"(?i)(bearer|token|secret|api[_-]?key)\s*[=:]\s*\S+",
        r"\1=<redacted>",
        text,
    )
    if len(text) > 300:
        return text[:300] + "..."
    return text


def format_error_detail(exc: BaseException | None) -> str | None:
    """Краткий безопасный detail исключения без токенов."""
    if exc is None:
        return None
    detail = f"{type(exc).__name__}: {exc}"
    detail = re.sub(
        r"(?i)(bearer|token|secret|api[_-]?key)\s*[=:]\s*\S+",
        r"\1=<redacted>",
        detail,
    )
    if len(detail) > 300:
        return detail[:300] + "..."
    return detail


def log_cluster_bid_trace(
    *,
    step: str,
    shop_id: str | None = None,
    adv_id: int | None = None,
    search_adv_id: int | None = None,
    nmid: int | None = None,
    ks_id: int | None = None,
    key: str | None = None,
    **fields: Any,
) -> None:
    """Структурированный INFO-лог одной точки pipeline (только exact match)."""
    if not is_trace_cell(
        shop_id=shop_id,
        adv_id=adv_id,
        search_adv_id=search_adv_id,
        nmid=nmid,
        ks_id=ks_id,
        key=key,
    ):
        return
    parts: list[str] = ["[cluster_bid_trace]", f"step={step}"]
    if shop_id is not None:
        parts.append(f"shop_id={shop_id}")
    if adv_id is not None:
        parts.append(f"adv_id={adv_id}")
    if search_adv_id is not None:
        parts.append(f"search_adv_id={search_adv_id}")
    if nmid is not None:
        parts.append(f"nmid={nmid}")
    if ks_id is not None:
        parts.append(f"ks_id={ks_id}")
    if key is not None:
        parts.append(f"key={key}")
    for field_name, value in fields.items():
        parts.append(f"{field_name}={_sanitize_field(field_name, value)}")
    logger.info(" ".join(parts))
