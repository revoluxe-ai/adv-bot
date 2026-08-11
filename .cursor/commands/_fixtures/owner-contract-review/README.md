# Fixtures: /opsx-owner-contract-review

Process-only regression cases for independent Owner Contract semantic review.

Command under test: `/opsx-owner-contract-review`

## How to use

Dry-run: given the fixture’s durable inputs, a correct reviewer MUST emit the
`Expected` check outcomes (and overall `VERDICT` where stated).

These fixtures do **not** authorize writes. They do **not** hard-gate
`continue` / `ff`.

## Index

| ID | File | Primary check | Expected |
|----|------|---------------|----------|
| 01 | `01-wrong-technical-reinterpretation.md` | INTENT_PRESERVATION | FAIL; VERDICT FAIL |
| 02 | `02-agent-proposal-promoted.md` | OWNER_DECISION_PROVENANCE | FAIL or NEEDS_OWNER |
| 03 | `03-ambiguous-terminology.md` | TERMINOLOGY | FAIL or NEEDS_OWNER |
| 04 | `04-contradictory-start-semantics.md` | INTERNAL_CONSISTENCY | FAIL |
| 05 | `05-stale-correction.md` | STALE_ASSUMPTIONS | FAIL |
| 06 | `06-clean-auto-shelf-exhausted-pause-retest.md` | all | PASS only with durable provenance |

## Static matrix

| Check | Fixture coverage |
|-------|------------------|
| INTENT_PRESERVATION | 01, 06 |
| OWNER_DECISION_PROVENANCE | 02, 06 |
| INTERNAL_CONSISTENCY | 04, 06 |
| TERMINOLOGY | 03, 06 |
| SCOPE_INTEGRITY | 01, 06 |
| ACCEPTANCE_COHERENCE | 04, 06 |
| STALE_ASSUMPTIONS | 05 |
| CONTRACT_VS_REALITY | optional / NOT_CHECKED unless stated |
| MODE READ_ONLY | all (command contract) |
| continue/ff/apply/verify/Supervisor untouched by this command’s writes | n/a (out of fixture scope; meta-design invariant) |
