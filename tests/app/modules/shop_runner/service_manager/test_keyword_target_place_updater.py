"""Tests for KeywordTargetPlaceUpdater."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.modules.shop_runner.service_manager.services.keywords_target_place_updater import (
    KeywordTargetPlaceUpdater,
)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_set_new_target_places_normalizes_zero_to_fallback():
    """When target_places dict contains 0 or negative, keyword.target_place is set to 2, never 0."""
    mock_keyword = MagicMock()
    mock_keyword.text = "key"

    mock_result = MagicMock()
    mock_result.scalars().all.return_value = [mock_keyword]

    mock_session = AsyncMock()
    mock_session.execute = AsyncMock(return_value=mock_result)

    class AsyncCtx:
        async def __aenter__(self):
            return mock_session

        async def __aexit__(self, *args):
            return None

    def fake_sm(*, read_only: bool = True):
        return AsyncCtx()

    mock_adv = MagicMock()
    mock_adv.adv_setting_original_id = 1
    mock_adv.adv_id = 100

    with patch(
        "app.modules.shop_runner.service_manager.services.keywords_target_place_updater.keyword_target_place_updater.sm",
        fake_sm,
    ):
        await KeywordTargetPlaceUpdater._set_new_target_places(
            mock_adv,
            target_places={"key": 0},
        )

    assert mock_keyword.target_place == 2


@pytest.mark.unit
@pytest.mark.asyncio
async def test_set_new_target_places_normalizes_negative_to_fallback():
    """When target_places dict contains negative value, keyword.target_place is set to 2."""
    mock_keyword = MagicMock()
    mock_keyword.text = "kw"

    mock_result = MagicMock()
    mock_result.scalars().all.return_value = [mock_keyword]

    mock_session = AsyncMock()
    mock_session.execute = AsyncMock(return_value=mock_result)

    class AsyncCtx:
        async def __aenter__(self):
            return mock_session

        async def __aexit__(self, *args):
            return None

    def fake_sm(*, read_only: bool = True):
        return AsyncCtx()

    mock_adv = MagicMock()
    mock_adv.adv_setting_original_id = 1
    mock_adv.adv_id = 100

    with patch(
        "app.modules.shop_runner.service_manager.services.keywords_target_place_updater.keyword_target_place_updater.sm",
        fake_sm,
    ):
        await KeywordTargetPlaceUpdater._set_new_target_places(
            mock_adv,
            target_places={"kw": -5},
        )

    assert mock_keyword.target_place == 2
