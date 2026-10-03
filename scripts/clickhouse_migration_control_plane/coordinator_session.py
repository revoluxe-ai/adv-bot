"""Сессия координатора ``coordinator-session-v1``.

Spec ``clickhouse-migration-lifecycle``: сессионный advisory lock отдельного
координатора, не ключ Alembic и не журнал применённых версий. Подстановка
записывает вызов примитива в процессе и не открывает PostgreSQL.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass

from scripts.clickhouse_migration_control_plane.target_port import (
    ExecSqlRequest,
    IsolatedTargetPort,
)

ALEMBIC_LOCK_ID = 731984123


def _migration_control_namespace_key() -> int:
    """Фиксированный int32 пространства имён migration-control.

    Spec ``clickhouse-migration-lifecycle`` требует константу, отличную от
    ключа Alembic. Значение выводится из имени пространства, а не из
    ``731984123``.
    """
    digest = hashlib.sha256(
        b"clickhouse-migration-control-namespace-v1"
    ).digest()
    value = int.from_bytes(digest[:4], byteorder="big", signed=True)
    if value == ALEMBIC_LOCK_ID:
        raise RuntimeError("namespace key collided with the Alembic lock id")
    return value


MIGRATION_CONTROL_NAMESPACE_KEY = _migration_control_namespace_key()


class CoordinatorRefusal(Exception):
    """Отказ сессии координатора до вызова порта цели.

    Spec ``clickhouse-migration-lifecycle``: ложный ``try`` и смерть сессии
    не отправляют следующий statement. ``code`` называет эту причину.
    """

    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


@dataclass(frozen=True)
class AdvisoryLockCall:
    """Один вызов двухключевого advisory lock.

    Spec ``clickhouse-migration-lifecycle``: в журнале сессии только
    примитив PostgreSQL, без applied-status.
    """

    function: str
    namespace_key: int
    target_key: int


def target_key_for_isolated_default_db(server_uuid: str) -> int:
    """Знаковый int32 цели ``serverUUID`` плюс ``default_db``.

    Spec ``clickhouse-migration-lifecycle``: SHA-256 UTF-8 строки
    ``clickhouse-migration-control``, перевод строки, UUID, перевод строки,
    ``default_db``. Берутся первые четыре байта, big-endian.
    """
    text = f"clickhouse-migration-control\n{server_uuid}\ndefault_db"
    digest = hashlib.sha256(text.encode("utf-8")).digest()
    return int.from_bytes(digest[:4], byteorder="big", signed=True)


def refusal_before_statement(*, held: bool, alive: bool) -> str | None:
    """Можно ли звать порт, пока сессия держит lock.

    Spec ``clickhouse-migration-lifecycle``: решение принадлежит шву
    координатора. Подстановка не отправляет SQL, если функция вернула код.
    """
    if not alive:
        return "coordinator_session_lost"
    if not held:
        return "blocked_lock_contention"
    return None


class RecordingCoordinatorSession:
    """Внутрипроцессная сессия advisory lock без applied-status.

    Spec ``clickhouse-migration-lifecycle``: запись вызовов не заменяет
    ``refusal_before_statement`` и не хранит журнал ClickHouse.
    """

    def __init__(
        self,
        *,
        server_uuid: str,
        try_acquire_returns: bool,
    ) -> None:
        self.server_uuid = server_uuid
        self._calls: list[AdvisoryLockCall] = []
        self._held = False
        self._alive = True
        self._try_acquire_returns = try_acquire_returns
        self._statements_sent: list[str] = []

    @property
    def held(self) -> bool:
        """Сессия всё ещё держит advisory lock."""
        return self._held

    @property
    def calls(self) -> tuple[AdvisoryLockCall, ...]:
        """Записанные вызовы lock. Чтение nonce сюда не входит."""
        return tuple(self._calls)

    @property
    def statements_sent(self) -> tuple[str, ...]:
        """SQL, который сессия передала в порт под удержанным lock."""
        return tuple(self._statements_sent)

    @property
    def alive(self) -> bool:
        """Жива ли выделенная PostgreSQL session координатора."""
        return self._alive

    def acquire(self, *, operator_wait: bool = False) -> bool:
        """Взять ``pg_try_advisory_lock`` или явный ``pg_advisory_lock``.

        Spec ``clickhouse-migration-lifecycle``: блокирующий вызов только
        при ``operator_wait``. Ключ пространства имён не равен Alembic.
        """
        call = AdvisoryLockCall(
            function=(
                "pg_advisory_lock" if operator_wait else "pg_try_advisory_lock"
            ),
            namespace_key=MIGRATION_CONTROL_NAMESPACE_KEY,
            target_key=target_key_for_isolated_default_db(self.server_uuid),
        )
        self._calls.append(call)
        if operator_wait:
            self._held = True
            return True
        self._held = self._try_acquire_returns
        return self._held

    def send_statement(
        self,
        port: IsolatedTargetPort,
        request: ExecSqlRequest,
    ) -> None:
        """Передать statement в порт только при живом удержанном lock.

        Spec ``clickhouse-migration-lifecycle``: ложный ``try`` и мёртвая
        сессия не вызывают ``EXEC_SQL``. Санкцию команды это не выбирает.
        """
        reason = refusal_before_statement(held=self._held, alive=self._alive)
        if reason is not None:
            raise CoordinatorRefusal(reason)
        port.exec_sql(request)
        self._statements_sent.append(request.sql)

    def release(self) -> None:
        """Отпустить lock на той же живой сессии после terminal outcome.

        Spec ``clickhouse-migration-lifecycle``: unlock выполняется тем же
        namespace/target key. При уже умершей сессии явного unlock нет:
        PostgreSQL отпустил session lock вместе с соединением.
        """
        if not self._alive or not self._held:
            self._held = False
            return
        self._calls.append(
            AdvisoryLockCall(
                function="pg_advisory_unlock",
                namespace_key=MIGRATION_CONTROL_NAMESPACE_KEY,
                target_key=target_key_for_isolated_default_db(self.server_uuid),
            )
        )
        self._held = False

    def require_held(self) -> None:
        """Fail closed перед любой следующей мутацией target."""
        reason = refusal_before_statement(held=self._held, alive=self._alive)
        if reason is not None:
            raise CoordinatorRefusal(reason)

    def mark_session_dead(self) -> None:
        """Потерять сессию вместе с lock.

        Spec ``clickhouse-migration-lifecycle``: следующий statement после
        смерти координатора запрещён. Уже отправленный SQL не стирается.
        """
        self._alive = False
        self._held = False

    def read_nonce(self) -> str:
        """Наблюдение nonce. Это не захват lock.

        Spec ``clickhouse-migration-lifecycle``: чтение последнего nonce
        не выставляет ``held`` и не пишет ``pg_try_advisory_lock``.
        """
        return "nonce-observed"
