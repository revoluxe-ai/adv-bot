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

## 6. SQLAlchemy RowMapping normalization + regression (runtime follow-up)

Do **not** reopen completed tasks 1–5. Preserve Job-local PG ownership, one
Job-scoped loop, deterministic dispose, typed `EvidenceReaderFailure`,
read-only posture, and WB/fullstats/orders behavior. Do **not** rewrite to
asyncpg or recast this TypeError as a legitimate GAP.

- [x] 6.1 Update shared `_pg_row_as_dict` so Job-path SQLAlchemy mapping
      results are accepted: `collections.abc.Mapping` including
      `sqlalchemy.engine.row.RowMapping` → deterministic plain `dict`;
      SQLAlchemy `Row` via documented `row._mapping`; unsupported objects →
      explicit `TypeError`.
- [x] 6.2 Add executable regression using real SQLAlchemy `RowMapping`
      (preferably an execute/result seam returning the same concrete type):
      dict-only / current helper fails; corrected helper preserves column
      names and values; negative test: unsupported non-mapping object →
      explicit `TypeError`.

## 7. Runtime t0055 — bundle shape, section boundaries, physical_spend (apply only)

Do **not** reopen tasks 1–6 or lifecycle/RowMapping/WB adapter fixes unless
regression proof requires it. No new collector, Registry entry, or ProKraft fork.

- [x] 7.1 **Shared bundle normalization:** ensure `load_owner_bot_evidence_bundle`
      emits dict-only `pg_rows`, `orders`, and `fullstats` trees (recursive
      `jsonable` / `to_dict` for `FullStatsItem` and nested day/app/nm nodes) so
      plane readers never call `.get()` on attrs/ORM objects. Preserve Job-local
      PG engine, one loop, dispose, `assert_read_only_op`, and existing WB seams.
- [x] 7.2 **Section reader hardening:** align
      `OwnerBotStrictSingleNmidReadOnlyPlane` `read_current_contour`,
      `read_orders`, `read_attribution`, `read_topology`, and
      `read_physical_spend` with the normalized bundle contract; fix
      `read_topology` / membership handling for t0055-shaped payloads (no bare
      `AttributeError` on supported shapes).
- [x] 7.3 **Orchestration boundary:** update `StrictSingleNmidAudit.run` so
      implementation shape failures are not mislabeled as legitimate section GAPs
      via bare `{section}: AttributeError` when bundle/reader code is at fault;
      preserve typed `EvidenceReaderFailure` mapping and `write_budget.writes=0`.
      Do not “fix” by wrapping every `AttributeError` into `EvidenceReaderFailure`
      without normalization.
- [x] 7.4 **Physical spend reconciliation:** fix canonical `physical_spend`
      vs top-level `evidence[]` split (t0055: confirmed `562.01` in `evidence[]`
      but `physical_spend.status=missing` / empty `physical_spend.evidence`); no
      new spend semantics.
- [x] 7.5 **Executable regressions (t0055 shapes):** add tests using realistic
      production objects/payloads (SQLAlchemy mapping rows → dict, supplier order
      dicts, `FullStatsItem` / nested stats trees, t0055-like membership + spend
      fixtures). Prove: no raw `AttributeError` crosses section boundary for
      supported shapes; legitimate source absence stays typed GAP;
      canonical `physical_spend` populated when spend reader confirms; `writes=0`.
