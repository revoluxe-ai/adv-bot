# 03_VERDICT_SCHEMA — machine-readable review result (R39)

Aligned with project review policy.

```json
{
  "VERDICT": "ACCEPTED | ACCEPTED_WITH_GAPS | REVISION_REQUIRED | REJECTED",
  "REVIEW_LEVEL": {
    "COMMAND_INTERNAL_REVIEW": "PERFORMED_PASSED | PERFORMED_FAILED | PARTIAL_* | NOT_PERFORMED_*",
    "OPSX_CONTEXTUAL_REVIEW": "PERFORMED_PASSED | PERFORMED_FAILED | NOT_PERFORMED_*",
    "SCENARIO_EVIDENCE_REVIEW": "PERFORMED_PASSED | PERFORMED_FAILED | NOT_PERFORMED_*"
  },
  "PACKAGE_VERSION": "0.39.0",
  "CONTRACT_SCHEMA_VERSION": "opsx-resolve-conflict/v2",
  "CONTEXT_SUFFICIENCY": "SUFFICIENT | INSUFFICIENT",
  "SOURCE_COMMIT_STATUS": {
    "status": "MATCHED | CONTRADICTORY | UNKNOWN",
    "manifest": "<sha>"
  },
  "FINDINGS_COUNT": {
    "CRITICAL": 0,
    "HIGH": 0,
    "MEDIUM": 0,
    "LOW": 0,
    "PROCESS": 0
  },
  "SAFE_TO_USE": false,
  "SAFE_USAGE_SCOPE": "NONE_EXECUTION | PREVIEW_ONLY | GO_STAGING_ONLY",
  "REQUIRED_REVISION": "none | [...]",
  "REVIEW_LIMITATIONS": [],
  "AUTHOR": "Cursor"
}
```

Rules:

- `ACCEPTED` requires zero open CRITICAL / HIGH / MEDIUM.
- `SAFE_TO_USE=true` only with `ACCEPTED` and `CONTEXT_SUFFICIENCY=SUFFICIENT`.
- Contextual review requires host contracts under `context/host_contracts/` **or** live repo paths from MANIFEST `required_repo_paths`.
