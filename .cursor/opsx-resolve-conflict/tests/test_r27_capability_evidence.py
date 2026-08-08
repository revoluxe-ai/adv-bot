"""R27: authenticated capability evidence (R25-HIGH-002).

Local AST symbol→binding mapping is diagnostic only and cannot prove
completeness or ``none_applicable``. Completeness requires signed evidence
from a producer-authorized ``capability_attestor``.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from authority_test_helpers import (
    base_declaration,
    base_declaration_payload,
    build_capability_evidence,
    hash_blob,
    init_git_repo,
    install_os_trust_pubkey,
    make_snapshot,
    pin_git_trust,
    sign_declaration,
    write_signed_producer,
)
from opsx_conflict.authority import (
    AUTHORITY_DECLARATION_SCHEMA_LEGACY_V4,
    CAPABILITY_ATTESTOR_ROLE,
    CAPABILITY_EVIDENCE_SCHEMA,
    _extract_symbols_from_source,
    verify_external_authority_declaration,
)
from opsx_conflict.errors import StopRequired
from opsx_conflict.hashutil import sha256_bytes


def _setup(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    *,
    source: bytes = b"def reconcile(client):\n    client.delete_user()\n",
    authorize_none: bool = True,
    issuer_roles: list[str] | None = None,
    capability_bindings: list[dict[str, str]] | None = None,
) -> tuple[Ed25519PrivateKey, str, dict, dict, str, list[str]]:
    """Create signed producer + conflict stage fixture."""
    priv = install_os_trust_pubkey(monkeypatch, tmp_path)
    pin_git_trust(monkeypatch, tmp_path / "state")
    head = init_git_repo(tmp_path)
    oid = hash_blob(tmp_path, source)
    stages = {"app/x.py": {"1": oid, "2": oid, "3": oid}}
    bound = write_signed_producer(
        tmp_path,
        monkeypatch,
        private_key=priv,
        authorize_none=authorize_none,
        issuer_roles=issuer_roles,
        capability_bindings=capability_bindings or [],
    )
    snapshot = make_snapshot(head=head, other=head, stage_blob_oids=stages)
    symbols = _local_symbols(source)
    return priv, head, stages, bound, snapshot, symbols


def _write_decl(tmp_path: Path, decl: dict) -> str:
    """Persist declaration and return relative path."""
    rel = "openspec/changes/c1/authority-declaration.json"
    path = tmp_path / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(decl), encoding="utf-8")
    return rel


def _verify(
    tmp_path: Path,
    *,
    rel: str,
    snapshot: str,
    head: str,
    stages: dict,
) -> dict:
    """Run authority verification for fixture declaration."""
    return verify_external_authority_declaration(
        tmp_path,
        declaration_rel=rel,
        expected_snapshot_id=snapshot,
        operation="merge",
        commit_oids={"head": head, "operation_head": head},
        stage_blob_oids=stages,
        conflict_paths=sorted(stages),
        source_commit=head,
    )


def _local_symbols(source: bytes) -> list[str]:
    """Mechanical symbols only (diagnostic; deliberately incomplete)."""
    return sorted(
        _extract_symbols_from_source(
            source.decode("utf-8"),
            blob_oid="fixture",
            path="app/x.py",
        )
    )


def test_method_call_without_evidence_stops(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """``client.delete_user()`` local symbols alone must not PASS empty caps."""
    source = b"def reconcile(client):\n    client.delete_user()\n"
    _, head, stages, bound, snapshot, symbols = _setup(
        tmp_path, monkeypatch, source=source
    )
    assert symbols == ["reconcile"]
    payload = base_declaration_payload(
        snapshot=snapshot,
        producer_sha=bound["sha256"],
        contracts_digest=bound["contracts"],
        producer_path=bound["path"],
        stage_blob_oids=stages,
        symbols=symbols,
        capabilities=[],
        head=head,
        other=head,
        omit_capability_evidence=True,
    )
    with pytest.raises(StopRequired) as exc:
        from opsx_conflict.authority import canonicalize_declaration_payload

        canonicalize_declaration_payload(payload)
    assert exc.value.details.get("reason") == "declaration_payload_missing_field"
    assert "capability_evidence" in (exc.value.details.get("fields") or [])


def test_missing_capability_evidence_stops(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Signed-looking payload without capability_evidence → STOP."""
    _, head, stages, bound, snapshot, symbols = _setup(tmp_path, monkeypatch)
    payload = base_declaration_payload(
        snapshot=snapshot,
        producer_sha=bound["sha256"],
        contracts_digest=bound["contracts"],
        producer_path=bound["path"],
        stage_blob_oids=stages,
        symbols=symbols,
        head=head,
        other=head,
        omit_capability_evidence=True,
    )
    # Inject null evidence after building other fields to exercise verifier.
    payload["capability_evidence"] = None
    decl = sign_declaration(
        payload,
        issuer_private_key=bound["issuer_private_key"],
        issuer_key_id=bound["issuer_key_id"],
    )
    rel = _write_decl(tmp_path, decl)
    with pytest.raises(StopRequired) as exc:
        _verify(tmp_path, rel=rel, snapshot=snapshot, head=head, stages=stages)
    assert exc.value.details.get("reason") == "capability_evidence_missing"


def test_issuer_without_capability_attestor_role_stops(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Issuer lacking capability_attestor role cannot attest completeness."""
    _, head, stages, bound, snapshot, symbols = _setup(
        tmp_path, monkeypatch, issuer_roles=["declaration_signer"]
    )
    decl = base_declaration(
        snapshot=snapshot,
        producer_sha=bound["sha256"],
        contracts_digest=bound["contracts"],
        producer_path=bound["path"],
        issuer_private_key=bound["issuer_private_key"],
        stage_blob_oids=stages,
        symbols=symbols,
        head=head,
        other=head,
    )
    rel = _write_decl(tmp_path, decl)
    with pytest.raises(StopRequired) as exc:
        _verify(tmp_path, rel=rel, snapshot=snapshot, head=head, stages=stages)
    assert exc.value.details.get("reason") == "issuer_not_capability_attestor"
    assert CAPABILITY_ATTESTOR_ROLE == "capability_attestor"


def test_analysis_complete_false_stops(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """analysis_complete=false → STOP."""
    _, head, stages, bound, snapshot, symbols = _setup(tmp_path, monkeypatch)
    evidence = build_capability_evidence(
        snapshot=snapshot,
        stage_blob_oids=stages,
        capabilities=[],
        analysis_complete=False,
    )
    decl = base_declaration(
        snapshot=snapshot,
        producer_sha=bound["sha256"],
        contracts_digest=bound["contracts"],
        producer_path=bound["path"],
        issuer_private_key=bound["issuer_private_key"],
        stage_blob_oids=stages,
        symbols=symbols,
        capability_evidence=evidence,
        head=head,
        other=head,
    )
    rel = _write_decl(tmp_path, decl)
    with pytest.raises(StopRequired) as exc:
        _verify(tmp_path, rel=rel, snapshot=snapshot, head=head, stages=stages)
    assert exc.value.details.get("reason") == "capability_analysis_incomplete"


def test_unknown_targets_nonempty_stops(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Non-empty unknown_targets → STOP even with declared capabilities."""
    _, head, stages, bound, snapshot, symbols = _setup(tmp_path, monkeypatch)
    evidence = build_capability_evidence(
        snapshot=snapshot,
        stage_blob_oids=stages,
        capabilities=["auth"],
        unknown_targets=["client.delete_user"],
        observations=[
            {
                "kind": "unknown_target",
                "target": "client.delete_user",
                "path": "app/x.py",
                "stage": "2",
            }
        ],
    )
    decl = base_declaration(
        snapshot=snapshot,
        producer_sha=bound["sha256"],
        contracts_digest=bound["contracts"],
        producer_path=bound["path"],
        issuer_private_key=bound["issuer_private_key"],
        stage_blob_oids=stages,
        symbols=symbols,
        capabilities=["auth"],
        capability_evidence=evidence,
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
    from opsx_conflict.hashutil import sha256_canonical

    payload = decl["payload"]
    payload["authority_inventory_digest"] = sha256_canonical(
        [
            {
                "path": row["path"],
                "role": row["role"],
                "sha256": row["sha256"],
            }
            for row in payload["applicable_authorities"]
        ]
    )
    decl = sign_declaration(
        payload,
        issuer_private_key=bound["issuer_private_key"],
        issuer_key_id=bound["issuer_key_id"],
    )
    rel = _write_decl(tmp_path, decl)
    with pytest.raises(StopRequired) as exc:
        _verify(tmp_path, rel=rel, snapshot=snapshot, head=head, stages=stages)
    assert exc.value.details.get("reason") == "capability_unknown_targets_present"


@pytest.mark.parametrize(
    "drop_stage",
    ["1", "2", "3"],
)
def test_missing_stage_coverage_row_stops(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, drop_stage: str
) -> None:
    """Skipping any stage 1/2/3 coverage row → STOP."""
    _, head, stages, bound, snapshot, symbols = _setup(tmp_path, monkeypatch)
    coverage = build_capability_evidence(
        snapshot=snapshot, stage_blob_oids=stages, capabilities=[]
    )["stage_coverage"]
    coverage = [row for row in coverage if row["stage"] != drop_stage]
    evidence = build_capability_evidence(
        snapshot=snapshot,
        stage_blob_oids=stages,
        capabilities=[],
        stage_coverage=coverage,
    )
    decl = base_declaration(
        snapshot=snapshot,
        producer_sha=bound["sha256"],
        contracts_digest=bound["contracts"],
        producer_path=bound["path"],
        issuer_private_key=bound["issuer_private_key"],
        stage_blob_oids=stages,
        symbols=symbols,
        capability_evidence=evidence,
        head=head,
        other=head,
    )
    rel = _write_decl(tmp_path, decl)
    with pytest.raises(StopRequired) as exc:
        _verify(tmp_path, rel=rel, snapshot=snapshot, head=head, stages=stages)
    assert exc.value.details.get("reason") == "capability_stage_coverage_mismatch"


def test_extra_coverage_row_stops(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Extra stage_coverage row → STOP."""
    _, head, stages, bound, snapshot, symbols = _setup(tmp_path, monkeypatch)
    coverage = build_capability_evidence(
        snapshot=snapshot, stage_blob_oids=stages, capabilities=[]
    )["stage_coverage"]
    coverage = list(coverage) + [
        {"path": "app/x.py", "stage": "9", "blob_oid": "f" * 40}
    ]
    evidence = build_capability_evidence(
        snapshot=snapshot,
        stage_blob_oids=stages,
        capabilities=[],
        stage_coverage=coverage,
    )
    decl = base_declaration(
        snapshot=snapshot,
        producer_sha=bound["sha256"],
        contracts_digest=bound["contracts"],
        producer_path=bound["path"],
        issuer_private_key=bound["issuer_private_key"],
        stage_blob_oids=stages,
        symbols=symbols,
        capability_evidence=evidence,
        head=head,
        other=head,
    )
    rel = _write_decl(tmp_path, decl)
    with pytest.raises(StopRequired) as exc:
        _verify(tmp_path, rel=rel, snapshot=snapshot, head=head, stages=stages)
    assert exc.value.details.get("reason") == "capability_stage_coverage_mismatch"


def test_wrong_blob_oid_in_coverage_stops(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Wrong path/stage/blob_oid in coverage → STOP."""
    _, head, stages, bound, snapshot, symbols = _setup(tmp_path, monkeypatch)
    coverage = build_capability_evidence(
        snapshot=snapshot, stage_blob_oids=stages, capabilities=[]
    )["stage_coverage"]
    coverage = [
        {**row, "blob_oid": "0" * 40} if row["stage"] == "2" else row
        for row in coverage
    ]
    evidence = build_capability_evidence(
        snapshot=snapshot,
        stage_blob_oids=stages,
        capabilities=[],
        stage_coverage=coverage,
    )
    decl = base_declaration(
        snapshot=snapshot,
        producer_sha=bound["sha256"],
        contracts_digest=bound["contracts"],
        producer_path=bound["path"],
        issuer_private_key=bound["issuer_private_key"],
        stage_blob_oids=stages,
        symbols=symbols,
        capability_evidence=evidence,
        head=head,
        other=head,
    )
    rel = _write_decl(tmp_path, decl)
    with pytest.raises(StopRequired) as exc:
        _verify(tmp_path, rel=rel, snapshot=snapshot, head=head, stages=stages)
    assert exc.value.details.get("reason") == "capability_stage_coverage_mismatch"


def test_evidence_snapshot_mismatch_stops(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Evidence conflict_snapshot_id must match declaration/expected."""
    _, head, stages, bound, snapshot, symbols = _setup(tmp_path, monkeypatch)
    evidence = build_capability_evidence(
        snapshot="f" * 64,
        stage_blob_oids=stages,
        capabilities=[],
    )
    decl = base_declaration(
        snapshot=snapshot,
        producer_sha=bound["sha256"],
        contracts_digest=bound["contracts"],
        producer_path=bound["path"],
        issuer_private_key=bound["issuer_private_key"],
        stage_blob_oids=stages,
        symbols=symbols,
        capability_evidence=evidence,
        head=head,
        other=head,
    )
    rel = _write_decl(tmp_path, decl)
    with pytest.raises(StopRequired) as exc:
        _verify(tmp_path, rel=rel, snapshot=snapshot, head=head, stages=stages)
    assert exc.value.details.get("reason") == "capability_evidence_snapshot_mismatch"


def test_evidence_capabilities_mismatch_stops(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Evidence capability set must equal declaration capabilities."""
    _, head, stages, bound, snapshot, symbols = _setup(tmp_path, monkeypatch)
    evidence = build_capability_evidence(
        snapshot=snapshot,
        stage_blob_oids=stages,
        capabilities=["auth"],
    )
    decl = base_declaration(
        snapshot=snapshot,
        producer_sha=bound["sha256"],
        contracts_digest=bound["contracts"],
        producer_path=bound["path"],
        issuer_private_key=bound["issuer_private_key"],
        stage_blob_oids=stages,
        symbols=symbols,
        capabilities=[],
        capability_evidence=evidence,
        head=head,
        other=head,
    )
    rel = _write_decl(tmp_path, decl)
    with pytest.raises(StopRequired) as exc:
        _verify(tmp_path, rel=rel, snapshot=snapshot, head=head, stages=stages)
    assert (
        exc.value.details.get("reason") == "capability_evidence_capabilities_mismatch"
    )


def test_tampered_capability_evidence_signature_stops(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Mutating capability_evidence after signature → signature STOP."""
    _, head, stages, bound, snapshot, symbols = _setup(tmp_path, monkeypatch)
    decl = base_declaration(
        snapshot=snapshot,
        producer_sha=bound["sha256"],
        contracts_digest=bound["contracts"],
        producer_path=bound["path"],
        issuer_private_key=bound["issuer_private_key"],
        stage_blob_oids=stages,
        symbols=symbols,
        head=head,
        other=head,
    )
    decl["payload"]["capability_evidence"]["observations"] = [
        {"kind": "tamper", "note": "post-sign"}
    ]
    rel = _write_decl(tmp_path, decl)
    with pytest.raises(StopRequired) as exc:
        _verify(tmp_path, rel=rel, snapshot=snapshot, head=head, stages=stages)
    assert exc.value.details.get("reason") in {
        "declaration_signature_invalid",
        "declaration_signature_verify_failed",
    }


def test_legacy_v4_declaration_rejected(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """v4 schema has no silent compatibility path."""
    _, head, stages, bound, snapshot, symbols = _setup(tmp_path, monkeypatch)
    decl = base_declaration(
        snapshot=snapshot,
        producer_sha=bound["sha256"],
        contracts_digest=bound["contracts"],
        producer_path=bound["path"],
        issuer_private_key=bound["issuer_private_key"],
        stage_blob_oids=stages,
        symbols=symbols,
        head=head,
        other=head,
    )
    decl["schema"] = AUTHORITY_DECLARATION_SCHEMA_LEGACY_V4
    decl["payload"]["schema"] = AUTHORITY_DECLARATION_SCHEMA_LEGACY_V4
    rel = _write_decl(tmp_path, decl)
    with pytest.raises(StopRequired) as exc:
        _verify(tmp_path, rel=rel, snapshot=snapshot, head=head, stages=stages)
    assert exc.value.details.get("reason") == "legacy_v4_declaration_rejected"


def test_valid_nonempty_capability_evidence_passes_gate(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Complete signed non-empty evidence passes capability gate."""
    source = b"def reconcile(client):\n    client.delete_user()\n"
    _, head, stages, bound, snapshot, symbols = _setup(tmp_path, monkeypatch, source=source)
    symbols = _local_symbols(source)
    assert symbols == ["reconcile"]
    evidence = build_capability_evidence(
        snapshot=snapshot,
        stage_blob_oids=stages,
        capabilities=["auth"],
        observations=[
            {
                "kind": "method_call",
                "target": "client.delete_user",
                "path": "app/x.py",
                "stage": "2",
                "capability": "auth",
            },
            {
                "kind": "aliased_import",
                "target": "import client as c",
                "path": "app/x.py",
                "stage": "1",
            },
            {
                "kind": "module_api_call",
                "target": "client.delete_user",
                "path": "app/x.py",
                "stage": "3",
            },
            {
                "kind": "decorator",
                "target": "@requires_auth",
                "path": "app/x.py",
                "stage": "2",
            },
            {
                "kind": "inherited_api",
                "target": "BaseClient.delete_user",
                "path": "app/x.py",
                "stage": "1",
            },
            {
                "kind": "dynamic_dispatch",
                "target": "getattr(client, name)()",
                "path": "app/x.py",
                "stage": "3",
            },
        ],
    )
    root = "openspec/policies/OPSX_ROOT_CONTRACT.md"
    applicable = [
        {
            "path": root,
            "role": "contract",
            "sha256": sha256_bytes((tmp_path / root).read_bytes()),
        }
    ]
    decl = base_declaration(
        snapshot=snapshot,
        producer_sha=bound["sha256"],
        contracts_digest=bound["contracts"],
        producer_path=bound["path"],
        issuer_private_key=bound["issuer_private_key"],
        stage_blob_oids=stages,
        symbols=symbols,
        capabilities=["auth"],
        capability_evidence=evidence,
        head=head,
        other=head,
        none_applicable=False,
        applicable=applicable,
    )
    from opsx_conflict.hashutil import sha256_canonical

    payload = decl["payload"]
    payload["authority_inventory_digest"] = sha256_canonical(
        [{"path": r["path"], "role": r["role"], "sha256": r["sha256"]} for r in applicable]
    )
    decl = sign_declaration(
        payload,
        issuer_private_key=bound["issuer_private_key"],
        issuer_key_id=bound["issuer_key_id"],
    )
    rel = _write_decl(tmp_path, decl)
    proof = _verify(tmp_path, rel=rel, snapshot=snapshot, head=head, stages=stages)
    assert proof["none_applicable"] is False
    assert proof["capabilities"] == ["auth"]


def test_valid_none_applicable_with_empty_evidence(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Empty complete evidence + producer auth allows none_applicable."""
    source = b"x = 1\n"
    _, head, stages, bound, snapshot, symbols = _setup(
        tmp_path, monkeypatch, source=source, authorize_none=True
    )
    symbols = _local_symbols(source)
    evidence = build_capability_evidence(
        snapshot=snapshot,
        stage_blob_oids=stages,
        capabilities=[],
        observations=[{"kind": "no_capability_surface", "path": "app/x.py"}],
    )
    decl = base_declaration(
        snapshot=snapshot,
        producer_sha=bound["sha256"],
        contracts_digest=bound["contracts"],
        producer_path=bound["path"],
        issuer_private_key=bound["issuer_private_key"],
        stage_blob_oids=stages,
        symbols=symbols,
        capabilities=[],
        capability_evidence=evidence,
        head=head,
        other=head,
        none_applicable=True,
    )
    rel = _write_decl(tmp_path, decl)
    proof = _verify(tmp_path, rel=rel, snapshot=snapshot, head=head, stages=stages)
    assert proof["none_applicable"] is True
    assert proof["capabilities"] == []


def test_local_ast_empty_caps_insufficient_for_none_applicable(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Local AST empty mapping cannot authorize none_applicable without evidence."""
    source = b"def reconcile(client):\n    client.delete_user()\n"
    _, head, stages, bound, snapshot, symbols = _setup(tmp_path, monkeypatch, source=source)
    symbols = _local_symbols(source)
    assert symbols == ["reconcile"]
    # Evidence claims complete empty — that is attestor claim; here we prove
    # that omitting complete analysis (unknown target listed) STOPs instead of
    # accepting local-empty bindings as none_applicable.
    evidence = build_capability_evidence(
        snapshot=snapshot,
        stage_blob_oids=stages,
        capabilities=[],
        unknown_targets=["client.delete_user"],
        observations=[
            {
                "kind": "unknown_target",
                "target": "client.delete_user",
                "path": "app/x.py",
                "stage": "2",
            }
        ],
    )
    decl = base_declaration(
        snapshot=snapshot,
        producer_sha=bound["sha256"],
        contracts_digest=bound["contracts"],
        producer_path=bound["path"],
        issuer_private_key=bound["issuer_private_key"],
        stage_blob_oids=stages,
        symbols=symbols,
        capabilities=[],
        capability_evidence=evidence,
        head=head,
        other=head,
        none_applicable=True,
    )
    rel = _write_decl(tmp_path, decl)
    with pytest.raises(StopRequired) as exc:
        _verify(tmp_path, rel=rel, snapshot=snapshot, head=head, stages=stages)
    assert exc.value.details.get("reason") == "capability_unknown_targets_present"


def test_stage2_only_observation_still_requires_full_coverage(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Target only in stage 2 still needs stage 1/2/3 coverage rows."""
    side1 = b"def reconcile():\n    return 0\n"
    side2 = b"def reconcile(client):\n    client.delete_user()\n"
    side3 = b"def reconcile():\n    return 1\n"
    priv = install_os_trust_pubkey(monkeypatch, tmp_path)
    pin_git_trust(monkeypatch, tmp_path / "state")
    head = init_git_repo(tmp_path)
    stages = {
        "app/x.py": {
            "1": hash_blob(tmp_path, side1),
            "2": hash_blob(tmp_path, side2),
            "3": hash_blob(tmp_path, side3),
        }
    }
    bound = write_signed_producer(tmp_path, monkeypatch, private_key=priv)
    snapshot = make_snapshot(head=head, other=head, stage_blob_oids=stages)
    from opsx_conflict.authority import recompute_mechanical_symbols_from_stages
    from opsx_conflict.git_typed import TypedGit

    symbols = recompute_mechanical_symbols_from_stages(
        TypedGit(tmp_path),
        conflict_paths=["app/x.py"],
        stage_blob_oids=stages,
    )
    evidence = build_capability_evidence(
        snapshot=snapshot,
        stage_blob_oids=stages,
        capabilities=["auth"],
        observations=[
            {
                "kind": "method_call",
                "target": "client.delete_user",
                "path": "app/x.py",
                "stage": "2",
                "capability": "auth",
            }
        ],
    )
    root = "openspec/policies/OPSX_ROOT_CONTRACT.md"
    applicable = [
        {
            "path": root,
            "role": "contract",
            "sha256": sha256_bytes((tmp_path / root).read_bytes()),
        }
    ]
    decl = base_declaration(
        snapshot=snapshot,
        producer_sha=bound["sha256"],
        contracts_digest=bound["contracts"],
        producer_path=bound["path"],
        issuer_private_key=bound["issuer_private_key"],
        stage_blob_oids=stages,
        symbols=symbols,
        capabilities=["auth"],
        capability_evidence=evidence,
        head=head,
        other=head,
        none_applicable=False,
        applicable=applicable,
    )
    from opsx_conflict.hashutil import sha256_canonical

    payload = decl["payload"]
    payload["authority_inventory_digest"] = sha256_canonical(
        [{"path": r["path"], "role": r["role"], "sha256": r["sha256"]} for r in applicable]
    )
    decl = sign_declaration(
        payload,
        issuer_private_key=bound["issuer_private_key"],
        issuer_key_id=bound["issuer_key_id"],
    )
    rel = _write_decl(tmp_path, decl)
    proof = _verify(tmp_path, rel=rel, snapshot=snapshot, head=head, stages=stages)
    assert proof["capabilities"] == ["auth"]
    assert evidence["schema"] == CAPABILITY_EVIDENCE_SCHEMA
    assert len(evidence["stage_coverage"]) == 3


def test_stage3_only_observation_still_requires_full_coverage(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Target only in stage 3 remains covered by full stage_coverage."""
    side1 = b"def reconcile():\n    pass\n"
    side2 = b"def reconcile():\n    pass\n"
    side3 = b"@audit\ndef reconcile():\n    pass\n"
    priv = install_os_trust_pubkey(monkeypatch, tmp_path)
    pin_git_trust(monkeypatch, tmp_path / "state")
    head = init_git_repo(tmp_path)
    stages = {
        "app/x.py": {
            "1": hash_blob(tmp_path, side1),
            "2": hash_blob(tmp_path, side2),
            "3": hash_blob(tmp_path, side3),
        }
    }
    bound = write_signed_producer(tmp_path, monkeypatch, private_key=priv)
    snapshot = make_snapshot(head=head, other=head, stage_blob_oids=stages)
    from opsx_conflict.authority import recompute_mechanical_symbols_from_stages
    from opsx_conflict.git_typed import TypedGit

    symbols = recompute_mechanical_symbols_from_stages(
        TypedGit(tmp_path),
        conflict_paths=["app/x.py"],
        stage_blob_oids=stages,
    )
    evidence = build_capability_evidence(
        snapshot=snapshot,
        stage_blob_oids=stages,
        capabilities=["audit"],
        observations=[
            {
                "kind": "decorator",
                "target": "@audit",
                "path": "app/x.py",
                "stage": "3",
                "capability": "audit",
            }
        ],
    )
    root = "openspec/policies/OPSX_ROOT_CONTRACT.md"
    applicable = [
        {
            "path": root,
            "role": "contract",
            "sha256": sha256_bytes((tmp_path / root).read_bytes()),
        }
    ]
    decl = base_declaration(
        snapshot=snapshot,
        producer_sha=bound["sha256"],
        contracts_digest=bound["contracts"],
        producer_path=bound["path"],
        issuer_private_key=bound["issuer_private_key"],
        stage_blob_oids=stages,
        symbols=symbols,
        capabilities=["audit"],
        capability_evidence=evidence,
        head=head,
        other=head,
        none_applicable=False,
        applicable=applicable,
    )
    from opsx_conflict.hashutil import sha256_canonical

    payload = decl["payload"]
    payload["authority_inventory_digest"] = sha256_canonical(
        [{"path": r["path"], "role": r["role"], "sha256": r["sha256"]} for r in applicable]
    )
    decl = sign_declaration(
        payload,
        issuer_private_key=bound["issuer_private_key"],
        issuer_key_id=bound["issuer_key_id"],
    )
    rel = _write_decl(tmp_path, decl)
    proof = _verify(tmp_path, rel=rel, snapshot=snapshot, head=head, stages=stages)
    assert proof["capabilities"] == ["audit"]
