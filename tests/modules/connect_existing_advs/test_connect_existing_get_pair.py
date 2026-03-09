"""Unit tests for _get_existing_adv_pair_not_done helper."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.client_bot.user_interface.handlers import connect_existing_advs

MODULE = "app.client_bot.user_interface.handlers.connect_existing_advs"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_existing_adv_pair_not_done_returns_tuple_when_one_row() -> None:
    """One row with adv_id=10, search_adv_id=20, active_status != done -> (10, 20)."""
    mock_adv = MagicMock()
    mock_adv.adv_id = 10
    mock_adv.search_adv_id = 20
    mock_result = MagicMock()
    mock_result.scalars.return_value.one_or_none.return_value = mock_adv
    mock_session = MagicMock()
    mock_session.execute = AsyncMock(return_value=mock_result)
    mock_sm = MagicMock()
    mock_sm.return_value.__aenter__ = AsyncMock(return_value=mock_session)
    mock_sm.return_value.__aexit__ = AsyncMock(return_value=None)

    with patch(f"{MODULE}.sm", mock_sm):
        out = await connect_existing_advs._get_existing_adv_pair_not_done(
            wb_cabinet_id=1, nmid=100
        )

    assert out == (10, 20)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_existing_adv_pair_not_done_returns_none_when_done() -> None:
    """When query returns no row (e.g. only done record) -> None."""
    mock_result = MagicMock()
    mock_result.scalars.return_value.one_or_none.return_value = None
    mock_session = MagicMock()
    mock_session.execute = AsyncMock(return_value=mock_result)
    mock_sm = MagicMock()
    mock_sm.return_value.__aenter__ = AsyncMock(return_value=mock_session)
    mock_sm.return_value.__aexit__ = AsyncMock(return_value=None)

    with patch(f"{MODULE}.sm", mock_sm):
        out = await connect_existing_advs._get_existing_adv_pair_not_done(
            wb_cabinet_id=1, nmid=100
        )

    assert out is None


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_existing_adv_pair_not_done_returns_none_when_no_row() -> None:
    """When no matching row -> None."""
    mock_result = MagicMock()
    mock_result.scalars.return_value.one_or_none.return_value = None
    mock_session = MagicMock()
    mock_session.execute = AsyncMock(return_value=mock_result)
    mock_sm = MagicMock()
    mock_sm.return_value.__aenter__ = AsyncMock(return_value=mock_session)
    mock_sm.return_value.__aexit__ = AsyncMock(return_value=None)

    with patch(f"{MODULE}.sm", mock_sm):
        out = await connect_existing_advs._get_existing_adv_pair_not_done(
            wb_cabinet_id=99, nmid=200
        )

    assert out is None
