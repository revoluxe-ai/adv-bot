"""Per-shop feature flag dual-path (задача 2.3).

Spec: ``connected-shop-campaign-ad-data-collection``.
Debt: ``openspec/architectural-debt/TEMPORARY_DUAL_CAMPAIGN_COLLECTION.md``.

Доказывает сам флаг, а не подмену его результата: OFF и rollback оставляют
managed-only, ON не входит в unmanaged slice и не зовёт запрещённые writers.
История ClickHouse не удаляется. Резолвер 3.1 этим тестом не подменяется.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from app.core.redis_manager_v2.redis_client import RedisClient
from app.modules.shop_runner.modules.wb_api import WBApi
from app.modules.shop_runner.shop_run_worker.redis_manager import RedisShopManager
from app.modules.shop_runner.shop_wide_collection.feature_flag import (
    ROUTE_EPOCH_SOURCE,
    ShopWideCollectionDecision,
    ShopWideCollectionMode,
    ShopWideUnmanagedSliceNotReady,
    apply_shop_wide_collection_gate,
    enforce_shop_wide_collection_fail_closed,
    evaluate_shop_wide_collection,
)
from app.modules.shop_runner.tasks_manager.tasks_manager import TasksManager
from app.modules.shop_runner.wb_shop import WBShop

_SHOP_A = "shop-a"
_SHOP_B = "shop-b"
_RECORD_COROUTINES = (
    "update_common_sale_stat",
    "update_full_adv_stat",
    "update_clusters_adv_stats_today",
    "update_clusters_adv_stats_history",
)


class _FakeTaskGroup:
    """TaskGroup, который фиксирует create_task и не исполняет корутины."""

    def __init__(self) -> None:
        self.created: list[Any] = []

    async def __aenter__(self) -> _FakeTaskGroup:
        return self

    async def __aexit__(self, exc_type: Any, exc: Any, tb: Any) -> bool:
        return False

    def create_task(self, coro: Any) -> MagicMock:
        """Сохранить аргумент create_task. Цикл shop-runner здесь не идёт."""
        self.created.append(coro)
        close = getattr(coro, "close", None)
        if close is not None:
            close()
        return MagicMock()


def _forbid(*_args: object, **_kwargs: object) -> None:
    """Падает, если запрещённый writer сконструирован или вызван."""
    raise AssertionError("forbidden shop-wide side effect")


@pytest.fixture
def forbid_foreign_writers(monkeypatch: pytest.MonkeyPatch) -> None:
    """Падает, если gate откроет CH, Redis epoch или management write.

    Spec запрещает ``update_advs_in_db``, AdvSetting, ``bot_active`` и WB
    management adapters. Узкий patch на класс, не на module attribute вокруг
    await: сам флаг синхронный и читает только env.
    """
    monkeypatch.setattr(
        "app.utils.click_house.client.get_clickhouse_client",
        _forbid,
    )
    monkeypatch.setattr(
        "app.modules.common_slaves.wildberries.wb_db_manager.update_advs_in_db",
        _forbid,
    )
    monkeypatch.setattr(
        "app.core.redis_manager_v2.redis_client.RedisClient",
        _forbid,
    )
    monkeypatch.setattr(
        "app.modules.shop_runner.service_manager.services.auto_updater_v3.apply_manager.manager.ApplyManager",
        _forbid,
    )
    monkeypatch.setattr(
        "app.modules.common_slaves.wildberries.models.AdvSetting",
        _forbid,
    )


def _enable(monkeypatch: pytest.MonkeyPatch, shop_ids: str) -> None:
    """Включить master и задать allowlist. Пустой список никого не открывает."""
    monkeypatch.setenv("SHOP_WIDE_COLLECTION_ENABLED", "1")
    monkeypatch.setenv("SHOP_WIDE_COLLECTION_SHOP_IDS", shop_ids)


def _assert_no_harm(decision: ShopWideCollectionDecision) -> None:
    """История CH цела, unmanaged не вошли, Redis epoch не записан."""
    assert decision.unmanaged_slice_entered is False
    assert decision.clickhouse_history_retained is True
    assert decision.deletes_clickhouse_history is False
    assert decision.route_epoch_consulted is False
    assert decision.route_epoch_source == ROUTE_EPOCH_SOURCE
    assert decision.redis_route_epoch_written is False


@pytest.mark.unit
def test_default_off_keeps_managed_only(
    monkeypatch: pytest.MonkeyPatch, forbid_foreign_writers: None
) -> None:
    """Без env магазин остаётся на managed-only.

    Spec ``connected-shop-campaign-ad-data-collection``, Migration Plan:
    флаг per shop по умолчанию не расширяет universe.
    """
    monkeypatch.delenv("SHOP_WIDE_COLLECTION_ENABLED", raising=False)
    monkeypatch.delenv("SHOP_WIDE_COLLECTION_SHOP_IDS", raising=False)
    decision = apply_shop_wide_collection_gate(_SHOP_A)
    assert decision.mode is ShopWideCollectionMode.MANAGED_ONLY
    _assert_no_harm(decision)


@pytest.mark.unit
def test_unknown_master_value_stays_managed_only(
    monkeypatch: pytest.MonkeyPatch, forbid_foreign_writers: None
) -> None:
    """Неизвестное значение master не открывает dual-path.

    Spec: rollback и выключенный флаг сохраняют прежний managed охват.
    """
    monkeypatch.setenv("SHOP_WIDE_COLLECTION_ENABLED", "maybe")
    monkeypatch.setenv("SHOP_WIDE_COLLECTION_SHOP_IDS", _SHOP_A)
    decision = apply_shop_wide_collection_gate(_SHOP_A)
    assert decision.mode is ShopWideCollectionMode.MANAGED_ONLY
    _assert_no_harm(decision)


@pytest.mark.unit
def test_enabled_shop_is_dual_path_active_and_sibling_stays_managed(
    monkeypatch: pytest.MonkeyPatch, forbid_foreign_writers: None
) -> None:
    """ON для shop-a открывает dual-path scheduling; shop-b остаётся managed-only.

    Spec: dual-path per shop. Соседний магазин не получает чужой allowlist.
    Gate snapshot не означает вход в unmanaged slice — только режим tick.
    """
    _enable(monkeypatch, f" {_SHOP_A} , ")
    enabled = apply_shop_wide_collection_gate(_SHOP_A)
    sibling = apply_shop_wide_collection_gate(_SHOP_B)
    prefix = apply_shop_wide_collection_gate("shop-ab")
    assert enabled.mode is ShopWideCollectionMode.DUAL_PATH_ACTIVE
    assert sibling.mode is ShopWideCollectionMode.MANAGED_ONLY
    assert prefix.mode is ShopWideCollectionMode.MANAGED_ONLY
    _assert_no_harm(enabled)
    _assert_no_harm(sibling)
    again = evaluate_shop_wide_collection(_SHOP_A)
    assert again == enabled


@pytest.mark.unit
def test_rollback_returns_managed_only_and_retains_clickhouse_history(
    monkeypatch: pytest.MonkeyPatch, forbid_foreign_writers: None
) -> None:
    """Снятие флага после ON возвращает managed-only и не удаляет CH.

    Spec Migration Plan: rollback = прежнее managed-only поведение, уже
    записанная история ClickHouse остаётся.
    """
    _enable(monkeypatch, _SHOP_A)
    assert (
        apply_shop_wide_collection_gate(_SHOP_A).mode
        is ShopWideCollectionMode.DUAL_PATH_ACTIVE
    )
    monkeypatch.setenv("SHOP_WIDE_COLLECTION_ENABLED", "0")
    rolled = apply_shop_wide_collection_gate(_SHOP_A)
    assert rolled.mode is ShopWideCollectionMode.MANAGED_ONLY
    _assert_no_harm(rolled)
    _enable(monkeypatch, _SHOP_B)
    removed = apply_shop_wide_collection_gate(_SHOP_A)
    assert removed.mode is ShopWideCollectionMode.MANAGED_ONLY
    _assert_no_harm(removed)


@pytest.mark.unit
def test_empty_shop_id_does_not_match_allowlist(
    monkeypatch: pytest.MonkeyPatch, forbid_foreign_writers: None
) -> None:
    """Пустой shop_id не считается включённым, даже если в CSV есть пустой токен.

    Spec: флаг per shop. Пустое значение не открывает все магазины.
    """
    _enable(monkeypatch, f",{_SHOP_A},")
    decision = apply_shop_wide_collection_gate("")
    assert decision.mode is ShopWideCollectionMode.MANAGED_ONLY
    _assert_no_harm(decision)


@pytest.mark.unit
def test_fail_closed_guard_refuses_unmanaged_entry_without_writers() -> None:
    """Снимок с входом в unmanaged slice падает до write.

    Spec: неполный collector нельзя активировать. Если инвариант entered
    снять, gate обязан остановиться, а не пойти в CH/WB.
    """
    leaked = ShopWideCollectionDecision(
        shop_id=_SHOP_A,
        mode=ShopWideCollectionMode.DUAL_PATH_ACTIVE,
        unmanaged_slice_entered=True,
        clickhouse_history_retained=True,
        deletes_clickhouse_history=False,
        route_epoch_consulted=False,
        route_epoch_source=ROUTE_EPOCH_SOURCE,
        redis_route_epoch_written=False,
    )
    with pytest.raises(ShopWideUnmanagedSliceNotReady) as caught:
        enforce_shop_wide_collection_fail_closed(leaked)
    assert caught.value.shop_id == _SHOP_A


@pytest.mark.unit
@pytest.mark.parametrize(
    ("entered", "retained", "deletes", "redis_written"),
    [
        (False, True, True, False),
        (False, False, False, False),
        (False, True, False, True),
    ],
)
def test_fail_closed_guard_refuses_history_and_redis_epoch(
    entered: bool, retained: bool, deletes: bool, redis_written: bool
) -> None:
    """Удаление истории CH и Redis epoch не проходят gate.

    Spec: единственный durable epoch — ``shop_campaign_inventory.route_version``.
    Rollback не стирает уже записанные строки.
    """
    leaked = ShopWideCollectionDecision(
        shop_id=_SHOP_A,
        mode=ShopWideCollectionMode.MANAGED_ONLY,
        unmanaged_slice_entered=entered,
        clickhouse_history_retained=retained,
        deletes_clickhouse_history=deletes,
        route_epoch_consulted=False,
        route_epoch_source=ROUTE_EPOCH_SOURCE,
        redis_route_epoch_written=redis_written,
    )
    with pytest.raises(ShopWideUnmanagedSliceNotReady):
        enforce_shop_wide_collection_fail_closed(leaked)


@pytest.mark.unit
@pytest.mark.asyncio
@pytest.mark.parametrize("enabled", [False, True])
async def test_wb_shop_run_keeps_managed_record_coroutines(
    monkeypatch: pytest.MonkeyPatch, enabled: bool
) -> None:
    """Tick с флагом OFF и ON по-прежнему ставит managed RECORD.

    Spec: OFF сохраняет текущий managed-only. ON дополнительно ставит
    ``collect_shop_wide_campaign_advertising`` без scripts/Job delegate.
    """
    if enabled:
        _enable(monkeypatch, _SHOP_A)
    else:
        monkeypatch.delenv("SHOP_WIDE_COLLECTION_ENABLED", raising=False)
        monkeypatch.delenv("SHOP_WIDE_COLLECTION_SHOP_IDS", raising=False)
    wb_api = MagicMock(spec=WBApi)
    wb_api.shop_id = _SHOP_A
    redis_manager = MagicMock(spec=RedisShopManager)
    redis_manager.DEFAULT_TTL = 60
    shop = WBShop(
        wb_api,
        redis_manager,
        RedisClient(redis_client=MagicMock()),
        tasks_manager=TasksManager(max_workers=1),
        plan_fact_reader=MagicMock(),
        wb_manager_hub=MagicMock(),
    )
    shop._alive_worker_run = MagicMock(return_value=None)  # type: ignore[method-assign]
    with (
        patch("app.modules.shop_runner.wb_shop.CoroutinesManager") as manager_cls,
        patch("app.modules.shop_runner.wb_shop._taskgroup_coro", side_effect=lambda _name, factory: factory()),
        patch("asyncio.TaskGroup", new=_FakeTaskGroup),
    ):
        await shop.run()
    instance = manager_cls.return_value
    for name in _RECORD_COROUTINES:
        call = getattr(instance, name).call_args
        assert call is not None, name
        assert call.kwargs["only_bot_active"] is False
    assert instance.update_advs_data_from_wb_to_pg.call_count == 1
    unmanaged_call = getattr(
        instance, "collect_shop_wide_campaign_advertising"
    ).call_args
    if enabled:
        assert unmanaged_call is not None
    else:
        assert unmanaged_call is None
