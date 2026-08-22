"""R26 authority declaration issuer-key signature authentication tests."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from opsx_conflict.authority import (
    AUTHORITY_DECLARATION_SCHEMA,
    AUTHORITY_DECLARATION_SCHEMA_LEGACY_UNSIGNED,
    canonicalize_declaration_payload,
    verify_external_authority_declaration,
)
from opsx_conflict.errors import StopRequired
from opsx_conflict.hashutil import sha256_bytes

from authority_test_helpers import (
    base_declaration,
    base_declaration_payload,
    hash_blob,
    init_git_repo,
    install_os_trust_pubkey,
    make_snapshot,
    pin_git_trust,
    sign_declaration,
    write_signed_producer,
)


def _setup(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Common fixture: OS trust, git pin, producer, empty-AST stage blob."""
    priv = install_os_trust_pubkey(monkeypatch, tmp_path)
    pin_git_trust(monkeypatch, tmp_path / "state")
    head = init_git_repo(tmp_path)
    oid = hash_blob(tmp_path, b"x = 1\n")
    stages = {"app/x.py": {"1": oid, "2": oid, "3": oid}}
    bound = write_signed_producer(
        tmp_path, monkeypatch, private_key=priv, authorize_none=True
    )
    snapshot = make_snapshot(head=head, other=head, stage_blob_oids=stages)
    return priv, head, stages, bound, snapshot


def _write_decl(tmp_path: Path, decl: dict) -> str:
    """Persist declaration JSON and return relative path."""
    rel = "openspec/changes/c1/authority-declaration.json"
    path = tmp_path / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(decl), encoding="utf-8")
    return rel


def _verify(tmp_path, *, rel, snapshot, head, stages):
    """Call verifier with standard merge fixture args."""
    return verify_external_authority_declaration(
        tmp_path,
        declaration_rel=rel,
        expected_snapshot_id=snapshot,
        operation="merge",
        commit_oids={"head": head, "operation_head": head},
        stage_blob_oids=stages,
        conflict_paths=["app/x.py"],
        source_commit=head,
    )


def test_unsigned_allowed_issuer_stops(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Allowed issuer ID without signature → STOP."""
    _, head, stages, bound, snapshot = _setup(tmp_path, monkeypatch)
    payload = base_declaration_payload(
        snapshot=snapshot,
        producer_sha=bound["sha256"],
        contracts_digest=bound["contracts"],
        producer_path=bound["path"],
        stage_blob_oids=stages,
        head=head,
        other=head,
    )
    envelope = {
        "schema": AUTHORITY_DECLARATION_SCHEMA,
        "payload": payload,
        "issuer_key_id": bound["issuer_key_id"],
        # missing signature
    }
    rel = _write_decl(tmp_path, envelope)
    with pytest.raises(StopRequired) as exc:
        _verify(tmp_path, rel=rel, snapshot=snapshot, head=head, stages=stages)
    assert exc.value.details.get("reason") == "declaration_signature_missing"


def test_unknown_issuer_stops(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Unknown issuer ID → STOP."""
    _, head, stages, bound, snapshot = _setup(tmp_path, monkeypatch)
    decl = base_declaration(
        snapshot=snapshot,
        producer_sha=bound["sha256"],
        contracts_digest=bound["contracts"],
        producer_path=bound["path"],
        issuer_private_key=bound["issuer_private_key"],
        stage_blob_oids=stages,
        head=head,
        other=head,
        issuer_id="not-an-allowed-issuer",
    )
    rel = _write_decl(tmp_path, decl)
    with pytest.raises(StopRequired) as exc:
        _verify(tmp_path, rel=rel, snapshot=snapshot, head=head, stages=stages)
    assert exc.value.details.get("reason") == "unknown_issuer"


def test_unknown_issuer_key_id_stops(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Unknown issuer key ID → STOP."""
    _, head, stages, bound, snapshot = _setup(tmp_path, monkeypatch)
    decl = base_declaration(
        snapshot=snapshot,
        producer_sha=bound["sha256"],
        contracts_digest=bound["contracts"],
        producer_path=bound["path"],
        issuer_private_key=bound["issuer_private_key"],
        issuer_key_id="wrong-key-id",
        stage_blob_oids=stages,
        head=head,
        other=head,
    )
    rel = _write_decl(tmp_path, decl)
    with pytest.raises(StopRequired) as exc:
        _verify(tmp_path, rel=rel, snapshot=snapshot, head=head, stages=stages)
    assert exc.value.details.get("reason") == "unknown_issuer_key_id"


def test_signature_from_other_allowed_issuer_key_stops(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Signature by another key (not bound to issuer) → STOP."""
    os_priv = install_os_trust_pubkey(monkeypatch, tmp_path)
    pin_git_trust(monkeypatch, tmp_path / "state")
    head = init_git_repo(tmp_path)
    oid = hash_blob(tmp_path, b"x = 1\n")
    stages = {"app/x.py": {"1": oid, "2": oid, "3": oid}}
    issuer_a = Ed25519PrivateKey.generate()
    issuer_b = Ed25519PrivateKey.generate()
    bound = write_signed_producer(
        tmp_path,
        monkeypatch,
        private_key=os_priv,
        issuer_private_key=issuer_a,
        authorize_none=True,
    )
    snapshot = make_snapshot(head=head, other=head, stage_blob_oids=stages)
    payload = base_declaration_payload(
        snapshot=snapshot,
        producer_sha=bound["sha256"],
        contracts_digest=bound["contracts"],
        producer_path=bound["path"],
        stage_blob_oids=stages,
        head=head,
        other=head,
    )
    # Sign with unbound key B while claiming issuer A's key_id.
    decl = sign_declaration(
        payload, issuer_private_key=issuer_b, issuer_key_id=bound["issuer_key_id"]
    )
    rel = _write_decl(tmp_path, decl)
    with pytest.raises(StopRequired) as exc:
        _verify(tmp_path, rel=rel, snapshot=snapshot, head=head, stages=stages)
    assert exc.value.details.get("reason") == "declaration_signature_invalid"
    assert "traceback" not in str(exc.value).lower()


def test_tampered_none_applicable_stops(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Changing none_applicable after signing → STOP."""
    _, head, stages, bound, snapshot = _setup(tmp_path, monkeypatch)
    decl = base_declaration(
        snapshot=snapshot,
        producer_sha=bound["sha256"],
        contracts_digest=bound["contracts"],
        producer_path=bound["path"],
        issuer_private_key=bound["issuer_private_key"],
        stage_blob_oids=stages,
        head=head,
        other=head,
        none_applicable=True,
    )
    decl["payload"]["none_applicable"] = False
    rel = _write_decl(tmp_path, decl)
    with pytest.raises(StopRequired) as exc:
        _verify(tmp_path, rel=rel, snapshot=snapshot, head=head, stages=stages)
    assert exc.value.details.get("reason") == "declaration_signature_invalid"


def test_tampered_capabilities_stops(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Changing capabilities after signing → STOP."""
    _, head, stages, bound, snapshot = _setup(tmp_path, monkeypatch)
    decl = base_declaration(
        snapshot=snapshot,
        producer_sha=bound["sha256"],
        contracts_digest=bound["contracts"],
        producer_path=bound["path"],
        issuer_private_key=bound["issuer_private_key"],
        stage_blob_oids=stages,
        head=head,
        other=head,
    )
    decl["payload"]["capabilities"] = ["invented"]
    rel = _write_decl(tmp_path, decl)
    with pytest.raises(StopRequired) as exc:
        _verify(tmp_path, rel=rel, snapshot=snapshot, head=head, stages=stages)
    assert exc.value.details.get("reason") == "declaration_signature_invalid"


def test_tampered_applicable_authorities_stops(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Changing applicable_authorities after signing → STOP."""
    _, head, stages, bound, snapshot = _setup(tmp_path, monkeypatch)
    decl = base_declaration(
        snapshot=snapshot,
        producer_sha=bound["sha256"],
        contracts_digest=bound["contracts"],
        producer_path=bound["path"],
        issuer_private_key=bound["issuer_private_key"],
        stage_blob_oids=stages,
        head=head,
        other=head,
    )
    decl["payload"]["applicable_authorities"] = [
        {
            "path": "openspec/policies/OPSX_ROOT_CONTRACT.md",
            "role": "contract",
            "sha256": "a" * 64,
        }
    ]
    rel = _write_decl(tmp_path, decl)
    with pytest.raises(StopRequired) as exc:
        _verify(tmp_path, rel=rel, snapshot=snapshot, head=head, stages=stages)
    assert exc.value.details.get("reason") == "declaration_signature_invalid"


def test_tampered_operation_or_oids_stops(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Changing operation / commit / stage OID after signing → STOP."""
    _, head, stages, bound, snapshot = _setup(tmp_path, monkeypatch)
    decl = base_declaration(
        snapshot=snapshot,
        producer_sha=bound["sha256"],
        contracts_digest=bound["contracts"],
        producer_path=bound["path"],
        issuer_private_key=bound["issuer_private_key"],
        stage_blob_oids=stages,
        head=head,
        other=head,
    )
    decl["payload"]["operation"] = "rebase"
    rel = _write_decl(tmp_path, decl)
    with pytest.raises(StopRequired) as exc:
        _verify(tmp_path, rel=rel, snapshot=snapshot, head=head, stages=stages)
    assert exc.value.details.get("reason") == "declaration_signature_invalid"


def test_different_snapshot_stops(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Declaration signed for another conflict_snapshot_id → STOP."""
    _, head, stages, bound, snapshot = _setup(tmp_path, monkeypatch)
    decl = base_declaration(
        snapshot="0" * 64,
        producer_sha=bound["sha256"],
        contracts_digest=bound["contracts"],
        producer_path=bound["path"],
        issuer_private_key=bound["issuer_private_key"],
        stage_blob_oids=stages,
        head=head,
        other=head,
    )
    rel = _write_decl(tmp_path, decl)
    with pytest.raises(StopRequired) as exc:
        _verify(tmp_path, rel=rel, snapshot=snapshot, head=head, stages=stages)
    assert exc.value.details.get("reason") == "conflict_snapshot_mismatch"


def test_different_stage_oid_stops(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Signed declaration with wrong stage OID vs live snapshot → STOP."""
    _, head, stages, bound, snapshot = _setup(tmp_path, monkeypatch)
    wrong_stages = {"app/x.py": {"1": "1" * 40, "2": "1" * 40, "3": "1" * 40}}
    wrong_snapshot = make_snapshot(
        head=head, other=head, stage_blob_oids=wrong_stages
    )
    decl = base_declaration(
        snapshot=wrong_snapshot,
        producer_sha=bound["sha256"],
        contracts_digest=bound["contracts"],
        producer_path=bound["path"],
        issuer_private_key=bound["issuer_private_key"],
        stage_blob_oids=wrong_stages,
        head=head,
        other=head,
    )
    rel = _write_decl(tmp_path, decl)
    with pytest.raises(StopRequired) as exc:
        _verify(tmp_path, rel=rel, snapshot=snapshot, head=head, stages=stages)
    assert exc.value.details.get("reason") in {
        "conflict_snapshot_mismatch",
        "stage_blob_oid_mismatch",
    }


def test_producer_contract_digest_mismatch_stops(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Declaration with other producer_contract_sha256 → STOP."""
    _, head, stages, bound, snapshot = _setup(tmp_path, monkeypatch)
    decl = base_declaration(
        snapshot=snapshot,
        producer_sha="f" * 64,
        contracts_digest=bound["contracts"],
        producer_path=bound["path"],
        issuer_private_key=bound["issuer_private_key"],
        stage_blob_oids=stages,
        head=head,
        other=head,
    )
    rel = _write_decl(tmp_path, decl)
    with pytest.raises(StopRequired) as exc:
        _verify(tmp_path, rel=rel, snapshot=snapshot, head=head, stages=stages)
    assert exc.value.details.get("reason") == "producer_contract_sha256_mismatch"


def test_valid_signed_declaration_passes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Correct issuer-key signature + matching snapshot continues mechanical checks."""
    _, head, stages, bound, snapshot = _setup(tmp_path, monkeypatch)
    decl = base_declaration(
        snapshot=snapshot,
        producer_sha=bound["sha256"],
        contracts_digest=bound["contracts"],
        producer_path=bound["path"],
        issuer_private_key=bound["issuer_private_key"],
        stage_blob_oids=stages,
        head=head,
        other=head,
    )
    rel = _write_decl(tmp_path, decl)
    proof = _verify(tmp_path, rel=rel, snapshot=snapshot, head=head, stages=stages)
    assert proof["none_applicable"] is True
    assert proof["issuer"] == "opsx-authority-issuer"
    assert proof["issuer_key_id"] == bound["issuer_key_id"]
    assert len(proof["declaration_canonical_sha256"]) == 64


def test_legacy_unsigned_v3_schema_rejected(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Legacy unsigned v3 flat declaration → STOP (no auto-upgrade)."""
    _, head, stages, bound, snapshot = _setup(tmp_path, monkeypatch)
    legacy = base_declaration_payload(
        snapshot=snapshot,
        producer_sha=bound["sha256"],
        contracts_digest=bound["contracts"],
        producer_path=bound["path"],
        stage_blob_oids=stages,
        head=head,
        other=head,
    )
    legacy["schema"] = AUTHORITY_DECLARATION_SCHEMA_LEGACY_UNSIGNED
    rel = _write_decl(tmp_path, legacy)
    with pytest.raises(StopRequired) as exc:
        _verify(tmp_path, rel=rel, snapshot=snapshot, head=head, stages=stages)
    assert exc.value.details.get("reason") == "legacy_unsigned_declaration_rejected"


def test_canonicalization_deterministic_across_insertion_order() -> None:
    """Canonical bytes ignore dict insertion order."""
    a = {
        "schema": AUTHORITY_DECLARATION_SCHEMA,
        "none_applicable": True,
        "paths": ["a.py"],
        "conflict_snapshot_id": "s" * 64,
        "source_commit": "a" * 40,
        "operation": "merge",
        "conflicting_commit_oids": {"head": "a" * 40, "operation_head": "b" * 40},
        "stage_blob_oids": {"a.py": {"1": "1" * 40}},
        "rename_lineage": {},
        "symbols": [],
        "capabilities": [],
        "capability_evidence": {
            "schema": "opsx-resolve-conflict/capability-evidence/v1",
            "classifier_id": "c",
            "classifier_version": "1",
            "conflict_snapshot_id": "s" * 64,
            "stage_coverage": [
                {"path": "a.py", "stage": "1", "blob_oid": "1" * 40}
            ],
            "capabilities": [],
            "analysis_complete": True,
            "unknown_targets": [],
            "observations": [],
        },
        "symbol_extractor_version": "opsx-symbol-extractor/v1",
        "contracts_inventory_digest": "c" * 64,
        "authority_inventory_digest": "d" * 64,
        "producer_contract_sha256": "e" * 64,
        "issuer": {"id": "i", "contract_path": "p"},
        "applicable_authorities": [],
    }
    b = dict(reversed(list(a.items())))
    assert canonicalize_declaration_payload(a) == canonicalize_declaration_payload(b)
    assert sha256_bytes(canonicalize_declaration_payload(a)) == sha256_bytes(
        canonicalize_declaration_payload(b)
    )


def test_bare_issuer_string_in_producer_rejected(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Producer with bare issuer strings cannot authenticate declarations."""
    import binascii

    from opsx_conflict.authority import (
        AUTHORITY_ROOT_DIGEST_ENV,
        AUTHORITY_ROOT_PATH_ENV,
        AUTHORITY_ROOT_SIGNATURE_ENV,
    )

    priv = install_os_trust_pubkey(monkeypatch, tmp_path)
    pin_git_trust(monkeypatch, tmp_path / "state")
    head = init_git_repo(tmp_path)
    oid = hash_blob(tmp_path, b"x = 1\n")
    stages = {"app/x.py": {"1": oid, "2": oid, "3": oid}}
    rel = ".cursor/opsx-authority-producers.json"
    root = "openspec/policies/OPSX_ROOT_CONTRACT.md"
    (tmp_path / root).parent.mkdir(parents=True, exist_ok=True)
    (tmp_path / root).write_text("# root\n", encoding="utf-8")
    payload = {
        "issuers": ["opsx-authority-issuer"],
        "authoritative_roots": [root],
        "authorize_none_applicable": True,
        "capability_bindings": [],
    }
    raw = (json.dumps(payload) + "\n").encode("utf-8")
    (tmp_path / rel).parent.mkdir(parents=True, exist_ok=True)
    (tmp_path / rel).write_bytes(raw)
    monkeypatch.setenv(AUTHORITY_ROOT_PATH_ENV, rel)
    monkeypatch.setenv(AUTHORITY_ROOT_DIGEST_ENV, sha256_bytes(raw))
    monkeypatch.setenv(
        AUTHORITY_ROOT_SIGNATURE_ENV,
        binascii.hexlify(priv.sign(raw)).decode("ascii"),
    )
    snapshot = make_snapshot(head=head, other=head, stage_blob_oids=stages)
    decl = {
        "schema": AUTHORITY_DECLARATION_SCHEMA,
        "payload": base_declaration_payload(
            snapshot=snapshot,
            producer_sha=sha256_bytes(raw),
            contracts_digest="0" * 64,
            producer_path=rel,
            stage_blob_oids=stages,
            head=head,
            other=head,
        ),
        "issuer_key_id": "k",
        "signature": "a" * 128,
    }
    rel_d = _write_decl(tmp_path, decl)
    with pytest.raises(StopRequired) as exc:
        _verify(tmp_path, rel=rel_d, snapshot=snapshot, head=head, stages=stages)
    assert exc.value.details.get("reason") == "issuer_missing_key_binding"
