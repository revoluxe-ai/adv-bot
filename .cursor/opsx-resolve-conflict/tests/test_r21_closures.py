"""R21 acceptance closures adapted for R23 signed OS trust channel."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from opsx_conflict.authority import (
    AUTHORITY_DECLARATION_SCHEMA,
    AUTHORITY_PRODUCER_CONTRACT_CANDIDATES,
    AUTHORITY_ROOT_DIGEST_ENV,
    AUTHORITY_ROOT_PATH_ENV,
    AUTHORITY_ROOT_SIGNATURE_ENV,
    discover_authority_producer_contract,
    resolve_authority,
    verify_external_authority_declaration,
)
from opsx_conflict.errors import StopRequired
from opsx_conflict.hashutil import sha256_bytes, sha256_canonical
from opsx_conflict import attestation

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


def test_path_stem_heuristic_absent_from_authority_source() -> None:
    """R20 filename/stem substring completeness scan must not remain."""
    source = (
        PACKAGE_ROOT / "runtime" / "opsx_conflict" / "authority.py"
    ).read_text(encoding="utf-8")
    assert "conflict_tokens" not in source
    assert "AUTHORITY_COMPLETENESS_OMISSION" not in source
    assert "Path(conflict_path).stem" not in source
    assert "path_stem_heuristic_forbidden" in source


def test_producer_contract_missing_is_blocker(tmp_path: Path) -> None:
    """No external producer contract → discover returns None."""
    assert discover_authority_producer_contract(tmp_path) is None
    for rel in AUTHORITY_PRODUCER_CONTRACT_CANDIDATES:
        assert not (tmp_path / rel).exists()


def test_none_applicable_without_producer_stops(tmp_path: Path) -> None:
    """Local none_applicable binding without external producer is unproven."""
    change = tmp_path / "openspec" / "changes" / "c1"
    change.mkdir(parents=True)
    (change / "proposal.md").write_text("# change\n", encoding="utf-8")
    (change / "conflict-authority.json").write_text(
        json.dumps(
            {
                "schema": "opsx-resolve-conflict/authority-binding/v1",
                "change_id": "c1",
                "precedence": [
                    "accepted_decision",
                    "main_spec",
                    "active_change",
                ],
                "paths": {
                    "app/service.py": {
                        "authority": ["openspec/changes/c1/proposal.md"],
                        "strategy": "namespace_closed_comment_exact_ast_union",
                        "external_authority": "none_applicable",
                    }
                },
            }
        ),
        encoding="utf-8",
    )
    with pytest.raises(StopRequired) as exc:
        resolve_authority(
            tmp_path,
            run_id="r",
            fingerprint="f" * 64,
            scope_sha256="s" * 64,
            conflict_paths=["app/service.py"],
            change_id="c1",
            commit_oids={"head": "a" * 40, "operation_head": "b" * 40},
            strict=True,
            operation="merge",
            source_commit="a" * 40,
            stage_blob_oids={
                "app/service.py": {"1": "1" * 40, "2": "2" * 40, "3": "3" * 40}
            },
        )
    assert exc.value.reason in {
        "STOP_AUTHORITY_UNPROVEN",
        "AUTHORITY_COMMIT_LINEAGE_UNBOUND",
        "GIT_READ_FAILED",
        "GIT_TRUST_DIGEST_REQUIRED",
    }


def test_self_authored_declaration_rejected_without_issuer_contract(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Dropping a local declaration JSON is not evidence without OS trust."""
    monkeypatch.delenv(AUTHORITY_ROOT_DIGEST_ENV, raising=False)
    monkeypatch.delenv(AUTHORITY_ROOT_PATH_ENV, raising=False)
    monkeypatch.delenv(AUTHORITY_ROOT_SIGNATURE_ENV, raising=False)
    path = tmp_path / "openspec/changes/c1/authority-declaration.json"
    path.parent.mkdir(parents=True)
    path.write_text(
        json.dumps({"schema": AUTHORITY_DECLARATION_SCHEMA}),
        encoding="utf-8",
    )
    with pytest.raises(StopRequired) as exc:
        verify_external_authority_declaration(
            tmp_path,
            declaration_rel="openspec/changes/c1/authority-declaration.json",
            expected_snapshot_id="x" * 64,
            operation="merge",
            commit_oids={"head": "a" * 40, "operation_head": "b" * 40},
            stage_blob_oids={"app/x.py": {"1": "1" * 40}},
            conflict_paths=["app/x.py"],
            source_commit="a" * 40,
        )
    assert exc.value.details.get("blocker") == "BLOCKER_AUTHORITY_PRODUCER_MISSING"


def test_proven_none_applicable_with_external_producer(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Happy path when OS-pinned pubkey + signature + declaration exist."""
    priv = install_os_trust_pubkey(monkeypatch, tmp_path)
    pin_git_trust(monkeypatch, tmp_path / "state")
    head = init_git_repo(tmp_path)
    oid = hash_blob(tmp_path, b"x = 1\n")
    stages = {"app/x.py": {"1": oid, "2": oid, "3": oid}}
    bound = write_signed_producer(tmp_path, monkeypatch, private_key=priv)
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
    assert proof["issuer"] == "opsx-authority-issuer"


def test_best_effort_sandbox_cannot_satisfy_go(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Packaged BEST_EFFORT allowlist entry must not unlock GO."""
    monkeypatch.setenv(
        "OPSX_CONFLICT_SANDBOX_TRUST_DIGEST",
        sha256_bytes(
            (
                PACKAGE_ROOT
                / "runtime"
                / "opsx_conflict"
                / "sandbox_runner.py"
            ).read_bytes()
        ),
    )
    monkeypatch.delenv("OPSX_CONFLICT_SANDBOX_RUNNER", raising=False)
    manifest = {
        "trusted_sandbox_runners": [
            {
                "sha256": sha256_bytes(
                    (
                        PACKAGE_ROOT
                        / "runtime"
                        / "opsx_conflict"
                        / "sandbox_runner.py"
                    ).read_bytes()
                ),
                "protocol": "opsx-sandbox-path-confinement/v1",
                "package_path": "runtime/opsx_conflict/sandbox_runner.py",
                "enforcement_level": "BEST_EFFORT",
            }
        ]
    }
    with pytest.raises(StopRequired) as exc:
        attestation._resolve_sandbox_capability(manifest, mode="go")
    assert exc.value.reason == "STOP_SANDBOX_UNAVAILABLE"
    assert exc.value.details.get("blocker") == "BLOCKER_OS_SANDBOX_RUNNER_MISSING"


def test_packaged_runner_source_never_claims_os_verified() -> None:
    """BEST_EFFORT packaged runner must not self-declare OS_VERIFIED."""
    source = (
        PACKAGE_ROOT / "runtime" / "opsx_conflict" / "sandbox_runner.py"
    ).read_text(encoding="utf-8")
    assert 'ENFORCEMENT_LEVEL = "OS_VERIFIED"' not in source
    assert 'ENFORCEMENT_LEVEL = "BEST_EFFORT"' in source
    assert "not_sufficient_for_GO" in source


def test_incomplete_declaration_missing_inventory_digest_stops(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Missing required declaration fields → STOP_AUTHORITY_UNPROVEN."""
    priv = install_os_trust_pubkey(monkeypatch, tmp_path)
    write_signed_producer(tmp_path, monkeypatch, private_key=priv)
    path = tmp_path / "openspec/changes/c1/authority-declaration.json"
    path.parent.mkdir(parents=True)
    path.write_text(
        json.dumps(
            {
                "schema": AUTHORITY_DECLARATION_SCHEMA,
                "conflict_snapshot_id": "x" * 64,
                "source_commit": "a" * 40,
                "operation": "merge",
                "conflicting_commit_oids": {
                    "head": "a" * 40,
                    "operation_head": "b" * 40,
                },
                "stage_blob_oids": {},
                "paths": ["app/x.py"],
                "rename_lineage": {},
                "symbols": [],
                "capabilities": [],
            }
        ),
        encoding="utf-8",
    )
    with pytest.raises(StopRequired) as exc:
        verify_external_authority_declaration(
            tmp_path,
            declaration_rel="openspec/changes/c1/authority-declaration.json",
            expected_snapshot_id="x" * 64,
            operation="merge",
            commit_oids={"head": "a" * 40, "operation_head": "b" * 40},
            stage_blob_oids={"app/x.py": {"1": "1" * 40}},
            conflict_paths=["app/x.py"],
            source_commit="a" * 40,
        )
    assert exc.value.details.get("reason") in {
        "legacy_unsigned_declaration_rejected",
        "declaration_payload_missing",
        "declaration_missing_field",
    }


def test_validation_prewrite_statuses_are_required_na_or_blocked() -> None:
    """Pre-write inventory uses REQUIRED/NOT_APPLICABLE/BLOCKED — never SKIPPED."""
    validation_src = (
        PACKAGE_ROOT / "runtime" / "opsx_conflict" / "validation.py"
    ).read_text(encoding="utf-8")
    receipts_src = (
        PACKAGE_ROOT / "runtime" / "opsx_conflict" / "receipts.py"
    ).read_text(encoding="utf-8")
    assert '"status": "REQUIRED"' in validation_src
    assert '"status": "NOT_APPLICABLE"' in validation_src
    assert '"status": "BLOCKED"' in validation_src
    assert '"status": "SKIPPED"' not in validation_src
    assert '"status": "SCHEDULED"' not in validation_src
    assert 'status in {"REQUIRED", "SCHEDULED"}' in receipts_src


def test_package_discloses_blockers_in_manifest_limitations() -> None:
    """MANIFEST/TRUST must disclose producer and OS sandbox blockers."""
    review = (PACKAGE_ROOT / "REVIEW_REQUEST.md").read_text(encoding="utf-8")
    assert "BLOCKER_AUTHORITY_PRODUCER_MISSING" in review
    assert "BLOCKER_OS_SANDBOX_RUNNER_MISSING" in review
    assert "GO_CAPABILITY=false" in review


def test_authority_schema_shipped() -> None:
    """External declaration schema must ship with the package."""
    schema = PACKAGE_ROOT / "schemas" / "authority-declaration.schema.json"
    assert schema.is_file()
    payload = json.loads(schema.read_text(encoding="utf-8"))
    assert payload["$id"] == "opsx-resolve-conflict/authority-declaration/v5"


def test_source_lineage_mapping_present_and_bound() -> None:
    """Host-contract lineage mapping must bind origin/snapshot dual OIDs."""
    lineage_path = PACKAGE_ROOT / "context" / "SOURCE_LINEAGE.json"
    assert lineage_path.is_file()
    lineage = json.loads(lineage_path.read_text(encoding="utf-8"))
    schema = lineage.get("schema")
    assert schema in {
        "opsx-resolve-conflict/source-lineage/v1",
        "opsx-resolve-conflict/source-lineage/v2",
    }
    files = lineage.get("files") or []
    assert files


def test_replay_evidence_summary_labels_fail_closed() -> None:
    """Replay evidence must not claim production GO readiness."""
    summary = PACKAGE_ROOT / "context" / "REPLAY_EVIDENCE_SUMMARY.json"
    assert summary.is_file()
    payload = json.loads(summary.read_text(encoding="utf-8"))
    assert payload.get("go_capability") is False
    assert "not" in payload.get("note", "").lower()
