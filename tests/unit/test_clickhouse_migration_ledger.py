"""Журнал цели: идентичность, append и drift.

Spec ``clickhouse-migration-lifecycle``, задачи 6.1 и 6.2. Мутация — реальный
``record_version_event`` и команды ``status`` / ``plan`` / ``apply`` на
подставном порте. PostgreSQL applied-status не пишется. Живого сокета нет.
EVIDENCE_CLASS=side_effect_proof. PROVES: PA_SIDE_EFFECT_PROOF.
"""

from __future__ import annotations

import socket
from pathlib import Path

import pytest

from scripts.clickhouse_migration_control_plane.coordinator_session import (
    RecordingCoordinatorSession,
)
from scripts.clickhouse_migration_control_plane.corpus import (
    canonical_corpus_dir,
    immutable_fingerprint,
)
from scripts.clickhouse_migration_control_plane.ledger import (
    CANONICAL_DATABASE,
    LEDGER_COLUMNS,
    LEDGER_RELATION,
    OPERATOR_STATES,
    LedgerRefusal,
    coordinator_lock_trace,
    ledger_ddl,
    record_version_event,
)
from scripts.clickhouse_migration_control_plane.pre_execution import apply, plan, status
from scripts.clickhouse_migration_control_plane.target_port import (
    IsolatedTargetPort,
    LedgerEvent,
)
from tests.unit.clickhouse_migration_contract_fixture import (
    SERVER_UUID,
    make_coordinator,
    make_target_port,
)

pytestmark = pytest.mark.unit

_HOSTNAME = "clickhouse.internal"
_ZERO_SERVER_UUID = "00000000-0000-0000-0000-000000000000"
_CREATED_AT = "2026-09-29T07:00:00+00:00"


def test_ledger_identity_appends_on_server_uuid_and_default_db(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Журнал цели — append на UUID и ``default_db``, не строка PostgreSQL.

    Spec ``clickhouse-migration-lifecycle``, сценарий ``Ledger identity is
    the server UUID and default_db``. Второе состояние не затирает первое.
    Координатор остаётся следом lock. PROVES: PA_SIDE_EFFECT_PROOF.
    """
    corpus_dir = canonical_corpus_dir()
    before = _snapshot(corpus_dir)
    recorded = immutable_fingerprint()
    port = make_target_port()
    coordinator = make_coordinator()
    _forbid_new_socket(monkeypatch)
    ddl = ledger_ddl()

    assert LEDGER_RELATION == "default_db.ch_schema_migration_ledger"
    assert "ENGINE = MergeTree" in ddl
    assert "ORDER BY (target_id, version_id, event_seq)" in ddl
    assert "ON CLUSTER" not in ddl
    for column in LEDGER_COLUMNS:
        assert column in ddl
    assert {field.name for field in LedgerEvent.__dataclass_fields__.values()} == set(
        LEDGER_COLUMNS
    )
    assert OPERATOR_STATES == {
        "ledger_absent",
        "history_unresolved",
        "applying",
        "partial",
        "applied",
        "drift",
        "blocked_privileged_grant",
    }

    first = _record(port, recorded.versions[0].sha256, "applying", 1)
    second = _record(port, recorded.versions[0].sha256, "statement_ok", 2)
    read = port.ledger_read(SERVER_UUID, CANONICAL_DATABASE)

    assert first.target_id == SERVER_UUID
    assert second.target_id == SERVER_UUID
    assert first.database == CANONICAL_DATABASE
    assert second.database == CANONICAL_DATABASE
    assert _HOSTNAME not in first.target_id
    assert first.event_seq == 1
    assert second.event_seq == 2
    assert read.events == (first, second)
    assert read.events[0] == first
    assert first.coordinator_lock_identity == coordinator_lock_trace(SERVER_UUID)
    assert "version_applied" not in first.coordinator_lock_identity
    assert not hasattr(port, "ledger_update")
    assert port.executed == ()
    _assert_coordinator_has_lock_trace_only(coordinator)
    assert _snapshot(corpus_dir) == before


@pytest.mark.parametrize("raw_uuid", [None, _ZERO_SERVER_UUID])
def test_missing_or_zero_server_uuid_fails_closed(
    raw_uuid: str | None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Пустой и нулевой UUID не заменяются именем хоста.

    Spec ``clickhouse-migration-lifecycle``, сценарий ``Missing or zero
    server UUID fails closed``. Append не начинается.
    PROVES: PA_SIDE_EFFECT_PROOF.
    """
    port = make_target_port(server_uuid=raw_uuid)
    _forbid_new_socket(monkeypatch)
    recorded = immutable_fingerprint()

    with pytest.raises(LedgerRefusal) as refused:
        _record(port, recorded.versions[0].sha256, "version_applied", 1)

    assert refused.value.code == "server_uuid_refused"
    assert _HOSTNAME not in str(refused.value)
    assert port.executed == ()
    assert "LEDGER_APPEND" not in port.operations
    assert port.ledger_read(SERVER_UUID, CANONICAL_DATABASE).events == ()
    if raw_uuid is not None:
        assert port.ledger_read(raw_uuid, CANONICAL_DATABASE).events == ()


@pytest.mark.parametrize(
    "database",
    ["test_adv_bot_clickhouse", "analytics"],
)
def test_another_database_is_not_this_corpus_target(
    database: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Чужая база, включая тестовую, не получает ``version_applied``.

    Spec ``clickhouse-migration-lifecycle``, сценарий ``Another database is
    not this corpus target``. PROVES: PA_SIDE_EFFECT_PROOF.
    """
    port = make_target_port(session_database=database)
    _forbid_new_socket(monkeypatch)
    recorded = immutable_fingerprint()

    with pytest.raises(LedgerRefusal) as refused:
        _record(port, recorded.versions[0].sha256, "version_applied", 1)

    assert refused.value.code == "database_not_corpus_target"
    assert port.executed == ()
    assert "LEDGER_APPEND" not in port.operations
    stored = port.ledger_read(SERVER_UUID, database)
    assert stored.events == ()
    assert all(event.event_type != "version_applied" for event in stored.events)


def test_ledger_checksum_differs_from_the_file(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Чужой SHA-256 журнала — drift, файл не исполняется и не переписывается.

    Spec ``clickhouse-migration-lifecycle``, сценарий ``Ledger checksum
    differs from the file``. Повторный apply тоже неуспешен.
    PROVES: PA_SIDE_EFFECT_PROOF.
    """
    corpus_dir = canonical_corpus_dir()
    before = _snapshot(corpus_dir)
    recorded = immutable_fingerprint()
    port = make_target_port()
    coordinator = make_coordinator()
    _forbid_new_socket(monkeypatch)
    port.ledger_append(
        LedgerEvent(
            target_id=SERVER_UUID,
            database=CANONICAL_DATABASE,
            version_id="001",
            event_type="version_applied",
            event_seq=1,
            sha256="0" * 64,
            privilege_class="schema_ddl",
            created_at=_CREATED_AT,
        )
    )
    appends_before = port.operations.count("LEDGER_APPEND")

    reported = status(
        corpus_dir,
        recorded,
        port=port,
        coordinator=coordinator,
    )
    planned = plan(
        corpus_dir,
        recorded,
        port=port,
        coordinator=coordinator,
    )
    applied = apply(
        corpus_dir,
        recorded,
        port=port,
        coordinator=coordinator,
    )
    again = apply(
        corpus_dir,
        recorded,
        port=port,
        coordinator=coordinator,
    )

    assert reported.success is False
    assert reported.code == "drift"
    assert reported.exit_code != 0
    assert reported.applied_version_ids == ()
    assert reported.version_reports[0].state == "drift"
    assert reported.version_reports[0].version_id == "001"
    assert planned.success is False
    assert planned.code == "drift"
    assert planned.exit_code != 0
    assert planned.version_reports[0].state == "drift"
    assert planned.planned_versions[0].statements != ()
    assert applied.success is False
    assert applied.code == "drift"
    assert applied.exit_code != 0
    assert applied.version_reports[0].state == "drift"
    assert again.success is False
    assert again.code == "drift"
    assert port.executed == ()
    assert "EXEC_SQL" not in port.operations
    assert port.operations.count("LEDGER_APPEND") == appends_before
    _assert_coordinator_has_lock_trace_only(coordinator)
    assert _snapshot(corpus_dir) == before
    assert before["005_grant_system_log_truncate_to_adv_bot_user.sql"] == (
        _snapshot(corpus_dir)["005_grant_system_log_truncate_to_adv_bot_user.sql"]
    )


def _record(
    port: IsolatedTargetPort,
    sha256: str,
    event_type: str,
    statement_ordinal: int,
) -> LedgerEvent:
    """Один append через форму журнала, без захвата координатора."""
    return record_version_event(
        port,
        version_id="001",
        sha256=sha256,
        privilege_class="schema_ddl",
        event_type=event_type,
        hostname=_HOSTNAME,
        statement_ordinal=statement_ordinal,
        statement_count=3,
        runner_nonce="runner-nonce-1",
        evidence_sha256="e" * 64,
        created_at=_CREATED_AT,
    )


def _assert_coordinator_has_lock_trace_only(
    coordinator: RecordingCoordinatorSession,
) -> None:
    """Сессия координатора не хранит applied-status корпуса."""
    assert coordinator.calls == ()
    assert coordinator.statements_sent == ()
    assert coordinator.held is False
    assert "applied" not in coordinator.__dict__
    assert "version_applied" not in coordinator.__dict__


def _snapshot(corpus_dir: Path) -> dict[str, bytes]:
    """Сырые байты ``001``–``005``. Сравнение ловит переписывание корпуса."""
    return {
        version.filename: (corpus_dir / version.filename).read_bytes()
        for version in immutable_fingerprint().versions
    }


def _forbid_new_socket(monkeypatch: pytest.MonkeyPatch) -> None:
    """Сторож сокета: журнал на подстановке сеть не открывает."""

    def _boom(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("команда открыла сокет")

    monkeypatch.setattr(socket, "socket", _boom)
    monkeypatch.setattr(socket, "create_connection", _boom)
