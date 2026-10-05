"""Чтение канонического корпуса ClickHouse и его отпечаток.

Spec ``clickhouse-migration-lifecycle``: идентичность ``001``–``005``
отделена от applied-state. Модуль читает сырые байты, выводит класс
привилегии из текста SQL и считает SHA-256. Порт цели, координатор, сеть
и журнал сюда не входят. Файлы корпуса не переписываются.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from pathlib import Path

from scripts.clickhouse_migration_control_plane.statements import (
    StatementParseError,
    split_statements,
)

_SCHEMA_DDL = "schema_ddl"
_PRIVILEGED_GRANT = "privileged_grant"

_CANONICAL_FILES: tuple[tuple[str, str], ...] = (
    ("001", "001_create_incremental_tables.sql"),
    ("002", "002_add_event_date_event_id_to_fact_stat_states.sql"),
    ("003", "003_add_buyouts_sum_rub_to_wb_common_stat.sql"),
    ("004", "004_create_auto_shelf_bid_increment_tables.sql"),
    ("005", "005_grant_system_log_truncate_to_adv_bot_user.sql"),
    ("006", "006_create_campaign_settings_history.sql"),
    (
        "007",
        "007_create_shop_campaign_inventory_and_availability.sql",
    ),
)

# SHA-256 сырых байтов канонических файлов, включая комментарии и переводы
# строк. Это записанный отпечаток пакета, а не хеш нарезки statement.
_IMMUTABLE_IDENTITY: tuple[tuple[str, str, str, str], ...] = (
    (
        "001",
        "001_create_incremental_tables.sql",
        _SCHEMA_DDL,
        "58400c33a0b1e3f8c57aab78bde5f0635fae00619ec537e36af558692336c688",
    ),
    (
        "002",
        "002_add_event_date_event_id_to_fact_stat_states.sql",
        _SCHEMA_DDL,
        "ddae5e6e91692b21ddb0b724ef50ea2395be43f2baa01187c664d3fa32607c2c",
    ),
    (
        "003",
        "003_add_buyouts_sum_rub_to_wb_common_stat.sql",
        _SCHEMA_DDL,
        "c359ebcbca17fc961b5081df4f7c264807df42a4e01912dc46067a56c69bbf28",
    ),
    (
        "004",
        "004_create_auto_shelf_bid_increment_tables.sql",
        _SCHEMA_DDL,
        "351b1af2b525ecbb53480b5cc2a59002d5f6f8ad938ef2ff6d7582500b57410a",
    ),
    (
        "005",
        "005_grant_system_log_truncate_to_adv_bot_user.sql",
        _PRIVILEGED_GRANT,
        "54a6ae0ea7b07ffb56784b50cbe29b627b56c0614f9377cd1a0cd69be7ce3cb0",
    ),
    (
        "006",
        "006_create_campaign_settings_history.sql",
        _SCHEMA_DDL,
        "424ee03f2521eeeceb4f35a9276fbc13c678f8322382d69a7059c5682d332eb2",
    ),
    (
        "007",
        "007_create_shop_campaign_inventory_and_availability.sql",
        _SCHEMA_DDL,
        "064772c5448a9824731cc8483a653e60b0c6a11f90937594b9ffd70a511479ab",
    ),
)

_NUMERIC_PREFIX = re.compile(r"^(\d+)")

_CREATE_OR_ALTER = re.compile(r"(?im)^\s*(CREATE|ALTER)\b")
_GRANT_LINE = re.compile(r"(?im)^\s*GRANT\b")
_DEFAULT_DB_OBJECT = re.compile(r"(?i)\bdefault_db\.[A-Za-z_][A-Za-z0-9_]*")
_SYSTEM_OBJECT = re.compile(r"(?i)\bsystem\.[A-Za-z_][A-Za-z0-9_]*")
_GRANT_ON_SYSTEM = re.compile(
    r"(?im)^\s*GRANT\b[^\n]*\bsystem\.[A-Za-z_][A-Za-z0-9_]*"
)


class CorpusAcceptanceError(Exception):
    """Корпус нельзя принять: класс или квалификация не сходятся с текстом.

    Spec ``clickhouse-migration-lifecycle``: отказ остаётся до исполнения
    SQL и до записи applied. ``code`` называет причину.
    """

    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


@dataclass(frozen=True)
class CorpusVersionIdentity:
    """Идентичность одной версии корпуса, не запись журнала цели.

    Spec ``clickhouse-migration-lifecycle``: id, имя файла, класс привилегии
    из текста SQL и SHA-256 сырых байтов. Эти поля не означают, что версия
    применена.
    """

    id: str
    filename: str
    privilege_class: str
    sha256: str


@dataclass(frozen=True)
class CorpusFingerprint:
    """Закрытый отпечаток ``001``–``005`` в порядке id.

    Spec ``clickhouse-migration-lifecycle``: файл ``006`` и session DDL
    тестовой базы сюда не входят. Отпечаток не заменяет байты SQL и не
    является applied-state.
    """

    versions: tuple[CorpusVersionIdentity, ...]


def canonical_corpus_dir() -> Path:
    """Каталог ``scripts/clickhouse_migrations`` этого репозитория.

    Spec ``clickhouse-migration-lifecycle``: канонический корпус лежит рядом
    с control plane. Чужой worktree и слой Alembic этим путём не читаются.
    """
    scripts_dir = Path(__file__).resolve().parents[1]
    return scripts_dir / "clickhouse_migrations"


def validate(corpus_dir: Path | None = None) -> CorpusFingerprint:
    """Принять корпус: прочитать пять файлов и вернуть отпечаток.

    Spec ``clickhouse-migration-lifecycle``, сценарии ``Register the existing
    corpus without executing it``, ``Qualification stays in the existing
    SQL``, ``Missing 006 is not imported``, ``Test DDL is not canonical``.
    Читаются только канонические имена. SQL не исполняется, сеть не
    открывается, applied не пишется, байты файлов не меняются.

    Args:
        corpus_dir: каталог корпуса. По умолчанию канонический каталог
            репозитория. Другие имена файлов в каталоге не читаются.

    Returns:
        Отпечаток пяти версий в порядке id.

    Raises:
        CorpusAcceptanceError: текст не даёт один класс привилегии, теряет
            квалификацию ``default_db`` / ``system`` или содержит ``;``
            внутри строкового литерала.
        FileNotFoundError: ожидаемого канонического файла нет.
    """
    root = canonical_corpus_dir() if corpus_dir is None else corpus_dir
    versions: list[CorpusVersionIdentity] = []
    for version_id, filename in _CANONICAL_FILES:
        raw = (root / filename).read_bytes()
        text = raw.decode("utf-8")
        privilege_class = _classify_privilege(text)
        _require_qualification(privilege_class, text)
        _require_statement_split(text)
        versions.append(
            CorpusVersionIdentity(
                id=version_id,
                filename=filename,
                privilege_class=privilege_class,
                sha256=_sha256_raw(raw),
            )
        )
    return CorpusFingerprint(versions=tuple(versions))


def immutable_fingerprint() -> CorpusFingerprint:
    """Записанный отпечаток ``001``–``005`` пакета.

    Spec ``clickhouse-migration-lifecycle``: SHA-256 — хеш сырых байтов
    вместе с комментариями и переводами строк. Класс ``005`` записан как
    ``privileged_grant``. Файл ``006`` в отпечаток не входит. Функция не
    читает диск и не исполняет SQL.
    """
    versions = tuple(
        CorpusVersionIdentity(
            id=version_id,
            filename=filename,
            privilege_class=privilege_class,
            sha256=digest,
        )
        for version_id, filename, privilege_class, digest in _IMMUTABLE_IDENTITY
    )
    return CorpusFingerprint(versions=versions)


def unreviewed_numeric_filenames(
    corpus_dir: Path,
    recorded: CorpusFingerprint | None = None,
) -> tuple[str, ...]:
    """Имена ``*.sql`` с числовым префиксом вне отпечатка пакета.

    Spec ``clickhouse-migration-lifecycle``: такой файл, включая
    непроверенный ``006`` в каталоге чтения, есть ``unreviewed_version``.
    Имя без числового префикса, в том числе session DDL, сюда не входит.
    Функция файл не исполняет и в отпечаток не добавляет.

    Args:
        corpus_dir: каталог, где лежат файлы миграций.
        recorded: принятый отпечаток пакета; по умолчанию ``immutable_fingerprint``.
    """
    fingerprint = recorded if recorded is not None else immutable_fingerprint()
    reviewed = frozenset(version.id for version in fingerprint.versions)
    found: list[str] = []
    for path in sorted(corpus_dir.iterdir()):
        if not path.is_file() or path.suffix != ".sql":
            continue
        match = _NUMERIC_PREFIX.match(path.name)
        if match is None:
            continue
        if match.group(1) not in reviewed:
            found.append(path.name)
    return tuple(found)


def _sha256_raw(payload: bytes) -> str:
    """SHA-256 сырых байт без нормализации перевода строк.

    Spec ``clickhouse-migration-lifecycle``: комментарии и перевод строки
    входят в идентичность. Хеш текста без комментариев не подменяет файл.
    """
    return hashlib.sha256(payload).hexdigest()


def _active_sql(sql_text: str) -> str:
    """Текст без полных строк ``--`` для класса и квалификации.

    Spec ``clickhouse-migration-lifecycle``: комментарии остаются в файле и
    в SHA-256. Для класса они не являются statement.
    """
    kept: list[str] = []
    for line in sql_text.splitlines():
        if line.lstrip().startswith("--"):
            continue
        kept.append(line)
    return "\n".join(kept)


def _classify_privilege(sql_text: str) -> str:
    """Вывести ``schema_ddl`` или ``privileged_grant`` из текста SQL.

    Spec ``clickhouse-migration-lifecycle``: класс — шаг планирования, не
    решение Owner. ``GRANT`` на ``system.<table>`` даёт ``privileged_grant``.
    ``CREATE`` / ``ALTER`` объекта ``default_db.<object>`` даёт ``schema_ddl``.
    Смешение обоих или отсутствие обоих останавливает принятие без SQL.
    """
    active = _active_sql(sql_text)
    has_grant = _GRANT_LINE.search(active) is not None and (
        _SYSTEM_OBJECT.search(active) is not None
    )
    has_schema = _CREATE_OR_ALTER.search(active) is not None and (
        _DEFAULT_DB_OBJECT.search(active) is not None
    )
    if has_grant and not has_schema:
        return _PRIVILEGED_GRANT
    if has_schema and not has_grant:
        return _SCHEMA_DDL
    raise CorpusAcceptanceError("privilege_class_unresolved")


def _require_qualification(privilege_class: str, sql_text: str) -> None:
    """Проверить, что квалификация объектов осталась в тексте.

    Spec ``clickhouse-migration-lifecycle``: ``schema_ddl`` держит
    ``default_db.<object>``, ``privileged_grant`` держит ``system.<table>``
    в строке ``GRANT``. Функция ничего не записывает и SQL не исполняет.
    """
    active = _active_sql(sql_text)
    if privilege_class == _SCHEMA_DDL:
        if _DEFAULT_DB_OBJECT.search(active) is None:
            raise CorpusAcceptanceError("qualification_missing")
        return
    if _GRANT_ON_SYSTEM.search(active) is None:
        raise CorpusAcceptanceError("qualification_missing")


def _require_statement_split(sql_text: str) -> None:
    """Остановить принятие, если в строке есть точка с запятой.

    Spec ``clickhouse-migration-lifecycle``: в канонических пяти файлах
    такой точки нет. Встретив её, разбор не возвращает statement и apply
    не начинает. Результат нарезки здесь не исполняется.
    """
    try:
        _ = split_statements(sql_text)
    except StatementParseError as exc:
        raise CorpusAcceptanceError(exc.code) from exc
