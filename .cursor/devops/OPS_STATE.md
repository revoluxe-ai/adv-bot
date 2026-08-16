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
| Control secret | `app-db-control` (`database_url`) → principal `release_controller` |
| Migrator secret | `app-db-migrator` (`database_url`) → principal `app_migrator` |
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
| `alembic_version` (prod) | `e8f9a0b1c2d3` |
| Expand columns | shelf-exhausted pause SoT columns (INC-AUTO-SHELF-PAUSE-01) + prior `card_ab_hold_*` |
| APPLICATION baseline | `baseline-adv-updater-20260731-post-cutover-app` / `RECONCILED` |
| APPLICATION `source_history_hash` | `interim-forensics-20260731T093353Z` |
| CONTROL baseline | `baseline-adv-updater-20260731-control-plane` / `RECONCILED` |
| `PROD_AUTOMATION_ENABLEMENT_ALLOWED` | `NO` |

## Last known good release

| Field | Value |
|-------|--------|
| Image tag | `3ad2d7d66aea88d3e872dce59ed28385acd15e59` |
| Platform digest | `sha256:8ae72bdbdfaa801fe0c34ee3ade665237e1eb4f756760893cce53d294e783016` |
| GHCR | `ghcr.io/revoluxe-ai/adv-bot:3ad2d7d66aea88d3e872dce59ed28385acd15e59` |
| App Deployments on this image | yes (CAS 2026-08-14; `free-bot` replicas=0) |
| Last migrate Job | `app-db-migrate-3ad2d7d6-r2` → SUCCESS `f2a3…`→`e8f9…` |
| Last CONTROL | `app-db-control-3ad2d7d6-r2` → `IDEMPOTENT_HIT` fencing_token=1 |
| Last complete_release | `app-db-ctrlplane-3ad2d7d6-complete-r2` → lease released / COMPLETED |
| Prepared fallback (prior LKG) | tag `4f2a84a086947bbf80174d354be495e6ba14ddd3` / digest `sha256:40b39f4f866f25bb3d8a3a0bc533a6662c7fe3495cc4534aeda7e4e6bc52668d` |

## Open risks / follow-ups

* **Authz repair DONE (2026-08-14):** `release_controller` LOGIN exists; `app-db-control` → `release_controller` with EXECUTE on all 8 release-control functions; `app_migrator` has **no** release-control EXECUTE.
* Zalando status `UpdateFailed` after adding `release_controller` (operator sync unhappy). Role/grants/secret work; CR pins `patroni.pg_hba` `host all all all md5` because `ssl=off` + default `hostnossl reject` broke remote Jobs. Investigate UpdateFailed separately.
* **prod-wb-gram PG routing (2026-08-14):** `POSTGRES_MASTER_HOST`/`REPLICA_HOST` → `postgres-db.prod-adv-bot.svc.cluster.local` (pooler disabled in CR); `POSTGRES_SSL_MODE=disable` (PG `ssl=off`). Cluster-only CM — not in git.
* Orphan `postgres-db-pooler-external` LB (no pooler pods/endpoints) — cleanup optional.
* Automation still `NO` — staff `/opsx-devops` path only.
* Harbor direct push from CI fails on proxy project; rely on pull-through.
* Next Expand release must update APPLICATION `source_history_hash` (Owner) before acquire with real graph hash.
* Shop-runner operational noise (`NotFoundActiveAdvCompany`, keywords cache miss) is not schema regression.

## Action log (append-only summary)

| When (UTC) | Action | Result |
|------------|--------|--------|
| 2026-07-31 | Expand + security cutover + migrate NOOP (`4edd75b…`) | schema at `f2a3…` |
| 2026-08-01 | CONTROL dry-run + CAS all entrypoints → `fd6d2d…` | apps Running; no UndefinedColumn |
| 2026-08-02 | OPTION_A: `/opsx-devops` + OPS_STATE memory landed in repo | process ready |
| 2026-08-09 | CONTROL dry-run `0e7273ae` + CAS entrypoints (migrate/complete_release skipped) | apps Running on `0e7273ae…` @ `sha256:0c3ee410…` |
| 2026-08-10 | CONTROL dry-run `4f2a84a0` + CAS entrypoints (migrate/complete_release skipped; PR #430) | apps Running on `4f2a84a0…` @ `sha256:40b39f4f…` |
| 2026-08-14 | GO safe_prod_release `3ad2d7d6…` CONTROL_DRY_RUN=0 | CONTROL `ACQUIRED` (token=1); `mark_migration_started` InsufficientPrivilege; STOP — no Migrate/CAS |
| 2026-08-14 | Authz repair mission (inspect-only) | `release_controller` missing; FAIL CLOSED — remediation packet |
| 2026-08-14 | Authz repair APPLY (kubectl) | CR user + ROLE/GRANT/REVOKE + Secret rewire + pg_hba host-md5; verify PASS; no migrate/CAS |
| 2026-08-14 | GO resume safe_prod_release `3ad2d7d6…` CONTROL_DRY_RUN=0 | CONTROL IDEMPOTENT_HIT token=1 → mark_started → migrate SUCCESS → mark_succeeded → begin → CAS all entrypoints → complete_release OK; alembic `e8f9…`; LKG now `3ad2d7d6…` |
| 2026-08-14 | GO CONFIG_PATCH prod-wb-gram PG hosts + SSL | pooler host → postgres-db direct; SSL require → disable; all entrypoints rolled out; run-update-active-shop-ids Running |
