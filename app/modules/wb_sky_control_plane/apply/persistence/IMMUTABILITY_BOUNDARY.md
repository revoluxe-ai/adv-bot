# Apply evidence immutability (Slice B)

`PostgresApplyEvidenceStore` exposes **insert** and **get_by_id** only. Execution
facts on `wbskyapplyevidence` are not updated through Apply Authority repository
APIs.

Privileged raw SQL `UPDATE`/`DELETE` on the table is outside this contract and
is not claimed as database-level cryptographic immutability (no triggers in V1).

Slice C orchestration MUST finalize evidence via insert-once semantics inside the
same PostgreSQL transaction as settings mutation.
