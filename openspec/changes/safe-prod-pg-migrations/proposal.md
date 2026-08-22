# Change: safe-prod-pg-migrations

## Why

Prod rollout of Expand schema must not rely on laptop `alembic upgrade`, startup migrate, or initContainers. Need Job-gated DDL with migrator role, baseline gates, and Expand–Contract discipline.

## What changes

- Migration Job wrapper + control-plane SQL (lease/fencing).
- CI migration gates.
- Runbook and security cutover SQL checklist.
- Provenance and dual-baseline requirements.

## Impact

- Ops / DevOps deploy path.
- PostgreSQL roles and `migration_control` schema.
- No product feature behavior except enabling safe schema rolls.
