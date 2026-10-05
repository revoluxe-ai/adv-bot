"""Порт изолированной цели ``isolated-target-port-v1``.

Spec ``clickhouse-migration-lifecycle``: ``EXEC_SQL``, журнал, ``serverUUID``,
база сессии и осмотр — контракт подстановки, не клиент приложения и не
живой ClickHouse. Запрет текста ``005`` и drift решает ``refuse_exec_sql``.
Записывающая подстановка только фиксирует вызов после этого решения.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

_REPO_ROOT = Path(__file__).resolve().parents[2]
_CORPUS_DIR = _REPO_ROOT / "scripts" / "clickhouse_migrations"
_SCHEMA_VERSIONS = frozenset({"001", "002", "003", "004"})
_ZERO_SERVER_UUID = "00000000-0000-0000-0000-000000000000"
_SERVER_UUID_RE = re.compile(
    r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-"
    r"[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$"
)
_CANONICAL_DATABASE = "default_db"


class ExecSqlRefused(Exception):
    """Отказ ``EXEC_SQL`` до записи statement.

    Spec ``clickhouse-migration-lifecycle``: порт не исполняет текст ``005``,
    непроверенную версию, разошедшийся SQL и комментарий. ``code`` — причина
    отказа, которую видит тест контракта.
    """

    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


@dataclass(frozen=True)
class ExecSqlRequest:
    """Один statement, который порт может принять или отвергнуть.

    Spec ``clickhouse-migration-lifecycle``: ``file_sha256`` — хеш сырого
    файла версии, а не хеш отдельной строки. Порт сверяет его с диском.
    """

    sql: str
    version_id: str
    file_sha256: str


@dataclass(frozen=True)
class LedgerEvent:
    """Одно append-only событие журнала цели.

    Spec ``clickhouse-migration-lifecycle``: состояние версии — событие, а
    не правка предыдущей строки. Колонки совпадают с
    ``default_db.ch_schema_migration_ledger``. Подстановка хранит поля как
    есть и не обновляет уже записанное событие.
    """

    target_id: str
    database: str
    version_id: str
    event_type: str
    event_seq: int
    sha256: str
    privilege_class: str = ""
    statement_ordinal: int = 0
    statement_count: int = 0
    runner_nonce: str = ""
    coordinator_lock_identity: str = ""
    evidence_sha256: str = ""
    created_at: str = ""


@dataclass(frozen=True)
class LedgerReadResult:
    """Выборка журнала одной цели.

    Spec ``clickhouse-migration-lifecycle``: пустая выборка остаётся
    ``ledger_absent`` и не означает, что версии применены.
    """

    status: str
    events: tuple[LedgerEvent, ...]


@dataclass(frozen=True)
class ServerUuidReading:
    """Классификация ``serverUUID()`` без подмены именем хоста.

    Spec ``clickhouse-migration-lifecycle``: цель принимается только при
    ненулевом UUID. ``reason`` отличает пустое, нулевое и не-UUID значение.
    """

    raw: str | None
    accepted: bool
    reason: str


@dataclass(frozen=True)
class SessionDatabaseReading:
    """Классификация базы сессии ClickHouse.

    Spec ``clickhouse-migration-lifecycle``: корпус рассчитан на
    ``default_db``. Иная база, включая тестовую, целью не является.
    """

    name: str
    accepted: bool


@dataclass(frozen=True)
class InspectMetadata:
    """Готовые метаданные осмотра, уже полученные вне сети.

    Spec ``clickhouse-migration-lifecycle``: ``INSPECT_READ`` только отдаёт
    их. ``catalog_reads`` — имена чтений подстановки (``system.tables``,
    ``system.columns``, ``SHOW CREATE``), не живой запрос. Подстановка не
    ходит в ClickHouse за этим набором.
    """

    target_id: str
    database: str
    object_names: tuple[str, ...]
    catalog_reads: tuple[str, ...] = (
        "system.tables",
        "system.columns",
        "SHOW CREATE",
    )


class IsolatedTargetPort(Protocol):
    """Контракт порта цели. Метода обновления журнала на месте нет.

    Spec ``clickhouse-migration-lifecycle``: исполнитель схемы, дописывание
    журнала и чтение осмотра разделены. Протокол не решает санкцию apply.
    """

    def exec_sql(self, request: ExecSqlRequest) -> None:
        """Принять один statement либо отказаться до записи."""

    def ensure_ledger(self, ddl: str) -> None:
        """Создать только canonical migration ledger под внешним lock."""

    def ledger_exists(self) -> bool:
        """Сообщить, создан ли migration ledger на этом порте."""
        ...

    def ledger_append(self, event: LedgerEvent) -> None:
        """Дописать событие журнала."""

    def ledger_read(self, target_id: str, database: str) -> LedgerReadResult:
        """Прочитать события одной цели по ``event_seq``."""
        ...

    def server_uuid(self) -> ServerUuidReading:
        """Вернуть классификацию идентификатора сервера."""
        ...

    def session_database(self) -> SessionDatabaseReading:
        """Вернуть классификацию базы сессии."""
        ...

    def inspect_read(self) -> InspectMetadata:
        """Отдать подготовленные метаданные без записи журнала."""
        ...


def classify_server_uuid(raw: str | None) -> ServerUuidReading:
    """Отличить ненулевой UUID от пустого, нулевого и hostname.

    Spec ``clickhouse-migration-lifecycle``: отсутствующий или нулевой
    ``serverUUID()`` останавливает цель. Имя хоста не подставляется вместо
    идентификатора сервера.
    """
    if raw is None or raw.strip() == "":
        return ServerUuidReading(raw=raw, accepted=False, reason="missing")
    if raw == _ZERO_SERVER_UUID:
        return ServerUuidReading(raw=raw, accepted=False, reason="zero")
    if _SERVER_UUID_RE.fullmatch(raw) is None:
        return ServerUuidReading(raw=raw, accepted=False, reason="not_uuid")
    return ServerUuidReading(raw=raw, accepted=True, reason="ok")


def classify_session_database(name: str) -> SessionDatabaseReading:
    """Принять только базу ``default_db``.

    Spec ``clickhouse-migration-lifecycle``: ``test_adv_bot_clickhouse`` и
    любая другая база не становятся целью корпуса ``001``–``005``.
    """
    return SessionDatabaseReading(
        name=name,
        accepted=name == _CANONICAL_DATABASE,
    )


def refuse_exec_sql(request: ExecSqlRequest) -> None:
    """Отвергнуть statement, который порту цели исполнять нельзя.

    Spec ``clickhouse-migration-lifecycle``: это решение шва ``EXEC_SQL``,
    не флаг подстановки. Контрактный тест требует код
    ``blocked_privileged_grant`` и пустой список исполненных statement.
    Снятие этой проверки обязано уронить тест 2.1.

    Raises:
        ExecSqlRefused: комментарий, ``005``, непроверенная версия или drift.
    """
    if _is_comment_only(request.sql):
        raise ExecSqlRefused("comment_only_statement")
    if request.version_id == "005" or _is_privileged_grant_text(request.sql):
        raise ExecSqlRefused("blocked_privileged_grant")
    if request.version_id not in _SCHEMA_VERSIONS:
        raise ExecSqlRefused("unreviewed_version")
    raw = _schema_file_bytes(request.version_id)
    digest = hashlib.sha256(raw).hexdigest()
    if request.file_sha256 != digest:
        raise ExecSqlRefused("corpus_drift")
    if request.sql.strip() not in raw.decode("utf-8"):
        raise ExecSqlRefused("corpus_drift")


def _is_comment_only(sql: str) -> bool:
    """Пустой текст и полные строки ``--`` не являются statement."""
    for line in sql.splitlines():
        stripped = line.strip()
        if stripped == "" or stripped.startswith("--"):
            continue
        return False
    return True


def _is_privileged_grant_text(sql: str) -> bool:
    """Текст ``005`` или его строка ``GRANT`` не входят в schema-writer.

    Файл ``005`` этого worktree читается как канон GRANT. Чужой ``006``
    здесь не открывается.
    """
    text = _version_file("005").read_text(encoding="utf-8")
    if sql == text:
        return True
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("GRANT ") and stripped in sql:
            return True
    folded = sql.lstrip().upper()
    return folded.startswith("GRANT ") and "system." in sql.lower()


def _version_file(version_id: str) -> Path:
    """Путь канонического файла ``001``–``005`` в этом worktree.

    Spec ``clickhouse-migration-lifecycle`` запрещает читать ``006`` из
    другой копии. Шаблон ограничен переданным префиксом корпуса.
    """
    matches = sorted(_CORPUS_DIR.glob(f"{version_id}_*.sql"))
    if len(matches) != 1:
        raise ExecSqlRefused("unreviewed_version")
    return matches[0]


def _schema_file_bytes(version_id: str) -> bytes:
    """Сырые байты schema-файла ``001``–``004`` для сверки SHA-256."""
    if version_id not in _SCHEMA_VERSIONS:
        raise ExecSqlRefused("unreviewed_version")
    return _version_file(version_id).read_bytes()


class RecordingIsolatedTargetPort:
    """Внутрипроцессная запись вызовов порта после решения контракта.

    Spec ``clickhouse-migration-lifecycle``: подстановка не выбирает санкцию
    apply и не подменяет ``refuse_exec_sql``. Сети и учётных данных нет.
    """

    def __init__(
        self,
        *,
        server_uuid_raw: str | None,
        session_database: str,
        inspect_metadata: InspectMetadata,
    ) -> None:
        self._server_uuid_raw = server_uuid_raw
        self._session_database = session_database
        self._inspect_metadata = inspect_metadata
        self._executed: list[ExecSqlRequest] = []
        self._events: list[LedgerEvent] = []
        self._operations: list[str] = []
        self._ledger_created = False
        self._ledger_ddl_text = ""

    @property
    def executed(self) -> tuple[ExecSqlRequest, ...]:
        """Statement, которые ``EXEC_SQL`` уже принял."""
        return tuple(self._executed)

    @property
    def operations(self) -> tuple[str, ...]:
        """Имена операций порта в порядке вызовов."""
        return tuple(self._operations)

    @property
    def ledger_created(self) -> bool:
        """Создан ли canonical ledger в изолированном контракте."""
        return self._ledger_created

    @property
    def ledger_ddl_text(self) -> str:
        """DDL, которым был создан ledger; пусто до ensure-ledger."""
        return self._ledger_ddl_text

    def exec_sql(self, request: ExecSqlRequest) -> None:
        """Записать statement только если ``refuse_exec_sql`` его пропустил.

        Spec ``clickhouse-migration-lifecycle``: запрет текста ``005`` живёт
        в решении порта. Подстановка не принимает GRANT сама по себе.
        """
        refuse_exec_sql(request)
        self._executed.append(request)
        self._operations.append("EXEC_SQL")

    def ensure_ledger(self, ddl: str) -> None:
        """Создать только ``default_db.ch_schema_migration_ledger``.

        Spec ``clickhouse-migration-lifecycle``: fence, ON CLUSTER и
        произвольный DDL этим швом не принимаются. Сам advisory lock
        проверяет command layer до вызова порта.
        """
        normalized = " ".join(ddl.split())
        if not normalized.startswith(
            "CREATE TABLE default_db.ch_schema_migration_ledger "
        ):
            raise ExecSqlRefused("invalid_ledger_ddl")
        if "fence" in normalized.lower() or " ON CLUSTER " in normalized.upper():
            raise ExecSqlRefused("invalid_ledger_ddl")
        self._ledger_created = True
        self._ledger_ddl_text = ddl
        self._operations.append("ENSURE_LEDGER")

    def ledger_exists(self) -> bool:
        """Вернуть durable-факт существования ledger на подстановке."""
        return self._ledger_created

    def ledger_append(self, event: LedgerEvent) -> None:
        """Дописать событие. Предыдущие события не заменяются.

        Spec ``clickhouse-migration-lifecycle``: журнал не обновляется
        на месте. Отдельного метода правки нет.
        """
        self._ledger_created = True
        self._events.append(event)
        self._operations.append("LEDGER_APPEND")

    def ledger_read(self, target_id: str, database: str) -> LedgerReadResult:
        """События одного UUID и одной базы, по возрастанию ``event_seq``.

        Spec ``clickhouse-migration-lifecycle``: чужая база и чужой сервер
        в эту выборку не входят. Пустота — ``ledger_absent``.
        """
        matched = [
            event
            for event in self._events
            if event.target_id == target_id and event.database == database
        ]
        ordered = tuple(sorted(matched, key=lambda event: event.event_seq))
        if ordered == ():
            return LedgerReadResult(status="ledger_absent", events=())
        return LedgerReadResult(status="events_present", events=ordered)

    def server_uuid(self) -> ServerUuidReading:
        """Классифицировать заранее подставленное значение UUID.

        Spec ``clickhouse-migration-lifecycle``: подстановка не добывает
        UUID по сети. Правило приёмки — ``classify_server_uuid``.
        """
        self._operations.append("SERVER_UUID")
        return classify_server_uuid(self._server_uuid_raw)

    def session_database(self) -> SessionDatabaseReading:
        """Классифицировать заранее подставленное имя базы.

        Spec ``clickhouse-migration-lifecycle``: правило приёмки —
        ``classify_session_database``, не ответ живой сессии.
        """
        self._operations.append("SESSION_DATABASE")
        return classify_session_database(self._session_database)

    def inspect_read(self) -> InspectMetadata:
        """Вернуть подготовленные метаданные, не трогая журнал.

        Spec ``clickhouse-migration-lifecycle``: осмотр не дописывает
        события и не исполняет SQL.
        """
        self._operations.append("INSPECT_READ")
        return self._inspect_metadata
