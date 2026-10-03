"""Контракт ``isolated-target-port-v1``.

Spec ``clickhouse-migration-lifecycle``, задача 2.1. Порт принимает один
statement ``schema_ddl`` и отвергает текст ``005``, непроверенный файл,
разошедшийся SQL и statement из комментария. Журнал только дописывается.
Живого ClickHouse нет.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from scripts.clickhouse_migration_control_plane.target_port import (
    ExecSqlRefused,
    IsolatedTargetPort,
    LedgerEvent,
    classify_server_uuid,
    classify_session_database,
)
from tests.unit.clickhouse_migration_contract_fixture import (
    CANONICAL_DATABASE,
    SERVER_UUID,
    accepted_schema_request,
    grant_005_request,
    grant_line_as_schema_version,
    make_target_port,
    sha256_raw,
)

pytestmark = pytest.mark.unit

_REPO_ROOT = Path(__file__).resolve().parents[2]
_VERSION_001 = (
    _REPO_ROOT
    / "scripts"
    / "clickhouse_migrations"
    / "001_create_incremental_tables.sql"
)


def test_exec_sql_accepts_one_schema_statement() -> None:
    """Порт записывает один statement ``001``.

    Spec ``clickhouse-migration-lifecycle``: положительная ветка
    ``EXEC_SQL`` нужна, чтобы запрет ``005`` не стал запретом всего SQL.
    """
    port = make_target_port()
    request = accepted_schema_request()

    port.exec_sql(request)

    assert port.executed == (request,)
    assert "CREATE TABLE" in request.sql
    assert "default_db." in request.sql


def test_exec_sql_rejects_005_text_and_records_nothing() -> None:
    """Текст ``005`` не попадает в список исполненных statement.

    Spec ``clickhouse-migration-lifecycle``: удаление запрета ``EXEC_SQL``
    на текст ``005`` обязано уронить этот тест. Хеш файла при этом верный.
    """
    port = make_target_port()

    with pytest.raises(ExecSqlRefused) as refused:
        port.exec_sql(grant_005_request())

    assert refused.value.code == "blocked_privileged_grant"
    assert port.executed == ()


def test_exec_sql_rejects_grant_line_even_with_schema_version_hash() -> None:
    """Строка ``GRANT`` из ``005`` отвергается при хеше ``001``.

    Spec ``clickhouse-migration-lifecycle``: schema-writer не получает
    текст privileged GRANT, даже если номер версии подменён.
    """
    port = make_target_port()

    with pytest.raises(ExecSqlRefused) as refused:
        port.exec_sql(grant_line_as_schema_version())

    assert refused.value.code == "blocked_privileged_grant"
    assert port.executed == ()


def test_exec_sql_rejects_unreviewed_version_without_reading_006() -> None:
    """Версия ``006`` — непроверенный файл, statement не записывается.

    Spec ``clickhouse-migration-lifecycle``: префикса ``006`` нет в
    отпечатке. Отказ не требует открыть чужой worktree.
    """
    port = make_target_port()
    request = accepted_schema_request()
    unreviewed = type(request)(
        sql=request.sql,
        version_id="006",
        file_sha256=request.file_sha256,
    )
    absent = (
        _REPO_ROOT
        / "scripts"
        / "clickhouse_migrations"
        / "006_unreviewed.sql"
    )
    assert absent.is_file() is False

    with pytest.raises(ExecSqlRefused) as refused:
        port.exec_sql(unreviewed)

    assert refused.value.code == "unreviewed_version"
    assert port.executed == ()
    assert absent.is_file() is False


def test_exec_sql_rejects_drifted_checksum() -> None:
    """Несовпавший SHA-256 файла не исполняется.

    Spec ``clickhouse-migration-lifecycle``: разошедшийся отпечаток —
    ``corpus_drift`` до записи ``EXEC_SQL``.
    """
    port = make_target_port()
    request = accepted_schema_request()
    drifted = type(request)(
        sql=request.sql,
        version_id=request.version_id,
        file_sha256="0" * 64,
    )

    with pytest.raises(ExecSqlRefused) as refused:
        port.exec_sql(drifted)

    assert refused.value.code == "corpus_drift"
    assert port.executed == ()


def test_exec_sql_rejects_sql_that_is_not_in_the_file() -> None:
    """Текст, которого нет в файле версии, не исполняется.

    Spec ``clickhouse-migration-lifecycle``: разошедшийся SQL отвергается,
    даже если вызывающий передал хеш текущего файла.
    """
    port = make_target_port()
    request = accepted_schema_request()
    mutated = type(request)(
        sql=request.sql.replace(
            "default_db.",
            "test_adv_bot_clickhouse.",
            1,
        ),
        version_id=request.version_id,
        file_sha256=request.file_sha256,
    )
    assert mutated.file_sha256 == sha256_raw(_VERSION_001.read_bytes())

    with pytest.raises(ExecSqlRefused) as refused:
        port.exec_sql(mutated)

    assert refused.value.code == "corpus_drift"
    assert port.executed == ()


def test_exec_sql_rejects_comment_only_statement() -> None:
    """Полная строка ``--`` не становится statement.

    Spec ``clickhouse-migration-lifecycle``: комментарий, в том числе про
    пересоздание объекта, не уходит в ``EXEC_SQL``.
    """
    port = make_target_port()
    request = accepted_schema_request()
    comment = type(request)(
        sql="-- recreate table default_db.wb_common_stat_incremental\n",
        version_id=request.version_id,
        file_sha256=request.file_sha256,
    )

    with pytest.raises(ExecSqlRefused) as refused:
        port.exec_sql(comment)

    assert refused.value.code == "comment_only_statement"
    assert port.executed == ()


def test_ledger_append_does_not_replace_earlier_event() -> None:
    """Второй insert не меняет уже записанное событие.

    Spec ``clickhouse-migration-lifecycle``: журнал append-only. Обновления
    на месте у порта нет.
    """
    port = make_target_port()
    first = LedgerEvent(
        target_id=SERVER_UUID,
        database=CANONICAL_DATABASE,
        version_id="001",
        event_type="apply_started",
        event_seq=1,
        sha256="a" * 64,
    )
    second = LedgerEvent(
        target_id=SERVER_UUID,
        database=CANONICAL_DATABASE,
        version_id="001",
        event_type="statement_ok",
        event_seq=2,
        sha256="a" * 64,
    )

    port.ledger_append(first)
    port.ledger_append(second)
    read = port.ledger_read(SERVER_UUID, CANONICAL_DATABASE)

    assert read.events[0] == first
    assert read.events[1] == second
    assert not hasattr(port, "ledger_update")
    assert not hasattr(IsolatedTargetPort, "ledger_update")


def test_ledger_read_scopes_one_uuid_and_default_db_by_event_seq() -> None:
    """Чтение журнала фильтрует цель и упорядочивает ``event_seq``.

    Spec ``clickhouse-migration-lifecycle``: события чужого UUID и чужой
    базы, включая ``test_adv_bot_clickhouse``, в эту выборку не входят.
    """
    port = make_target_port()
    later = LedgerEvent(
        target_id=SERVER_UUID,
        database=CANONICAL_DATABASE,
        version_id="001",
        event_type="statement_ok",
        event_seq=5,
        sha256="b" * 64,
    )
    earlier = LedgerEvent(
        target_id=SERVER_UUID,
        database=CANONICAL_DATABASE,
        version_id="001",
        event_type="apply_started",
        event_seq=2,
        sha256="b" * 64,
    )
    other_uuid = LedgerEvent(
        target_id="aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee",
        database=CANONICAL_DATABASE,
        version_id="001",
        event_type="version_applied",
        event_seq=1,
        sha256="c" * 64,
    )
    test_database = LedgerEvent(
        target_id=SERVER_UUID,
        database="test_adv_bot_clickhouse",
        version_id="001",
        event_type="version_applied",
        event_seq=3,
        sha256="d" * 64,
    )

    port.ledger_append(later)
    port.ledger_append(other_uuid)
    port.ledger_append(test_database)
    port.ledger_append(earlier)

    read = port.ledger_read(SERVER_UUID, CANONICAL_DATABASE)
    empty_other = port.ledger_read(
        "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee",
        "test_adv_bot_clickhouse",
    )

    assert read.status == "events_present"
    assert tuple(event.event_seq for event in read.events) == (2, 5)
    assert empty_other.status == "ledger_absent"
    assert empty_other.events == ()


def test_ledger_read_absent_when_nothing_appended() -> None:
    """Пустой журнал цели — ``ledger_absent``.

    Spec ``clickhouse-migration-lifecycle``: отсутствие событий не
    превращается в applied-state.
    """
    port = make_target_port()

    read = port.ledger_read(SERVER_UUID, CANONICAL_DATABASE)

    assert read.status == "ledger_absent"
    assert read.events == ()


def test_server_uuid_distinguishes_present_missing_and_zero() -> None:
    """Идентификатор цели: ненулевой, пустой, нулевой и имя хоста.

    Spec ``clickhouse-migration-lifecycle``: отсутствующий и нулевой UUID
    не принимаются, hostname не подменяет ``serverUUID()``.
    """
    present = make_target_port(server_uuid=SERVER_UUID).server_uuid()
    missing = make_target_port(server_uuid=None).server_uuid()
    zero = make_target_port(
        server_uuid="00000000-0000-0000-0000-000000000000"
    ).server_uuid()
    hostname = classify_server_uuid("clickhouse.internal")

    assert present.accepted is True
    assert present.reason == "ok"
    assert missing.accepted is False
    assert missing.reason == "missing"
    assert zero.accepted is False
    assert zero.reason == "zero"
    assert hostname.accepted is False
    assert hostname.reason == "not_uuid"


def test_session_database_accepts_only_default_db() -> None:
    """База сессии — только ``default_db``.

    Spec ``clickhouse-migration-lifecycle``: ``test_adv_bot_clickhouse`` и
    любая иная база не являются целью этого корпуса.
    """
    canonical = make_target_port().session_database()
    test_db = make_target_port(
        session_database="test_adv_bot_clickhouse"
    ).session_database()
    other = classify_session_database("analytics")

    assert canonical.accepted is True
    assert canonical.name == CANONICAL_DATABASE
    assert test_db.accepted is False
    assert other.accepted is False
    assert other.name == "analytics"


def test_inspect_read_returns_metadata_without_ledger_write() -> None:
    """Осмотр отдаёт подготовленные метаданные и не пишет журнал.

    Spec ``clickhouse-migration-lifecycle``: ``INSPECT_READ`` не дописывает
    события и не исполняет SQL.
    """
    port = make_target_port()

    metadata = port.inspect_read()
    read = port.ledger_read(SERVER_UUID, CANONICAL_DATABASE)

    assert metadata.object_names == ("default_db.wb_common_stat_incremental",)
    assert read.status == "ledger_absent"
    assert port.executed == ()
    assert port.operations == ("INSPECT_READ",)
