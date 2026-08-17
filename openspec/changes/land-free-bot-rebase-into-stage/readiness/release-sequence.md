# Release sequence: `land-free-bot-rebase-into-stage`

Каждый переход привязан к одному `candidate_sha` и `release_id`; receipt
следующего состояния не заменяет receipt предыдущего.

1. `READINESS_GO`: graph, safety, data-transition и compatibility evidence.
2. `STAGE_DEPLOYED`: schema step, approved backfill Job, UI rollout, smoke и
   paid/free compatibility receipts.
3. `DATABASE_APPLIED`: отдельный receipt approved migration Job application.
4. `PRODUCTION_ROLLED_OUT`: deployment CAS receipt и UI deployment receipt.
5. `PRODUCTION_VERIFIED`: monitoring-window smoke, paid/free compatibility
   baseline comparison и recovery evidence.

## Required receipt fields

`release_id`, `candidate_sha`, `phase`, `started_at`, `completed_at`,
`outcome`, `migration_target`, `backfill_kind`, `affected_record_preview`,
`compatibility_baseline_ref`, `recovery_action_ref`.

Production rollout remains `NO_GO` until the approved write-path provides the
migration receipt and the deployment path provides the deployment/UI receipts.
The forward recovery owner is the migration rollout owner named by the release
operator; a missing named owner is an actionable final-gate gap.
