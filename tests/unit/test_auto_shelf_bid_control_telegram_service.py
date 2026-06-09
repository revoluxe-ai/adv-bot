from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timezone, UTC
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.modules.shop_runner.service_manager.services.auto_shelf_bid_control_manager.auto_shelf_bid_control_telegram_service import (
    AutoShelfBidControlTelegramError,
    AutoShelfBidControlTelegramService,
)
from app.modules.shop_runner.service_manager.services.auto_shelf_bid_control_manager.dto import (
    AutoShelfBidControlViewDTO,
    OptimizationMetric,
)

pytestmark = pytest.mark.unit


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
async def test_reset_cycle_sets_state_to_test_and_middle_bid() -> None:
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
async def test_force_main_switches_to_main_when_main_bid_exists() -> None:
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
