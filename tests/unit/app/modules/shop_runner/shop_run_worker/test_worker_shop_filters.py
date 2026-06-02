"""Фильтры SHOP_* на уровне ShopWorker."""

from __future__ import annotations

import os
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.modules.shop_runner.shop_run_worker.worker.worker import ShopWorker


@pytest.mark.unit
@pytest.mark.asyncio
async def test_acquire_allowed_skips_excluded_and_removes_from_redis(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("SHOP_EXCLUDE_LIST", "bad_shop")
    monkeypatch.delenv("SHOP_FILTER_LIST", raising=False)

    redis_manager = MagicMock()
    redis_manager.get_next_free_shop_id = AsyncMock(
        side_effect=["bad_shop", "good_shop"]
    )
    redis_manager.remove_shops = AsyncMock()

    worker = ShopWorker(
        session=MagicMock(),
        tasks_manager=MagicMock(),
        plan_fact_reader=MagicMock(),
        redis_manager=redis_manager,
    )
    shop_id = await worker._acquire_allowed_free_shop_id(redis_manager)

    assert shop_id == "good_shop"
    redis_manager.remove_shops.assert_awaited_once_with(["bad_shop"])


@pytest.mark.unit
@pytest.mark.asyncio
async def test_acquire_allowed_respects_whitelist(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SHOP_FILTER_LIST", "only_shop")
    monkeypatch.delenv("SHOP_EXCLUDE_LIST", raising=False)

    redis_manager = MagicMock()
    redis_manager.get_next_free_shop_id = AsyncMock(
        side_effect=["other", "only_shop"]
    )
    redis_manager.remove_shops = AsyncMock()

    worker = ShopWorker(
        session=MagicMock(),
        tasks_manager=MagicMock(),
        plan_fact_reader=MagicMock(),
        redis_manager=redis_manager,
    )
    assert await worker._acquire_allowed_free_shop_id(redis_manager) == "only_shop"
