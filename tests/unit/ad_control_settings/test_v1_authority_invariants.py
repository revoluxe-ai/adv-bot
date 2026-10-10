"""Инварианты Task 4.1: нет Apply, allocator, funnel и catalog CPO."""

from __future__ import annotations

from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

_ROOT = Path(__file__).resolve().parents[3]
_PATHS = [
    _ROOT / "app" / "modules" / "ad_control_settings" / "runtime",
    _ROOT
    / "app"
    / "modules"
    / "shop_runner"
    / "hierarchical_ad_control_diagnostics.py",
]
_FORBIDDEN = (
    "ApplyManager",
    "apply_changeset",
    "validate_ad_control_changeset",
    "ProductCpoResolver",
    "wb_common_stat",
    "HeadroomAllocator",
    "get_supplier_sales",
    "finishedPrice",
    "finished_price",
    "totalPrice",
)


def test_runtime_sources_do_not_import_forbidden_authorities() -> None:
    """Исходники 4.1 не подключают Apply, funnel, catalog CPO и чужие цены."""
    offenders: list[str] = []
    for path in _PATHS:
        files = [path] if path.is_file() else sorted(path.rglob("*.py"))
        for file_path in files:
            text = file_path.read_text(encoding="utf-8")
            for token in _FORBIDDEN:
                if token in text:
                    offenders.append(f"{file_path.name}:{token}")
    assert offenders == []


def test_supplier_orders_symbol_is_present_once_per_shop_helper() -> None:
    """Провайдер ходит в get_supplier_orders, не в sales."""
    provider = (
        _ROOT / "app" / "modules" / "ad_control_settings" / "runtime" / "providers.py"
    ).read_text(encoding="utf-8")
    assert "get_supplier_orders" in provider
    assert "full_adv_wb_stat" in provider
    assert "campaign_settings_history" in provider
    assert "shop_campaign_inventory" in provider
