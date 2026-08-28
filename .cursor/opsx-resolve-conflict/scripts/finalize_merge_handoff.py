"""Finalize merge verification handoff after manual Owner resolutions."""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
RUNTIME = ROOT / ".cursor" / "opsx-resolve-conflict" / "runtime"
sys.path.insert(0, str(RUNTIME))

from opsx_conflict.git_capture import capture_operation, list_staged_paths  # noqa: E402
from opsx_conflict.models import ResolutionClass, ResolutionKind, ResolutionLedgerEntry  # noqa: E402
from opsx_conflict.pipeline import run_preview, _operation_identity_str  # noqa: E402
from opsx_conflict.verify import verify_candidate, verify_resolution_unit  # noqa: E402
from opsx_conflict.verification_handoff import build_verification_handoff  # noqa: E402


def main() -> None:
    preview = run_preview(ROOT)
    manifest = preview.manifest
    if manifest is None:
        raise SystemExit("no manifest")

    classified_by_path = {c.path: c for c in preview.classified}
    staged = list_staged_paths(ROOT)
    resolved_paths = sorted(
        set(staged)
        | {p.path for p in preview.classified if p.path not in staged}
    )
    # Only paths that were part of this operation's conflict surface
    conflict_paths = {p.path for p in preview.partitions}
    resolved_paths = sorted(p for p in resolved_paths if p in conflict_paths or p in staged)

    op_id = _operation_identity_str(manifest)
    ledger: list[ResolutionLedgerEntry] = []
    verify_failures: list[str] = []

    for path in sorted(conflict_paths):
        item = classified_by_path.get(path)
        if item is None:
            continue
        target = ROOT / path
        if not target.is_file() and item.resolution_kind != ResolutionKind.DELETE:
            if path in staged:
                verify_failures.append(f"missing_file:{path}")
            continue
        if target.is_file() or item.resolution_kind == ResolutionKind.DELETE:
            ok, refs = verify_resolution_unit(ROOT, path, item)
            if not ok:
                verify_failures.append(f"{path}:{refs}")
        wt_hash = (
            hashlib.sha256(target.read_bytes()).hexdigest()
            if target.is_file()
            else None
        )
        ledger.append(
            ResolutionLedgerEntry(
                conflict_id=item.conflict_id,
                cluster_id=item.cluster_id,
                path=path,
                operation_identity=op_id,
                base_oid=manifest.operation.base_oid,
                side_a_oid=manifest.operation.side_a_oid,
                side_b_oid=manifest.operation.side_b_oid,
                authority_refs=item.semantic_authority_refs,
                lane=item.lane.value,
                resolution_class=item.resolution_class.value,
                resolution_kind=item.resolution_kind.value,
                reason=item.reason,
                result_worktree_sha256=wt_hash,
                verification_refs=refs if target.is_file() else ["resolution:delete_verified"],
                applied_policy_id=item.applied_policy_id,
                policy_compatibility_reason=item.policy_compatibility_reason,
            )
        )

    cand_ok, cand_refs, _ = verify_candidate(ROOT, manifest, list(conflict_paths), ledger, {})
    handoff = build_verification_handoff(
        ROOT, manifest, ledger, sorted(conflict_paths), op_id
    )

    owner_remaining = [
        p.path
        for p in preview.classified
        if p.resolution_class == ResolutionClass.OWNER_REQUIRED
    ]

    report = {
        "STATUS": "RESOLVED_PENDING_VERIFICATION" if not verify_failures and cand_ok else "FAILED",
        "STAGE": "RESOLVED_PENDING_VERIFICATION",
        "UNMERGED_COUNT": len(
            subprocess.run(
                ["git", "diff", "--name-only", "--diff-filter=U"],
                cwd=ROOT,
                capture_output=True,
                text=True,
            ).stdout.splitlines()
        ),
        "candidate_identity": handoff.candidate_identity,
        "CANDIDATE_IDENTITY": handoff.candidate_identity,
        "candidate_tree_oid": handoff.candidate_tree_oid,
        "FINGERPRINT": manifest.fingerprint,
        "RESOLUTION_LEDGER_COUNT": len(ledger),
        "RESOLUTION_LEDGER": [e.to_dict() for e in ledger[:5]],
        "OWNER_REQUIRED_REMAINING": owner_remaining,
        "VERIFY_FAILURES": verify_failures,
        "CANDIDATE_VERIFY": cand_ok,
        "CANDIDATE_VERIFY_REFS": cand_refs,
        "VERIFICATION_HANDOFF": handoff.to_dict(),
    }
    print(json.dumps(report, ensure_ascii=True, indent=2))


if __name__ == "__main__":
    main()
