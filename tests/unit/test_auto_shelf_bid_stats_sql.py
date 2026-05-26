"""Unit-тесты контракта SQL агрегации точек ставки (без split по mode)."""

from __future__ import annotations

from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

_SQL_DIR = (
    Path(__file__).resolve().parents[2]
    / "app"
    / "modules"
    / "shop_runner"
    / "service_manager"
    / "services"
    / "auto_shelf_bid_control_manager"
    / "sql"
)


def test_get_bid_stats_dedup_groups_by_bid_not_mode() -> None:
    """Покрытые ставки: одна строка на bid_minor, не на mode."""
    sql = (_SQL_DIR / "get_bid_stats_dedup.sql").read_text(encoding="utf-8")
    assert "GROUP BY dedup.bid_minor, dedup.currency" in sql
    assert "GROUP BY dedup.bid_minor, dedup.currency, dedup.mode" not in sql
    assert "max(dedup.src_ts) AS last_interval_at" in sql
    assert "ORDER BY last_interval_at DESC" in sql


def test_get_best_bid_by_cart_cpa_groups_by_bid_not_mode() -> None:
    """Лучшая ставка: CPC по суммарной точке bid_minor."""
    sql = (_SQL_DIR / "get_best_bid_by_cart_cpa.sql").read_text(encoding="utf-8")
    assert "GROUP BY dedup.bid_minor, dedup.currency" in sql
    assert "GROUP BY dedup.bid_minor, dedup.currency, dedup.mode" not in sql


def test_get_best_bid_by_cart_cpa_uses_greatest_clicks_one() -> None:
    """0 кликов: CPC = spend/1, точка участвует в ранжировании."""
    sql = (_SQL_DIR / "get_best_bid_by_cart_cpa.sql").read_text(encoding="utf-8")
    assert "greatest(stats.clicks, 1)" in sql
    assert "greatest(stats.carts, 1)" not in sql
    assert "stats.carts > 0" not in sql


def test_get_best_bid_by_cart_cpa_supports_mode_filter() -> None:
    sql = (_SQL_DIR / "get_best_bid_by_cart_cpa.sql").read_text(encoding="utf-8")
    assert "%(mode)s IS NULL OR dedup.mode = %(mode)s" in sql


def test_get_best_bid_by_cart_cpa_supports_to_ts_window() -> None:
    """Предыдущий цикл: ``src_ts < to_ts``."""
    sql = (_SQL_DIR / "get_best_bid_by_cart_cpa.sql").read_text(encoding="utf-8")
    assert "%(to_ts)s IS NULL OR i.src_ts < %(to_ts)s" in sql
