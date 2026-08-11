# Fixtures: /opsx-new REPAIR MODE (owner-contract)

Process-only dry-run cases for `/opsx-new` when input contains a valid (or
intentionally invalid) `OWNER_REVIEW_HANDOFF` with
`MODE: REPAIR_EXISTING_OWNER_CONTRACT`.

These fixtures do **not** authorize live product writes during meta-fix.
They define expected command behavior for simulation / acceptance.

Shared handoff literal must match
`/opsx-owner-contract-review` READY_FOR_REPAIR output
(see `../owner-contract-review/10-ready-for-repair-handoff.md`).

## Index

| ID | File | Theme | Expected |
|----|------|-------|----------|
| 01 | `01-valid-repair.md` | T5 valid repair | only `owner-contract.md` changed; `OWNER_CONTRACT_REPAIR_RESULT` |
| 02 | `02-reject-unresolved-choice.md` | T6 A/B in repair | `PAUSE` / `UNRESOLVED_SEMANTIC_CHOICE`; no write |
| 03 | `03-invalid-write-boundary.md` | T7 boundary | `PAUSE` / `INVALID_REPAIR_BOUNDARY`; no extra writes |
| 04 | `04-do-not-change-preservation.md` | T8 | requested R-* applied; `DO_NOT_CHANGE` preserved |
| 05 | `05-idempotency.md` | T11 | re-run; no duplicate/broaden; already satisfied OK |
| 06 | `06-create-mode-unchanged.md` | T12 | no handoff → CREATE path unchanged |
| 07 | `07-handoff-from-reviewer-fixture-10.md` | T4↔T5 | reviewer Fixture 10 output accepted without rewrite |

## Out of scope

- continue / ff / apply / verify / Supervisor
- product code / product tests
