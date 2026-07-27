# OPSX not-admin pipeline graph

## Meta
- scope: ALL_NON_ADMIN_OPSX
- role: shared_materialization
- authority: navigation_snapshot_only
- recommendation_strength: advisory
- operator_may_deviate: true
- not_authority_for: verify_go_nogo, archive, commit, command_contracts, forced_path
- inventory_count: 25
- fingerprint_strength: names_only
- excluded_by_owner: opsx-propose.md (obsolescent; do not recommend)
- evidence_note: |
  UPDATE GO 2026-07-27T05:00Z: three learning branches recorded (soft);
  process lesson path → admin promote-process-lesson → design-command;
  learn-from-bug = product/logic only. Inventory 25 names_only
  fingerprint f013cfe340ab4996. F6 kept. F3/F5 still open. Bodies still
  partially NOT_OPENED_BUDGET.

## States

### Core change lifecycle
- change_idea: need named change / description
- change_scaffolded: change dir exists; first artifact pending (`/opsx-new`)
- artifacts_in_progress: `/opsx-continue` filling artifacts
- apply_ready: applyRequires done (`/opsx-ff` or continue complete)
- implementing: `/opsx-apply` in progress
- impl_done: tasks complete; need verify
- verify_pass: archive-eligible after `/opsx-verify`
- verify_fail: back to apply/update
- archived: `/opsx-archive` done
- planning_revise: `/opsx-update` / `/opsx-explore`

### Bug / case map
- bug_signal_raw: product/behavioral Bugbot/CI/user signal (not process-contract)
- intake_recorded: durable intake on disk
- finding_queued: findings available in case map
- finding_claimed: ownership via `/opsx-claim-next-bug`
- adjudicating: `/opsx-fix-bug` without GO / `/opsx-classify-bug`
- fix_now_ready: fix-bug verdict `fix_now`; awaiting GO
- fixed_or_closed: adjudication complete
- learning_candidate: `/opsx-learn-from-bug` phase-1 (**product/logic only**)
- invariant_defined: invariant packet ready for hunt/fix
- command_defect_signal: off-graph — Bugbot/review on process contracts
  (`.cursor/commands/**`, rules/skills/static-check, mirrors); not a not-admin edge
- process_lesson_candidate: off-graph — after process FIXED / process Bugbot;
  `/opsx-admin-command-promote-process-lesson` (not `/opsx-learn-from-bug`)

### Typing / quality / ship
- typing_packet: pyright/mypy → `/opsx-fix-types`
- tests_authored: `/opsx-test`
- static_check_done: `/opsx-static-check` synthesized
- product_dirty: need `/opsx-commit`
- pr_ready: `/opsx-create-pr` / `/opsx-split-for-pr`

## Commands

### /opsx-explore
- purpose: think through ideas before scaffolding a change
- input_state: change_idea
- output_state: change_idea | planning_revise
- artifacts_read: none required
- artifacts_written: none
- decision_owner: operator
- next_typical: /opsx-new | /opsx-ff
- known_flaws: NOT_OPENED_BUDGET detail

### /opsx-new
- purpose: scaffold a new OpenSpec change; stop before creating artifacts
- input_state: change_idea
- output_state: change_scaffolded
- artifacts_read: openspec status/instructions
- artifacts_written: change scaffold only
- decision_owner: operator
- next_typical: /opsx-continue
- known_flaws: none recorded

### /opsx-continue
- purpose: create next planning artifact for an existing change
- input_state: change_scaffolded | artifacts_in_progress
- output_state: artifacts_in_progress | apply_ready
- artifacts_read: change artifacts / openspec status
- artifacts_written: next ready artifact
- decision_owner: operator
- next_typical: /opsx-continue | /opsx-apply
- known_flaws: none recorded

### /opsx-ff
- purpose: fast-forward all applyRequires artifacts
- input_state: change_idea | change_scaffolded
- output_state: apply_ready
- artifacts_read: openspec status/instructions
- artifacts_written: all applyRequires artifacts
- decision_owner: operator
- next_typical: /opsx-apply
- known_flaws: none recorded

### /opsx-update
- purpose: revise existing planning artifacts coherently
- input_state: planning_revise | apply_ready | verify_fail
- output_state: apply_ready | planning_revise
- artifacts_read: change planning artifacts
- artifacts_written: revised planning artifacts
- decision_owner: operator
- next_typical: /opsx-continue | /opsx-apply
- known_flaws: NOT_OPENED_BUDGET detail

### /opsx-apply
- purpose: implement tasks from an OpenSpec change
- input_state: apply_ready | implementing | verify_fail
- output_state: implementing | impl_done
- artifacts_read: tasks.md, design, decisions (context-first)
- artifacts_written: production/code per tasks
- decision_owner: implementer + architecture decisions
- next_typical: /opsx-verify
- known_flaws: none recorded (ADL budget-exhaust→NO_GO closed 2026-07-27)

### /opsx-verify
- purpose: read-only audit before archive
- input_state: impl_done
- output_state: verify_pass | verify_fail
- artifacts_read: change artifacts, code, VERIFY_POLICY
- artifacts_written: none (read-only)
- decision_owner: verifier
- next_typical: /opsx-archive | /opsx-apply | /opsx-update
- known_flaws: none recorded

### /opsx-archive
- purpose: archive a completed change
- input_state: verify_pass
- output_state: archived
- artifacts_read: change + decisions to promote
- artifacts_written: archive move; promoted decisions
- decision_owner: archiver
- next_typical: none | /opsx-commit | /opsx-create-pr
- known_flaws: NOT_OPENED_BUDGET detail

### /opsx-sync
- purpose: sync delta specs to main specs
- input_state: apply_ready | impl_done | verify_pass
- output_state: planning_revise | apply_ready
- artifacts_read: change delta specs
- artifacts_written: main specs
- decision_owner: operator
- next_typical: /opsx-verify | /opsx-apply
- known_flaws: NOT_OPENED_BUDGET detail

### /opsx-materialize-bug-queue
- purpose: durable bug-case map (intake/update/hunt-result/promote)
- input_state: bug_signal_raw | finding_queued
- output_state: intake_recorded | finding_queued
- artifacts_read: .tmp/opsx-bug-cases/**
- artifacts_written: .tmp/opsx-bug-cases/**
- decision_owner: materialize contract
- next_typical: /opsx-fix-bug case= intake= | /opsx-claim-next-bug
- known_flaws: none recorded

### /opsx-claim-next-bug
- purpose: claim one available chat-required finding
- input_state: finding_queued
- output_state: finding_claimed
- artifacts_read: CASE/LEDGER/finding packet
- artifacts_written: claim fields in case map
- decision_owner: claimer chat_label
-   next_typical: /opsx-fix-bug WITHOUT GO (+ claim_token)
- known_flaws: F2 addressed in contract (keep historical id)

### /opsx-fix-bug
- purpose: adjudicate (and with GO+fix_now fix) a **product/behavioral** bug signal
- input_state: bug_signal_raw | intake_recorded | finding_claimed | adjudicating | fix_now_ready
- output_state: adjudicating | fix_now_ready | fixed_or_closed | learning_candidate | invariant_defined
- artifacts_read: intakes/findings; code forensics
- artifacts_written: .tmp/opsx-bug-cases/** without GO; production only with GO+fix_now
- decision_owner: adjudicator + claim gate
- next_typical: /opsx-fix-bug GO | /opsx-invariant | /opsx-learn-from-bug | /opsx-commit | none
- known_flaws: |
  does not own process-contract defects (F6); if signal targets
  `.cursor/commands/**` → exit to `/opsx-admin-command-fix-command-defects`

### /opsx-classify-bug
- purpose: classify finding vs OpenSpec (read-only)
- input_state: finding_claimed | adjudicating | bug_signal_raw
- output_state: adjudicating | planning_revise
- artifacts_read: finding packet / OpenSpec
- artifacts_written: none
- decision_owner: classifier
- next_typical: /opsx-fix-bug WITHOUT GO + durable IDs | /opsx-update
- known_flaws: F1 addressed in contract (forbids GO on handoff)

### /opsx-invariant
- purpose: named behavioral invariant + hunt/fix handoff packets
- input_state: adjudicating | invariant_defined
- output_state: invariant_defined
- artifacts_read: case/finding / code
- artifacts_written: invariant packets (per contract)
- decision_owner: invariant author
- next_typical: /opsx-bug-hunt | /opsx-fix-bug WITHOUT GO
- known_flaws: NOT_OPENED_BUDGET detail

### /opsx-bug-hunt
- purpose: root-aware invariant-focused hunt
- input_state: invariant_defined | implementing
- output_state: finding_queued
- artifacts_read: root packet / code
- artifacts_written: hunt findings (process) ; minimal fixes only with GO+confirmed
- decision_owner: hunter
- next_typical: /opsx-materialize-bug-queue | /opsx-fix-bug WITHOUT GO
- known_flaws: NOT_OPENED_BUDGET detail

### /opsx-fanout-bug-hunt
- purpose: fan-out hunt registry for parallel adjudication
- input_state: invariant_defined | finding_queued
- output_state: finding_queued
- artifacts_read: hunt sources
- artifacts_written: fanout registry
- decision_owner: fanout operator
- next_typical: /opsx-fix-bug WITHOUT GO
- known_flaws: NOT_OPENED_BUDGET detail

### /opsx-learn-from-bug
- purpose: product/logic bug → transferable lesson to **existing** process target
- input_state: fixed_or_closed | learning_candidate
- output_state: learning_candidate | fixed_or_closed
- artifacts_read: case/finding / prior classify/fix output
- artifacts_written: approved existing target only with GO
- decision_owner: owner approval for writes
- next_typical: /opsx-learn-from-bug GO | none
- known_flaws: |
  NOT_OPENED_BUDGET detail; MUST NOT own F6/command-contract lessons
  (redirect advisory: `/opsx-admin-command-promote-process-lesson`)

### /opsx-fix-types
- purpose: pyright/mypy typing fixes with GO
- input_state: typing_packet
- output_state: typing_packet | bug_signal_raw
- artifacts_read: type diagnostics
- artifacts_written: typing-only production with GO
- decision_owner: typer
- next_typical: /opsx-fix-bug (behavioral) WITHOUT GO | /opsx-static-check | none
- known_flaws: NOT_OPENED_BUDGET detail

### /opsx-test
- purpose: write targeted tests without production edits
- input_state: implementing | impl_done | tests_authored
- output_state: tests_authored
- artifacts_read: request / code under test
- artifacts_written: tests only
- decision_owner: tester
- next_typical: /opsx-fix-types | /opsx-apply | none
- known_flaws: NOT_OPENED_BUDGET detail

### /opsx-test-triage
- purpose: triage failing/noisy tests
- input_state: tests_authored | static_check_done
- output_state: typing_packet | tests_authored
- artifacts_read: test failures
- artifacts_written: none or triage notes per contract
- decision_owner: triage operator
- next_typical: /opsx-fix-types | /opsx-test
- known_flaws: NOT_OPENED_BUDGET detail

### /opsx-static-check
- purpose: orchestrated FAST/FULL static checks (read-only)
- input_state: implementing | impl_done | static_check_done
- output_state: static_check_done
- artifacts_read: registry + check outputs
- artifacts_written: none (read-only)
- decision_owner: synthesizer
- next_typical: one pasteable NEXT_ACTION from synthesis
- known_flaws: NOT_OPENED_BUDGET detail

### /opsx-commit
- purpose: atomic local commits for product/code/OpenSpec/docs
- input_state: product_dirty
- output_state: product_dirty | pr_ready
- artifacts_read: git status/diff
- artifacts_written: git commits (product scope)
- decision_owner: committer
- next_typical: /opsx-create-pr | /opsx-admin-command-commit (process only; admin off-graph)
- known_flaws: none recorded

### /opsx-split-for-pr
- purpose: split oversized diff into PR-sized parts
- input_state: product_dirty | pr_ready
- output_state: pr_ready
- artifacts_read: diff
- artifacts_written: split plans / handoff prompts
- decision_owner: splitter
- next_typical: /opsx-create-pr
- known_flaws: NOT_OPENED_BUDGET detail

### /opsx-create-pr
- purpose: open a pull request
- input_state: pr_ready
- output_state: pr_ready
- artifacts_read: commits/diff vs base
- artifacts_written: remote PR (via gh)
- decision_owner: PR author
- next_typical: none
- known_flaws: NOT_OPENED_BUDGET detail

### Explicitly excluded from graph
- /opsx-propose — obsolescent; file may exist on disk; do not recommend (F5)

## Transitions

```text
change_idea --/opsx-new--> change_scaffolded
change_scaffolded --/opsx-continue--> artifacts_in_progress|apply_ready
change_idea --/opsx-ff--> apply_ready
artifacts_in_progress --/opsx-continue--> apply_ready
apply_ready --/opsx-apply--> implementing|impl_done
impl_done --/opsx-verify--> verify_pass|verify_fail
verify_pass --/opsx-archive--> archived
verify_fail --/opsx-apply|/opsx-update--> implementing|planning_revise
planning_revise --/opsx-update|/opsx-explore--> apply_ready|change_idea
product_dirty --/opsx-commit--> pr_ready
pr_ready --/opsx-split-for-pr--> pr_ready
pr_ready --/opsx-create-pr--> pr_ready

# product/behavioral only — process-contract Bugbot ≠ this edge (see F6)
bug_signal_raw --/opsx-fix-bug (first-run)--> intake_recorded
intake_recorded --/opsx-fix-bug adjudication--> finding_queued
finding_queued --/opsx-claim-next-bug--> finding_claimed
finding_claimed --/opsx-fix-bug (no GO)--> adjudicating
adjudicating --/opsx-classify-bug--> adjudicating|planning_revise
adjudicating --/opsx-fix-bug GO [iff fix_now]--> fixed_or_closed
adjudicating --/opsx-invariant--> invariant_defined
invariant_defined --/opsx-bug-hunt|/opsx-fanout-bug-hunt--> finding_queued
fixed_or_closed --/opsx-learn-from-bug--> learning_candidate
typing_packet --/opsx-fix-types--> typing_packet|bug_signal_raw
implementing|impl_done --/opsx-static-check--> static_check_done
implementing|impl_done --/opsx-test--> tests_authored
# off-graph (not a not-admin transition; recorded for NAVIGATE orientation):
# command_defect_signal --/opsx-admin-command-fix-command-defects--> FIXED
# FIXED --/opsx-admin-command-promote-process-lesson--> process_lesson_candidate
# process_lesson_candidate --DESIGN_BRIEF_READY--> /opsx-admin-command-design-command
# process_lesson_candidate --EXTEND_EXISTING--> /opsx-admin-command-fix-command-defects
```

## Soft recommendations (advisory only)

NAVIGATE may surface these; they are **not** forced edges and **not**
lifecycle authority.

### Three learning branches (do not mix)

1. **typing** → `/opsx-fix-types` / `/opsx-static-check` — no learning command
2. **logic/product** → `/opsx-fix-bug` → `/opsx-learn-from-bug`
3. **commands/process (F6)** → `/opsx-admin-command-fix-command-defects`
   → optional `/opsx-admin-command-promote-process-lesson`
   → `/opsx-admin-command-design-command` if `DESIGN_BRIEF_READY`

### New command (admin path — soft)

When a **process gap** looks like a missing command (not a one-line fix):

1. Prefer `/opsx-admin-command-promote-process-lesson` if evidence is a
   process Bugbot / FIXED packet (emits `DESIGN_BRIEF_READY`).
2. Or paste the problem into `/opsx-admin-command-design-command` directly.
3. Wait for design need verdict (`NEW_COMMAND_REQUIRED` vs improve existing).
4. Owner `GO OPTION_*` → implement companions → `/opsx-admin-command-commit`.
5. Optional: `/opsx-pipeline UPDATE` → `UPDATE GO` to refresh this graph.

Do **not** invent a new not-admin `/opsx-*` to “learn process contracts”.
Do **not** use `/opsx-bug-hunt` to discover command-contract classes (F6).

### After process FIXED

- Primary: `/opsx-admin-command-commit` if process files changed.
- Soft: `/opsx-admin-command-promote-process-lesson` when the defect class
  looks transferable (guardrail gap, wrong branch, durable handoff omission,
  ADL exhaust, etc.).

## Known pipeline flaws

- id: F1 CLASSIFY_FIXBUG_GO_HANDOFF
  where: opsx-classify-bug.md
  symptom: next action `/opsx-fix-bug GO <summary>` omits durable IDs/claim_token and jumps GO before adjudication
  operator_workaround: `/opsx-claim-next-bug` then `/opsx-fix-bug` WITHOUT GO with case/intake/finding/claim_token; GO only after `fix_now`
  do_not_pretend_fixed: false (contract now forbids GO on classify handoff; Grep 2026-07-27)

- id: F2 CLAIM_RECEIPT_MISSING_CLAIM_TOKEN
  where: opsx-claim-next-bug.md COMMAND_RECEIPT schema
  symptom: CLAIM_TOKEN in body/NEXT_COMMAND_ARGS but omitted from COMMAND_RECEIPT
  operator_workaround: copy `claim_token` from NEXT_COMMAND_ARGS / top-level CLAIM_TOKEN
  do_not_pretend_fixed: false (COMMAND_RECEIPT schema requires CLAIM_TOKEN; Grep 2026-07-27)

- id: F3 SLASH_ALIAS_DRIFT
  where: lifecycle command prose (`/opsx:apply` vs `/opsx-apply`)
  symptom: mixed slash aliases in docs
  operator_workaround: invoke Cursor command id / `opsx-*.md` name
  do_not_pretend_fixed: true

- id: F4 GRAPH_WAS_UNMATERIALIZED
  where: .cursor/pipeline/
  symptom: NAVIGATE blocked before first UPDATE GO
  operator_workaround: this materialization
  do_not_pretend_fixed: false (addressed by this GRAPH.md)

- id: F5 PROPOSE_OBSOLETE_OFF_GRAPH
  where: opsx-propose.md still on disk
  symptom: agents may still suggest `/opsx-propose` from muscle memory
  operator_workaround: use `/opsx-new` + `/opsx-continue` or `/opsx-ff`
  do_not_pretend_fixed: true (graph exclusion ≠ file deletion)

- id: F6 COMMAND_CONTRACT_DEFECT_OFF_GRAPH
  where: NAVIGATE / bug subgraph vs admin process surfaces
  symptom: Bugbot/review on `.cursor/commands/**` was routed to `/opsx-fix-bug` as bug_signal_raw
  operator_workaround: |
    treat as `command_defect_signal`; `/opsx-admin-command-fix-command-defects`
    (READ_ONLY then GO); do not open product bug case map; after FIXED, soft
    `/opsx-admin-command-promote-process-lesson` (not `/opsx-learn-from-bug`)
  do_not_pretend_fixed: false (routing recorded; example ADL apply instance closed in contracts 2026-07-27 — F6 still applies to future process Bugbots)

## Terminal / recovery

- Lifecycle terminal: `archived` (commit/PR may happen earlier)
- Bug recovery: `.tmp/opsx-bug-cases/INDEX.md` pasteable NEXT_ACTION
- Same-chat `/opsx-fix-bug` GO resume: prior `COMMAND_RECEIPT` (CASE_ID / INTAKE_ID / FINDING_ID / CLAIM_TOKEN)
- `/opsx-static-check` / `/opsx-verify`: read-only; no auto-fix inside those commands
- Process-contract defect (Bugbot on commands/rules/skills/static-check): off-graph → `/opsx-admin-command-fix-command-defects` (F6); not `/opsx-fix-bug`
- Process lesson after FIXED: soft → `/opsx-admin-command-promote-process-lesson`
  → `DESIGN_BRIEF_READY` → `/opsx-admin-command-design-command` | `EXTEND_EXISTING` → fix-command-defects
- Admin surfaces (consult, analyze-pipeline, fix-command-defects,
  promote-process-lesson, design-command, admin-commit, opsx-review-commands):
  off-graph by design
- Process ambiguity / command-relationship / admin misbehavior triage (before
  knowing fix vs analyze vs design): `/opsx-admin-command-consult` (READ_ONLY;
  routes to one specialized next step; does not own GRAPH.md)
- Uncommitted process edits after design/fix: `/opsx-admin-command-commit` (not `/opsx-commit`)
