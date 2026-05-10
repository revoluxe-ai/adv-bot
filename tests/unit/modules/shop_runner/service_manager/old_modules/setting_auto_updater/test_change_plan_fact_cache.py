"""Unit tests for ChangePlanFact Redis guard."""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock, PropertyMock, patch

import pytest

from app.modules.common_slaves.wildberries.models.fact_methods_enum import FactMethods
from app.modules.shop_runner.service_manager.old_modules.setting_auto_updater.data_classes import (
    FactData,
    PlanData,
)
from app.modules.shop_runner.service_manager.old_modules.setting_auto_updater.plan_fact_change_redis_caches import (
    ChangePlanFact,
)

pytestmark = pytest.mark.unit


def _patch_client(redis_like: MagicMock):
    return patch.object(ChangePlanFact, "client", new_callable=PropertyMock, return_value=redis_like)


def _sample_plan_fact() -> tuple[PlanData, FactData]:
    plan = PlanData(orders=10, target_pay_for_order=100, max_pay_for_order=300)
    fact = FactData(
        predict_orders=5.0,
        pay_for_order=150.0,
        original_orders=5,
        fact_method=FactMethods.DIRECT_SALES,
    )
    return plan, fact


@pytest.mark.asyncio
async def test_check_equal_in_cache_returns_false_when_missing_key() -> None:
    adv = MagicMock()
    adv.adv_id = 99
    redis_like = MagicMock()
    redis_like.get = AsyncMock(return_value=None)
    with _patch_client(redis_like):
        cache = ChangePlanFact(adv)
        plan, fact = _sample_plan_fact()
        assert await cache.check_equal_in_cache(plan, fact) is False


@pytest.mark.asyncio
async def test_check_equal_in_cache_handles_str_payload() -> None:
    adv = MagicMock()
    adv.adv_id = 3
    plan, fact = _sample_plan_fact()
    plan_json = json.dumps(plan.model_dump(mode="json"))
    fact_json = json.dumps(fact.model_dump(mode="json"))
    raw = f"{plan_json}|{fact_json}"
    redis_like = MagicMock()
    redis_like.get = AsyncMock(return_value=raw)
    with _patch_client(redis_like):
        cache = ChangePlanFact(adv)
        assert await cache.check_equal_in_cache(plan, fact) is True


@pytest.mark.asyncio
async def test_check_equal_in_cache_handles_bytes_payload() -> None:
    adv = MagicMock()
    adv.adv_id = 4
    plan, fact = _sample_plan_fact()
    plan_json = json.dumps(plan.model_dump(mode="json"))
    fact_json = json.dumps(fact.model_dump(mode="json"))
    raw = f"{plan_json}|{fact_json}".encode()
    redis_like = MagicMock()
    redis_like.get = AsyncMock(return_value=raw)
    with _patch_client(redis_like):
        cache = ChangePlanFact(adv)
        assert await cache.check_equal_in_cache(plan, fact) is True


@pytest.mark.asyncio
async def test_check_equal_in_cache_returns_false_on_corrupt_pipe() -> None:
    adv = MagicMock()
    adv.adv_id = 5
    redis_like = MagicMock()
    redis_like.get = AsyncMock(return_value="no_pipe_separator")
    with _patch_client(redis_like):
        cache = ChangePlanFact(adv)
        plan, fact = _sample_plan_fact()
        assert await cache.check_equal_in_cache(plan, fact) is False


@pytest.mark.asyncio
async def test_check_equal_in_cache_returns_false_when_fact_pay_changed() -> None:
    adv = MagicMock()
    adv.adv_id = 6
    plan, fact_old = _sample_plan_fact()
    _, fact_new = _sample_plan_fact()
    fact_new = fact_new.model_copy(update={"pay_for_order": 999.0})
    plan_json = json.dumps(plan.model_dump(mode="json"))
    fact_json = json.dumps(fact_old.model_dump(mode="json"))
    raw = f"{plan_json}|{fact_json}"
    redis_like = MagicMock()
    redis_like.get = AsyncMock(return_value=raw)
    with _patch_client(redis_like):
        cache = ChangePlanFact(adv)
        assert await cache.check_equal_in_cache(plan, fact_new) is False


@pytest.mark.asyncio
async def test_set_new_plan_fact_writes_pipe_separated_json() -> None:
    adv = MagicMock()
    adv.adv_id = 8
    redis_like = MagicMock()
    redis_like.set = AsyncMock()
    with _patch_client(redis_like):
        cache = ChangePlanFact(adv)
        plan, fact = _sample_plan_fact()
        await cache.set_new_plan_fact(plan, fact)
    redis_like.set.assert_awaited_once()
    assert redis_like.set.await_args.args[0] == cache.key
    value = redis_like.set.await_args.args[1]
    assert "|" in value
    left, right = value.split("|", 1)
    assert PlanData.model_validate_json(left) == plan
    assert FactData.model_validate_json(right) == fact
