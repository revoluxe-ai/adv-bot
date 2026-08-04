# DEVOPS_DB_MIGRATIONS

Безопасные PostgreSQL-миграции для `prod-adv-bot` (план r06–r10).

## Command contract (`/opsx-devops`)

Workflow/gates: Cursor command `/opsx-devops`  
Durable memory (infra + past actions): `.cursor/devops/OPS_STATE.md` + `LAST.json`  
Domain facts: `.cursor/rules/devops.mdc`

| Mode | What happens |
|------|----------------|
| `PLAN_WRITE intent=safe_prod_release\|migrate_rollout\|image_cas` | Read OPS_STATE + this runbook; emit ordered CONTROL→Migrate→CAS plan (skip steps already done per memory) |
| `GO …` (same intent) | Allowlisted Job apply + CAS `test`+`replace` only; then refresh OPS_STATE |
| Other `/opsx-devops` intents | Unchanged (restart/scale/manifest); still no laptop alembic |

Examples:

```text
/opsx-devops PLAN_WRITE intent=safe_prod_release ns=prod-adv-bot image=harbor…/adv-bot:<sha> digest=sha256:…
/opsx-devops GO intent=safe_prod_release ns=prod-adv-bot image=harbor…/adv-bot:<sha> digest=sha256:…
```

`.tmp/opsx-devops/` = optional ephemeral receipt, **not** source of truth.

## Жёсткие правила

- Не `alembic upgrade` с ноутбука на prod.
- Не migrate в startup / initContainer.
- Не exec RELEASE image как provenance extractor.
- `PROD_AUTOMATION_ENABLEMENT` только после APPLICATION + CONTROL baselines.
- Expand–Contract; первый schema release после baseline — Expand-only.
- Ошибка после старта upgrade → `PARTIAL_OR_UNKNOWN` (не blind retry).

## Порядок релиза

1. Forensics / baseline gates (`SOURCE_HISTORY_HASH`, `TARGET_BUNDLE_HASH`, digest provenance).
2. CONTROL_IMAGE: `verify_baseline_and_acquire_release` → termination-log JSON.
3. RELEASE_IMAGE Migrate Job: `python -m app.db.migrate`.
4. Deployment CAS: JSON Patch `test`+`replace` image (не голый `set image`).
5. `complete_release` освобождает singleton lease.

## Provenance

- Предпочтительно: signed attestation на OCI digest.
- MVP (`app.db.provenance` + `python -m app.db.control_acquire`):
  - `PROVENANCE_MODE=digest_pin` — равенство pin digest (без registry fetch);
  - `PROVENANCE_MODE=registry_manifest` — GET OCI index/manifest из Harbor
    по digest, resolve `linux/amd64`, **без** `docker run` / exec RELEASE.
- Multi-arch: различать `RELEASE_INDEX_DIGEST` и `RELEASE_PLATFORM_MANIFEST_DIGEST`.
- `EXPECTED_SOURCE_HISTORY_HASH` должен совпасть с RECONCILED APPLICATION
  baseline (`migration_control.baseline_registry`). Interim prod pin:
  `interim-forensics-20260731T093353Z` (не invent; Owner обновляет baseline).

## Automation gate

```
PROD_AUTOMATION_ENABLEMENT_ALLOWED=NO
```

Пока NO: protected deploy workflow / CAS rollout **не** включать.
CONTROL+Migrate Jobs — staff/dry-run path. Flip to YES только после
реального CONTROL provenance в CI gate + GRANT EXECUTE + secret wiring.

## APPLICATION_SECURITY_CUTOVER

См. `k8s/migrations/sql/002_application_security_cutover.sql` и Zalando CR
`k8s/postgres-db-basic.yaml` (`advupdater: []`, `databases.adv_updater: app_owner`).

Постоянный regime:

- `app_owner` владеет app objects / DB;
- `advupdater` DML-only, **без** SUPERUSER/CREATEDB/CREATE на `public`;
- `app_migrator` LOGIN NOINHERIT + `SET ROLE app_owner` (Job env `SET_ROLE_APP_OWNER=1`);
- Secret `app-db-migrator` (DSN на primary, не pooler).

**Zalando residual:** operator держит `app_owner` как LOGIN (secret существует).
Runtime Deployments **не** монтируют этот secret — operational NOLOGIN.
Не возвращать `superuser`/`createdb` в CR для `advupdater`.

## Replay

- `REPLAY_ENVIRONMENT_MANIFEST` (PG version, extensions, locales, …).
- `STRUCTURAL_REPLAY` и `STATEFUL_REPLAY` (со snapshot provenance).
- NetworkPolicy default-deny egress: `k8s/network/migration-replay-netpol.yaml`.

## Rollback приложения

Откат image на совместимую версию; схему не downgrade; forward-fix.  
PITR только при порче данных.

## Jobs

Порядок: **CONTROL → Migrate → Deployment CAS** (не наоборот).

- `k8s/jobs/app-db-control.yaml` — CONTROL verify+acquire; Secret `app-db-control`.
  `CONTROL_DRY_RUN=1` — provenance + baseline SELECT, без lease.
- `k8s/jobs/app-db-migrate.yaml` — RELEASE migrate; `envFrom` ConfigMap `prod-wb-gram`
  + Secret `common-secrets` (settings import via `alembic_/env.py`), plus
  `DATABASE_URL` from `app-db-migrator`.
- Helper: `scripts/Invoke-ProdDbMigrateThenRollout.ps1` (migrate+CAS note only;
  CONTROL must already have succeeded).
