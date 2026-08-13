#!/usr/bin/env python3
"""Build origin vs host-contract-snapshot lineage mapping (R24).

Separates:
- ``origin_source_commit`` — real repository lineage
- ``host_contract_snapshot_commit`` — synthetic immutable tree of packaged
  contract bytes (never recorded as ordinary OPSX ``source_commit``)

Ship STOPS when a normative host contract is missing or differs in the origin
tree unless an external signed provenance file is supplied via
``OPSX_LINEAGE_SIGNED_PROVENANCE`` (package self-sign is rejected).
"""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

PACKAGE_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = PACKAGE_ROOT.parents[1]


def sha256_bytes(data: bytes) -> str:
    """Return SHA-256 hex digest of bytes."""
    return hashlib.sha256(data).hexdigest()


def git_show(commit: str, rel: str) -> bytes | None:
    """Return blob bytes for commit:path or None if missing."""
    proc = subprocess.run(
        ["git", "-C", str(REPO_ROOT), "show", f"{commit}:{rel}"],
        capture_output=True,
        check=False,
    )
    if proc.returncode != 0:
        return None
    return proc.stdout


def git_blob_oid(commit: str, rel: str) -> str | None:
    """Return blob OID for commit:path when present."""
    proc = subprocess.run(
        ["git", "-C", str(REPO_ROOT), "ls-tree", commit, "--", rel],
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode != 0 or not proc.stdout.strip():
        return None
    parts = proc.stdout.strip().split(None, 3)
    if len(parts) < 3 or parts[1] != "blob":
        return None
    return parts[2]


def _external_signed_provenance_allows(path: str) -> bool:
    """Accept only independently signed provenance (never ship-generated).

    Requires ``OPSX_LINEAGE_SIGNED_PROVENANCE`` pointing to a JSON payload with
    ``signature_ed25519_hex`` over canonical ``allowed_origin_drift_paths``
    bytes, verified against the OS-pinned authority trust pubkey. Package ship
    scripts must not create this file.
    """
    from cryptography.exceptions import InvalidSignature
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
    from cryptography.hazmat.primitives.serialization import load_pem_public_key
    import binascii
    import stat as statmod

    # Import OS pubkey path from runtime when available.
    try:
        from opsx_conflict.authority import os_authority_trust_pubkey_path
    except Exception:
        return False

    prov = os.environ.get("OPSX_LINEAGE_SIGNED_PROVENANCE", "").strip()
    if not prov:
        return False
    prov_path = Path(prov)
    if not prov_path.is_file() or prov_path.is_symlink():
        return False
    try:
        if PACKAGE_ROOT.resolve() in prov_path.resolve().parents:
            return False
    except OSError:
        return False
    try:
        payload = json.loads(prov_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return False
    allowed = payload.get("allowed_origin_drift_paths") or []
    sig_hex = str(payload.get("signature_ed25519_hex") or "").strip().lower()
    if not isinstance(allowed, list) or path not in allowed or len(sig_hex) != 128:
        return False
    pubkey_path = os_authority_trust_pubkey_path()
    try:
        st = os.lstat(pubkey_path)
        if statmod.S_ISLNK(st.st_mode) or not pubkey_path.is_file():
            return False
        raw_key = pubkey_path.read_bytes()
        if b"BEGIN" in raw_key:
            key = load_pem_public_key(raw_key)
        else:
            key = Ed25519PublicKey.from_public_bytes(
                binascii.unhexlify(raw_key.strip())
                if len(raw_key.strip()) == 64
                else raw_key
            )
        if not isinstance(key, Ed25519PublicKey):
            return False
        message = json.dumps(
            {
                "origin_source_commit": payload.get("origin_source_commit"),
                "allowed_origin_drift_paths": sorted(str(p) for p in allowed),
            },
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        key.verify(binascii.unhexlify(sig_hex), message)
    except (OSError, InvalidSignature, ValueError, TypeError, binascii.Error):
        return False
    return True


def _build_snapshot_commit(files: list[tuple[str, bytes]]) -> tuple[str, dict[str, str]]:
    """Create a synthetic git commit tree of packaged contract bytes.

    Returns:
        (commit_oid, {repository_path: blob_oid})
    """
    with tempfile.TemporaryDirectory(prefix="opsx-lineage-snap-") as tmp:
        tmp_path = Path(tmp)
        subprocess.run(
            ["git", "init", "--quiet"],
            cwd=tmp_path,
            check=True,
            capture_output=True,
        )
        subprocess.run(
            ["git", "config", "user.email", "opsx-lineage@local"],
            cwd=tmp_path,
            check=True,
            capture_output=True,
        )
        subprocess.run(
            ["git", "config", "user.name", "OPSX Lineage Snapshot"],
            cwd=tmp_path,
            check=True,
            capture_output=True,
        )
        blob_oids: dict[str, str] = {}
        for rel, data in files:
            dest = tmp_path / rel
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(data)
            proc = subprocess.run(
                ["git", "hash-object", "-w", "--", rel],
                cwd=tmp_path,
                capture_output=True,
                text=True,
                check=True,
            )
            blob_oids[rel] = proc.stdout.strip()
            subprocess.run(
                ["git", "add", "--", rel],
                cwd=tmp_path,
                check=True,
                capture_output=True,
            )
        subprocess.run(
            [
                "git",
                "commit",
                "--quiet",
                "-m",
                "opsx host_contract_snapshot (synthetic; not OPSX origin)",
            ],
            cwd=tmp_path,
            check=True,
            capture_output=True,
        )
        commit = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=tmp_path,
            capture_output=True,
            text=True,
            check=True,
        ).stdout.strip()
        return commit, blob_oids


def main() -> None:
    """Write origin/snapshot lineage mapping next to packaged host contracts."""
    manifest = json.loads((PACKAGE_ROOT / "MANIFEST.json").read_text(encoding="utf-8"))
    origin = str(
        manifest.get("origin_source_commit") or manifest.get("source_commit") or ""
    ).strip()
    if not origin:
        proc = subprocess.run(
            ["git", "-C", str(REPO_ROOT), "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            check=True,
        )
        origin = proc.stdout.strip()

    # Never treat synthetic snapshot as ordinary source_commit.
    if manifest.get("source_commit") and manifest.get("source_commit") == manifest.get(
        "host_contract_snapshot_commit"
    ):
        raise SystemExit(
            "lineage STOP: MANIFEST source_commit must not equal "
            "host_contract_snapshot_commit"
        )

    categories = manifest.get("input_categories") or {}
    host_list = categories.get("host_frozen_contracts") or []
    host_hashes_raw = manifest.get("host_contract_sha256") or {}
    # Prefer exact host_frozen set; never lineage-check dropped origin-absent paths.
    if isinstance(host_list, list) and host_list:
        host_hashes = {}
        for rel in host_list:
            if not isinstance(rel, str):
                continue
            if isinstance(host_hashes_raw, dict) and rel in host_hashes_raw:
                host_hashes[rel] = host_hashes_raw[rel]
            elif (REPO_ROOT / rel).is_file():
                host_hashes[rel] = sha256_bytes((REPO_ROOT / rel).read_bytes())
    elif isinstance(host_hashes_raw, dict) and host_hashes_raw:
        host_hashes = dict(host_hashes_raw)
    else:
        fallback = manifest.get("required_repo_paths") or []
        host_hashes = {
            rel: sha256_bytes((REPO_ROOT / rel).read_bytes())
            for rel in fallback
            if isinstance(rel, str) and (REPO_ROOT / rel).is_file()
        }

    packaged: list[tuple[str, bytes]] = []
    files: list[dict[str, str]] = []
    origin_stops: list[str] = []

    for repo_path, expected_sha in sorted(host_hashes.items()):
        wt = REPO_ROOT / repo_path
        if not wt.is_file():
            origin_stops.append(f"missing_working_tree:{repo_path}")
            continue
        data = wt.read_bytes()
        wt_sha = sha256_bytes(data)
        if wt_sha != expected_sha:
            origin_stops.append(f"manifest_hash_mismatch:{repo_path}")
            continue
        packaged.append((repo_path, data))

        origin_bytes = git_show(origin, repo_path)
        origin_oid = git_blob_oid(origin, repo_path) or ""
        if origin_bytes is None or sha256_bytes(origin_bytes) != wt_sha:
            if _external_signed_provenance_allows(repo_path):
                binding = "origin_drift_externally_provenanced"
                note = (
                    "Origin tree missing/differs; external signed provenance "
                    "allows packaging. Synthetic snapshot proves packaged-byte "
                    "immutability only."
                )
            else:
                origin_stops.append(f"origin_drift:{repo_path}")
                continue
        else:
            binding = "origin_source_blob"
            note = (
                "Packaged bytes match origin_source_commit blob; "
                "snapshot commit proves packaged-byte immutability only."
            )

        files.append(
            {
                "repository_path": repo_path,
                "package_path": f"context/host_contracts/{repo_path}",
                "origin_blob_oid": origin_oid,
                "snapshot_blob_oid": "",  # filled after snapshot commit
                "sha256": wt_sha,
                "binding": binding,
                "note": note,
            }
        )

    if origin_stops:
        raise SystemExit(
            "lineage STOP: origin_source_commit drift/missing without external "
            f"signed provenance: {origin_stops}"
        )

    snapshot_commit, snapshot_blobs = _build_snapshot_commit(packaged)
    for row in files:
        row["snapshot_blob_oid"] = snapshot_blobs.get(row["repository_path"], "")

    payload = {
        "schema": "opsx-resolve-conflict/source-lineage/v2",
        "origin_source_commit": origin,
        "host_contract_snapshot_commit": snapshot_commit,
        "package_version": manifest.get("package_version"),
        "note": (
            "host_contract_snapshot_commit is a synthetic immutable tree of "
            "packaged contracts and must never be treated as OPSX origin "
            "source_commit."
        ),
        "files": files,
    }
    out = PACKAGE_ROOT / "context" / "SOURCE_LINEAGE.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

    # Persist origin/snapshot fields on MANIFEST without overwriting origin into
    # a synthetic OID under the ordinary source_commit field.
    manifest["origin_source_commit"] = origin
    manifest["host_contract_snapshot_commit"] = snapshot_commit
    if "source_commit" in manifest and manifest["source_commit"] == snapshot_commit:
        raise SystemExit("lineage STOP: refused to record synthetic OID as source_commit")
    # Keep source_commit as origin if present; never set it to snapshot.
    if not manifest.get("source_commit"):
        manifest["source_commit"] = origin
    (PACKAGE_ROOT / "MANIFEST.json").write_text(
        json.dumps(manifest, indent=2) + "\n",
        encoding="utf-8",
    )
    print(
        f"wrote {out} files={len(files)} "
        f"origin={origin[:12]} snapshot={snapshot_commit[:12]}"
    )


if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    main()
