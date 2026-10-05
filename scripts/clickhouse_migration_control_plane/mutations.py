"""Мутирующий lifecycle миграций ClickHouse на изолированном target port.

Spec ``clickhouse-migration-lifecycle``: ensure-ledger, reconcile и apply
имеют разные санкции, используют один session advisory lock и fail closed.
Модуль не импортирует application ClickHouse client, Alembic или DATABASE_URL.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import Path

from scripts.clickhouse_migration_control_plane.coordinator_session import (
    CoordinatorRefusal,
    RecordingCoordinatorSession,
)
from scripts.clickhouse_migration_control_plane.corpus import CorpusFingerprint
from scripts.clickhouse_migration_control_plane.ledger import (
    LedgerRefusal,
    ledger_ddl,
    operator_state,
    record_version_event,
)
from scripts.clickhouse_migration_control_plane.pre_execution import (
    CommandResult,
    gate_corpus,
    latest_by_version,
    ledger_has_drift,
)
from scripts.clickhouse_migration_control_plane.statements import (
    StatementParseError,
    split_statements,
)
from scripts.clickhouse_migration_control_plane.target_port import (
    ExecSqlRefused,
    ExecSqlRequest,
    InspectMetadata,
    IsolatedTargetPort,
)

_BASELINE_VERSION_ID = "__baseline__"
_OPEN_EVENTS = frozenset({"apply_started", "statement_ok", "partial", "applying"})
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


@dataclass(frozen=True)
class InspectionEvidence:
    """Sanctioned reconcile evidence, structurally bound to inspect output.

    Spec ``clickhouse-migration-lifecycle``: evidence — результат inspect,
    а не список имён файлов. SHA-256 пересчитывается по canonical payload,
    поэтому caller не может закрыть baseline одной произвольной hex-строкой.
    """

    inspection: InspectMetadata
    evidence_sha256: str
    version_states: tuple[tuple[str, str], ...]

    @classmethod
    def create(
        cls,
        *,
        inspection: InspectMetadata,
        version_states: tuple[tuple[str, str], ...],
    ) -> InspectionEvidence:
        """Создать evidence с SHA-256 canonical inspection payload."""
        payload = _inspection_evidence_payload(inspection, version_states)
        return cls(
            inspection=inspection,
            evidence_sha256=hashlib.sha256(payload).hexdigest(),
            version_states=version_states,
        )

    def as_dict(self) -> dict[str, str]:
        """Вернуть states без изменения исходного immutable evidence."""
        return dict(self.version_states)


def ensure_ledger(
    corpus_dir: Path,
    recorded: CorpusFingerprint,
    *,
    port: IsolatedTargetPort,
    coordinator: RecordingCoordinatorSession,
    authorize_ensure_ledger: bool,
    target_class: str,
    target_configured: bool,
    coordinator_dsn: str | None,
    runner_nonce: str,
    created_at: str,
    coordinator_kind: str = "migration_control",
    operator_wait: bool = False,
) -> CommandResult:
    """Создать только migration ledger и оставить history unresolved.

    Spec ``clickhouse-migration-lifecycle``: ledger creation выполняется
    только на isolated target под собственным флагом и advisory lock.
    Historic versions не получают ``version_applied``.
    """
    blocked = gate_corpus(corpus_dir, recorded)
    if blocked is not None:
        return blocked
    preflight = _mutation_preflight(
        port=port,
        coordinator=coordinator,
        authorized=authorize_ensure_ledger,
        authorization_code="blocked_ensure_ledger_authorization",
        target_class=target_class,
        target_configured=target_configured,
        coordinator_dsn=coordinator_dsn,
        coordinator_kind=coordinator_kind,
    )
    if isinstance(preflight, CommandResult):
        return preflight
    target_id = preflight
    if not coordinator.acquire(operator_wait=operator_wait):
        return _failure("blocked_lock_contention")
    try:
        coordinator.require_held()
        if not port.ledger_exists():
            port.ensure_ledger(ledger_ddl())
        coordinator.require_held()
        latest = latest_by_version(
            port.ledger_read(target_id, "default_db").events
        )
        baseline = latest.get(_BASELINE_VERSION_ID)
        if baseline is None:
            _append_event(
                port,
                coordinator,
                version_id=_BASELINE_VERSION_ID,
                sha256=_baseline_digest(recorded),
                privilege_class="control_plane",
                event_type="history_unresolved",
                runner_nonce=runner_nonce,
                evidence_sha256="",
                created_at=created_at,
            )
            return _success("history_unresolved")
        if baseline.event_type == "history_unresolved":
            return _success("history_unresolved")
        return _success("ledger_exists")
    except (CoordinatorRefusal, LedgerRefusal, ExecSqlRefused) as exc:
        return _failure(exc.code)
    finally:
        coordinator.release()


def reconcile(
    corpus_dir: Path,
    recorded: CorpusFingerprint,
    *,
    port: IsolatedTargetPort,
    coordinator: RecordingCoordinatorSession,
    evidence: InspectionEvidence | object | None,
    authorize_reconcile: bool,
    target_class: str,
    target_configured: bool,
    coordinator_dsn: str | None,
    runner_nonce: str,
    created_at: str,
    authorize_apply: bool = False,
    coordinator_kind: str = "migration_control",
    operator_wait: bool = False,
) -> CommandResult:
    """Записать sanctioned baseline без исполнения corpus SQL.

    Spec ``clickhouse-migration-lifecycle``: apply flag не заменяет
    reconcile flag. Undetermined evidence не закрывает unknown history.
    """
    _ = authorize_apply
    blocked = gate_corpus(corpus_dir, recorded)
    if blocked is not None:
        return blocked
    if not authorize_reconcile:
        return _failure("blocked_reconcile_authorization")
    preflight = _mutation_preflight(
        port=port,
        coordinator=coordinator,
        authorized=True,
        authorization_code="blocked_reconcile_authorization",
        target_class=target_class,
        target_configured=target_configured,
        coordinator_dsn=coordinator_dsn,
        coordinator_kind=coordinator_kind,
    )
    if isinstance(preflight, CommandResult):
        return preflight
    target_id = preflight
    checked = _validate_evidence(
        recorded,
        evidence,
        target_id=target_id,
        database="default_db",
    )
    if isinstance(checked, CommandResult):
        return checked
    states = checked
    if any(state == "undetermined" for state in states.values()):
        return _failure("history_unresolved")
    assert isinstance(evidence, InspectionEvidence)
    if not coordinator.acquire(operator_wait=operator_wait):
        return _failure("blocked_lock_contention")
    try:
        coordinator.require_held()
        if not port.ledger_exists():
            return _failure("history_unresolved")
        latest = latest_by_version(
            port.ledger_read(target_id, "default_db").events
        )
        baseline = latest.get(_BASELINE_VERSION_ID)
        if baseline is None:
            return _failure("history_unresolved")
        for version in recorded.versions:
            event_type = (
                "version_applied"
                if states[version.id] == "applied"
                else "baseline_not_applied"
            )
            _append_event(
                port,
                coordinator,
                version_id=version.id,
                sha256=version.sha256,
                privilege_class=version.privilege_class,
                event_type=event_type,
                runner_nonce=runner_nonce,
                evidence_sha256=evidence.evidence_sha256,
                created_at=created_at,
            )
        _append_event(
            port,
            coordinator,
            version_id=_BASELINE_VERSION_ID,
            sha256=_baseline_digest(recorded),
            privilege_class="control_plane",
            event_type="baseline_reconciled",
            runner_nonce=runner_nonce,
            evidence_sha256=evidence.evidence_sha256,
            created_at=created_at,
        )
        return _success("reconciled")
    except (CoordinatorRefusal, LedgerRefusal, ExecSqlRefused) as exc:
        return _failure(exc.code)
    finally:
        coordinator.release()


def apply_migrations(
    corpus_dir: Path,
    recorded: CorpusFingerprint,
    *,
    port: IsolatedTargetPort,
    coordinator: RecordingCoordinatorSession,
    authorize_apply: bool,
    target_class: str,
    target_configured: bool,
    coordinator_dsn: str | None,
    runner_nonce: str,
    created_at: str,
    version_ids: tuple[str, ...] | None = None,
    coordinator_kind: str = "migration_control",
    operator_wait: bool = False,
) -> CommandResult:
    """Исполнить selected schema DDL 001–004 под всеми воротами.

    Spec ``clickhouse-migration-lifecycle``: unknown history, partial,
    production, missing/wrong coordinator и 005 останавливаются fail closed.
    Каждый statement получает audit boundary и файл не считается transaction.
    """
    blocked = gate_corpus(corpus_dir, recorded)
    if blocked is not None:
        return blocked
    if not authorize_apply:
        return _failure("mutation_not_opened")
    preflight = _mutation_preflight(
        port=port,
        coordinator=coordinator,
        authorized=True,
        authorization_code="mutation_not_opened",
        target_class=target_class,
        target_configured=target_configured,
        coordinator_dsn=coordinator_dsn,
        coordinator_kind=coordinator_kind,
    )
    if isinstance(preflight, CommandResult):
        return preflight
    target_id = preflight
    versions = {version.id: version for version in recorded.versions}
    selected = version_ids or tuple(versions)
    if any(version_id not in versions for version_id in selected):
        return _failure("unreviewed_version")
    if not coordinator.acquire(operator_wait=operator_wait):
        return _failure("blocked_lock_contention")
    executed_any = False
    skipped_any = False
    try:
        coordinator.require_held()
        if not port.ledger_exists():
            return _failure("history_unresolved")
        latest = latest_by_version(
            port.ledger_read(target_id, "default_db").events
        )
        if ledger_has_drift(recorded, latest):
            return _failure("drift")
        baseline = latest.get(_BASELINE_VERSION_ID)
        if baseline is None or baseline.event_type != "baseline_reconciled":
            return _failure("history_unresolved")
        for version_id in selected:
            version = versions[version_id]
            current = latest.get(version_id)
            state = operator_state(current, file_sha256=version.sha256)
            if state == "drift":
                return _failure("drift")
            if current is not None and current.event_type in _OPEN_EVENTS:
                return _failure("partial")
            if (
                current is not None
                and current.event_type == "version_applied"
                and current.sha256 == version.sha256
            ):
                skipped_any = True
                continue
            if version.privilege_class != "schema_ddl":
                return _failure("blocked_privileged_grant")
            if current is None or current.event_type != "baseline_not_applied":
                return _failure("history_unresolved")
            outcome = _apply_one_version(
                corpus_dir,
                version.id,
                version.filename,
                version.sha256,
                version.privilege_class,
                port=port,
                coordinator=coordinator,
                runner_nonce=runner_nonce,
                created_at=created_at,
            )
            if outcome is not None:
                return outcome
            executed_any = True
            latest = latest_by_version(
                port.ledger_read(target_id, "default_db").events
            )
        if executed_any:
            return _success("applied")
        if skipped_any:
            return _success("already_applied")
        return _success("nothing_to_apply")
    finally:
        coordinator.release()


def mark_applied(
    corpus_dir: Path,
    recorded: CorpusFingerprint,
    *,
    port: IsolatedTargetPort,
    version_id: str,
) -> CommandResult:
    """Не дать прямой mark-applied закрыть неизвестную историю.

    Spec ``clickhouse-migration-lifecycle``: sanctioned applied baseline
    создаёт только reconcile. Отдельного обходного writer здесь нет.
    """
    blocked = gate_corpus(corpus_dir, recorded)
    if blocked is not None:
        return blocked
    if not port.ledger_exists():
        return _failure("history_unresolved")
    identity = port.server_uuid()
    database = port.session_database()
    if not identity.accepted or identity.raw is None or not database.accepted:
        return _failure("history_unresolved")
    latest = latest_by_version(
        port.ledger_read(identity.raw, database.name).events
    )
    baseline = latest.get(_BASELINE_VERSION_ID)
    if baseline is None or baseline.event_type != "baseline_reconciled":
        return _failure("history_unresolved")
    if version_id not in {item.id for item in recorded.versions}:
        return _failure("unreviewed_version")
    return _failure("blocked_direct_mark_applied")


def _mutation_preflight(
    *,
    port: IsolatedTargetPort,
    coordinator: RecordingCoordinatorSession,
    authorized: bool,
    authorization_code: str,
    target_class: str,
    target_configured: bool,
    coordinator_dsn: str | None,
    coordinator_kind: str,
) -> str | CommandResult:
    """Проверить mutation gates до advisory lock и target statement."""
    if target_class == "production":
        return _failure("blocked_production_target")
    if target_class != "isolated" or not target_configured:
        return _failure("blocked_missing_target_config")
    if not authorized:
        return _failure(authorization_code)
    if coordinator_dsn is None or coordinator_dsn.strip() == "":
        return _failure("blocked_missing_coordinator")
    if coordinator_kind != "migration_control":
        return _failure("blocked_wrong_coordinator")
    identity = port.server_uuid()
    database = port.session_database()
    if not identity.accepted or identity.raw is None:
        return _failure("server_uuid_refused")
    if not database.accepted or database.name != "default_db":
        return _failure("database_not_corpus_target")
    if coordinator.server_uuid != identity.raw:
        return _failure("blocked_wrong_coordinator")
    return identity.raw


def _validate_evidence(
    recorded: CorpusFingerprint,
    evidence: InspectionEvidence | object | None,
    *,
    target_id: str,
    database: str,
) -> dict[str, str] | CommandResult:
    """Принять только complete inspect evidence с проверенным SHA-256."""
    if not isinstance(evidence, InspectionEvidence):
        return _failure("blocked_invalid_evidence")
    if evidence.inspection.target_id != target_id:
        return _failure("blocked_invalid_evidence")
    if evidence.inspection.database != database:
        return _failure("blocked_invalid_evidence")
    if _SHA256_RE.fullmatch(evidence.evidence_sha256) is None:
        return _failure("blocked_invalid_evidence")
    payload = _inspection_evidence_payload(
        evidence.inspection,
        evidence.version_states,
    )
    if hashlib.sha256(payload).hexdigest() != evidence.evidence_sha256:
        return _failure("blocked_invalid_evidence")
    states = evidence.as_dict()
    allowed = {"applied", "not_applied", "undetermined"}
    version_ids = {version.id for version in recorded.versions}
    if set(states) != version_ids:
        return _failure("history_unresolved")
    if any(value not in allowed for value in states.values()):
        return _failure("blocked_invalid_evidence")
    return states


def _inspection_evidence_payload(
    inspection: InspectMetadata,
    version_states: tuple[tuple[str, str], ...],
) -> bytes:
    """Canonical JSON bytes, чей SHA-256 хранится в reconcile events."""
    document = {
        "target_id": inspection.target_id,
        "database": inspection.database,
        "object_names": list(inspection.object_names),
        "catalog_reads": list(inspection.catalog_reads),
        "version_states": [list(item) for item in version_states],
    }
    return json.dumps(
        document,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def _apply_one_version(
    corpus_dir: Path,
    version_id: str,
    filename: str,
    sha256: str,
    privilege_class: str,
    *,
    port: IsolatedTargetPort,
    coordinator: RecordingCoordinatorSession,
    runner_nonce: str,
    created_at: str,
) -> CommandResult | None:
    """Исполнить один schema file без transaction/resume semantics."""
    try:
        statements = split_statements(
            (corpus_dir / filename).read_text(encoding="utf-8")
        )
    except StatementParseError as exc:
        return _failure(exc.code)
    try:
        coordinator.require_held()
        _append_event(
            port,
            coordinator,
            version_id=version_id,
            sha256=sha256,
            privilege_class=privilege_class,
            event_type="apply_started",
            runner_nonce=runner_nonce,
            evidence_sha256="",
            created_at=created_at,
            statement_count=len(statements),
        )
        for ordinal, sql in enumerate(statements, start=1):
            coordinator.require_held()
            coordinator.send_statement(
                port,
                ExecSqlRequest(
                    sql=sql,
                    version_id=version_id,
                    file_sha256=sha256,
                ),
            )
            coordinator.require_held()
            _append_event(
                port,
                coordinator,
                version_id=version_id,
                sha256=sha256,
                privilege_class=privilege_class,
                event_type="statement_ok",
                runner_nonce=runner_nonce,
                evidence_sha256="",
                created_at=created_at,
                statement_ordinal=ordinal,
                statement_count=len(statements),
            )
        coordinator.require_held()
        _append_event(
            port,
            coordinator,
            version_id=version_id,
            sha256=sha256,
            privilege_class=privilege_class,
            event_type="version_applied",
            runner_nonce=runner_nonce,
            evidence_sha256="",
            created_at=created_at,
            statement_ordinal=len(statements),
            statement_count=len(statements),
        )
    except (CoordinatorRefusal, LedgerRefusal, ExecSqlRefused) as exc:
        return _failure(exc.code)
    except Exception:
        return _failure("statement_failed")
    return None


def _append_event(
    port: IsolatedTargetPort,
    coordinator: RecordingCoordinatorSession,
    *,
    version_id: str,
    sha256: str,
    privilege_class: str,
    event_type: str,
    runner_nonce: str,
    evidence_sha256: str,
    created_at: str,
    statement_ordinal: int = 0,
    statement_count: int = 0,
) -> None:
    """Append event только пока coordinator session удерживает lock."""
    coordinator.require_held()
    _ = record_version_event(
        port,
        version_id=version_id,
        sha256=sha256,
        privilege_class=privilege_class,
        event_type=event_type,
        hostname="migration-control",
        statement_ordinal=statement_ordinal,
        statement_count=statement_count,
        runner_nonce=runner_nonce,
        evidence_sha256=evidence_sha256,
        created_at=created_at,
    )


def _baseline_digest(recorded: CorpusFingerprint) -> str:
    """Стабильный SHA-256 identity всего принятого corpus для baseline event."""
    payload = "\n".join(
        f"{version.id}:{version.sha256}:{version.privilege_class}"
        for version in recorded.versions
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _failure(code: str) -> CommandResult:
    """Единый честный non-zero refusal."""
    return CommandResult(success=False, code=code, exit_code=1)


def _success(code: str) -> CommandResult:
    """Единый terminal success mutating command."""
    return CommandResult(success=True, code=code, exit_code=0)
