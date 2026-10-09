#!/usr/bin/env python3
"""Verify or emit durable scenario-plan receipt for product-control-context.

Recipe (OPSX_SCENARIO_TEST_COVERAGE_V1 DURABLE_PLAN_EVIDENCE):
1. LF-normalize each INPUT file bytes (CRLF -> LF) before content_hash.
2. SOURCE_SPEC_SHA = sha256(utf-8 concat of SPEC_REVISION content_hash hex strings).
3. Identity object:
   {CHANGE_ID, MODE, DESIGN_REVISION, SPEC_REVISION[], LIFECYCLE_REVISION,
    OWNER_CONTRACT_REVISION, SOURCE_SPEC_SHA}
4. identity_blob = json.dumps(obj, sort_keys=True, separators=(',', ':')).encode('utf-8')
5. PLAN_EVIDENCE_ID = 'SCPV1-' + sha256(identity_blob).hexdigest()[:16]
6. PLAN_CONTENT_HASH = sha256(LF-normalized plan.md bytes)

Usage:
  verify (default): print checks; exit 0 if receipt matches inputs.
  --write-receipt: regenerate plan.receipt.json from current inputs + plan.md.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import sys

CHANGE_ROOT = pathlib.Path(__file__).resolve().parents[1]
REPO_ROOT = CHANGE_ROOT.parents[2]
CHANGE_ID = "product-control-context"

INPUT_PATHS = {
    "DESIGN_REVISION": CHANGE_ROOT / "design.md",
    "SPEC_REVISION": [
        CHANGE_ROOT / "specs/product-control-context/spec.md",
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


def lifecycle_coverage_from_plan() -> dict[str, list[str]]:
    """Lifecycle coverage mirrored in plan.receipt.json (must match plan.md)."""
    return {
        "covered": [
            "L1:S03,S16",
            "L2:S06,S13,S18,S19,S20",
            "L3:S07,S08,S09,S10,S21",
            "L4:S11,S12,S16,S22",
            "L5:S04,S14,S15,S06",
            "L6:S01,S02,S05,S17",
        ],
        "gaps": [],
    }


def build_receipt(
    *,
    design_hash: str,
    spec_hashes: list[str],
    lifecycle_hash: str,
    owner_hash: str,
    source_spec: str,
    identity_blob: bytes,
    evidence_id: str,
    plan_hash: str,
) -> dict[str, object]:
    """Assemble machine receipt dict."""
    spec_inputs = [
        {
            "path": str(INPUT_PATHS["SPEC_REVISION"][i].relative_to(REPO_ROOT)),
            "content_hash": spec_hashes[i],
        }
        for i in range(len(spec_hashes))
    ]
    design_rel = str(INPUT_PATHS["DESIGN_REVISION"].relative_to(REPO_ROOT))
    owner_rel = str(INPUT_PATHS["OWNER_CONTRACT_REVISION"].relative_to(REPO_ROOT))
    plan_rel = str(PLAN_PATH.relative_to(REPO_ROOT))
    receipt_rel = str(RECEIPT_PATH.relative_to(REPO_ROOT))
    lifecycle_cov = lifecycle_coverage_from_plan()
    return {
        "SCHEMA_VERSION": 1,
        "SCENARIO_COVERAGE_RECEIPT": True,
        "CHANGE_ID": CHANGE_ID,
        "MODE": "plan",
        "PLAN_STATUS": "ready",
        "PLAN_EVIDENCE_ID": evidence_id,
        "PLAN_CONTENT_HASH": plan_hash,
        "PLAN_PATH": plan_rel,
        "RECEIPT_PATH": receipt_rel,
        "SCENARIO_COUNT": 22,
        "SOURCE_SPEC_SHA": source_spec,
        "LIFECYCLE_COVERAGE": lifecycle_cov,
        "UNRESOLVED_GAPS": [],
        "INPUTS": {
            "DESIGN_REVISION": {"path": design_rel, "content_hash": design_hash},
            "SPEC_REVISION": spec_inputs,
            "LIFECYCLE_REVISION": {
                "source": f"{design_rel}#derived-lifecycle",
                "content_hash": lifecycle_hash,
            },
            "OWNER_CONTRACT_REVISION": {
                "path": owner_rel,
                "content_hash": owner_hash,
            },
        },
        "GENERATED_FROM": {
            "DESIGN_REVISION": design_hash,
            "SPEC_REVISION": spec_hashes,
            "LIFECYCLE_REVISION": lifecycle_hash,
            "OWNER_CONTRACT_REVISION": owner_hash,
        },
        "MATERIALIZATION_STATUS": "COMMITTED",
    }


def sync_plan_evidence_id_in_plan_md(evidence_id: str) -> None:
    """Replace PLAN_EVIDENCE_ID line in plan.md with computed SCPV1 id."""
    text = PLAN_PATH.read_text(encoding="utf-8")
    marker = "PLAN_EVIDENCE_ID: "
    lines = text.splitlines()
    for i, line in enumerate(lines):
        if line.startswith(marker):
            lines[i] = f"{marker}{evidence_id}"
            break
    else:
        raise RuntimeError("PLAN_EVIDENCE_ID line not found in plan.md")
    PLAN_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")


def compute() -> tuple[dict[str, object], str, str, bytes]:
    """Compute receipt fields from current files (plan.md as-is)."""
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
    evidence_id = plan_evidence_id(identity_blob)
    plan_hash = lf_sha256(PLAN_PATH)
    receipt = build_receipt(
        design_hash=design_hash,
        spec_hashes=spec_hashes,
        lifecycle_hash=lifecycle_hash,
        owner_hash=owner_hash,
        source_spec=source_spec,
        identity_blob=identity_blob,
        evidence_id=evidence_id,
        plan_hash=plan_hash,
    )
    return receipt, evidence_id, plan_hash, identity_blob


def verify_receipt(receipt: dict[str, object], evidence_id: str, plan_hash: str) -> bool:
    """Return True if on-disk receipt matches computed identity."""
    on_disk = json.loads(RECEIPT_PATH.read_text(encoding="utf-8"))
    checks = {
        "PLAN_EVIDENCE_ID": on_disk.get("PLAN_EVIDENCE_ID") == evidence_id,
        "PLAN_CONTENT_HASH": on_disk.get("PLAN_CONTENT_HASH") == plan_hash,
        "DESIGN": on_disk["INPUTS"]["DESIGN_REVISION"]["content_hash"]
        == receipt["INPUTS"]["DESIGN_REVISION"]["content_hash"],
        "OWNER": on_disk["INPUTS"]["OWNER_CONTRACT_REVISION"]["content_hash"]
        == receipt["INPUTS"]["OWNER_CONTRACT_REVISION"]["content_hash"],
        "SOURCE_SPEC_SHA": on_disk.get("SOURCE_SPEC_SHA") == receipt["SOURCE_SPEC_SHA"],
    }
    print(json.dumps({"checks": checks}, indent=2))
    return all(checks.values())


def main() -> int:
    """CLI entry."""
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--write-receipt",
        action="store_true",
        help="Write plan.receipt.json and sync PLAN_EVIDENCE_ID in plan.md",
    )
    args = parser.parse_args()

    receipt, evidence_id, plan_hash, _ = compute()

    if args.write_receipt:
        sync_plan_evidence_id_in_plan_md(evidence_id)
        receipt, evidence_id, plan_hash, _ = compute()
        RECEIPT_PATH.write_text(
            json.dumps(receipt, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        print("Wrote", RECEIPT_PATH)
        print("PLAN_EVIDENCE_ID:", evidence_id)
        print("PLAN_CONTENT_HASH:", plan_hash)

    if not RECEIPT_PATH.exists():
        print("Missing receipt; run with --write-receipt", file=sys.stderr)
        return 1

    ok = verify_receipt(receipt, evidence_id, plan_hash)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
