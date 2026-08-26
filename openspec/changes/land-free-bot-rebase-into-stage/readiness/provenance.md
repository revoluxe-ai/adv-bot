# Provenance record: d1e2f3a4b5c6

Дата сбора evidence: 2026-08-17  
Change: `land-free-bot-rebase-into-stage`

## Matrix

- `REMOTE_BRANCH_REACHABLE`: `yes`
- `MERGED_TO_RELEASE_BRANCH`: `no`
- `DEPLOYMENT_REFERENCED`: `no`
- `DATABASE_APPLIED`: `unproven`
- `PUBLICATION_CLASSIFICATION`: `published_remotely_not_released`
- `EVIDENCE_GAP`: отсутствует migration Job receipt, `alembic_version` dump или
  release record, доказывающий применение в stage/production.

Источник: Owner-provided read-only provenance report. Report identified the
revision on `origin/implement-free-bot-rebase` and open PR #437, while
`origin/stage` and `origin/master` did not contain it.

## Route decision

`ROUTE: rewrite-before-landing`

Rationale: application is unproven, the revision is not in the release/base
history, and the Owner explicitly accepted a schema-only Alembic step plus an
approved migration Job for the classifier-owned backfill. The published/applied
history rule remains protected: if later evidence proves database application,
this route is invalid and a new forward repair is required.

## Snapshot warning

This record is historical provenance evidence. The final readiness package MUST
rebind all gates to the final candidate SHA after the migration rewrite and
must repeat verification if that SHA or the in-scope set changes.
