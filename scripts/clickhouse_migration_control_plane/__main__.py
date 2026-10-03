"""CLI surface control plane миграций ClickHouse.

Spec ``clickhouse-migration-lifecycle``: пакет обязан запускаться через
``python -m scripts.clickhouse_migration_control_plane`` и иметь ``--help``.
Живой production adapter этим change намеренно не создаётся.
"""

from __future__ import annotations

import argparse
import json
from collections.abc import Sequence

from scripts.clickhouse_migration_control_plane.coordinator_session import (
    RecordingCoordinatorSession,
)
from scripts.clickhouse_migration_control_plane.corpus import (
    canonical_corpus_dir,
    immutable_fingerprint,
)
from scripts.clickhouse_migration_control_plane.pre_execution import (
    inspect,
    plan,
    status,
    validate,
)
from scripts.clickhouse_migration_control_plane.target_port import (
    InspectMetadata,
    RecordingIsolatedTargetPort,
)

_CLI_UUID = "018f0b3c-7a21-7c3e-8e11-9a0b1c2d3e4f"


def build_parser() -> argparse.ArgumentParser:
    """Собрать documented command surface без скрытого production fallback."""
    parser = argparse.ArgumentParser(
        prog="clickhouse-migration-control-plane",
        description="Fail-closed ClickHouse migration lifecycle control plane.",
    )
    subparsers = parser.add_subparsers(dest="command")
    for name in (
        "status",
        "validate",
        "plan",
        "inspect",
        "ensure-ledger",
        "reconcile",
        "apply",
    ):
        _ = subparsers.add_parser(name)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Выполнить только безопасные local/read-only CLI paths этого change.

    Mutating commands требуют injected isolated target/coordinator adapters;
    CLI не подменяет их application credentials или DATABASE_URL.
    """
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command is None:
        parser.print_help()
        return 0
    if args.command in {"ensure-ledger", "reconcile", "apply"}:
        return _print_result(False, "isolated_target_adapter_required", 1)
    coordinator = RecordingCoordinatorSession(
        server_uuid=_CLI_UUID,
        try_acquire_returns=True,
    )
    corpus = canonical_corpus_dir()
    recorded = immutable_fingerprint()
    if args.command == "validate":
        port = _local_port()
        result = validate(
            corpus,
            recorded,
            port=port,
            coordinator=coordinator,
        )
    elif args.command == "status":
        result = status(
            corpus,
            recorded,
            port=None,
            coordinator=coordinator,
        )
    elif args.command == "plan":
        result = plan(
            corpus,
            recorded,
            port=None,
            coordinator=coordinator,
        )
    else:
        result = inspect(port=None, coordinator=coordinator)
    return _print_result(result.success, result.code, result.exit_code)


def _local_port() -> RecordingIsolatedTargetPort:
    """Создать network-free port только для local validate dispatch."""
    return RecordingIsolatedTargetPort(
        server_uuid_raw=_CLI_UUID,
        session_database="default_db",
        inspect_metadata=InspectMetadata(
            target_id=_CLI_UUID,
            database="default_db",
            object_names=(),
        ),
    )


def _print_result(success: bool, code: str, exit_code: int) -> int:
    """Вывести machine-readable terminal result CLI."""
    print(json.dumps({"success": success, "code": code}, sort_keys=True))
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
