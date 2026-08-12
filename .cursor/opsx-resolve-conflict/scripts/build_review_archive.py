#!/usr/bin/env python3
"""Build self-contained R24 review zip with SHA256SUMS and Cursor authorship."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import sys
import zipfile
from datetime import datetime, timezone
from pathlib import Path

_SCRIPTS_DIR = Path(__file__).resolve().parent
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

from path_workspace import native_artifact_root  # noqa: E402

PACKAGE_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = PACKAGE_ROOT.parents[1]
OUT_DIR = native_artifact_root()
PACKAGE_NAME = "OPSX_RESOLVE_CONFLICT_COMMAND_001_R39"
PACKAGE_VERSION = "0.39.0"
STAGING = OUT_DIR / PACKAGE_NAME
ZIP_PATH = OUT_DIR / f"{PACKAGE_NAME}.zip"

# Candidate host contracts. Ship/restore may drop paths absent from origin;
# archive build must use MANIFEST host_frozen_contracts, never re-inject drops.
CANDIDATE_HOST_CONTRACTS = [
    ".cursor/commands/opsx-source-resolution.md",
    ".cursor/commands/opsx-execution-preflight.md",
    ".cursor/rules/testing-rules.mdc",
    "openspec/config.yaml",
    "openspec/policies/VERIFY_POLICY.md",
    "openspec/decisions/index.md",
    ".cursor/static-check/registry.yaml",
    ".cursor/static-check/checks/pyright-strict/context.md",
    ".cursor/static-check/checks/pyright-strict/instructions.md",
    ".cursor/static-check/checks/mypy/context.md",
    ".cursor/static-check/checks/mypy/instructions.md",
    ".cursor/static-check/checks/pytest-unit/context.md",
    ".cursor/static-check/checks/pytest-unit/instructions.md",
    ".cursor/static-check/checks/pytest-full/context.md",
    ".cursor/static-check/checks/pytest-full/instructions.md",
    ".cursor/static-check/contracts/synthesis.md",
    ".cursor/pipeline/GRAPH.md",
    ".cursor/pipeline/META.md",
    ".cursor/opsx-review-commands",
    ".github/copilot-instructions.md",
    ".github/git-commit-instructions.md",
]


def _host_contracts_from_manifest() -> list[str]:
    """Return origin-bound host_frozen_contracts from MANIFEST (fail closed)."""
    manifest = json.loads((PACKAGE_ROOT / "MANIFEST.json").read_text(encoding="utf-8"))
    categories = manifest.get("input_categories") or {}
    frozen = categories.get("host_frozen_contracts")
    if isinstance(frozen, list) and frozen:
        return [rel for rel in frozen if isinstance(rel, str)]
    # Fallback: only candidates that exist in working tree (restore should have run).
    return [rel for rel in CANDIDATE_HOST_CONTRACTS if (REPO_ROOT / rel).is_file()]


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> None:
    host_contracts = _host_contracts_from_manifest()
    contract_hashes = {
        rel: sha256_file(REPO_ROOT / rel)
        for rel in host_contracts
        if (REPO_ROOT / rel).is_file()
    }
    package_manifest_path = PACKAGE_ROOT / "MANIFEST.json"
    package_manifest = json.loads(
        package_manifest_path.read_text(encoding="utf-8")
    )
    package_owned = [
        ".cursor/commands/opsx-resolve-conflict.md",
        ".cursor/opsx-resolve-conflict/process_surfaces.json",
    ]
    package_manifest["host_contract_sha256"] = contract_hashes
    package_manifest["input_categories"] = {
        "package_owned_required": package_owned,
        "host_frozen_contracts": list(contract_hashes),
        "runtime_repository_input_kinds": [
            "active Git operation objects",
            "openspec/changes/<change>/conflict-authority.json",
            "authority files explicitly listed by conflict-authority.json",
        ],
    }
    package_manifest["required_repo_paths"] = sorted(
        set(package_owned) | set(contract_hashes)
    )
    package_manifest_path.write_text(
        json.dumps(package_manifest, indent=2) + "\n",
        encoding="utf-8",
    )
    cmd_src = REPO_ROOT / ".cursor/commands/opsx-resolve-conflict.md"
    local_cand = PACKAGE_ROOT / "candidate/.cursor/commands"
    local_cand.mkdir(parents=True, exist_ok=True)
    shutil.copy2(cmd_src, local_cand / "opsx-resolve-conflict.md")

    env = dict(os.environ)
    env["PYTHONPATH"] = str(PACKAGE_ROOT / "runtime")
    subprocess.check_call(
        [sys.executable, str(PACKAGE_ROOT / "scripts" / "update_manifest_hashes.py")],
        cwd=str(PACKAGE_ROOT),
        env=env,
    )

    if STAGING.exists():
        shutil.rmtree(STAGING)
    STAGING.mkdir(parents=True)

    cand = STAGING / "candidate"
    (cand / ".cursor" / "commands").mkdir(parents=True)
    shutil.copy2(cmd_src, cand / ".cursor/commands/opsx-resolve-conflict.md")

    dest_pkg = cand / ".cursor" / "opsx-resolve-conflict"
    for name in ("runtime", "schemas", "tests", "context", "scripts", "candidate"):
        src = PACKAGE_ROOT / name
        if src.exists():
            shutil.copytree(
                src,
                dest_pkg / name,
                dirs_exist_ok=True,
                ignore=shutil.ignore_patterns("__pycache__", "*.pyc", "*.pyo"),
            )

    root_docs = [
        "MANIFEST.json",
        "TRUST_ANCHOR.json",
        "CHANGELOG.md",
        "AUTHORSHIP.md",
        "00_SCOPE.md",
        "01_REVIEW_STANDARD.md",
        "01_ARCHITECTURE_BASELINE.md",
        "02_REQUIRED_CONTEXT.md",
        "02_WORKFLOW_CONTRACT.md",
        "03_VERDICT_SCHEMA.md",
        "03_HANDOFF_SCHEMAS.md",
        "04_REVISION_CLOSURE_MATRIX.md",
        "04_DECISION_LOG.md",
        "REVIEW_REQUEST.md",
        "CLEAN_UNPACK_TEST_REPORT.json",
        "process_surfaces.json",
        "PACKAGE_INDEX.json",
        "README_REVIEW.md",
    ]
    for name in root_docs:
        src = PACKAGE_ROOT / name
        if src.exists():
            shutil.copy2(src, dest_pkg / name)
            shutil.copy2(src, STAGING / name)

    shutil.copytree(PACKAGE_ROOT / "context", STAGING / "context", dirs_exist_ok=True)

    host_root = STAGING / "context" / "host_contracts"
    host_root.mkdir(parents=True, exist_ok=True)
    for rel in host_contracts:
        src = REPO_ROOT / rel
        if not src.is_file():
            continue
        dst = host_root / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
        contract_hashes[rel] = sha256_file(src)
    (STAGING / "context" / "HOST_CONTRACT_HASHES.json").write_text(
        json.dumps(contract_hashes, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    built = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    authorship = STAGING / "CURSOR_AUTHORSHIP.txt"
    authorship.write_text(
        "\n".join(
            [
                "OPSX_PACKAGE_AUTHORSHIP_V1",
                "author=Cursor",
                f"package={PACKAGE_NAME}",
                f"package_version={PACKAGE_VERSION}",
                f"built_at_utc={built}",
                "statement=This archive was authored by Cursor for independent review.",
                "note=Not a cryptographic signature; authenticity is hash-bound via SHA256SUMS + TRUST_ANCHOR.",
                "open_blockers=BLOCKER_AUTHORITY_PRODUCER_MISSING,BLOCKER_OS_SANDBOX_RUNNER_MISSING",
                "",
            ]
        ),
        encoding="utf-8",
    )

    # Refresh installed command hash after sync; keep inventory from update script
    manifest_path = STAGING / "MANIFEST.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["package_name"] = PACKAGE_NAME
    manifest["package_version"] = PACKAGE_VERSION
    manifest["author"] = "Cursor"
    manifest["built_at_utc"] = built
    manifest["installed_command_sha256"] = sha256_file(
        cand / ".cursor/commands/opsx-resolve-conflict.md"
    )
    manifest["host_contract_sha256"] = contract_hashes
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    shutil.copy2(manifest_path, dest_pkg / "MANIFEST.json")
    shutil.copy2(PACKAGE_ROOT / "TRUST_ANCHOR.json", dest_pkg / "TRUST_ANCHOR.json")

    # Re-run hash updater against staging package? Keep PACKAGE_ROOT as SoT;
    # re-sync installed hash into PACKAGE_ROOT manifest for local install consistency.
    pkg_manifest = PACKAGE_ROOT / "MANIFEST.json"
    local = json.loads(pkg_manifest.read_text(encoding="utf-8"))
    local["installed_command_sha256"] = manifest["installed_command_sha256"]
    local["built_at_utc"] = built
    local["host_contract_sha256"] = contract_hashes
    pkg_manifest.write_text(json.dumps(local, indent=2) + "\n", encoding="utf-8")
    shutil.copy2(pkg_manifest, dest_pkg / "MANIFEST.json")
    shutil.copy2(pkg_manifest, STAGING / "MANIFEST.json")

    lines = [
        f"{sha256_file(path)}  {path.relative_to(STAGING).as_posix()}"
        for path in sorted(STAGING.rglob("*"))
        if path.is_file()
    ]
    (STAGING / "SHA256SUMS").write_text("\n".join(lines) + "\n", encoding="utf-8")

    if ZIP_PATH.exists():
        ZIP_PATH.unlink()
    with zipfile.ZipFile(ZIP_PATH, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for path in sorted(STAGING.rglob("*")):
            if path.is_file():
                zf.write(path, path.relative_to(STAGING).as_posix())

    digest = sha256_file(ZIP_PATH)
    sidecar = ZIP_PATH.with_suffix(".AUTHOR.txt")
    sidecar.write_text(
        "\n".join(
            [
                "OPSX_PACKAGE_SIDECAR_V1",
                "author=Cursor",
                f"package={PACKAGE_NAME}",
                f"package_version={PACKAGE_VERSION}",
                f"archive_sha256={digest}",
                f"external_trust_package_digest={local['package_digest']}",
                "usage=Set OPSX_CONFLICT_TRUST_DIGEST to external_trust_package_digest for GO.",
                "usage_sandbox=Set OPSX_CONFLICT_SANDBOX_TRUST_DIGEST to an OS_VERIFIED allowlisted runner digest.",
                "note=Not a cryptographic signature. Packaged sandbox_runner is BEST_EFFORT only.",
                "open_blockers=BLOCKER_AUTHORITY_PRODUCER_MISSING,BLOCKER_OS_SANDBOX_RUNNER_MISSING",
                "",
            ]
        ),
        encoding="utf-8",
    )
    print(f"wrote {ZIP_PATH}")
    print(f"sha256 {digest}")
    print(f"sidecar {sidecar}")


if __name__ == "__main__":
    main()
