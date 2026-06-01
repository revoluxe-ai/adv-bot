"""Unit-тесты классификации httpx timeout в with_raise_errors."""

from unittest.mock import AsyncMock, MagicMock

import httpcore
import httpx
import pytest

from app.core.mp.wb.api.adapter.raise_errors import with_raise_errors
from app.core.mp.wb.api.adapter.sections_enum import SectionsEnum
from app.core.mp.wb.api.excs import HttpTimeOutError, PoolTimeoutError


def _make_client(section: SectionsEnum = SectionsEnum.PROMOTION) -> MagicMock:
    client = MagicMock()
    client.section = section
    return client


@pytest.mark.unit
@pytest.mark.asyncio
async def test_httpx_pool_timeout_classified_separately() -> None:
    method = AsyncMock(
        side_effect=httpx.PoolTimeout("pool exhausted", request=MagicMock())
    )
    client = _make_client()

    with pytest.raises(PoolTimeoutError) as exc_info:
        await with_raise_errors(method, client, ids="1,2,3")

    assert isinstance(exc_info.value, PoolTimeoutError)
    assert exc_info.value.exc_type == "PoolTimeout"
    assert isinstance(exc_info.value.original_exc, httpx.PoolTimeout)
    method.assert_awaited_once()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_httpcore_pool_timeout_classified_separately() -> None:
    method = AsyncMock(side_effect=httpcore.PoolTimeout("pool exhausted"))
    client = _make_client()

    with pytest.raises(PoolTimeoutError) as exc_info:
        await with_raise_errors(method, client, ids="1,2,3")

    assert isinstance(exc_info.value, PoolTimeoutError)
    assert exc_info.value.exc_type == "PoolTimeout"
    assert isinstance(exc_info.value.original_exc, httpcore.PoolTimeout)
    method.assert_awaited_once()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_read_timeout_remains_http_timeout_error() -> None:
    method = AsyncMock(
        side_effect=httpx.ReadTimeout("read timed out", request=MagicMock())
    )
    client = _make_client(SectionsEnum.ANALYTIC_AND_DATA)

    with pytest.raises(HttpTimeOutError) as exc_info:
        await with_raise_errors(method, client)

    assert type(exc_info.value) is HttpTimeOutError
    assert "exc_type=ReadTimeout" in str(exc_info.value)
    method.assert_awaited_once()
