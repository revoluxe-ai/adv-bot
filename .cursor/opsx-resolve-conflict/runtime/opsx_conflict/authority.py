"""Executable OPSX authority resolver (R27 signed declaration + capability evidence).

Producer trust requires an Ed25519 signature over producer bytes verified
against an OS-pinned public key path that is **not** ambient-environment
configurable. Path+digest env alone is never a trust boundary.

Authority declarations (v4) require a second Ed25519 signature over the
canonical semantic payload, verified with an issuer public key that is
bound to the issuer ID inside the authenticated producer contract.

MANIFEST / ``host_frozen_contracts`` cannot mint trust. This module is a
consumer/verifier only and must not mint declarations.
"""

from __future__ import annotations

import ast
import binascii
import json
import os
import re
from pathlib import Path
from typing import Any, Mapping, Sequence

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
from cryptography.hazmat.primitives.serialization import (
    Encoding,
    PublicFormat,
    load_pem_public_key,
)

from .errors import StopRequired
from .git_typed import TypedGit
from .hashutil import canonical_json, sha256_bytes, sha256_canonical, sha256_text
from .os_trust_store import (
    open_authenticated_trust_pubkey,
    os_authority_trust_pubkey_path,
)
from .pathsafety import resolve_existing_under_repo
from .proofs import Proof

AUTHORITY_DECLARATION_SCHEMA = "opsx-resolve-conflict/authority-declaration/v5"
AUTHORITY_DECLARATION_SCHEMA_LEGACY_UNSIGNED = (
    "opsx-resolve-conflict/authority-declaration/v3"
)
AUTHORITY_DECLARATION_SCHEMA_LEGACY_V4 = (
    "opsx-resolve-conflict/authority-declaration/v4"
)
CAPABILITY_EVIDENCE_SCHEMA = "opsx-resolve-conflict/capability-evidence/v1"
CAPABILITY_ATTESTOR_ROLE = "capability_attestor"
DECLARATION_PAYLOAD_FIELD_ORDER: tuple[str, ...] = (
    "schema",
    "conflict_snapshot_id",
    "source_commit",
    "operation",
    "conflicting_commit_oids",
    "stage_blob_oids",
    "paths",
    "rename_lineage",
    "symbols",
    "capabilities",
    "capability_evidence",
    "symbol_extractor_version",
    "contracts_inventory_digest",
    "authority_inventory_digest",
    "producer_contract_sha256",
    "issuer",
    "none_applicable",
    "applicable_authorities",
)
AUTHORITY_BINDING_SCHEMA = "opsx-resolve-conflict/authority-binding/v1"
SYMBOL_EXTRACTOR_VERSION = "opsx-symbol-extractor/v1"

# Legacy candidate paths — never trusted by mere existence.
AUTHORITY_PRODUCER_CONTRACT_CANDIDATES: tuple[str, ...] = (
    "openspec/policies/CONFLICT_AUTHORITY_PRODUCER.md",
    "openspec/policies/CONFLICT_AUTHORITY_ISSUERS.md",
    ".cursor/opsx-authority-producers.json",
)

# Ambient path/digest alone are NOT a trust root (R22-HIGH-001).
AUTHORITY_ROOT_DIGEST_ENV = "OPSX_CONFLICT_AUTHORITY_ROOT_DIGEST"
AUTHORITY_ROOT_PATH_ENV = "OPSX_CONFLICT_AUTHORITY_ROOT_PATH"
AUTHORITY_ROOT_SIGNATURE_ENV = "OPSX_CONFLICT_AUTHORITY_ROOT_SIGNATURE"

RENAME_THRESHOLD = "50%"
_CONFLICT_MARKER_RE = re.compile(r"^(<<<<<<<|=======|>>>>>>>)", re.MULTILINE)


def _read_text(path: Path) -> str:
    """Read UTF-8 text or return empty string when missing."""
    return path.read_text(encoding="utf-8") if path.exists() else ""


def _parse_producer_payload(text: str, *, path_rel: str) -> dict[str, Any]:
    """Parse producer JSON from raw JSON or a markdown fenced block."""
    payload: Any
    if path_rel.endswith(".json"):
        payload = json.loads(text)
    else:
        match = re.search(r"```json\s*(\{.*?\})\s*```", text, flags=re.DOTALL)
        if not match:
            raise StopRequired(
                "STOP_AUTHORITY_UNPROVEN",
                {
                    "blocker": "BLOCKER_AUTHORITY_PRODUCER_MISSING",
                    "reason": "producer_contract_missing_json_block",
                    "path": path_rel,
                },
            )
        payload = json.loads(match.group(1))
    if not isinstance(payload, dict):
        raise StopRequired(
            "STOP_AUTHORITY_UNPROVEN",
            {
                "blocker": "BLOCKER_AUTHORITY_PRODUCER_MISSING",
                "reason": "producer_contract_not_object",
            },
        )
    return payload


def _assert_os_trust_store_file(path: Path) -> bytes:
    """Load OS-pinned pubkey via secure trust-store session (compat wrapper)."""
    session = open_authenticated_trust_pubkey(path)
    try:
        session.recheck_identity()
        return session.key_bytes
    finally:
        session.close()


def _load_ed25519_public_key(raw: bytes) -> Ed25519PublicKey:
    """Parse PEM or raw 32-byte Ed25519 public key material."""
    try:
        if b"BEGIN PUBLIC KEY" in raw or b"BEGIN ED25519" in raw:
            key = load_pem_public_key(raw)
            if not isinstance(key, Ed25519PublicKey):
                raise StopRequired(
                    "STOP_AUTHORITY_UNPROVEN",
                    {
                        "blocker": "BLOCKER_AUTHORITY_PRODUCER_MISSING",
                        "reason": "os_trust_pubkey_not_ed25519",
                    },
                )
            return key
        if len(raw.strip()) == 64 and all(
            ch in b"0123456789abcdefABCDEF" for ch in raw.strip()
        ):
            return Ed25519PublicKey.from_public_bytes(binascii.unhexlify(raw.strip()))
        if len(raw) == 32:
            return Ed25519PublicKey.from_public_bytes(raw)
    except (ValueError, binascii.Error) as exc:
        raise StopRequired(
            "STOP_AUTHORITY_UNPROVEN",
            {
                "blocker": "BLOCKER_AUTHORITY_PRODUCER_MISSING",
                "reason": "os_trust_pubkey_invalid",
            },
        ) from exc
    raise StopRequired(
        "STOP_AUTHORITY_UNPROVEN",
        {
            "blocker": "BLOCKER_AUTHORITY_PRODUCER_MISSING",
            "reason": "os_trust_pubkey_invalid",
        },
    )


def load_authenticated_authority_root(repo_root: Path) -> dict[str, Any]:
    """Load producer contract authenticated by OS-pinned pubkey + signature.

    Ambient ``PATH`` + ``DIGEST`` alone are rejected. Signature must verify
    against the installer-pinned Ed25519 public key.

    Returns:
        Producer payload with path, sha256, issuers, authoritative_roots,
        capability_bindings.

    Raises:
        StopRequired: when OS trust root, signature, or producer is unproven.
    """
    # Explicitly reject the ambient-only channel even if set.
    path_rel = os.environ.get(AUTHORITY_ROOT_PATH_ENV, "").strip().replace("\\", "/")
    digest = os.environ.get(AUTHORITY_ROOT_DIGEST_ENV, "").strip().lower()
    signature_hex = os.environ.get(AUTHORITY_ROOT_SIGNATURE_ENV, "").strip().lower()

    pubkey_path = os_authority_trust_pubkey_path()
    trust_session = open_authenticated_trust_pubkey(pubkey_path)
    try:
        public_key = _load_ed25519_public_key(trust_session.key_bytes)

        if not path_rel or path_rel.startswith("/") or ".." in Path(path_rel).parts:
            raise StopRequired(
                "STOP_AUTHORITY_UNPROVEN",
                {
                    "blocker": "BLOCKER_AUTHORITY_PRODUCER_MISSING",
                    "reason": "authority_root_path_missing",
                    "required": [
                        AUTHORITY_ROOT_PATH_ENV,
                        AUTHORITY_ROOT_SIGNATURE_ENV,
                        f"os_trust_pubkey:{pubkey_path}",
                    ],
                },
            )
        if (
            not signature_hex
            or len(signature_hex) != 128
            or any(ch not in "0123456789abcdef" for ch in signature_hex)
        ):
            raise StopRequired(
                "STOP_AUTHORITY_UNPROVEN",
                {
                    "blocker": "BLOCKER_AUTHORITY_PRODUCER_MISSING",
                    "reason": "authority_root_signature_missing",
                    "note": (
                        "Ambient path+digest without a signature verifiable against "
                        "the OS-pinned pubkey is not a trust boundary."
                    ),
                },
            )

        try:
            _, path = resolve_existing_under_repo(repo_root, path_rel)
        except StopRequired as exc:
            raise StopRequired(
                "STOP_AUTHORITY_UNPROVEN",
                {
                    "blocker": "BLOCKER_AUTHORITY_PRODUCER_MISSING",
                    "reason": "authority_root_path_missing",
                    "path": path_rel,
                },
            ) from exc
        if path.is_symlink() or not path.is_file():
            raise StopRequired(
                "STOP_AUTHORITY_UNPROVEN",
                {
                    "blocker": "BLOCKER_AUTHORITY_PRODUCER_MISSING",
                    "reason": "authority_root_path_invalid",
                    "path": path_rel,
                },
            )
        raw = path.read_bytes()
        actual = sha256_bytes(raw)
        if digest and digest != actual:
            raise StopRequired(
                "STOP_AUTHORITY_UNPROVEN",
                {
                    "blocker": "BLOCKER_AUTHORITY_PRODUCER_MISSING",
                    "reason": "authority_root_digest_mismatch",
                    "expected": digest,
                    "actual": actual,
                },
            )
        # Identity must be unchanged immediately before producer signature use.
        trust_session.recheck_identity()
        try:
            public_key.verify(binascii.unhexlify(signature_hex), raw)
        except (InvalidSignature, binascii.Error, ValueError) as exc:
            raise StopRequired(
                "STOP_AUTHORITY_UNPROVEN",
                {
                    "blocker": "BLOCKER_AUTHORITY_PRODUCER_MISSING",
                    "reason": "authority_root_signature_invalid",
                    "path": path_rel,
                },
            ) from exc
        trust_session.recheck_identity()

        try:
            payload = _parse_producer_payload(raw.decode("utf-8"), path_rel=path_rel)
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise StopRequired(
                "STOP_AUTHORITY_UNPROVEN",
                {
                    "blocker": "BLOCKER_AUTHORITY_PRODUCER_MISSING",
                    "reason": "authority_root_invalid_json",
                    "path": path_rel,
                },
            ) from exc
        issuers = payload.get("issuers")
        roots = payload.get("authoritative_roots")
        if not isinstance(issuers, list) or not issuers:
            raise StopRequired(
                "STOP_AUTHORITY_UNPROVEN",
                {
                    "blocker": "BLOCKER_AUTHORITY_PRODUCER_MISSING",
                    "reason": "authority_root_issuers_missing",
                },
            )
        if not isinstance(roots, list) or not roots:
            raise StopRequired(
                "STOP_AUTHORITY_UNPROVEN",
                {
                    "reason": "authoritative_roots_missing",
                    "note": (
                        "Producer contract must list the closed authoritative OPSX "
                        "root set; two-directory digests are not completeness proof."
                    ),
                },
            )
        normalized_issuers = _normalize_producer_issuers(issuers)
        bindings = payload.get("capability_bindings")
        if bindings is None:
            bindings = []
        if not isinstance(bindings, list):
            raise StopRequired(
                "STOP_AUTHORITY_UNPROVEN",
                {"reason": "capability_bindings_invalid"},
            )
        normalized_bindings: list[dict[str, str]] = []
        for row in bindings:
            if not isinstance(row, dict) or not row.get("symbol") or not row.get(
                "capability"
            ):
                raise StopRequired(
                    "STOP_AUTHORITY_UNPROVEN",
                    {"reason": "capability_binding_row_invalid"},
                )
            normalized_bindings.append(
                {"symbol": str(row["symbol"]), "capability": str(row["capability"])}
            )
        pubkey_fingerprint = sha256_bytes(
            public_key.public_bytes(Encoding.Raw, PublicFormat.Raw)
        )
        return {
            "contract_path": path_rel,
            "sha256": actual,
            "issuers": [row["id"] for row in normalized_issuers],
            "issuer_entries": normalized_issuers,
            "authoritative_roots": [str(item) for item in roots],
            "capability_bindings": normalized_bindings,
            "authorize_none_applicable": bool(
                payload.get("authorize_none_applicable", False)
            ),
            "raw_bytes": raw,
            "trust_pubkey_path": str(pubkey_path),
            "trust_pubkey_sha256": pubkey_fingerprint,
            "signature_sha256": sha256_bytes(binascii.unhexlify(signature_hex)),
        }
    finally:
        trust_session.close()


def discover_authority_producer_contract(
    repo_root: Path,
) -> dict[str, Any] | None:
    """Return authenticated producer root or None when external root absent."""
    if not os.environ.get(AUTHORITY_ROOT_SIGNATURE_ENV, "").strip():
        return None
    if not os.environ.get(AUTHORITY_ROOT_PATH_ENV, "").strip():
        return None
    try:
        return load_authenticated_authority_root(repo_root)
    except StopRequired:
        return None


def compute_conflict_snapshot_id(
    *,
    source_commit: str,
    operation: str,
    commit_oids: Mapping[str, str],
    stage_blob_oids: Mapping[str, Mapping[str, str]],
    paths: Sequence[str],
) -> str:
    """Deterministic conflict snapshot identity for declaration binding."""
    return sha256_canonical(
        {
            "source_commit": source_commit,
            "operation": operation,
            "conflicting_commit_oids": dict(commit_oids),
            "stage_blob_oids": {
                path: dict(stages) for path, stages in sorted(stage_blob_oids.items())
            },
            "paths": sorted(paths),
        }
    )


def recompute_contracts_inventory_digest(
    repo_root: Path,
    authoritative_roots: Sequence[str],
) -> str:
    """Hash the closed authoritative root list from the producer contract."""
    rows: list[dict[str, str]] = []
    for rel in sorted(set(authoritative_roots)):
        try:
            _, path = resolve_existing_under_repo(repo_root, rel)
        except StopRequired as exc:
            raise StopRequired(
                "STOP_AUTHORITY_UNPROVEN",
                {"reason": "authoritative_root_missing", "path": rel},
            ) from exc
        if path.is_symlink() or not path.is_file():
            raise StopRequired(
                "STOP_AUTHORITY_UNPROVEN",
                {"reason": "authoritative_root_invalid", "path": rel},
            )
        rows.append({"path": rel, "sha256": sha256_bytes(path.read_bytes())})
    return sha256_canonical(rows)


def _extract_symbols_from_source(source: str, *, blob_oid: str, path: str) -> set[str]:
    """Extract mechanical symbols from one blob; parse failure → STOP."""
    if _CONFLICT_MARKER_RE.search(source):
        raise StopRequired(
            "STOP_AUTHORITY_UNPROVEN",
            {
                "reason": "conflict_markers_in_stage_blob",
                "path": path,
                "blob_oid": blob_oid,
            },
        )
    try:
        tree = ast.parse(source)
    except SyntaxError as exc:
        raise StopRequired(
            "STOP_AUTHORITY_UNPROVEN",
            {
                "reason": "stage_blob_parse_failed",
                "path": path,
                "blob_oid": blob_oid,
                "error": str(exc),
            },
        ) from exc
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            names.add(node.name)
        elif isinstance(node, ast.Import):
            for alias in node.names:
                names.add(alias.asname or alias.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom):
            for alias in node.names:
                names.add(alias.asname or alias.name)
    return names


def recompute_mechanical_symbols_from_stages(
    git: TypedGit,
    *,
    conflict_paths: Sequence[str],
    stage_blob_oids: Mapping[str, Mapping[str, str]],
) -> list[str]:
    """Recompute symbols from stage 1/2/3 blob bytes (not worktree).

    Missing required stage blobs or unparsable content → STOP.
    """
    names: set[str] = set()
    for rel in conflict_paths:
        stages = stage_blob_oids.get(rel) or {}
        if not stages:
            raise StopRequired(
                "STOP_AUTHORITY_UNPROVEN",
                {"reason": "stage_blob_oids_missing_for_symbols", "path": rel},
            )
        for stage, oid in sorted(stages.items(), key=lambda item: str(item[0])):
            oid_s = str(oid)
            if not oid_s:
                raise StopRequired(
                    "STOP_AUTHORITY_UNPROVEN",
                    {
                        "reason": "stage_blob_oid_empty",
                        "path": rel,
                        "stage": str(stage),
                    },
                )
            if not rel.endswith(".py"):
                # Non-Python conflict paths still require readable blobs.
                try:
                    git.cat_file_blob_bytes(oid_s)
                except StopRequired as exc:
                    raise StopRequired(
                        "STOP_AUTHORITY_UNPROVEN",
                        {
                            "reason": "stage_blob_unreadable",
                            "path": rel,
                            "stage": str(stage),
                            "blob_oid": oid_s,
                        },
                    ) from exc
                continue
            try:
                raw = git.cat_file_blob_bytes(oid_s)
            except StopRequired as exc:
                raise StopRequired(
                    "STOP_AUTHORITY_UNPROVEN",
                    {
                        "reason": "stage_blob_unreadable",
                        "path": rel,
                        "stage": str(stage),
                        "blob_oid": oid_s,
                    },
                ) from exc
            try:
                text = raw.decode("utf-8")
            except UnicodeDecodeError as exc:
                raise StopRequired(
                    "STOP_AUTHORITY_UNPROVEN",
                    {
                        "reason": "stage_blob_decode_failed",
                        "path": rel,
                        "blob_oid": oid_s,
                    },
                ) from exc
            names |= _extract_symbols_from_source(text, blob_oid=oid_s, path=rel)
    return sorted(names)


def recompute_capabilities_from_bindings(
    symbols: Sequence[str],
    capability_bindings: Sequence[Mapping[str, str]],
) -> list[str]:
    """Map mechanical symbols through producer capability bindings."""
    symbol_set = set(symbols)
    caps: set[str] = set()
    for row in capability_bindings:
        if row["symbol"] in symbol_set:
            caps.add(row["capability"])
    return sorted(caps)


def _normalize_producer_issuers(
    issuers: Sequence[Any],
) -> list[dict[str, Any]]:
    """Require issuer ID ↔ key_id ↔ Ed25519 public key (+ optional roles)."""
    out: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    seen_keys: set[str] = set()
    for item in issuers:
        if isinstance(item, str):
            raise StopRequired(
                "STOP_AUTHORITY_UNPROVEN",
                {
                    "blocker": "BLOCKER_AUTHORITY_PRODUCER_MISSING",
                    "reason": "issuer_missing_key_binding",
                    "issuer": item,
                    "note": (
                        "Bare issuer ID strings are insufficient; producer must "
                        "bind issuer ID to key_id and Ed25519 public key."
                    ),
                },
            )
        if not isinstance(item, dict):
            raise StopRequired(
                "STOP_AUTHORITY_UNPROVEN",
                {"reason": "issuer_entry_invalid"},
            )
        issuer_id = str(item.get("id") or "").strip()
        key_id = str(item.get("key_id") or "").strip()
        pub_hex = str(item.get("public_key_ed25519") or "").strip().lower()
        if not issuer_id or not key_id:
            raise StopRequired(
                "STOP_AUTHORITY_UNPROVEN",
                {"reason": "issuer_entry_incomplete"},
            )
        if (
            len(pub_hex) != 64
            or any(ch not in "0123456789abcdef" for ch in pub_hex)
        ):
            raise StopRequired(
                "STOP_AUTHORITY_UNPROVEN",
                {
                    "reason": "issuer_public_key_invalid",
                    "issuer": issuer_id,
                    "key_id": key_id,
                },
            )
        roles_raw = item.get("roles", [])
        if roles_raw is None:
            roles_raw = []
        if not isinstance(roles_raw, list) or any(
            not isinstance(role, str) or not role.strip() for role in roles_raw
        ):
            raise StopRequired(
                "STOP_AUTHORITY_UNPROVEN",
                {"reason": "issuer_roles_invalid", "issuer": issuer_id},
            )
        roles = sorted({str(role).strip() for role in roles_raw})
        if issuer_id in seen_ids:
            raise StopRequired(
                "STOP_AUTHORITY_UNPROVEN",
                {"reason": "issuer_id_duplicate", "issuer": issuer_id},
            )
        if key_id in seen_keys:
            raise StopRequired(
                "STOP_AUTHORITY_UNPROVEN",
                {"reason": "issuer_key_id_duplicate", "key_id": key_id},
            )
        # Validate key material parses as Ed25519.
        try:
            _load_ed25519_public_key(pub_hex.encode("ascii"))
        except StopRequired as exc:
            raise StopRequired(
                "STOP_AUTHORITY_UNPROVEN",
                {
                    "reason": "issuer_public_key_unusable",
                    "issuer": issuer_id,
                    "key_id": key_id,
                },
            ) from exc
        seen_ids.add(issuer_id)
        seen_keys.add(key_id)
        out.append(
            {
                "id": issuer_id,
                "key_id": key_id,
                "public_key_ed25519": pub_hex,
                "roles": roles,
            }
        )
    return out


def expected_stage_coverage_rows(
    *,
    conflict_paths: Sequence[str],
    stage_blob_oids: Mapping[str, Mapping[str, str]],
) -> list[dict[str, str]]:
    """Exact path/stage/blob_oid rows required for capability evidence."""
    rows: list[dict[str, str]] = []
    for path in sorted(conflict_paths):
        stages = stage_blob_oids.get(path) or {}
        if not isinstance(stages, Mapping) or not stages:
            raise StopRequired(
                "STOP_AUTHORITY_UNPROVEN",
                {"reason": "stage_blob_oids_path_missing", "path": path},
            )
        stage_items = sorted(
            ((str(stage), str(oid)) for stage, oid in stages.items()),
            key=lambda item: (
                (0, int(item[0])) if item[0].isdigit() else (1, item[0])
            ),
        )
        for stage, blob_oid in stage_items:
            if not blob_oid:
                raise StopRequired(
                    "STOP_AUTHORITY_UNPROVEN",
                    {
                        "reason": "stage_blob_oid_empty",
                        "path": path,
                        "stage": stage,
                    },
                )
            rows.append(
                {"path": path, "stage": stage, "blob_oid": blob_oid}
            )
    return rows


def _normalize_capability_list(values: Any, *, field: str) -> list[str]:
    """Require a unique sorted capability list."""
    if not isinstance(values, list):
        raise StopRequired(
            "STOP_AUTHORITY_UNPROVEN",
            {"reason": f"{field}_invalid"},
        )
    caps = [str(item) for item in values]
    if any(not item for item in caps):
        raise StopRequired(
            "STOP_AUTHORITY_UNPROVEN",
            {"reason": f"{field}_empty_item"},
        )
    if len(caps) != len(set(caps)):
        raise StopRequired(
            "STOP_AUTHORITY_UNPROVEN",
            {"reason": f"{field}_not_unique"},
        )
    if caps != sorted(caps):
        raise StopRequired(
            "STOP_AUTHORITY_UNPROVEN",
            {"reason": f"{field}_not_sorted", "declared": caps, "expected": sorted(caps)},
        )
    return caps


def verify_capability_evidence(
    declaration: Mapping[str, Any],
    *,
    producer: Mapping[str, Any],
    expected_snapshot_id: str,
    conflict_paths: Sequence[str],
    stage_blob_oids: Mapping[str, Mapping[str, str]],
) -> dict[str, Any]:
    """Authenticate snapshot-bound capability completeness evidence.

    Local AST symbol→binding recomputation is diagnostic only and never proves
    completeness or ``none_applicable``.
    """
    evidence = declaration.get("capability_evidence")
    if evidence is None:
        raise StopRequired(
            "STOP_AUTHORITY_UNPROVEN",
            {
                "reason": "capability_evidence_missing",
                "note": (
                    "Capability completeness requires authenticated evidence from "
                    "a producer-authorized capability_attestor."
                ),
            },
        )
    if not isinstance(evidence, dict):
        raise StopRequired(
            "STOP_AUTHORITY_UNPROVEN",
            {"reason": "capability_evidence_invalid"},
        )
    required = (
        "schema",
        "classifier_id",
        "classifier_version",
        "conflict_snapshot_id",
        "stage_coverage",
        "capabilities",
        "analysis_complete",
        "unknown_targets",
        "observations",
    )
    for key in required:
        if key not in evidence:
            raise StopRequired(
                "STOP_AUTHORITY_UNPROVEN",
                {"reason": "capability_evidence_missing_field", "field": key},
            )
    if evidence.get("schema") != CAPABILITY_EVIDENCE_SCHEMA:
        raise StopRequired(
            "STOP_AUTHORITY_UNPROVEN",
            {
                "reason": "capability_evidence_schema_mismatch",
                "expected": CAPABILITY_EVIDENCE_SCHEMA,
                "declared": evidence.get("schema"),
            },
        )
    if not str(evidence.get("classifier_id") or "").strip():
        raise StopRequired(
            "STOP_AUTHORITY_UNPROVEN",
            {"reason": "capability_classifier_id_missing"},
        )
    if not str(evidence.get("classifier_version") or "").strip():
        raise StopRequired(
            "STOP_AUTHORITY_UNPROVEN",
            {"reason": "capability_classifier_version_missing"},
        )
    if evidence.get("conflict_snapshot_id") != expected_snapshot_id:
        raise StopRequired(
            "STOP_AUTHORITY_UNPROVEN",
            {
                "reason": "capability_evidence_snapshot_mismatch",
                "declared": evidence.get("conflict_snapshot_id"),
                "expected": expected_snapshot_id,
            },
        )
    if evidence.get("conflict_snapshot_id") != declaration.get("conflict_snapshot_id"):
        raise StopRequired(
            "STOP_AUTHORITY_UNPROVEN",
            {"reason": "capability_evidence_declaration_snapshot_mismatch"},
        )
    if evidence.get("analysis_complete") is not True:
        raise StopRequired(
            "STOP_AUTHORITY_UNPROVEN",
            {
                "reason": "capability_analysis_incomplete",
                "analysis_complete": evidence.get("analysis_complete"),
            },
        )
    unknown = evidence.get("unknown_targets")
    if not isinstance(unknown, list):
        raise StopRequired(
            "STOP_AUTHORITY_UNPROVEN",
            {"reason": "capability_unknown_targets_invalid"},
        )
    if unknown:
        raise StopRequired(
            "STOP_AUTHORITY_UNPROVEN",
            {
                "reason": "capability_unknown_targets_present",
                "unknown_targets": unknown,
            },
        )
    if not isinstance(evidence.get("observations"), list):
        raise StopRequired(
            "STOP_AUTHORITY_UNPROVEN",
            {"reason": "capability_observations_invalid"},
        )

    issuer_id = str(declaration["issuer"]["id"])
    entry = next(
        (
            row
            for row in (producer.get("issuer_entries") or [])
            if row["id"] == issuer_id
        ),
        None,
    )
    if entry is None:
        raise StopRequired(
            "STOP_AUTHORITY_UNPROVEN",
            {"reason": "unknown_issuer", "issuer": issuer_id},
        )
    roles = list(entry.get("roles") or [])
    if CAPABILITY_ATTESTOR_ROLE not in roles:
        raise StopRequired(
            "STOP_AUTHORITY_UNPROVEN",
            {
                "reason": "issuer_not_capability_attestor",
                "issuer": issuer_id,
                "roles": roles,
                "required_role": CAPABILITY_ATTESTOR_ROLE,
            },
        )

    expected_rows = expected_stage_coverage_rows(
        conflict_paths=conflict_paths,
        stage_blob_oids=stage_blob_oids,
    )
    coverage = evidence.get("stage_coverage")
    if not isinstance(coverage, list):
        raise StopRequired(
            "STOP_AUTHORITY_UNPROVEN",
            {"reason": "capability_stage_coverage_invalid"},
        )
    normalized_coverage: list[dict[str, str]] = []
    for row in coverage:
        if not isinstance(row, dict):
            raise StopRequired(
                "STOP_AUTHORITY_UNPROVEN",
                {"reason": "capability_stage_coverage_row_invalid"},
            )
        path = str(row.get("path") or "")
        stage = str(row.get("stage") or "")
        blob_oid = str(row.get("blob_oid") or "")
        if not path or not stage or not blob_oid:
            raise StopRequired(
                "STOP_AUTHORITY_UNPROVEN",
                {"reason": "capability_stage_coverage_row_incomplete", "row": row},
            )
        normalized_coverage.append(
            {"path": path, "stage": stage, "blob_oid": blob_oid}
        )
    expected_key = sorted(
        (row["path"], row["stage"], row["blob_oid"]) for row in expected_rows
    )
    actual_key = sorted(
        (row["path"], row["stage"], row["blob_oid"]) for row in normalized_coverage
    )
    if actual_key != expected_key:
        raise StopRequired(
            "STOP_AUTHORITY_UNPROVEN",
            {
                "reason": "capability_stage_coverage_mismatch",
                "expected": expected_rows,
                "declared": normalized_coverage,
            },
        )

    evidence_caps = _normalize_capability_list(
        evidence.get("capabilities"), field="capability_evidence_capabilities"
    )
    declared_caps = _normalize_capability_list(
        declaration.get("capabilities"), field="capabilities"
    )
    if evidence_caps != declared_caps:
        raise StopRequired(
            "STOP_AUTHORITY_UNPROVEN",
            {
                "reason": "capability_evidence_capabilities_mismatch",
                "evidence": evidence_caps,
                "declaration": declared_caps,
            },
        )

    if declaration["none_applicable"]:
        if evidence_caps:
            raise StopRequired(
                "STOP_AUTHORITY_UNPROVEN",
                {
                    "reason": "none_applicable_with_capability_evidence",
                    "capabilities": evidence_caps,
                },
            )
        if not producer["authorize_none_applicable"]:
            raise StopRequired(
                "STOP_AUTHORITY_UNPROVEN",
                {
                    "reason": "none_applicable_not_authorized_by_producer",
                    "note": (
                        "none_applicable requires producer authorization plus "
                        "complete empty authenticated capability evidence."
                    ),
                },
            )
    elif not evidence_caps:
        raise StopRequired(
            "STOP_AUTHORITY_UNPROVEN",
            {
                "reason": "capabilities_empty_without_none_applicable",
            },
        )

    # Diagnostic only: local AST→binding mapping cannot prove completeness.
    # Non-empty recomputed caps that are not covered by evidence STOP as
    # inconsistency; empty/matching recomputation never grants none_applicable.
    return {
        "schema": CAPABILITY_EVIDENCE_SCHEMA,
        "classifier_id": str(evidence["classifier_id"]),
        "classifier_version": str(evidence["classifier_version"]),
        "capabilities": evidence_caps,
        "stage_coverage_rows": len(normalized_coverage),
        "analysis_complete": True,
        "unknown_targets": [],
        "local_ast_role": "diagnostic_symbols_only",
    }


def canonicalize_declaration_payload(payload: Mapping[str, Any]) -> bytes:
    """Deterministic signed bytes for declaration payload (no external deps).

    Canonicalization:
    - UTF-8 JSON;
    - ``sort_keys=True``;
    - separators ``(",", ":")``;
    - ``ensure_ascii=True``;
    - exact payload field set (no envelope signature/key fields).
    """
    if not isinstance(payload, Mapping):
        raise StopRequired(
            "STOP_AUTHORITY_UNPROVEN",
            {"reason": "declaration_payload_invalid"},
        )
    missing = [k for k in DECLARATION_PAYLOAD_FIELD_ORDER if k not in payload]
    if missing:
        raise StopRequired(
            "STOP_AUTHORITY_UNPROVEN",
            {"reason": "declaration_payload_missing_field", "fields": missing},
        )
    extra = sorted(set(payload) - set(DECLARATION_PAYLOAD_FIELD_ORDER))
    if extra:
        raise StopRequired(
            "STOP_AUTHORITY_UNPROVEN",
            {"reason": "declaration_payload_unknown_field", "fields": extra},
        )
    ordered = {key: payload[key] for key in DECLARATION_PAYLOAD_FIELD_ORDER}
    return canonical_json(ordered)


def _validate_declaration_payload_shape(payload: Mapping[str, Any]) -> None:
    """Minimal schema gate for signed semantic payload."""
    for key in DECLARATION_PAYLOAD_FIELD_ORDER:
        if key not in payload:
            raise StopRequired(
                "STOP_AUTHORITY_UNPROVEN",
                {"reason": "declaration_missing_field", "field": key},
            )
    if payload.get("schema") != AUTHORITY_DECLARATION_SCHEMA:
        raise StopRequired(
            "STOP_AUTHORITY_UNPROVEN",
            {"reason": "declaration_schema_mismatch"},
        )
    if payload.get("symbol_extractor_version") != SYMBOL_EXTRACTOR_VERSION:
        raise StopRequired(
            "STOP_AUTHORITY_UNPROVEN",
            {
                "reason": "symbol_extractor_version_mismatch",
                "expected": SYMBOL_EXTRACTOR_VERSION,
                "declared": payload.get("symbol_extractor_version"),
            },
        )
    if payload.get("operation") not in {"merge", "rebase"}:
        raise StopRequired(
            "STOP_AUTHORITY_UNPROVEN",
            {"reason": "declaration_operation_invalid"},
        )
    if not isinstance(payload.get("none_applicable"), bool):
        raise StopRequired(
            "STOP_AUTHORITY_UNPROVEN",
            {"reason": "declaration_none_applicable_invalid"},
        )
    issuer = payload.get("issuer")
    if not isinstance(issuer, dict) or not issuer.get("id") or not issuer.get(
        "contract_path"
    ):
        raise StopRequired(
            "STOP_AUTHORITY_UNPROVEN",
            {"reason": "declaration_issuer_invalid"},
        )
    for digest_key in (
        "contracts_inventory_digest",
        "authority_inventory_digest",
        "producer_contract_sha256",
    ):
        digest = str(payload.get(digest_key, ""))
        if len(digest) != 64 or any(ch not in "0123456789abcdef" for ch in digest):
            raise StopRequired(
                "STOP_AUTHORITY_UNPROVEN",
                {"reason": "declaration_digest_invalid", "field": digest_key},
            )


def _authenticate_declaration_envelope(
    envelope: Mapping[str, Any],
    *,
    producer: Mapping[str, Any],
) -> dict[str, Any]:
    """Verify issuer-key binding + Ed25519 signature over canonical payload."""
    schema = envelope.get("schema")
    if schema == AUTHORITY_DECLARATION_SCHEMA_LEGACY_UNSIGNED or (
        isinstance(envelope, Mapping)
        and "payload" not in envelope
        and "signature" not in envelope
    ):
        raise StopRequired(
            "STOP_AUTHORITY_UNPROVEN",
            {
                "reason": "legacy_unsigned_declaration_rejected",
                "schema": schema,
                "note": (
                    "Unsigned v3/flat declarations are rejected in strict/GO "
                    "authority flow; no compatibility upgrade path."
                ),
            },
        )
    if schema == AUTHORITY_DECLARATION_SCHEMA_LEGACY_V4:
        raise StopRequired(
            "STOP_AUTHORITY_UNPROVEN",
            {
                "reason": "legacy_v4_declaration_rejected",
                "schema": schema,
                "note": (
                    "v4 declarations lack authenticated capability evidence; "
                    "no silent compatibility path to v5."
                ),
            },
        )
    if schema != AUTHORITY_DECLARATION_SCHEMA:
        raise StopRequired(
            "STOP_AUTHORITY_UNPROVEN",
            {"reason": "declaration_schema_mismatch", "schema": schema},
        )
    payload = envelope.get("payload")
    if not isinstance(payload, dict):
        raise StopRequired(
            "STOP_AUTHORITY_UNPROVEN",
            {"reason": "declaration_payload_missing"},
        )
    key_id = str(envelope.get("issuer_key_id") or "").strip()
    signature_hex = str(envelope.get("signature") or "").strip().lower()
    if not key_id:
        raise StopRequired(
            "STOP_AUTHORITY_UNPROVEN",
            {"reason": "declaration_issuer_key_id_missing"},
        )
    if (
        len(signature_hex) != 128
        or any(ch not in "0123456789abcdef" for ch in signature_hex)
    ):
        raise StopRequired(
            "STOP_AUTHORITY_UNPROVEN",
            {
                "reason": "declaration_signature_missing",
                "note": "Allowed issuer ID without a valid signature is STOP.",
            },
        )

    _validate_declaration_payload_shape(payload)
    issuer_id = str(payload["issuer"]["id"])
    entries = list(producer.get("issuer_entries") or [])
    match = next((row for row in entries if row["id"] == issuer_id), None)
    if match is None:
        raise StopRequired(
            "STOP_AUTHORITY_UNPROVEN",
            {
                "reason": "unknown_issuer",
                "issuer": issuer_id,
                "allowed": [row["id"] for row in entries],
                "producer_contract": producer["contract_path"],
            },
        )
    if match["key_id"] != key_id:
        raise StopRequired(
            "STOP_AUTHORITY_UNPROVEN",
            {
                "reason": "unknown_issuer_key_id",
                "issuer": issuer_id,
                "declared_key_id": key_id,
                "bound_key_id": match["key_id"],
            },
        )
    try:
        issuer_key = _load_ed25519_public_key(
            match["public_key_ed25519"].encode("ascii")
        )
    except StopRequired as exc:
        raise StopRequired(
            "STOP_AUTHORITY_UNPROVEN",
            {
                "reason": "issuer_public_key_unusable",
                "issuer": issuer_id,
                "key_id": key_id,
            },
        ) from exc
    canonical = canonicalize_declaration_payload(payload)
    try:
        issuer_key.verify(binascii.unhexlify(signature_hex), canonical)
    except (InvalidSignature, binascii.Error, ValueError) as exc:
        raise StopRequired(
            "STOP_AUTHORITY_UNPROVEN",
            {
                "reason": "declaration_signature_invalid",
                "issuer": issuer_id,
                "key_id": key_id,
                "note": (
                    "Signature must verify with the producer-bound issuer key; "
                    "no fallback to issuer ID string matching."
                ),
            },
        ) from exc
    return {
        "payload": payload,
        "issuer_id": issuer_id,
        "issuer_key_id": key_id,
        "canonical_sha256": sha256_bytes(canonical),
    }


def verify_rename_lineage_evidence(
    repo_root: Path,
    *,
    commit_oids: Mapping[str, str],
    conflict_paths: Sequence[str],
    declared_lineage: Mapping[str, Any],
) -> dict[str, Any]:
    """Compare declaration rename_lineage to fixed-argv Git rename evidence.

    ``git diff -M/-C`` is heuristic evidence, not absolute truth. Ambiguous
    or multi-candidate renames STOP rather than inventing precision.
    """
    if not isinstance(declared_lineage, dict):
        raise StopRequired(
            "STOP_AUTHORITY_UNPROVEN",
            {"reason": "rename_lineage_invalid"},
        )
    head = str(commit_oids.get("head", ""))
    other = str(commit_oids.get("operation_head", ""))
    argv = [
        "diff",
        f"-M{RENAME_THRESHOLD}",
        f"-C{RENAME_THRESHOLD}",
        "--name-status",
        "-z",
        head,
        other,
    ]
    # Always probe — empty declaration does not skip Git evidence (R22-HIGH-003).
    if not head or not other:
        raise StopRequired(
            "STOP_AUTHORITY_UNPROVEN",
            {"reason": "rename_endpoints_missing"},
        )
    git = TypedGit(repo_root)
    try:
        text = git.diff_tree_name_status_z(head, other)
    except StopRequired as exc:
        raise StopRequired(
            "STOP_AUTHORITY_UNPROVEN",
            {
                "reason": "rename_evidence_unavailable",
                "argv": argv,
                "threshold": RENAME_THRESHOLD,
            },
        ) from exc

    evidence: dict[str, list[str]] = {}
    ambiguous: list[str] = []
    # NUL-delimited name-status: STATUS\0path[\0path2]\0...
    parts = [p for p in text.split("\0") if p]
    i = 0
    while i < len(parts):
        status = parts[i]
        code = status[:1] if status else ""
        if code in {"R", "C"}:
            if i + 2 >= len(parts):
                ambiguous.append(status)
                break
            src, dst = parts[i + 1], parts[i + 2]
            evidence.setdefault(dst, []).append(src)
            if len(evidence[dst]) > 1:
                ambiguous.append(dst)
            i += 3
            continue
        i += 2 if i + 1 < len(parts) else 1

    if ambiguous:
        raise StopRequired(
            "STOP_AUTHORITY_UNPROVEN",
            {
                "reason": "rename_evidence_ambiguous",
                "ambiguous": sorted(set(ambiguous)),
                "argv": argv,
                "threshold": RENAME_THRESHOLD,
                "note": "Git rename detection is heuristic; ambiguity requires STOP",
            },
        )

    for path in conflict_paths:
        declared = declared_lineage.get(path)
        if declared is None:
            declared_list: list[str] = []
        elif isinstance(declared, list):
            declared_list = [str(item) for item in declared]
        else:
            raise StopRequired(
                "STOP_AUTHORITY_UNPROVEN",
                {"reason": "rename_lineage_path_invalid", "path": path},
            )
        evidenced = evidence.get(path, [])
        if declared_list and sorted(declared_list) != sorted(evidenced):
            raise StopRequired(
                "STOP_AUTHORITY_UNPROVEN",
                {
                    "reason": "rename_lineage_mismatch",
                    "path": path,
                    "declared": declared_list,
                    "evidence": evidenced,
                    "argv": argv,
                },
            )
        if evidenced and not declared_list:
            raise StopRequired(
                "STOP_AUTHORITY_UNPROVEN",
                {
                    "reason": "rename_lineage_omitted",
                    "path": path,
                    "evidence": evidenced,
                },
            )
    return {
        "argv": argv,
        "threshold": RENAME_THRESHOLD,
        "evidence_paths": sorted(evidence),
        "note": "Git -M/-C is heuristic evidence, not absolute truth",
    }


def verify_external_authority_declaration(
    repo_root: Path,
    *,
    declaration_rel: str,
    expected_snapshot_id: str,
    operation: str,
    commit_oids: Mapping[str, str],
    stage_blob_oids: Mapping[str, Mapping[str, str]],
    conflict_paths: Sequence[str],
    source_commit: str,
) -> dict[str, Any]:
    """Verify an external declaration against live conflict snapshot.

    Raises:
        StopRequired: on missing external authority root, unknown issuer,
            digest mismatch, incomplete inventory, or contradictory requirements.
    """
    producer = load_authenticated_authority_root(repo_root)

    try:
        _, decl_path = resolve_existing_under_repo(repo_root, declaration_rel)
    except StopRequired as exc:
        raise StopRequired(
            "STOP_AUTHORITY_UNPROVEN",
            {"reason": "declaration_missing", "path": declaration_rel},
        ) from exc
    if decl_path.is_symlink() or not decl_path.is_file():
        raise StopRequired(
            "STOP_AUTHORITY_UNPROVEN",
            {"reason": "declaration_missing", "path": declaration_rel},
        )
    try:
        raw = decl_path.read_bytes()
        declaration = json.loads(raw.decode("utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise StopRequired(
            "STOP_AUTHORITY_UNPROVEN",
            {"reason": "declaration_invalid_json", "path": declaration_rel},
        ) from exc
    if not isinstance(declaration, dict):
        raise StopRequired(
            "STOP_AUTHORITY_UNPROVEN",
            {"reason": "declaration_not_object"},
        )
    auth = _authenticate_declaration_envelope(declaration, producer=producer)
    declaration = auth["payload"]
    issuer_id = auth["issuer_id"]

    if str(declaration.get("producer_contract_sha256", "")).lower() != producer[
        "sha256"
    ]:
        raise StopRequired(
            "STOP_AUTHORITY_UNPROVEN",
            {
                "reason": "producer_contract_sha256_mismatch",
                "expected": producer["sha256"],
                "declared": declaration.get("producer_contract_sha256"),
            },
        )

    if str(declaration["issuer"]["contract_path"]) != producer["contract_path"]:
        raise StopRequired(
            "STOP_AUTHORITY_UNPROVEN",
            {
                "reason": "issuer_contract_mismatch",
                "declared": declaration["issuer"]["contract_path"],
                "expected": producer["contract_path"],
            },
        )

    if declaration.get("conflict_snapshot_id") != expected_snapshot_id:
        raise StopRequired(
            "STOP_AUTHORITY_UNPROVEN",
            {
                "reason": "conflict_snapshot_mismatch",
                "declared": declaration.get("conflict_snapshot_id"),
                "expected": expected_snapshot_id,
            },
        )
    if declaration.get("operation") != operation:
        raise StopRequired(
            "STOP_AUTHORITY_UNPROVEN",
            {"reason": "operation_mismatch"},
        )
    if declaration.get("source_commit") != source_commit:
        raise StopRequired(
            "STOP_AUTHORITY_UNPROVEN",
            {"reason": "source_commit_mismatch"},
        )
    declared_oids = declaration.get("conflicting_commit_oids")
    if not isinstance(declared_oids, dict):
        raise StopRequired(
            "STOP_AUTHORITY_UNPROVEN",
            {"reason": "commit_oids_invalid"},
        )
    for role in ("head", "operation_head"):
        if str(declared_oids.get(role, "")) != str(commit_oids.get(role, "")):
            raise StopRequired(
                "STOP_AUTHORITY_UNPROVEN",
                {"reason": "commit_oid_mismatch", "role": role},
            )
    if sorted(declaration.get("paths") or []) != sorted(conflict_paths):
        raise StopRequired(
            "STOP_AUTHORITY_UNPROVEN",
            {"reason": "paths_mismatch"},
        )
    declared_stages = declaration.get("stage_blob_oids")
    if not isinstance(declared_stages, dict):
        raise StopRequired(
            "STOP_AUTHORITY_UNPROVEN",
            {"reason": "stage_blob_oids_invalid"},
        )
    for path in conflict_paths:
        expected = {
            str(stage): oid
            for stage, oid in (stage_blob_oids.get(path) or {}).items()
        }
        actual_raw = declared_stages.get(path) or {}
        if not isinstance(actual_raw, dict):
            raise StopRequired(
                "STOP_AUTHORITY_UNPROVEN",
                {"reason": "stage_blob_oids_path_invalid", "path": path},
            )
        actual = {str(k): str(v) for k, v in actual_raw.items()}
        if actual != expected:
            raise StopRequired(
                "STOP_AUTHORITY_UNPROVEN",
                {
                    "reason": "stage_blob_oid_mismatch",
                    "path": path,
                    "expected": expected,
                    "declared": actual,
                },
            )

    applicable = declaration.get("applicable_authorities")
    if not isinstance(applicable, list):
        raise StopRequired(
            "STOP_AUTHORITY_UNPROVEN",
            {"reason": "applicable_authorities_invalid"},
        )
    if declaration["none_applicable"] and applicable:
        raise StopRequired(
            "STOP_AUTHORITY_UNPROVEN",
            {"reason": "none_applicable_contradiction"},
        )
    if not declaration["none_applicable"] and not applicable:
        raise StopRequired(
            "STOP_AUTHORITY_UNPROVEN",
            {"reason": "applicable_authorities_empty"},
        )

    # Closed authoritative root inventory (not two hardcoded globs).
    recomputed_contracts = recompute_contracts_inventory_digest(
        repo_root,
        producer["authoritative_roots"],
    )
    if recomputed_contracts != declaration["contracts_inventory_digest"]:
        raise StopRequired(
            "STOP_AUTHORITY_UNPROVEN",
            {
                "reason": "contracts_inventory_digest_mismatch",
                "expected": recomputed_contracts,
                "declared": declaration["contracts_inventory_digest"],
            },
        )

    # Mechanical symbols from stage blobs; invent/omit/parse-fail → STOP.
    declared_symbols = declaration.get("symbols")
    if not isinstance(declared_symbols, list):
        raise StopRequired(
            "STOP_AUTHORITY_UNPROVEN",
            {"reason": "symbols_invalid"},
        )
    git = TypedGit(repo_root)
    recomputed_symbols = recompute_mechanical_symbols_from_stages(
        git,
        conflict_paths=conflict_paths,
        stage_blob_oids=stage_blob_oids,
    )
    if sorted(str(s) for s in declared_symbols) != recomputed_symbols:
        raise StopRequired(
            "STOP_AUTHORITY_UNPROVEN",
            {
                "reason": "symbols_mismatch",
                "declared": sorted(str(s) for s in declared_symbols),
                "recomputed": recomputed_symbols,
                "extractor": SYMBOL_EXTRACTOR_VERSION,
            },
        )

    # Capability completeness: authenticated evidence only (R27 / R25-HIGH-002).
    # Local AST → capability_bindings recomputation is diagnostic and never
    # proves completeness or none_applicable by itself.
    capability_proof = verify_capability_evidence(
        declaration,
        producer=producer,
        expected_snapshot_id=expected_snapshot_id,
        conflict_paths=conflict_paths,
        stage_blob_oids=stage_blob_oids,
    )
    diagnostic_caps = recompute_capabilities_from_bindings(
        recomputed_symbols,
        producer["capability_bindings"],
    )
    evidence_cap_set = set(capability_proof["capabilities"])
    if diagnostic_caps and not set(diagnostic_caps).issubset(evidence_cap_set):
        raise StopRequired(
            "STOP_AUTHORITY_UNPROVEN",
            {
                "reason": "capability_diagnostic_bindings_exceed_evidence",
                "diagnostic": diagnostic_caps,
                "evidence": capability_proof["capabilities"],
                "note": (
                    "Local symbol→binding mapping is diagnostic only; it cannot "
                    "replace authenticated capability evidence, and must not "
                    "claim capabilities absent from that evidence."
                ),
            },
        )

    rename_proof = verify_rename_lineage_evidence(
        repo_root,
        commit_oids=commit_oids,
        conflict_paths=conflict_paths,
        declared_lineage=declaration.get("rename_lineage") or {},
    )

    inventory_rows: list[dict[str, str]] = []
    for row in applicable:
        if not isinstance(row, dict):
            raise StopRequired(
                "STOP_AUTHORITY_UNPROVEN",
                {"reason": "authority_row_invalid"},
            )
        rel = str(row.get("path", ""))
        expected_hash = str(row.get("sha256", "")).lower()
        try:
            _, path = resolve_existing_under_repo(repo_root, rel)
        except StopRequired as exc:
            raise StopRequired(
                "STOP_AUTHORITY_UNPROVEN",
                {"reason": "authority_inventory_incomplete", "path": rel},
            ) from exc
        if path.is_symlink() or not path.is_file():
            raise StopRequired(
                "STOP_AUTHORITY_UNPROVEN",
                {"reason": "authority_inventory_incomplete", "path": rel},
            )
        actual_hash = sha256_bytes(path.read_bytes())
        if actual_hash != expected_hash:
            raise StopRequired(
                "STOP_AUTHORITY_UNPROVEN",
                {
                    "reason": "authority_digest_mismatch",
                    "path": rel,
                    "expected": expected_hash,
                    "actual": actual_hash,
                },
            )
        inventory_rows.append(
            {
                "path": rel,
                "role": str(row.get("role", "")),
                "sha256": actual_hash,
            }
        )
    recomputed_inventory = sha256_canonical(inventory_rows)
    if recomputed_inventory != declaration["authority_inventory_digest"]:
        if declaration["none_applicable"] and not inventory_rows:
            empty_digest = sha256_canonical([])
            if declaration["authority_inventory_digest"] != empty_digest:
                raise StopRequired(
                    "STOP_AUTHORITY_UNPROVEN",
                    {
                        "reason": "authority_inventory_digest_mismatch",
                        "expected": empty_digest,
                        "declared": declaration["authority_inventory_digest"],
                    },
                )
        else:
            raise StopRequired(
                "STOP_AUTHORITY_UNPROVEN",
                {
                    "reason": "authority_inventory_digest_mismatch",
                    "expected": recomputed_inventory,
                    "declared": declaration["authority_inventory_digest"],
                },
            )

    return {
        "declaration_path": declaration_rel,
        "declaration_sha256": sha256_bytes(raw),
        "producer_contract": producer["contract_path"],
        "producer_contract_sha256": producer["sha256"],
        "issuer": issuer_id,
        "issuer_key_id": auth["issuer_key_id"],
        "declaration_canonical_sha256": auth["canonical_sha256"],
        "none_applicable": declaration["none_applicable"],
        "capabilities": list(capability_proof["capabilities"]),
        "capability_evidence": {
            "schema": capability_proof["schema"],
            "classifier_id": capability_proof["classifier_id"],
            "classifier_version": capability_proof["classifier_version"],
            "analysis_complete": True,
            "stage_coverage_rows": capability_proof["stage_coverage_rows"],
            "local_ast_role": capability_proof["local_ast_role"],
        },
        "applicable_authorities": inventory_rows,
        "conflict_snapshot_id": expected_snapshot_id,
        "contracts_inventory_digest": recomputed_contracts,
        "rename_proof": rename_proof,
        "path_stem_heuristic_forbidden": True,
    }


def _collect_stage_blob_oids(
    git: TypedGit,
    conflict_paths: Sequence[str],
) -> dict[str, dict[str, str]]:
    """Map conflict path → stage number → blob OID from the unmerged index."""
    from .operation import parse_unmerged_z

    wanted = set(conflict_paths)
    out: dict[str, dict[str, str]] = {path: {} for path in conflict_paths}
    for entry in parse_unmerged_z(git.ls_files_unmerged_z()):
        if entry.path not in wanted:
            continue
        out.setdefault(entry.path, {})[str(entry.stage)] = entry.oid
    return out


def _resolve_strict_manifest_authority(
    repo_root: Path,
    *,
    run_id: str,
    fingerprint: str,
    scope_sha256: str,
    conflict_paths: Sequence[str],
    change_id: str | None,
    commit_oids: Mapping[str, str],
    operation: str | None = None,
    source_commit: str | None = None,
    stage_blob_oids: Mapping[str, Mapping[str, str]] | None = None,
    store_id: str | None = None,
) -> Proof:
    """Bind commit trailers and external declaration for strict GO authority."""
    del store_id  # reserved orchestrator kw; unused by consumer verifier
    if not change_id:
        raise StopRequired("APPLICABLE_AUTHORITY_CHANGE_REQUIRED")
    if operation not in {"merge", "rebase"}:
        raise StopRequired(
            "STOP_AUTHORITY_UNPROVEN",
            {
                "reason": "operation_required_for_strict_authority",
                "operation": operation,
            },
        )
    manifest_rel = f"openspec/changes/{change_id}/conflict-authority.json"
    _, manifest_path = resolve_existing_under_repo(repo_root, manifest_rel)
    if manifest_path.is_symlink() or not manifest_path.is_file():
        raise StopRequired(
            "AUTHORITY_BINDING_MANIFEST_MISSING",
            {"path": manifest_rel},
        )
    try:
        manifest_bytes = manifest_path.read_bytes()
        manifest = json.loads(manifest_bytes.decode("utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise StopRequired(
            "AUTHORITY_BINDING_MANIFEST_INVALID",
            {"path": manifest_rel},
        ) from exc
    expected_paths = sorted(set(conflict_paths))
    path_bindings = manifest.get("paths")
    if (
        manifest.get("schema") != AUTHORITY_BINDING_SCHEMA
        or manifest.get("change_id") != change_id
        or manifest.get("precedence")
        != ["accepted_decision", "main_spec", "active_change"]
        or not isinstance(path_bindings, dict)
        or sorted(path_bindings) != expected_paths
    ):
        raise StopRequired(
            "AUTHORITY_BINDING_MANIFEST_MISMATCH",
            {"path": manifest_rel, "conflict_paths": expected_paths},
        )

    trailer = f"OPSX-Change: {change_id}"
    git = TypedGit(repo_root)
    lineage: dict[str, str] = {}
    for role in ("head", "operation_head"):
        oid = str(commit_oids.get(role, ""))
        if not oid or trailer not in {
            line.strip() for line in git.commit_message(oid).splitlines()
        }:
            raise StopRequired(
                "AUTHORITY_COMMIT_LINEAGE_UNBOUND",
                {"role": role, "oid": oid, "required_trailer": trailer},
            )
        lineage[role] = oid

    effective_source_commit = (source_commit or lineage.get("head") or "").lower()
    if not effective_source_commit:
        raise StopRequired(
            "STOP_AUTHORITY_UNPROVEN",
            {"reason": "source_commit_missing"},
        )
    stages = (
        {k: dict(v) for k, v in stage_blob_oids.items()}
        if stage_blob_oids is not None
        else _collect_stage_blob_oids(git, expected_paths)
    )
    snapshot_id = compute_conflict_snapshot_id(
        source_commit=effective_source_commit,
        operation=operation,
        commit_oids=lineage,
        stage_blob_oids=stages,
        paths=expected_paths,
    )

    sources: list[dict[str, Any]] = [
        {
            "path": manifest_rel,
            "sha256": sha256_bytes(manifest_bytes),
            "role": "authority_binding_manifest",
        },
        {
            "path": "git://operation_lineage",
            "sha256": sha256_text(json.dumps(lineage, sort_keys=True)),
            "role": "git_object_lineage",
            "oids": lineage,
        },
    ]
    applicability: dict[str, str] = {}
    allowed_prefixes = (
        f"openspec/changes/{change_id}/",
        "openspec/specs/",
        "openspec/decisions/",
        ".cursor/commands/",
        ".cursor/rules/",
    )
    declaration_proof: dict[str, Any] | None = None

    for conflict_path in expected_paths:
        binding = path_bindings.get(conflict_path)
        authority_paths = (
            binding.get("authority") if isinstance(binding, dict) else None
        )
        if (
            not isinstance(authority_paths, list)
            or not authority_paths
            or binding.get("strategy")
            != "namespace_closed_comment_exact_ast_union"
        ):
            raise StopRequired(
                "AUTHORITY_PATH_APPLICABILITY_UNPROVEN",
                {"path": conflict_path},
            )
        external_authority = binding.get("external_authority")
        if external_authority not in {
            "none_applicable",
            "includes_main_or_decision",
        }:
            raise StopRequired(
                "STOP_AUTHORITY_UNPROVEN",
                {
                    "path": conflict_path,
                    "required_field": "external_authority",
                },
            )

        for rel in authority_paths:
            if not isinstance(rel, str) or not rel.startswith(allowed_prefixes):
                raise StopRequired(
                    "AUTHORITY_SOURCE_PATH_INVALID",
                    {"path": rel},
                )
            try:
                _, source_path = resolve_existing_under_repo(repo_root, rel)
            except StopRequired as exc:
                if exc.reason == "PATH_NOT_FOUND":
                    raise StopRequired(
                        "APPLICABLE_SEMANTIC_AUTHORITY_MISSING",
                        {"path": rel},
                    ) from exc
                raise
            if source_path.is_symlink() or not source_path.is_file():
                raise StopRequired(
                    "APPLICABLE_SEMANTIC_AUTHORITY_MISSING",
                    {"path": rel},
                )
            source_bytes = source_path.read_bytes()
            role = (
                "accepted_decision"
                if rel.startswith("openspec/decisions/")
                else "main_spec"
                if rel.startswith("openspec/specs/")
                else "active_change"
            )
            source = {
                "path": rel,
                "sha256": sha256_bytes(source_bytes),
                "role": role,
                "applies_to": conflict_path,
            }
            if source not in sources:
                sources.append(source)

        path_roles = {
            str(source.get("role"))
            for source in sources
            if source.get("applies_to") == conflict_path
        }
        if external_authority == "includes_main_or_decision" and not (
            path_roles & {"main_spec", "accepted_decision"}
        ):
            raise StopRequired(
                "STOP_AUTHORITY_UNPROVEN",
                {
                    "path": conflict_path,
                    "roles": sorted(path_roles),
                },
            )
        if external_authority == "none_applicable" and (
            path_roles & {"main_spec", "accepted_decision"}
        ):
            raise StopRequired(
                "AUTHORITY_COMPLETENESS_CONTRADICTION",
                {"path": conflict_path, "roles": sorted(path_roles)},
            )

        # R24: none_applicable requires externally authenticated declaration.
        if external_authority == "none_applicable":
            declaration_rel = binding.get("authority_declaration")
            if not isinstance(declaration_rel, str) or not declaration_rel:
                declaration_rel = (
                    f"openspec/changes/{change_id}/authority-declaration.json"
                )
            declaration_proof = verify_external_authority_declaration(
                repo_root,
                declaration_rel=declaration_rel,
                expected_snapshot_id=snapshot_id,
                operation=operation,
                commit_oids=lineage,
                stage_blob_oids=stages,
                conflict_paths=expected_paths,
                source_commit=effective_source_commit,
            )
            if not declaration_proof["none_applicable"]:
                raise StopRequired(
                    "STOP_AUTHORITY_UNPROVEN",
                    {"reason": "declaration_rejects_none_applicable"},
                )
            sources.append(
                {
                    "path": declaration_rel,
                    "sha256": declaration_proof["declaration_sha256"],
                    "role": "external_authority_declaration",
                }
            )
        applicability[conflict_path] = "explicit_manifest_binding"

    return Proof.issue(
        "AUTHORITY",
        run_id=run_id,
        fingerprint=fingerprint,
        scope_sha256=scope_sha256,
        payload={
            "sources": sources,
            "applicability": applicability,
            "declaration": declaration_proof,
            "path_stem_heuristic_forbidden": True,
            "consumer_trust_enforcement": "external_authority_root_required",
        },
    )


def resolve_authority(
    repo_root: Path,
    *,
    run_id: str,
    fingerprint: str,
    scope_sha256: str,
    conflict_paths: Sequence[str],
    change_id: str | None = None,
    commit_oids: Mapping[str, str] | None = None,
    strict: bool = False,
    operation: str | None = None,
    source_commit: str | None = None,
    stage_blob_oids: Mapping[str, Mapping[str, str]] | None = None,
    store_id: str | None = None,
) -> Proof:
    """Resolve applicable authority for conflict paths.

    In strict/GO mode, ``none_applicable`` requires an externally authenticated
    producer root and declaration. Path/stem heuristics are forbidden.

    Args:
        store_id: Opaque store identifier from the orchestrator (reserved;
            consumer trust does not mint declarations from store state).
    """
    if strict:
        return _resolve_strict_manifest_authority(
            repo_root,
            run_id=run_id,
            fingerprint=fingerprint,
            scope_sha256=scope_sha256,
            conflict_paths=conflict_paths,
            change_id=change_id,
            commit_oids=commit_oids or {},
            operation=operation,
            source_commit=source_commit,
            stage_blob_oids=stage_blob_oids,
            store_id=store_id,
        )
    # Preview: static binding proof without GO declaration completeness.
    sources: list[dict[str, Any]] = []
    if change_id:
        for rel in (
            f"openspec/changes/{change_id}/proposal.md",
            f"openspec/changes/{change_id}/design.md",
        ):
            candidate = repo_root / rel
            if candidate.is_file() and not candidate.is_symlink():
                sources.append(
                    {
                        "path": rel,
                        "sha256": sha256_bytes(candidate.read_bytes()),
                        "role": "active_change",
                    }
                )
    return Proof.issue(
        "AUTHORITY",
        run_id=run_id,
        fingerprint=fingerprint,
        scope_sha256=scope_sha256,
        payload={
            "sources": sources,
            "mode": "preview",
            "path_stem_heuristic_forbidden": True,
        },
    )
