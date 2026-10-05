"""Контракт ``coordinator-session-v1``.

Spec ``clickhouse-migration-lifecycle``, задача 2.2. Сессия координатора
берёт ``pg_try_advisory_lock`` или, только при явном ожидании,
``pg_advisory_lock``. Ключ Alembic, ложный ``try``, смерть сессии и чтение
nonce не отправляют statement. Применённого статуса в координаторе нет.
"""

from __future__ import annotations

import hashlib

import pytest

from scripts.clickhouse_migration_control_plane.coordinator_session import (
    ALEMBIC_LOCK_ID,
    MIGRATION_CONTROL_NAMESPACE_KEY,
    CoordinatorRefusal,
    target_key_for_isolated_default_db,
)
from tests.unit.clickhouse_migration_contract_fixture import (
    SERVER_UUID,
    accepted_schema_request,
    make_coordinator,
    make_target_port,
)

pytestmark = pytest.mark.unit


def _expected_target_key(server_uuid: str) -> int:
    """Знаковый int32 по формуле spec, независимо от модуля координатора.

    Spec ``clickhouse-migration-lifecycle``: ключ цели — первые четыре
    байта SHA-256 строки UTF-8 с UUID и ``default_db``, big-endian.
    """
    text = f"clickhouse-migration-control\n{server_uuid}\ndefault_db"
    digest = hashlib.sha256(text.encode("utf-8")).digest()
    return int.from_bytes(digest[:4], byteorder="big", signed=True)


def test_namespace_key_is_not_the_alembic_lock() -> None:
    """Пространство имён migration-control не равно ``731984123``.

    Spec ``clickhouse-migration-lifecycle``: ключ Alembic не является
    блокировкой этого control plane.
    """
    assert ALEMBIC_LOCK_ID == 731984123
    assert MIGRATION_CONTROL_NAMESPACE_KEY != ALEMBIC_LOCK_ID


def test_try_acquire_records_two_argument_lock() -> None:
    """Обычный захват — ``pg_try_advisory_lock`` и ключ цели.

    Spec ``clickhouse-migration-lifecycle``: по умолчанию неблокирующий
    захват на паре namespace и ``target_key``.
    """
    session = make_coordinator()

    acquired = session.acquire()

    assert acquired is True
    assert session.held is True
    assert len(session.calls) == 1
    call = session.calls[0]
    assert call.function == "pg_try_advisory_lock"
    assert call.namespace_key == MIGRATION_CONTROL_NAMESPACE_KEY
    assert call.namespace_key != ALEMBIC_LOCK_ID
    assert call.target_key == _expected_target_key(SERVER_UUID)
    assert call.target_key == target_key_for_isolated_default_db(SERVER_UUID)
    assert -(2**31) <= call.target_key < 2**31


def test_blocking_lock_only_when_operator_wait_is_explicit() -> None:
    """``pg_advisory_lock`` только при явном ожидании оператора.

    Spec ``clickhouse-migration-lifecycle``: блокирующий захват — тот же
    ключ и та же сессия, но не режим по умолчанию.
    """
    waiting = make_coordinator()
    default = make_coordinator()

    waiting.acquire(operator_wait=True)
    default.acquire()

    assert waiting.calls[0].function == "pg_advisory_lock"
    assert waiting.calls[0].target_key == _expected_target_key(SERVER_UUID)
    assert default.calls[0].function == "pg_try_advisory_lock"
    assert all(call.function != "pg_advisory_lock" for call in default.calls)


def test_false_try_sends_no_statement() -> None:
    """Ложный ``pg_try_advisory_lock`` не вызывает порт.

    Spec ``clickhouse-migration-lifecycle``: конкуренция lock запрещает
    statement. Подстановка не должна отправить SQL «вместо» отказа.
    """
    session = make_coordinator(try_acquire_returns=False)
    port = make_target_port()
    request = accepted_schema_request()

    acquired = session.acquire()
    with pytest.raises(CoordinatorRefusal) as refused:
        session.send_statement(port, request)

    assert acquired is False
    assert session.held is False
    assert refused.value.code == "blocked_lock_contention"
    assert port.executed == ()
    assert session.statements_sent == ()


def test_lock_is_held_across_mutation() -> None:
    """Удержанный захват переживает отправку statement.

    Spec ``clickhouse-migration-lifecycle``: сессия остаётся держателем
    lock на время мутации и не пишет applied-status.
    """
    session = make_coordinator()
    port = make_target_port()
    request = accepted_schema_request()

    assert session.acquire() is True
    session.send_statement(port, request)

    assert session.held is True
    assert session.statements_sent == (request.sql,)
    assert port.executed == (request,)
    assert [call.function for call in session.calls] == ["pg_try_advisory_lock"]
    assert "applied" not in session.__dict__


def test_session_death_stops_the_next_statement() -> None:
    """Смерть сессии не пускает следующий statement.

    Spec ``clickhouse-migration-lifecycle``: потеря координатора
    останавливает SQL. Уже отправленный statement не откатывается портом.
    """
    session = make_coordinator()
    port = make_target_port()
    request = accepted_schema_request()
    session.acquire()
    session.send_statement(port, request)

    session.mark_session_dead()
    with pytest.raises(CoordinatorRefusal) as refused:
        session.send_statement(port, request)

    assert refused.value.code == "coordinator_session_lost"
    assert session.held is False
    assert len(port.executed) == 1
    assert session.statements_sent == (request.sql,)


def test_nonce_read_is_not_an_acquire() -> None:
    """Чтение nonce не считается захватом.

    Spec ``clickhouse-migration-lifecycle``: append-only fence и последний
    nonce не являются advisory lock.
    """
    session = make_coordinator()

    nonce = session.read_nonce()

    assert nonce == "nonce-observed"
    assert session.held is False
    assert session.calls == ()
    with pytest.raises(CoordinatorRefusal):
        session.send_statement(make_target_port(), accepted_schema_request())


def test_coordinator_stores_no_applied_status() -> None:
    """В сессии координатора нет статуса применённой версии.

    Spec ``clickhouse-migration-lifecycle``: PostgreSQL держит только
    advisory lock. Журнал applied-state здесь не появляется.
    """
    session = make_coordinator()
    session.acquire()
    names = [
        name
        for name in dir(session)
        if "applied" in name.lower() or "version_status" in name.lower()
    ]

    assert names == []
    assert not hasattr(session, "record_applied")
    assert set(session.__dict__) <= {
        "server_uuid",
        "_calls",
        "_held",
        "_alive",
        "_try_acquire_returns",
        "_statements_sent",
    }
