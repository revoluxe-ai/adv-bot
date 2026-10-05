"""Runtime boundary tests for campaign-settings-history."""

from __future__ import annotations

from contextlib import asynccontextmanager
from types import SimpleNamespace

import pytest

import app.modules.campaign_settings_history.runtime as runtime_module

pytestmark = pytest.mark.unit


@pytest.mark.asyncio
async def test_lock_contender_never_reaches_history_compare_or_insert(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Spec campaign-settings-history: only xact-lock owner may touch CH history."""

    @asynccontextmanager
    async def contended(_wb_cabinet_id: int):
        yield SimpleNamespace(acquired=False, session=object())

    async def forbidden_collect(**_kwargs):
        raise AssertionError("lock contender must not reach collector")

    monkeypatch.setattr(
        runtime_module,
        "locked_cabinet_transaction",
        contended,
    )
    monkeypatch.setattr(runtime_module, "collect_cabinet", forbidden_collect)

    result = await runtime_module.collect_one_locked_cabinet(
        wb_cabinet_id=77,
        clickhouse_client=object(),  # type: ignore[arg-type]
    )

    assert result.code == "lock_contended"
    assert result.inserted == 0
    assert result.campaigns_read == 0
