from __future__ import annotations

import pytest

from app.core.mp.wb.api.adapter.promotion_client.normquery_bids.catch_special_errors import (
    catch_special_errors,
)
from app.core.mp.wb.api.excs import BadRequestError


@pytest.mark.unit
@pytest.mark.asyncio
async def test_catch_special_errors_known_message_returns_none() -> None:
    async def _raise_known() -> int:
        raise BadRequestError("norm_query disabled for nm 123")

    result = await catch_special_errors(_raise_known())
    assert result is None


@pytest.mark.unit
@pytest.mark.asyncio
async def test_catch_special_errors_none_detail_does_not_crash() -> None:
    async def _raise_none_detail() -> int:
        err = BadRequestError("placeholder")
        err.detail = None  # type: ignore[assignment]
        raise err

    with pytest.raises(BadRequestError):
        await catch_special_errors(_raise_none_detail())


@pytest.mark.unit
@pytest.mark.asyncio
async def test_catch_special_errors_non_string_detail_does_not_crash() -> None:
    async def _raise_non_string_detail() -> int:
        err = BadRequestError("placeholder")
        err.detail = {"detail": "not a string"}  # type: ignore[assignment]
        raise err

    with pytest.raises(BadRequestError):
        await catch_special_errors(_raise_non_string_detail())
