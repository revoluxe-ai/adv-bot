"""Fail-closed validator для destructive ClickHouse test endpoints.

Конфигурация проекта (реальные имена env):

* ``CLICK_HOUSE_HOST``
* ``CLICKHOUSE_PORT`` (HTTP)
* ``CLICK_HOUSE_USER`` / ``CLICK_HOUSE_PASSWORD``

Allowlist для destructive tests:

* host: ``localhost`` | ``127.0.0.1``
* port: ``8124`` (``tests/docker-compose.test.yml`` HTTP mapping)
* database: ``test_adv_bot_clickhouse`` (выделенное имя, не prod ``default_db``)
* opt-in: ``ALLOW_DESTRUCTIVE_TEST_CLICKHOUSE=1``
* tunnels: ``DEV_TUNNELS_ENABLED`` / tunnel port env — hard-fail

Вызывать ``validate_destructive_clickhouse_endpoint`` **до**
``get_async_client`` / ``create_async_client``.
"""

from __future__ import annotations

import os
import re
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from tests.support.destructive_pg_dsn import assert_no_dev_tunnels_for_destructive_tests

ALLOWED_CH_HOSTS: frozenset[str] = frozenset({"localhost", "127.0.0.1"})
ALLOWED_CH_HTTP_PORT: int = 8124
ALLOWED_CH_DATABASE: str = "test_adv_bot_clickhouse"
ALLOW_DESTRUCTIVE_TEST_CLICKHOUSE_ENV: str = "ALLOW_DESTRUCTIVE_TEST_CLICKHOUSE"

CLICK_HOUSE_HOST_ENV: str = "CLICK_HOUSE_HOST"
CLICKHOUSE_PORT_ENV: str = "CLICKHOUSE_PORT"
CLICK_HOUSE_USER_ENV: str = "CLICK_HOUSE_USER"
CLICK_HOUSE_PASSWORD_ENV: str = "CLICK_HOUSE_PASSWORD"

FORBIDDEN_CH_DATABASES: frozenset[str] = frozenset(
    {
        "production",
        "prod",
        "stage",
        "staging",
        "dev",
        "development",
        "adv_updater",
        "system",
        "default",
        "default_db",  # prod SQL prefix — запрещён для destructive tests
    }
)


class DestructiveTestClickHouseError(RuntimeError):
    """ClickHouse endpoint не прошёл fail-closed allowlist."""


@dataclass(frozen=True, slots=True)
class ValidatedDestructiveClickHouseEndpoint:
    """Безопасный CH endpoint после валидации (без password в repr)."""

    host: str
    port: int
    database: str
    username: str

    def render_redacted(self) -> str:
        """Строка для логов без секретов."""
        return (
            f"clickhouse://{self.username}:***@{self.host}:{self.port}/{self.database}"
        )


def _parse_truthy_opt_in(raw: str | None) -> bool:
    if raw is None:
        return False
    return str(raw).strip().lower() in {"1", "true", "yes", "on"}


def is_destructive_ch_opt_in_enabled(
    *,
    environ: dict[str, str] | None = None,
) -> bool:
    """Проверить ``ALLOW_DESTRUCTIVE_TEST_CLICKHOUSE`` без I/O."""
    env = environ if environ is not None else os.environ
    return _parse_truthy_opt_in(env.get(ALLOW_DESTRUCTIVE_TEST_CLICKHOUSE_ENV))


def validate_destructive_clickhouse_endpoint(
    *,
    host: str | None,
    port: int | str | None,
    database: str | None,
    username: str | None = None,
    allow_destructive: bool | None = None,
    environ: dict[str, str] | None = None,
    check_tunnels: bool = True,
) -> ValidatedDestructiveClickHouseEndpoint:
    """Валидировать CH endpoint до создания клиента.

    Raises:
        DestructiveTestClickHouseError: при любой несовместимости allowlist.
    """
    env = environ if environ is not None else os.environ
    if check_tunnels:
        try:
            assert_no_dev_tunnels_for_destructive_tests(environ=dict(env))
        except Exception as exc:  # noqa: BLE001 — map to CH error type
            raise DestructiveTestClickHouseError(str(exc)) from None

    opt_in = (
        allow_destructive
        if allow_destructive is not None
        else is_destructive_ch_opt_in_enabled(environ=dict(env))
    )
    if not opt_in:
        raise DestructiveTestClickHouseError(
            "Destructive ClickHouse tests require explicit opt-in "
            f"{ALLOW_DESTRUCTIVE_TEST_CLICKHOUSE_ENV}=1 — refuse connect"
        )

    if host is None or not str(host).strip():
        raise DestructiveTestClickHouseError(
            "ClickHouse host is empty — refuse connect"
        )
    host_norm = str(host).strip().lower()
    if host_norm not in ALLOWED_CH_HOSTS:
        raise DestructiveTestClickHouseError(
            f"ClickHouse host {host_norm!r} is not allowlisted "
            f"(allowed={sorted(ALLOWED_CH_HOSTS)}) — refuse connect"
        )

    if port is None or str(port).strip() == "":
        raise DestructiveTestClickHouseError(
            "ClickHouse port is empty — refuse connect"
        )
    try:
        port_int = int(port)
    except (TypeError, ValueError) as exc:
        raise DestructiveTestClickHouseError(
            f"ClickHouse port {port!r} is not an int — refuse connect"
        ) from exc
    if port_int != ALLOWED_CH_HTTP_PORT:
        raise DestructiveTestClickHouseError(
            f"ClickHouse port {port_int} is not the test HTTP port "
            f"{ALLOWED_CH_HTTP_PORT} — refuse connect"
        )

    if database is None or not str(database).strip():
        raise DestructiveTestClickHouseError(
            "ClickHouse database is empty — refuse connect"
        )
    db = str(database).strip()
    db_lower = db.lower()
    if db_lower in FORBIDDEN_CH_DATABASES:
        raise DestructiveTestClickHouseError(
            f"ClickHouse database {db!r} is forbidden — refuse connect"
        )
    if db != ALLOWED_CH_DATABASE:
        raise DestructiveTestClickHouseError(
            f"ClickHouse database must be exactly {ALLOWED_CH_DATABASE!r}, "
            f"got {db!r} — refuse connect"
        )

    user = (username or "").strip() or "CLICK_HOUSE_USER"
    return ValidatedDestructiveClickHouseEndpoint(
        host=host_norm,
        port=port_int,
        database=db,
        username=user,
    )


def validate_destructive_clickhouse_from_environ(
    *,
    environ: dict[str, str] | None = None,
    database: str = ALLOWED_CH_DATABASE,
) -> ValidatedDestructiveClickHouseEndpoint:
    """Прочитать CH env и провалидировать (без сети)."""
    env = environ if environ is not None else os.environ
    return validate_destructive_clickhouse_endpoint(
        host=env.get(CLICK_HOUSE_HOST_ENV),
        port=env.get(CLICKHOUSE_PORT_ENV),
        database=database,
        username=env.get(CLICK_HOUSE_USER_ENV),
        environ=dict(env),
    )


async def create_validated_async_clickhouse_client(
    *,
    host: str,
    port: int | str,
    database: str,
    username: str,
    password: str,
    get_async_client_fn: Callable[..., Any],
    environ: dict[str, str] | None = None,
    wrap_sql_guard: bool = True,
    **client_kwargs: Any,
) -> Any:
    """Validation-before-connect: factory вызывается только после allowlist.

    По умолчанию оборачивает клиент в ``GuardedClickHouseClient`` (SQL gate).
    """
    validate_destructive_clickhouse_endpoint(
        host=host,
        port=port,
        database=database,
        username=username,
        environ=environ,
    )
    client = await get_async_client_fn(
        host=host,
        port=int(port),
        username=username,
        password=password,
        database=database,
        **client_kwargs,
    )
    if wrap_sql_guard:
        return GuardedClickHouseClient(client)
    return client


_IDENT = r'(?:`[^`]+`|"[^"]+"|[A-Za-z_][A-Za-z0-9_]*)'
_QUALIFIED_IDENT_RE = re.compile(
    rf"(?P<db>{_IDENT})\s*\.\s*(?P<object>{_IDENT})",
    re.IGNORECASE,
)
_DESTRUCTIVE_VERB_RE = re.compile(
    r"\b(DROP|TRUNCATE|ALTER|DELETE|CREATE)\b",
    re.IGNORECASE,
)
_DESTRUCTIVE_TARGET_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    (
        "DROP TABLE",
        re.compile(
            rf"^\s*DROP\s+TABLE\s+(?:IF\s+EXISTS\s+)?(?P<target>{_IDENT}(?:\s*\.\s*{_IDENT})?)\b",
            re.IGNORECASE | re.DOTALL,
        ),
    ),
    (
        "DROP VIEW",
        re.compile(
            rf"^\s*DROP\s+VIEW\s+(?:IF\s+EXISTS\s+)?(?P<target>{_IDENT}(?:\s*\.\s*{_IDENT})?)\b",
            re.IGNORECASE | re.DOTALL,
        ),
    ),
    (
        "TRUNCATE TABLE",
        re.compile(
            rf"^\s*TRUNCATE\s+TABLE\s+(?:IF\s+EXISTS\s+)?(?P<target>{_IDENT}(?:\s*\.\s*{_IDENT})?)\b",
            re.IGNORECASE | re.DOTALL,
        ),
    ),
    (
        "ALTER TABLE",
        re.compile(
            rf"^\s*ALTER\s+TABLE\s+(?P<target>{_IDENT}(?:\s*\.\s*{_IDENT})?)\b",
            re.IGNORECASE | re.DOTALL,
        ),
    ),
    (
        "DELETE FROM",
        re.compile(
            rf"^\s*DELETE\s+FROM\s+(?P<target>{_IDENT}(?:\s*\.\s*{_IDENT})?)\b",
            re.IGNORECASE | re.DOTALL,
        ),
    ),
    (
        "CREATE TABLE",
        re.compile(
            rf"^\s*CREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?(?P<target>{_IDENT}(?:\s*\.\s*{_IDENT})?)\b",
            re.IGNORECASE | re.DOTALL,
        ),
    ),
    (
        "CREATE VIEW",
        re.compile(
            rf"^\s*CREATE\s+(?:MATERIALIZED\s+)?VIEW\s+(?:IF\s+NOT\s+EXISTS\s+)?(?P<target>{_IDENT}(?:\s*\.\s*{_IDENT})?)\b",
            re.IGNORECASE | re.DOTALL,
        ),
    ),
)
_LINE_COMMENT_RE = re.compile(r"--[^\n\r]*")
_BLOCK_COMMENT_RE = re.compile(r"/\*.*?\*/", re.DOTALL)


def _strip_identifier_quotes(token: str) -> str:
    """Снять quoting/backticks вокруг SQL-идентификатора."""
    raw = token.strip()
    if len(raw) >= 2 and raw[0] == raw[-1] and raw[0] in {'"', "`"}:
        return raw[1:-1]
    return raw


def _remove_sql_comments(sql: str) -> str:
    """Удалить SQL comments для устойчивого policy-анализа."""
    no_block = _BLOCK_COMMENT_RE.sub(" ", sql)
    return _LINE_COMMENT_RE.sub(" ", no_block)


def _split_statements(sql: str) -> list[str]:
    """Разбить SQL на statements по ``;`` вне quoted контекстов."""
    statements: list[str] = []
    buf: list[str] = []
    in_single = False
    in_double = False
    in_backtick = False
    i = 0
    while i < len(sql):
        ch = sql[i]
        nxt = sql[i + 1] if i + 1 < len(sql) else ""
        if ch == "'" and not in_double and not in_backtick:
            if in_single and nxt == "'":
                buf.append(ch)
                buf.append(nxt)
                i += 2
                continue
            in_single = not in_single
            buf.append(ch)
            i += 1
            continue
        if ch == '"' and not in_single and not in_backtick:
            if in_double and nxt == '"':
                buf.append(ch)
                buf.append(nxt)
                i += 2
                continue
            in_double = not in_double
            buf.append(ch)
            i += 1
            continue
        if ch == "`" and not in_single and not in_double:
            in_backtick = not in_backtick
            buf.append(ch)
            i += 1
            continue
        if ch == ";" and not in_single and not in_double and not in_backtick:
            statement = "".join(buf).strip()
            if statement:
                statements.append(statement)
            buf = []
            i += 1
            continue
        buf.append(ch)
        i += 1
    tail = "".join(buf).strip()
    if tail:
        statements.append(tail)
    return statements


def _parse_qualified_target(target: str) -> tuple[str, str]:
    """Извлечь db/object из ``db.object`` с кавычками/backticks."""
    m = re.fullmatch(
        rf"\s*(?P<db>{_IDENT})\s*\.\s*(?P<object>{_IDENT})\s*",
        target,
        re.IGNORECASE | re.DOTALL,
    )
    if m is None:
        raise DestructiveTestClickHouseError(
            "Destructive SQL requires fully-qualified target "
            f"{ALLOWED_CH_DATABASE!r}.<object> — unqualified target forbidden"
        )
    db = _strip_identifier_quotes(m.group("db"))
    obj = _strip_identifier_quotes(m.group("object"))
    return db, obj


def _extract_destructive_target(statement: str) -> tuple[str, str] | None:
    """Найти destructive-команду и target object (если шаблон поддержан)."""
    for command, pattern in _DESTRUCTIVE_TARGET_PATTERNS:
        m = pattern.match(statement)
        if m is not None:
            return command, m.group("target")
    return None


def _assert_readonly_references_allowed(statement: str) -> None:
    """Разрешить только test DB + system/info_schema для non-destructive SQL."""
    readonly_ok = {
        ALLOWED_CH_DATABASE.lower(),
        "system",
        "information_schema",
    }
    for m in _QUALIFIED_IDENT_RE.finditer(statement):
        db = _strip_identifier_quotes(m.group("db")).lower()
        if db == "default_db":
            raise DestructiveTestClickHouseError(
                "ClickHouse SQL must not reference default_db — "
                f"use {ALLOWED_CH_DATABASE!r} only"
            )
        if db in FORBIDDEN_CH_DATABASES and db not in {"system"}:
            raise DestructiveTestClickHouseError(
                f"ClickHouse SQL references forbidden database {db!r} — refuse"
            )
        if db not in readonly_ok and db in {
            "adv_bot",
            "adv-bot",
            "postgres",
            "production",
            "prod",
            "stage",
            "staging",
        }:
            raise DestructiveTestClickHouseError(
                f"ClickHouse SQL references non-test database {db!r} — refuse"
            )


def assert_destructive_clickhouse_sql_allowed(sql: str | None) -> None:
    """Fail-closed SQL policy для command/query перед вызовом underlying client.

    Блокирует multi-statements, ``USE``, ``CREATE/DROP DATABASE``, unqualified
    destructive SQL и любые destructive operations вне
    ``test_adv_bot_clickhouse.<object>``.
    """
    if sql is None:
        raise DestructiveTestClickHouseError("ClickHouse SQL is empty — refuse")
    original = str(sql)
    without_comments = _remove_sql_comments(original)
    statements = _split_statements(without_comments)
    if not statements:
        raise DestructiveTestClickHouseError("ClickHouse SQL is empty — refuse")
    if len(statements) > 1:
        raise DestructiveTestClickHouseError(
            "ClickHouse multi-statement SQL is forbidden in destructive tests"
        )
    statement = statements[0]
    normalized = re.sub(r"\s+", " ", statement).strip().lower()

    if "default_db" in normalized:
        raise DestructiveTestClickHouseError(
            "ClickHouse SQL must not reference default_db — "
            f"use {ALLOWED_CH_DATABASE!r} only"
        )
    if normalized.startswith("use "):
        raise DestructiveTestClickHouseError(
            "ClickHouse SQL must not change database via USE"
        )
    if re.search(r"\b(create|drop)\s+database\b", normalized, flags=re.IGNORECASE):
        raise DestructiveTestClickHouseError(
            "ClickHouse CREATE/DROP DATABASE is forbidden in destructive tests"
        )

    destructive = _DESTRUCTIVE_VERB_RE.search(normalized) is not None
    if not destructive:
        _assert_readonly_references_allowed(statement)
        return

    parsed = _extract_destructive_target(statement)
    if parsed is None:
        raise DestructiveTestClickHouseError(
            "Unsupported destructive SQL shape — require explicit qualified "
            f"{ALLOWED_CH_DATABASE!r}.<object> target"
        )
    command, target = parsed
    db, _obj = _parse_qualified_target(target)
    if db.lower() != ALLOWED_CH_DATABASE.lower():
        raise DestructiveTestClickHouseError(
            f"{command} target must use {ALLOWED_CH_DATABASE!r}, got {db!r}"
        )


def assert_destructive_clickhouse_table_allowed(table: str | None) -> None:
    """Проверить target table для ``insert`` до underlying client.insert."""
    if table is None or not str(table).strip():
        raise DestructiveTestClickHouseError("ClickHouse table name is empty — refuse")
    name = str(table).strip()
    if "default_db" in name.lower():
        raise DestructiveTestClickHouseError(
            "ClickHouse table must not reference default_db — refuse"
        )
    db, _obj = _parse_qualified_target(name)
    if db.lower() != ALLOWED_CH_DATABASE.lower():
        raise DestructiveTestClickHouseError(
            f"ClickHouse table database must be {ALLOWED_CH_DATABASE!r}, got {db!r}"
        )


class GuardedClickHouseClient:
    """Fail-closed wrapper: только явный whitelist API, без raw-client доступа."""

    __slots__ = ("__inner_client",)

    def __init__(self, client: Any) -> None:
        """Args:
            client: исходный async ClickHouse client после endpoint validation.
        """
        self.__inner_client = client

    async def command(self, *args: Any, **kwargs: Any) -> Any:
        """Выполнить ``command`` только после SQL policy-check."""
        sql = args[0] if args else kwargs.get("cmd", kwargs.get("query"))
        assert_destructive_clickhouse_sql_allowed(
            sql if isinstance(sql, str) else str(sql) if sql is not None else None
        )
        return await self.__inner_client.command(*args, **kwargs)

    async def query(self, *args: Any, **kwargs: Any) -> Any:
        """Выполнить ``query`` только после SQL policy-check."""
        sql = args[0] if args else kwargs.get("query")
        assert_destructive_clickhouse_sql_allowed(
            sql if isinstance(sql, str) else str(sql) if sql is not None else None
        )
        return await self.__inner_client.query(*args, **kwargs)

    async def insert(self, *args: Any, **kwargs: Any) -> Any:
        """Выполнить ``insert`` только для qualified table в test DB."""
        table = args[0] if args else kwargs.get("table")
        assert_destructive_clickhouse_table_allowed(
            table if isinstance(table, str) else str(table) if table is not None else None
        )
        return await self.__inner_client.insert(*args, **kwargs)

    def close(self) -> Any:
        """Закрыть underlying client через whitelisted lifecycle API."""
        return self.__inner_client.close()

    def __getattr__(self, name: str) -> Any:
        """Запретить доступ к не-whitelisted API underlying client."""
        raise AttributeError(
            f"GuardedClickHouseClient does not expose attribute {name!r}. "
            "Allowed API: command, query, insert, close."
        )
