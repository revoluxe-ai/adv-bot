## Context

Нужен Owner-local research path: safe WB API read для выбранного магазина,
best-effort сбор по четырём семьям данных, архив на локаль через `/opsx-scripts`.
Не Web CLEAN_DUMP и не Stage B accept gate.

Pilot binding (TZ, arg only): shop «Дилера»,
`shop_id=bab6bc8e-8123-4559-862e-5da3a8ed5b69`.

Стек: `get_access_for_wb_cabinet` + `app/core/mp/wb/api` managers/adapters;
ретраи — shop-runner production patterns + finite run ceiling.
Policy: `READ_ONLY_NO_MUTATION` (POST-read OK).

## Goals / Non-Goals

**Goals:**

- Entrypoint + Job: `--shop-id`, `--mode preflight|collect`.
- `preflight` — smallest probe по 4 aliases.
- `collect` — best-effort pull; PARTIAL + gap report OK; no silent full success.
- Reuse existing stack + shop-runner retries; no new HTTP client.
- L0 archive: payload + report; secret-strip only.
- `/opsx-scripts` → absolute local path; Cursor never hits prod API.
- Honest gaps → Future swagger sync signal, not invent URL.

**Non-Goals:**

- Web L2 sanitize / quarantine→transfer / CLEAN_DUMP Web contract /
  `READ_ONLY_PREFLIGHT_PASS` accept gate.
- Swagger sync / API Master / read-only token hardening.
- Finance / mutation write / PROCESSOR / RHP.
- New raw WB HTTP client; local Cursor→prod API.

## Architecture Decision References

- Proposed (this change):
  `openspec/changes/wb-readonly-api-preflight/decisions/scripts-wb-api-ops-stack/decision.md`
- Future gap SoT (not DoD):
  `openspec/changes/wb-api-swagger-inventory-ops/` (scaffold; activate on gap)

## Ownership & Placement

| Concern | Owner | Placement |
|--------|--------|-----------|
| Ops entrypoint + modes + archive L0 | scripts capability | `scripts/` (+ Job yaml under `k8s/jobs/` as needed) |
| Token/access by shop_id | existing Owner-bot | reuse `get_access_for_wb_cabinet` |
| WB HTTP + retries | existing product API | `app/core/mp/wb/api` + shop-runner patterns |
| Job run / copy archive | `/opsx-scripts` | plan → run → cp → report |
| Swagger status / API Master | Future increments | not this change |

Checklist:

- [x] context-first decision lookup
- [x] relevant decisions cited (proposed ADL)
- [x] new decision proposed if missing
- [x] implementation layer matches decision (scripts ops; no product rewrite)

## Decisions

1. **Modes:** `preflight` (probe) and `collect` (best-effort). Collect is in scope.
2. **Families (4):** ads / cards / analytics / norms — via existing managers only.
3. **Partial OK:** collect MAY exit with PARTIAL + gap report; MUST NOT claim full
   success when gaps remain.
4. **Retries:** reuse shop-runner WB API retry/rate-limit/timeout; finite ceiling
   for whole run (no hang).
5. **Archive L0:** zip/dir with payload + structured report (+ sha256);
   MUST strip secrets from outputs/logs; Web-grade body redaction — out.
6. **Runtime:** API only inside Owner-bot Job; Cursor = kubectl/plan/cp.
7. **Policy:** `READ_ONLY_NO_MUTATION` — no create/update/delete/finance writes;
   POST-for-read allowed.
8. **No Web PASS claim:** do not emit `READ_ONLY_PREFLIGHT_PASS` as Web gate.

## Risks / Trade-offs

| Risk | Mitigation |
|------|------------|
| Incomplete manager coverage | PARTIAL + gap; escalate to Future swagger sync |
| Secrets in archive | secret-strip MUST; never log Authorization |
| Confused with Web RETURN | label as Owner-local research dump |
| Retry storm / hang | production patterns + run ceiling |
| Shop hardcoded | Dilera only via Job arg |

## Migration Plan

1. Implement entrypoint + Job + registry row (not battle_tested yet).
2. `/opsx-scripts` prepare → RUN GO on Dilera arg.
3. Confirm local archive path + report honesty (PARTIAL if needed).
4. Rollback: stop using Job / delete Job artifact; revert registry line.

## Open Questions

- Exact manager method mapping per family — resolve at apply via existing
  `wb/api` surface (no invent URL).
- Run-ceiling defaults (time/calls) — pick conservative values at apply;
  document in report.

## Deferred (not owed)

See `DOTO/WORKLOG.md` section
`## Deferred from change wb-readonly-api-preflight (2026-08-04)` and evolution
Future Increments INC-RO-02..05.
