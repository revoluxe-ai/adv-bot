from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.core.mp.wb.api.domain_managers.promotion.promotion_manager import (
    PromotionManager,
    _extract_invalid_norm_query,
)
from app.core.mp.wb.api.excs import BadRequestError


@pytest.mark.unit
@pytest.mark.asyncio
async def test_set_minus_phrases_with_fallback_drops_one_invalid_phrase() -> None:
    manager = PromotionManager(promotion_client=MagicMock())
    calls: list[list[str]] = []

    async def _fake_set_minus(
        advert_id: int, nm_id: int, phrases: list[str]
    ) -> None:
        assert advert_id == 101
        assert nm_id == 202
        calls.append(list(phrases))
        if "bad" in phrases:
            raise BadRequestError(
                json.dumps({"detail": "norm_query 'bad' is not valid for nm 202"})
            )

    manager.set_minus_phrases = AsyncMock(side_effect=_fake_set_minus)  # type: ignore[method-assign]

    result = await manager.set_minus_phrases_with_fallback(
        advert_id=101,
        nm_id=202,
        phrases=["good", "bad"],
    )

    assert calls == [["good", "bad"], ["good"]]
    assert result.applied_phrases == ["good"]
    assert result.dropped_invalid_phrases == ["bad"]
    assert result.attempts == 2


@pytest.mark.unit
@pytest.mark.asyncio
async def test_set_minus_phrases_with_fallback_drops_several_invalid_phrases() -> None:
    manager = PromotionManager(promotion_client=MagicMock())
    calls: list[list[str]] = []

    async def _fake_set_minus(
        advert_id: int, nm_id: int, phrases: list[str]
    ) -> None:
        assert advert_id == 11
        assert nm_id == 22
        calls.append(list(phrases))
        if "bad1" in phrases:
            raise BadRequestError(
                json.dumps({"detail": "norm_query 'bad1' is not valid for nm 22"})
            )
        if "bad2" in phrases:
            raise BadRequestError(
                json.dumps({"detail": "norm_query 'bad2' is not valid for nm 22"})
            )

    manager.set_minus_phrases = AsyncMock(side_effect=_fake_set_minus)  # type: ignore[method-assign]

    result = await manager.set_minus_phrases_with_fallback(
        advert_id=11,
        nm_id=22,
        phrases=["good", "bad1", "bad2"],
    )

    assert calls == [
        ["good", "bad1", "bad2"],
        ["good", "bad2"],
        ["good"],
    ]
    assert result.applied_phrases == ["good"]
    assert result.dropped_invalid_phrases == ["bad1", "bad2"]
    assert result.attempts == 3


@pytest.mark.unit
@pytest.mark.asyncio
async def test_set_minus_phrases_with_fallback_skips_unsupported_campaign_type() -> None:
    manager = PromotionManager(promotion_client=MagicMock())
    manager.set_minus_phrases = AsyncMock(  # type: ignore[method-assign]
        side_effect=BadRequestError(
            json.dumps(
                {
                    "detail": "only for campaigns with manual bid, search placement",
                    "status": 400,
                }
            )
        )
    )

    result = await manager.set_minus_phrases_with_fallback(
        advert_id=32824944,
        nm_id=100,
        phrases=["bad_phrase"],
    )

    manager.set_minus_phrases.assert_awaited_once_with(32824944, 100, ["bad_phrase"])
    assert result.applied_phrases == []
    assert result.dropped_invalid_phrases == []
    assert result.skipped_unsupported_campaign is True
    assert result.attempts == 1


@pytest.mark.unit
@pytest.mark.asyncio
async def test_set_minus_phrases_with_fallback_propagates_unrelated_bad_request() -> None:
    manager = PromotionManager(promotion_client=MagicMock())
    manager.set_minus_phrases = AsyncMock(  # type: ignore[method-assign]
        side_effect=BadRequestError(json.dumps({"detail": "some other validation"}))
    )

    with pytest.raises(BadRequestError):
        await manager.set_minus_phrases_with_fallback(
            advert_id=1,
            nm_id=2,
            phrases=["good"],
        )


@pytest.mark.unit
@pytest.mark.asyncio
async def test_set_minus_phrases_with_fallback_succeeds_on_first_attempt() -> None:
    manager = PromotionManager(promotion_client=MagicMock())
    manager.set_minus_phrases = AsyncMock(return_value=None)  # type: ignore[method-assign]

    result = await manager.set_minus_phrases_with_fallback(
        advert_id=42,
        nm_id=77,
        phrases=["one", "two"],
    )

    manager.set_minus_phrases.assert_awaited_once_with(42, 77, ["one", "two"])
    assert result.applied_phrases == ["one", "two"]
    assert result.dropped_invalid_phrases == []
    assert result.attempts == 1


@pytest.mark.unit
@pytest.mark.asyncio
async def test_set_minus_phrases_with_fallback_empty_phrases_returns_success() -> None:
    manager = PromotionManager(promotion_client=MagicMock())
    manager.set_minus_phrases = AsyncMock(return_value=None)  # type: ignore[method-assign]

    result = await manager.set_minus_phrases_with_fallback(
        advert_id=42,
        nm_id=77,
        phrases=[],
    )

    manager.set_minus_phrases.assert_awaited_once_with(42, 77, [])
    assert result.applied_phrases == []
    assert result.dropped_invalid_phrases == []
    assert result.attempts == 1


@pytest.mark.unit
@pytest.mark.asyncio
async def test_set_minus_phrases_with_fallback_deduplicates_input_phrases() -> None:
    manager = PromotionManager(promotion_client=MagicMock())
    calls: list[list[str]] = []

    async def _fake_set_minus(advert_id: int, nm_id: int, phrases: list[str]) -> None:
        assert advert_id == 100
        assert nm_id == 200
        calls.append(list(phrases))

    manager.set_minus_phrases = AsyncMock(side_effect=_fake_set_minus)  # type: ignore[method-assign]

    result = await manager.set_minus_phrases_with_fallback(
        advert_id=100,
        nm_id=200,
        phrases=["dup", "keep", "dup", "keep", "new"],
    )

    assert calls == [["dup", "keep", "new"]]
    assert result.applied_phrases == ["dup", "keep", "new"]
    assert result.dropped_invalid_phrases == []
    assert result.attempts == 1


@pytest.mark.unit
@pytest.mark.asyncio
async def test_set_minus_phrases_with_fallback_raises_when_max_attempts_exceeded() -> None:
    manager = PromotionManager(promotion_client=MagicMock())
    manager.set_minus_phrases = AsyncMock(  # type: ignore[method-assign]
        side_effect=BadRequestError(
            json.dumps({"detail": "norm_query 'bad' is not valid for nm 2"})
        )
    )

    with pytest.raises(BadRequestError, match="Max attempts reached"):
        await manager.set_minus_phrases_with_fallback(
            advert_id=1,
            nm_id=2,
            phrases=["good", "bad"],
            max_attempts=1,
        )


@pytest.mark.unit
@pytest.mark.asyncio
async def test_set_minus_phrases_with_fallback_reraises_when_invalid_not_in_active_list() -> None:
    manager = PromotionManager(promotion_client=MagicMock())
    manager.set_minus_phrases = AsyncMock(  # type: ignore[method-assign]
        side_effect=BadRequestError(
            json.dumps({"detail": "norm_query 'ghost' is not valid for nm 2"})
        )
    )

    with pytest.raises(BadRequestError):
        await manager.set_minus_phrases_with_fallback(
            advert_id=1,
            nm_id=2,
            phrases=["good", "bad"],
        )
    manager.set_minus_phrases.assert_awaited_once()


@pytest.mark.unit
@pytest.mark.parametrize(
    ("detail", "expected"),
    [
        (
            json.dumps({"detail": "norm_query 'abc' is not valid for nm 11"}),
            "abc",
        ),
        ('{"detail":"norm_query \\"abc def\\" is not valid for nm 11"}', "abc def"),
        ("norm_query 'plain text' is not valid for nm 123", "plain text"),
        ("norm_query 'trim me' is not valid for nm", "trim me"),
        (json.dumps({"detail": "other error"}), None),
        ("not json and not pattern", None),
        ("", None),
    ],
)
def test_extract_invalid_norm_query(detail: str, expected: str | None) -> None:
    assert _extract_invalid_norm_query(detail) == expected


@pytest.mark.unit
def test_extract_invalid_norm_query_non_string_detail_is_safe() -> None:
    assert _extract_invalid_norm_query(None) is None  # type: ignore[arg-type]
