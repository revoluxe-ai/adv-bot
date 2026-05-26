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
from app.modules.shop_runner.service_manager.services.keywords_target_place_updater.keyword_target_place_updater import (
    KeywordTargetPlaceUpdater,
)


def _patched_sm(session_cm: AsyncMock) -> Callable[..., AsyncMock]:
    def _open(*_a: object, **_k: object) -> AsyncMock:
        return session_cm

    return _open


def _minimal_bid_profiles() -> dict[str, list[BidPosition]]:
    ts = datetime.now()
    return {"kw_min": [BidPosition("kw_min", 1, 100, ts)]}


@pytest.mark.unit
@pytest.mark.asyncio
async def test_set_new_target_places_v3_keeps_off_target_place(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    predictor = AsyncMock()
    updater = KeywordTargetPlaceUpdater(predict_keyword_target_place=predictor)

    off_kw = SimpleNamespace(
        text="kw_off",
        strategy_mode=KeywordStrategyMode.OFF,
        target_place=7,
    )
    min_kw = SimpleNamespace(
        text="kw_min",
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
        "app.modules.shop_runner.service_manager.services.keywords_target_place_updater.keyword_target_place_updater.sm",
        _patched_sm(session_cm),
    )

    predictor.get_target_position_for_strategy_mode = MagicMock(return_value=3)
    adv = MagicMock()
    adv.adv_setting_original_id = 1
    adv.adv_id = 123

    await updater._set_new_target_places_v3(  # pyright: ignore[reportPrivateUsage]
        adv=adv,
        bid_profiles=_minimal_bid_profiles(),
    )

    assert off_kw.target_place == 7
    assert min_kw.target_place == 3
    predictor.get_target_position_for_strategy_mode.assert_called_once()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_set_new_target_places_v3_clears_target_place_when_no_profile(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    predictor = AsyncMock()
    updater = KeywordTargetPlaceUpdater(predict_keyword_target_place=predictor)

    min_kw = SimpleNamespace(
        text="kw_min",
        strategy_mode=KeywordStrategyMode.MIN_CPA,
        target_place=99,
    )
    fake_result = MagicMock()
    fake_result.scalars.return_value.all.return_value = [min_kw]

    session = AsyncMock()
    session.execute = AsyncMock(return_value=fake_result)
    session.commit = AsyncMock()

    session_cm = AsyncMock()
    session_cm.__aenter__.return_value = session
    session_cm.__aexit__.return_value = None
    monkeypatch.setattr(
        "app.modules.shop_runner.service_manager.services.keywords_target_place_updater.keyword_target_place_updater.sm",
        _patched_sm(session_cm),
    )

    adv = MagicMock()
    adv.adv_setting_original_id = 1
    adv.adv_id = 123

    await updater._set_new_target_places_v3(adv=adv, bid_profiles={})  # pyright: ignore[reportPrivateUsage]

    assert min_kw.target_place is None
    predictor.get_target_position_for_strategy_mode.assert_not_called()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_set_new_target_places_v3_accepts_none_from_predictor(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    predictor = AsyncMock()
    predictor.get_target_position_for_strategy_mode = MagicMock(return_value=None)
    updater = KeywordTargetPlaceUpdater(predict_keyword_target_place=predictor)

    min_kw = SimpleNamespace(
        text="kw_min",
        strategy_mode=KeywordStrategyMode.MIN_CPA,
        target_place=5,
    )
    fake_result = MagicMock()
    fake_result.scalars.return_value.all.return_value = [min_kw]

    session = AsyncMock()
    session.execute = AsyncMock(return_value=fake_result)
    session.commit = AsyncMock()

    session_cm = AsyncMock()
    session_cm.__aenter__.return_value = session
    session_cm.__aexit__.return_value = None
    monkeypatch.setattr(
        "app.modules.shop_runner.service_manager.services.keywords_target_place_updater.keyword_target_place_updater.sm",
        _patched_sm(session_cm),
    )

    adv = MagicMock()
    adv.adv_setting_original_id = 1
    adv.adv_id = 123

    await updater._set_new_target_places_v3(  # pyright: ignore[reportPrivateUsage]
        adv=adv,
        bid_profiles=_minimal_bid_profiles(),
    )

    assert min_kw.target_place is None
    predictor.get_target_position_for_strategy_mode.assert_called_once()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_set_new_target_places_v3_resolves_profile_with_mixed_case_ch_key(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """CH может вернуть ключ в исходном регистре, в БД текст ключа — lower."""
    predictor = AsyncMock()
    predictor.get_target_position_for_strategy_mode = MagicMock(return_value=4)
    updater = KeywordTargetPlaceUpdater(predict_keyword_target_place=predictor)

    min_kw = SimpleNamespace(
        text="kw_min",
        strategy_mode=KeywordStrategyMode.MIN_CPA,
        target_place=None,
    )
    fake_result = MagicMock()
    fake_result.scalars.return_value.all.return_value = [min_kw]

    session = AsyncMock()
    session.execute = AsyncMock(return_value=fake_result)
    session.commit = AsyncMock()

    session_cm = AsyncMock()
    session_cm.__aenter__.return_value = session
    session_cm.__aexit__.return_value = None
    monkeypatch.setattr(
        "app.modules.shop_runner.service_manager.services.keywords_target_place_updater.keyword_target_place_updater.sm",
        _patched_sm(session_cm),
    )

    ts = datetime.now()
    bid_profiles = {
        "Kw_Min": [BidPosition("Kw_Min", 1, 100, ts)],
    }
    adv = MagicMock()
    adv.adv_setting_original_id = 1
    adv.adv_id = 123

    await updater._set_new_target_places_v3(  # pyright: ignore[reportPrivateUsage]
        adv=adv,
        bid_profiles=bid_profiles,
    )

    assert min_kw.target_place == 4
    predictor.get_target_position_for_strategy_mode.assert_called_once()
