"""R22 acceptance closures retained under R23 trust channel."""

from __future__ import annotations

import json
import os
from pathlib import Path
from unittest import mock

import pytest

from opsx_conflict.authority import (
    AUTHORITY_ROOT_DIGEST_ENV,
    AUTHORITY_ROOT_PATH_ENV,
    AUTHORITY_ROOT_SIGNATURE_ENV,
    load_authenticated_authority_root,
    verify_external_authority_declaration,
)
from opsx_conflict.errors import StopRequired
from opsx_conflict.git_typed import _bind_trusted_git_executable
from opsx_conflict.hashutil import sha256_bytes

from authority_test_helpers import (
    base_declaration,
    hash_blob,
    init_git_repo,
    install_os_trust_pubkey,
    make_snapshot,
    pin_git_trust,
    write_signed_producer,
)

PACKAGE_ROOT = Path(__file__).resolve().parents[1]


def test_local_producer_without_external_root_is_blocker(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Self-minted producer + declaration without signature → BLOCKER."""
    monkeypatch.delenv(AUTHORITY_ROOT_DIGEST_ENV, raising=False)
    monkeypatch.delenv(AUTHORITY_ROOT_PATH_ENV, raising=False)
    monkeypatch.delenv(AUTHORITY_ROOT_SIGNATURE_ENV, raising=False)
    path = tmp_path / ".cursor/opsx-authority-producers.json"
    path.parent.mkdir(parents=True)
    path.write_text("{}", encoding="utf-8")
    with pytest.raises(StopRequired) as exc:
        verify_external_authority_declaration(
            tmp_path,
            declaration_rel="missing.json",
            expected_snapshot_id="x" * 64,
            operation="merge",
            commit_oids={"head": "a" * 40, "operation_head": "b" * 40},
            stage_blob_oids={"app/x.py": {"1": "1" * 40}},
            conflict_paths=["app/x.py"],
            source_commit="a" * 40,
        )
    assert exc.value.details.get("blocker") == "BLOCKER_AUTHORITY_PRODUCER_MISSING"


def test_manifest_host_frozen_cannot_mint_producer_trust(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Listing a producer in host_frozen_contracts does not create trust."""
    monkeypatch.delenv(AUTHORITY_ROOT_SIGNATURE_ENV, raising=False)
    with pytest.raises(StopRequired) as exc:
        load_authenticated_authority_root(tmp_path)
    assert exc.value.details.get("blocker") == "BLOCKER_AUTHORITY_PRODUCER_MISSING"


def test_declaration_from_other_snapshot_stops(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Declaration bound to another conflict_snapshot_id is rejected."""
    priv = install_os_trust_pubkey(monkeypatch, tmp_path)
    pin_git_trust(monkeypatch, tmp_path / "state")
    head = init_git_repo(tmp_path)
    oid = hash_blob(tmp_path, b"def foo():\n    return 1\n")
    stages = {"app/x.py": {"1": oid, "2": oid, "3": oid}}
    bound = write_signed_producer(tmp_path, monkeypatch, private_key=priv)
    snapshot = make_snapshot(head=head, other=head, stage_blob_oids=stages)
    decl = base_declaration(
        snapshot="0" * 64,
        producer_sha=bound["sha256"],
        contracts_digest=bound["contracts"],
        producer_path=bound["path"],
        issuer_private_key=bound["issuer_private_key"],
        stage_blob_oids=stages,
        symbols=["foo"],
        head=head,
        other=head,
    )
    path = tmp_path / "openspec/changes/c1/authority-declaration.json"
    path.parent.mkdir(parents=True)
    path.write_text(json.dumps(decl), encoding="utf-8")
    with pytest.raises(StopRequired) as exc:
        verify_external_authority_declaration(
            tmp_path,
            declaration_rel="openspec/changes/c1/authority-declaration.json",
            expected_snapshot_id=snapshot,
            operation="merge",
            commit_oids={"head": head, "operation_head": head},
            stage_blob_oids=stages,
            conflict_paths=["app/x.py"],
            source_commit=head,
        )
    assert exc.value.details.get("reason") == "conflict_snapshot_mismatch"


def test_proven_none_applicable_with_external_root(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Happy path under OS-pinned pubkey + signature + empty stage symbols."""
    priv = install_os_trust_pubkey(monkeypatch, tmp_path)
    pin_git_trust(monkeypatch, tmp_path / "state")
    head = init_git_repo(tmp_path)
    oid = hash_blob(tmp_path, b"x = 1\n")
    stages = {"app/x.py": {"1": oid, "2": oid, "3": oid}}
    bound = write_signed_producer(
        tmp_path, monkeypatch, private_key=priv, authorize_none=True
    )
    snapshot = make_snapshot(
        head=head, other=head, stage_blob_oids=stages, operation="rebase"
    )
    decl = base_declaration(
        snapshot=snapshot,
        producer_sha=bound["sha256"],
        contracts_digest=bound["contracts"],
        producer_path=bound["path"],
        issuer_private_key=bound["issuer_private_key"],
        stage_blob_oids=stages,
        symbols=[],
        capabilities=[],
        operation="rebase",
        head=head,
        other=head,
    )
    path = tmp_path / "openspec/changes/c1/authority-declaration.json"
    path.parent.mkdir(parents=True)
    path.write_text(json.dumps(decl), encoding="utf-8")
    proof = verify_external_authority_declaration(
        tmp_path,
        declaration_rel="openspec/changes/c1/authority-declaration.json",
        expected_snapshot_id=snapshot,
        operation="rebase",
        commit_oids={"head": head, "operation_head": head},
        stage_blob_oids=stages,
        conflict_paths=["app/x.py"],
        source_commit=head,
    )
    assert proof["none_applicable"] is True


def test_git_bind_permission_error_is_typed_stop(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """PermissionError during bind publish → StopRequired."""
    monkeypatch.setenv("OPSX_CONFLICT_STATE", str(tmp_path / "state"))
    source = tmp_path / ("git.exe" if os.name == "nt" else "git")
    source.write_bytes(b"trusted-git-bytes")
    digest = sha256_bytes(b"trusted-git-bytes")
    real_open = os.open

    def boom(path, flags, mode=0o777):  # type: ignore[no-untyped-def]
        if ".tmp" in str(path):
            raise PermissionError("denied")
        return real_open(path, flags, mode)

    with mock.patch("os.open", boom):
        with pytest.raises(StopRequired) as exc:
            _bind_trusted_git_executable(executable=str(source), digest=digest)
    assert exc.value.reason in {
        "GIT_TRUST_BIND_FAILED",
        "GIT_TRUST_BIND_TMP_UNSAFE",
    }


def test_authority_schema_v3_requires_producer_contract_sha256() -> None:
    """Shipped schema is v5 envelope; payload requires producer_contract_sha256."""
    schema = json.loads(
        (
            PACKAGE_ROOT / "schemas" / "authority-declaration.schema.json"
        ).read_text(encoding="utf-8")
    )
    assert schema["$id"] == "opsx-resolve-conflict/authority-declaration/v5"
    assert set(schema["required"]) >= {
        "schema",
        "payload",
        "issuer_key_id",
        "signature",
    }
    payload_required = schema["properties"]["payload"]["required"]
    assert "producer_contract_sha256" in payload_required
    assert "symbol_extractor_version" in payload_required
    assert "capability_evidence" in payload_required


def test_package_discloses_r22_status() -> None:
    """Review docs disclose consumer-side status and open blockers."""
    review = (PACKAGE_ROOT / "REVIEW_REQUEST.md").read_text(encoding="utf-8")
    assert "BLOCKER_AUTHORITY_PRODUCER_MISSING" in review
    assert "BLOCKER_OS_SANDBOX_RUNNER_MISSING" in review
    assert "GO_CAPABILITY=false" in review
