# scripts/evidence — cluster-safe forensic metadata

## prod_revision_timeline.jsonl

Compact **production deployment event** ledger shipped inside the scripts image
(`COPY . .` in `dockers/Dockerfile`). Used by **Adv-bot historical state
extractor** when git is unavailable in Kubernetes Job (no `.git`, no `git`
binary, no `.cursor/devops/**`).

Each line is **one actual prod deployment / CAS / SAFE_PROD_RELEASE event** —
not a git commit.

```json
{
  "deployed_at": "2026-08-09T10:35:00Z",
  "commit_sha": "0e7273aec3bd41470f0fe664fa492f5eef10df99",
  "image_ref": "harbor.skyline360.ru/git-registry-cache/revoluxe-ai/adv-bot:0e7273aec3bd41470f0fe664fa492f5eef10df99",
  "image_digest": "sha256:0c3ee41057f198ec7e6847847bfc20aea74c442312bc2cc5228c60a7b32c29e1",
  "workflow_run_id": "31307330107",
  "evidence_source": "LAST.json",
  "evidence_ref": ".cursor/devops/LAST.json@e4bf3951f",
  "evidence_kind": "DIRECT_DEPLOYMENT_RECEIPT",
  "confidence": "HIGH",
  "notes": "Receipt timestamp used as best-known effective point."
}
```

### Semantics

| Field | Meaning |
|-------|---------|
| `deployed_at` | Best-known point when prod CAS/release became effective (often LAST.json `updated_at_utc`; may be date-only from OPS_STATE action log) |
| `commit_sha` | Deployed git SHA (image tag) |
| `image_ref` / `image_digest` | Harbor pull ref and digest when known |
| `workflow_run_id` | GHA run id when present in receipt |
| `evidence_source` | Authoritative receipt family |
| `evidence_ref` | Git path@sha or action-log pointer |
| `evidence_kind` | Always `DIRECT_DEPLOYMENT_RECEIPT` in ledger rows |
| `confidence` | `HIGH` / `MEDIUM` — reflects timestamp precision, not deploy certainty |

The extractor derives **effective intervals** for `--from` / `--to`:

- `effective_from` / `effective_to` — runtime window in requested timezone
- `evidence_kind=INFERRED_CONTINUITY` when period start continues a prior deployment
- `evidence_kind=DIRECT_DEPLOYMENT_RECEIPT` when interval opens at a ledger event

### Maintenance

Rebuild from git-history `.cursor/devops/LAST.json` + `OPS_STATE.md` receipts
during development; append one row per **new** prod deployment. Do not dump
`git log`. Do not embed case-specific (DILERA) data.
