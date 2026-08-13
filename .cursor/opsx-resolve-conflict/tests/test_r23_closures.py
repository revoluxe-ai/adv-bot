"""R23 closures: signed OS trust channel, stage-blob symbols, rename always-on."""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from opsx_conflict.authority import (
    AUTHORITY_ROOT_DIGEST_ENV,
    AUTHORITY_ROOT_PATH_ENV,
    AUTHORITY_ROOT_SIGNATURE_ENV,
    load_authenticated_authority_root,
    verify_external_authority_declaration,
    verify_rename_lineage_evidence,
)
from opsx_conflict.errors import StopRequired
from opsx_conflict.git_typed import _bind_trusted_git_executable, _verify_bound_executable
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


def test_ambient_path_digest_alone_rejected(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """R22-HIGH-001: path+digest without OS pubkey signature → BLOCKER."""
    monkeypatch.delenv(AUTHORITY_ROOT_SIGNATURE_ENV, raising=False)
    # No OS pubkey installed at pinned path (default ProgramData/etc).
    rel = ".cursor/opsx-authority-producers.json"
    path = tmp_path / rel
    path.parent.mkdir(parents=True)
    raw = json.dumps(
        {
            "issuers": ["self-minted"],
            "authoritative_roots": ["openspec/policies/OPSX_ROOT_CONTRACT.md"],
            "authorize_none_applicable": True,
            "capability_bindings": [],
        }
    ).encode()
    (tmp_path / "openspec/policies").mkdir(parents=True)
    (tmp_path / "openspec/policies/OPSX_ROOT_CONTRACT.md").write_text("x\n")
    path.write_bytes(raw)
    monkeypatch.setenv(AUTHORITY_ROOT_PATH_ENV, rel)
    monkeypatch.setenv(AUTHORITY_ROOT_DIGEST_ENV, sha256_bytes(raw))
    with pytest.raises(StopRequired) as exc:
        load_authenticated_authority_root(tmp_path)
    assert exc.value.details.get("blocker") == "BLOCKER_AUTHORITY_PRODUCER_MISSING"


def test_signed_producer_accepted_with_os_pubkey(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Valid OS pubkey + signature authenticates producer."""
    priv = install_os_trust_pubkey(monkeypatch, tmp_path)
    bound = write_signed_producer(tmp_path, monkeypatch, private_key=priv)
    loaded = load_authenticated_authority_root(tmp_path)
    assert loaded["sha256"] == bound["sha256"]
    assert loaded["issuers"] == ["opsx-authority-issuer"]


def test_mutated_producer_invalidates_signature(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Byte mutation after signing → signature invalid STOP."""
    priv = install_os_trust_pubkey(monkeypatch, tmp_path)
    bound = write_signed_producer(tmp_path, monkeypatch, private_key=priv)
    path = tmp_path / bound["path"]
    path.write_text(path.read_text(encoding="utf-8") + "\n", encoding="utf-8")
    with pytest.raises(StopRequired) as exc:
        load_authenticated_authority_root(tmp_path)
    assert exc.value.details.get("reason") in {
        "authority_root_signature_invalid",
        "authority_root_digest_mismatch",
    }


def test_symbols_from_stage_blobs_not_worktree(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Conflict-marker worktree cannot hide stage-blob symbols."""
    priv = install_os_trust_pubkey(monkeypatch, tmp_path)
    pin_git_trust(monkeypatch, tmp_path / "state")
    head = init_git_repo(tmp_path)
    side_a = b"def auth_handler():\n    return 1\n"
    side_b = b"def audit_handler():\n    return 2\n"
    oid_a = hash_blob(tmp_path, side_a)
    oid_b = hash_blob(tmp_path, side_b)
    # Poison worktree with conflict markers.
    py = tmp_path / "app" / "x.py"
    py.parent.mkdir(parents=True)
    py.write_text(
        "<<<<<<< ours\ndef auth_handler():\n=======\ndef audit_handler():\n>>>>>>> theirs\n",
        encoding="utf-8",
    )
    stages = {"app/x.py": {"1": oid_a, "2": oid_a, "3": oid_b}}
    bound = write_signed_producer(
        tmp_path,
        monkeypatch,
        private_key=priv,
        capability_bindings=[
            {"symbol": "auth_handler", "capability": "auth"},
            {"symbol": "audit_handler", "capability": "audit"},
        ],
        authorize_none=False,
    )
    snapshot = make_snapshot(head=head, other=head, stage_blob_oids=stages)
    # Omitting a symbol must STOP.
    decl = base_declaration(
        snapshot=snapshot,
        producer_sha=bound["sha256"],
        contracts_digest=bound["contracts"],
        producer_path=bound["path"],
        issuer_private_key=bound["issuer_private_key"],
        stage_blob_oids=stages,
        symbols=["auth_handler"],  # missing audit_handler
        capabilities=["auth"],
        head=head,
        other=head,
        none_applicable=False,
        applicable=[
            {
                "path": "openspec/policies/OPSX_ROOT_CONTRACT.md",
                "role": "contract",
                "sha256": sha256_bytes(
                    (tmp_path / "openspec/policies/OPSX_ROOT_CONTRACT.md").read_bytes()
                ),
            }
        ],
    )
    # Fix inventory digest for non-empty applicable, then re-sign payload.
    from opsx_conflict.hashutil import sha256_canonical
    from authority_test_helpers import sign_declaration

    payload = decl["payload"]
    payload["authority_inventory_digest"] = sha256_canonical(
        [
            {
                "path": "openspec/policies/OPSX_ROOT_CONTRACT.md",
                "role": "contract",
                "sha256": payload["applicable_authorities"][0]["sha256"],
            }
        ]
    )
    decl = sign_declaration(
        payload,
        issuer_private_key=bound["issuer_private_key"],
        issuer_key_id=bound["issuer_key_id"],
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
    assert exc.value.details.get("reason") == "symbols_mismatch"


def test_conflict_markers_in_stage_blob_stop(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Unparsable/conflict-marker stage blob → STOP (not empty symbols)."""
    priv = install_os_trust_pubkey(monkeypatch, tmp_path)
    pin_git_trust(monkeypatch, tmp_path / "state")
    head = init_git_repo(tmp_path)
    bad = b"<<<<<<< ours\ndef a():\n=======\ndef b():\n>>>>>>> theirs\n"
    oid = hash_blob(tmp_path, bad)
    stages = {"app/x.py": {"1": oid, "2": oid, "3": oid}}
    bound = write_signed_producer(tmp_path, monkeypatch, private_key=priv)
    snapshot = make_snapshot(head=head, other=head, stage_blob_oids=stages)
    decl = base_declaration(
        snapshot=snapshot,
        producer_sha=bound["sha256"],
        contracts_digest=bound["contracts"],
        producer_path=bound["path"],
        issuer_private_key=bound["issuer_private_key"],
        stage_blob_oids=stages,
        symbols=[],
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
    assert exc.value.details.get("reason") == "conflict_markers_in_stage_blob"


def test_empty_rename_still_probes_git(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Empty declaration still requires endpoints; missing endpoints STOP."""
    pin_git_trust(monkeypatch, tmp_path / "state")
    init_git_repo(tmp_path)
    with pytest.raises(StopRequired) as exc:
        verify_rename_lineage_evidence(
            tmp_path,
            commit_oids={"head": "", "operation_head": ""},
            conflict_paths=["app/x.py"],
            declared_lineage={},
        )
    assert exc.value.details.get("reason") == "rename_endpoints_missing"


def test_empty_rename_omission_when_rename_exists(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Actual rename + empty declaration → STOP."""
    pin_git_trust(monkeypatch, tmp_path / "state")
    import subprocess

    subprocess.run(["git", "init"], cwd=tmp_path, check=True, capture_output=True)
    subprocess.run(
        ["git", "config", "user.email", "t@t"], cwd=tmp_path, check=True, capture_output=True
    )
    subprocess.run(
        ["git", "config", "user.name", "t"], cwd=tmp_path, check=True, capture_output=True
    )
    (tmp_path / "old.py").write_text("x=1\n", encoding="utf-8")
    subprocess.run(["git", "add", "old.py"], cwd=tmp_path, check=True, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "a"], cwd=tmp_path, check=True, capture_output=True
    )
    head_a = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=tmp_path, text=True
    ).strip()
    subprocess.run(
        ["git", "mv", "old.py", "new.py"], cwd=tmp_path, check=True, capture_output=True
    )
    subprocess.run(
        ["git", "commit", "-m", "rename"], cwd=tmp_path, check=True, capture_output=True
    )
    head_b = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=tmp_path, text=True
    ).strip()
    with pytest.raises(StopRequired) as exc:
        verify_rename_lineage_evidence(
            tmp_path,
            commit_oids={"head": head_a, "operation_head": head_b},
            conflict_paths=["new.py"],
            declared_lineage={},
        )
    assert exc.value.details.get("reason") == "rename_lineage_omitted"


def test_empty_rename_pass_when_no_rename_evidence(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Same commit endpoints + empty lineage → proven PASS."""
    pin_git_trust(monkeypatch, tmp_path / "state")
    head = init_git_repo(tmp_path)
    proof = verify_rename_lineage_evidence(
        tmp_path,
        commit_oids={"head": head, "operation_head": head},
        conflict_paths=["app/x.py"],
        declared_lineage={},
    )
    assert proof["evidence_paths"] == []


def test_git_bind_pre_exec_digest_check(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Bound path replaced after publish fails pre-exec digest verify."""
    monkeypatch.setenv("OPSX_CONFLICT_STATE", str(tmp_path / "state"))
    source = tmp_path / ("git.exe" if os.name == "nt" else "git")
    source.write_bytes(b"trusted-git-bytes-r23")
    digest = sha256_bytes(b"trusted-git-bytes-r23")
    bound = _bind_trusted_git_executable(executable=str(source), digest=digest)
    Path(bound).write_bytes(b"replaced-after-bind")
    with pytest.raises(StopRequired) as exc:
        _verify_bound_executable(path=bound, digest=digest)
    assert exc.value.reason == "GIT_TRUST_BOUND_DIGEST_MISMATCH"


def test_ship_does_not_define_prepare_external_lineage_provenance() -> None:
    """R22-PROCESS-001: ship must not mint unsigned provenance helpers."""
    src = (
        PACKAGE_ROOT / "scripts" / "ship_review_package.py"
    ).read_text(encoding="utf-8")
    assert "def prepare_external_lineage_provenance" not in src
    assert "restore_host_contracts_from_origin" in src


def test_authority_schema_v3() -> None:
    """Shipped schema is v5; payload requires capability_evidence."""
    schema = json.loads(
        (
            PACKAGE_ROOT / "schemas" / "authority-declaration.schema.json"
        ).read_text(encoding="utf-8")
    )
    assert schema["$id"] == "opsx-resolve-conflict/authority-declaration/v5"
    assert "symbol_extractor_version" in schema["properties"]["payload"]["required"]
    assert "capability_evidence" in schema["properties"]["payload"]["required"]
