# Tasks — attribution-facts-contract

Planning artifact. Implementation via `/opsx-apply` after Owner implementation GO.

```text
TASKS_STATUS: SLICE_A_COMPLETE
PLANNING_READY: yes
APPLY_READY: slice_a_applied
OWNER_CONTRACT_STATUS: ACCEPTED (Owner GO Slice A)
```

## Out of scope (all slices)

Dynamic DRR implementation; shop-wide DRR capacity controller; MCP transport;
ChangeSet Apply; unrelated collectors; production deployment.

---

## Slice A — Domain contract + port + unit tests

- [x] A.1 Scaffold `app/modules/attribution_facts/` package (domain, ports)
- [x] A.2 Implement `AttributionCommerceFact`, keys, `MembershipSnapshot`, coverage types
- [x] A.3 Pure `classify_fact`, `reconcile_day`, derived metric helpers (CPO/DRR)
- [x] A.4 Define `AttributionFactsReader` protocol + in-memory fake
- [x] A.5 Unit tests: DIRECT/LINKED/UNKNOWN/UNATTRIBUTED, revision replace, DENOMINATOR_ZERO
- [x] A.6 Unit tests: fail-closed reason codes; no zero-on-missing

**Gate:** `poetry run pytest -m unit tests/unit/attribution_facts/ -v`

---

## Slice B — Source adapter + membership resolver

- [ ] B.1 ADR `attribution-facts-collector-ownership` accepted at apply start
- [ ] B.2 Raw fullstats apps/nms normalizer (before collapsed mapper)
- [ ] B.3 `MembershipSnapshotResolver` (history → inventory fallback → provenance)
- [ ] B.4 Wire ingest hook from shop-runner fullstats fetch seam (no spend duplication)
- [ ] B.5 Unit tests with fixture payloads (`wb_a1_associated_conversions` shape)
- [ ] B.6 Integration test: history repository read + resolver as-of (if CH/PG fixtures exist)

**Gate:** ingest produces observations; mapper-only path cannot mark COMPLETE

---

## Slice C — CH store + backfill + reader

- [ ] C.1 Propose CH DDL via clickhouse-migrations control plane (separate migration GO)
- [ ] C.2 Observation repository append + latest projection queries
- [ ] C.3 Backfill job design (bounded windows; read-only WB if needed — Owner GO for live)
- [ ] C.4 `ChAttributionFactsReader` implements port
- [ ] C.5 Reconciliation batch marks day PASS/FAIL in metadata
- [ ] C.6 Integration tests destructive_local CH

**Gate:** reader returns facts + coverage for fixture shop/adv window

---

## Slice D — AI Package / analysis consumption

- [ ] D.1 Wire `AnalysisAggregationService` to `AttributionFactsReader`
- [ ] D.2 Emit `attributed_orders` / GMV direct+linked; CPO_FACT_* / DRR_FACT_* when COMPLETE
- [ ] D.3 Retain `BLOCKED_BY_ATTRIBUTION_FACTS` when not COMPLETE
- [ ] D.4 Contract tests under `tests/unit/ai_package_v1/` for analysis attribution fields
- [ ] D.5 Update multi-window spec scenarios (consumer change coordination)

**Gate:** targeted ai_package_v1 unit tests; no MCP transport edits

---

## Planning verification (this hop)

- [x] P.1 Scaffold OpenSpec change artifacts
- [x] P.2 Proposed ADR `attribution-facts-collector-ownership`
- [x] P.3 `openspec validate attribution-facts-contract --type change --strict`
- [x] P.4 `git diff --check`
- [ ] P.5 `poetry run python tools/openspec/openspec_guard.py` on touched paths (if applicable)

---

## Final acceptance (post Slice D)

- `openspec validate attribution-facts-contract --type change --strict` passes
- Unit + integration gates per slices A–D
- No production WB writes from attribution module
- Spend still owned by `full_adv_wb_stat` only
