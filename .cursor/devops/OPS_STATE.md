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
| `alembic_version` (prod) | `d7e3c9f1a204` |
| Expand columns | shelf-exhausted pause SoT + `card_ab_hold_*` + `advsetting.auto_update_minus_phrases` (**NOT NULL**; backfill DONE 2026-08-28) + `raise_plan_on_promobonuses` + promo allocation/spend journals |
| APPLICATION baseline | `baseline-adv-updater-20260731-post-cutover-app` / `RECONCILED` |
| APPLICATION `source_history_hash` | `interim-forensics-20260731T093353Z` |
| CONTROL baseline | `baseline-adv-updater-20260731-control-plane` / `RECONCILED` |
| `PROD_AUTOMATION_ENABLEMENT_ALLOWED` | `NO` |

## Last known good release

| Field | Value |
|-------|--------|
| Image tag | `4d5fae43576d290ca8324424b29772ce0eb1a5f5` |
| Platform digest | `sha256:51a966e5434421b7c858169cdb44521afe1bf485e82d24ead7ec55e3d317da28` (digest_pin) |
| GHCR | `ghcr.io/revoluxe-ai/adv-bot:4d5fae43576d290ca8324424b29772ce0eb1a5f5` |
| App Deployments on this image | **all entrypoints on `4d5fae43…`**; `free-bot` replicas=0 |
| Last CONTROL | `app-db-control-4d5fae43-r1` → `ACQUIRED` (fencing_token=10; CONTROL_DRY_RUN=0) |
| Last migrate Job | `app-db-migrate-4d5fae43-r1` → `SUCCESS_NOOP` (`d7e3c9f1a204` @ target) |
| Last complete_release | `app-db-ctrlplane-4d5fae43-r1-complete` → OK lease released |
| Prepared fallback (prior LKG) | tag `01e29e36fa539e8bdf4307516af922e176c8a0d6` / digest `sha256:f33349f2c163727b356ae3039ef5f2c73dfa08cde67758260cd5f77b1335b207` |

## Rollback reserve (Owner policy)

If a **forward** image rollout fails (failed rollout / CrashLoop on a target Deployment, e.g.
`adv-bot-asq-worker` after PR #443):

* **Reserve target:** CAS revert to **prod LKG** or **Prepared fallback** (table above) — master-line
  tags recorded in this file. **Do not** revert to stage-tip or bare `kubectl set image`.
* **Procedure:** `INVESTIGATE` → `PLAN_WRITE intent=image_cas` (JSON Patch `test`+`replace`,
  namespace `prod-adv-bot`) → Owner `GO`. Partial CAS (one Deployment) is OK (see action log).
* **Schema:** at current posture `d7e3c9f1a204` — image-only rollback unless forward-fix (`LAST.json`).
* **After successful GO:** refresh this file + `LAST.json` (`/opsx-meta-commit`).

## Open risks / follow-ups

* **Authz repair DONE (2026-08-14):** `release_controller` LOGIN exists; `app-db-control` → `release_controller` with EXECUTE on all 8 release-control functions; `app_migrator` has **no** release-control EXECUTE.
* **Authz baseline SELECT DONE (2026-08-16):** Job `app-db-authz-grant-baseline-select-0816` → `release_controller` has `USAGE` on schema `migration_control` + `SELECT` on `migration_control.baseline_registry` (needed for CONTROL_DRY_RUN=1).
* Zalando status `UpdateFailed` after adding `release_controller` (operator sync unhappy). Role/grants/secret work; CR pins `patroni.pg_hba` `host all all all md5` because `ssl=off` + default `hostnossl reject` broke remote Jobs. Investigate UpdateFailed separately.
* **prod-wb-gram PG routing (2026-08-14):** `POSTGRES_MASTER_HOST`/`REPLICA_HOST` → `postgres-db.prod-adv-bot.svc.cluster.local` (pooler disabled in CR); `POSTGRES_SSL_MODE=disable` (PG `ssl=off`). Cluster-only CM — not in git.
* Orphan `postgres-db-pooler-external` LB (no pooler pods/endpoints) — cleanup optional.
* Automation still `NO` — staff `/opsx-devops` path only.
* Harbor direct push from CI fails on proxy project; rely on pull-through.
* Next Expand release must update APPLICATION `source_history_hash` (Owner) before acquire with real graph hash.
* Shop-runner operational noise (`NotFoundActiveAdvCompany`, keywords cache miss) is not schema regression.
* **2026-08-22 v3 predeploy:** Q1 gate applied (`bot_active=FALSE` for 5 legacy rows). Orphan-cabinet admin `NoResultFound` — tech debt in `DOTO/WORKLOG.md` (not deploy blocker).
* **2026-08-22 v3-only release DONE:** PR #438 → `be173f55…` phased CAS all entrypoints; migrate skip; shop-runner `replicas=1` (was already 1 pre-rollout).
* **2026-08-28 land-free-bot release DONE:** PR #441 → `39e77cdd…`; CONTROL acquire token=2; migrate Expand `auto_update_minus_phrases` + merges → `0b0fe…`; phased CAS canary→shop-runner-last; complete_release OK. Minus-phrases backfill Job still deferred.
* **2026-08-28 shop-runner rollback:** CAS `run-shop-update-worker` only → `be173f55…` (Owner: minus-phrases backfill not run; leave UI/`wb-sky-bot` on `39e77…`). Schema stays `0b0fe…` (nullable column; no downgrade).
* **2026-08-28 UI rollback:** CAS `wb-sky-bot` + `free-bot` → `be173f55…` (Owner bug on land-free-bot UI). Schema stays `0b0fe…`; minus backfill still deferred; updater/asq/active-shops remain on `39e77…`.
* **2026-08-28 SAFE_PROD_RELEASE 2077dd PARTIAL then RECOVERED:** CONTROL token=3; migrate Failed (SET ROLE skip on NOOP backfill). Recovery GO: `app-db-backfill-minus-2077dd751-r1` with `SET ROLE app_owner` → updated 69823 / enabled 13; mark_succeeded → begin → phased CAS all → `2077dd…` → complete_release OK. Product debt: `migrate.py` must `_maybe_set_role` before backfill when `current == target`.
* Post-release watch: shop-runner `NotFoundActiveAdvCompany` remains known noise; monitor FREE/PAID overlays, owner-check UI, v3 cycles, updater restarts, minus auto-update for 13 bot_active rows.

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
| 2026-08-16 | CONTROL_DRY_RUN=1 `bb81f827-r1` | PRECONDITION_FAILED: permission denied baseline_registry; no CAS |
| 2026-08-16 | GO authz_baseline_select | Job `app-db-authz-grant-baseline-select-0816` OK; SELECT+USAGE for release_controller; no CAS |
| 2026-08-16 | GO safe_prod_release `bb81f827…` CONTROL_DRY_RUN=1 | CONTROL DRY_RUN_OK → migrate skip (e8f9) → CAS all entrypoints → LKG `bb81f827…` |
| 2026-08-22 | Pre-v3-cutover gate: `advsetting.bot_active=FALSE` where `bot_active=TRUE AND automatic_version!=3` | UPDATE 5 rows (ids 1151716277–1151716280, 201852); Q1 verify 0 rows |
| 2026-08-22 | PR #438 merge → stage CI `be173f55…`; CONTROL DRY_RUN_OK; canary CAS `run-update-active-shop-ids` | pod Running on `be173f55…`; migrate skip; остальные на `bb81f827…` |
| 2026-08-22 | Phased CAS waves 2–7 all entrypoints → `be173f55…` | all Running 0 restarts; v3 shop-runner cycles OK; wb-sky-bot polling; LKG `be173f55…` |
| 2026-08-28 | GO safe_prod_release `39e77cdd…` CONTROL_DRY_RUN=0 phased shop_runner_last | CONTROL ACQUIRED token=2 → migrate SUCCESS `0b0fe…` → begin → CAS W1–W6 → complete_release OK; LKG `39e77cdd…` |
| 2026-08-28 | CAS rollback `run-shop-update-worker` only → `be173f55…` | UI/`wb-sky-bot` stays `39e77…`; schema `0b0fe…`; minus backfill still deferred |
| 2026-08-28 | CAS rollback `wb-sky-bot` + `free-bot` → `be173f55…` | UI + shop-runner on `be173f55…`; schema `0b0fe…`; minus backfill still deferred |
| 2026-08-28 | GO safe_prod_release `2077dd751…` CONTROL_DRY_RUN=0 + backfill | CONTROL ACQUIRED token=3; mark_started OK; migrate Failed (SET ROLE skip on NOOP backfill); **PARTIAL — lease held; no CAS** |
| 2026-08-28 | GO recovery SET_ROLE_BACKFILL + CAS `2077dd…` | backfill OK 69823/13; mark_succeeded→begin→CAS W1–W6→complete; lease released; LKG `2077dd…` |
| 2026-09-05 | GO safe_prod_release `dd061bf0…` CONTROL_DRY_RUN=0 | CONTROL ACQUIRED token=4 → mark_started → migrate SUCCESS_NOOP `0b0fe…` → mark_noop → begin → CAS all entrypoints → complete_release OK; LKG `dd061bf0…` (WB token rotation) |
| 2026-09-09 | GO safe_prod_release `70106ad38…` CONTROL_DRY_RUN=0 | CONTROL ACQUIRED token=5 → mark_started → migrate SUCCESS `c4f8a1…` → mark_succeeded → begin → phased CAS W1–W5 → complete_release OK; LKG `70106ad38…` (token add relax + promobonus) |
| 2026-09-10 | GO safe_prod_release `82c3d36b2…` CONTROL_DRY_RUN=0 | CONTROL ACQUIRED token=6 → mark_started → migrate SUCCESS_NOOP `c4f8a1…` → mark_noop → begin → phased CAS W1–W5 → complete_release OK; LKG `82c3d36b2…` (fix raise CPO on promo) |
| 2026-09-24 | GO safe_prod_release `01e29e36…` CONTROL_DRY_RUN=0 phased shop_runner_last | CONTROL ACQUIRED token=9 → mark_started → migrate SUCCESS `d7e3c9…` → mark_succeeded → begin → phased CAS W1–W7 → complete_release OK; LKG `01e29e36…` (absolute total budget limits) |
| 2026-09-25 | GO safe_prod_release `4d5fae43…` CONTROL_DRY_RUN=0 phased shop_runner_last | CONTROL ACQUIRED token=10 → mark_started → migrate SUCCESS_NOOP `d7e3c9…` → mark_noop → begin → phased CAS W1–W7 → complete_release OK; LKG `4d5fae43…` (stage @ 4d5fae43) |
