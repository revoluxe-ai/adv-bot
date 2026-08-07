# COL-R04-001 — OpsX Install Package

## Dispatcher decision

- ROUTE: `REUSE_OPSX_WITH_INSTALL`
- EXACT_TITLE: `COL-R04-001 — OWNER_LOCAL_READ_ONLY_PREFLIGHT_R04`
- PURPOSE: upgrade/reuse the existing Owner OpsX `wb_api_readonly_ops` job contour for the r04 owner-local read-only preflight.
- RETURN_TARGET: WB Promotion Audit Research Lab chat supplied by Owner.

## Why this route

The governing r04 materials require credentialed execution to remain Owner-local/OpsX, explicitly exclude Web Collector, and prohibit Local Cursor from calling the production cabinet/API. The preferred runtime is the existing Owner OpsX / `wb_api_readonly_ops` job contour, upgraded for documented POST-as-read plus the new cabinet B1 preflight fields.

Do not create a new ChatGPT Project for execution. Do not move credentials into ChatGPT. Do not use Local Cursor as the production API/cabinet caller.

## Install contract

Install or upgrade a dedicated task/job named:

`COL-R04-001 — OWNER_LOCAL_READ_ONLY_PREFLIGHT_R04`

The job MUST:

1. Treat the attached r04 authority files as binding and fail closed on conflict or missing evidence.
2. Lock non-secret scope to:
   - STORE_LABEL=`Дилера`
   - ACCOUNT_SCOPE_ALIAS=`WB-TEST-CABINET-001`
   - CABINET_ROLE=`Аналитик`
   - PERIOD=`2026-07-04T00:00:00+03:00..2026-08-02T23:59:59+03:00`
3. Keep all credentials, token values, cookies, session state, raw account IDs, browser profiles and identifier maps Owner-local only.
4. Enforce `READ_ONLY_METHOD_POLICY=GET_OR_DOCUMENTED_POST_AS_READ`.
5. Allow only `GET_READ`, `POST_DOCUMENTED_AS_READ`, and `POST_READ_AUXILIARY_JOB` after endpoint-level authoritative documentation binding and local allowlisting.
6. Always prohibit PUT, PATCH, DELETE, GraphQL mutation, undocumented POST, and any business-state mutation.
7. Perform a NEW cabinet B1 preflight. r03/r03b bytes may be diagnostic context only and MUST NOT satisfy r04 PASS.
8. Preflight the three mandatory API families:
   - `ORDERS_OR_SALES_REPORTS_READ`
   - `PROMOTION_STATISTICS_READ`
   - `PROMOTION_CAMPAIGNS_READ`
   `CONTENT_CARDS_READ` is optional only with an explicit disclosed gap.
9. Require collector `captured_at` RFC3339 with explicit offset for 100% of new evidence items. If source-native timestamp is absent, record `SOURCE_NATIVE_TIMESTAMP=ABSENT`; never infer it.
10. Produce both `schema_fingerprint` and `runtime_source_instance_fingerprint`. If WB semantic version is unavailable, record `VENDOR_SEMANTIC_VERSION=NOT_EXPOSED` and `SOURCE_VERSION_CLASS=LOCAL_RUNTIME_FINGERPRINT`.
11. Establish no-write evidence, redaction/secret scan, exact source bindings, endpoint classifications, period semantics, entitlement/token-category checks, pagination/completeness and limits for each mandatory API family.
12. Return PASS only when CABINET=PASS, all three mandatory API families=PASS, NO_WRITE_GATE=PASS, SECRET_GATE=PASS, and SCOPE_DRIFT=NO.
13. Stop after generating the preflight return package for Lab. Do NOT begin mass collection in this install/run step.

## Required preflight return package

Produce exactly one general ZIP for the Lab handoff, suggested name:

`COL-R04-001_OWNER_LOCAL_READ_ONLY_PREFLIGHT_R04.zip`

It should contain, at minimum:

- authorization/scope record;
- new cabinet preflight report;
- new API preflight report;
- endpoint allowlist and documentation bindings;
- no-write invariant evidence;
- timestamp completeness report;
- schema/source-instance fingerprint register;
- source binding register;
- gaps/refusals/contradictions;
- secret/redaction scan;
- preflight verdict / exact blocker;
- `SHA256SUMS.txt` for included artifacts.

Return the ZIP plus its SHA-256 in handoff text. The ZIP MUST contain no credentials, cookie/token values, browser profiles, session secrets, or raw identifier maps.

## Authority priority

1. `sources/TOWER_PILOT_REOPEN_DECISION_r04.md`
2. `sources/R04_EXECUTION_SCOPE.yaml`
3. `sources/COL-R04-001_OWNER_LOCAL_PREFLIGHT_TZ.md`
4. `sources/OWNER_REQUEST_DISPATCHER_COL_R04_001.md`

If any implementation behavior conflicts with these sources, stop fail-closed and report the exact conflict.
