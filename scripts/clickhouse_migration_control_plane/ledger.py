"""Форма журнала ``default_db.ch_schema_migration_ledger``.

Spec ``clickhouse-migration-lifecycle``: применённое состояние корпуса живёт
только append-only событием на цели ClickHouse. PostgreSQL хранит след
advisory lock, не статус версии. Git, Alembic и Redis журналом не являются.
Этот модуль задаёт форму таблицы и отказ идентичности. ``ensure-ledger``
её не создаёт: создание таблицы — следующий срез.
"""

from __future__ import annotations

from scripts.clickhouse_migration_control_plane.coordinator_session import (
    MIGRATION_CONTROL_NAMESPACE_KEY,
    target_key_for_isolated_default_db,
)
from scripts.clickhouse_migration_control_plane.target_port import (
    IsolatedTargetPort,
    LedgerEvent,
)

LEDGER_RELATION = "default_db.ch_schema_migration_ledger"
CANONICAL_DATABASE = "default_db"

LEDGER_COLUMNS: tuple[str, ...] = (
    "target_id",
    "database",
    "version_id",
    "sha256",
    "privilege_class",
    "event_type",
    "statement_ordinal",
    "statement_count",
    "runner_nonce",
    "coordinator_lock_identity",
    "evidence_sha256",
    "event_seq",
    "created_at",
)

OPERATOR_STATES = frozenset(
    {
        "ledger_absent",
        "history_unresolved",
        "applying",
        "partial",
        "applied",
        "drift",
        "blocked_privileged_grant",
    }
)

_EVENT_TO_OPERATOR = {
    "ledger_absent": "ledger_absent",
    "history_unresolved": "history_unresolved",
    "applying": "applying",
    "apply_started": "applying",
    "partial": "partial",
    "statement_ok": "partial",
    "applied": "applied",
    "version_applied": "applied",
    "drift": "drift",
    "blocked_privileged_grant": "blocked_privileged_grant",
}


class LedgerRefusal(Exception):
    """Отказ записи журнала до append.

    Spec ``clickhouse-migration-lifecycle``: нулевой UUID, пустой UUID и
    чужая база не становятся целью. ``code`` называет причину. Имя хоста в
    это сообщение не подставляется.
    """

    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


def ledger_ddl() -> str:
    """Текст формы таблицы без исполнения на сервере.

    Spec ``clickhouse-migration-lifecycle``: ``MergeTree`` без ``ON CLUSTER``,
    порядок ``(target_id, version_id, event_seq)``. Создание таблицы на цели
    остаётся за ``ensure-ledger``.

    Returns:
        DDL ``default_db.ch_schema_migration_ledger``.
    """
    body = ", ".join(
        f"{name} {kind}" for name, kind in _LEDGER_COLUMN_TYPES
    )
    return (
        f"CREATE TABLE {LEDGER_RELATION} ({body}) "
        "ENGINE = MergeTree "
        "ORDER BY (target_id, version_id, event_seq)"
    )


def coordinator_lock_trace(server_uuid: str) -> str:
    """След захвата: пространство имён, ключ цели и местная сессия.

    Spec ``clickhouse-migration-lifecycle``: это не строка applied-status
    в PostgreSQL. Функция ничего не пишет в координатор.
    """
    target_key = target_key_for_isolated_default_db(server_uuid)
    return (
        f"{MIGRATION_CONTROL_NAMESPACE_KEY}:{target_key}:session-local"
    )


def operator_state(event: LedgerEvent | None, *, file_sha256: str) -> str:
    """Состояние версии, которое видит оператор.

    Spec ``clickhouse-migration-lifecycle``: нет события — ``ledger_absent``.
    SHA-256 события, не совпавший с файлом, — ``drift``, даже если тип
    события ``version_applied``. Иначе тип события сворачивается в одно из
    операторских состояний.

    Args:
        event: последнее событие версии либо ``None``.
        file_sha256: SHA-256 сырых байтов файла корпуса.

    Returns:
        Одно из ``OPERATOR_STATES`` либо исходный тип, если он ещё не сведён.
    """
    if event is None:
        return "ledger_absent"
    if event.sha256 != file_sha256:
        return "drift"
    mapped = _EVENT_TO_OPERATOR.get(event.event_type)
    if mapped is None:
        return event.event_type
    return mapped


def record_version_event(
    port: IsolatedTargetPort,
    *,
    version_id: str,
    sha256: str,
    privilege_class: str,
    event_type: str,
    hostname: str,
    statement_ordinal: int,
    statement_count: int,
    runner_nonce: str,
    evidence_sha256: str,
    created_at: str,
) -> LedgerEvent:
    """Дописать событие журнала на ``serverUUID()`` и ``default_db``.

    Spec ``clickhouse-migration-lifecycle``, сценарии идентичности цели.
    Каждый вызов — новый append. Строка журнала на месте не обновляется.
    Координатор не получает applied-status и lock здесь не захватывается.
    ``hostname`` не подменяет отсутствующий UUID.

    Args:
        port: шов цели. Сети нет.
        version_id: версия корпуса.
        sha256: SHA-256, который записывается в событие.
        privilege_class: класс привилегии версии.
        event_type: тип события, не операторское состояние после drift.
        hostname: имя, которое нельзя сделать ``target_id``.
        statement_ordinal: номер statement в версии.
        statement_count: сколько statement в версии.
        runner_nonce: nonce запуска.
        evidence_sha256: хеш доказательства, не хеш файла.
        created_at: метка времени события.

    Returns:
        Событие, уже дописанное в журнал шва.

    Raises:
        LedgerRefusal: UUID пустой, нулевой или не UUID, либо база не
        ``default_db``.
    """
    target_id = _require_server_uuid(port, hostname)
    database = _require_default_db(port)
    event = LedgerEvent(
        target_id=target_id,
        database=database,
        version_id=version_id,
        event_type=event_type,
        event_seq=_next_event_seq(port, target_id, database, version_id),
        sha256=sha256,
        privilege_class=privilege_class,
        statement_ordinal=statement_ordinal,
        statement_count=statement_count,
        runner_nonce=runner_nonce,
        coordinator_lock_identity=coordinator_lock_trace(target_id),
        evidence_sha256=evidence_sha256,
        created_at=created_at,
    )
    port.ledger_append(event)
    return event


def _require_server_uuid(port: IsolatedTargetPort, hostname: str) -> str:
    """Принять только ненулевой UUID. Hostname целью не становится."""
    reading = port.server_uuid()
    if not reading.accepted or reading.raw is None or reading.raw == hostname:
        raise LedgerRefusal("server_uuid_refused")
    return reading.raw


def _require_default_db(port: IsolatedTargetPort) -> str:
    """Принять только базу сессии ``default_db``."""
    reading = port.session_database()
    if not reading.accepted or reading.name != CANONICAL_DATABASE:
        raise LedgerRefusal("database_not_corpus_target")
    return reading.name


def _next_event_seq(
    port: IsolatedTargetPort,
    target_id: str,
    database: str,
    version_id: str,
) -> int:
    """Следующий ``event_seq`` версии. Чужие цели в счёт не входят."""
    current = 0
    read = port.ledger_read(target_id, database)
    for event in read.events:
        if event.version_id == version_id and event.event_seq > current:
            current = event.event_seq
    return current + 1


_LEDGER_COLUMN_TYPES: tuple[tuple[str, str], ...] = (
    ("target_id", "String"),
    ("database", "String"),
    ("version_id", "String"),
    ("sha256", "String"),
    ("privilege_class", "String"),
    ("event_type", "String"),
    ("statement_ordinal", "UInt32"),
    ("statement_count", "UInt32"),
    ("runner_nonce", "String"),
    ("coordinator_lock_identity", "String"),
    ("evidence_sha256", "String"),
    ("event_seq", "UInt64"),
    ("created_at", "DateTime64(3, 'UTC')"),
)
