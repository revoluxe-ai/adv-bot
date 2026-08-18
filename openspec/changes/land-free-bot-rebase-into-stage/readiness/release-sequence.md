# Deferred owner operational sequence: `land-free-bot-rebase-into-stage`

Этот файл описывает только handoff после merge. Он не является частью
merge-readiness DoD и выполняется Owner отдельным approved operational flow.
Каждый последующий переход привязан к одному `candidate_sha` и `release_id`;
receipt следующего состояния не заменяет receipt предыдущего.

1. `MERGE_READINESS_GO`: graph, safety, data-transition и local compatibility
   evidence.
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

The current change stops after `MERGE_READINESS_GO`. Image build, Harbor upload,
deployment restart, pod startup and stage/prod verification start only after
merge. The forward recovery owner is the migration rollout owner named by the
Owner's operational flow.
