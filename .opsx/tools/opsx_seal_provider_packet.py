"""Seal INDEPENDENT_REAUDIT provider-run packet at current HEAD (untracked)."""

from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from pathlib import Path


def _load_guard():
    tools = Path(__file__).resolve().parent
    spec = importlib.util.spec_from_file_location(
        "opsx_provider_run_guard", tools / "opsx_provider_run_guard.py"
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


guard = _load_guard()


def _default_test_ids() -> list[str]:
    return [
        "tests/integration/wb_sky_mcp/test_mcp_pg_connection_repository.py::test_sql_connection_repository_persist_and_raw_select",
        "tests/integration/wb_sky_mcp/test_mcp_pg_connection_repository.py::test_sql_connection_repository_refresh_rotation_rejects_reuse",
        "tests/integration/wb_sky_mcp/test_mcp_pg_connection_repository.py::test_sql_connection_repository_contract_cases[persist_add_get_disconnect_version]",
        "tests/integration/wb_sky_mcp/test_mcp_pg_connection_repository.py::test_sql_connection_repository_contract_cases[refresh_rotation_rejects_reuse]",
        "tests/integration/wb_sky_mcp/test_mcp_pg_shop_grant_reader.py::test_sql_shop_grant_reader_lists_only_principal_cabinets",
        "tests/integration/wb_sky_mcp/test_mcp_pg_shop_grant_reader.py::test_sql_shop_grant_reader_empty_grant_is_success",
    ]


def build_packet(
    repo_root: Path,
    *,
    change_id: str,
    live_token: str,
    redis_port: int = 6379,
) -> dict[str, object]:
    """Build packet dict bound to current git HEAD and worktree fingerprints."""

    head = guard.compute_audited_head(repo_root)
    status = guard.compute_audited_status_sha256(repo_root)
    diff = guard.compute_audited_tracked_diff_sha256(repo_root)
    manifest = guard.compute_audited_untracked_manifest_sha256(repo_root)
    pytest_argv = [
        "poetry",
        "run",
        "pytest",
        "tests/integration/wb_sky_mcp/",
        "-m",
        "destructive_local",
        "-vv",
        "--tb=short",
    ]
    pytest_targets = list(guard.extract_pytest_targets_from_argv(tuple(pytest_argv)))
    block = (
        "set -euo pipefail\n"
        "cd \"$(git rev-parse --show-toplevel)\"\n"
        f"test \"$(git rev-parse HEAD)\" = \"{head}\"\n"
        "export POSTGRES_MASTER_HOST=127.0.0.1\n"
        "export POSTGRES_PORT=5433\n"
        "export POSTGRES_DBNAME=test_adv_bot_db\n"
        "export ALLOW_DESTRUCTIVE_TEST_DB=1\n"
        "export ALLOW_DESTRUCTIVE_TEST_CLICKHOUSE=1\n"
        "export REDIS_HOST=127.0.0.1\n"
        f"export REDIS_PORT={redis_port}\n"
        "export AUTHORIZE_ONE_LIVE_RUN=\"${AUTHORIZE_ONE_LIVE_RUN:?required}\"\n"
        "docker compose -f tests/docker-compose.test.yml up -d test_db test_clickhouse test_redis\n"
        "pg_isready -h 127.0.0.1 -p 5433 -U test_user -d test_adv_bot_db\n"
        "curl -fsS http://127.0.0.1:8124/ping >/dev/null\n"
        f"# PYTEST_TARGETS: {pytest_targets[0]}\n"
        "poetry run python .opsx/tools/opsx_provider_run_guard.py verify --packet "
        f".opsx/runs/scenario-coverage/{change_id}/provider-run-packet.json --repo .\n"
        "poetry run python .opsx/tools/opsx_provider_run_guard.py run --packet "
        f".opsx/runs/scenario-coverage/{change_id}/provider-run-packet.json --repo .\n"
        "docker compose -f tests/docker-compose.test.yml down\n"
    )
    return {
        "audited_head": head,
        "audited_status_sha256": status,
        "audited_tracked_diff_sha256": diff,
        "audited_untracked_manifest_sha256": manifest,
        "allowed_run_block_sha256": guard.allowed_run_block_sha256(block),
        "allowed_run_block_text": block,
        "pytest_argv": pytest_argv,
        "pytest_targets": pytest_targets,
        "provider_test_ids": _default_test_ids(),
        "postgres_host": "127.0.0.1",
        "postgres_port": 5433,
        "postgres_dbname": "test_adv_bot_db",
        "redis_host": "127.0.0.1",
        "redis_port": redis_port,
        "change_id": change_id,
        "one_shot_authorization_id": guard.one_shot_authorization_token_sha256(
            live_token
        ),
    }


def main(argv: list[str] | None = None) -> int:
    """CLI: write provider-run-packet.json under scenario-coverage run dir."""

    parser = argparse.ArgumentParser(description="Seal provider-run packet at HEAD")
    parser.add_argument("--repo", type=Path, default=Path.cwd())
    parser.add_argument("--change-id", default="wb-sky-mcp-read-interface")
    parser.add_argument(
        "--live-token",
        required=True,
        help="Value for AUTHORIZE_ONE_LIVE_RUN (hashed into packet)",
    )
    parser.add_argument("--redis-port", type=int, default=6379)
    args = parser.parse_args(argv)

    repo_root = args.repo.resolve()
    packet = build_packet(
        repo_root,
        change_id=args.change_id,
        live_token=args.live_token,
        redis_port=args.redis_port,
    )
    out = (
        repo_root
        / ".opsx"
        / "runs"
        / "scenario-coverage"
        / args.change_id
        / "provider-run-packet.json"
    )
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(packet, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    _ = guard.ProviderRunPacket.from_mapping(packet)
    print(json.dumps({"packet_path": str(out), "audited_head": packet["audited_head"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
