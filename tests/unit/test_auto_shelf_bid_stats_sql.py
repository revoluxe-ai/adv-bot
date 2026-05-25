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


def test_get_best_bid_by_cart_cpa_groups_by_bid_not_mode() -> None:
    """Лучшая ставка: CPA по суммарной точке bid_minor."""
    sql = (_SQL_DIR / "get_best_bid_by_cart_cpa.sql").read_text(encoding="utf-8")
    assert "GROUP BY dedup.bid_minor, dedup.currency" in sql
    assert "GROUP BY dedup.bid_minor, dedup.currency, dedup.mode" not in sql


def test_get_best_bid_by_cart_cpa_uses_min_one_cart_for_cpa() -> None:
    """0 корзин участвует в ранжировании с делителем 1."""
    sql = (_SQL_DIR / "get_best_bid_by_cart_cpa.sql").read_text(encoding="utf-8")
    assert "greatest(stats.carts, 1)" in sql
    assert "WHERE stats.carts > 0" not in sql
    assert "WHERE stats.impressions > 0" in sql
