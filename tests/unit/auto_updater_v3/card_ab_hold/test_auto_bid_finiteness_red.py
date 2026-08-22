"""RED regression tests for finite Auto-bid confirmation values."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.modules.shop_runner.service_manager.services.auto_updater_v3.card_ab_hold.epoch_write import (
    EpochWriteError,
    confirm_auto_bid_in_session,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.card_ab_hold.mode import (
    CardAbHoldPhase,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.card_ab_hold.telegram.confirm_handlers import (
    _parse_auto_bid_text,
)


@pytest.mark.unit
@pytest.mark.parametrize(
    "text",
    [
        "NaN",
        "Infinity",
        "-Infinity",
    ],
    ids=[
        "CAH-CONFIRM-005-PARSER-NAN-001",
        "CAH-CONFIRM-005-PARSER-POSITIVE-INF-001",
        "CAH-CONFIRM-005-PARSER-NEGATIVE-INF-001",
    ],
)
def test_auto_bid_parser_rejects_nonfinite_values(text: str) -> None:
    """CAH-CONFIRM-005: parser must fail closed for every non-finite value."""
    assert _parse_auto_bid_text(text) is None


@pytest.mark.unit
@pytest.mark.asyncio
@pytest.mark.parametrize(
    "bid",
    [
        float("nan"),
        float("inf"),
        float("-inf"),
    ],
    ids=[
        "CAH-CONFIRM-005-WRITER-NAN-001",
        "CAH-CONFIRM-005-WRITER-POSITIVE-INF-001",
        "CAH-CONFIRM-005-WRITER-NEGATIVE-INF-001",
    ],
)
async def test_auto_bid_writer_rejects_nonfinite_before_durable_update(
    bid: float,
) -> None:
    """CAH-CONFIRM-005: writer must reject non-finite bids before commit."""
    adv = SimpleNamespace(
        adv_id=4242,
        card_ab_hold_phase=CardAbHoldPhase.AWAITING_AUTO_BID_CONFIRM.value,
    )
    result = MagicMock()
    result.scalar_one.return_value = adv
    session = AsyncMock()
    session.execute = AsyncMock(return_value=result)
    session.commit = AsyncMock()

    with pytest.raises(EpochWriteError, match="finite"):
        await confirm_auto_bid_in_session(session, 42, bid)

    assert session.execute.await_count <= 1
    session.commit.assert_not_awaited()
