# COL-R04-001 — OWNER_LOCAL_READ_ONLY_PREFLIGHT_R04

RECORDED_AT: 2026-08-07T11:30:27.983105+03:00
SOURCE: PILOT EXECUTION Lab first-gate response
LAB_CHAT: https://chatgpt.com/g/g-p-6a6a79c2150481918258d6db0ce5415b-wb-promotion-audit-research-lab/c/6a7588e6-03a8-83ed-a2b8-ecef47c99930
AUTHORITY: TOWER_PILOT_REOPEN_DECISION_r04 + RESEARCH_COMMISSION_AMENDMENT_r04 + R04_EXECUTION_SCOPE.yaml

## Mode

TASK_ID=COL-R04-001
MODE=OWNER_LOCAL_READ_ONLY_PREFLIGHT_R04
MASS_COLLECTION=FORBIDDEN
FINAL_REVIEW_AUTHORIZED=NO
R03B_BYTES_AS_PASS=FORBIDDEN

## Binding (non-secret)

STORE_LABEL=Дилера
ACCOUNT_SCOPE_ALIAS=WB-TEST-CABINET-001
CABINET_ROLE=Аналитик
PERIOD=2026-07-04T00:00:00+03:00..2026-08-02T23:59:59+03:00

shop_id / tokens / cookies: OWNER_LOCAL_ONLY — never into Web/Cursor packages.

## 1. Cabinet B1 — NEW Owner-local preflight

Do not reuse r03/r03b cabinet bytes as PASS.

Must capture for every new evidence item:
- exact report/path alias
- period/filter semantics
- timezone/source label
- allowed UI/network operation classes
- explicit mutation denylist
- export/capture capability
- captured_at RFC3339 with explicit offset (100% of new items)
- source-native timestamp OR SOURCE_NATIVE_TIMESTAMP=ABSENT (do not invent)
- schema_fingerprint
- runtime_source_instance_fingerprint
- VENDOR_SEMANTIC_VERSION=NOT_EXPOSED if WB does not expose
- no-write evidence
- redaction/secret scan

Period/event admission only with native event/effective time OR source-defined report/filter interval semantics.

## 2. API preflight — same contour

READ_ONLY_METHOD_POLICY=GET_OR_DOCUMENTED_POST_AS_READ

MANDATORY families:
- ORDERS_OR_SALES_REPORTS_READ
- PROMOTION_STATISTICS_READ
- PROMOTION_CAMPAIGNS_READ

OPTIONAL_WITH_DISCLOSED_GAP:
- CONTENT_CARDS_READ

Before any POST:
- bind exact host/path/family to authoritative WB docs/OpenAPI/local immutable contract
- record immutable hash OR exact dated/versioned reference
- prove non-mutating read semantics
- classify POST_DOCUMENTED_AS_READ or POST_READ_AUXILIARY_JOB
- add to r04 read-only allowlist

Forbidden: PUT/PATCH/DELETE/GraphQL mutation/undocumented POST/business-state mutation.

HTTP success ≠ PASS. Per mandatory family also check:
entitlement/token-category, schema fingerprint, source/version binding,
period semantics, pagination/completeness, limits, no-write semantics.

## 3. Global PASS condition

READ_ONLY_PREFLIGHT_PASS only if:
CABINET=PASS
AND 3 mandatory API families=PASS
AND NO_WRITE_GATE=PASS
AND SECRET_GATE=PASS
AND SCOPE_DRIFT=NO

Else fail closed with exact blocker. No mass collection.

## 4. Return packaging

One general ZIP of new r04 preflight artifacts + SHA-256 in chat handoff text.
No credentials/cookies/token values/browser profiles/raw identifier maps.

Upload return ZIP into Lab chat:
https://chatgpt.com/g/g-p-6a6a79c2150481918258d6db0ce5415b-wb-promotion-audit-research-lab/c/6a7588e6-03a8-83ed-a2b8-ecef47c99930

Preferred runtime: existing Owner OpsX / wb_api_readonly_ops Job contour (upgrade for POST-as-read + cabinet B1 fields), not Local Cursor calling prod/API.
