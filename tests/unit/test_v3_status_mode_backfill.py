"""Unit tests: backfill ``strategy_mode`` для V3 после включения версии."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.modules.common_slaves.wildberries.models.enums import KeywordStrategyMode
from app.modules.common_slaves.wildberries.models.enums.strategy import Strategy
from app.modules.shop_runner.service_manager.services.v3_status_mode_backfill import (
    backfill_v3_hard_statuses_and_states_consistency,
)


@pytest.mark.asyncio
async def test_backfill_repairs_auto_keyword_with_min_cpa_for_single_adv() -> None:
    kw = MagicMock()
    kw.hard_status = 1
    kw.strategy_mode = KeywordStrategyMode.MIN_CPA

    session = MagicMock()
    execute_result = MagicMock()
    execute_result.all.return_value = [(kw, 3, Strategy.MIN_CPO)]
    session.execute = AsyncMock(return_value=execute_result)
    session.commit = AsyncMock()

    cm = MagicMock()
    cm.__aenter__ = AsyncMock(return_value=session)
    cm.__aexit__ = AsyncMock(return_value=None)

    with patch(
        "app.modules.shop_runner.service_manager.services.v3_status_mode_backfill.sm",
        return_value=cm,
    ):
        count = await backfill_v3_hard_statuses_and_states_consistency(
            dry_run=False,
            adv_setting_id=99,
        )

    assert count == 1
    assert kw.strategy_mode == KeywordStrategyMode.OFF
    session.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_backfill_dry_run_does_not_mutate() -> None:
    kw = MagicMock()
    kw.hard_status = 1
    kw.strategy_mode = KeywordStrategyMode.MIN_CPA

    session = MagicMock()
    execute_result = MagicMock()
    execute_result.all.return_value = [(kw, 3, Strategy.MIN_CPO)]
    session.execute = AsyncMock(return_value=execute_result)
    session.commit = AsyncMock()

    cm = MagicMock()
    cm.__aenter__ = AsyncMock(return_value=session)
    cm.__aexit__ = AsyncMock(return_value=None)

    with patch(
        "app.modules.shop_runner.service_manager.services.v3_status_mode_backfill.sm",
        return_value=cm,
    ):
        count = await backfill_v3_hard_statuses_and_states_consistency(
            dry_run=True,
            adv_setting_id=99,
        )

    assert count == 1
    assert kw.strategy_mode == KeywordStrategyMode.MIN_CPA
    session.commit.assert_not_awaited()


@pytest.mark.asyncio
async def test_backfill_repairs_fixed_phrase_to_max_for_max_conv_adv() -> None:
    kw = MagicMock()
    kw.hard_status = 4
    kw.strategy_mode = KeywordStrategyMode.MIN_CPA

    session = MagicMock()
    execute_result = MagicMock()
    execute_result.all.return_value = [(kw, 3, Strategy.MAX_CONV)]
    session.execute = AsyncMock(return_value=execute_result)
    session.commit = AsyncMock()

    cm = MagicMock()
    cm.__aenter__ = AsyncMock(return_value=session)
    cm.__aexit__ = AsyncMock(return_value=None)

    with patch(
        "app.modules.shop_runner.service_manager.services.v3_status_mode_backfill.sm",
        return_value=cm,
    ):
        count = await backfill_v3_hard_statuses_and_states_consistency(
            dry_run=False,
            adv_setting_id=99,
        )

    assert count == 1
    assert kw.strategy_mode == KeywordStrategyMode.MAX_CONVERSION


@pytest.mark.asyncio
async def test_backfill_repairs_fixed_phrase_to_optimum_for_optimum_adv() -> None:
    kw = MagicMock()
    kw.hard_status = 4
    kw.strategy_mode = KeywordStrategyMode.MIN_CPA

    session = MagicMock()
    execute_result = MagicMock()
    execute_result.all.return_value = [(kw, 3, Strategy.OPTIMUM)]
    session.execute = AsyncMock(return_value=execute_result)
    session.commit = AsyncMock()

    cm = MagicMock()
    cm.__aenter__ = AsyncMock(return_value=session)
    cm.__aexit__ = AsyncMock(return_value=None)

    with patch(
        "app.modules.shop_runner.service_manager.services.v3_status_mode_backfill.sm",
        return_value=cm,
    ):
        count = await backfill_v3_hard_statuses_and_states_consistency(
            dry_run=False,
            adv_setting_id=99,
        )

    assert count == 1
    assert kw.strategy_mode == KeywordStrategyMode.OPTIMUM
