"""LEGACY_BASELINE characterization: full-active комплект = count 1 и прежний дневной тариф.

Контраст для миграции (tasks 1.1–1.2; spec S15–S16). После fair leg-pause billing
full-active MUST сохранять legacy total, даже если AdvPayment split на слоты.
"""

from __future__ import annotations

import pytest

from app.modules.billing.pricer.pricer import Pricer, TariffMode
from app.modules.billing.pricer.tariffs import tariffs_for_auto_setting
from tests.modules.billing.test_pricer_tariffs import DummyAdv, _patch_metering_advs

pytestmark = pytest.mark.unit


def _full_active_setup() -> list[DummyAdv]:
    search = DummyAdv(
        id=2,
        adv_id=200,
        bot_active=False,
        active_status="started",
        search_adv_id=None,
        automatic_version=None,
    )
    anchor = DummyAdv(
        id=1,
        adv_id=100,
        bot_active=True,
        active_status="started",
        search_adv_id=200,
        automatic_version=2,
        auto_update_white_list=True,
        auto_update_target_place=False,
    )
    return [search, anchor]


@pytest.mark.asyncio
async def test_legacy_baseline_full_active_effective_count_one(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """LEGACY_BASELINE 1.1: обе ноги started → effective_count=1 на комплект."""
    advs = _full_active_setup()
    _patch_metering_advs(monkeypatch, advs)

    context = await Pricer.calculate_tariff_context(None, "shop")  # type: ignore[arg-type]
    details = await Pricer().get_tariff_details(None, "shop")  # type: ignore[arg-type]

    assert context.count == 1.0
    assert details.count == 1.0
    assert details.mode == TariffMode.AUTO
    assert details.price_per_adv == float(tariffs_for_auto_setting[1])
    assert details.total_per_month == float(tariffs_for_auto_setting[1])


@pytest.mark.asyncio
async def test_legacy_baseline_full_active_daily_total_matches_legacy_tariff(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """LEGACY_BASELINE 1.2: дневная сумма full-active = legacy count=1 × tariff/30."""
    advs = _full_active_setup()
    _patch_metering_advs(monkeypatch, advs)

    details = await Pricer().get_tariff_details(None, "shop")  # type: ignore[arg-type]
    legacy_month = float(tariffs_for_auto_setting[1])
    legacy_day = Pricer.get_tariff_for_day(legacy_month)

    assert details.total_per_day == legacy_day
    assert details.total_per_day == round(legacy_month / 30, 2)
