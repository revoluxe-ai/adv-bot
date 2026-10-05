# Proposal — ai-package-full-export-contract-repair

## Problem

Full AI Package lacks `PACKAGE_SUMMARY.json`, a single canonical family status vocabulary, explicit campaign/keyword identity, and validator cross-checks. Shop feed and settings slices are ambiguous to external AI consumers.

## Solution

Deterministic read-only metadata layer under `app/modules/ai_package_v1/`: build `PACKAGE_SUMMARY.json`, derive `COMPLETE|PARTIAL|GAP|UNSUPPORTED|FAILED`, align keyword `leg_role` in DATA_MAP/cards/coverage, extend validator. No new collectors; `zip_determinism_contract` = `PAYLOAD_HASH_ONLY` (archive byte identity out of scope).

## Acceptance

Unit tests in `tests/unit/ai_package_v1/`; locked semantic contract; `FULL_AI_PACKAGE_ACCEPTANCE_REPORT` absent in repo (recorded, non-blocking).
