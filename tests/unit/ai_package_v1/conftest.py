"""Fixtures для unit-тестов ai_package_v1 campaign settings snapshot."""

from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace
from typing import Any
from unittest.mock import MagicMock

import pytest

from app.modules.ai_package_v1.export.campaign_settings_assembler import (
    CampaignSettingsAssembler,
)


def _enum_like(value: str) -> SimpleNamespace:
    return SimpleNamespace(value=value)


def make_adv_setting(**overrides: Any) -> MagicMock:
    """Создаёт mock AdvSetting с PG-like полями для assembler tests."""
    cabinet = SimpleNamespace(shop_id=overrides.pop("shop_id", "shop-1"))
    row = MagicMock()
    row.id = overrides.pop("adv_setting_id", 101)
    row.wb_cabinet = cabinet
    row.adv_id = overrides.pop("adv_id", 9001)
    row.search_adv_id = overrides.pop("search_adv_id", 9002)
    row.name = overrides.pop("name", "Test Campaign")
    row.active_status = overrides.pop("active_status", "active")
    row.nmids = overrides.pop("nmids", [111, 222])
    row.bot_active = overrides.pop("bot_active", False)
    row.bidder_active = overrides.pop("bidder_active", True)
    row.parsing_active = overrides.pop("parsing_active", False)
    row.wb_bid_type = overrides.pop("wb_bid_type", "manual")
    row.wb_placement_search = overrides.pop("wb_placement_search", True)
    row.wb_placement_recommendations = overrides.pop(
        "wb_placement_recommendations", False
    )
    row.last_update = overrides.pop("last_update", datetime(2026, 10, 1, tzinfo=UTC))
    row.auto_budget_watchdog_enabled = overrides.pop(
        "auto_budget_watchdog_enabled", True
    )
    row.auto_budget_daily_limit = overrides.pop("auto_budget_daily_limit", 1000)
    row.search_auto_budget_daily_limit = overrides.pop(
        "search_auto_budget_daily_limit", None
    )
    row.use_common_budget = overrides.pop("use_common_budget", False)
    row.common_budget_daily_limit = overrides.pop("common_budget_daily_limit", None)
    row.auto_budget_total_limit = overrides.pop("auto_budget_total_limit", None)
    row.search_auto_budget_total_limit = overrides.pop(
        "search_auto_budget_total_limit", None
    )
    row.common_budget_total_limit = overrides.pop("common_budget_total_limit", None)
    row.orders_source_for_auto_mode = overrides.pop(
        "orders_source_for_auto_mode", _enum_like("plan_fact")
    )
    row.plan_for_sales_for_day = overrides.pop("plan_for_sales_for_day", 10)
    row.target_price_for_order = overrides.pop("target_price_for_order", 500.0)
    row.max_price_for_order = overrides.pop("max_price_for_order", 800)
    row.sales_predict_method = overrides.pop(
        "sales_predict_method", _enum_like("linear")
    )
    row.strategy = overrides.pop("strategy", _enum_like("default"))
    row.auto_update_strategy = overrides.pop("auto_update_strategy", False)
    row.auto_shelf_bid_control_enabled = overrides.pop(
        "auto_shelf_bid_control_enabled", False
    )
    row.auto_shelf_bid_control_strategy = overrides.pop(
        "auto_shelf_bid_control_strategy", None
    )
    row.bidder_for_auto = overrides.pop("bidder_for_auto", True)
    row.max_cpm = overrides.pop("max_cpm", None)
    row.bidder_step = overrides.pop("bidder_step", 5)
    row.black_phrases = overrides.pop("black_phrases", [])
    row.relevant_phrases = overrides.pop("relevant_phrases", [])
    row.auto_update_minus_phrases = overrides.pop("auto_update_minus_phrases", False)
    row.auto_update_white_list = overrides.pop("auto_update_white_list", False)
    for key, value in overrides.items():
        setattr(row, key, value)
    return row


class FakeSettingsReader:
    """In-memory reader для assembler unit tests."""

    def __init__(self, rows: list[Any]) -> None:
        self._rows = rows
        self.load_calls: list[str] = []

    async def load_adv_settings(self, shop_id: str) -> list[Any]:
        self.load_calls.append(shop_id)
        return self._rows


@pytest.fixture
def fixed_clock() -> datetime:
    return datetime(2026, 10, 3, 12, 0, 0, tzinfo=UTC)


@pytest.fixture
def assembler_factory(fixed_clock: datetime):
    def _factory(rows: list[Any]) -> CampaignSettingsAssembler:
        return CampaignSettingsAssembler(
            reader=FakeSettingsReader(rows),
            clock=lambda: fixed_clock,
        )

    return _factory
