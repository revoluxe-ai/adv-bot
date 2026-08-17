## ADDED Requirements

### Requirement: Forward-only convergence of parallel Alembic heads
The migration graph SHALL converge the existing terminal revisions
`d1e2f3a4b5c6` and `f2a3b4c5d6e7` through exactly one new forward-only merge
revision. The convergence SHALL preserve every existing revision and SHALL NOT
perform schema or data changes.

#### Scenario: Parallel heads are merged without rewriting history
- **GIVEN** `d1e2f3a4b5c6` and `f2a3b4c5d6e7` are terminal revisions in the migration graph
- **WHEN** the convergence change is applied
- **THEN** exactly one new merge revision joins both terminal revisions and no existing revision is modified, deleted, or rewritten
- **THEN** the new merge revision performs no schema or data operation

### Requirement: Explicit single-head contract
The migration-head contract SHALL name the new merge revision as its only
expected final head. The contract SHALL reject a graph that retains either
parallel terminal revision as an additional head.

#### Scenario: Converged graph satisfies the single-head contract
- **GIVEN** the forward-only merge revision joins both former terminal revisions
- **WHEN** the migration-head contract is evaluated
- **THEN** the contract expects exactly one final head, namely the new merge revision
- **THEN** the contract does not retain either former terminal revision as a separately expected head

### Requirement: Focused convergence regression replay
Validation of this change SHALL replay only the designated
`test_exactly_one_alembic_head` regression node. The replay SHALL establish
that the converged graph has exactly one final head without expanding to
unrelated test or product surfaces.

#### Scenario: Single-head regression is replayed in isolation
- **GIVEN** the new merge revision and explicit expected-head contract are present
- **WHEN** regression validation is run for this change
- **THEN** only the `test_exactly_one_alembic_head` node is replayed
- **THEN** the replay passes only when the migration graph has exactly one final head
