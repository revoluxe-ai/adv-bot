"""Unit: OPSX provider-run fail-closed fingerprint guard (без PG/Docker)."""

from __future__ import annotations

import importlib.util
import subprocess
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


def _default_pytest_argv(
    target: str = "tests/integration/wb_sky_mcp/",
) -> tuple[str, ...]:
    return (
        "poetry",
        "run",
        "pytest",
        target,
        "-m",
        "destructive_local",
        "-vv",
        "--tb=short",
    )


def _minimal_block(
    *,
    host: str = "127.0.0.1",
    port: int = 5433,
    dbname: str = "test_adv_bot_db",
    target: str = "tests/integration/wb_sky_mcp/",
    pytest_argv: tuple[str, ...] | None = None,
    include_unguarded_pytest: bool = False,
) -> str:
    argv = pytest_argv if pytest_argv is not None else _default_pytest_argv(target)
    argv_sha = guard.canonical_pytest_argv_sha256(argv)
    lines = [
        f"export POSTGRES_MASTER_HOST={host}",
        f"export POSTGRES_PORT={port}",
        f"export POSTGRES_DBNAME={dbname}",
        "export REDIS_HOST=127.0.0.1",
        "export REDIS_PORT=6379",
        f"# PYTEST_TARGETS: {target}",
        f"# CANONICAL_PYTEST_ARGV_SHA256: {argv_sha}",
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
    pytest_argv: tuple[str, ...] | None = None,
    test_ids: tuple[str, ...] = (
        "tests/integration/wb_sky_mcp/test_mcp_pg_connection_repository.py::test_x",
    ),
    pytest_targets: tuple[str, ...] = ("tests/integration/wb_sky_mcp/",),
    host: str = "127.0.0.1",
    port: int = 5433,
    dbname: str = "test_adv_bot_db",
) -> guard.ProviderRunPacket:
    resolved_argv = pytest_argv if pytest_argv is not None else _default_pytest_argv(
        pytest_targets[0]
    )
    return guard.ProviderRunPacket(
        audited_head=head,
        audited_status_sha256=status,
        audited_tracked_diff_sha256=diff,
        audited_untracked_manifest_sha256=manifest,
        allowed_run_block_sha256=guard.allowed_run_block_sha256(block),
        allowed_run_block_text=block,
        canonical_pytest_argv_sha256=guard.canonical_pytest_argv_sha256(resolved_argv),
        pytest_argv=resolved_argv,
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


def _completed(returncode: int) -> subprocess.CompletedProcess[str]:
    return subprocess.CompletedProcess(args=["pytest"], returncode=returncode)


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

    other_argv = (
        "poetry",
        "run",
        "pytest",
        "tests/other/",
        "-m",
        "destructive_local",
    )
    other_block = _minimal_block(target="tests/other/", pytest_argv=other_argv)
    packet_cmd = _packet(
        other_block,
        pytest_argv=other_argv,
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
    mock_run = MagicMock(return_value=_completed(0))
    first = guard.run_guarded_pytest(
        repo,
        packet,
        subprocess_runner=mock_run,
        **base_kw,
    )
    assert first.status == "PROVIDER_PASSED"
    assert first.provider_result == "PASSED"
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
    ledger = guard.authorization_ledger_path(
        repo, packet.change_id, packet.one_shot_authorization_id
    )
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
        return _completed(0)

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


def _run_packet(tmp_path: Path):
    block = _minimal_block()
    packet = _packet(block)
    base_kw = {
        "compute_head": _identity_compute(packet.audited_head),
        "compute_status": _identity_compute(packet.audited_status_sha256),
        "compute_diff": _identity_compute(packet.audited_tracked_diff_sha256),
        "compute_manifest": _identity_compute(packet.audited_untracked_manifest_sha256),
        "live_token": _TEST_LIVE_TOKEN,
    }
    return block, packet, tmp_path, base_kw


@pytest.mark.unit
def test_provider_rc_zero_consumed_and_cli_success(tmp_path: Path) -> None:
    _, packet, repo, base_kw = _run_packet(tmp_path)
    mock_run = MagicMock(return_value=_completed(0))
    verdict = guard.run_guarded_pytest(
        repo, packet, subprocess_runner=mock_run, **base_kw
    )
    assert verdict.status == "PROVIDER_PASSED"
    assert verdict.authorization_state == "AUTHORIZED_CONSUMED"
    assert verdict.guard_permission == "PERMITTED"
    assert guard.cli_exit_code_for_verdict(verdict) == guard.EXIT_PERMIT


@pytest.mark.unit
def test_provider_rc_nonzero_failed_and_cli_nonzero(tmp_path: Path) -> None:
    _, packet, repo, base_kw = _run_packet(tmp_path)
    mock_run = MagicMock(return_value=_completed(1))
    verdict = guard.run_guarded_pytest(
        repo, packet, subprocess_runner=mock_run, **base_kw
    )
    assert verdict.status == "PROVIDER_FAILED"
    assert verdict.provider_return_code == 1
    assert verdict.provider_result == "FAILED"
    assert verdict.authorization_state == "AUTHORIZED_CONSUMED"
    assert guard.cli_exit_code_for_verdict(verdict) == guard.EXIT_PROVIDER_FAILED


@pytest.mark.unit
def test_provider_runner_exception_error_and_consumed(tmp_path: Path) -> None:
    _, packet, repo, base_kw = _run_packet(tmp_path)

    def _boom(*_a, **_k):
        raise RuntimeError("spawn failed")

    verdict = guard.run_guarded_pytest(
        repo, packet, subprocess_runner=_boom, **base_kw
    )
    assert verdict.status == "PROVIDER_ERROR"
    assert verdict.provider_result == "ERROR"
    assert verdict.spawn_count == 1
    assert verdict.authorization_state == "AUTHORIZED_CONSUMED"
    assert guard.cli_exit_code_for_verdict(verdict) == guard.EXIT_PROVIDER_ERROR


@pytest.mark.unit
def test_provider_missing_returncode_is_error(tmp_path: Path) -> None:
    _, packet, repo, base_kw = _run_packet(tmp_path)
    verdict = guard.run_guarded_pytest(
        repo,
        packet,
        subprocess_runner=lambda *_a, **_k: None,
        **base_kw,
    )
    assert verdict.status == "PROVIDER_ERROR"


@pytest.mark.unit
def test_fingerprint_mismatch_does_not_consume(tmp_path: Path) -> None:
    block = _minimal_block()
    packet = _packet(block, head="wrong")
    verdict = guard.verify_provider_run_packet(
        tmp_path,
        packet,
        compute_head=_identity_compute("abc123"),
        compute_status=_identity_compute(packet.audited_status_sha256),
        compute_diff=_identity_compute(packet.audited_tracked_diff_sha256),
        compute_manifest=_identity_compute(packet.audited_untracked_manifest_sha256),
        live_token=_TEST_LIVE_TOKEN,
    )
    assert verdict.status == "BLOCKED_FINGERPRINT_MISMATCH"
    assert not guard.authorization_ledger_path(
        tmp_path, packet.change_id, packet.one_shot_authorization_id
    ).is_file()


@pytest.mark.unit
def test_canonical_pytest_argv_sha256_mismatch_rejects() -> None:
    block = _minimal_block()
    packet = _packet(block)
    packet = replace(
        packet,
        canonical_pytest_argv_sha256="0" * 64,
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
    assert verdict.mismatch_field == "canonical_pytest_argv_sha256"


@pytest.mark.unit
def test_python_m_pytest_in_block_rejected() -> None:
    block = _minimal_block()
    lines = block.splitlines()
    lines.insert(
        -2,
        "python -m pytest tests/integration/wb_sky_mcp/ -m destructive_local",
    )
    bad_block = "\n".join(lines) + "\n"
    packet = _packet(bad_block)
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


def _mp_try_claim_worker(repo_str: str, packet: guard.ProviderRunPacket, token: str) -> str:
    mod = _load_guard()
    return mod.try_claim_one_shot_authorization(
        Path(repo_str),
        packet,
        live_token=token,
    )


@pytest.mark.unit
def test_concurrent_one_shot_claim_exactly_one_winner(tmp_path: Path) -> None:
    from concurrent.futures import ProcessPoolExecutor

    block = _minimal_block()
    packet = _packet(block)
    repo = str(tmp_path)
    with ProcessPoolExecutor(max_workers=2) as pool:
        futures = [
            pool.submit(_mp_try_claim_worker, repo, packet, _TEST_LIVE_TOKEN),
            pool.submit(_mp_try_claim_worker, repo, packet, _TEST_LIVE_TOKEN),
        ]
        results = [f.result() for f in futures]
    assert results.count("CLAIMED") == 1
    assert results.count("ALREADY_CONSUMED") == 1
    state = guard.resolve_authorization_state(
        tmp_path,
        packet,
        live_token=_TEST_LIVE_TOKEN,
    )
    assert state == "AUTHORIZED_CONSUMED"


def _mp_run_guarded_worker(
    repo_str: str,
    packet: guard.ProviderRunPacket,
    token: str,
    counter_path: str,
) -> dict[str, object]:
    import os

    mod = _load_guard()

    def _counting_runner(argv, cwd, env, check=False):  # type: ignore[no-untyped-def]
        path = Path(counter_path)
        prior = int(path.read_text(encoding="utf-8")) if path.is_file() else 0
        path.write_text(str(prior + 1), encoding="utf-8")
        return subprocess.CompletedProcess(list(argv), 0)

    base_kw = {
        "compute_head": lambda _r: packet.audited_head,
        "compute_status": lambda _r: packet.audited_status_sha256,
        "compute_diff": lambda _r: packet.audited_tracked_diff_sha256,
        "compute_manifest": lambda _r: packet.audited_untracked_manifest_sha256,
        "live_token": token,
    }
    verdict = mod.run_guarded_pytest(
        Path(repo_str),
        packet,
        subprocess_runner=_counting_runner,
        **base_kw,
    )
    return verdict.to_dict()


@pytest.mark.unit
def test_concurrent_run_guarded_exactly_one_provider_spawn(tmp_path: Path) -> None:
    from concurrent.futures import ProcessPoolExecutor

    block = _minimal_block()
    packet = _packet(block)
    counter = tmp_path / "spawn.count"
    counter.write_text("0", encoding="utf-8")
    repo = str(tmp_path)
    with ProcessPoolExecutor(max_workers=2) as pool:
        futures = [
            pool.submit(
                _mp_run_guarded_worker,
                repo,
                packet,
                _TEST_LIVE_TOKEN,
                str(counter),
            ),
            pool.submit(
                _mp_run_guarded_worker,
                repo,
                packet,
                _TEST_LIVE_TOKEN,
                str(counter),
            ),
        ]
        verdicts = [f.result() for f in futures]
    spawned = sum(1 for v in verdicts if v.get("provider_spawned"))
    blocked = sum(1 for v in verdicts if v.get("status") == "BLOCKED_AUTHORIZATION")
    assert int(counter.read_text(encoding="utf-8")) == 1
    assert spawned == 1
    assert blocked == 1
