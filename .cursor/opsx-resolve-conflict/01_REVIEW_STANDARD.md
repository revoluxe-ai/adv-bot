# 01_REVIEW_STANDARD — R39

Review must cover:

1. **COMMAND_INTERNAL_REVIEW** — command entrypoint present in candidate;
   runtime matches contract; no false RESOLVED; no default `--continue`.
2. **OPSX_CONTEXTUAL_REVIEW** — use `context/OPSX_CONTEXT_EXTRACT.md` plus
   repository contracts listed in MANIFEST `required_repo_paths` when the
   review environment includes the host repo.
3. **SCENARIO_EVIDENCE_REVIEW** — replay package tests from a clean unpack
   without external worktree command files or monkeypatched safety gates in
   acceptance evidence (unit fixtures may stub the compatibility gate).

## Verdict schema

See `03_VERDICT_SCHEMA.md`.

## Hard fail

Any CRITICAL from CF-001..CF-004 class remaining → REJECTED / SAFE_TO_USE=NO.
