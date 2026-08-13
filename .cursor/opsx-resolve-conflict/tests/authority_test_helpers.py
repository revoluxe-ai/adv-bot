"""Shared helpers for R26/R27 authority trust tests (OS pubkey + issuer signatures)."""

from __future__ import annotations

import binascii
import json
import os
import shutil
import subprocess
from pathlib import Path
from typing import Any

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat

from opsx_conflict import authority as authority_module
from opsx_conflict.authority import (
    AUTHORITY_DECLARATION_SCHEMA,
    AUTHORITY_ROOT_DIGEST_ENV,
    AUTHORITY_ROOT_PATH_ENV,
    AUTHORITY_ROOT_SIGNATURE_ENV,
    CAPABILITY_ATTESTOR_ROLE,
    CAPABILITY_EVIDENCE_SCHEMA,
    SYMBOL_EXTRACTOR_VERSION,
    canonicalize_declaration_payload,
    compute_conflict_snapshot_id,
    expected_stage_coverage_rows,
    recompute_contracts_inventory_digest,
)
from opsx_conflict.hashutil import sha256_bytes, sha256_canonical


def _set_readonly(path: Path) -> None:
    """Mark path read-only for OS trust-store checks."""
    if os.name == "nt":
        import ctypes

        FILE_ATTRIBUTE_READONLY = 0x1
        ctypes.windll.kernel32.SetFileAttributesW(str(path), FILE_ATTRIBUTE_READONLY)
    else:
        path.chmod(0o444)


def install_os_trust_pubkey(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    private_key: Ed25519PrivateKey | None = None,
) -> Ed25519PrivateKey:
    """Install a test OS-pinned pubkey and return the matching private key.

    R30: production openers enforce installer-owned ACL/owner walks. Unit tests
    monkeypatch the opener to a fixture session that still binds path identity
    and keeps a stable FD through signature verification.
    """
    from opsx_conflict import os_trust_store as trust_store
    from opsx_conflict.os_trust_store import TrustKeySession

    priv = private_key or Ed25519PrivateKey.generate()
    pub_raw = priv.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw)
    store = tmp_path.parent / f"opsx-trust-{tmp_path.name}"
    store.mkdir(parents=True, exist_ok=True)
    pub_path = store / "ed25519.pub"
    pub_path.write_bytes(binascii.hexlify(pub_raw))
    _set_readonly(pub_path)

    def _test_path() -> Path:
        return pub_path

    def _test_open(path: Path | None = None) -> TrustKeySession:
        from opsx_conflict.errors import StopRequired

        target = path if path is not None else pub_path
        if Path(target).resolve() != pub_path.resolve():
            raise StopRequired(
                "STOP_AUTHORITY_UNPROVEN",
                {
                    "blocker": "BLOCKER_AUTHORITY_PRODUCER_MISSING",
                    "reason": "os_trust_pubkey_unreadable",
                    "path": str(target),
                },
            )
        fd = os.open(pub_path, os.O_RDONLY)
        owned_fd = fd
        try:
            st = os.fstat(fd)
            raw = os.read(fd, 1 << 20)
            while True:
                chunk = os.read(fd, 1 << 20)
                if not chunk:
                    break
                raw += chunk
            identity = {
                "device": int(st.st_dev),
                "inode": int(st.st_ino),
                "size": int(st.st_size),
                "uid": int(getattr(st, "st_uid", 0)),
                "mode": int(st.st_mode),
            }
            session = TrustKeySession(
                path=pub_path,
                key_bytes=raw,
                identity=identity,
                _fd=fd,
            )
            owned_fd = -1
            return session
        finally:
            if owned_fd >= 0:
                os.close(owned_fd)

    monkeypatch.setattr(authority_module, "os_authority_trust_pubkey_path", _test_path)
    monkeypatch.setattr(trust_store, "os_authority_trust_pubkey_path", _test_path)
    monkeypatch.setattr(
        authority_module, "open_authenticated_trust_pubkey", _test_open
    )
    monkeypatch.setattr(trust_store, "open_authenticated_trust_pubkey", _test_open)
    return priv


def _pub_hex(priv: Ed25519PrivateKey) -> str:
    """Return raw Ed25519 public key as lowercase hex."""
    return binascii.hexlify(
        priv.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw)
    ).decode("ascii")


def write_signed_producer(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    *,
    private_key: Ed25519PrivateKey,
    issuer_private_key: Ed25519PrivateKey | None = None,
    issuer_id: str = "opsx-authority-issuer",
    issuer_key_id: str = "issuer-key-1",
    issuers: list[Any] | None = None,
    roots: list[str] | None = None,
    authorize_none: bool = True,
    capability_bindings: list[dict[str, str]] | None = None,
    issuer_roles: list[str] | None = None,
) -> dict[str, Any]:
    """Write producer JSON with issuer key binding, sign it, bind env."""
    rel = ".cursor/opsx-authority-producers.json"
    root_list = roots or ["openspec/policies/OPSX_ROOT_CONTRACT.md"]
    for root_rel in root_list:
        root_path = tmp_path / root_rel
        root_path.parent.mkdir(parents=True, exist_ok=True)
        if not root_path.exists():
            root_path.write_text("# authoritative root\n", encoding="utf-8")
    issuer_priv = issuer_private_key or Ed25519PrivateKey.generate()
    roles = (
        issuer_roles
        if issuer_roles is not None
        else [CAPABILITY_ATTESTOR_ROLE]
    )
    if issuers is None:
        issuers = [
            {
                "id": issuer_id,
                "key_id": issuer_key_id,
                "public_key_ed25519": _pub_hex(issuer_priv),
                "roles": roles,
            }
        ]
    payload = {
        "issuers": issuers,
        "authoritative_roots": root_list,
        "authorize_none_applicable": authorize_none,
        "capability_bindings": capability_bindings or [],
    }
    path = tmp_path / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    raw = (json.dumps(payload, indent=2) + "\n").encode("utf-8")
    path.write_bytes(raw)
    digest = sha256_bytes(raw)
    signature = binascii.hexlify(private_key.sign(raw)).decode("ascii")
    monkeypatch.setenv(AUTHORITY_ROOT_PATH_ENV, rel)
    monkeypatch.setenv(AUTHORITY_ROOT_DIGEST_ENV, digest)
    monkeypatch.setenv(AUTHORITY_ROOT_SIGNATURE_ENV, signature)
    return {
        "path": rel,
        "sha256": digest,
        "signature": signature,
        "contracts": recompute_contracts_inventory_digest(tmp_path, root_list),
        "issuer_private_key": issuer_priv,
        "issuer_id": issuer_id,
        "issuer_key_id": issuer_key_id,
    }


def pin_git_trust(monkeypatch: pytest.MonkeyPatch, state_dir: Path) -> None:
    """Pin Git trust digest for TypedGit in fixture repos."""
    git = shutil.which("git")
    assert git
    digest = sha256_bytes(Path(git).read_bytes())
    monkeypatch.setenv("OPSX_CONFLICT_GIT_TRUST_DIGEST", digest)
    monkeypatch.setenv("OPSX_CONFLICT_STATE", str(state_dir))
    monkeypatch.delenv("OPSX_CONFLICT_GIT_TRUST_UNBOUND", raising=False)


def init_git_repo(tmp_path: Path) -> str:
    """Initialize a git repo and return HEAD oid after an initial commit."""
    subprocess.run(["git", "init"], cwd=tmp_path, check=True, capture_output=True)
    subprocess.run(
        ["git", "config", "user.email", "t@example.com"],
        cwd=tmp_path,
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "test"],
        cwd=tmp_path,
        check=True,
        capture_output=True,
    )
    (tmp_path / "README").write_text("init\n", encoding="utf-8")
    subprocess.run(["git", "add", "README"], cwd=tmp_path, check=True, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "init"],
        cwd=tmp_path,
        check=True,
        capture_output=True,
    )
    return subprocess.check_output(
        ["git", "rev-parse", "HEAD"],
        cwd=tmp_path,
        text=True,
    ).strip()


def hash_blob(tmp_path: Path, data: bytes) -> str:
    """Write a git blob and return its OID."""
    proc = subprocess.run(
        ["git", "hash-object", "-w", "--stdin"],
        cwd=tmp_path,
        input=data,
        capture_output=True,
        check=True,
    )
    return proc.stdout.decode("utf-8").strip()


def build_capability_evidence(
    *,
    snapshot: str,
    stage_blob_oids: dict,
    capabilities: list[str] | None = None,
    analysis_complete: bool = True,
    unknown_targets: list[Any] | None = None,
    observations: list[dict[str, Any]] | None = None,
    classifier_id: str = "test-capability-attestor",
    classifier_version: str = "1.0.0",
    stage_coverage: list[dict[str, str]] | None = None,
) -> dict[str, Any]:
    """Build capability-evidence object for signed declaration payloads."""
    caps = list(capabilities) if capabilities is not None else []
    coverage = stage_coverage
    if coverage is None:
        coverage = expected_stage_coverage_rows(
            conflict_paths=sorted(stage_blob_oids),
            stage_blob_oids=stage_blob_oids,
        )
    return {
        "schema": CAPABILITY_EVIDENCE_SCHEMA,
        "classifier_id": classifier_id,
        "classifier_version": classifier_version,
        "conflict_snapshot_id": snapshot,
        "stage_coverage": coverage,
        "capabilities": caps,
        "analysis_complete": analysis_complete,
        "unknown_targets": list(unknown_targets) if unknown_targets is not None else [],
        "observations": list(observations) if observations is not None else [],
    }


def base_declaration_payload(
    *,
    snapshot: str,
    producer_sha: str,
    contracts_digest: str,
    producer_path: str,
    stage_blob_oids: dict,
    symbols: list[str] | None = None,
    capabilities: list[str] | None = None,
    capability_evidence: dict[str, Any] | None = None,
    operation: str = "merge",
    head: str,
    other: str,
    none_applicable: bool = True,
    applicable: list | None = None,
    issuer_id: str = "opsx-authority-issuer",
    omit_capability_evidence: bool = False,
) -> dict:
    """Build a v5 declaration semantic payload (unsigned)."""
    caps = list(capabilities) if capabilities is not None else []
    evidence = capability_evidence
    if evidence is None and not omit_capability_evidence:
        evidence = build_capability_evidence(
            snapshot=snapshot,
            stage_blob_oids=stage_blob_oids,
            capabilities=caps,
        )
    payload: dict[str, Any] = {
        "schema": AUTHORITY_DECLARATION_SCHEMA,
        "conflict_snapshot_id": snapshot,
        "source_commit": head,
        "operation": operation,
        "conflicting_commit_oids": {"head": head, "operation_head": other},
        "stage_blob_oids": stage_blob_oids,
        "paths": sorted(stage_blob_oids),
        "rename_lineage": {},
        "symbols": symbols if symbols is not None else [],
        "capabilities": caps,
        "symbol_extractor_version": SYMBOL_EXTRACTOR_VERSION,
        "contracts_inventory_digest": contracts_digest,
        "authority_inventory_digest": sha256_canonical([]),
        "producer_contract_sha256": producer_sha,
        "issuer": {
            "id": issuer_id,
            "contract_path": producer_path,
        },
        "none_applicable": none_applicable,
        "applicable_authorities": applicable or [],
    }
    if not omit_capability_evidence:
        payload["capability_evidence"] = evidence
    return payload


def sign_declaration(
    payload: dict,
    *,
    issuer_private_key: Ed25519PrivateKey,
    issuer_key_id: str = "issuer-key-1",
) -> dict:
    """Wrap payload in a v5 signed declaration envelope."""
    canonical = canonicalize_declaration_payload(payload)
    signature = binascii.hexlify(issuer_private_key.sign(canonical)).decode("ascii")
    return {
        "schema": AUTHORITY_DECLARATION_SCHEMA,
        "payload": payload,
        "issuer_key_id": issuer_key_id,
        "signature": signature,
    }


def base_declaration(
    *,
    snapshot: str,
    producer_sha: str,
    contracts_digest: str,
    producer_path: str,
    stage_blob_oids: dict,
    symbols: list[str] | None = None,
    capabilities: list[str] | None = None,
    capability_evidence: dict[str, Any] | None = None,
    operation: str = "merge",
    head: str,
    other: str,
    none_applicable: bool = True,
    applicable: list | None = None,
    issuer_private_key: Ed25519PrivateKey | None = None,
    issuer_key_id: str = "issuer-key-1",
    issuer_id: str = "opsx-authority-issuer",
    sign: bool = True,
    omit_capability_evidence: bool = False,
) -> dict:
    """Build a v5 declaration envelope (signed by default)."""
    payload = base_declaration_payload(
        snapshot=snapshot,
        producer_sha=producer_sha,
        contracts_digest=contracts_digest,
        producer_path=producer_path,
        stage_blob_oids=stage_blob_oids,
        symbols=symbols,
        capabilities=capabilities,
        capability_evidence=capability_evidence,
        operation=operation,
        head=head,
        other=other,
        none_applicable=none_applicable,
        applicable=applicable,
        issuer_id=issuer_id,
        omit_capability_evidence=omit_capability_evidence,
    )
    if not sign:
        return payload
    assert issuer_private_key is not None
    return sign_declaration(
        payload,
        issuer_private_key=issuer_private_key,
        issuer_key_id=issuer_key_id,
    )


def make_snapshot(
    *,
    head: str,
    other: str,
    stage_blob_oids: dict,
    operation: str = "merge",
) -> str:
    """Compute conflict snapshot id for fixture declarations."""
    return compute_conflict_snapshot_id(
        source_commit=head,
        operation=operation,
        commit_oids={"head": head, "operation_head": other},
        stage_blob_oids=stage_blob_oids,
        paths=sorted(stage_blob_oids),
    )
