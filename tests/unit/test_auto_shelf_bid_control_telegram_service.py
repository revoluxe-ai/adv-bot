from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timezone, UTC
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.modules.shop_runner.service_manager.services.auto_shelf_bid_control_manager.auto_shelf_bid_control_manager import (
    MainBidRefreshResult,
)
from app.modules.shop_runner.service_manager.services.auto_shelf_bid_control_manager.auto_shelf_bid_control_telegram_service import (
    AutoShelfBidControlTelegramError,
    AutoShelfBidControlTelegramService,
)
from app.modules.shop_runner.service_manager.services.auto_shelf_bid_control_manager.dto import (
    AutoShelfBidControlViewDTO,
    OptimizationMetric,
)
from app.modules.common_slaves.wildberries.models.enums.auto_shelf_bid_control_strategy import (
    AutoShelfBidControlStrategy,
)
from app.modules.shop_runner.service_manager.services.auto_shelf_bid_control_manager.dto.decision_snapshot_dto import (
    AutoShelfBidControlDecisionSnapshot,
    BidSyncStatus,
)

pytestmark = pytest.mark.unit

BOT_ACTIVE_PAYWALL_MESSAGE = (
    "Управление ставкой в полках доступно только после включения автоуправления кампанией.\n\n"
    "Бесплатно можно смотреть аналитику и рекламные данные.\n"
    "Чтобы бот сам тестировал и выставлял ставки в полках — подключите автоуправление."
)


def _adv(nmids: list[int]) -> SimpleNamespace:
    return SimpleNamespace(
        id=1,
        nmids=nmids,
        adv_id=12345,
        wb_cabinet=SimpleNamespace(shop_id="shop-1"),
    )


def _view(min_bid: int | None = None) -> AutoShelfBidControlViewDTO:
    return AutoShelfBidControlViewDTO(
        nmid=111,
        auto_adv_id=12345,
        enabled=True,
        has_settings=True,
        has_state=True,
        dry_run=True,
        bid_units_confirmed=False,
        actual_bid_minor=min_bid,
        min_bid_minor=min_bid,
        max_bid_minor=500,
        current_main_bid_minor=450,
        current_test_bid_minor=300,
        cycle_best_bid_minor=450,
        global_best_bid_minor=450,
        next_test_bid_minor=200,
        currency="RUB",
        current_mode="test",
        current_cycle_started_at=None,
        test_started_at=None,
        main_started_at=None,
        test_share=0.1,
        target_test_impressions=500,
        target_test_observation_minutes=60,
        target_main_impressions=4500,
        target_main_observation_minutes=540,
        min_bid_distance_minor=10,
        test_impressions=0,
        main_impressions=0,
        test_elapsed_minutes=0,
        main_elapsed_minutes=0,
        covered_points_count=0,
        bid_points_total=0,
        bid_points=[],
        cycle_covered_points_count=0,
        cycle_bid_points=[],
        last_reason=None,
        warnings=[],
        optimization_metric=OptimizationMetric.CPC,
        fact_cpo=None,
        resolve_cpo=None,
        auto_shelf_bid_control_strategy=AutoShelfBidControlStrategy.PLAN_DISTANCE,
    )


def _service(
    repository: MagicMock | None = None,
    view_provider: MagicMock | None = None,
) -> AutoShelfBidControlTelegramService:
    return AutoShelfBidControlTelegramService(
        redis_client=MagicMock(),
        repository=repository,
        view_provider=view_provider,
    )


def _enabled_main_adv() -> SimpleNamespace:
    adv = _adv([111])
    adv.auto_shelf_bid_control_enabled = True
    adv.auto_shelf_bid_control_strategy = AutoShelfBidControlStrategy.PLAN_DISTANCE
    adv.bot_active = True
    adv.auto_adv_active_status = True
    adv.max_price_for_order = 1000.0
    adv.plan_for_sales_for_day = 10
    adv.target_price_for_order = 500.0
    return adv


def _inactive_adv() -> SimpleNamespace:
    adv = _enabled_main_adv()
    adv.bot_active = False
    return adv


def _main_mode_state(*, current_main_bid_minor: int = 48_000) -> SimpleNamespace:
    return SimpleNamespace(
        current_mode="main",
        current_main_bid_minor=current_main_bid_minor,
        current_test_bid_minor=41_000,
    )


def _decision_snapshot(
    *,
    expected_bid_minor: int | None,
    actual_bid_minor: int | None = 48_000,
) -> AutoShelfBidControlDecisionSnapshot:
    return AutoShelfBidControlDecisionSnapshot(
        nmid=111,
        auto_adv_id=12345,
        current_mode="main",
        actual_bid_minor=actual_bid_minor,
        min_bid_minor=12_000,
        max_bid_minor=80_000,
        fresh_best_main_bid_minor=expected_bid_minor,
        fresh_next_test_bid_minor=41_000,
        expected_bid_minor=expected_bid_minor,
        bid_sync_status=BidSyncStatus.MISMATCH_NOT_APPLIED,
        can_count_progress=True,
        qualified_tested_bids_count=2 if expected_bid_minor is not None else 1,
    )


def _telegram_main_open_setup(
    *,
    expected_bid_minor: int | None,
    actual_bid_minor: int | None = 48_000,
    current_main_bid_minor: int = 48_000,
) -> tuple[
    AutoShelfBidControlTelegramService,
    MagicMock,
    AutoShelfBidControlDecisionSnapshot,
]:
    repository = MagicMock()
    repository.get_adv_setting_by_original_id = AsyncMock(return_value=_enabled_main_adv())
    repository.get_state = AsyncMock(
        return_value=_main_mode_state(current_main_bid_minor=current_main_bid_minor)
    )
    repository.get_or_create_default_settings = AsyncMock(
        return_value=SimpleNamespace(max_bid_minor=80_000)
    )
    view_provider = MagicMock()
    view_provider._fetch_wb_min_bid_minor = AsyncMock(return_value=12_000)
    view_provider._analytics = MagicMock()
    view_provider.build_view = AsyncMock(return_value=_view(min_bid=12_000))
    service = _service(repository, view_provider)
    service._bid_cache.get_bid = AsyncMock(
        return_value=(
            SimpleNamespace(bid_minor=actual_bid_minor)
            if actual_bid_minor is not None
            else None
        )
    )
    snapshot = _decision_snapshot(
        expected_bid_minor=expected_bid_minor,
        actual_bid_minor=actual_bid_minor,
    )
    manager_instance = MagicMock()
    manager_instance.build_decision_snapshot = AsyncMock(return_value=snapshot)
    return service, manager_instance, snapshot


@pytest.mark.asyncio
async def test_enable_creates_default_settings_when_missing() -> None:
    repository = MagicMock()
    repository.get_adv_setting_by_original_id = AsyncMock(return_value=_adv([111]))
    repository.get_or_create_default_settings = AsyncMock(return_value=SimpleNamespace())
    repository.set_enabled = AsyncMock()
    view_provider = MagicMock()
    view_provider.build_view = AsyncMock(return_value=_view())
    service = _service(repository, view_provider)

    await service.enable(1)

    repository.get_or_create_default_settings.assert_awaited_once_with(nmid=111)
    repository.set_enabled.assert_awaited_once_with(1, True)


@pytest.mark.asyncio
async def test_enable_does_not_shrink_repaired_max_to_actual_only() -> None:
    """После build_view legacy repair max=50k не затирается сравнением со stale 500."""
    repository = MagicMock()
    repository.get_adv_setting_by_original_id = AsyncMock(return_value=_adv([111]))
    repository.get_or_create_default_settings = AsyncMock(
        return_value=SimpleNamespace(max_bid_minor=500)
    )
    repository.set_enabled = AsyncMock()
    repository.update_settings = AsyncMock()
    view_provider = MagicMock()
    repaired = replace(
        _view(min_bid=12_000),
        actual_bid_minor=31_000,
        max_bid_minor=50_000,
    )
    view_provider.build_view = AsyncMock(side_effect=[repaired, repaired])
    service = _service(repository, view_provider)

    await service.enable(1)

    repository.update_settings.assert_not_awaited()


@pytest.mark.asyncio
async def test_enable_raises_max_when_repaired_ceiling_below_actual() -> None:
    repository = MagicMock()
    repository.get_adv_setting_by_original_id = AsyncMock(return_value=_adv([111]))
    repository.get_or_create_default_settings = AsyncMock(
        return_value=SimpleNamespace(max_bid_minor=500)
    )
    repository.set_enabled = AsyncMock()
    repository.update_settings = AsyncMock(return_value=SimpleNamespace())
    view_provider = MagicMock()
    repaired = replace(
        _view(min_bid=12_000),
        actual_bid_minor=55_000,
        max_bid_minor=40_000,
    )
    view_provider.build_view = AsyncMock(side_effect=[repaired, repaired])
    service = _service(repository, view_provider)

    await service.enable(1)

    repository.update_settings.assert_awaited_once_with(
        nmid=111,
        max_bid_minor=55_000,
    )


@pytest.mark.asyncio
async def test_enable_fails_for_multi_nmid() -> None:
    repository = MagicMock()
    repository.get_adv_setting_by_original_id = AsyncMock(return_value=_adv([111, 222]))
    service = _service(repository, MagicMock())

    with pytest.raises(AutoShelfBidControlTelegramError):
        await service.enable(1)


@pytest.mark.asyncio
async def test_disable_sets_flag_false() -> None:
    repository = MagicMock()
    repository.get_adv_setting_by_original_id = AsyncMock(return_value=_adv([111]))
    repository.set_enabled = AsyncMock()
    view_provider = MagicMock()
    view_provider.build_view = AsyncMock(return_value=_view())
    service = _service(repository, view_provider)

    await service.disable(1)

    repository.set_enabled.assert_awaited_once_with(1, False)


@pytest.mark.asyncio
async def test_enable_paywalls_when_bot_inactive() -> None:
    repository = MagicMock()
    repository.get_adv_setting_by_original_id = AsyncMock(return_value=_inactive_adv())
    repository.get_or_create_default_settings = AsyncMock()
    repository.set_enabled = AsyncMock()
    service = _service(repository, MagicMock())

    with pytest.raises(AutoShelfBidControlTelegramError) as exc_info:
        await service.enable(1)

    assert exc_info.value.message == BOT_ACTIVE_PAYWALL_MESSAGE
    repository.get_or_create_default_settings.assert_not_awaited()
    repository.set_enabled.assert_not_awaited()


@pytest.mark.asyncio
async def test_update_max_bid_paywalls_when_bot_inactive() -> None:
    repository = MagicMock()
    repository.get_adv_setting_by_original_id = AsyncMock(return_value=_inactive_adv())
    repository.update_settings = AsyncMock()
    service = _service(repository, MagicMock())

    with pytest.raises(AutoShelfBidControlTelegramError) as exc_info:
        await service.update_max_bid(1, "500")

    assert exc_info.value.message == BOT_ACTIVE_PAYWALL_MESSAGE
    repository.update_settings.assert_not_awaited()


@pytest.mark.asyncio
async def test_update_max_bid_validates_positive() -> None:
    repository = MagicMock()
    repository.get_adv_setting_by_original_id = AsyncMock(return_value=_adv([111]))
    service = _service(repository, MagicMock())

    with pytest.raises(AutoShelfBidControlTelegramError):
        await service.update_max_bid(1, "0")


@pytest.mark.asyncio
async def test_update_max_bid_validates_min_bid_when_available() -> None:
    repository = MagicMock()
    repository.get_adv_setting_by_original_id = AsyncMock(return_value=_adv([111]))
    repository.get_or_create_default_settings = AsyncMock(return_value=SimpleNamespace())
    view_provider = MagicMock()
    view_provider.build_view = AsyncMock(
        side_effect=[_view(min_bid=70_000), _view(min_bid=70_000)]
    )
    service = _service(repository, view_provider)

    with pytest.raises(AutoShelfBidControlTelegramError):
        await service.update_max_bid(1, "6")


@pytest.mark.asyncio
async def test_update_max_bid_saves_rubles_as_kopecks() -> None:
    repository = MagicMock()
    repository.get_adv_setting_by_original_id = AsyncMock(return_value=_adv([111]))
    repository.get_or_create_default_settings = AsyncMock(return_value=SimpleNamespace())
    repository.update_settings = AsyncMock()
    view_provider = MagicMock()
    view_provider.build_view = AsyncMock(
        side_effect=[_view(min_bid=10_000), _view(min_bid=10_000)]
    )
    service = _service(repository, view_provider)

    await service.update_max_bid(1, "500")

    repository.update_settings.assert_awaited_once_with(nmid=111, max_bid_minor=50_000)


def test_update_test_share_parser_accepts_percent_and_fraction() -> None:
    assert AutoShelfBidControlTelegramService._parse_test_share("10") == 0.1
    assert AutoShelfBidControlTelegramService._parse_test_share("0.1") == 0.1


def test_update_test_share_parser_rejects_out_of_range() -> None:
    with pytest.raises(AutoShelfBidControlTelegramError):
        AutoShelfBidControlTelegramService._parse_test_share("50")
    with pytest.raises(AutoShelfBidControlTelegramError):
        AutoShelfBidControlTelegramService._parse_test_share("0")


@pytest.mark.asyncio
async def test_update_target_test_impressions_invalid_text() -> None:
    repository = MagicMock()
    repository.get_adv_setting_by_original_id = AsyncMock(return_value=_adv([111]))
    service = _service(repository, MagicMock())

    with pytest.raises(AutoShelfBidControlTelegramError):
        await service.update_target_test_impressions(1, "abc")


@pytest.mark.asyncio
async def test_update_target_test_observation_minutes_rejects_less_than_hour() -> None:
    repository = MagicMock()
    repository.get_adv_setting_by_original_id = AsyncMock(return_value=_adv([111]))
    service = _service(repository, MagicMock())

    with pytest.raises(AutoShelfBidControlTelegramError):
        await service.update_target_test_observation_minutes(1, "30")


@pytest.mark.asyncio
async def test_update_min_bid_distance_invalid_value() -> None:
    repository = MagicMock()
    repository.get_adv_setting_by_original_id = AsyncMock(return_value=_adv([111]))
    service = _service(repository, MagicMock())

    with pytest.raises(AutoShelfBidControlTelegramError):
        await service.update_min_bid_distance(1, "0")


@pytest.mark.asyncio
async def test_reset_cycle_sets_state_to_test_and_middle_bid(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("AUTO_SHELF_BID_CONTROL_BID_UNITS_CONFIRMED", "true")
    repository = MagicMock()
    repository.get_adv_setting_by_original_id = AsyncMock(return_value=_adv([111]))
    settings_obj = SimpleNamespace(max_bid_minor=500, currency="RUB")
    repository.get_or_create_default_settings = AsyncMock(return_value=settings_obj)
    repository.get_state = AsyncMock(return_value=None)
    repository.build_state = AsyncMock(
        return_value=SimpleNamespace(
            current_cycle_started_at=datetime.now(UTC),
            previous_cycle_started_at=None,
            current_mode="test",
            current_test_bid_minor=300,
            test_started_at=datetime.now(UTC),
            main_started_at=None,
            last_reason="manual_cycle_reset",
            currency="RUB",
        )
    )
    repository.save_state = AsyncMock()
    view_provider = MagicMock()
    view_provider.build_view = AsyncMock(side_effect=[_view(min_bid=100), _view(min_bid=100)])
    service = _service(repository, view_provider)
    service._set_bid = AsyncMock()  # type: ignore[method-assign]

    await service.reset_cycle(1)

    repository.save_state.assert_awaited()
    service._set_bid.assert_awaited_once()


@pytest.mark.asyncio
async def test_force_main_errors_without_state() -> None:
    repository = MagicMock()
    repository.get_adv_setting_by_original_id = AsyncMock(return_value=_adv([111]))
    repository.get_state = AsyncMock(return_value=None)
    service = _service(repository, MagicMock())

    with pytest.raises(AutoShelfBidControlTelegramError):
        await service.force_main(1)


@pytest.mark.asyncio
async def test_force_main_switches_to_main_when_main_bid_exists(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("AUTO_SHELF_BID_CONTROL_BID_UNITS_CONFIRMED", "true")
    state = SimpleNamespace(
        current_main_bid_minor=450,
        current_mode="test",
        main_started_at=None,
        last_reason=None,
    )
    repository = MagicMock()
    repository.get_adv_setting_by_original_id = AsyncMock(return_value=_adv([111]))
    repository.get_state = AsyncMock(return_value=state)
    repository.get_or_create_default_settings = AsyncMock(
        return_value=SimpleNamespace(currency="RUB")
    )
    repository.save_state = AsyncMock(return_value=state)
    view_provider = MagicMock()
    view_provider.build_view = AsyncMock(return_value=_view(min_bid=100))
    service = _service(repository, view_provider)
    service._set_bid = AsyncMock()  # type: ignore[method-assign]

    await service.force_main(1)

    assert state.current_mode == "main"
    assert state.last_reason == "manual_force_main"
    service._set_bid.assert_awaited_once()


@pytest.mark.asyncio
async def test_reset_cycle_bid_units_gate_false_does_not_set_bid_or_save_transition(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("AUTO_SHELF_BID_CONTROL_BID_UNITS_CONFIRMED", "false")
    state = SimpleNamespace(
        current_mode="main",
        current_cycle_started_at=datetime(2026, 6, 1, tzinfo=UTC),
        previous_cycle_started_at=None,
        current_test_bid_minor=300,
        test_started_at=datetime(2026, 6, 1, tzinfo=UTC),
        main_started_at=datetime(2026, 6, 1, tzinfo=UTC),
        last_reason="before_reset",
    )
    repository = MagicMock()
    repository.get_adv_setting_by_original_id = AsyncMock(return_value=_adv([111]))
    repository.get_or_create_default_settings = AsyncMock(
        return_value=SimpleNamespace(max_bid_minor=500, currency="RUB")
    )
    repository.get_state = AsyncMock(return_value=state)
    repository.build_state = AsyncMock()
    repository.save_state = AsyncMock()
    view_provider = MagicMock()
    view_provider.build_view = AsyncMock(return_value=_view(min_bid=100))
    service = _service(repository, view_provider)
    service._set_bid = AsyncMock()  # type: ignore[method-assign]

    with pytest.raises(AutoShelfBidControlTelegramError) as exc_info:
        await service.reset_cycle(1)

    assert (
        exc_info.value.message
        == "Gate ставок не подтверждён: AUTO_SHELF_BID_CONTROL_BID_UNITS_CONFIRMED=false"
    )
    assert state.current_mode == "main"
    assert state.last_reason == "before_reset"
    repository.save_state.assert_not_awaited()
    repository.build_state.assert_not_awaited()
    service._set_bid.assert_not_awaited()


@pytest.mark.asyncio
async def test_force_main_bid_units_gate_false_does_not_set_bid_or_save_transition(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("AUTO_SHELF_BID_CONTROL_BID_UNITS_CONFIRMED", "false")
    state = SimpleNamespace(
        current_main_bid_minor=450,
        current_mode="test",
        main_started_at=None,
        last_reason="before_force_main",
    )
    repository = MagicMock()
    repository.get_adv_setting_by_original_id = AsyncMock(return_value=_adv([111]))
    repository.get_state = AsyncMock(return_value=state)
    repository.get_or_create_default_settings = AsyncMock(
        return_value=SimpleNamespace(currency="RUB")
    )
    repository.save_state = AsyncMock(return_value=state)
    service = _service(repository, MagicMock())
    service._set_bid = AsyncMock()  # type: ignore[method-assign]

    with pytest.raises(AutoShelfBidControlTelegramError) as exc_info:
        await service.force_main(1)

    assert (
        exc_info.value.message
        == "Gate ставок не подтверждён: AUTO_SHELF_BID_CONTROL_BID_UNITS_CONFIRMED=false"
    )
    assert state.current_mode == "test"
    assert state.last_reason == "before_force_main"
    repository.save_state.assert_not_awaited()
    service._set_bid.assert_not_awaited()


@pytest.mark.asyncio
async def test_reset_cycle_bid_units_gate_true_sets_bid(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("AUTO_SHELF_BID_CONTROL_BID_UNITS_CONFIRMED", "true")
    repository = MagicMock()
    repository.get_adv_setting_by_original_id = AsyncMock(return_value=_adv([111]))
    settings_obj = SimpleNamespace(max_bid_minor=500, currency="RUB")
    repository.get_or_create_default_settings = AsyncMock(return_value=settings_obj)
    repository.get_state = AsyncMock(return_value=None)
    repository.build_state = AsyncMock(
        return_value=SimpleNamespace(
            current_cycle_started_at=datetime.now(UTC),
            previous_cycle_started_at=None,
            current_mode="test",
            current_test_bid_minor=300,
            test_started_at=datetime.now(UTC),
            main_started_at=None,
            last_reason="manual_cycle_reset",
            currency="RUB",
        )
    )
    repository.save_state = AsyncMock()
    view_provider = MagicMock()
    view_provider.build_view = AsyncMock(side_effect=[_view(min_bid=100), _view(min_bid=100)])
    service = _service(repository, view_provider)
    service._set_bid = AsyncMock()  # type: ignore[method-assign]

    await service.reset_cycle(1)

    repository.save_state.assert_awaited_once()
    service._set_bid.assert_awaited_once()


@pytest.mark.asyncio
async def test_force_main_bid_units_gate_true_sets_bid(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("AUTO_SHELF_BID_CONTROL_BID_UNITS_CONFIRMED", "true")
    state = SimpleNamespace(
        current_main_bid_minor=450,
        current_mode="test",
        main_started_at=None,
        last_reason=None,
    )
    repository = MagicMock()
    repository.get_adv_setting_by_original_id = AsyncMock(return_value=_adv([111]))
    repository.get_state = AsyncMock(return_value=state)
    repository.get_or_create_default_settings = AsyncMock(
        return_value=SimpleNamespace(currency="RUB")
    )
    repository.save_state = AsyncMock(return_value=state)
    view_provider = MagicMock()
    view_provider.build_view = AsyncMock(return_value=_view(min_bid=100))
    service = _service(repository, view_provider)
    service._set_bid = AsyncMock()  # type: ignore[method-assign]

    await service.force_main(1)

    assert state.current_mode == "main"
    assert state.last_reason == "manual_force_main"
    repository.save_state.assert_awaited_once()
    service._set_bid.assert_awaited_once()


@pytest.mark.asyncio
async def test_telegram_open_main_mode_no_typeerror_when_refresh_skipped_no_desired_bid() -> None:
    service, manager_instance, _snapshot = _telegram_main_open_setup(
        expected_bid_minor=57_000,
    )

    with (
        patch(
            "app.modules.shop_runner.service_manager.services.auto_shelf_bid_control_manager.auto_shelf_bid_control_telegram_service.AutoShelfBidControlManager",
            return_value=manager_instance,
        ),
        patch(
            "app.modules.shop_runner.service_manager.services.auto_shelf_bid_control_manager.auto_shelf_bid_control_telegram_service.PlanFactReader"
        ) as plan_fact_reader_cls,
        ):
        plan_fact_reader_cls.return_value.get_latest_plan_fact = AsyncMock(return_value=None)
        result = await service.apply_main_bid_refresh_if_needed(1)

    assert result == MainBidRefreshResult.NO_CHANGE
    manager_instance.build_decision_snapshot.assert_awaited_once()


@pytest.mark.asyncio
async def test_telegram_open_read_only_skips_main_bid_refresh_sync() -> None:
    repository = MagicMock()
    repository.get_adv_setting_by_original_id = AsyncMock(return_value=_inactive_adv())
    repository.get_state = AsyncMock()
    view_provider = MagicMock()
    service = _service(repository, view_provider)

    with patch(
        "app.modules.shop_runner.service_manager.services.auto_shelf_bid_control_manager.auto_shelf_bid_control_telegram_service.AutoShelfBidControlManager"
    ) as manager_cls:
        result = await service.apply_main_bid_refresh_if_needed(1)

    assert result == MainBidRefreshResult.SKIPPED_DISABLED
    repository.get_state.assert_not_awaited()
    manager_cls.assert_not_called()


@pytest.mark.asyncio
async def test_telegram_open_main_mode_passes_snapshot_expected_to_reconcile() -> None:
    service, manager_instance, snapshot = _telegram_main_open_setup(
        expected_bid_minor=57_000,
        actual_bid_minor=48_000,
    )

    with (
        patch(
            "app.modules.shop_runner.service_manager.services.auto_shelf_bid_control_manager.auto_shelf_bid_control_telegram_service.AutoShelfBidControlManager",
            return_value=manager_instance,
        ),
        patch(
            "app.modules.shop_runner.service_manager.services.auto_shelf_bid_control_manager.auto_shelf_bid_control_telegram_service.PlanFactReader"
        ) as plan_fact_reader_cls,
        ):
        plan_fact_reader_cls.return_value.get_latest_plan_fact = AsyncMock(return_value=None)
        await service.apply_main_bid_refresh_if_needed(1)

    manager_instance.build_decision_snapshot.assert_awaited_once()
    snapshot_kwargs = manager_instance.build_decision_snapshot.await_args.kwargs
    assert snapshot_kwargs["actual_bid_minor"] == 48_000
    assert snapshot.expected_bid_minor == 57_000


@pytest.mark.asyncio
async def test_telegram_open_main_mode_no_expected_does_not_reconcile_with_state() -> None:
    service, manager_instance, _snapshot = _telegram_main_open_setup(
        expected_bid_minor=None,
        actual_bid_minor=48_000,
        current_main_bid_minor=48_000,
    )

    with (
        patch(
            "app.modules.shop_runner.service_manager.services.auto_shelf_bid_control_manager.auto_shelf_bid_control_telegram_service.AutoShelfBidControlManager",
            return_value=manager_instance,
        ),
        patch(
            "app.modules.shop_runner.service_manager.services.auto_shelf_bid_control_manager.auto_shelf_bid_control_telegram_service.PlanFactReader"
        ) as plan_fact_reader_cls,
        ):
        plan_fact_reader_cls.return_value.get_latest_plan_fact = AsyncMock(return_value=None)
        await service.apply_main_bid_refresh_if_needed(1)
        view = await service.build_view(1)

    manager_instance.build_decision_snapshot.assert_awaited_once()
    assert view.has_state is True
    assert view.current_main_bid_minor == 450


@pytest.mark.asyncio
async def test_set_strategy_in_test_mode_preserves_current_test_state() -> None:
    repository = MagicMock()
    adv = _enabled_main_adv()
    repository.get_adv_setting_by_original_id = AsyncMock(return_value=adv)
    repository.update_adv_strategy = AsyncMock(return_value=adv)
    repository.get_state = AsyncMock(
        return_value=SimpleNamespace(current_mode="test", current_test_bid_minor=41_000)
    )
    view_provider = MagicMock()
    view_provider.build_view = AsyncMock(return_value=_view(min_bid=12_000))
    service = _service(repository, view_provider)

    await service.set_strategy(1, AutoShelfBidControlStrategy.CTR)

    repository.update_adv_strategy.assert_awaited_once_with(
        1,
        AutoShelfBidControlStrategy.CTR,
    )
    view_provider.build_view.assert_awaited_once_with(1)


@pytest.mark.asyncio
async def test_set_strategy_in_main_mode_only_rebuilds_view() -> None:
    repository = MagicMock()
    adv = _enabled_main_adv()
    repository.get_adv_setting_by_original_id = AsyncMock(return_value=adv)
    repository.update_adv_strategy = AsyncMock(return_value=adv)
    repository.get_state = AsyncMock(return_value=_main_mode_state())
    repository.get_or_create_default_settings = AsyncMock(
        return_value=SimpleNamespace(max_bid_minor=80_000)
    )
    view_provider = MagicMock()
    view_provider._fetch_wb_min_bid_minor = AsyncMock(return_value=12_000)
    view_provider._analytics = MagicMock()
    view_provider.build_view = AsyncMock(return_value=_view(min_bid=12_000))
    service = _service(repository, view_provider)

    await service.set_strategy(1, AutoShelfBidControlStrategy.CPC)

    view_provider.build_view.assert_awaited_once_with(1)


@pytest.mark.asyncio
async def test_apply_main_bid_refresh_normalizes_legacy_cycle_metric_strategy() -> None:
    service, manager_instance, _snapshot = _telegram_main_open_setup(
        expected_bid_minor=57_000,
    )
    repository = service._repository
    adv = _enabled_main_adv()
    adv.auto_shelf_bid_control_strategy = AutoShelfBidControlStrategy.CYCLE_METRIC
    repository.get_adv_setting_by_original_id = AsyncMock(return_value=adv)

    async def _build_snapshot(complex_adv: object, **_: object) -> AutoShelfBidControlDecisionSnapshot:
        assert (
            getattr(complex_adv, "auto_shelf_bid_control_strategy")
            == AutoShelfBidControlStrategy.CPC
        )
        return _decision_snapshot(expected_bid_minor=57_000, actual_bid_minor=48_000)

    manager_instance.build_decision_snapshot = AsyncMock(side_effect=_build_snapshot)

    with (
        patch(
            "app.modules.shop_runner.service_manager.services.auto_shelf_bid_control_manager.auto_shelf_bid_control_telegram_service.AutoShelfBidControlManager",
            return_value=manager_instance,
        ),
        patch(
            "app.modules.shop_runner.service_manager.services.auto_shelf_bid_control_manager.auto_shelf_bid_control_telegram_service.PlanFactReader"
        ) as plan_fact_reader_cls,
        ):
        plan_fact_reader_cls.return_value.get_latest_plan_fact = AsyncMock(return_value=None)
        await service.apply_main_bid_refresh_if_needed(1)

    manager_instance.build_decision_snapshot.assert_awaited_once()
