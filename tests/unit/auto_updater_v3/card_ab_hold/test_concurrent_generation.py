"""Concurrent generation / idempotency for ``create_pending_intent_for_generation`` (§22.7.3).

Live PG недоступен в unit CI — in-memory AdvSetting store с asyncio.Lock
симулирует SELECT FOR UPDATE + UNIQUE idempotency key (lock на всю транзакцию).
"""

from __future__ import annotations

import asyncio
from copy import deepcopy
from types import SimpleNamespace
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy.sql.dml import Update

from app.modules.shop_runner.service_manager.services.auto_updater_v3.card_ab_hold.epoch_lifecycle import (
    build_pending_intent_payload,
    build_wb_sync_idempotency_key,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.card_ab_hold.epoch_write import (
    create_pending_intent_for_generation,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.card_ab_hold.mode import (
    CardAbHoldPhase,
)


class _InMemoryAdvStore:
    """Сериализованный in-memory store: транзакция = lock + shared row."""

    def __init__(self, adv: SimpleNamespace) -> None:
        self._lock = asyncio.Lock()
        self._row = deepcopy(adv)
        self._idempotency_keys: set[str] = set()
        if self._row.card_ab_hold_wb_sync_idempotency_key:
            self._idempotency_keys.add(
                str(self._row.card_ab_hold_wb_sync_idempotency_key)
            )

    def session_factory(self) -> MagicMock:
        store = self

        class _Session:
            async def execute(self, stmt: Any) -> MagicMock:
                mock_result = MagicMock()
                if isinstance(stmt, Update):
                    current_gen = int(store._row.card_ab_hold_generation or 0)
                    next_gen = current_gen + 1
                    idem_key = build_wb_sync_idempotency_key(
                        int(store._row.adv_id), next_gen
                    )
                    if store._row.card_ab_hold_wb_sync_idempotency_key == idem_key:
                        return mock_result
                    if idem_key in store._idempotency_keys:
                        return mock_result
                    payload = build_pending_intent_payload(
                        generation=next_gen,
                        keywords=list(
                            store._row.card_ab_hold_confirmed_keywords_json or []
                        ),
                        target_places=dict(
                            store._row.card_ab_hold_confirmed_target_places_json or {}
                        ),
                        auto_participation=bool(
                            store._row.card_ab_hold_confirmed_auto_participation
                        ),
                        auto_bid=float(store._row.card_ab_hold_confirmed_auto_bid or 0),
                    )
                    store._row.card_ab_hold_generation = next_gen
                    store._row.card_ab_hold_wb_sync_idempotency_key = idem_key
                    store._row.card_ab_hold_pending_intent_json = payload
                    store._row.card_ab_hold_phase = (
                        CardAbHoldPhase.PENDING_INTENT.value
                    )
                    store._row.card_ab_hold_sync_status = "pending"
                    store._idempotency_keys.add(idem_key)
                else:
                    mock_result.scalar_one.return_value = store._row
                return mock_result

            async def commit(self) -> None:
                return None

        mock_cm = MagicMock()
        lock = store._lock

        async def _aenter(*_args: object, **_kwargs: object) -> _Session:
            await lock.acquire()
            return _Session()

        async def _aexit(*_args: object, **_kwargs: object) -> None:
            lock.release()

        mock_cm.__aenter__ = _aenter
        mock_cm.__aexit__ = _aexit
        return mock_cm


def _complete_adv(*, adv_setting_id: int = 1, adv_id: int = 9001) -> SimpleNamespace:
    return SimpleNamespace(
        id=adv_setting_id,
        adv_id=adv_id,
        card_ab_hold_generation=0,
        card_ab_hold_wb_sync_idempotency_key=None,
        card_ab_hold_confirmed_keywords_json=["alpha"],
        card_ab_hold_confirmed_target_places_json={"alpha": 5},
        card_ab_hold_confirmed_auto_participation=True,
        card_ab_hold_confirmed_auto_bid=100.0,
        card_ab_hold_pending_intent_json=None,
        card_ab_hold_phase=CardAbHoldPhase.AWAITING_AUTO_BID_CONFIRM.value,
        card_ab_hold_sync_status="none",
    )


@pytest.mark.unit
@pytest.mark.asyncio
async def test_concurrent_generation_only_one_wins() -> None:
    """Два параллельных вызова: один intent, второй duplicate no-op (§22.7.3)."""
    adv_setting_id = 1
    store = _InMemoryAdvStore(_complete_adv(adv_setting_id=adv_setting_id))

    with patch(
        "app.modules.shop_runner.service_manager.services.auto_updater_v3.card_ab_hold.epoch_write.sm",
        return_value=store.session_factory(),
    ):
        results = await asyncio.gather(
            create_pending_intent_for_generation(adv_setting_id, adv_id=9001),
            create_pending_intent_for_generation(adv_setting_id, adv_id=9001),
        )

    assert sorted(results) == [False, True]
    assert store._row.card_ab_hold_generation == 1
    assert store._row.card_ab_hold_pending_intent_json is not None
    assert int(store._row.card_ab_hold_pending_intent_json["generation"]) == 1


@pytest.mark.unit
@pytest.mark.asyncio
async def test_duplicate_intent_retry_reuses_same_generation_and_key() -> None:
    """Повтор после победы: тот же generation + idempotency key → no-op."""
    adv_setting_id = 2
    store = _InMemoryAdvStore(
        _complete_adv(adv_setting_id=adv_setting_id, adv_id=8002)
    )

    with patch(
        "app.modules.shop_runner.service_manager.services.auto_updater_v3.card_ab_hold.epoch_write.sm",
        return_value=store.session_factory(),
    ):
        first = await create_pending_intent_for_generation(adv_setting_id, adv_id=8002)
        second = await create_pending_intent_for_generation(adv_setting_id, adv_id=8002)

    assert first is True
    assert second is False
    expected_key = build_wb_sync_idempotency_key(8002, 1)
    assert store._row.card_ab_hold_generation == 1
    assert store._row.card_ab_hold_wb_sync_idempotency_key == expected_key


@pytest.mark.unit
@pytest.mark.asyncio
async def test_loser_keeps_prior_generation_on_duplicate_key() -> None:
    """Duplicate idempotency key до bump — generation остаётся прежним."""
    adv_id = 7007
    adv = _complete_adv(adv_setting_id=3, adv_id=adv_id)
    adv.card_ab_hold_generation = 2
    adv.card_ab_hold_wb_sync_idempotency_key = build_wb_sync_idempotency_key(adv_id, 3)
    adv.card_ab_hold_pending_intent_json = {"generation": 2}

    mock_result = MagicMock()
    mock_result.scalar_one.return_value = adv
    mock_session = AsyncMock()
    mock_session.execute = AsyncMock(return_value=mock_result)
    mock_session.commit = AsyncMock()
    mock_cm = MagicMock()
    mock_cm.__aenter__ = AsyncMock(return_value=mock_session)
    mock_cm.__aexit__ = AsyncMock(return_value=None)

    with patch(
        "app.modules.shop_runner.service_manager.services.auto_updater_v3.card_ab_hold.epoch_write.sm",
        return_value=mock_cm,
    ):
        created = await create_pending_intent_for_generation(3, adv_id=adv_id)

    assert created is False
    mock_session.commit.assert_not_called()
    assert adv.card_ab_hold_generation == 2
    assert adv.card_ab_hold_wb_sync_idempotency_key == build_wb_sync_idempotency_key(
        adv_id, 3
    )
