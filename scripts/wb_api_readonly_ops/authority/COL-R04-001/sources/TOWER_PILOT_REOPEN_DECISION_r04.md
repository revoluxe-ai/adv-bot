# TOWER PILOT REOPEN DECISION — r04

## Request identity

- Request ID: `REQ-WBSKY-AUDIT-METHODOLOGY-V1-PILOT-DATA-COLLECTION-001`
- Decision type: `PILOT_REOPEN_AND_PROSPECTIVE_SCOPE_AMENDMENT`
- Effective at: `2026-08-07T10:10:00+03:00`
- Parent terminal evidence: `r03b`
- Reopen request ZIP SHA-256: `cd14194648edb9b7fa14e91a9aeb863d4c91544ba62e63cc5b7ae05b88599a96`

## Decision

```text
PILOT_REOPEN_DECISION=YES
PILOT_REOPEN_AUTHORIZED=YES
EXECUTION_ROUND=r04
R03B_PARK_STATUS=SEALED_HISTORICAL_TERMINAL_EVIDENCE
R03B_REINTERPRETATION_AUTHORIZED=NO
R03B_RECOLLECTION_AUTHORIZED=NO

READ_ONLY_METHOD_POLICY=GET_OR_DOCUMENTED_POST_AS_READ
READ_ONLY_COLLECTION_AUTHORIZED=NO
READ_ONLY_ACTIVE=NO
FINAL_REVIEW_AUTHORIZED=NO

CLIENT_AUDIT_AUTHORIZED=NO
PRODUCTION_IMPLEMENTATION_AUTHORIZED=NO
WRITE_OPERATIONS_AUTHORIZED=NO
CAUSAL_LAYERS_AUTHORIZED=NO
```

This is a prospective coordination decision for a new `r04` execution contour. It is not a Final Review and assigns none of `ACCEPTED`, `ACCEPTED_WITH_GAPS`, `REVISION_REQUIRED`, or `REJECTED`.

The sealed `r03b` record remains exactly `PARK / BLOCKED_BY_SPECIFIC_INPUT`. Nothing in r04 converts the quarantined/refusal evidence into PASS.

## Why reopen is admissible

The Owner explicitly requests a new execution round after terminal PARK and supplies two prospective scope amendments. The prior run is not under review and its acceptance criteria are not being rewritten retroactively.

The r01 pilot Commission used a stricter GET-only execution contour. r04 replaces that run-specific restriction prospectively while retaining the methodology-level no-write invariant: an HTTP verb does not itself determine mutation; only endpoint-specific documented and runtime semantics may admit a POST operation as read-only.

## API method policy — r04

### Allowed method classes

1. `GET_READ`
2. `POST_DOCUMENTED_AS_READ`
3. `POST_READ_AUXILIARY_JOB` only when the operation creates/retrieves an ephemeral report/query job and cannot create, update, delete, start, stop, pause, resume, bid, budget, price, content, stock, order, user/access or other seller/business state.

### Endpoint-level admission rule

A POST endpoint is allowed only when all of the following are evidenced before its first runtime call:

- exact host/path/service family is frozen;
- current official WB API documentation, exact OpenAPI/Swagger artifact, or equivalent authoritative local contract identifies the operation and its input/output semantics;
- the supporting documentation artifact has an immutable reference/hash or exact dated URL/version;
- request body is query/filter/report-retrieval input, not a mutation command;
- no seller/account/business-state mutation is documented or reasonably implied;
- required token category/entitlement is account-specific and secret-safe;
- executor classifies the operation as `POST_DOCUMENTED_AS_READ` or `POST_READ_AUXILIARY_JOB`;
- the operation is added to the r04 read-only allowlist before use.

`POST` is therefore **not globally allowed**. Unknown or mixed semantics produce `REFUSED_MUTATION_SEMANTICS_UNRESOLVED`.

Always prohibited:

- `PUT`, `PATCH`, `DELETE`;
- GraphQL mutation;
- any POST that changes campaigns, bids, budgets, cards/content, prices/discounts, stock, orders, users/access or operational state;
- undocumented POST;
- any endpoint whose side effects cannot be bounded.

HTTP success alone never proves admissibility. Runtime PASS still requires entitlement, response schema fingerprint, period/time semantics, pagination/completeness, limits and source-semantic binding.

## Required API family set

Target family set:

- `ORDERS_OR_SALES_REPORTS_READ`
- `PROMOTION_STATISTICS_READ`
- `PROMOTION_CAMPAIGNS_READ`
- `CONTENT_CARDS_READ`

Pilot minimum admissible family set:

- `ORDERS_OR_SALES_REPORTS_READ`
- `PROMOTION_STATISTICS_READ`
- `PROMOTION_CAMPAIGNS_READ`

`CONTENT_CARDS_READ` is `OPTIONAL_FOR_R04_COLLECTION_PASS_WITH_DISCLOSED_GAP` if no endpoint can be admitted under the r04 documented read-only policy.

A missing mandatory family means `API_PREFLIGHT=REFUSED`. A missing optional content-card family must be recorded as an explicit gap and may not be silently substituted.

## Cabinet policy — r04

Tower selects **B1: NEW OWNER-LOCAL CABINET PREFLIGHT**.

The quarantined r03/r03b cabinet bytes may be used only as historical diagnostic context. They cannot satisfy any r04 PASS condition.

### Required new cabinet preflight fields

- account alias: `WB-TEST-CABINET-001`;
- store label: `Дилера`;
- role: `Аналитик`;
- exact report/path alias;
- exact period: `2026-07-04..2026-08-02`;
- timezone: `+03:00` / source label if exposed;
- allowed UI/network operation classes;
- explicit mutation denylist;
- export/capture capability;
- new same-session schema fingerprint;
- new same-session source-instance fingerprint;
- collector capture timestamps;
- period/event-time semantics;
- no-write evidence;
- redaction/secret scan result.

### Timestamp rule

Every new r04 network occurrence/evidence item must have a collector-generated `captured_at` timestamp in RFC3339 with explicit offset.

If a source-native timestamp is absent, record:

```text
SOURCE_NATIVE_TIMESTAMP=ABSENT
```

Do not infer or synthesize it.

Absence of a source-native timestamp is not by itself a preflight failure when the evidence is a structural/session observation and `captured_at` is complete. For data used as period/event evidence, admission additionally requires either:

1. a source-native event/effective timestamp; or
2. a source-defined report/filter interval whose semantics prove that the row/aggregate belongs to the locked period.

Otherwise that dataset is quarantined with `REFUSE_EVENT_TIME_OR_PERIOD_SEMANTICS_UNPROVEN`.

The r03 statistic `800/1125 UNKNOWN_SOURCE_TIMESTAMP` cannot be carried forward as PASS evidence; r04 must collect new timestamp-complete preflight evidence.

### Schema/source version rule

A vendor-exposed semantic version is preferred but not mandatory if WB does not expose one.

r04 requires both:

- `schema_fingerprint`: deterministic hash of the observed report/export/network response structure;
- `runtime_source_instance_fingerprint`: deterministic hash binding report/path alias + observed schema + relevant visible/runtime version/build markers + capture protocol version.

If the vendor semantic version is unavailable, record:

```text
VENDOR_SEMANTIC_VERSION=NOT_EXPOSED
SOURCE_VERSION_CLASS=LOCAL_RUNTIME_FINGERPRINT
```

This local fingerprint is a pilot evidence identity, not a claim about an official WB semantic version. Any fingerprint change during the session triggers `SESSION_BOUNDARY_CHANGED` and revalidation.

## Source-contour gate

r04 retains one global `READ_ONLY_PREFLIGHT_PASS`.

To enter it:

- Cabinet preflight must PASS under the new r04 rules;
- API preflight must PASS for all three mandatory API families;
- any optional `CONTENT_CARDS_READ` refusal must be explicitly logged;
- no secret may enter artifacts;
- no prohibited mutation operation may occur;
- exact account/object/period/source scope remains locked.

Only then may bounded mass collection begin.

## Execution contour

```text
OWNER_LOCAL_PREFLIGHT_R04
→ READ_ONLY_PREFLIGHT_PASS
→ OWNER_LOCAL_BOUNDED_COLLECTION_R04
→ CLEAN_DUMP
→ FORMATTER_R04
→ INDEPENDENT_VALIDATION_R04
→ SUBMITTED_FOR_REVIEW (only if package/validation support it)
→ FINAL REVIEW (Tower-authorized only after deliberate submission)
```

`WEB COLLECTOR=OUT_OF_SCHEME`.

Owner-local / OpsX runtime handles credentialed access. Secrets never leave Owner-local runtime. FORMATTER may package only redacted/sealed artifacts and references.

## Locked non-secret scope

```text
STORE_LABEL=Дилера
ACCOUNT_SCOPE_ALIAS=WB-TEST-CABINET-001
CABINET_ROLE=Аналитик
PERIOD_START=2026-07-04T00:00:00+03:00
PERIOD_END=2026-08-02T23:59:59+03:00
CABINET_INCLUDED=YES
API_INCLUDED=YES
PUBLIC_BUYER_SURFACE_INCLUDED=NO
CLIENT_PROVIDED_DATA_INCLUDED=NO
```

Raw account IDs, tokens, cookies, session state and identifier maps remain `OWNER_LOCAL_ONLY`.

## Required r04 terminal outputs

The r04 RHP must preserve the r01 package contract but use round `r04` and include at minimum:

- authorization/scope record amended by this decision;
- new cabinet preflight report;
- new API preflight report with endpoint-level method classification;
- endpoint allowlist and documentation bindings;
- no-write invariant evidence;
- timestamp completeness report;
- schema/source-instance fingerprint register;
- source binding register;
- collection plan and session log;
- raw evidence index;
- module activation register;
- gaps/refusals/contradictions;
- evidence ledger;
- secret/redaction scan;
- session close record;
- validation report;
- Research Handoff.

## Stop conditions

Return `BLOCKED_BY_SPECIFIC_INPUT` or `FAILED_EXECUTION` rather than weakening fail-closed if:

- a mandatory API family cannot be mapped/admitted;
- cabinet period/event semantics remain unresolved;
- new preflight lacks complete collector `captured_at`;
- schema/source-instance fingerprint cannot be established;
- an operation has mutation risk or undocumented semantics;
- secret-safe execution cannot be maintained;
- scope drifts from the locked account/period/source set.

## Explicit retained negative authorizations

```text
FINAL_REVIEW_AUTHORIZED=NO
CLIENT_AUDIT_AUTHORIZED=NO
PRODUCTION_IMPLEMENTATION_AUTHORIZED=NO
WRITE_OPERATIONS_AUTHORIZED=NO
CAUSAL_LAYERS_AUTHORIZED=NO
```

Final Review remains unavailable until a later deliberate package is returned with executor status `SUBMITTED_FOR_REVIEW`.

## Next task

```text
NEXT_TASK_ID=COL-R04-001
NEXT_CHAT_TITLE=PILOT EXECUTION — REQ-WBSKY-AUDIT-METHODOLOGY-V1-PILOT-DATA-COLLECTION-001 — r04
```
