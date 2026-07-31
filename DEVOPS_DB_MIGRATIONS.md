# DEVOPS_DB_MIGRATIONS

Безопасные PostgreSQL-миграции для `prod-adv-bot` (план r06–r10).

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
- MVP: CONTROL image читает OCI layers из Harbor по digest **без** запуска RELEASE.
- Multi-arch: различать `RELEASE_INDEX_DIGEST` и `RELEASE_PLATFORM_MANIFEST_DIGEST` (`linux/amd64`).

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

- `k8s/jobs/app-db-migrate.yaml` — RELEASE migrate; `envFrom` ConfigMap `prod-wb-gram`
  + Secret `common-secrets` (settings import via `alembic_/env.py`), plus
  `DATABASE_URL` from `app-db-migrator`.
- `k8s/jobs/app-db-control.yaml` — CONTROL verify+acquire (не exec RELEASE).
- Helper: `scripts/Invoke-ProdDbMigrateThenRollout.ps1`
