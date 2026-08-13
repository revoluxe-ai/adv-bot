#!/usr/bin/env python3
"""Пересобрать R33 inventory и внешний digest с manifest policy binding."""

from __future__ import annotations

import json
import sys
from pathlib import Path

PACKAGE_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = PACKAGE_ROOT.parents[1]
sys.path.insert(0, str(PACKAGE_ROOT / "runtime"))

from opsx_conflict.attestation import (  # noqa: E402
    PACKAGE_VERSION,
    _file_sha256,
    inventory_hashes,
    package_digest,
)


def invalidate_archive_binding_after_digest_refresh(digest: str) -> None:
    """Сбросить ZIP/pytest binding после digest-only re-pin.

    CLEAN_UNPACK / PACKAGE_INDEX не входят в package_digest inventory, но
    могут хранить external_archive_sha256_ref от предыдущего ship. После
    обновления digest эти ссылки и pytest totals обязаны стать placeholder
    (null / удалены), иначе новый digest окажется привязан к чужому ZIP.
    Полный rebind — только через ship_review_package.
    """
    clean_path = PACKAGE_ROOT / "CLEAN_UNPACK_TEST_REPORT.json"
    if clean_path.is_file():
        clean = json.loads(clean_path.read_text(encoding="utf-8"))
        clean["package_digest"] = digest
        clean["archive_sha256"] = None
        clean["passed"] = None
        clean["skipped"] = None
        clean["pytest_exit_code"] = None
        clean.pop("external_archive_sha256_ref", None)
        clean.pop("raw_log_sha256_ref", None)
        clean_path.write_text(
            json.dumps(clean, indent=2) + "\n", encoding="utf-8"
        )

    index_path = PACKAGE_ROOT / "PACKAGE_INDEX.json"
    if index_path.is_file():
        index = json.loads(index_path.read_text(encoding="utf-8"))
        index["package_digest"] = digest
        index["archive_sha256"] = None
        index.pop("external_archive_sha256_ref", None)
        index.pop("raw_log_sha256_ref", None)
        index_path.write_text(
            json.dumps(index, indent=2) + "\n", encoding="utf-8"
        )


def main() -> None:
    """Refresh MANIFEST inventory hashes and TRUST_ANCHOR digest."""
    manifest_path = PACKAGE_ROOT / "MANIFEST.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["package_name"] = "OPSX_RESOLVE_CONFLICT_COMMAND_001_R40"
    manifest["package_version"] = PACKAGE_VERSION
    manifest["contract_schema_version"] = "opsx-resolve-conflict/v2"
    manifest["status"] = "preview_only_no_go"
    manifest["go_capability"] = False
    manifest["author"] = "Cursor"
    manifest["limitations"] = [
        "GO_CAPABILITY=false",
        "SAFE_USAGE_SCOPE=PREVIEW_ONLY",
        "BLOCKER_AUTHORITY_PRODUCER_MISSING",
        "BLOCKER_OS_SANDBOX_RUNNER_MISSING",
        "R25-MEDIUM-002 trusted-Git execution boundary not Owner-closed",
        "R25-PROCESS-001 pack/commit membership open",
        "ADR-OPSX-RC-PLATFORM-001 APPROVE_WINDOWS_ONLY (linux/macos UNSUPPORTED)",
        "External authority declaration consumer only; no self-producer",
        "Packaged sandbox_runner is BEST_EFFORT only",
    ]
    sandbox_runner = (
        PACKAGE_ROOT / "runtime" / "opsx_conflict" / "sandbox_runner.py"
    )
    sandbox_digest = _file_sha256(sandbox_runner)
    manifest["trusted_sandbox_runners"] = [
        {
            "sha256": sandbox_digest,
            "protocol": "opsx-sandbox-path-confinement/v1",
            "package_path": "runtime/opsx_conflict/sandbox_runner.py",
            "enforcement_level": "BEST_EFFORT",
            "note": (
                "Packaged runner is path-confinement only. GO requires an "
                "independently supplied OS_VERIFIED runner "
                "(BLOCKER_OS_SANDBOX_RUNNER_MISSING)."
            ),
        }
    ]
    manifest["supersedes"] = {
        "package_versions": [
            "0.5.0",
            "0.6.0",
            "0.7.0",
            "0.8.0",
            "0.9.0",
            "0.10.0",
            "0.11.0",
            "0.12.0",
            "0.13.0",
            "0.14.0",
            "0.15.0",
            "0.16.0",
            "0.17.0",
            "0.18.0",
            "0.19.0",
            "0.20.0",
            "0.21.0",
            "0.22.0",
            "0.23.0",
            "0.24.0",
            "0.25.0",
            "0.26.0",
            "0.27.0",
            "0.28.0",
            "0.29.0",
            "0.30.0",
            "0.31.0",
            "0.32.0",
        ],
        "verdict": "REVISION_REQUIRED",
    }
    manifest["source_branch_compare"] = {
        "status": "package_working_tree",
        "note": (
            "R33 candidate after ADR-OPSX-RC-PLATFORM-001 WINDOWS_PREVIEW_ONLY: "
            "advisory preview on Windows; linux/macos UNSUPPORTED; typed "
            "UNSUPPORTED_PLATFORM; platform matrix sealed; git_typed/"
            "validation/trust-store frozen for GO; GO_CAPABILITY=false"
        ),
    }
    manifest["go_capability"] = False
    manifest["safe_usage_scope"] = "PREVIEW_ONLY"
    manifest["limitations"] = [
        "consumer-side trust enforcement implemented",
        "operational producer trust unavailable",
        "GO_CAPABILITY=false",
        "BLOCKER_AUTHORITY_PRODUCER_MISSING",
        "BLOCKER_OS_SANDBOX_RUNNER_MISSING",
        "ADR-OPSX-RC-PLATFORM-001 APPROVE_WINDOWS_ONLY",
    ]
    manifest["entrypoints"] = {
        "command": ".cursor/commands/opsx-resolve-conflict.md",
        "bundled_command": "candidate/.cursor/commands/opsx-resolve-conflict.md",
        "runtime": ".cursor/opsx-resolve-conflict/runtime/opsx_conflict/runtime.py",
        "boot": ".cursor/opsx-resolve-conflict/runtime/boot_opsx_conflict.py",
    }
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")

    hashes = inventory_hashes()
    hashes.pop("TRUST_ANCHOR.json", None)
    digest = package_digest(hashes)
    anchor = {
        "schema": "opsx-resolve-conflict/trust-anchor/v1",
        "package_version": PACKAGE_VERSION,
        "package_digest": digest,
        "author": "Cursor",
        "note": "Hash-bound trust aggregate; outer archive SHA256SUMS is review root.",
        "open_blockers": [
            "BLOCKER_AUTHORITY_PRODUCER_MISSING",
            "BLOCKER_OS_SANDBOX_RUNNER_MISSING",
        ],
    }
    (PACKAGE_ROOT / "TRUST_ANCHOR.json").write_text(
        json.dumps(anchor, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    hashes = inventory_hashes()
    digest = package_digest({k: v for k, v in hashes.items() if k != "TRUST_ANCHOR.json"})
    anchor["package_digest"] = digest
    (PACKAGE_ROOT / "TRUST_ANCHOR.json").write_text(
        json.dumps(anchor, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    hashes["TRUST_ANCHOR.json"] = _file_sha256(PACKAGE_ROOT / "TRUST_ANCHOR.json")

    manifest["package_digest"] = digest
    file_hashes = {k: v for k, v in hashes.items()}
    manifest["file_sha256"] = {
        k: v for k, v in file_hashes.items() if k != "TRUST_ANCHOR.json"
    }
    manifest["trust_anchor_sha256"] = file_hashes["TRUST_ANCHOR.json"]
    cmd = (
        PACKAGE_ROOT
        / "candidate"
        / ".cursor"
        / "commands"
        / "opsx-resolve-conflict.md"
    )
    manifest["installed_command_sha256"] = _file_sha256(cmd)
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    invalidate_archive_binding_after_digest_refresh(digest)
    print(f"updated {manifest_path} version={PACKAGE_VERSION} digest={digest[:16]}…")


if __name__ == "__main__":
    main()
