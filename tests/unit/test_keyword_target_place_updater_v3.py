from __future__ import annotations

from collections.abc import Callable
from datetime import datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.modules.common_slaves.wildberries.models.enums import KeywordStrategyMode
from app.modules.predict_keywords_target_place.clickhouse_manager.dto.bid_position import (
    BidPosition,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.target_place_sync import (
    sync_keyword_target_places_v3,
)
from app.modules.wb_adv_updater.calculated_keywords_manager.dto.calculated_keyword import (
    CalculatedKeyword,
)
from tests.unit.auto_updater_v3.test_no_data_activation import _kw as _calculated_kw_fixture


def _patched_sm(session_cm: AsyncMock) -> Callable[..., AsyncMock]:
    def _open(*_a: object, **_k: object) -> AsyncMock:
        return session_cm

    return _open


def _ladder_bid_profiles(keyword: str = "kw_min") -> dict[str, list[BidPosition]]:
    """Три позиции: MAX=1, OPT=2, MIN=3 при conv=0.01 (CPO min на pos 3)."""
    ts = datetime.now()
    positions = [
        (1, 500, 0.40),
        (2, 80, 0.25),
        (3, 60, 0.22),
    ]
    rows: list[BidPosition] = []
    for pos, bid, conv in positions:
        bp = BidPosition(keyword, pos, bid, ts)
        bp.conv_carts_to_views = conv
        rows.append(bp)
    return {keyword: rows}


def _calc_map(text: str, *, conv: float = 0.01) -> dict[str, CalculatedKeyword]:
    return {
        text.lower(): _calculated_kw_fixture(
            ks_id=1,
            text=text,
            mode=KeywordStrategyMode.MIN_CPA,
            conv=conv,
            cpm_set_bid=200,
        )
    }


def _kw_row(
    *,
    text: str = "kw_min",
    strategy_mode: KeywordStrategyMode = KeywordStrategyMode.MIN_CPA,
    target_place: int | None = None,
    ks_id: int = 1,
    hard_status: int = 2,
) -> SimpleNamespace:
    return SimpleNamespace(
        id=ks_id,
        text=text,
        strategy_mode=strategy_mode,
        target_place=target_place,
        hard_status=hard_status,
    )


@pytest.mark.unit
@pytest.mark.asyncio
async def test_sync_keyword_target_places_v3_updates_off_via_min_cpa_proxy(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    off_kw = _kw_row(
        strategy_mode=KeywordStrategyMode.OFF,
        target_place=7,
    )
    min_kw = _kw_row(
        strategy_mode=KeywordStrategyMode.MIN_CPA,
        target_place=None,
    )
    fake_result = MagicMock()
    fake_result.scalars.return_value.all.return_value = [off_kw, min_kw]

    session = AsyncMock()
    session.execute = AsyncMock(return_value=fake_result)
    session.commit = AsyncMock()

    session_cm = AsyncMock()
    session_cm.__aenter__.return_value = session
    session_cm.__aexit__.return_value = None
    monkeypatch.setattr(
        "app.modules.shop_runner.service_manager.services.auto_updater_v3.target_place_sync.sm",
        _patched_sm(session_cm),
    )

    adv = MagicMock()
    adv.adv_setting_original_id = 1
    adv.adv_id = 123

    await sync_keyword_target_places_v3(
        adv=adv,
        bid_profiles=_ladder_bid_profiles(),
        calculated_by_text=_calc_map("kw_min"),
    )

    assert off_kw.target_place == 3
    assert min_kw.target_place == 3


@pytest.mark.unit
@pytest.mark.asyncio
async def test_sync_keyword_target_places_v3_sets_zero_when_no_profile_active_mode(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    min_kw = _kw_row(target_place=99)
    fake_result = MagicMock()
    fake_result.scalars.return_value.all.return_value = [min_kw]

    session = AsyncMock()
    session.execute = AsyncMock(return_value=fake_result)
    session.commit = AsyncMock()

    session_cm = AsyncMock()
    session_cm.__aenter__.return_value = session
    session_cm.__aexit__.return_value = None
    monkeypatch.setattr(
        "app.modules.shop_runner.service_manager.services.auto_updater_v3.target_place_sync.sm",
        _patched_sm(session_cm),
    )

    adv = MagicMock()
    adv.adv_setting_original_id = 1
    adv.adv_id = 123

    await sync_keyword_target_places_v3(
        adv=adv,
        bid_profiles={},
        calculated_by_text=_calc_map("kw_min"),
    )

    assert min_kw.target_place == 0


@pytest.mark.unit
@pytest.mark.asyncio
async def test_sync_keyword_target_places_v3_sets_zero_when_candidate_invalid(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Invalid кандидат активного режима → target_place=0 (min bid), не None."""
    opt_kw = _kw_row(
        strategy_mode=KeywordStrategyMode.OPTIMUM,
        target_place=5,
    )
    fake_result = MagicMock()
    fake_result.scalars.return_value.all.return_value = [opt_kw]

    session = AsyncMock()
    session.execute = AsyncMock(return_value=fake_result)
    session.commit = AsyncMock()

    session_cm = AsyncMock()
    session_cm.__aenter__.return_value = session
    session_cm.__aexit__.return_value = None
    monkeypatch.setattr(
        "app.modules.shop_runner.service_manager.services.auto_updater_v3.target_place_sync.sm",
        _patched_sm(session_cm),
    )

    ts = datetime.now()
    bp = BidPosition("kw_min", 1, 100, ts)
    bid_profiles = {"kw_min": [bp]}

    adv = MagicMock()
    adv.adv_setting_original_id = 1
    adv.adv_id = 123

    await sync_keyword_target_places_v3(
        adv=adv,
        bid_profiles=bid_profiles,
        calculated_by_text=_calc_map("kw_min"),
    )

    assert opt_kw.target_place == 0


@pytest.mark.unit
@pytest.mark.asyncio
async def test_sync_keyword_target_places_v3_resolves_profile_with_mixed_case_ch_key(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """CH может вернуть ключ в исходном регистре, в БД текст ключа — lower."""
    min_kw = _kw_row(target_place=None)
    fake_result = MagicMock()
    fake_result.scalars.return_value.all.return_value = [min_kw]

    session = AsyncMock()
    session.execute = AsyncMock(return_value=fake_result)
    session.commit = AsyncMock()

    session_cm = AsyncMock()
    session_cm.__aenter__.return_value = session
    session_cm.__aexit__.return_value = None
    monkeypatch.setattr(
        "app.modules.shop_runner.service_manager.services.auto_updater_v3.target_place_sync.sm",
        _patched_sm(session_cm),
    )

    ts = datetime.now()
    bid_profiles = _ladder_bid_profiles("Kw_Min")
    adv = MagicMock()
    adv.adv_setting_original_id = 1
    adv.adv_id = 123

    await sync_keyword_target_places_v3(
        adv=adv,
        bid_profiles=bid_profiles,
        calculated_by_text=_calc_map("kw_min"),
    )

    assert min_kw.target_place == 3


@pytest.mark.unit
@pytest.mark.asyncio
async def test_sync_keyword_target_places_v3_sets_zero_when_no_v2_cpo_with_profile(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Есть CH-профиль, но нет V2 CPO — target_place=0 (min bid)."""
    min_kw = _kw_row(target_place=5)
    fake_result = MagicMock()
    fake_result.scalars.return_value.all.return_value = [min_kw]

    session = AsyncMock()
    session.execute = AsyncMock(return_value=fake_result)
    session.commit = AsyncMock()

    session_cm = AsyncMock()
    session_cm.__aenter__.return_value = session
    session_cm.__aexit__.return_value = None
    monkeypatch.setattr(
        "app.modules.shop_runner.service_manager.services.auto_updater_v3.target_place_sync.sm",
        _patched_sm(session_cm),
    )

    calc_kw: CalculatedKeyword = _calculated_kw_fixture(
        ks_id=1,
        text="kw_min",
        mode=KeywordStrategyMode.MIN_CPA,
        conv=0.0,
        cpm_set_bid=0,
    )

    adv = MagicMock()
    adv.adv_setting_original_id = 1
    adv.adv_id = 123

    ts = datetime.now()
    await sync_keyword_target_places_v3(
        adv=adv,
        bid_profiles={"kw_min": [BidPosition("kw_min", 1, 100, ts)]},
        calculated_by_text={"kw_min": calc_kw},
    )

    assert min_kw.target_place == 0


@pytest.mark.unit
@pytest.mark.asyncio
async def test_sync_keyword_target_places_v3_uses_calculated_keyword_strategy_mode(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """DB ``strategy_mode`` может отставать; target_place — по режиму из ``calculated_by_text``."""
    kw_row = _kw_row(
        strategy_mode=KeywordStrategyMode.OPTIMUM,
        target_place=1,
    )
    fake_result = MagicMock()
    fake_result.scalars.return_value.all.return_value = [kw_row]

    session = AsyncMock()
    session.execute = AsyncMock(return_value=fake_result)
    session.commit = AsyncMock()

    session_cm = AsyncMock()
    session_cm.__aenter__.return_value = session
    session_cm.__aexit__.return_value = None
    monkeypatch.setattr(
        "app.modules.shop_runner.service_manager.services.auto_updater_v3.target_place_sync.sm",
        _patched_sm(session_cm),
    )

    adv = MagicMock()
    adv.adv_setting_original_id = 1
    adv.adv_id = 123

    await sync_keyword_target_places_v3(
        adv=adv,
        bid_profiles=_ladder_bid_profiles(),
        calculated_by_text=_calc_map("kw_min"),
    )

    assert kw_row.target_place == 3


@pytest.mark.unit
@pytest.mark.asyncio
async def test_sync_force_all_target_place_zero_with_profile(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """CAMPAIGN_NO_DATA: force zero даже при CH profile + V2 CPO."""
    min_kw = _kw_row(target_place=5)
    fake_result = MagicMock()
    fake_result.scalars.return_value.all.return_value = [min_kw]

    session = AsyncMock()
    session.execute = AsyncMock(return_value=fake_result)
    session.commit = AsyncMock()

    session_cm = AsyncMock()
    session_cm.__aenter__.return_value = session
    session_cm.__aexit__.return_value = None
    monkeypatch.setattr(
        "app.modules.shop_runner.service_manager.services.auto_updater_v3.target_place_sync.sm",
        _patched_sm(session_cm),
    )

    adv = MagicMock()
    adv.adv_setting_original_id = 1
    adv.adv_id = 123

    await sync_keyword_target_places_v3(
        adv=adv,
        bid_profiles=_ladder_bid_profiles(),
        calculated_by_text=_calc_map("kw_min"),
        force_all_target_place_zero=True,
    )

    assert min_kw.target_place == 0


@pytest.mark.unit
@pytest.mark.asyncio
async def test_sync_force_zero_skips_fixed_manual(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fixed_kw = _kw_row(target_place=7, hard_status=3)
    fake_result = MagicMock()
    fake_result.scalars.return_value.all.return_value = [fixed_kw]

    session = AsyncMock()
    session.execute = AsyncMock(return_value=fake_result)
    session.commit = AsyncMock()

    session_cm = AsyncMock()
    session_cm.__aenter__.return_value = session
    session_cm.__aexit__.return_value = None
    monkeypatch.setattr(
        "app.modules.shop_runner.service_manager.services.auto_updater_v3.target_place_sync.sm",
        _patched_sm(session_cm),
    )

    adv = MagicMock()
    adv.adv_setting_original_id = 1
    adv.adv_id = 123

    await sync_keyword_target_places_v3(
        adv=adv,
        bid_profiles=_ladder_bid_profiles(),
        calculated_by_text=_calc_map("kw_min"),
        force_all_target_place_zero=True,
    )

    assert fixed_kw.target_place == 7


@pytest.mark.unit
@pytest.mark.asyncio
async def test_sync_eligibility_fallback_zero_by_keyword_id(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    min_kw = _kw_row(target_place=5, ks_id=42)
    fake_result = MagicMock()
    fake_result.scalars.return_value.all.return_value = [min_kw]

    session = AsyncMock()
    session.execute = AsyncMock(return_value=fake_result)
    session.commit = AsyncMock()

    session_cm = AsyncMock()
    session_cm.__aenter__.return_value = session
    session_cm.__aexit__.return_value = None
    monkeypatch.setattr(
        "app.modules.shop_runner.service_manager.services.auto_updater_v3.target_place_sync.sm",
        _patched_sm(session_cm),
    )

    adv = MagicMock()
    adv.adv_setting_original_id = 1
    adv.adv_id = 123

    await sync_keyword_target_places_v3(
        adv=adv,
        bid_profiles=_ladder_bid_profiles(),
        calculated_by_text=_calc_map("kw_min"),
        target_place_fallback_zero_by_keyword_id={42: True},
    )

    assert min_kw.target_place == 0
