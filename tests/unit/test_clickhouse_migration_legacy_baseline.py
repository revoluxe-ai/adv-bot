"""LEGACY_BASELINE корпуса ClickHouse ``001``–``005``.

Фиксирует сырые байты канонических SQL и границы чужих слоёв до запускатора.
Spec: ``clickhouse-migration-lifecycle``. Тесты остаются зелёными, когда
пакет control plane появится: они не требуют его отсутствия.

Чужой worktree shop-wide и файл ``006`` оттуда не открываются. Сокет,
учётные данные, Kubernetes и выкладка не используются.
"""

from __future__ import annotations

import hashlib
import re
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

_REPO_ROOT = Path(__file__).resolve().parents[2]
_CORPUS_DIR = _REPO_ROOT / "scripts" / "clickhouse_migrations"
_ALEMBIC_INI = _REPO_ROOT / "alembic.ini"
_ALEMBIC_DIR = _REPO_ROOT / "alembic_"
_DESTRUCTIVE_CH_RESET = _REPO_ROOT / "tests" / "support" / "destructive_ch_reset.py"

# SHA-256 сырых байт файлов на диске. Не хеш текста после универсальных
# переводов строк и не хеш SQL без комментариев.
_RAW_SHA256_BY_FILENAME: dict[str, str] = {
    "001_create_incremental_tables.sql": (
        "58400c33a0b1e3f8c57aab78bde5f0635fae00619ec537e36af558692336c688"
    ),
    "002_add_event_date_event_id_to_fact_stat_states.sql": (
        "ddae5e6e91692b21ddb0b724ef50ea2395be43f2baa01187c664d3fa32607c2c"
    ),
    "003_add_buyouts_sum_rub_to_wb_common_stat.sql": (
        "c359ebcbca17fc961b5081df4f7c264807df42a4e01912dc46067a56c69bbf28"
    ),
    "004_create_auto_shelf_bid_increment_tables.sql": (
        "351b1af2b525ecbb53480b5cc2a59002d5f6f8ad938ef2ff6d7582500b57410a"
    ),
    "005_grant_system_log_truncate_to_adv_bot_user.sql": (
        "54a6ae0ea7b07ffb56784b50cbe29b627b56c0614f9377cd1a0cd69be7ce3cb0"
    ),
    "006_create_campaign_settings_history.sql": (
        "424ee03f2521eeeceb4f35a9276fbc13c678f8322382d69a7059c5682d332eb2"
    ),
    "007_create_shop_campaign_inventory_and_availability.sql": (
        "064772c5448a9824731cc8483a653e60b0c6a11f90937594b9ffd70a511479ab"
    ),
    "008_create_attribution_facts.sql": (
        "6b0edcb3a7a23a15b8d9b273552c476ca5d79052f6a4d47f2b8728fdb4ce0356"
    ),
}

_004_FILENAME = "004_create_auto_shelf_bid_increment_tables.sql"
_004_DEFAULT_DB_OBJECTS: tuple[str, ...] = (
    "CREATE TABLE IF NOT EXISTS default_db.auto_shelf_bid_intervals",
    "CREATE TABLE IF NOT EXISTS default_db.auto_shelf_bid_prev",
)

_CORPUS_REVISION_IDS: tuple[str, ...] = (
    "001",
    "002",
    "003",
    "004",
    "005",
    "006",
    "007",
    "008",
)
_ALEMBIC_REVISION_LINE = re.compile(
    r"(?m)^(?:Revision ID:\s*|revision\s*(?::\s*str\s*)?=\s*)['\"]?"
    r"(00[1-7])['\"]?\s*$"
)
_TEXT_SUFFIXES: frozenset[str] = frozenset({".py", ".mako", ".ini", ".toml", ".cfg"})


def _sha256_raw(payload: bytes) -> str:
    """SHA-256 переданных байт без перекодирования.

    Spec ``clickhouse-migration-lifecycle``: отпечаток корпуса — хеш сырого
    файла, поэтому нормализация перевода строк здесь не выполняется.
    """
    return hashlib.sha256(payload).hexdigest()


def _without_full_line_comments(raw: bytes) -> bytes:
    """Убирает полные строки ``--``, чтобы доказать, что отпечаток их хранит.

    Spec ``clickhouse-migration-lifecycle`` запрещает отбрасывать комментарии
    из идентичности корпуса. Этот помощник нужен только тесту: если сырой
    хеш совпадёт с хешем без комментариев, baseline не отличит порчу файла.
    """
    kept: list[bytes] = []
    for line in raw.split(b"\n"):
        if line.lstrip().startswith(b"--"):
            continue
        kept.append(line)
    return b"\n".join(kept)


def _read_corpus_raw(filename: str) -> bytes:
    """Читает один файл корпуса байтами из этого worktree.

    Spec ``clickhouse-migration-lifecycle``: идентичность ``001``–``005``
    считается по файлу на диске. ``Path.read_bytes`` не переводит ``\\n``.
    """
    return (_CORPUS_DIR / filename).read_bytes()


def test_legacy_baseline_pins_raw_sha256_and_004_default_db_names() -> None:
    """Фиксирует SHA-256 сырых ``001``–``005`` и читатель объектов ``004``.

    Spec ``clickhouse-migration-lifecycle``: корпус не переписывается, хеш
    не нормализует переводы строк и не выкидывает комментарии, а существующий
    читатель ``004`` по-прежнему видит
    ``default_db.auto_shelf_bid_intervals`` и
    ``default_db.auto_shelf_bid_prev``. Запускатор этому тесту не нужен и
    его отсутствие не требуется.
    """
    present = sorted(path.name for path in _CORPUS_DIR.iterdir() if path.is_file())
    assert present == sorted(_RAW_SHA256_BY_FILENAME)

    for filename, expected in _RAW_SHA256_BY_FILENAME.items():
        raw = _read_corpus_raw(filename)
        assert _sha256_raw(raw) == expected
        assert _sha256_raw(_without_full_line_comments(raw)) != expected
        crlf = raw.replace(b"\n", b"\r\n")
        assert _sha256_raw(crlf) != expected

    raw_004 = _read_corpus_raw(_004_FILENAME)
    reader_text = (_CORPUS_DIR / _004_FILENAME).read_text(encoding="utf-8")
    for qualified_name in _004_DEFAULT_DB_OBJECTS:
        assert qualified_name in reader_text
        assert qualified_name.encode("utf-8") in raw_004


def _alembic_text_files() -> list[Path]:
    """Собирает текстовые файлы слоя Alembic этого репозитория.

    Spec ``clickhouse-migration-lifecycle``: PostgreSQL Alembic не становится
    корпусом ClickHouse. Обход ограничен ``alembic.ini`` и ``alembic_/``.
    """
    files = [_ALEMBIC_INI]
    for path in _ALEMBIC_DIR.rglob("*"):
        if not path.is_file():
            continue
        if path.suffix.lower() not in _TEXT_SUFFIXES:
            continue
        if "__pycache__" in path.parts:
            continue
        files.append(path)
    return files


def test_legacy_baseline_foreign_trees_stay_outside_corpus() -> None:
    """Проверяет, что Alembic и session DDL не стали корпусом ClickHouse.

    Spec ``clickhouse-migration-lifecycle``, сценарии ``Alembic stays out of
    ClickHouse migrations`` и ``Test DDL is not canonical``. Корпус ``001``–``007``
    лежит только в ``scripts/clickhouse_migrations``; чужие ``009``+ не
    подмешиваются из соседних worktree.
    """
    corpus_resolved = _CORPUS_DIR.resolve()
    destructive_resolved = _DESTRUCTIVE_CH_RESET.resolve()
    assert destructive_resolved.is_file()
    assert corpus_resolved not in destructive_resolved.parents
    destructive_text = destructive_resolved.read_text(encoding="utf-8")
    assert "test_adv_bot_clickhouse" in destructive_text

    for filename in _RAW_SHA256_BY_FILENAME:
        corpus_text = (_CORPUS_DIR / filename).read_text(encoding="utf-8")
        assert "test_adv_bot_clickhouse" not in corpus_text
        assert "destructive_ch_reset" not in corpus_text

    copied_009 = [
        path
        for path in _CORPUS_DIR.rglob("*")
        if path.is_file() and path.name.startswith("009")
    ]
    assert copied_009 == []
    assert sorted(path.name for path in _CORPUS_DIR.iterdir() if path.is_file()) == (
        sorted(_RAW_SHA256_BY_FILENAME)
    )

    corpus_names = set(_RAW_SHA256_BY_FILENAME)
    for path in _alembic_text_files():
        assert path.name not in corpus_names
        assert not path.name.startswith(_CORPUS_REVISION_IDS)
        text = path.read_text(encoding="utf-8")
        assert "clickhouse_migrations" not in text
        assert "ch_schema_migration_ledger" not in text
        for corpus_name in corpus_names:
            assert corpus_name not in text
        assert _ALEMBIC_REVISION_LINE.search(text) is None

    alembic_ini = _ALEMBIC_INI.read_text(encoding="utf-8")
    assert "script_location = alembic_" in alembic_ini

    opened = (
        _CORPUS_DIR,
        _ALEMBIC_INI,
        _ALEMBIC_DIR,
        _DESTRUCTIVE_CH_RESET,
    )
    for path in opened:
        relative = path.resolve().relative_to(_REPO_ROOT)
        assert relative.parts[0] not in {"k8s", "dockers"}
        assert path.name != ".env"
