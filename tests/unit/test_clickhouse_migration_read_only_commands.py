"""Команды status, plan, inspect и validate не пишут журнал.

Spec ``clickhouse-migration-lifecycle``, задачи 5.1 и 5.2. Проверяются
реальные команды пакета. Порт и координатор — швы после границы записи:
тест считает вход в ``exec_sql``, append и захват lock.
EVIDENCE_CLASS=side_effect_proof. PROVES: PA_SIDE_EFFECT_PROOF.
Живой сокет, учётные данные и запись ``version_applied`` не используются.
"""

from __future__ import annotations

import socket
from pathlib import Path

import pytest

from scripts.clickhouse_migration_control_plane.coordinator_session import (
    RecordingCoordinatorSession,
)
from scripts.clickhouse_migration_control_plane.corpus import (
    CorpusFingerprint,
    canonical_corpus_dir,
    immutable_fingerprint,
)
from scripts.clickhouse_migration_control_plane.pre_execution import (
    CommandResult,
    inspect,
    plan,
    status,
    validate,
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

_VERSION_IDS = ("001", "002", "003", "004", "005", "006", "007")
_INSPECT_READS = ("system.tables", "system.columns", "SHOW CREATE")


class CountingIsolatedTargetPort(RecordingIsolatedTargetPort):
    """Порт, который считает вход в writer раньше решения родителя.

    Spec ``clickhouse-migration-lifecycle``: пустой ``executed`` после
    отказа порта не доказывает, что команда не вызывала шов.
    """

    def __init__(self) -> None:
        super().__init__(
            server_uuid_raw=SERVER_UUID,
            session_database=CANONICAL_DATABASE,
            inspect_metadata=InspectMetadata(
                target_id=SERVER_UUID,
                database=CANONICAL_DATABASE,
                object_names=("default_db.wb_common_stat_incremental",),
                catalog_reads=_INSPECT_READS,
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


def _forbid_new_socket(monkeypatch: pytest.MonkeyPatch) -> None:
    """Сторож сокета: у команд нет клиента, более узкий шов не подставить."""

    def _boom(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("команда открыла сокет")

    monkeypatch.setattr(socket, "socket", _boom)
    monkeypatch.setattr(socket, "create_connection", _boom)


def _assert_writer_closed(
    port: CountingIsolatedTargetPort,
    coordinator: RecordingCoordinatorSession,
    *,
    appends_before: int,
) -> None:
    """Writer и координатор не открыты этим прогоном.

    Доказательство — нет нового ``exec_sql`` и ``ledger_append`` и нет
    вызова advisory lock. Чтение журнала этим запретом не закрыто.
    """
    assert port.exec_calls == []
    assert len(port.ledger_calls) == appends_before
    assert "EXEC_SQL" not in port.operations
    assert port.operations.count("LEDGER_APPEND") == appends_before
    assert coordinator.calls == ()
    assert coordinator.statements_sent == ()
    assert coordinator.held is False


def _copy_corpus(tmp_path: Path) -> Path:
    """Копия пяти канонических файлов. Каталог репозитория не меняется."""
    dest = tmp_path / "corpus"
    dest.mkdir()
    source = canonical_corpus_dir()
    for version in immutable_fingerprint().versions:
        target = dest / version.filename
        target.write_bytes((source / version.filename).read_bytes())
    return dest


def _seed(port: CountingIsolatedTargetPort, event: LedgerEvent) -> None:
    """Подготовить журнал до команды. Сама команда этот append не делает."""
    port.ledger_append(event)


def test_status_without_target_is_not_an_applied_record(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Без цели status печатает ``target_not_attached`` и не пишет applied.

    Spec ``clickhouse-migration-lifecycle``, сценарий ``Status without a
    target is not an applied record``. Координатор не открывается. Повтор
    команды тоже не создаёт запись. PROVES: PA_SIDE_EFFECT_PROOF.
    """
    corpus_dir = canonical_corpus_dir()
    recorded = immutable_fingerprint()
    coordinator = make_coordinator()
    _forbid_new_socket(monkeypatch)

    result = status(
        corpus_dir,
        recorded,
        port=None,
        coordinator=coordinator,
    )
    again = status(
        corpus_dir,
        recorded,
        port=None,
        coordinator=coordinator,
    )

    assert result.success is True
    assert result.exit_code == 0
    assert result.code == "target_not_attached"
    assert result.applied_version_ids == ()
    assert result.satisfies_reconcile is False
    assert tuple(item.state for item in result.version_reports) == (
        ("target_not_attached",) * len(_VERSION_IDS)
    )
    assert again.code == "target_not_attached"
    assert again.applied_version_ids == ()
    assert coordinator.calls == ()
    assert coordinator.held is False


def test_file_presence_is_not_applied_state(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Прикреплённая цель отвечает из журнала, не из файлов и не из DDL.

    Spec ``clickhouse-migration-lifecycle``, сценарий ``File presence is
    not applied state``. ``IF NOT EXISTS`` в ``001``–``004`` не становится
    ``version_applied``. Пустой журнал остаётся ``ledger_absent``.
    PROVES: PA_SIDE_EFFECT_PROOF.
    """
    corpus_dir = canonical_corpus_dir()
    recorded = immutable_fingerprint()
    sql_001 = (corpus_dir / recorded.versions[0].filename).read_text(
        encoding="utf-8"
    )
    assert "IF NOT EXISTS" in sql_001
    port = CountingIsolatedTargetPort()
    coordinator = make_coordinator()
    _forbid_new_socket(monkeypatch)

    result = status(
        corpus_dir,
        recorded,
        port=port,
        coordinator=coordinator,
    )
    again = status(
        corpus_dir,
        recorded,
        port=port,
        coordinator=coordinator,
    )

    assert result.success is True
    assert result.exit_code == 0
    assert result.code == "ledger_absent"
    assert result.applied_version_ids == ()
    assert "IF NOT EXISTS" not in result.code
    assert tuple(item.version_id for item in result.version_reports) == (
        _VERSION_IDS
    )
    assert tuple(item.state for item in result.version_reports) == (
        ("ledger_absent",) * len(_VERSION_IDS)
    )
    assert all("IF NOT EXISTS" not in item.state for item in result.version_reports)
    assert again.applied_version_ids == ()
    assert again.code == "ledger_absent"
    _assert_writer_closed(port, coordinator, appends_before=0)
    assert port.ledger_read(SERVER_UUID, CANONICAL_DATABASE).events == ()


def test_plan_is_dry_for_stop_reasons(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """План показывает версии и причину остановки и не исполняет SQL.

    Spec ``clickhouse-migration-lifecycle``, сценарий ``Plan is dry``.
    Ветки: нет цели, неизвестная история, ``005``, drift, ``partial``,
    прод-класс. Lock не берётся, журнал не пишется.
    PROVES: PA_SIDE_EFFECT_PROOF.
    """
    corpus_dir = canonical_corpus_dir()
    recorded = immutable_fingerprint()
    _forbid_new_socket(monkeypatch)

    missing_port_coordinator = make_coordinator()
    missing = plan(
        corpus_dir,
        recorded,
        port=None,
        coordinator=missing_port_coordinator,
    )
    _assert_plan_shape(missing, recorded)
    assert missing.success is True
    assert missing.exit_code == 0
    assert missing.code == "target_not_attached"
    assert missing_port_coordinator.calls == ()
    assert missing_port_coordinator.held is False

    unknown_port = CountingIsolatedTargetPort()
    unknown_coordinator = make_coordinator()
    _seed(
        unknown_port,
        LedgerEvent(
            target_id=SERVER_UUID,
            database=CANONICAL_DATABASE,
            version_id="001",
            event_type="history_unresolved",
            event_seq=1,
            sha256=recorded.versions[0].sha256,
        ),
    )
    unknown = plan(
        corpus_dir,
        recorded,
        port=unknown_port,
        coordinator=unknown_coordinator,
    )
    _assert_plan_shape(unknown, recorded)
    assert unknown.success is True
    assert unknown.exit_code == 0
    assert unknown.code == "history_unresolved"
    _assert_writer_closed(unknown_port, unknown_coordinator, appends_before=1)

    grant_port = CountingIsolatedTargetPort()
    grant_coordinator = make_coordinator()
    for ordinal, version in enumerate(recorded.versions[:4], start=1):
        _seed(
            grant_port,
            LedgerEvent(
                target_id=SERVER_UUID,
                database=CANONICAL_DATABASE,
                version_id=version.id,
                event_type="version_applied",
                event_seq=ordinal,
                sha256=version.sha256,
            ),
        )
    granted = plan(
        corpus_dir,
        recorded,
        port=grant_port,
        coordinator=grant_coordinator,
    )
    _assert_plan_shape(granted, recorded)
    assert granted.success is True
    assert granted.exit_code == 0
    assert granted.code == "blocked_privileged_grant"
    assert granted.planned_versions[4].privilege_class == "privileged_grant"
    assert any(
        "GRANT TRUNCATE ON system." in statement
        for statement in granted.planned_versions[4].statements
    )
    _assert_writer_closed(grant_port, grant_coordinator, appends_before=4)
    assert all("GRANT" not in request.sql for request in grant_port.exec_calls)

    drifted_dir = _copy_corpus(tmp_path)
    drifted_path = drifted_dir / recorded.versions[0].filename
    drifted_path.write_bytes(drifted_path.read_bytes() + b"\n-- drift-comment\n")
    drift_port = CountingIsolatedTargetPort()
    drift_coordinator = make_coordinator()
    drifted = plan(
        drifted_dir,
        recorded,
        port=drift_port,
        coordinator=drift_coordinator,
    )
    assert tuple(item.version_id for item in drifted.planned_versions) == (
        _VERSION_IDS
    )
    assert drifted.planned_versions[0].statements != ()
    assert drifted.planned_versions[0].sha256 != recorded.versions[0].sha256
    assert drifted.success is False
    assert drifted.exit_code != 0
    assert drifted.code == "corpus_drift"
    assert drifted.parsed_statements == ()
    _assert_writer_closed(drift_port, drift_coordinator, appends_before=0)

    partial_port = CountingIsolatedTargetPort()
    partial_coordinator = make_coordinator()
    _seed(
        partial_port,
        LedgerEvent(
            target_id=SERVER_UUID,
            database=CANONICAL_DATABASE,
            version_id="001",
            event_type="statement_ok",
            event_seq=1,
            sha256=recorded.versions[0].sha256,
        ),
    )
    partial = plan(
        corpus_dir,
        recorded,
        port=partial_port,
        coordinator=partial_coordinator,
    )
    _assert_plan_shape(partial, recorded)
    assert partial.success is True
    assert partial.exit_code == 0
    assert partial.code == "partial"
    _assert_writer_closed(partial_port, partial_coordinator, appends_before=1)

    production_port = CountingIsolatedTargetPort()
    production_coordinator = make_coordinator()
    production = plan(
        corpus_dir,
        recorded,
        port=production_port,
        coordinator=production_coordinator,
        target_class="production",
    )
    _assert_plan_shape(production, recorded)
    assert production.success is True
    assert production.exit_code == 0
    assert production.code == "blocked_production_target"
    assert production_port.operations == ()
    _assert_writer_closed(
        production_port,
        production_coordinator,
        appends_before=0,
    )


def test_inspect_does_not_write_and_does_not_baseline(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Inspect читает только каталоги подстановки и не становится сверкой.

    Spec ``clickhouse-migration-lifecycle``, сценарий ``Inspect does not
    write and does not baseline``. Без цели порт не открывается. Повтор
    осмотра тоже не пишет журнал и не берёт lock.
    PROVES: PA_SIDE_EFFECT_PROOF.
    """
    coordinator = make_coordinator()
    _forbid_new_socket(monkeypatch)

    detached = inspect(port=None, coordinator=coordinator)

    assert detached.success is True
    assert detached.exit_code == 0
    assert detached.code == "target_not_attached"
    assert detached.catalog_reads == ()
    assert detached.applied_version_ids == ()
    assert detached.satisfies_reconcile is False
    assert coordinator.calls == ()
    assert coordinator.held is False

    port = CountingIsolatedTargetPort()
    attached_coordinator = make_coordinator()
    attached = inspect(port=port, coordinator=attached_coordinator)
    repeated = inspect(port=port, coordinator=attached_coordinator)

    assert attached.success is True
    assert attached.exit_code == 0
    assert attached.catalog_reads == _INSPECT_READS
    assert attached.applied_version_ids == ()
    assert attached.satisfies_reconcile is False
    assert repeated.satisfies_reconcile is False
    assert repeated.applied_version_ids == ()
    assert port.operations == ("INSPECT_READ", "INSPECT_READ")
    _assert_writer_closed(port, attached_coordinator, appends_before=0)
    assert port.ledger_read(SERVER_UUID, CANONICAL_DATABASE).status == (
        "ledger_absent"
    )


def test_intact_validate_exits_zero_without_coordinator(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Цельный validate успешен и не открывает координатор.

    Spec ``clickhouse-migration-lifecycle``: код выхода ``0`` допустим для
    цельного корпуса. Порт writer не вызывается. PROVES: PA_SIDE_EFFECT_PROOF.
    """
    corpus_dir = canonical_corpus_dir()
    recorded = immutable_fingerprint()
    port = CountingIsolatedTargetPort()
    coordinator = make_coordinator()
    _forbid_new_socket(monkeypatch)

    result = validate(
        corpus_dir,
        recorded,
        port=port,
        coordinator=coordinator,
    )

    assert result.success is True
    assert result.exit_code == 0
    assert result.code == "ok"
    assert result.parsed_statements != ()
    _assert_writer_closed(port, coordinator, appends_before=0)
    assert port.operations == ()


def _assert_plan_shape(
    result: CommandResult,
    recorded: CorpusFingerprint,
) -> None:
    """Порядок версий, класс, SHA-256 и хотя бы один statement на файл."""
    planned = result.planned_versions
    versions = recorded.versions
    assert tuple(item.version_id for item in planned) == _VERSION_IDS
    assert tuple(item.privilege_class for item in planned) == tuple(
        version.privilege_class for version in versions
    )
    assert tuple(item.sha256 for item in planned) == tuple(
        version.sha256 for version in versions
    )
    assert all(item.statements for item in planned)
    assert result.parsed_statements == ()
