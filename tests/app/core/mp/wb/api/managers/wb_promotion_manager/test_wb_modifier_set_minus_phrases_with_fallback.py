"""Unit tests for WBModifier.set_minus_phrases_with_fallback_for_adv."""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from app.core.mp.wb.api.domain_managers.promotion.promotion_manager import (
    PromotionManager,
    SetMinusPhrasesFallbackResult,
)
from app.core.mp.wb.api.managers.wb_promotion_manager.wb_promotion_manager import (
    WBModifier,
)


@pytest.fixture
def mock_promotion_manager() -> AsyncMock:
    return AsyncMock(spec=PromotionManager)


@pytest.fixture
def wb_modifier(mock_promotion_manager: AsyncMock) -> WBModifier:
    return WBModifier(promotion_manager=mock_promotion_manager)


@pytest.mark.asyncio
@pytest.mark.unit
async def test_set_minus_phrases_with_fallback_for_adv_updates_redis_on_success(
    wb_modifier: WBModifier,
    mock_promotion_manager: AsyncMock,
) -> None:
    mock_promotion_manager.set_minus_phrases_with_fallback = AsyncMock(
        return_value=SetMinusPhrasesFallbackResult(
            applied_phrases=["bad"],
            dropped_invalid_phrases=[],
            attempts=1,
            skipped_unsupported_campaign=False,
        )
    )
    update_redis_timestamp_manager = AsyncMock()

    result = await wb_modifier.set_minus_phrases_with_fallback_for_adv(
        adv_id=100,
        nmid=200,
        phrases=["bad"],
        update_redis_timestamp_manager=update_redis_timestamp_manager,
    )

    assert result.applied_phrases == ["bad"]
    update_redis_timestamp_manager.set_one.assert_awaited_once_with(adv_id=100)


@pytest.mark.asyncio
@pytest.mark.unit
async def test_set_minus_phrases_with_fallback_for_adv_skips_redis_when_unsupported(
    wb_modifier: WBModifier,
    mock_promotion_manager: AsyncMock,
) -> None:
    mock_promotion_manager.set_minus_phrases_with_fallback = AsyncMock(
        return_value=SetMinusPhrasesFallbackResult(
            applied_phrases=[],
            dropped_invalid_phrases=[],
            attempts=1,
            skipped_unsupported_campaign=True,
        )
    )
    update_redis_timestamp_manager = AsyncMock()

    result = await wb_modifier.set_minus_phrases_with_fallback_for_adv(
        adv_id=100,
        nmid=200,
        phrases=["bad"],
        update_redis_timestamp_manager=update_redis_timestamp_manager,
    )

    assert result.skipped_unsupported_campaign is True
    update_redis_timestamp_manager.set_one.assert_not_awaited()
