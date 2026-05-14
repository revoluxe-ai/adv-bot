"""Tests for KeywordTargetPlaceUpdater."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.modules.shop_runner.service_manager.services.keywords_target_place_updater import (
    KeywordTargetPlaceUpdater,
)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_set_new_target_places_invalid_zero_clears_target_place():
    """When target_places dict contains 0, keyword.target_place is cleared (None)."""
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

    assert mock_keyword.target_place is None


@pytest.mark.unit
@pytest.mark.asyncio
async def test_set_new_target_places_invalid_negative_clears_target_place():
    """When target_places dict contains negative value, keyword.target_place is cleared (None)."""
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

    assert mock_keyword.target_place is None


@pytest.mark.unit
@pytest.mark.asyncio
async def test_set_new_target_places_missing_key_clears_target_place():
    """When keyword is absent from target_places, target_place is set to None."""
    mock_keyword = MagicMock()
    mock_keyword.text = "orphan"

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
    mock_adv.adv_id = 200

    with patch(
        "app.modules.shop_runner.service_manager.services.keywords_target_place_updater.keyword_target_place_updater.sm",
        fake_sm,
    ):
        await KeywordTargetPlaceUpdater._set_new_target_places(mock_adv, target_places={})

    assert mock_keyword.target_place is None


@pytest.mark.unit
@pytest.mark.asyncio
async def test_set_new_target_places_valid_value_persisted():
    mock_keyword = MagicMock()
    mock_keyword.text = "good"

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
    mock_adv.adv_id = 300

    with patch(
        "app.modules.shop_runner.service_manager.services.keywords_target_place_updater.keyword_target_place_updater.sm",
        fake_sm,
    ):
        await KeywordTargetPlaceUpdater._set_new_target_places(
            mock_adv,
            target_places={"good": 7},
        )

    assert mock_keyword.target_place == 7
