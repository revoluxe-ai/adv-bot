"""PgBouncer-safe coordinator tests."""

from __future__ import annotations

from contextlib import asynccontextmanager
from types import SimpleNamespace

import pytest
from sqlalchemy.exc import SQLAlchemyError

import app.modules.campaign_settings_history.coordinator as coordinator_module
from app.modules.campaign_settings_history.coordinator import (
    PostgresTransactionCoordinator,
    locked_cabinet_transaction,
    validate_cabinet_lock_key,
)

pytestmark = pytest.mark.unit


class _ScalarResult:
    def __init__(self, value: object) -> None:
        self._value = value

    def scalar_one(self) -> object:
        return self._value


class _Begin:
    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return None


class _FakeSession:
    def __init__(self, *, lock_result: bool = True) -> None:
        self.is_active = True
        self._in_transaction = False
        self.lock_result = lock_result
        self.calls: list[tuple[str, dict[str, object] | None]] = []
        self.fail_select_one = False

    def in_transaction(self):
        return self._in_transaction

    def begin(self):
        session = self

        class _Tx:
            async def __aenter__(self_inner):
                session._in_transaction = True
                return self_inner

            async def __aexit__(self_inner, exc_type, exc, tb):
                session._in_transaction = False
                return None

        return _Tx()

    async def execute(self, statement, params=None):
        sql = str(statement)
        self.calls.append((sql, params))
        if sql.strip() == "SELECT 1" and self.fail_select_one:
            raise SQLAlchemyError("connection lost")
        if "pg_try_advisory_xact_lock" in sql:
            return _ScalarResult(self.lock_result)
        return _ScalarResult(1)


@pytest.mark.parametrize("bad", [2**31, -(2**31) - 1, True, "77"])
def test_lock_key_fails_closed_outside_int32_or_non_int(bad) -> None:
    with pytest.raises(ValueError):
        validate_cabinet_lock_key(bad)


def test_lock_key_accepts_int32_boundary() -> None:
    validate_cabinet_lock_key(-(2**31))
    validate_cabinet_lock_key(2**31 - 1)


@pytest.mark.asyncio
async def test_transaction_alive_probes_same_open_transaction() -> None:
    session = _FakeSession()
    session._in_transaction = True
    coordinator = PostgresTransactionCoordinator(session)  # type: ignore[arg-type]

    assert await coordinator.transaction_alive() is True
    assert session.calls[-1][0].strip() == "SELECT 1"


@pytest.mark.asyncio
async def test_transaction_alive_fails_closed_on_probe_error() -> None:
    session = _FakeSession()
    session._in_transaction = True
    session.fail_select_one = True
    coordinator = PostgresTransactionCoordinator(session)  # type: ignore[arg-type]

    assert await coordinator.transaction_alive() is False


@pytest.mark.asyncio
async def test_locked_cabinet_uses_xact_lock_and_holds_transaction(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    session = _FakeSession(lock_result=True)

    @asynccontextmanager
    async def fake_session_maker(*, read_only: bool = False):
        assert read_only is False
        yield session

    monkeypatch.setattr(
        coordinator_module,
        "get_async_session_maker",
        fake_session_maker,
    )

    async with locked_cabinet_transaction(77) as locked:
        assert locked.acquired is True
        assert locked.session is session
        assert session.in_transaction() is True
        lock_sql, params = session.calls[0]
        assert "pg_try_advisory_xact_lock" in lock_sql
        assert "pg_try_advisory_lock(" not in lock_sql
        assert params == {
            "namespace_key": 1129531441,
            "object_key": 77,
        }

    assert session.in_transaction() is False


@pytest.mark.asyncio
async def test_lock_contention_yields_unowned_transaction(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    session = _FakeSession(lock_result=False)

    @asynccontextmanager
    async def fake_session_maker(*, read_only: bool = False):
        yield session

    monkeypatch.setattr(
        coordinator_module,
        "get_async_session_maker",
        fake_session_maker,
    )

    async with locked_cabinet_transaction(77) as locked:
        assert locked.acquired is False
        assert session.in_transaction() is True
