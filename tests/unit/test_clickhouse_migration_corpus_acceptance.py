"""Принятие корпуса ``001``–``005`` через ``validate`` без исполнения.

Spec ``clickhouse-migration-lifecycle``: отпечаток фиксирует id, имя файла,
класс привилегии и SHA-256 сырых байтов. Порт цели и сессия координатора
из среза 2 здесь только свидетели, что ``validate`` до них не доходит.
Живой сокет, учётные данные и запись applied не используются.
"""

from __future__ import annotations

import hashlib
import inspect
import re
import shutil
import socket
from pathlib import Path

import pytest

from scripts.clickhouse_migration_control_plane.corpus import (
    CorpusFingerprint,
    CorpusVersionIdentity,
    canonical_corpus_dir,
    validate,
)
from tests.unit.clickhouse_migration_contract_fixture import (
    make_coordinator,
    make_target_port,
)

pytestmark = pytest.mark.unit

_REPO_ROOT = Path(__file__).resolve().parents[2]
_DESTRUCTIVE_CH_RESET = (
    _REPO_ROOT / "tests" / "support" / "destructive_ch_reset.py"
)
_REWRITE_SEAM = _REPO_ROOT / "tests" / "support" / "rewrite_default_db_ch_client.py"

# Те же сырые SHA-256, что у LEGACY_BASELINE. Это канонические байты, а не
# хеш после нормализации перевода строк или вырезания комментариев.
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
}

_IDS_IN_ORDER: tuple[str, ...] = ("001", "002", "003", "004", "005", "006", "007")
_FILENAMES_IN_ORDER: tuple[str, ...] = tuple(_RAW_SHA256_BY_FILENAME)
_SCHEMA_PRIVILEGE = "schema_ddl"
_GRANT_PRIVILEGE = "privileged_grant"

_DEFAULT_DB_OBJECTS: dict[str, tuple[str, ...]] = {
    "001": (
        "default_db.wb_common_stat_incremental",
        "default_db.wb_common_stat_hourly",
        "default_db.full_adv_wb_stat_incremental",
        "default_db.full_adv_wb_stat_hourly",
    ),
    "002": ("default_db.fact_stat_states",),
    "003": ("default_db.wb_common_stat",),
    "004": (
        "default_db.auto_shelf_bid_intervals",
        "default_db.auto_shelf_bid_prev",
    ),
    "006": ("default_db.campaign_settings_history",),
    "007": (
        "default_db.shop_campaign_inventory",
        "default_db.shop_campaign_collection_availability",
    ),
}
_SYSTEM_OBJECTS: tuple[str, ...] = (
    "system.processors_profile_log",
    "system.metric_log",
    "system.query_log",
    "system.text_log",
    "system.asynchronous_metric_log",
    "system.query_metric_log",
    "system.part_log",
    "system.trace_log",
    "system.error_log",
)

_QUALIFIED_OBJECT = re.compile(r"\b(?:default_db|system)\.[A-Za-z_][A-Za-z0-9_]*")


def _sha256_raw(payload: bytes) -> str:
    """SHA-256 переданных байт без перекодирования.

    Spec ``clickhouse-migration-lifecycle``: отпечаток считается по сырому
    файлу. Этот помощник нужен тесту, чтобы сверить результат ``validate``
    с независимым чтением, а не с заранее подставленным флагом.
    """
    return hashlib.sha256(payload).hexdigest()


def _snapshot_corpus(corpus_dir: Path) -> dict[str, bytes]:
    """Снимок сырых байт файлов каталога до принятия.

    Spec ``clickhouse-migration-lifecycle`` запрещает менять байты
    ``001``–``005``. Снимок сравнивается после ``validate``.
    """
    return {
        path.name: path.read_bytes()
        for path in corpus_dir.iterdir()
        if path.is_file()
    }


def _forbid_new_socket(monkeypatch: pytest.MonkeyPatch) -> None:
    """Сторож конструктора сокета на время ``validate``.

    Spec ``clickhouse-migration-lifecycle``: принятие корпуса не открывает
    сеть. У ``validate`` нет параметра клиента, поэтому более узкий шов
    подменить нельзя: сторож стоит на конструкторе сокета процесса.
    """

    def _boom(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("validate открыл сокет")

    monkeypatch.setattr(socket, "socket", _boom)
    monkeypatch.setattr(socket, "create_connection", _boom)


def test_validate_registers_corpus_without_executing_it(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Фиксирует id, имя, класс и SHA-256, не исполняя SQL и не пиша applied.

    Spec ``clickhouse-migration-lifecycle``, сценарий ``Register the existing
    corpus without executing it``. ``validate`` читает канонический каталог.
    Порт ``isolated-target-port-v1`` и сессия ``coordinator-session-v1``
    остаются пустыми: команда до них не доходит и applied не записывает.
    Класс ``005`` — планировочный ``privileged_grant``, не решение Owner.
    """
    corpus_dir = canonical_corpus_dir()
    before = _snapshot_corpus(corpus_dir)
    port = make_target_port()
    coordinator = make_coordinator()
    _forbid_new_socket(monkeypatch)

    fingerprint = validate()

    assert isinstance(fingerprint, CorpusFingerprint)
    assert [field.name for field in fingerprint.__dataclass_fields__.values()] == [
        "versions",
    ]
    identity_fields = [
        field.name for field in CorpusVersionIdentity.__dataclass_fields__.values()
    ]
    assert identity_fields == ["id", "filename", "privilege_class", "sha256"]
    assert "applied" not in identity_fields
    assert "version_applied" not in identity_fields

    versions = fingerprint.versions
    assert tuple(version.id for version in versions) == _IDS_IN_ORDER
    assert tuple(version.filename for version in versions) == _FILENAMES_IN_ORDER
    for version in versions:
        raw = before[version.filename]
        assert version.sha256 == _sha256_raw(raw)
        assert version.sha256 == _RAW_SHA256_BY_FILENAME[version.filename]
        assert _sha256_raw(raw.replace(b"\n", b"\r\n")) != version.sha256
    by_id = {version.id: version for version in versions}
    for version_id in ("001", "002", "003", "004", "006"):
        assert by_id[version_id].privilege_class == _SCHEMA_PRIVILEGE
    assert by_id["005"].privilege_class == _GRANT_PRIVILEGE

    assert _snapshot_corpus(corpus_dir) == before
    assert port.executed == ()
    assert port.operations == ()
    assert coordinator.calls == ()
    assert coordinator.statements_sent == ()
    assert coordinator.held is False
    parameters = inspect.signature(validate).parameters
    assert "port" not in parameters
    assert "coordinator" not in parameters
    assert "target" not in parameters


def test_validate_keeps_default_db_and_system_qualification() -> None:
    """После ``validate`` квалификация объектов остаётся в исходном SQL.

    Spec ``clickhouse-migration-lifecycle``, сценарий ``Qualification stays
    in the existing SQL``. ``001``–``004`` по-прежнему именуют
    ``default_db.<object>``, ``005`` по-прежнему именует ``system.<table>``
    в ``GRANT``. Принятие не переписывает файлы.
    """
    corpus_dir = canonical_corpus_dir()
    before = _snapshot_corpus(corpus_dir)

    fingerprint = validate()

    assert _snapshot_corpus(corpus_dir) == before
    by_id = {version.id: version for version in fingerprint.versions}
    for version_id, objects in _DEFAULT_DB_OBJECTS.items():
        raw = before[by_id[version_id].filename]
        text = raw.decode("utf-8")
        assert by_id[version_id].privilege_class == _SCHEMA_PRIVILEGE
        for qualified in objects:
            assert qualified in text
            assert qualified.encode("utf-8") in raw
        assert _QUALIFIED_OBJECT.search(text)
        assert "test_adv_bot_clickhouse" not in text
    grant = before[by_id["005"].filename]
    grant_text = grant.decode("utf-8")
    assert by_id["005"].privilege_class == _GRANT_PRIVILEGE
    for qualified in _SYSTEM_OBJECTS:
        assert qualified in grant_text
        assert f"GRANT TRUNCATE ON {qualified} TO adv_bot_user;" in grant_text
    assert "default_db." not in grant_text


def test_validate_fingerprint_is_exactly_001_through_007(
    tmp_path: Path,
) -> None:
    """Reviewed ``006``–``007`` входят в corpus, чужой successor не входит.

    Spec ``clickhouse-migration-lifecycle``, сценарии reviewed successor и
    ``Unreviewed successor blocks apply``. Хеш копии включает комментарии,
    а соседний ``008`` не расширяет reviewed fingerprint.
    """
    corpus_dir = canonical_corpus_dir()
    canonical = validate()
    assert tuple(version.id for version in canonical.versions) == _IDS_IN_ORDER
    assert canonical.versions[-1].id == "007"
    assert canonical.versions[-1].privilege_class == _SCHEMA_PRIVILEGE

    for filename in _FILENAMES_IN_ORDER:
        shutil.copyfile(corpus_dir / filename, tmp_path / filename)
    probed_name = _FILENAMES_IN_ORDER[0]
    probed_path = tmp_path / probed_name
    probed_raw = probed_path.read_bytes() + b"\n-- probe-keeps-comments\n"
    probed_path.write_bytes(probed_raw)
    foreign = tmp_path / "008_unreviewed.sql"
    foreign.write_bytes(b"-- FOREIGN_008_MARKER\nSELECT 1;\n")
    fingerprint = validate(corpus_dir=tmp_path)

    assert tuple(version.id for version in fingerprint.versions) == _IDS_IN_ORDER
    assert all(not version.filename.startswith("008") for version in fingerprint.versions)
    assert all(
        version.sha256 != _sha256_raw(foreign.read_bytes())
        for version in fingerprint.versions
    )
    probed = fingerprint.versions[0]
    assert probed.filename == probed_name
    assert probed.sha256 == _sha256_raw(probed_raw)
    assert probed.sha256 != _RAW_SHA256_BY_FILENAME[probed_name]
    assert probed.privilege_class == _SCHEMA_PRIVILEGE
    assert foreign.read_bytes().startswith(b"-- FOREIGN_008_MARKER\n")


def test_validate_excludes_test_ddl_from_the_fingerprint(tmp_path: Path) -> None:
    """Session DDL тестовой базы не становится версией отпечатка.

    Spec ``clickhouse-migration-lifecycle``, сценарий ``Test DDL is not
    canonical``. ``validate`` не берёт ``destructive_ch_reset`` и не
    использует шов переписывания ``default_db`` в ``test_adv_bot_clickhouse``.
    ``001``–``004`` остаются с ``default_db``.
    """
    corpus_dir = canonical_corpus_dir()
    for filename in _FILENAMES_IN_ORDER:
        shutil.copyfile(corpus_dir / filename, tmp_path / filename)
    decoy = tmp_path / "session_test_ddl.sql"
    decoy.write_text(
        "CREATE TABLE test_adv_bot_clickhouse.session_probe (id UInt8) "
        "ENGINE = Memory;\n",
        encoding="utf-8",
    )
    module_source = Path(validate.__code__.co_filename).read_text(encoding="utf-8")

    fingerprint = validate(corpus_dir=tmp_path)

    names = {version.filename for version in fingerprint.versions}
    assert names == set(_FILENAMES_IN_ORDER)
    assert decoy.name not in names
    assert _DESTRUCTIVE_CH_RESET.name not in names
    assert _REWRITE_SEAM.name not in names
    assert "rewrite_default_db_ch_client" not in module_source
    assert "destructive_ch_reset" not in module_source
    assert "get_clickhouse_client" not in module_source
    assert "test_adv_bot_clickhouse" not in module_source
    for version in fingerprint.versions:
        if version.id == "005":
            continue
        text = (tmp_path / version.filename).read_text(encoding="utf-8")
        assert "default_db." in text
        assert "test_adv_bot_clickhouse" not in text
    assert _DESTRUCTIVE_CH_RESET.is_file()
    assert "test_adv_bot_clickhouse" in _DESTRUCTIVE_CH_RESET.read_text(
        encoding="utf-8"
    )
