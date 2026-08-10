# OPS_STATE — durable DevOps memory (prod-adv-bot)

Source of truth for **what is already true** in ops. Procedure lives in
`DEVOPS_DB_MIGRATIONS.md`. Workflow/gates: `/opsx-devops`.

Update this file (and `LAST.json`) after every successful `/opsx-devops GO`
that changes release posture. Never store secrets, DSN, passwords, or tokens.

## Infra snapshot

| Field | Value |
|-------|--------|
| Primary app namespace | `prod-adv-bot` |
| Postgres | Zalando `postgres-db` (PG 17), DB `adv_updater` |
| Database identity (CONTROL) | `prod-adv-bot/postgres-db/adv_updater` |
| Registry (cluster pull) | `harbor.skyline360.ru/git-registry-cache/revoluxe-ai/adv-bot` |
| Harbor note | `git-registry-cache` is **proxy** — CI push to Harbor may fail; pull-through from GHCR works |
| Migrator secret | `app-db-migrator` (`database_url`) |
| Control secret | `app-db-control` (`database_url`) |
| Pull secret | `harbor-skyline360-login-secret` |
| Job templates | `k8s/jobs/app-db-control.yaml`, `k8s/jobs/app-db-migrate.yaml` |

### Adv-bot entrypoint Deployments (CAS targets)

| Deployment | Notes |
|------------|--------|
| `wb-sky-bot` | Telegram bot |
| `adv-bot-updater` | updater |
| `adv-bot-asq-worker` | ASQ worker |
| `run-shop-update-worker` | shop runner |
| `run-update-active-shop-ids` | active shops |
| `trunc-system-log-clickhouse` | log trunc |
| `free-bot` | often `replicas=0` — still CAS image when present |

Skip non-app: `postgres-db*`, `xray*`, `bebra-shared-proxy`, pooler.

## Schema / CONTROL baselines

| Field | Value |
|-------|--------|
| `alembic_version` (prod) | `f2a3b4c5d6e7` |
| Expand columns | `card_ab_hold_*` present (incl. `emergency_latch`) |
| APPLICATION baseline | `baseline-adv-updater-20260731-post-cutover-app` / `RECONCILED` |
| APPLICATION `source_history_hash` | `interim-forensics-20260731T093353Z` |
| CONTROL baseline | `baseline-adv-updater-20260731-control-plane` / `RECONCILED` |
| `PROD_AUTOMATION_ENABLEMENT_ALLOWED` | `NO` |

## Last known good release

| Field | Value |
|-------|--------|
| Image tag | `4f2a84a086947bbf80174d354be495e6ba14ddd3` |
| Platform digest | `sha256:40b39f4f866f25bb3d8a3a0bc533a6662c7fe3495cc4534aeda7e4e6bc52668d` |
| GHCR | `ghcr.io/revoluxe-ai/adv-bot:4f2a84a086947bbf80174d354be495e6ba14ddd3` |
| App Deployments on this image | yes (CAS 2026-08-10; `free-bot` replicas=0) |
| Last migrate Job | skipped this GO (`CONTROL_DRY_RUN=1`, head already `f2a3…`; no alembic files in PR #430) |
| Last CONTROL | dry-run Job `app-db-control-4f2a84a0-dry` → `DRY_RUN_OK` (no lease) |
| Prepared fallback (prior LKG) | tag `0e7273aec3bd41470f0fe664fa492f5eef10df99` / digest `sha256:0c3ee41057f198ec7e6847847bfc20aea74c442312bc2cc5228c60a7b32c29e1` |

## Open risks / follow-ups

* Automation still `NO` — staff `/opsx-devops` path only.
* Harbor direct push from CI fails on proxy project; rely on pull-through.
* Next Expand release must update APPLICATION `source_history_hash` (Owner) before acquire with real graph hash.
* Shop-runner operational noise (`NotFoundActiveAdvCompany`, keywords cache miss) is not schema regression.
* Watch empty-keywords Search pause path in prod after PR #430 image (two-tick + warmup gate); rollback CAS to fallback if needed.

## Action log (append-only summary)

| When (UTC) | Action | Result |
|------------|--------|--------|
| 2026-07-31 | Expand + security cutover + migrate NOOP (`4edd75b…`) | schema at `f2a3…` |
| 2026-08-01 | CONTROL dry-run + CAS all entrypoints → `fd6d2d…` | apps Running; no UndefinedColumn |
| 2026-08-02 | OPTION_A: `/opsx-devops` + OPS_STATE memory landed in repo | process ready |
| 2026-08-09 | CONTROL dry-run `0e7273ae` + CAS entrypoints (migrate/complete_release skipped) | apps Running on `0e7273ae…` @ `sha256:0c3ee410…` |
| 2026-08-10 | CONTROL dry-run `4f2a84a0` + CAS entrypoints (migrate/complete_release skipped; PR #430) | apps Running on `4f2a84a0…` @ `sha256:40b39f4f…` |
