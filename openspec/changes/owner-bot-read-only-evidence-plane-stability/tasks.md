## 1. Planning verification (read-only)

- [x] 1.1 Зафиксировать HEAD baseline и recheck table в design (orphan API, loop, PG, typed failures).
- [x] 1.2 Подтвердить, что задачи не дублируют уже исправленное на HEAD без regression proof (`get_fullstats`, single-plane loop skeleton).

## 2. Shared evidence plane design

- [x] 2.1 Finalize placement shared loader (prefer `scripts/wb_api_readonly_ops/` extract) и связь с proposed decision lifecycle.
- [x] 2.2 Specify Job-scoped async entry/exit contract (`ensure_bundle`, `close`, dispose) as reusable API.
- [x] 2.3 Specify Job-safe PG read facade aligned with `ch_a1_evidence.run_pg_query` semantics (no ProKraft fork).

## 3. Implementation tasks (apply phase — not started)

- [x] 3.1 Extract/implement shared Owner-bot evidence loader wrapping orders/sales + supported fullstats + PG reads.
- [x] 3.2 Refactor `strict_single_nmid_audit_owner_bot_plane.py` to consume shared loader only; remove remaining ad-hoc SQLAlchemy PG path if superseded.
- [x] 3.3 Normalize fullstats/jsonable shape for attribution/spend readers; align with adapter types.
- [x] 3.4 Map reader/lifecycle failures to typed provenance consumed by `StrictSingleNmidAudit.run`.
- [x] 3.5 Wire strict Job entry to shared plane lifecycle (preload + finally close) without Registry changes.

## 4. Tests and regression

- [x] 4.1 Add unit tests: Job loop lifecycle, engine dispose, forbid orphan `get_fullstats` references.
- [x] 4.2 Add unit tests: typed failure provenance mapping at orchestration boundary.
- [x] 4.3 Run/extend A1 strict collect targeted regression tests — must stay green.
- [x] 4.4 Add integration/harness test simulating plane open/load/close without cross-loop `RuntimeError` (no live prod WB if unit mocks suffice).

## 5. Verification gates (pre-archive of this change)

- [x] 5.1 `poetry run pytest` targeted suites for new/changed tests.
- [x] 5.2 Confirm `write_budget.writes=0` invariant preserved in strict audit tests.
- [x] 5.3 Document explicit non-goals: stock/attribution catalog, Registry/resolver untouched.
