"""Отказ validate, plan и apply до execute.

Spec ``clickhouse-migration-lifecycle``, задачи 4.1 и 4.2. Проверяется
реальный разбор, сравнение с записанным отпечатком и отказ команд.
Порт и координатор — швы после этой границы: тест считает вход в них.
EVIDENCE_CLASS=side_effect_proof. PROVES: PA_SIDE_EFFECT_PROOF.
Живой сокет, учётные данные и запись applied не используются.
"""

from __future__ import annotations

import hashlib
import socket
from pathlib import Path

import pytest

from scripts.clickhouse_migration_control_plane.coordinator_session import (
    RecordingCoordinatorSession,
)
from scripts.clickhouse_migration_control_plane.corpus import (
    CorpusFingerprint,
    CorpusVersionIdentity,
    canonical_corpus_dir,
    immutable_fingerprint,
    validate as accept_corpus,
)
from scripts.clickhouse_migration_control_plane.pre_execution import (
    CommandResult,
    apply,
    plan,
    validate,
)
from scripts.clickhouse_migration_control_plane.statements import (
    StatementParseError,
    split_statements,
)
from scripts.clickhouse_migration_control_plane.target_port import (
    ExecSqlRequest,
    InspectMetadata,
    LedgerEvent,
    RecordingIsolatedTargetPort,
)
from tests.unit.clickhouse_migration_contract_fixture import (
    CANONICAL_DATABASE,
    SERVER_UUID,
    make_coordinator,
)

pytestmark = pytest.mark.unit

_FILENAMES: tuple[str, ...] = (
    "001_create_incremental_tables.sql",
    "002_add_event_date_event_id_to_fact_stat_states.sql",
    "003_add_buyouts_sum_rub_to_wb_common_stat.sql",
    "004_create_auto_shelf_bid_increment_tables.sql",
    "005_grant_system_log_truncate_to_adv_bot_user.sql",
    "006_create_campaign_settings_history.sql",
    "007_create_shop_campaign_inventory_and_availability.sql",
)
_VERSION_003 = "003_add_buyouts_sum_rub_to_wb_common_stat.sql"
_VERSION_001 = "001_create_incremental_tables.sql"
_VERSION_005 = "005_grant_system_log_truncate_to_adv_bot_user.sql"


class CountingIsolatedTargetPort(RecordingIsolatedTargetPort):
    """Порт, который считает вход в writer до собственного отказа.

    Spec ``clickhouse-migration-lifecycle``: ``executed == ()`` после
    ``refuse_exec_sql`` не доказывает, что команда не вызывала шов.
    Счётчик растёт в начале метода, раньше решения родителя.
    """

    def __init__(self) -> None:
        super().__init__(
            server_uuid_raw=SERVER_UUID,
            session_database=CANONICAL_DATABASE,
            inspect_metadata=InspectMetadata(
                target_id=SERVER_UUID,
                database=CANONICAL_DATABASE,
                object_names=("default_db.wb_common_stat_incremental",),
            ),
        )
        self.exec_calls: list[ExecSqlRequest] = []
        self.ledger_calls: list[LedgerEvent] = []

    def exec_sql(self, request: ExecSqlRequest) -> None:
        """Запомнить statement и только затем отдать его родителю."""
        self.exec_calls.append(request)
        super().exec_sql(request)

    def ledger_append(self, event: LedgerEvent) -> None:
        """Запомнить append и только затем отдать его родителю."""
        self.ledger_calls.append(event)
        super().ledger_append(event)


def _sha256_raw(payload: bytes) -> str:
    """SHA-256 сырых байт, включая комментарии и перевод строки."""
    return hashlib.sha256(payload).hexdigest()


def _copy_corpus(tmp_path: Path) -> Path:
    """Копия пяти канонических файлов. Каталог репозитория не меняется."""
    dest = tmp_path / "corpus"
    dest.mkdir()
    source = canonical_corpus_dir()
    for filename in _FILENAMES:
        target = dest / filename
        target.write_bytes((source / filename).read_bytes())
    return dest


def _snapshot(corpus_dir: Path) -> dict[str, bytes]:
    """Сырые байты файлов каталога до команды."""
    return {
        path.name: path.read_bytes()
        for path in corpus_dir.iterdir()
        if path.is_file()
    }


def _forbid_new_socket(monkeypatch: pytest.MonkeyPatch) -> None:
    """Сторож сокета: у команд нет клиента, более узкий шов не подставить."""

    def _boom(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("команда открыла сокет")

    monkeypatch.setattr(socket, "socket", _boom)
    monkeypatch.setattr(socket, "create_connection", _boom)


def _run(
    corpus_dir: Path,
    recorded: CorpusFingerprint,
) -> tuple[
    tuple[CommandResult, CountingIsolatedTargetPort, RecordingCoordinatorSession],
    ...,
]:
    """Прогнать validate, plan и apply на отдельных закрытых швах."""
    outcomes: list[
        tuple[CommandResult, CountingIsolatedTargetPort, RecordingCoordinatorSession]
    ] = []
    for command in (validate, plan, apply):
        port = CountingIsolatedTargetPort()
        coordinator = make_coordinator()
        result = command(
            corpus_dir,
            recorded,
            port=port,
            coordinator=coordinator,
        )
        outcomes.append((result, port, coordinator))
    return tuple(outcomes)


def _assert_closed(
    port: CountingIsolatedTargetPort,
    coordinator: RecordingCoordinatorSession,
) -> None:
    """Writer и координатор не открыты этим прогоном.

    Доказательство — пустой вход в ``exec_sql`` и ``ledger_append``, а не
    только пустой список успешно принятых statement.
    """
    assert port.exec_calls == []
    assert port.ledger_calls == []
    assert port.executed == ()
    assert "EXEC_SQL" not in port.operations
    assert "LEDGER_APPEND" not in port.operations
    assert coordinator.calls == ()
    assert coordinator.statements_sent == ()
    assert coordinator.held is False


def test_raw_bytes_drift_blocks_validate_plan_and_apply(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Комментарий в сырых байтах расходится с отпечатком и не исполняется.

    Spec ``clickhouse-migration-lifecycle``, сценарий ``Raw bytes no longer
    match the fingerprint``. Хвост ``--`` входит в SHA-256. Повторный apply
    снова неуспешен и снова не входит в writer и координатор.
    PROVES: PA_SIDE_EFFECT_PROOF.
    """
    canonical = canonical_corpus_dir()
    canonical_before = _snapshot(canonical)
    corpus_dir = _copy_corpus(tmp_path)
    recorded = immutable_fingerprint()
    original = (corpus_dir / _VERSION_001).read_bytes()
    assert recorded.versions[0].sha256 == _sha256_raw(original)
    drifted = original + b"\n-- drift-comment\n"
    (corpus_dir / _VERSION_001).write_bytes(drifted)
    assert _sha256_raw(drifted) != recorded.versions[0].sha256
    _forbid_new_socket(monkeypatch)

    outcomes = _run(corpus_dir, recorded)
    second_port = CountingIsolatedTargetPort()
    second_coordinator = make_coordinator()
    again = apply(
        corpus_dir,
        recorded,
        port=second_port,
        coordinator=second_coordinator,
    )

    for result, port, coordinator in outcomes:
        assert result.success is False
        assert result.code == "corpus_drift"
        assert result.parsed_statements == ()
        _assert_closed(port, coordinator)
    assert again.success is False
    assert again.code == "corpus_drift"
    _assert_closed(second_port, second_coordinator)
    assert _snapshot(canonical) == canonical_before
    assert (corpus_dir / _VERSION_001).read_bytes() == drifted


def test_privilege_class_substitution_blocks_005_before_writer() -> None:
    """Метка schema DDL на тексте ``005`` не доходит до writer.

    Spec ``clickhouse-migration-lifecycle``, сценарий ``Privilege class
    cannot be substituted``. Класс из текста остаётся ``privileged_grant``.
    Расхождение метки с текстом — ``corpus_drift``. PROVES:
    PA_SIDE_EFFECT_PROOF.
    """
    corpus_dir = canonical_corpus_dir()
    before = _snapshot(corpus_dir)
    accepted = accept_corpus(corpus_dir)
    grant = next(version for version in accepted.versions if version.id == "005")
    assert grant.privilege_class == "privileged_grant"
    substituted = CorpusFingerprint(
        versions=tuple(
            CorpusVersionIdentity(
                id=version.id,
                filename=version.filename,
                privilege_class=(
                    "schema_ddl" if version.id == "005" else version.privilege_class
                ),
                sha256=version.sha256,
            )
            for version in immutable_fingerprint().versions
        )
    )
    grant_text = (corpus_dir / _VERSION_005).read_text(encoding="utf-8")
    assert "GRANT TRUNCATE ON system." in grant_text

    outcomes = _run(corpus_dir, substituted)

    for result, port, coordinator in outcomes:
        assert result.success is False
        assert result.code == "corpus_drift"
        assert result.parsed_statements == ()
        _assert_closed(port, coordinator)
        assert all("GRANT" not in request.sql for request in port.exec_calls)
    assert _snapshot(corpus_dir) == before
    assert accept_corpus(corpus_dir).versions[4].privilege_class == (
        "privileged_grant"
    )


def test_semicolon_inside_string_fails_validate_before_apply(
    tmp_path: Path,
) -> None:
    """``;`` внутри кавычек валит validate, apply не начинает statement.

    Spec ``clickhouse-migration-lifecycle``, сценарий ``A semicolon inside
    a string stops before apply``. Предыдущий целый ``ALTER`` тоже не
    уходит в writer. PROVES: PA_SIDE_EFFECT_PROOF.
    """
    canonical = canonical_corpus_dir()
    canonical_before = _snapshot(canonical)
    corpus_dir = _copy_corpus(tmp_path)
    path = corpus_dir / _VERSION_003
    path.write_bytes(path.read_bytes() + b"\nSELECT 'before;after';\n")
    recorded = immutable_fingerprint()

    outcomes = _run(corpus_dir, recorded)

    for result, port, coordinator in outcomes:
        assert result.success is False
        assert result.code == "semicolon_in_string"
        assert result.parsed_statements == ()
        _assert_closed(port, coordinator)
        assert all("ALTER TABLE" not in request.sql for request in port.exec_calls)
    assert _snapshot(canonical) == canonical_before


def test_unreviewed_008_blocks_apply(tmp_path: Path) -> None:
    """Непроверенный successor в каталоге чтения блокирует apply.

    Spec ``clickhouse-migration-lifecycle``, сценарий ``Unreviewed numeric
    prefix blocks apply``. Отпечаток ``001``–``007`` не включает ``008``.
    Команда не принимает его молча и не исполняет.
    PROVES: PA_SIDE_EFFECT_PROOF.
    """
    canonical = canonical_corpus_dir()
    canonical_before = _snapshot(canonical)
    corpus_dir = _copy_corpus(tmp_path)
    foreign_name = "008_unreviewed.sql"
    foreign_sql = (
        b"CREATE TABLE default_db.should_not_run (id UInt8) ENGINE = Memory;\n"
    )
    foreign = corpus_dir / foreign_name
    foreign.write_bytes(foreign_sql)
    recorded = immutable_fingerprint()
    accepted = accept_corpus(corpus_dir)

    outcomes = _run(corpus_dir, recorded)

    assert tuple(version.id for version in accepted.versions) == (
        "001",
        "002",
        "003",
        "004",
        "005",
        "006",
        "007",
    )
    assert all(version.filename != foreign_name for version in accepted.versions)
    for result, port, coordinator in outcomes:
        assert result.success is False
        assert result.code == "unreviewed_version"
        assert result.parsed_statements == ()
        _assert_closed(port, coordinator)
        assert all(
            "should_not_run" not in request.sql for request in port.exec_calls
        )
    assert foreign.read_bytes() == foreign_sql
    assert _snapshot(canonical) == canonical_before


def test_matching_fingerprint_parses_without_opening_mutation() -> None:
    """Совпавший отпечаток не открывает мутацию и не переписывает файлы.

    Парная ветка отказов среза 4: validate цельного корпуса успешен,
    plan и apply остаются до execute. Класс ``005`` не становится
    schema DDL. PROVES: PA_SIDE_EFFECT_PROOF.
    """
    corpus_dir = canonical_corpus_dir()
    before = _snapshot(corpus_dir)
    recorded = immutable_fingerprint()
    assert accept_corpus(corpus_dir) == recorded

    outcomes = _run(corpus_dir, recorded)
    validated, planned, applied = outcomes

    assert validated[0].success is True
    assert validated[0].code == "ok"
    assert validated[0].parsed_statements != ()
    assert any(
        statement.startswith("GRANT TRUNCATE ON system.")
        for statement in validated[0].parsed_statements
    )
    assert all(
        "default_db." in (corpus_dir / filename).read_text(encoding="utf-8")
        for filename in _FILENAMES[:4]
    )
    for result, _port, _coordinator in (planned, applied):
        assert result.success is False
        assert result.code == "mutation_not_opened"
        assert result.parsed_statements == ()
    for _result, port, coordinator in outcomes:
        _assert_closed(port, coordinator)
        assert all("GRANT" not in request.sql for request in port.exec_calls)
    assert _snapshot(corpus_dir) == before


def test_full_line_recreate_comment_is_not_a_statement() -> None:
    """Полнострочный комментарий о пересоздании не становится statement.

    Spec ``clickhouse-migration-lifecycle``: срез 4 снимает такие строки
    до исполнения. Отправка комментария в writer закрывается срезом 10;
    здесь нарезка и отказ apply не содержат ``DROP VIEW``.
    """
    text = (canonical_corpus_dir() / _VERSION_001).read_text(encoding="utf-8")
    assert "-- DROP VIEW default_db.wb_common_stat_hourly_mv;" in text
    assert "пересоздайте" in text

    statements = split_statements(text)

    joined = "\n".join(statements)
    assert "DROP VIEW" not in joined
    assert "пересоздайте" not in joined
    assert all(
        not line.lstrip().startswith("--")
        for statement in statements
        for line in statement.splitlines()
    )
    assert any("default_db.wb_common_stat_incremental" in item for item in statements)
    outcomes = _run(canonical_corpus_dir(), immutable_fingerprint())
    for _result, port, coordinator in outcomes:
        _assert_closed(port, coordinator)


def test_split_treats_escaped_quote_and_rejects_semicolon_in_string() -> None:
    """``''`` не прячет внешнюю ``;``, а ``;`` внутри кавычек валит разбор.

    Парная ветка сканера: обычный литерал режется как один statement,
    литерал с точкой с запятой не возвращает statement наружу.
    """
    escaped = split_statements("SELECT 'it''s fine';\n")
    assert escaped == ("SELECT 'it''s fine';",)

    with pytest.raises(StatementParseError) as refused:
        _ = split_statements("SELECT 'before;after';\n")

    assert refused.value.code == "semicolon_in_string"
