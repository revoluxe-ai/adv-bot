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
    pytest_line: str = (
        "poetry run pytest tests/integration/wb_sky_mcp/ "
        "-m destructive_local -vv --tb=short"
    ),
) -> str:
    return (
        f"export POSTGRES_MASTER_HOST={host}\n"
        f"export POSTGRES_PORT={port}\n"
        f"export POSTGRES_DBNAME={dbname}\n"
        f"{pytest_line}\n"
    )


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
        provider_test_ids=test_ids,
        postgres_host=host,
        postgres_port=port,
        postgres_dbname=dbname,
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

    wrong_cmd_block = _minimal_block(
        pytest_line="poetry run pytest tests/other/ -m destructive_local"
    )
    packet_cmd = _packet(
        wrong_cmd_block,
        pytest_argv=("poetry", "run", "pytest", "tests/integration/wb_sky_mcp/"),
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
    assert verdict_cmd.mismatch_field == "pytest_argv_in_block"


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
def test_allowed_run_block_sha256_trailing_newline_canonical() -> None:
    text = "echo ok"
    assert guard.allowed_run_block_sha256(text) == guard.allowed_run_block_sha256(
        "echo ok\n"
    )
