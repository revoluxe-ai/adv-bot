#!/usr/bin/env python3
"""Independent PLAN_EVIDENCE_ID / receipt hash verification for repair3.

Recipe (OPSX_SCENARIO_TEST_COVERAGE_V1 DURABLE_PLAN_EVIDENCE identity fields):
1. LF-normalize each INPUT file bytes (CRLF -> LF) before content_hash.
2. SOURCE_SPEC_SHA = sha256(utf-8 concat of SPEC_REVISION content_hash hex strings).
3. Identity object (no plan content, no timestamps, no PRODUCER_COMMAND):
   {CHANGE_ID, MODE, DESIGN_REVISION, SPEC_REVISION[], LIFECYCLE_REVISION,
    OWNER_CONTRACT_REVISION, SOURCE_SPEC_SHA}
4. identity_blob = json.dumps(obj, sort_keys=True, separators=(',', ':')).encode('utf-8')
   (no trailing newline; UTF-8 without BOM)
5. PLAN_EVIDENCE_ID = 'SCPV1-' + sha256(identity_blob).hexdigest()[:16]
6. PLAN_CONTENT_HASH = sha256(LF-normalized plan.md bytes)
"""

from __future__ import annotations

import base64
import hashlib
import json
import pathlib
import sys

CHANGE_ROOT = pathlib.Path(__file__).resolve().parents[1]
CHANGE_ID = "ai-package-keyword-performance-history"

INPUT_PATHS = {
    "DESIGN_REVISION": CHANGE_ROOT / "design.md",
    "SPEC_REVISION": [
        CHANGE_ROOT / "specs/ai-package-keyword-performance-history/spec.md",
        CHANGE_ROOT / "specs/ai-package-v1-exporter/spec.md",
        CHANGE_ROOT / "specs/ai-package-v1-contract-tests/spec.md",
    ],
    "LIFECYCLE_REVISION": CHANGE_ROOT / "design.md",
    "OWNER_CONTRACT_REVISION": CHANGE_ROOT / "owner-contract.md",
}
PLAN_PATH = CHANGE_ROOT / "scenario-coverage/plan.md"
RECEIPT_PATH = CHANGE_ROOT / "scenario-coverage/plan.receipt.json"


def lf_sha256(path: pathlib.Path) -> str:
    """Return sha256 of LF-normalized file bytes."""
    data = path.read_bytes().replace(b"\r\n", b"\n")
    return hashlib.sha256(data).hexdigest()


def source_spec_sha(spec_hashes: list[str]) -> str:
    """Concatenate spec content_hash hex strings in array order, then sha256."""
    return hashlib.sha256("".join(spec_hashes).encode("utf-8")).hexdigest()


def build_identity_blob(
    *,
    change_id: str,
    design_hash: str,
    spec_hashes: list[str],
    lifecycle_hash: str,
    owner_hash: str,
    source_spec: str,
) -> bytes:
    """Build canonical UTF-8 identity blob bytes."""
    obj = {
        "CHANGE_ID": change_id,
        "MODE": "plan",
        "DESIGN_REVISION": design_hash,
        "SPEC_REVISION": spec_hashes,
        "LIFECYCLE_REVISION": lifecycle_hash,
        "OWNER_CONTRACT_REVISION": owner_hash,
        "SOURCE_SPEC_SHA": source_spec,
    }
    return json.dumps(obj, sort_keys=True, separators=(",", ":")).encode("utf-8")


def plan_evidence_id(identity_blob: bytes) -> str:
    """Derive SCPV1-* id from identity blob."""
    digest = hashlib.sha256(identity_blob).hexdigest()
    return f"SCPV1-{digest[:16]}"


def main() -> int:
    design_hash = lf_sha256(INPUT_PATHS["DESIGN_REVISION"])
    spec_hashes = [lf_sha256(p) for p in INPUT_PATHS["SPEC_REVISION"]]
    lifecycle_hash = lf_sha256(INPUT_PATHS["LIFECYCLE_REVISION"])
    owner_hash = lf_sha256(INPUT_PATHS["OWNER_CONTRACT_REVISION"])
    source_spec = source_spec_sha(spec_hashes)

    identity_blob = build_identity_blob(
        change_id=CHANGE_ID,
        design_hash=design_hash,
        spec_hashes=spec_hashes,
        lifecycle_hash=lifecycle_hash,
        owner_hash=owner_hash,
        source_spec=source_spec,
    )
    identity_sha256 = hashlib.sha256(identity_blob).hexdigest()
    evidence_id = plan_evidence_id(identity_blob)
    plan_hash = lf_sha256(PLAN_PATH)

    receipt = json.loads(RECEIPT_PATH.read_text(encoding="utf-8"))
    checks = {
        "DESIGN_REVISION": receipt["INPUTS"]["DESIGN_REVISION"]["content_hash"] == design_hash,
        "SPEC_REVISION": [
            a == b
            for a, b in zip(
                [s["content_hash"] for s in receipt["INPUTS"]["SPEC_REVISION"]],
                spec_hashes,
                strict=True,
            )
        ],
        "OWNER_CONTRACT_REVISION": receipt["INPUTS"]["OWNER_CONTRACT_REVISION"]["content_hash"]
        == owner_hash,
        "SOURCE_SPEC_SHA": receipt.get("SOURCE_SPEC_SHA") == source_spec,
        "PLAN_EVIDENCE_ID": receipt.get("PLAN_EVIDENCE_ID") == evidence_id,
        "PLAN_CONTENT_HASH": receipt.get("PLAN_CONTENT_HASH") == plan_hash,
        "IDENTITY_BLOB_SHA256": receipt.get("REPAIR_METADATA", {})
        .get("identity_blob_sha256")
        == identity_sha256,
    }

    print("CHANGE_ID:", CHANGE_ID)
    print("DESIGN_REVISION:", design_hash)
    for i, h in enumerate(spec_hashes):
        print(f"SPEC_REVISION[{i}]:", h)
    print("LIFECYCLE_REVISION:", lifecycle_hash)
    print("OWNER_CONTRACT_REVISION:", owner_hash)
    print("SOURCE_SPEC_SHA:", source_spec)
    print("IDENTITY_BLOB_UTF8:", identity_blob.decode("utf-8"))
    print("IDENTITY_BLOB_BASE64:", base64.b64encode(identity_blob).decode("ascii"))
    print("IDENTITY_BLOB_SHA256:", identity_sha256)
    print("PLAN_EVIDENCE_ID:", evidence_id)
    print("PLAN_CONTENT_HASH:", plan_hash)
    print("CHECKS:", json.dumps(checks, indent=2))

    all_ok = (
        checks["DESIGN_REVISION"]
        and all(checks["SPEC_REVISION"])
        and checks["OWNER_CONTRACT_REVISION"]
        and checks["SOURCE_SPEC_SHA"]
        and checks["PLAN_EVIDENCE_ID"]
        and checks["PLAN_CONTENT_HASH"]
        and checks["IDENTITY_BLOB_SHA256"]
    )
    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())
