"""Общий fixture контрактов ``isolated-target-port-v1`` и ``coordinator-session-v1``.

Spec ``clickhouse-migration-lifecycle``: срезы 2.1 и 2.2 проверяют один и тот
же изолированный порт и одну сессию координатора, без живого сокета.
Нарезка первого statement файла ``001`` здесь только готовит вход порта.
Это не диспетчер команд и не разбор корпуса запускатора.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

from scripts.clickhouse_migration_control_plane.coordinator_session import (
    RecordingCoordinatorSession,
)
from scripts.clickhouse_migration_control_plane.target_port import (
    ExecSqlRequest,
    InspectMetadata,
    RecordingIsolatedTargetPort,
)

_REPO_ROOT = Path(__file__).resolve().parents[2]
_CORPUS_DIR = _REPO_ROOT / "scripts" / "clickhouse_migrations"
_VERSION_001 = _CORPUS_DIR / "001_create_incremental_tables.sql"
_VERSION_005 = _CORPUS_DIR / "005_grant_system_log_truncate_to_adv_bot_user.sql"

# Ненулевой UUID цели. Не имя хоста и не нулевой serverUUID().
SERVER_UUID = "018f0b3c-7a21-7c3e-8e11-9a0b1c2d3e4f"
CANONICAL_DATABASE = "default_db"


def sha256_raw(payload: bytes) -> str:
    """SHA-256 сырых байт файла корпуса.

    Spec ``clickhouse-migration-lifecycle``: отпечаток не нормализует
    переводы строк. Fixture передаёт этот хеш в порт, чтобы отказ
    ``corpus_drift`` сравнивался с диском, а не с заранее принятым флагом.
    """
    return hashlib.sha256(payload).hexdigest()


def first_schema_statement(sql_text: str) -> str:
    """Первый непустой statement файла ``001`` после строк ``--``.

    Spec ``clickhouse-migration-lifecycle``: ``EXEC_SQL`` принимает один
    statement ``schema_ddl``. Вырезание нужно только fixture; порт сам
    решает, записывать ли вызов.
    """
    kept: list[str] = []
    for line in sql_text.splitlines(keepends=True):
        if line.lstrip().startswith("--"):
            continue
        kept.append(line)
    body = "".join(kept).lstrip("\n")
    semicolon = body.find(";")
    if semicolon < 0:
        raise AssertionError("в 001 нет statement с точкой с запятой")
    return body[: semicolon + 1].strip()


def accepted_schema_request() -> ExecSqlRequest:
    """Один statement ``001`` с хешем сырого файла.

    Spec ``clickhouse-migration-lifecycle``: положительная ветка
    ``EXEC_SQL`` для ``schema_ddl``. Без этого входа тест не отличает
    отказ порта от полного запрета любого SQL.
    """
    raw = _VERSION_001.read_bytes()
    return ExecSqlRequest(
        sql=first_schema_statement(raw.decode("utf-8")),
        version_id="001",
        file_sha256=sha256_raw(raw),
    )


def grant_005_request() -> ExecSqlRequest:
    """Полный текст ``005`` как один вызов ``EXEC_SQL``.

    Spec ``clickhouse-migration-lifecycle``: schema-writer не получает
    текст privileged GRANT. Хеш файла верный, чтобы отказ не спутать с drift.
    """
    raw = _VERSION_005.read_bytes()
    return ExecSqlRequest(
        sql=raw.decode("utf-8"),
        version_id="005",
        file_sha256=sha256_raw(raw),
    )


def grant_line_as_schema_version() -> ExecSqlRequest:
    """Строка ``GRANT`` из ``005`` под видом версии ``001`` с её хешем.

    Spec ``clickhouse-migration-lifecycle``: запрет на текст ``005``, а не
    только на номер версии. Хеш ``001`` совпадает с диском.
    """
    raw_001 = _VERSION_001.read_bytes()
    grant_line = next(
        line.strip()
        for line in _VERSION_005.read_text(encoding="utf-8").splitlines()
        if line.strip().startswith("GRANT ")
    )
    return ExecSqlRequest(
        sql=grant_line,
        version_id="001",
        file_sha256=sha256_raw(raw_001),
    )


def make_target_port(
    *,
    server_uuid: str | None = SERVER_UUID,
    session_database: str = CANONICAL_DATABASE,
) -> RecordingIsolatedTargetPort:
    """Подставной порт ``isolated-target-port-v1`` без сети.

    Spec ``clickhouse-migration-lifecycle``: запись журнала и ``EXEC_SQL``
    наблюдаются в процессе. Метаданные осмотра подготовлены заранее и не
    читают ClickHouse.
    """
    identity = server_uuid if server_uuid is not None else ""
    return RecordingIsolatedTargetPort(
        server_uuid_raw=server_uuid,
        session_database=session_database,
        inspect_metadata=InspectMetadata(
            target_id=identity,
            database=session_database,
            object_names=("default_db.wb_common_stat_incremental",),
        ),
    )


def make_coordinator(
    *,
    server_uuid: str = SERVER_UUID,
    try_acquire_returns: bool = True,
) -> RecordingCoordinatorSession:
    """Подставная сессия ``coordinator-session-v1`` без PostgreSQL.

    Spec ``clickhouse-migration-lifecycle``: захват — запись вызова
    advisory lock, а не соединение. ``try_acquire_returns`` задаёт ответ
    примитива, не решение запускатора о санкции.
    """
    return RecordingCoordinatorSession(
        server_uuid=server_uuid,
        try_acquire_returns=try_acquire_returns,
    )
