"""Unit: OPSX provider-run fail-closed fingerprint guard (без PG/Docker)."""

from __future__ import annotations

import importlib.util
import sys
from dataclasses import replace
from pathlib import Path
from unittest.mock import MagicMock

import pytest

_TEST_LIVE_TOKEN = "unit-test-authorize-one-live-run"

pytestmark = pytest.mark.unit

_REPO_ROOT = Path(__file__).resolve().parents[3]
_GUARD_PATH = _REPO_ROOT / ".opsx" / "tools" / "opsx_provider_run_guard.py"


def _load_guard():
    spec = importlib.util.spec_from_file_location(
        "opsx_provider_run_guard", _GUARD_PATH
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


guard = _load_guard()
_TEST_AUTH_ID = guard.one_shot_authorization_token_sha256(_TEST_LIVE_TOKEN)


def _minimal_block(
    *,
    host: str = "127.0.0.1",
    port: int = 5433,
    dbname: str = "test_adv_bot_db",
    target: str = "tests/integration/wb_sky_mcp/",
    include_unguarded_pytest: bool = False,
) -> str:
    lines = [
        f"export POSTGRES_MASTER_HOST={host}",
        f"export POSTGRES_PORT={port}",
        f"export POSTGRES_DBNAME={dbname}",
        "export REDIS_HOST=127.0.0.1",
        "export REDIS_PORT=6379",
        f"# PYTEST_TARGETS: {target}",
        "poetry run python .opsx/tools/opsx_provider_run_guard.py verify --packet pkt.json --repo .",
        "poetry run python .opsx/tools/opsx_provider_run_guard.py run --packet pkt.json --repo .",
    ]
    if include_unguarded_pytest:
        lines.insert(
            -2,
            "poetry run pytest tests/integration/wb_sky_mcp/ -m destructive_local",
        )
    return "\n".join(lines) + "\n"


def _packet(
    block: str,
    *,
    head: str = "abc123",
    status: str = "status_hash",
    diff: str = "diff_hash",
    manifest: str = "manifest_hash",
    pytest_argv: tuple[str, ...] = (
        "poetry",
        "run",
        "pytest",
        "tests/integration/wb_sky_mcp/",
        "-m",
        "destructive_local",
        "-vv",
        "--tb=short",
    ),
    test_ids: tuple[str, ...] = (
        "tests/integration/wb_sky_mcp/test_mcp_pg_connection_repository.py::test_x",
    ),
    pytest_targets: tuple[str, ...] = ("tests/integration/wb_sky_mcp/",),
    host: str = "127.0.0.1",
    port: int = 5433,
    dbname: str = "test_adv_bot_db",
) -> guard.ProviderRunPacket:
    return guard.ProviderRunPacket(
        audited_head=head,
        audited_status_sha256=status,
        audited_tracked_diff_sha256=diff,
        audited_untracked_manifest_sha256=manifest,
        allowed_run_block_sha256=guard.allowed_run_block_sha256(block),
        allowed_run_block_text=block,
        pytest_argv=pytest_argv,
        pytest_targets=pytest_targets,
        provider_test_ids=test_ids,
        postgres_host=host,
        postgres_port=port,
        postgres_dbname=dbname,
        redis_host="127.0.0.1",
        redis_port=6379,
        change_id="wb-sky-mcp-read-interface",
        one_shot_authorization_id=_TEST_AUTH_ID,
    )


def _identity_compute(expected: str):
    return lambda _root: expected


@pytest.mark.unit
def test_matching_packet_permit_dry_run_no_subprocess() -> None:
    block = _minimal_block()
    packet = _packet(block)
    repo = Path("/tmp/unused")

    verdict = guard.verify_provider_run_packet(
        repo,
        packet,
        compute_head=_identity_compute("abc123"),
        compute_status=_identity_compute("status_hash"),
        compute_diff=_identity_compute("diff_hash"),
        compute_manifest=_identity_compute("manifest_hash"),
        live_token=_TEST_LIVE_TOKEN,
    )
    assert verdict.status == "PERMIT"
    assert verdict.spawn_count == 0

    mock_run = MagicMock()
    run_verdict = guard.run_guarded_pytest(
        repo,
        packet,
        subprocess_runner=mock_run,
        dry_run=True,
        compute_head=_identity_compute("abc123"),
        compute_status=_identity_compute("status_hash"),
        compute_diff=_identity_compute("diff_hash"),
        compute_manifest=_identity_compute("manifest_hash"),
        live_token=_TEST_LIVE_TOKEN,
    )
    assert run_verdict.status == "PERMIT"
    assert run_verdict.spawn_count == 0
    mock_run.assert_not_called()


@pytest.mark.unit
def test_run_block_sha_mismatch_rejects_spawn_zero() -> None:
    block = _minimal_block()
    packet = _packet(block)
    packet = replace(packet, allowed_run_block_sha256="0" * 64)
    verdict = guard.verify_provider_run_packet(
        Path("/tmp"),
        packet,
        compute_head=_identity_compute(packet.audited_head),
        compute_status=_identity_compute(packet.audited_status_sha256),
        compute_diff=_identity_compute(packet.audited_tracked_diff_sha256),
        compute_manifest=_identity_compute(packet.audited_untracked_manifest_sha256),
        live_token=_TEST_LIVE_TOKEN,
    )
    assert verdict.status == "BLOCKED_FINGERPRINT_MISMATCH"
    assert verdict.mismatch_field == "allowed_run_block_sha256"
    assert verdict.spawn_count == 0

    mock_run = MagicMock()
    run_verdict = guard.run_guarded_pytest(
        Path("/tmp"),
        packet,
        subprocess_runner=mock_run,
        compute_head=_identity_compute(packet.audited_head),
        compute_status=_identity_compute(packet.audited_status_sha256),
        compute_diff=_identity_compute(packet.audited_tracked_diff_sha256),
        compute_manifest=_identity_compute(packet.audited_untracked_manifest_sha256),
        live_token=_TEST_LIVE_TOKEN,
    )
    mock_run.assert_not_called()
    assert run_verdict.spawn_count == 0


@pytest.mark.unit
def test_head_mismatch_rejects() -> None:
    block = _minimal_block()
    packet = _packet(block)
    verdict = guard.verify_provider_run_packet(
        Path("/tmp"),
        packet,
        compute_head=_identity_compute("other_head"),
        compute_status=_identity_compute(packet.audited_status_sha256),
        compute_diff=_identity_compute(packet.audited_tracked_diff_sha256),
        compute_manifest=_identity_compute(packet.audited_untracked_manifest_sha256),
        live_token=_TEST_LIVE_TOKEN,
    )
    assert verdict.status == "BLOCKED_FINGERPRINT_MISMATCH"
    assert verdict.mismatch_field == "audited_head"


@pytest.mark.unit
def test_status_diff_untracked_mismatch_rejects() -> None:
    block = _minimal_block()
    packet = _packet(block)
    base = {
        "compute_head": _identity_compute(packet.audited_head),
        "compute_diff": _identity_compute(packet.audited_tracked_diff_sha256),
        "compute_manifest": _identity_compute(
            packet.audited_untracked_manifest_sha256
        ),
    }
    v_status = guard.verify_provider_run_packet(
        Path("/tmp"),
        packet,
        compute_status=_identity_compute("bad"),
        live_token=_TEST_LIVE_TOKEN,
        **base,
    )
    assert v_status.mismatch_field == "audited_status_sha256"

    v_diff = guard.verify_provider_run_packet(
        Path("/tmp"),
        packet,
        compute_status=_identity_compute(packet.audited_status_sha256),
        compute_diff=_identity_compute("bad"),
        compute_manifest=base["compute_manifest"],
        compute_head=base["compute_head"],
        live_token=_TEST_LIVE_TOKEN,
    )
    assert v_diff.mismatch_field == "audited_tracked_diff_sha256"

    v_manifest = guard.verify_provider_run_packet(
        Path("/tmp"),
        packet,
        compute_status=_identity_compute(packet.audited_status_sha256),
        compute_diff=base["compute_diff"],
        compute_manifest=_identity_compute("bad"),
        compute_head=base["compute_head"],
        live_token=_TEST_LIVE_TOKEN,
    )
    assert v_manifest.mismatch_field == "audited_untracked_manifest_sha256"


@pytest.mark.unit
def test_command_and_db_coords_mismatch_rejects() -> None:
    block = _minimal_block(port=5433)
    packet = _packet(block, port=5432)
    verdict = guard.verify_provider_run_packet(
        Path("/tmp"),
        packet,
        compute_head=_identity_compute(packet.audited_head),
        compute_status=_identity_compute(packet.audited_status_sha256),
        compute_diff=_identity_compute(packet.audited_tracked_diff_sha256),
        compute_manifest=_identity_compute(packet.audited_untracked_manifest_sha256),
        live_token=_TEST_LIVE_TOKEN,
    )
    assert verdict.status == "BLOCKED_FINGERPRINT_MISMATCH"
    assert verdict.mismatch_field == "postgres_port_in_block"

    other_block = _minimal_block(target="tests/other/")
    packet_cmd = _packet(
        other_block,
        pytest_argv=(
            "poetry",
            "run",
            "pytest",
            "tests/other/",
            "-m",
            "destructive_local",
        ),
        pytest_targets=("tests/other/",),
    )
    verdict_cmd = guard.verify_provider_run_packet(
        Path("/tmp"),
        packet_cmd,
        compute_head=_identity_compute(packet_cmd.audited_head),
        compute_status=_identity_compute(packet_cmd.audited_status_sha256),
        compute_diff=_identity_compute(packet_cmd.audited_tracked_diff_sha256),
        compute_manifest=_identity_compute(
            packet_cmd.audited_untracked_manifest_sha256
        ),
        live_token=_TEST_LIVE_TOKEN,
    )
    assert verdict_cmd.mismatch_field == "provider_test_ids"


@pytest.mark.unit
def test_auth_not_authorized_blocks_spawn(tmp_path: Path) -> None:
    block = _minimal_block()
    packet = _packet(block)
    repo = tmp_path
    verdict = guard.verify_provider_run_packet(
        repo,
        packet,
        compute_head=_identity_compute(packet.audited_head),
        compute_status=_identity_compute(packet.audited_status_sha256),
        compute_diff=_identity_compute(packet.audited_tracked_diff_sha256),
        compute_manifest=_identity_compute(packet.audited_untracked_manifest_sha256),
        live_token=None,
    )
    assert verdict.status == "BLOCKED_AUTHORIZATION"
    assert verdict.mismatch_field == "AUTH_NOT_AUTHORIZED"
    mock_run = MagicMock()
    run_v = guard.run_guarded_pytest(
        repo,
        packet,
        subprocess_runner=mock_run,
        compute_head=_identity_compute(packet.audited_head),
        compute_status=_identity_compute(packet.audited_status_sha256),
        compute_diff=_identity_compute(packet.audited_tracked_diff_sha256),
        compute_manifest=_identity_compute(packet.audited_untracked_manifest_sha256),
        live_token=None,
    )
    mock_run.assert_not_called()
    assert run_v.spawn_count == 0


@pytest.mark.unit
def test_auth_token_mismatch_blocks_spawn(tmp_path: Path) -> None:
    block = _minimal_block()
    packet = _packet(block)
    repo = tmp_path
    verdict = guard.verify_provider_run_packet(
        repo,
        packet,
        compute_head=_identity_compute(packet.audited_head),
        compute_status=_identity_compute(packet.audited_status_sha256),
        compute_diff=_identity_compute(packet.audited_tracked_diff_sha256),
        compute_manifest=_identity_compute(packet.audited_untracked_manifest_sha256),
        live_token="wrong-token",
    )
    assert verdict.status == "BLOCKED_AUTHORIZATION"
    assert verdict.mismatch_field == "AUTH_TOKEN_MISMATCH"


@pytest.mark.unit
def test_one_shot_consumed_blocks_second_spawn(tmp_path: Path) -> None:
    block = _minimal_block()
    packet = _packet(block)
    repo = tmp_path
    base_kw = {
        "compute_head": _identity_compute(packet.audited_head),
        "compute_status": _identity_compute(packet.audited_status_sha256),
        "compute_diff": _identity_compute(packet.audited_tracked_diff_sha256),
        "compute_manifest": _identity_compute(packet.audited_untracked_manifest_sha256),
        "live_token": _TEST_LIVE_TOKEN,
    }
    mock_run = MagicMock()
    first = guard.run_guarded_pytest(
        repo,
        packet,
        subprocess_runner=mock_run,
        **base_kw,
    )
    assert first.spawn_count == 1
    assert mock_run.call_count == 1
    second = guard.run_guarded_pytest(
        repo,
        packet,
        subprocess_runner=mock_run,
        **base_kw,
    )
    assert second.status == "BLOCKED_AUTHORIZATION"
    assert second.mismatch_field == "AUTH_CONSUMED"
    assert mock_run.call_count == 1


@pytest.mark.unit
def test_extract_pytest_targets_ignores_options() -> None:
    argv = (
        "poetry",
        "run",
        "pytest",
        "tests/integration/wb_sky_mcp/",
        "-m",
        "destructive_local",
        "-vv",
        "--tb=short",
    )
    assert guard.extract_pytest_targets_from_argv(argv) == (
        "tests/integration/wb_sky_mcp/",
    )


@pytest.mark.unit
def test_provider_test_ids_use_posix_paths_on_windows_host_semantics() -> None:
    """Regression: host Path.parent must not be used for packet verification."""

    node = (
        "tests/integration/wb_sky_mcp/"
        "test_mcp_pg_connection_repository.py::test_sql_connection_repository_persist_and_raw_select"
    )
    targets = ("tests/integration/wb_sky_mcp/",)
    assert guard.provider_test_id_within_targets(node, targets)
    block = _minimal_block()
    packet = _packet(
        block,
        test_ids=(node,),
        pytest_targets=targets,
    )
    verdict = guard.verify_provider_run_packet(
        Path("/tmp"),
        packet,
        compute_head=_identity_compute(packet.audited_head),
        compute_status=_identity_compute(packet.audited_status_sha256),
        compute_diff=_identity_compute(packet.audited_tracked_diff_sha256),
        compute_manifest=_identity_compute(packet.audited_untracked_manifest_sha256),
        live_token=_TEST_LIVE_TOKEN,
    )
    assert verdict.status == "PERMIT"


@pytest.mark.unit
def test_provider_test_outside_sealed_target_rejected() -> None:
    block = _minimal_block()
    packet = _packet(
        block,
        test_ids=("tests/integration/other/test_x.py::test_x",),
    )
    verdict = guard.verify_provider_run_packet(
        Path("/tmp"),
        packet,
        compute_head=_identity_compute(packet.audited_head),
        compute_status=_identity_compute(packet.audited_status_sha256),
        compute_diff=_identity_compute(packet.audited_tracked_diff_sha256),
        compute_manifest=_identity_compute(packet.audited_untracked_manifest_sha256),
        live_token=_TEST_LIVE_TOKEN,
    )
    assert verdict.mismatch_field == "provider_test_ids"
    assert verdict.spawn_count == 0


@pytest.mark.unit
def test_unguarded_pytest_line_in_block_rejected() -> None:
    block = _minimal_block(include_unguarded_pytest=True)
    packet = _packet(block)
    verdict = guard.verify_provider_run_packet(
        Path("/tmp"),
        packet,
        compute_head=_identity_compute(packet.audited_head),
        compute_status=_identity_compute(packet.audited_status_sha256),
        compute_diff=_identity_compute(packet.audited_tracked_diff_sha256),
        compute_manifest=_identity_compute(packet.audited_untracked_manifest_sha256),
        live_token=_TEST_LIVE_TOKEN,
    )
    assert verdict.mismatch_field == "unguarded_pytest_in_block"


@pytest.mark.unit
def test_verify_failure_does_not_consume_authorization(tmp_path: Path) -> None:
    block = _minimal_block()
    packet = _packet(block, test_ids=("tests/integration/other/t.py::test_x",))
    repo = tmp_path
    guard.verify_provider_run_packet(
        repo,
        packet,
        compute_head=_identity_compute(packet.audited_head),
        compute_status=_identity_compute(packet.audited_status_sha256),
        compute_diff=_identity_compute(packet.audited_tracked_diff_sha256),
        compute_manifest=_identity_compute(packet.audited_untracked_manifest_sha256),
        live_token=_TEST_LIVE_TOKEN,
    )
    ledger = guard.authorization_ledger_path(repo, packet.change_id)
    assert not ledger.is_file()


@pytest.mark.unit
def test_build_provider_subprocess_env_preserves_path_and_overrides_db() -> None:
    block = _minimal_block()
    packet = _packet(block)
    parent = {
        "PATH": "/usr/local/bin:/bin",
        "POSTGRES_MASTER_HOST": "prod-db.example.com",
        "POSTGRES_PORT": "5432",
        "POSTGRES_DBNAME": "production",
        "REDIS_PORT": "6380",
    }
    env = guard.build_provider_subprocess_env(packet, parent_env=parent)
    assert env["PATH"] == parent["PATH"]
    assert env["POSTGRES_MASTER_HOST"] == "127.0.0.1"
    assert env["POSTGRES_REPLICA_HOST"] == "127.0.0.1"
    assert env["POSTGRES_PORT"] == "5433"
    assert env["POSTGRES_DBNAME"] == "test_adv_bot_db"
    assert env["REDIS_HOST"] == "127.0.0.1"
    assert env["REDIS_PORT"] == "6379"
    assert env["ALLOW_DESTRUCTIVE_TEST_DB"] == "1"
    assert env["ALLOW_DESTRUCTIVE_TEST_CLICKHOUSE"] == "1"


@pytest.mark.unit
def test_run_guarded_pytest_passes_merged_env_to_subprocess(tmp_path: Path) -> None:
    block = _minimal_block()
    packet = _packet(block)
    repo = tmp_path
    captured: dict[str, object] = {}

    def _capture_run(argv, cwd, env, check):  # type: ignore[no-untyped-def]
        captured["argv"] = argv
        captured["env"] = env

    base_kw = {
        "compute_head": _identity_compute(packet.audited_head),
        "compute_status": _identity_compute(packet.audited_status_sha256),
        "compute_diff": _identity_compute(packet.audited_tracked_diff_sha256),
        "compute_manifest": _identity_compute(packet.audited_untracked_manifest_sha256),
        "live_token": _TEST_LIVE_TOKEN,
        "extra_env": {"PATH": "/opt/poetry/bin"},
    }
    guard.run_guarded_pytest(
        repo,
        packet,
        subprocess_runner=_capture_run,
        **base_kw,
    )
    env = captured["env"]
    assert env["PATH"] == "/opt/poetry/bin"
    assert env["POSTGRES_DBNAME"] == "test_adv_bot_db"


@pytest.mark.unit
def test_allowed_run_block_sha256_trailing_newline_canonical() -> None:
    text = "echo ok"
    assert guard.allowed_run_block_sha256(text) == guard.allowed_run_block_sha256(
        "echo ok\n"
    )
