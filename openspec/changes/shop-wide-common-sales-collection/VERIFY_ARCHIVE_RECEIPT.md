# VERIFY_ARCHIVE_RECEIPT

```yaml
TASK_ID: WB-SKY-COMMON-SALES-ARCHIVE-VERIFY-20261005-0480
RECEIPT_CLOSE_TASK: WB-SKY-COMMON-SALES-ARCHIVE-RECEIPT-CLOSE-20261005-0481
CHANGE_ID: shop-wide-common-sales-collection
MODE: archive
REVIEWER: independent QA (0480; receipt-close 0481 same reviewer)
STAGE_HEAD: 58441b3589200e02f642628e05920e680e553355
MERGE_COMMIT: 58441b3589200e02f642628e05920e680e553355
FINISHED_AT: 2026-10-05T05:16:22+03:00
RECEIPT_CLOSED_AT: 2026-10-05T05:22:43+03:00
ARCHIVE_VERIFY: GO
POST_MERGE_VERIFY: PASS (CHANGE_SCOPED)
PRODUCT_ACCEPTANCE_STATUS: PASS
```

## Итоговый вердикт

**GO** — archive можно продолжать (`/opsx-archive shop-wide-common-sales-collection`).

Post-merge stage принят в scope change: 76 targeted tests PASS, canonical committed merge
0 pyright errors, foreign dirty baseline 4 errors без новых diagnostics.

## PRODUCT_ACCEPTANCE

| Field | Value |
|-------|-------|
| PRODUCT_ACCEPTANCE_REQUIRED | true |
| PRODUCT_ACCEPTANCE_STATUS | **PASS** |

### Pillar 1 — MEANING_LOCK

| Field | Value |
|-------|-------|
| SEMANTIC_WRITE_TARGET_STATUS | RESOLVED |
| Evidence | `design.md` explicit block: `TARGET_ENTITY_OR_LEG`, `ALLOWED_ADAPTERS`, `FORBIDDEN_ADAPTERS` |
| Decision | `decisions/shop-wide-common-sales-ownership/decision.md` (accepted) |
| Verdict | **PASS** — single coordinator → `wb_common_stat`; forbidden adapters not on production path |

### Pillar 2 — LIFECYCLE_COVERAGE

| Field | Value |
|-------|-------|
| LIFECYCLE_STATUS | DERIVED (design.md L1–L8) |
| Owner Contract | reviewed primary path; no second CONFIRM_LIFECYCLE |
| Scenario report | 0260 historical PASS 33/33; 0480 bridge `CURRENT_SCOPE_AUDIT_CERTIFICATION.md` |
| Log freshness | 0470 post-merge logs SHA256-verified (74+2 PASS) |
| Verdict | **PASS** — all lifecycle steps mapped; fresh provider/integration binding |

### Pillar 3 — SIDE_EFFECT_PROOF

| Field | Value |
|-------|-------|
| S12 CH write/read | 2/2 integration PASS (`postmerge-integration-ch.log`) |
| Production writer | `test_collect_by_nmids_uses_production_writer` green |
| S13 read-only WB | static module boundary + full coordinator tick seams (0260 note: placebo test not sole proof) |
| S14 no full_adv writes | import-graph isolation + S12 writer proof (0260 note: no explicit spy; adequate) |
| Verdict | **PASS** — this-run external CH side effects proven; forbidden sibling non-mutation evidenced |

## Поведение

Behavior matches spec: **yes**

Implementation @ `58441b358` matches delta spec scenarios; `git diff 3afdde673 58441b358`
empty on all shop-wide production/test paths.

## Архитектурное размещение

Implementation matches architecture decisions: **yes**

| Decision | Path | Status |
|----------|------|--------|
| Shop-wide ownership | `decisions/shop-wide-common-sales-ownership/decision.md` | accepted (in change; promotion at archive) |
| CH migration lifecycle | `openspec/decisions/clickhouse-migration-lifecycle-ownership/decision.md` | accepted |
| Campaign boundary | sibling reconciliation CAMPAIGN_CHANGE_RECONCILED=YES | cited in design |

Placement violations: **none**

`openspec/decisions/index.md` — foreign dirty; **not modified** (0460 normative).

## Тесты

| Check | Result |
|-------|--------|
| Targeted unit (74) | **passed** |
| Targeted integration CH (2) | **passed** |
| Import sanity | **passed** |
| openspec validate --strict | **passed** |
| git diff --check | **passed** |
| Test coverage packet | absent (legacy compatibility) |
| Scenario coverage report | PASS (0260 + 0480 bridge) |
| Scenario coverage required | true |
| Behavioral scenarios | covered (33/33) |
| Provider receipts | fresh (0470 CH log) |

### Pyright gate (scoped interpretation)

| Snapshot | errorCount | Scope |
|----------|------------|-------|
| Stage + 92 foreign dirty (actual working tree) | 4 | **baseline NOT GREEN** — foreign `adapter.py` only |
| Merged committed clean archive (`58441b358`) | **0** | change-scoped canonical |
| Diagnostic parity premerge vs postmerge | true | **no new regressions** |

0470 historical receipt preserved FAIL on unscoped pyright; 0480 supersedes scoped verdict only.

## Согласованность tasks

Task completion mismatch: **no**

All `- [x]` in `tasks.md`; `openspec status --json` → `isComplete: true`.

## Post-merge gates (0470 + 0480 re-verification)

| Gate | Result |
|------|--------|
| Unit 74 | PASS |
| Integration CH 2 | PASS |
| Import sanity | PASS |
| openspec validate | PASS |
| diff --check | PASS |
| Foreign 92 dirty preserved | PASS (0 hash mismatches vs preflight) |
| Index empty (pre-QA-commit) | PASS |
| Introduced pyright diagnostics | **none** (parity true) |
| Canonical committed merge pyright | **0 errors** |

## Source immutability

- Implementation + targeted tests: byte-stable `3afdde673` → `58441b358`.
- 15-path manifest: `CURRENT_SCOPE_AUDIT_CERTIFICATION.md`.
- Ancestors: `2ccff632`, `3afdde673` ⊆ HEAD ✓

## Scenario audit freshness

| Binding | 0260 (historical) | 0480 (current) |
|---------|-------------------|----------------|
| HEAD | `62c8d48…` (planning) | `58441b358` (merged stage) |
| Spec SHA | `5e24eab…` (0260 cert LF binding) | `5e24eab…` (git blob LF, stable `3afdde673`→HEAD) |
| Unit log | 72 passed | 74 passed (`dabdc328…`) |
| CH log | `47bff5dc…` | `eb57f8a3…` (fresh 0470) |

Historical cert/report **not rewritten**. Bridge artifact records deterministic current manifest.

## Spec EOL provenance (0481 receipt-close lineage)

0480 manifest row `4697e648…` for post-merge spec — **0481 recomputation invalidates that binding**
(no artifact in repo or runner produces SHA256 `4697e648d76f3efcf22b269c51db9048a6ef22e8`).

| Binding | SHA256 | Notes |
|---------|--------|-------|
| Git blob @ `3afdde673`..`58441b358` (LF, `.gitattributes eol=lf`) | `5e24eabdaa2f6bf4daaa494ea6bbca5da73dd443e0540d7568acbca78b508253` | git object `ca08b9a58bb65ab24c7dcbf81d2865ced813b59f`; worktree == blob |
| 0260 `SOURCE_SPEC_SHA` (cert, immutable) | `5e24eab…` | same LF-normalized content hash — **not** a separate semantic revision |
| CRLF simulation (Windows raw disk form) | `8098b768858249bf968a9ee6e7f26d8f765338232f9d2920bfb206fceb2a07bc` | EOL-only delta class; **no false raw-byte-equal claim** vs cert fingerprint |
| `git diff 3afdde673 58441b358 -- specs/` | empty | no content delta beyond EOL class (none observed; LF byte-stable) |
| 15-path implementation manifest | `git diff 3afdde673 58441b358` empty | exact physical path compare @ merge HEAD |

Historical `certify.receipt.json` / `SCENARIO_TEST_COVERAGE_REPORT.md` **not rewritten**.

## Archive prep (evaluate only — not executed)

| Item | Status |
|------|--------|
| Delta spec sync target | `openspec/specs/shop-wide-common-sales-collection/spec.md` — **not present** (sync at archive) |
| Decision promotion | `decisions/shop-wide-common-sales-ownership/decision.md` → `openspec/decisions/` at archive |
| index.md write | **forbidden** (foreign dirty) |
| openspec archive CLI (non-interactive) | `poetry run openspec archive shop-wide-common-sales-collection -y` |

## OUT_OF_SCOPE (explicit, not blockers)

- METRICS_SOURCE_CURRENCY unknown
- STORE_DRR_NUMERATOR BLOCKED_BY_CAMPAIGN_COVERAGE
- HISTORY_BACKFILL DEFERRED
- live WB proof not executed
- prod CH DDL unverified

## Linked bug cards (soft)

none

## Следующая команда (Owner-authorized; not executed by 0481)

```powershell
poetry run openspec archive shop-wide-common-sales-collection -y
```

Equivalent workflow entry: `/opsx-archive shop-wide-common-sales-collection` (uses `-y` / `--yes` to skip interactive sync prompt when Owner has pre-authorized sync+archive).

## Evidence artifacts (this run)

- `CURRENT_SCOPE_AUDIT_CERTIFICATION.md` (0481 EOL lineage addendum)
- `POST_MERGE_VERIFY.md` (scoped PASS + historical 0470 FAIL preserved)
- `MERGE_EVIDENCE.md` (0480 addendum)
- `scenario-coverage/logs/postmerge-*.log`
- `lifecycle-proof/comparison.json`, `diagnostic-parity.json`
- `lifecycle-proof/raw-canonical/` (4 pyright stdout/stderr logs + `postmerge-pyright-merged-committed.json`)

✅ GO
