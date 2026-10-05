"""Мутирующий lifecycle control plane ClickHouse на изолированных швах.

Spec ``clickhouse-migration-lifecycle``, срезы 7–14. Тесты выполняют
реальные команды пакета на RecordingIsolatedTargetPort и
RecordingCoordinatorSession без живой сети и production credentials.
EVIDENCE_CLASS=side_effect_proof. PROVES: PA_SIDE_EFFECT_PROOF.
"""

from __future__ import annotations

import socket
from pathlib import Path
from typing import NotRequired, TypedDict

import pytest

from scripts.clickhouse_migration_control_plane.corpus import (
    CorpusFingerprint,
    canonical_corpus_dir,
    immutable_fingerprint,
)
from scripts.clickhouse_migration_control_plane.mutations import (
    InspectionEvidence,
    apply_migrations,
    ensure_ledger,
    mark_applied,
    reconcile,
)
from scripts.clickhouse_migration_control_plane.statements import split_statements
from scripts.clickhouse_migration_control_plane.target_port import (
    ExecSqlRequest,
    LedgerEvent,
    RecordingIsolatedTargetPort,
)
from tests.unit.clickhouse_migration_contract_fixture import (
    CANONICAL_DATABASE,
    SERVER_UUID,
    make_coordinator,
    make_target_port,
)

pytestmark = pytest.mark.unit

_DSN = "postgresql://migration-control@isolated/coordinator"
_CREATED_AT = "2026-09-29T08:00:00+00:00"
_RUNNER = "runner-test-1"


class _MutationKwargs(TypedDict):
    """Типизированные явные входы mutating command из spec lifecycle."""

    target_class: str
    target_configured: bool
    coordinator_dsn: str | None
    runner_nonce: str
    created_at: str
    coordinator_kind: NotRequired[str]
    operator_wait: NotRequired[bool]


def _mutating_kwargs() -> _MutationKwargs:
    """Вернуть isolated-конфиг без application fallback."""
    return {
        "target_class": "isolated",
        "target_configured": True,
        "coordinator_dsn": _DSN,
        "runner_nonce": _RUNNER,
        "created_at": _CREATED_AT,
    }


def _evidence(
    port: RecordingIsolatedTargetPort,
    **overrides: str,
) -> InspectionEvidence:
    """Полная sanctioned baseline из реального результата inspect шва."""
    states = {version.id: "applied" for version in immutable_fingerprint().versions}
    states.update(overrides)
    return InspectionEvidence.create(
        inspection=port.inspect_read(),
        version_states=tuple(states.items()),
    )


def _prepare_baseline(
    *,
    states: dict[str, str] | None = None,
) -> tuple[Path, CorpusFingerprint, RecordingIsolatedTargetPort]:
    """Создать ledger и sanctioned baseline без исполнения corpus SQL."""
    corpus = canonical_corpus_dir()
    recorded = immutable_fingerprint()
    port = make_target_port()
    first = ensure_ledger(
        corpus,
        recorded,
        port=port,
        coordinator=make_coordinator(),
        authorize_ensure_ledger=True,
        **_mutating_kwargs(),
    )
    assert first.success is True
    evidence = _evidence(port, **(states or {}))
    second = reconcile(
        corpus,
        recorded,
        port=port,
        coordinator=make_coordinator(),
        evidence=evidence,
        authorize_reconcile=True,
        **_mutating_kwargs(),
    )
    assert second.success is True
    return corpus, recorded, port


def test_authorized_ensure_ledger_holds_advisory_lock_and_leaves_unknown() -> None:
    """Scenarios: Authorized ensure-ledger holds the advisory lock; Empty ledger does not apply the corpus."""
    corpus = canonical_corpus_dir()
    recorded = immutable_fingerprint()
    port = make_target_port()
    coordinator = make_coordinator()

    result = ensure_ledger(
        corpus,
        recorded,
        port=port,
        coordinator=coordinator,
        authorize_ensure_ledger=True,
        **_mutating_kwargs(),
    )

    assert result.success is True
    assert result.exit_code == 0
    assert result.code == "history_unresolved"
    assert port.ledger_created is True
    assert "ch_schema_migration_ledger" in port.ledger_ddl_text
    assert "fence" not in port.ledger_ddl_text.lower()
    assert port.executed == ()
    events = port.ledger_read(SERVER_UUID, CANONICAL_DATABASE).events
    assert [event.event_type for event in events] == ["history_unresolved"]
    assert all(event.event_type != "version_applied" for event in events)
    assert coordinator.calls[0].function == "pg_try_advisory_lock"
    assert coordinator.calls[-1].function == "pg_advisory_unlock"
    assert coordinator.held is False


@pytest.mark.parametrize(
    ("gate", "code"),
    [
        ("missing_coordinator", "blocked_missing_coordinator"),
        ("production", "blocked_production_target"),
        ("missing_target", "blocked_missing_target_config"),
    ],
)
def test_ensure_ledger_refuses_missing_mutation_gates(
    gate: str,
    code: str,
) -> None:
    """Scenarios: Missing coordinator fails closed; Production target without a separate GO refuses."""
    corpus = canonical_corpus_dir()
    port = make_target_port()
    coordinator = make_coordinator()
    args = _mutating_kwargs()
    if gate == "missing_coordinator":
        args["coordinator_dsn"] = None
    elif gate == "production":
        args["target_class"] = "production"
    else:
        args["target_configured"] = False

    result = ensure_ledger(
        corpus,
        immutable_fingerprint(),
        port=port,
        coordinator=coordinator,
        authorize_ensure_ledger=True,
        **args,
    )

    assert result.success is False
    assert result.code == code
    assert result.exit_code != 0
    assert port.ledger_created is False
    assert port.executed == ()
    assert coordinator.held is False


def test_unresolved_history_blocks_apply_and_mark_applied() -> None:
    """Scenarios: Unresolved history blocks apply and mark-applied; Catch-up cannot close unknown history."""
    corpus = canonical_corpus_dir()
    recorded = immutable_fingerprint()
    port = make_target_port()
    ensured = ensure_ledger(
        corpus,
        recorded,
        port=port,
        coordinator=make_coordinator(),
        authorize_ensure_ledger=True,
        **_mutating_kwargs(),
    )
    assert ensured.success is True

    applied = apply_migrations(
        corpus,
        recorded,
        port=port,
        coordinator=make_coordinator(),
        authorize_apply=True,
        version_ids=("001",),
        **_mutating_kwargs(),
    )
    marked = mark_applied(
        corpus,
        recorded,
        port=port,
        version_id="001",
    )

    assert applied.success is False
    assert applied.code == "history_unresolved"
    assert marked.success is False
    assert marked.code == "history_unresolved"
    assert port.executed == ()
    assert all(
        event.event_type != "version_applied"
        for event in port.ledger_read(SERVER_UUID, CANONICAL_DATABASE).events
    )


def test_reconcile_requires_own_flag_and_inspection_evidence() -> None:
    """Scenarios: Reconcile requires its own flag and inspection evidence; Reconcile without flag or evidence writes nothing."""
    corpus = canonical_corpus_dir()
    recorded = immutable_fingerprint()
    port = make_target_port()
    ensure_ledger(
        corpus,
        recorded,
        port=port,
        coordinator=make_coordinator(),
        authorize_ensure_ledger=True,
        **_mutating_kwargs(),
    )
    before = port.ledger_read(SERVER_UUID, CANONICAL_DATABASE).events

    no_flag = reconcile(
        corpus,
        recorded,
        port=port,
        coordinator=make_coordinator(),
        evidence=_evidence(port),
        authorize_reconcile=False,
        authorize_apply=True,
        **_mutating_kwargs(),
    )
    no_evidence = reconcile(
        corpus,
        recorded,
        port=port,
        coordinator=make_coordinator(),
        evidence=None,
        authorize_reconcile=True,
        **_mutating_kwargs(),
    )

    assert no_flag.success is False
    assert no_evidence.success is False
    assert port.ledger_read(SERVER_UUID, CANONICAL_DATABASE).events == before
    assert port.executed == ()


def test_reconcile_recomputes_inspection_evidence_sha256() -> None:
    """Reconcile не доверяет caller-provided evidence SHA без пересчёта."""
    corpus = canonical_corpus_dir()
    recorded = immutable_fingerprint()
    port = make_target_port()
    ensure_ledger(
        corpus,
        recorded,
        port=port,
        coordinator=make_coordinator(),
        authorize_ensure_ledger=True,
        **_mutating_kwargs(),
    )
    valid = _evidence(port)
    tampered = InspectionEvidence(
        inspection=valid.inspection,
        evidence_sha256="0" * 64,
        version_states=valid.version_states,
    )
    before = port.ledger_read(SERVER_UUID, CANONICAL_DATABASE).events
    coordinator = make_coordinator()

    result = reconcile(
        corpus,
        recorded,
        port=port,
        coordinator=coordinator,
        evidence=tampered,
        authorize_reconcile=True,
        **_mutating_kwargs(),
    )

    assert result.success is False
    assert result.code == "blocked_invalid_evidence"
    assert port.ledger_read(SERVER_UUID, CANONICAL_DATABASE).events == before
    assert coordinator.calls == ()


def test_filename_list_and_undetermined_evidence_do_not_apply_version() -> None:
    """Scenario: Filename list and undetermined evidence do not apply a version."""
    corpus = canonical_corpus_dir()
    recorded = immutable_fingerprint()
    port = make_target_port()
    ensure_ledger(
        corpus,
        recorded,
        port=port,
        coordinator=make_coordinator(),
        authorize_ensure_ledger=True,
        **_mutating_kwargs(),
    )

    filenames = reconcile(
        corpus,
        recorded,
        port=port,
        coordinator=make_coordinator(),
        evidence=("001.sql", "002.sql"),
        authorize_reconcile=True,
        **_mutating_kwargs(),
    )
    undetermined = reconcile(
        corpus,
        recorded,
        port=port,
        coordinator=make_coordinator(),
        evidence=_evidence(port, **{"003": "undetermined"}),
        authorize_reconcile=True,
        **_mutating_kwargs(),
    )

    assert filenames.success is False
    assert filenames.code == "blocked_invalid_evidence"
    assert undetermined.success is False
    assert undetermined.code == "history_unresolved"
    events = port.ledger_read(SERVER_UUID, CANONICAL_DATABASE).events
    assert all(
        not (event.version_id == "003" and event.event_type == "version_applied")
        for event in events
    )
    assert port.executed == ()


def test_reconcile_writes_baseline_without_executing_corpus() -> None:
    """Scenario: Reconcile requires its own flag and inspection evidence."""
    corpus = canonical_corpus_dir()
    recorded = immutable_fingerprint()
    port = make_target_port()
    ensure_ledger(
        corpus,
        recorded,
        port=port,
        coordinator=make_coordinator(),
        authorize_ensure_ledger=True,
        **_mutating_kwargs(),
    )

    result = reconcile(
        corpus,
        recorded,
        port=port,
        coordinator=make_coordinator(),
        evidence=_evidence(port, **{"001": "not_applied"}),
        authorize_reconcile=True,
        **_mutating_kwargs(),
    )

    assert result.success is True
    assert result.exit_code == 0
    assert port.executed == ()
    events = port.ledger_read(SERVER_UUID, CANONICAL_DATABASE).events
    assert any(event.event_type == "baseline_reconciled" for event in events)
    assert any(
        event.version_id == "001" and event.event_type == "baseline_not_applied"
        for event in events
    )
    assert not any(
        event.version_id == "001" and event.event_type == "version_applied"
        for event in events
    )


def test_schema_writer_runs_001_under_every_gate_statement_by_statement() -> None:
    """Scenarios: Schema writer may run only schema DDL under every gate; Statements commit one by one; Comments are not statements."""
    corpus, recorded, port = _prepare_baseline(states={"001": "not_applied"})
    coordinator = make_coordinator()
    expected = split_statements(
        (corpus / recorded.versions[0].filename).read_text(encoding="utf-8")
    )

    result = apply_migrations(
        corpus,
        recorded,
        port=port,
        coordinator=coordinator,
        authorize_apply=True,
        version_ids=("001",),
        **_mutating_kwargs(),
    )

    assert result.success is True
    assert result.exit_code == 0
    assert tuple(request.sql for request in port.executed) == expected
    assert all(not line.lstrip().startswith("--") for sql in expected for line in sql.splitlines())
    version_events = [
        event
        for event in port.ledger_read(SERVER_UUID, CANONICAL_DATABASE).events
        if event.version_id == "001"
    ]
    event_types = [event.event_type for event in version_events]
    assert event_types[-(len(expected) + 2)] == "apply_started"
    assert event_types[-1] == "version_applied"
    assert event_types.count("statement_ok") == len(expected)
    assert [event.statement_ordinal for event in version_events if event.event_type == "statement_ok"][-len(expected):] == list(range(1, len(expected) + 1))
    assert coordinator.calls[0].function == "pg_try_advisory_lock"
    assert coordinator.calls[-1].function == "pg_advisory_unlock"


def test_apply_without_authorization_refuses_before_statement() -> None:
    """Scenario: Apply without authorization refuses."""
    corpus, recorded, port = _prepare_baseline(states={"001": "not_applied"})
    coordinator = make_coordinator()

    result = apply_migrations(
        corpus,
        recorded,
        port=port,
        coordinator=coordinator,
        authorize_apply=False,
        version_ids=("001",),
        **_mutating_kwargs(),
    )

    assert result.success is False
    assert result.exit_code != 0
    assert port.executed == ()
    assert coordinator.calls == ()


def test_authorized_apply_still_refuses_005_before_schema_writer() -> None:
    """Scenario: Authorized apply still refuses 005."""
    corpus, recorded, port = _prepare_baseline(states={"005": "not_applied"})

    result = apply_migrations(
        corpus,
        recorded,
        port=port,
        coordinator=make_coordinator(),
        authorize_apply=True,
        version_ids=("005",),
        **_mutating_kwargs(),
    )

    assert result.success is False
    assert result.code == "blocked_privileged_grant"
    assert all(request.version_id != "005" for request in port.executed)
    assert all("GRANT" not in request.sql for request in port.executed)


def test_same_checksum_skips_sql_on_second_apply() -> None:
    """Scenario: Same checksum skips SQL."""
    corpus, recorded, port = _prepare_baseline(states={"001": "not_applied"})
    first = apply_migrations(
        corpus,
        recorded,
        port=port,
        coordinator=make_coordinator(),
        authorize_apply=True,
        version_ids=("001",),
        **_mutating_kwargs(),
    )
    executed = port.executed

    second = apply_migrations(
        corpus,
        recorded,
        port=port,
        coordinator=make_coordinator(),
        authorize_apply=True,
        version_ids=("001",),
        **_mutating_kwargs(),
    )

    assert first.success is True
    assert second.success is True
    assert second.code == "already_applied"
    assert port.executed == executed


@pytest.mark.parametrize("event_type", ["apply_started", "statement_ok", "partial", "applying"])
def test_partial_and_applying_are_not_idempotent_skips(event_type: str) -> None:
    """Scenario: Partial and applying are not idempotent skips."""
    corpus, recorded, port = _prepare_baseline(states={"001": "not_applied"})
    version = recorded.versions[0]
    previous = port.ledger_read(SERVER_UUID, CANONICAL_DATABASE).events
    seq = max((event.event_seq for event in previous if event.version_id == "001"), default=0)
    port.ledger_append(
        LedgerEvent(
            target_id=SERVER_UUID,
            database=CANONICAL_DATABASE,
            version_id="001",
            event_type=event_type,
            event_seq=seq + 1,
            sha256=version.sha256,
            privilege_class=version.privilege_class,
        )
    )
    before = port.executed

    result = apply_migrations(
        corpus,
        recorded,
        port=port,
        coordinator=make_coordinator(),
        authorize_apply=True,
        version_ids=("001",),
        **_mutating_kwargs(),
    )

    assert result.success is False
    assert result.code == "partial"
    assert port.executed == before


def test_lock_contention_sends_no_statement() -> None:
    """Scenario: Lock contention sends no statement."""
    corpus, recorded, port = _prepare_baseline(states={"001": "not_applied"})
    coordinator = make_coordinator(try_acquire_returns=False)

    result = apply_migrations(
        corpus,
        recorded,
        port=port,
        coordinator=coordinator,
        authorize_apply=True,
        version_ids=("001",),
        **_mutating_kwargs(),
    )

    assert result.success is False
    assert result.code == "blocked_lock_contention"
    assert port.executed == ()


def test_lock_loss_stops_further_sql_and_restart_does_not_resume(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Scenarios: Lock loss stops further SQL; Crash after a successful statement leaves the version unclosed; Restart does not continue a partial or unknown history."""
    corpus, recorded, port = _prepare_baseline(states={"001": "not_applied"})
    coordinator = make_coordinator()
    original_exec = port.exec_sql

    def _kill_after_first(request: ExecSqlRequest) -> None:
        original_exec(request)
        if len(port.executed) == 1:
            coordinator.mark_session_dead()

    monkeypatch.setattr(port, "exec_sql", _kill_after_first)

    first = apply_migrations(
        corpus,
        recorded,
        port=port,
        coordinator=coordinator,
        authorize_apply=True,
        version_ids=("001",),
        **_mutating_kwargs(),
    )
    sent = port.executed
    monkeypatch.setattr(port, "exec_sql", original_exec)
    second = apply_migrations(
        corpus,
        recorded,
        port=port,
        coordinator=make_coordinator(),
        authorize_apply=True,
        version_ids=("001",),
        **_mutating_kwargs(),
    )

    assert first.success is False
    assert first.code == "coordinator_session_lost"
    assert len(sent) == 1
    assert second.success is False
    assert second.code == "partial"
    assert port.executed == sent


@pytest.mark.parametrize(
    ("mutator", "expected"),
    [
        ("missing", "blocked_missing_coordinator"),
        ("wrong", "blocked_wrong_coordinator"),
        ("production", "blocked_production_target"),
    ],
)
def test_mutating_commands_fail_closed_on_coordinator_and_production(
    mutator: str,
    expected: str,
) -> None:
    """Scenarios: Missing coordinator fails closed; Wrong coordinator is not this lock; Production target without a separate GO refuses."""
    corpus, recorded, port = _prepare_baseline(states={"001": "not_applied"})
    kwargs = _mutating_kwargs()
    coordinator = make_coordinator()
    if mutator == "missing":
        kwargs["coordinator_dsn"] = None
    elif mutator == "wrong":
        kwargs["coordinator_kind"] = "application_database"
    else:
        kwargs["target_class"] = "production"

    result = apply_migrations(
        corpus,
        recorded,
        port=port,
        coordinator=coordinator,
        authorize_apply=True,
        version_ids=("001",),
        **kwargs,
    )

    assert result.success is False
    assert result.code == expected
    assert port.executed == ()
    assert coordinator.held is False


def test_all_mutating_commands_refuse_production_before_lock() -> None:
    """Scenario: Production target without a separate GO refuses."""
    corpus = canonical_corpus_dir()
    recorded = immutable_fingerprint()
    port = make_target_port()
    evidence = _evidence(port)
    coordinators = [make_coordinator(), make_coordinator(), make_coordinator()]
    production = _mutating_kwargs()
    production["target_class"] = "production"

    results = (
        ensure_ledger(
            corpus,
            recorded,
            port=port,
            coordinator=coordinators[0],
            authorize_ensure_ledger=True,
            **production,
        ),
        reconcile(
            corpus,
            recorded,
            port=port,
            coordinator=coordinators[1],
            evidence=evidence,
            authorize_reconcile=True,
            **production,
        ),
        apply_migrations(
            corpus,
            recorded,
            port=port,
            coordinator=coordinators[2],
            authorize_apply=True,
            version_ids=("001",),
            **production,
        ),
    )

    assert [result.code for result in results] == [
        "blocked_production_target",
        "blocked_production_target",
        "blocked_production_target",
    ]
    assert all(result.success is False for result in results)
    assert all(coordinator.calls == () for coordinator in coordinators)
    assert "ENSURE_LEDGER" not in port.operations
    assert "LEDGER_APPEND" not in port.operations
    assert "EXEC_SQL" not in port.operations


def test_all_mutating_commands_refuse_missing_coordinator_before_target_write() -> None:
    """Scenario: Missing coordinator fails closed."""
    corpus = canonical_corpus_dir()
    recorded = immutable_fingerprint()
    port = make_target_port()
    evidence = _evidence(port)
    coordinators = [make_coordinator(), make_coordinator(), make_coordinator()]
    missing = _mutating_kwargs()
    missing["coordinator_dsn"] = None

    results = (
        ensure_ledger(
            corpus,
            recorded,
            port=port,
            coordinator=coordinators[0],
            authorize_ensure_ledger=True,
            **missing,
        ),
        reconcile(
            corpus,
            recorded,
            port=port,
            coordinator=coordinators[1],
            evidence=evidence,
            authorize_reconcile=True,
            **missing,
        ),
        apply_migrations(
            corpus,
            recorded,
            port=port,
            coordinator=coordinators[2],
            authorize_apply=True,
            version_ids=("001",),
            **missing,
        ),
    )

    assert [result.code for result in results] == [
        "blocked_missing_coordinator",
        "blocked_missing_coordinator",
        "blocked_missing_coordinator",
    ]
    assert all(result.success is False for result in results)
    assert all(coordinator.calls == () for coordinator in coordinators)
    assert "ENSURE_LEDGER" not in port.operations
    assert "LEDGER_APPEND" not in port.operations
    assert "EXEC_SQL" not in port.operations


def test_isolated_apply_is_real_and_production_socket_is_untouched(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Scenarios: Isolated apply is real and production is untouched; The application client is not the migration executor."""

    def _boom(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("live socket forbidden")

    monkeypatch.setattr(socket, "socket", _boom)
    monkeypatch.setattr(socket, "create_connection", _boom)
    corpus, recorded, port = _prepare_baseline(states={"003": "not_applied"})

    result = apply_migrations(
        corpus,
        recorded,
        port=port,
        coordinator=make_coordinator(),
        authorize_apply=True,
        version_ids=("003",),
        **_mutating_kwargs(),
    )

    assert result.success is True
    assert result.exit_code == 0
    assert any(request.version_id == "003" for request in port.executed)
