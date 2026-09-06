# OPSX not-admin pipeline graph

## Meta
- scope: ALL_NON_ADMIN_OPSX
- role: shared_materialization
- authority: navigation_snapshot_only
- recommendation_strength: advisory
- operator_may_deviate: true
- not_authority_for: verify_go_nogo, archive, commit, command_contracts, forced_path
- inventory_count: 35
- fingerprint_strength: names_only
- fingerprint_algorithm: md5
- fingerprint_input_mode: names_only_newline_joined
- source_commit: 8917818ef
- excluded_by_owner: opsx-propose.md (obsolescent; do not recommend)
- evidence_note: |
  UPDATE GO 2026-08-18T15:01:00Z: inventory 35; fingerprint
  78bbacb3fcee9523e0bdf73df1a18a5d; indexed WORKTREE/REF target
  semantics for pyright, external-call, and antipattern audits; F13 closed.
  Existing soft chain remains pyright → ecc → optional performance
  → antipattern → static-check; F12 remains open.
  Prior: performance-review (2026-07-30T04:38:13Z); F10 closed.

## States

### Core change lifecycle
- change_idea: need named change / description
- change_scaffolded: change dir exists; first artifact pending (`/opsx-new`)
- artifacts_in_progress: `/opsx-continue` filling artifacts
- apply_ready: applyRequires done (`/opsx-ff` or continue complete)
- scope_bounded: scope split "now vs later" agreed; deferred parks prepared for update handoff
- implementing: `/opsx-apply` in progress
- impl_done: tasks complete; soft-recommend pyright then external-call then conditional performance-review when production `.py`, then antipattern-gate, then static-check / verify
- verify_pass: archive-eligible after `/opsx-verify`
- verify_fail: back to apply/update
- archived: `/opsx-archive` done
- planning_revise: `/opsx-update` / `/opsx-explore`

### Bug / case map
- bug_signal_raw: product/behavioral signal from `/opsx-project-bug-hunt`,
  residual Bugbot, CI, or user (not process-contract; see F6)
- intake_recorded: durable intake on disk
- finding_queued: findings available in case map
- finding_claimed: ownership via `/opsx-claim-next-bug` (only when claimable)
- classifying: `/opsx-classify-bug` (mandatory before implementation route)
- classified_impl: Route A IMPLEMENTATION_BUG → fix-bug WITHOUT GO path
- classified_spec: Route B SPEC_BUG|SPEC_GAP → `/opsx-update` then TASK_DELTA
- task_delta_changed: TASK_DELTA CHANGED → `/opsx-apply` (still needs RED+Owner GO)
- task_delta_unchanged: TASK_DELTA UNCHANGED → `/opsx-fix-bug` WITHOUT GO
- classified_fp: Route C FALSE_POSITIVE → REJECTED / CLOSED_NO_IMPLEMENTATION
- classified_oos: Route D OUT_OF_SCOPE → ROUTE_TO_OTHER_PROCESS (+ ROUTE_TARGET_PROCESS_ID)
- blocked_route_mismatch: EXPECTED≠ACTUAL execution route; no GO / no episode close
- blocked_missing_route_target: Route D without ROUTE_TARGET_PROCESS_ID
- adjudicating: `/opsx-fix-bug` without GO (after classify on implementation routes)
- fix_now_ready: **graph/nav label only** — verdict `fix_now`, awaiting RED
  path then Owner production GO; NOT durable `STATUS: ready_for_fix` (F7)
- red_pending: `/opsx-test case= finding=` authoring/running RED
- RED_CONFIRMED: durable RED evidence with FAILURE_MATCH=YES
- RED_NOT_APPLICABLE_APPROVED: Owner exception packet approved
- red_fail_*: TEST_NOT_REPRODUCING | RED_WRONG_REASON | TEST_SETUP_DEFECT |
  BUG_NOT_TESTABLE | BLOCKED | TIMEOUT (no production GO)
- production_go_ready: BUG_CONFIRMED ∧ FIX_NOW ∧ (RED_CONFIRMED ∨
  RED_NOT_APPLICABLE_APPROVED) — Owner may `/opsx-fix-bug GO`
- fix_implementing: production-only repair under Owner GO (test freeze)
- GREEN_CONFIRMED: `/opsx-test … verify` sole GREEN writer
- fixed_or_closed: branch terminal / fixed with evidence linkage
- learning_candidate: `/opsx-learn-from-bug` phase-1 (**product/logic only**)
- lesson_candidate_only: FANIN incomplete / lesson gate fail-closed
- class_closed: Owner FINAL closed or promoted class lesson
- invariant_defined: invariant packet ready for hunt/fix
- hunt_active: bounded `/opsx-bug-hunt` (MAX_HUNT_PASSES=3)
- branches_active: fanout/claimable children under MAX_ACTIVE_BRANCHES=3
- all_branches_terminal: every started branch has EPISODE_TERMINAL
- FANIN_READY: `results/FANIN.md` assemble complete (materialize
  `mode=fanin_assemble` only; no `/opsx-fan-in-*`)
- family_invariant_captured: post-root-GREEN INVARIANT_CAPTURE_WORKER done
- family_hunt_active: bounded hunter under family fanout policy
- family_relation_classified: RELATION_CLASSIFIER assigned
  SAME_INVARIANT_FINDING | NEW_ROOT_CAUSE | FALSE_POSITIVE | OUT_OF_SCOPE |
  INCONCLUSIVE
- family_branch_fanout_active: SAME_INVARIANT branch RED/FIX/GREEN waves
- family_integrating: INTEGRATION_OPERATOR applying branch patches
- family_green_pending: family-wide GREEN after integration
- FAMILY_FANIN_READY: `results/FAMILY-FANIN.json|.md` assembled
- family_learning: FAMILY_LEARNING_WORKER packet complete
- family_closed: family closure + HUMAN_SUMMARY; uncommitted owner review
- family_open_blocked: INCONCLUSIVE or blocking branch unresolved
- command_defect_signal: off-graph — Bugbot/review on process contracts
  (`.cursor/commands/**`, rules/skills/static-check, mirrors); not a not-admin edge
- process_lesson_candidate: off-graph — after process FIXED / process Bugbot;
  `/opsx-admin-command-promote-process-lesson` (not `/opsx-learn-from-bug`)

### Typing / quality / ship
- typing_packet: pyright/mypy → `/opsx-fix-types`
- tests_authored: `/opsx-test`
- coverage_pass: `/opsx-pyright-strict-coverage` — in-policy diff ⊆ strict include
- coverage_gaps: missing include and/or HIT_EXCLUDE; needs GO or manual include
- blocked_needs_base: coverage command missing/invalid `base=`
- external_call_pass: `/opsx-external-call-coverage` — external surfaces adequately tested
- external_call_gaps: MISSING_TEST / WEAK_EVIDENCE / UNTESTABLE_SEAM / DEFERRED_OWNER
- focus_pass_incomplete_gate: external-call PASS with focus≠all (full gate not closed)
- external_gap_closing: `/opsx-close-external-gap` REFACTOR_AND_TEST (PG/CH) in progress
- external_gap_closed: close STATUS=CLOSED; await focused re-audit
- performance_review_pending: soft gate after external_call_pass when performance trigger applies
- performance_pass: PASS | PASS_WITH_RISK | NOT_APPLICABLE | empty_scope / no surfaces
- performance_fail: FAIL (+ PERFORMANCE_FIX_PACKET) | DATA_GAP on fix/measurement path
- performance_fixing: `/opsx-performance-fix` applying packet (no independent PASS)
- performance_reaudit_pending: READY_FOR_PERFORMANCE_REAUDIT → independent review
- performance_measure_authorized: READY_FOR_ONE_AUTHORIZED_PERFORMANCE_RUN (owner unlocks one run inside fix)
- antipattern_pass: `/opsx-antipattern-gate` STATUS=PASS
- antipattern_suspects: PASS_WITH_SUSPECTS (Owner may continue to static)
- antipattern_fail: FAIL (FIX_EXIT / re-scan; static soft-blocked until Owner continues)
- antipattern_blocked: missing/invalid `base=` / unknown token / ledger write without GO
- debt_clear: `/opsx-bug-debt-board` STATUS=CLEAR (spare-slot; not a hard gate; ≠ card-close)
- debt_found: DEBT_FOUND (pasteable FIX_EXIT; verify/archive are NOT residual close)
- static_check_done: `/opsx-static-check` synthesized
- product_dirty: need `/opsx-commit`
- pr_ready: `/opsx-create-pr` / `/opsx-split-for-pr`

## Commands

### /opsx-explore
- purpose: think through ideas before scaffolding a change
- input_state: change_idea | OWNER_BLOCK (bug-team A/B/C)
- output_state: change_idea | planning_revise | OWNER_DECISION_READY
- artifacts_read: none required; optional case/finding when bug-tied
- artifacts_written: none
- decision_owner: operator
- next_typical: /opsx-new | /opsx-ff | /opsx-bug-team mode=continue (pasteable handback after A/B/C)
- known_flaws: when clarifying Owner A/B/C must emit pasteable team return — NO_SILENT_RETURN

### /opsx-bound-scope
- purpose: trim oversized change scope into now-vs-later with WORKLOG parking and `/opsx-update` handoff
- input_state: planning_revise | change_idea
- output_state: planning_revise | scope_bounded
- artifacts_read: change proposal/design/tasks/specs (+ targeted ADL when needed)
- artifacts_written: plan-only none; with `:GO` append `DOTO/WORKLOG.md` + emit `UPDATE_HANDOFF`
- decision_owner: operator (GO required for WORKLOG writes)
- next_typical: /opsx-update (after accepted keep/defer split, usually post `/opsx-explore` TЗ discussion)
- known_flaws: none recorded

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
- purpose: revise existing planning artifacts coherently; on bug-episode spec route emit TASK_DELTA
- input_state: planning_revise | apply_ready | verify_fail | classified_spec
- output_state: apply_ready | planning_revise | task_delta_changed | task_delta_unchanged
- artifacts_read: change planning artifacts; optional case ROUTE_STATE
- artifacts_written: revised planning artifacts; TASK-DELTA-*.md; ROUTE-TRACE.jsonl; ROUTE_STATE
- decision_owner: operator
- next_typical: /opsx-apply (TASK_DELTA CHANGED) | /opsx-fix-bug GO path (TASK_DELTA UNCHANGED) | /opsx-bug-team handback (SECONDARY) | /opsx-continue
- known_flaws: NOT_OPENED_BUDGET detail; update ≠ production GO; never closed_fixed from update; persist CLOSE_FINDING_INTENT on ROUTE_STATE

### /opsx-apply
- purpose: implement tasks from an OpenSpec change; bug-episode path requires RED+Owner GO
- input_state: apply_ready | implementing | verify_fail | task_delta_changed | production_go_ready
- output_state: implementing | impl_done | fix_implementing
- artifacts_read: tasks.md, design, decisions (context-first); RED evidence when bug-episode
- artifacts_written: production/code per tasks (after gate); ROUTE-TRACE.jsonl
- decision_owner: implementer + architecture decisions + Owner GO when bug-episode
- next_typical: /opsx-pyright-strict-coverage (when production .py changed) | /opsx-external-call-coverage | /opsx-performance-review (when trigger applies) | /opsx-antipattern-gate | /opsx-static-check | /opsx-verify | /opsx-test verify (bug-episode PRIMARY) | /opsx-bug-team handback (SECONDARY) | /opsx-project-bug-hunt
- known_flaws: soft recommend after apply (not hard archive gate); tests/** out of policy; bug-episode must not treat OpenSpec verify as card close; never silent team return; apply soft handoff may omit antipattern (F12 / NOT_OPENED_BUDGET)

### /opsx-pyright-strict-coverage
- purpose: audit base-to-WORKTREE or base-to-REF production Python ⊆ pyrightconfig_strict.json include (not exclude)
- input_state: implementing | impl_done | product_dirty
- output_state: coverage_pass | coverage_gaps | blocked_needs_base
- artifacts_read: base-to-target diff including staged/unstaged/untracked WORKTREE paths; pyrightconfig_strict.json
- artifacts_written: none without GO; with GO only additive include[] entries
- decision_owner: coverage auditor; include expansion only with owner GO
- next_typical: /opsx-external-call-coverage | /opsx-antipattern-gate | /opsx-static-check | /opsx-fix-types (after static FAIL) | /opsx-verify | retry with GO
- known_flaws: soft recommend after apply (not hard archive gate); tests/** out of policy; explicit `head=<ref>` is immutable while omitted `head=`/`head=working` audit WORKTREE; contract NEXT may lag antipattern insert (F12)

### /opsx-external-call-coverage
- purpose: audit base-to-WORKTREE or base-to-REF production external-call surfaces (HTTP/WB/PG/CH/Redis/…) ↔ adequate tests per testing-rules
- input_state: coverage_pass | impl_done | implementing | product_dirty | external_call_gaps | external_gap_closed
- output_state: external_call_pass | external_call_gaps | focus_pass_incomplete_gate | blocked_needs_base
- artifacts_read: base-to-target diff including staged/unstaged/untracked WORKTREE paths; app/**; tests/**; testing-rules.mdc; optional EXTERNAL_CALL_COVERAGE_REPORT / change artifacts
- artifacts_written: none (v1 read-only; chat report / optional pasted EXTERNAL_CALL_COVERAGE_REPORT)
- decision_owner: coverage auditor for dispositions; archive remains /opsx-verify
- next_typical: /opsx-performance-review (when trigger applies) | /opsx-antipattern-gate | /opsx-static-check | /opsx-test (TEST_ONLY) | /opsx-close-external-gap (PG/CH) | /opsx-verify | rerun with focus=
- known_flaws: soft recommend (not hard archive gate alone); kind taxonomy inside one command (no per-dep audit front-doors); PG/CH require live integration; omitted `head=` no longer requires a commit for WORKTREE re-audit; NEXT rules beyond opened budget may lag antipattern (F12)

### /opsx-performance-review
- purpose: READ_ONLY semantic performance verdict on scoped Python (N+1/async/queue/concurrency); sole issuer of PASS|PASS_WITH_RISK|FAIL|DATA_GAP; emits FIX_PACKET / optional measurement auth
- input_state: external_call_pass | impl_done | performance_reaudit_pending | performance_review_pending | product_dirty
- output_state: performance_pass | performance_fail | performance_measure_authorized | performance_review_pending
- artifacts_read: scoped git/app Python; optional PERFORMANCE_FIX_RESULT / MEASUREMENT_RESULT
- artifacts_written: none (chat report / packets only)
- decision_owner: independent performance reviewer (not fixer self-report)
- next_typical: /opsx-antipattern-gate (PASS|PASS_WITH_RISK|empty/no surfaces) | /opsx-static-check [operator skip / demoted primary] | /opsx-performance-fix + FIX_PACKET (FAIL) | re-run after measurement
- known_flaws: soft conditional gate (not every-diff hard archive gate); default scope=staged can empty_scope-PASS while working dirty; no /opsx-performance-run; contract NEXT still→static without antipattern (F12)

### /opsx-performance-fix
- purpose: apply PERFORMANCE_FIX_PACKET; optional one-shot measurement only under review-issued READY_FOR_ONE_AUTHORIZED_PERFORMANCE_RUN; never issues independent PASS
- input_state: performance_fail | performance_fixing | performance_measure_authorized
- output_state: performance_reaudit_pending | performance_fixing | performance_fail
- artifacts_read: pasted FIX_PACKET / AUTHORIZATION; causal paths
- artifacts_written: scoped app/** + tests per packet; measurement artifacts only under auth
- decision_owner: fixer (bounded); independent verdict remains /opsx-performance-review
- next_typical: /opsx-performance-review + PERFORMANCE_FIX_RESULT | measure under auth then review
- known_flaws: fixer self-report ≠ PASS; no invented /opsx-performance-run; do not strip Queue/Semaphore/Lock/Redis NX/caps without proof

### /opsx-antipattern-gate
- purpose: base-to-WORKTREE or base-to-REF antipattern over-report; optional practice ledger via `accept|reject` + GO
- input_state: external_call_pass | performance_pass | impl_done | product_dirty | antipattern_fail | antipattern_suspects
- output_state: antipattern_pass | antipattern_suspects | antipattern_fail | antipattern_blocked
- artifacts_read: base-to-target diff including staged/unstaged/untracked WORKTREE paths; catalog; PRACTICE_LEDGER.jsonl; optional change context
- artifacts_written: none on SCAN; with accept/reject+GO append-only `.cursor/antipattern-gate/PRACTICE_LEDGER.jsonl`
- decision_owner: antipattern auditor; ledger write only with Owner GO
- next_typical: /opsx-static-check (PASS|PASS_WITH_SUSPECTS) | FIX_EXIT / re-scan (FAIL) | /opsx-verify
- known_flaws: soft gate (not hard archive); over-report intentional; omitted `head=`/`head=working` audits WORKTREE while `head=<ref>` is immutable; MATCHES_ACCEPTED_PRACTICE ≠ testing-rules proof

### /opsx-bug-debt-board
- purpose: READ_ONLY cross-case bug debt inventory (INDEX + cases); pasteable recovery exits
- input_state: anytime (esp. post-GREEN | FANIN | chat-loss | pre-verify spare slot | family_closed)
- output_state: debt_clear | debt_found | blocked (missing INDEX/cases / bad case=)
- artifacts_read: `.opsx/runs/bug-cases/INDEX.md` + case LEDGER/FANIN/findings/HC-*
- artifacts_written: none (READ_ONLY; never INDEX/LEDGER/close writer)
- decision_owner: operator picks which debt row; FANIN/close remain other commands
- next_typical: first HARD_BLOCK / OPEN_CANDIDATE FIX_EXIT | /opsx-bug-team resume | /opsx-claim-next-bug | materialize update | continue planned hop if CLEAR
- known_flaws: soft only; CLEAR ≠ card-close; verify/archive are NOT residual close while debt open

### /opsx-close-external-gap
- purpose: REFACTOR_AND_TEST closure for PG/CH gaps from coverage packet (minimal seam + live integration); no base=
- input_state: external_call_gaps
- output_state: external_gap_closed | external_gap_closing | external_call_gaps | tests_authored | implementing
- artifacts_read: pasted EXTERNAL_CALL_COVERAGE_REPORT / GAPS; testing-rules; gap PATH symbols
- artifacts_written: minimal app/** seam + tests/integration/** when REFACTOR_AND_TEST
- decision_owner: closure writer; TEST_ONLY redirects to /opsx-test; oversized seam → /opsx-apply
- next_typical: /opsx-external-call-coverage base=<PACKET_BASE> focus=pg|ch | /opsx-test | /opsx-apply
- known_flaws: must not accept base=; session-mock unit ≠ CLOSED for PG/CH

### /opsx-materialize-bug-queue
- purpose: durable bug-case map (intake/update/hunt-result/promote/fanin_assemble) + corrupt-claim repair + ROUTE_STATE assist
- input_state: bug_signal_raw | finding_queued | finding_claimed | all_branches_terminal | FANIN_READY
- output_state: intake_recorded | finding_queued | finding_claimed | FANIN_READY | lesson_candidate_only
- artifacts_read: .opsx/runs/bug-cases/**
- artifacts_written: .opsx/runs/bug-cases/** ; fanin_assemble writes ONLY results/FANIN.md ; may append ROUTE-TRACE
- decision_owner: materialize contract (no Owner / class authority)
- next_typical: /opsx-claim-next-bug | /opsx-classify-bug | /opsx-learn-from-bug FANIN_PATH= | repair pasteable
- known_flaws: F8 (repair path exists; operators may still invent tokens)

### /opsx-claim-next-bug
- purpose: claim one eligible finding (`STATUS=available` ∧ `CHAT_REQUIRED=true` only)
- input_state: finding_queued | branches_active
- output_state: finding_claimed
- artifacts_read: CASE/LEDGER/finding packet
- artifacts_written: claim fields in case map (incl. durable CLAIM_TOKEN); ROUTE-TRACE; ROUTE_STATE
- decision_owner: claimer chat_label
- next_typical: /opsx-classify-bug (+ case/finding/claim_token context)
- known_flaws: |
  F2 addressed in contract (keep historical id); ineligible:
  known-root CHAT_REQUIRED=false, DUP-*/duplicate_root/duplicate_root_observation,
  backlog/blocked/closed/promoted; corrupt claimed+empty token → materialize repair
  (not invent token; not treat as owner_already_has success)

### /opsx-fix-bug
- purpose: adjudicate product/behavioral bugs after classify; Owner GO = production-only after RED gate
- input_state: classified_impl | task_delta_unchanged | finding_claimed | intake_recorded | adjudicating | fix_now_ready | production_go_ready | fix_implementing
- output_state: adjudicating | fix_now_ready | production_go_ready | fix_implementing | fixed_or_closed | learning_candidate | invariant_defined
- artifacts_read: intakes/findings; ROUTE_STATE/classification; RED evidence; code forensics
- artifacts_written: .opsx/runs/bug-cases/** without GO; production only with GO+fix_now+RED gate; tests forbidden under GO; ROUTE-TRACE
- decision_owner: adjudicator + claim gate + classify-first + Owner GO + RED-before-GO
- next_typical: /opsx-classify-bug (if missing) | /opsx-test case= finding= | /opsx-fix-bug GO (after RED) | /opsx-claim-next-bug | /opsx-invariant | /opsx-bug-team handback (post-GO SECONDARY) | /opsx-learn-from-bug | none
- known_flaws: |
  F6: does not own process-contract defects → `/opsx-admin-command-fix-command-defects`;
  F7: durable STATUS ready_for_fix/adjudicating/implementing/verification blocks
  finding= path; F8: claimed+empty durable CLAIM_TOKEN → materialize repair;
  claim-first when available+CHAT_REQUIRED=true; classify-first before impl route;
  skip-claim OK for known-root CHAT_REQUIRED=false; DUP-/duplicate_root →
  blocked_finding_status_not_actionable; production GO blocked without
  RED_CONFIRMED | RED_NOT_APPLICABLE_APPROVED (`blocked_needs_red_before_go`);
  not GREEN writer; no NON_WEAKEN_DELTA self-approve; never closed_fixed from fix-bug;
  post-GO PRIMARY = test verify + pasteable team handback

### /opsx-classify-bug
- purpose: classify finding vs OpenSpec; mandatory router before implementation route
- input_state: finding_claimed | finding_queued | intake_recorded | classifying
- output_state: classified_impl | classified_spec | classified_fp | classified_oos | classifying
- artifacts_read: finding packet / OpenSpec
- artifacts_written: ROUTE-TRACE.jsonl + LEDGER ## ROUTE_STATE only (no OpenSpec/code)
- decision_owner: classifier
- next_typical: /opsx-fix-bug WITHOUT GO | /opsx-update | stop FP | ROUTE_TO_OTHER_PROCESS
- known_flaws: F1 addressed in contract (forbids GO on handoff)

### /opsx-bug-team
- purpose: Active registry-driven Cursor Task team for full bug lifecycle
  (free-form intake → materialize/claim/classify → Route A|B|C|D → RED/FIX/GREEN
  → invariant capture → bounded hunt → relation classify → same-invariant fanout
  → integration → family GREEN → family fan-in → learning → closure)
- input_state: bug_signal_raw | intake_recorded | finding_queued | (resume) any team checkpoint | resume-family-fanout
- output_state: GREEN_CONFIRMED | FAMILY_FANIN_READY | family_closed | family_open_blocked | BLOCKED_* | UNCOMMITTED_AWAITING_OWNER_REVIEW
- artifacts_read: registry + checkpoint + case map + ACTIVATION.json + family policy
- artifacts_written: team/DISPATCH.jsonl + CHECKPOINT + worker packets; FANIN.md;
  family/*; FAMILY-FANIN; LEARNING; HUMAN_SUMMARY
- decision_owner: orchestrator (Task dispatch) + local uncommitted authority;
  final commit = OWNER_ONLY
- next_typical: /opsx-bug-team (continue/resume) | /opsx-explore case= finding= (OPTIONAL_IF_UNSURE on Owner-block) | owner review uncommitted diff
- known_flaws: |
  RUNTIME_STATUS=ACTIVE; PIPELINE_GENERATION=ACTIVE_V1_WITH_INVARIANT_FANOUT_V10;
  BUG_FAMILY_FANOUT_ENABLED=true; SAME_INVARIANT automatic fanout (no manual
  sibling relaunch); EXECUTION_IDENTITY_GATE=ACTIVE; commit/push/deploy forbidden;
  platform may serialize eligible parallel tasks (honest, not failure);
  command-native v2 PLANNED_SEPARATELY;
  Owner-block must show A/B/C + optional explore + pasteable THEN_RETURN

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

### /opsx-invariant
- purpose: named behavioral invariant + hunt/fix handoff packets
- input_state: adjudicating | invariant_defined | GREEN_CONFIRMED
- output_state: invariant_defined
- artifacts_read: case/finding / code
- artifacts_written: invariant packets (per contract)
- decision_owner: invariant author
- next_typical: /opsx-bug-team handback (PRIMARY when case=) | /opsx-bug-hunt | /opsx-fix-bug WITHOUT GO (ALSO_OK solo)
- known_flaws: invariant is a fork — prefer team handback over human hunt/close menu; NO_SILENT_RETURN

### /opsx-project-bug-hunt
- purpose: primary project-tuned discovery on base..head (WB Sky Bugbot analogue); feeds intake
- input_state: implementing | impl_done | product_dirty | pr_ready
- output_state: bug_signal_raw | pr_ready
- artifacts_read: git diff base...head; change/ADL context-first; own checklist
- artifacts_written: none by default; minimal confirmed fixes only with GO
- decision_owner: project hunter
- next_typical: /opsx-materialize-bug-queue mode=intake | /opsx-create-pr (after receipt)
- known_flaws: |
  must not absorb F6 or replace root-aware /opsx-bug-hunt; not a zero-Bugbot SLA

### /opsx-bug-hunt
- purpose: root-aware invariant-focused sibling hunt (NOT primary pre-PR hunter)
- input_state: invariant_defined | GREEN_CONFIRMED | hunt_active
- output_state: hunt_active | finding_queued | branches_active
- artifacts_read: root packet / code
- artifacts_written: hunt findings (process) ; minimal fixes only with GO+confirmed
- decision_owner: hunter
- next_typical: /opsx-materialize-bug-queue | /opsx-fanout-bug-hunt | /opsx-claim-next-bug (never bare fix-bug)
- known_flaws: |
  NOT_OPENED_BUDGET detail; MAX_HUNT_PASSES=3 / MAX_DEPTH_FROM_ROOT=3 /
  PASS_3=MANDATORY_STOP; NEW_INVARIANT_FROM_BRANCH=FORBIDDEN

### /opsx-fanout-bug-hunt
- purpose: fan-out hunt registry for parallel adjudication
- input_state: invariant_defined | finding_queued | hunt_active
- output_state: finding_queued | branches_active
- artifacts_read: hunt sources
- artifacts_written: fanout registry (preview); durable via materialize
- decision_owner: fanout operator
- next_typical: /opsx-claim-next-bug (chat-required) | materialize (never bare fix-bug; never FANIN)
- known_flaws: |
  NOT_OPENED_BUDGET detail; duplicate_root → observation not claimable;
  MAX_ACTIVE_BRANCHES=3; LEARNING_READY != FANIN_READY; no fan-in assemble

### /opsx-learn-from-bug
- purpose: product/logic bug → transferable lesson to **existing** process target
- input_state: fixed_or_closed | learning_candidate | FANIN_READY | lesson_candidate_only
- output_state: learning_candidate | lesson_candidate_only | class_closed | fixed_or_closed
- artifacts_read: case/finding / FANIN.md when class-level / prior classify/fix output
- artifacts_written: approved existing target only with GO + lesson gate
- decision_owner: owner approval for writes; class GO only after FANIN_READY
- next_typical: /opsx-learn-from-bug GO (class only if LESSON_GATE_PASS) | /opsx-project-bug-hunt | none
- known_flaws: |
  NOT_OPENED_BUDGET detail; MUST NOT own F6/command-contract lessons
  (redirect advisory: `/opsx-admin-command-promote-process-lesson`);
  Bugbot residual miss → prefer target opsx-project-bug-hunt.md checklist;
  without FANIN_READY → LESSON_CANDIDATE_ONLY + CLASS_LEVEL_GO_WRITE FORBIDDEN

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
- purpose: targeted tests; bug-regression RED producer; sole GREEN writer (verify)
- input_state: implementing | impl_done | tests_authored | fix_now_ready | red_pending | fix_implementing | GREEN_CONFIRMED
- output_state: tests_authored | red_pending | RED_CONFIRMED | red_fail_* | GREEN_CONFIRMED
- artifacts_read: request / finding packet / RED evidence
- artifacts_written: tests/** ; results/RED-*.md ; results/GREEN-*.md (verify only)
- decision_owner: tester / regression author
- next_typical: /opsx-fix-bug (after RED_CONFIRMED, Owner may GO) | /opsx-bug-team handback (after GREEN, default) | /opsx-materialize-bug-queue close=fixed (solo) | /opsx-fix-types | none
- known_flaws: NOT_OPENED_BUDGET detail; GREEN_BLOCKED_PENDING_TEST_DELTA_REVIEW on hash mismatch; post-GREEN default team handback not OpenSpec verify

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
- input_state: implementing | impl_done | antipattern_pass | antipattern_suspects | performance_pass | external_call_pass | static_check_done
- output_state: static_check_done
- artifacts_read: registry + check outputs
- artifacts_written: none (read-only)
- decision_owner: synthesizer
- next_typical: one pasteable NEXT_ACTION from synthesis
- known_flaws: NOT_OPENED_BUDGET detail

### /opsx-commit
- purpose: atomic local Git packaging for product/code/OpenSpec/docs (no verification gate)
- input_state: product_dirty
- output_state: product_dirty | pr_ready
- artifacts_read: git status/diff
- artifacts_written: git commits (product scope)
- decision_owner: committer
- next_typical: /opsx-static-check | /opsx-verify | /opsx-create-pr | /opsx-project-bug-hunt | /opsx-admin-command-commit (process only; admin off-graph)
- known_flaws: none recorded

### /opsx-split-for-pr
- purpose: split oversized diff into PR-sized parts
- input_state: product_dirty | pr_ready
- output_state: pr_ready
- artifacts_read: diff
- artifacts_written: split plans / handoff prompts
- decision_owner: splitter
- next_typical: /opsx-project-bug-hunt | /opsx-create-pr
- known_flaws: NOT_OPENED_BUDGET detail

### /opsx-create-pr
- purpose: open a pull request (publication/review container; no verification gate; PR ≠ merge auth)
- input_state: pr_ready
- output_state: pr_ready
- artifacts_read: commits/diff vs base
- artifacts_written: remote PR (via gh)
- decision_owner: PR author
- next_typical: /opsx-verify | /opsx-static-check | /opsx-project-bug-hunt (soft ALSO_OK) | CI review
- known_flaws: none recorded

### Explicitly excluded from graph
- /opsx-propose — obsolescent; file may exist on disk; do not recommend (F5)

## Transitions

```text
change_idea --/opsx-new--> change_scaffolded
change_scaffolded --/opsx-continue--> artifacts_in_progress|apply_ready
change_idea --/opsx-ff--> apply_ready
artifacts_in_progress --/opsx-continue--> apply_ready
apply_ready --/opsx-apply--> implementing|impl_done
impl_done --/opsx-pyright-strict-coverage--> coverage_pass|coverage_gaps
coverage_pass --/opsx-external-call-coverage--> external_call_pass|external_call_gaps|focus_pass_incomplete_gate
external_call_pass --/opsx-performance-review [trigger REQUIRED|RECOMMENDED]--> performance_pass|performance_fail|performance_measure_authorized|performance_review_pending
external_call_pass --/opsx-antipattern-gate [perf skipped / NOT_APPLICABLE]--> antipattern_pass|antipattern_suspects|antipattern_fail|antipattern_blocked
external_call_pass --/opsx-static-check [operator skip only; demoted]--> static_check_done
performance_pass --/opsx-antipattern-gate--> antipattern_pass|antipattern_suspects|antipattern_fail|antipattern_blocked
# demoted primary (was typical; keep as operator skip only):
# performance_pass --/opsx-static-check--> static_check_done
performance_pass --/opsx-static-check [operator skip / demoted primary]--> static_check_done
antipattern_pass|antipattern_suspects --/opsx-static-check--> static_check_done
antipattern_fail --FIX_EXIT|/opsx-antipattern-gate re-scan--> antipattern_pass|antipattern_suspects|antipattern_fail|antipattern_blocked
performance_fail --/opsx-performance-fix--> performance_reaudit_pending|performance_fixing
performance_reaudit_pending --/opsx-performance-review--> performance_pass|performance_fail|performance_measure_authorized
performance_measure_authorized --/opsx-performance-fix AUTHORIZE_ONE_PERFORMANCE_RUN--> performance_reaudit_pending
* --/opsx-bug-debt-board [ALSO_OK anytime]--> debt_clear|debt_found
coverage_pass --/opsx-static-check--> static_check_done
coverage_gaps --/opsx-pyright-strict-coverage GO|/opsx-pyright-strict-coverage--> coverage_pass|coverage_gaps
external_call_gaps --/opsx-test--> tests_authored
external_call_gaps --/opsx-close-external-gap--> external_gap_closed|external_gap_closing|external_call_gaps
external_gap_closed --/opsx-external-call-coverage--> external_call_pass|external_call_gaps|focus_pass_incomplete_gate
external_call_gaps --/opsx-external-call-coverage--> external_call_pass|external_call_gaps
focus_pass_incomplete_gate --/opsx-external-call-coverage--> external_call_pass|external_call_gaps
impl_done --/opsx-external-call-coverage--> external_call_pass|external_call_gaps|focus_pass_incomplete_gate
impl_done --/opsx-performance-review--> performance_pass|performance_fail|performance_measure_authorized
impl_done --/opsx-antipattern-gate--> antipattern_pass|antipattern_suspects|antipattern_fail|antipattern_blocked
impl_done --/opsx-verify--> verify_pass|verify_fail
verify_pass --/opsx-archive--> archived
verify_fail --/opsx-apply|/opsx-update--> implementing|planning_revise
planning_revise --/opsx-update|/opsx-explore--> apply_ready|change_idea
planning_revise --/opsx-bound-scope [after TЗ discussion in /opsx-explore]--> planning_revise|scope_bounded
planning_revise --/opsx-bound-scope:GO [accepted split]--> scope_bounded
scope_bounded --/opsx-update--> apply_ready|planning_revise
product_dirty --/opsx-commit--> product_dirty|pr_ready
impl_done|product_dirty|pr_ready --/opsx-static-check|/opsx-verify--> static_check_done|verify_pass|verify_fail
pr_ready --/opsx-split-for-pr--> pr_ready
pr_ready --/opsx-create-pr--> pr_ready

# primary project-tuned discovery (Bugbot = residual safety net)
implementing|impl_done|product_dirty|pr_ready --/opsx-project-bug-hunt--> bug_signal_raw|pr_ready
bug_signal_raw --/opsx-materialize-bug-queue mode=intake--> intake_recorded

# product/behavioral only — process-contract Bugbot ≠ this edge (see F6)
# residual Bugbot / CI / user may still enter here
bug_signal_raw --/opsx-fix-bug (first-run mode=intake)--> intake_recorded
intake_recorded --/opsx-fix-bug|materialize--> finding_queued

# queue / child-chat only (CHAT_REQUIRED=true ∧ STATUS=available)
finding_queued --/opsx-claim-next-bug--> finding_claimed
finding_claimed --/opsx-classify-bug--> classifying|classified_impl|classified_spec|classified_fp|classified_oos

# known-root / non-queue (CHAT_REQUIRED=false; claim optional/skipped)
finding_queued --/opsx-classify-bug [CHAT_REQUIRED=false known-root]--> classified_*

# Route A
classified_impl --/opsx-fix-bug (no GO)--> adjudicating|fix_now_ready
# Route B
classified_spec --/opsx-update--> task_delta_changed|task_delta_unchanged
task_delta_changed --/opsx-apply [after RED+Owner GO]--> fix_implementing|implementing
task_delta_unchanged --/opsx-fix-bug (no GO)--> adjudicating|fix_now_ready
# Route C / D
classified_fp --> fixed_or_closed
classified_oos --> ROUTE_TO_OTHER_PROCESS

fix_now_ready --/opsx-test case= finding=--> red_pending
red_pending --/opsx-test (RED run)--> RED_CONFIRMED|red_fail_*
# Owner may approve RED_NOT_APPLICABLE_APPROVED (exception packet) instead of RED_CONFIRMED
RED_CONFIRMED|RED_NOT_APPLICABLE_APPROVED --(Owner)--> production_go_ready
# production GO only if BUG_CONFIRMED ∧ FIX_NOW ∧ (RED_CONFIRMED ∨ RED_NOT_APPLICABLE_APPROVED)
production_go_ready --/opsx-fix-bug GO [iff fix_now + RED gate]--> fix_implementing
production_go_ready --/opsx-apply [bug-episode TASK_DELTA CHANGED + same gate]--> fix_implementing
fix_implementing --/opsx-test verify--> GREEN_CONFIRMED
GREEN_CONFIRMED --/opsx-bug-team resume-family-fanout [default POST_GREEN_OWNER=bug-team]--> family_invariant_captured|family_closed|…
GREEN_CONFIRMED --solo close=fixed [POST_GREEN_OWNER=solo only]--> fixed_or_closed
# do not treat apply all_done as fixed_or_closed; apply never writes closed_fixed
# phantom edge removed: GREEN_CONFIRMED --> fixed_or_closed (no command)
# durable STATUS for GO path: available+CHAT_REQUIRED=false OR claimed+token
# — NOT durable ready_for_fix / adjudicating / implementing / verification (F7)
# classify-first: fix-bug without CURRENT_CLASSIFICATION → blocked_needs_classify_first

# refuse / repair (orientation; not happy-path edges)
# DUP-*|duplicate_root|duplicate_root_observation --X--> claim-next | fix-bug adjudication
# claimed+empty CLAIM_TOKEN --/opsx-materialize-bug-queue repair=mint|release--> claimed|available

adjudicating --/opsx-invariant--> invariant_defined
# legacy optional classify after adjudication removed as typical edge;
# classify is mandatory BEFORE implementation route selection
GREEN_CONFIRMED|fixed_or_closed --/opsx-invariant--> invariant_defined
invariant_defined --/opsx-bug-hunt--> hunt_active
hunt_active --/opsx-fanout-bug-hunt|/opsx-materialize-bug-queue--> branches_active|finding_queued
branches_active --/opsx-claim-next-bug--> finding_claimed
# per-branch: claim → classify → route → RED → Owner GO → GREEN → EPISODE_TERMINAL
all_branches_terminal --/opsx-materialize-bug-queue mode=fanin_assemble--> FANIN_READY|lesson_candidate_only
FANIN_READY --/opsx-learn-from-bug--> learning_candidate|class_closed
# without FANIN_READY: lesson stays LESSON_CANDIDATE_ONLY (CLASS_LEVEL_GO_WRITE forbidden)

# /opsx-bug-team invariant-family fanout V8–V10 (ACTIVE; automatic after root GREEN)
GREEN_CONFIRMED --/opsx-bug-team INVARIANT_CAPTURE--> family_invariant_captured
family_invariant_captured --/opsx-bug-team BOUNDED_HUNTER--> family_hunt_active
family_hunt_active --/opsx-bug-team RELATION_CLASSIFIER--> family_relation_classified
family_relation_classified --SAME_INVARIANT_FINDING--> family_branch_fanout_active
family_relation_classified --NEW_ROOT_CAUSE--> finding_queued  # linked case
family_relation_classified --FALSE_POSITIVE--> fixed_or_closed  # durable rejection
family_relation_classified --OUT_OF_SCOPE--> ROUTE_TO_OTHER_PROCESS  # durable handoff
family_relation_classified --INCONCLUSIVE--> family_open_blocked
family_branch_fanout_active --branch RED/FIX/GREEN--> family_integrating
family_integrating --/opsx-bug-team INTEGRATION_OPERATOR--> family_green_pending
family_green_pending --FAMILY_WIDE_GREEN--> FAMILY_FANIN_READY
FAMILY_FANIN_READY --/opsx-bug-team FAMILY_LEARNING_WORKER--> family_learning
family_learning --/opsx-bug-team CLOSURE--> family_closed
# resume: /opsx-bug-team case=<CASE_ID> mode=resume-family-fanout
fixed_or_closed --/opsx-learn-from-bug [finding-local]--> learning_candidate|lesson_candidate_only
typing_packet --/opsx-fix-types--> typing_packet|bug_signal_raw
implementing|impl_done|coverage_pass|external_call_pass|performance_pass|antipattern_pass|antipattern_suspects --/opsx-static-check--> static_check_done
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

### Post-apply pyright-strict allowlist coverage

After `/opsx-apply` when production Python changed (`app/**/*.py` or
top-level production scripts): recommend
`/opsx-pyright-strict-coverage base=<BASE>` before
`/opsx-external-call-coverage`, optional `/opsx-performance-review`,
`/opsx-antipattern-gate`, `/opsx-static-check`, and `/opsx-verify`.
`PASS` pyright-strict alone does **not** prove changed files are in
`pyrightconfig_strict.json` include. Soft recommend — does not block
archive by itself.

### Post-apply external-call coverage

After pyright-coverage `PASS` (or when allowlist already known good) and
production `.py` changed: recommend
`/opsx-external-call-coverage base=<BASE>` before conditional
`/opsx-performance-review`, `/opsx-antipattern-gate`, `/opsx-static-check`,
and `/opsx-verify`. One command covers HTTP/WB/PG/CH/Redis/OTHER via kind
taxonomy (`focus=` optional for debug only). Soft recommend — absence of
report does not auto-`NO_GO` verify; open gaps in a present
`EXTERNAL_CALL_COVERAGE_REPORT` do. Does **not** replace
`TEST_COVERAGE_PACKET`.

Closure split after FAIL:

* TEST_ONLY (Redis/WB/…) → `/opsx-test` → focused re-audit
* REFACTOR_AND_TEST (PG/CH) → `/opsx-close-external-gap` with pasted
  report (**no** `base=` on close) → focused re-audit

### Post-apply performance review (conditional)

After external-call `PASS`, when performance trigger applies (DB/query/
repository; Queue/TasksManager/`run_tasks`/`gather`/`create_task`;
Semaphore/Lock/Redis NX; pool/cap/rate-limit/retry/backpressure): soft
recommend `/opsx-performance-review scope=base base=<BASE>` before
`/opsx-antipattern-gate` then `/opsx-static-check`. Not every-diff
mandatory. `FAIL` → `/opsx-performance-fix` + FIX_PACKET → independent
re-audit via review (fixer self-report is never PASS). Measurement only
under `READY_FOR_ONE_AUTHORIZED_PERFORMANCE_RUN` inside fix — there is no
`/opsx-performance-run`. Operator may skip soft gate (deviation allowed).
Direct `performance_pass → static-check` is demoted (operator skip only).

### Post-apply antipattern gate

After external-call `PASS` and optional performance
`PASS|PASS_WITH_RISK|NOT_APPLICABLE` (or when perf skipped): soft recommend
`/opsx-antipattern-gate base=<BASE>` before `/opsx-static-check` /
`/opsx-verify`. Over-report by design. `PASS|PASS_WITH_SUSPECTS` →
static-check (Owner may continue with suspects). `FAIL` → FIX_EXIT /
re-scan; soft-block static until Owner continues. Soft recommend — not a
hard archive gate. Optional practice ledger: `accept=` / `reject=` + GO.

### Bug debt board (ALSO_OK anytime)

Anytime (esp. post-GREEN / FANIN / chat-loss / pre-verify spare slot):
`/opsx-bug-debt-board` surfaces open findings, OPEN_CANDIDATE /
HARD_BLOCK_READY residuals, CLOSED-with-residual, stale claims with
pasteable FIX_EXIT. `CLEAR` ≠ card-close. `/opsx-verify` / `/opsx-archive`
are **not** residual close while debt open. Soft only — not FANIN/INDEX
writer.

### Pre-Bugbot primary hunt (soft ALSO_OK — not a PR gate)

`/opsx-project-bug-hunt base=<PR-base> head=<branch>` is recommended before
merge/review on product/runtime diffs but **does not** block `/opsx-create-pr`.
Bugbot PR section = residual only.
If Bugbot still finds product/logic: fix path → `/opsx-learn-from-bug`
`target=.cursor/commands/opsx-project-bug-hunt.md` checklist → re-hunt.
Do **not** use `/opsx-bug-hunt` as the first pre-PR sweep (needs root+invariant).

### Product bug-episode orchestration (ACTIVE_V1_WITH_INVARIANT_FANOUT_V10)

Typical advisory path (not forced; command contracts win):

```text
/opsx-bug-team (DEFAULT_FULL_BUG_ENTRY)
  materialize → claim → CLASSIFIER → Route A|B|C|D
  A: IMPLEMENTATION_BUG → RED → local authority → EXECUTOR → GREEN
  B: SPEC_* → SPEC_UPDATE → TASK_DELTA → RED → local authority → EXECUTOR → GREEN
  C: FALSE_POSITIVE → close recommendation (no implementation)
  D: OUT_OF_SCOPE → durable ROUTE_TARGET_PROCESS_ID handoff

ROOT GREEN
  → INVARIANT CAPTURE
  → BOUNDED HUNT
  → RELATION CLASSIFICATION
      SAME_INVARIANT_FINDING → BRANCH FANOUT → RED/FIX/GREEN per branch
        → INTEGRATION → FAMILY GREEN → FAMILY FAN-IN → LEARNING → CLOSURE
      NEW_ROOT_CAUSE → linked case (parent family not blocked by linked case alone)
      FALSE_POSITIVE → durable rejection
      OUT_OF_SCOPE → durable handoff
      INCONCLUSIVE → family OPEN_BLOCKED
  → HUMAN_SUMMARY
  → OWNER_REVIEWS_UNCOMMITTED_GIT_DIFF
```

### BUG_EPISODE_FORK (soft — human-native)

Authority: `.cursor/pipeline/contracts/bug-episode/CLOSE_POLICY.md`.

NAVIGATE / command soft recommends use **PRIMARY** + **ALSO_OK** (still one
pipeline `NEXT_ACTION`; alternatives named explicitly):

```text
PATH_TEAM (default after GREEN / after invariant / after Owner-block exit):
  /opsx-bug-team case=<CASE_ID> mode=resume-family-fanout|continue
  — pasteable only; NO_SILENT_RETURN

PATH_SOLO_WALK (Owner wants to see code / walk chain):
  update → apply | fix-bug GO → /opsx-test verify
  → then team handback OR solo close=fixed / leave_open
  — advisory; not a violation; not framed as bypass

TASK_DELTA: CHANGED   → apply path
TASK_DELTA: UNCHANGED → fix-bug GO (apply not required)

OWNER_BLOCK (team stopped for A/B/C):
  OWNER_DECISION_REQUIRED: A|B|C
  OPTIONAL_IF_UNSURE: /opsx-explore case= finding=
  THEN_RETURN pasteable: /opsx-bug-team case= mode=…
```

Hard reminders for NAVIGATE:

- classify-first before implementation route (`blocked_needs_classify_first`)
- claim-first unchanged for `available`+`CHAT_REQUIRED=true`
- `/opsx-update` ≠ production GO; TASK_DELTA CHANGED ≠ auto apply permission
- append-only `results/ROUTE-TRACE.jsonl` + LEDGER `## ROUTE_STATE`
- `LEARNING_READY` (fanout) ≠ `FANIN_READY` / `FAMILY_FANIN_READY`
- root FANIN writer = materialize `mode=fanin_assemble` / `FAN_IN_ASSEMBLER`
- family FANIN writer = `FAMILY_FAN_IN_ASSEMBLER` only
- SAME_INVARIANT automatic fanout — MANUAL_SIBLING_RELAUNCH_REQUIRED=NO
- GRAPH is navigation snapshot — not policy SoT
- git commit / push / deploy remain FORBIDDEN under this command
- apply/update never write `closed_fixed`; GREEN → team handback default
- silent/surprise return to bug-team is a UX defect (KNOWN_FLAW)

### Three learning branches (do not mix)

1. **typing** → `/opsx-fix-types` / `/opsx-static-check` — no learning command
2. **logic/product** → `/opsx-fix-bug` → `/opsx-learn-from-bug`
   (hunter miss → prefer project-bug-hunt checklist)
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
Do **not** use `/opsx-bug-hunt` or `/opsx-project-bug-hunt` to discover
command-contract classes (F6).

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

- id: F7 FIXBUG_STATUS_READY_FOR_FIX_DEAD_END
  where: opsx-fix-bug.md claim ownership / status refusal
  symptom: |
    durable STATUS in {ready_for_fix, adjudicating, implementing, verification,
    backlog, blocked, absorbed_*, closed_*, promoted_*, duplicate_ancestor,
    duplicate_root_observation} → blocked_finding_status_not_actionable even with GO
  operator_workaround: |
    after adjudication without GO keep durable STATUS=available with
    CHAT_REQUIRED=false (known-root) or STATUS=claimed with non-empty CLAIM_TOKEN;
    do not map graph state fix_now_ready onto durable ready_for_fix
  do_not_pretend_fixed: true (as-is contract quirk)

- id: F8 CORRUPT_CLAIM_EMPTY_TOKEN
  where: opsx-claim-next-bug / opsx-fix-bug / opsx-materialize-bug-queue repair=
  symptom: STATUS=claimed + empty/absent durable CLAIM_TOKEN
  operator_workaround: |
    /opsx-materialize-bug-queue mode=update case=<CASE_ID> finding=<FINDING_ID>
    repair=mint_missing_claim_token (OWNER_CHAT set) or repair=release_corrupt_claim;
    never invent CLAIM_TOKEN inside claim-next or fix-bug
  do_not_pretend_fixed: false (repair path in contracts; now indexed in GRAPH)

- id: F9 GRAPH_MISSING_PROJECT_BUG_HUNT
  where: .cursor/pipeline/GRAPH.md (pre 2026-07-27T21:39Z UPDATE)
  symptom: NAVIGATE could not recommend primary pre-Bugbot hunter
  operator_workaround: /opsx-project-bug-hunt directly; then UPDATE GO
  do_not_pretend_fixed: false (closed by this materialization)

- id: F10 GRAPH_MISSING_PERFORMANCE
  where: .cursor/pipeline/GRAPH.md (pre 2026-07-30T04:38:13Z UPDATE)
  symptom: |
    NAVIGATE skipped /opsx-performance-review and /opsx-performance-fix;
    quality chain jumped external_call_pass→static-check only despite
    /opsx-apply soft handoff
  operator_workaround: |
    /opsx-performance-review scope=base base=<BASE> directly when trigger
    applies; FAIL → /opsx-performance-fix + packet → re-audit
  do_not_pretend_fixed: false (closed by this materialization)

- id: F11 GRAPH_MISSING_ANTIPATTERN_AND_BUG_DEBT
  where: .cursor/pipeline/GRAPH.md (pre 2026-07-30T12:17:37Z UPDATE)
  symptom: |
    NAVIGATE could not recommend /opsx-antipattern-gate or
    /opsx-bug-debt-board; soft chain jumped performance_pass→static_check
  operator_workaround: |
    /opsx-antipattern-gate base=<BASE>; spare /opsx-bug-debt-board
  do_not_pretend_fixed: false (closed by this materialization)

- id: F12 SOFT_CHAIN_CONTRACT_LAG
  where: opsx-pyright-strict-coverage.md / opsx-performance-review.md vs
    opsx-antipattern-gate.md soft position
  symptom: |
    pyright + performance-review contracts still NEXT → static without
    antipattern; antipattern contract + owner soft-chain disagree
  operator_workaround: |
    follow GRAPH soft chain (antipattern before static); later
    /opsx-admin-command-fix-command-defects on lagging contracts
  do_not_pretend_fixed: true

- id: F13 DIRTY_WORKTREE_AUDIT_TARGET
  where: opsx-pyright-strict-coverage.md /
  opsx-external-call-coverage.md / opsx-antipattern-gate.md
  symptom: |
    base...HEAD audits omitted staged, unstaged, and untracked worktree changes,
    forcing an unnecessary commit before re-audit.
  operator_workaround: |
    current contracts default omitted head= to WORKTREE; use head=working for
    explicit WORKTREE or head=<ref> for immutable ref auditing.
  do_not_pretend_fixed: false (closed by process lesson commit 8917818ef)

## Terminal / recovery

- Lifecycle terminal: `archived` (commit/PR may happen earlier)
- Bug recovery: `.opsx/runs/bug-cases/INDEX.md` pasteable NEXT_ACTION
- Same-chat `/opsx-fix-bug` GO resume: prior `COMMAND_RECEIPT` (CASE_ID / INTAKE_ID / FINDING_ID / CLAIM_TOKEN)
- Known-root skip-claim: `CHAT_REQUIRED=false` + durable `available` → fix-bug (±GO) without claim-next
- Claimable queue: `available`+`CHAT_REQUIRED=true` → claim-next first (never invent token)
- After claim: `/opsx-classify-bug case= finding=` (mandatory before impl route)
- After classify Route A: `/opsx-fix-bug` WITHOUT GO (+ claim_token when claimed)
- After classify Route B: `/opsx-update` then TASK_DELTA → `/opsx-apply` | `/opsx-fix-bug`
- After `fix_now` without GO: `/opsx-test case= finding=` (RED), not immediate production GO
- Production GO: RED_CONFIRMED | RED_NOT_APPLICABLE_APPROVED + BUG_CONFIRMED ∧ FIX_NOW
  (both `/opsx-fix-bug` GO and bug-episode `/opsx-apply`)
- GREEN: `/opsx-test … verify` only; fix-bug may re-run pytest but not write GREEN
- Durable route: `results/ROUTE-TRACE.jsonl` + LEDGER `## ROUTE_STATE`
- Fan-in: `/opsx-materialize-bug-queue mode=fanin_assemble` → `results/FANIN.md` only
- Class lesson: requires FANIN_READY; else LESSON_CANDIDATE_ONLY
- Pre-merge/review product/runtime (soft): `/opsx-project-bug-hunt` — ALSO_OK
  before merge; does **not** block `/opsx-create-pr`; Bugbot = residual
- After apply with production `.py`: soft recommend
  `/opsx-pyright-strict-coverage base=<BASE>` then
  `/opsx-external-call-coverage base=<BASE>` then conditional
  `/opsx-performance-review scope=base base=<BASE>` (when trigger applies)
  then `/opsx-antipattern-gate base=<BASE>` before `/opsx-static-check` /
  `/opsx-verify` (allowlist coverage ≠ checker PASS; external-call PASS ≠
  archive GO; performance PASS ≠ archive GO; antipattern PASS ≠ archive GO;
  kinds stay inside one audit; PG/CH FAIL → `/opsx-close-external-gap`
  packet-in, not per-dep audit commands; performance FAIL →
  `/opsx-performance-fix` then independent re-audit; antipattern FAIL →
  FIX_EXIT / re-scan)
- Bug debt: `/opsx-bug-debt-board` ALSO_OK anytime; `CLEAR` ≠ card-close;
  verify/archive are **not** residual close while debt open
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
- Uncommitted process edits after design/fix/pipeline UPDATE GO: `/opsx-admin-command-commit` (not `/opsx-commit`)- inventory_count: 58
- source_commit: f10e47efea32bb771da54f37099493b788db36f7
  UPDATE GO 2026-08-14T15:53:00Z INCREMENTAL: inventory 58 (reproduce());
  fingerprint af626a84b261b3ccf2cb9a4a48f1a554; add explicit
  ## Post-implementation verification chain section; refresh META fingerprint
  (was 55/cb7ea54d); F13/F12 unchanged.
  Prior: UPDATE GO 2026-08-09T05:34:03Z test-env + local_test_env_* (F14 closed).
- change_scaffolded: change dir exists; `owner-contract.md` written/repaired
  (`/opsx-new` CREATE or REPAIR); soft next is OCR before continue/ff
- owner_contract_under_review: `/opsx-owner-contract-review` cycle
  (`NEEDS_CONTEXT` / `NEEDS_OWNER`); not FAIL
- owner_contract_ready_for_repair: OCR `READY_FOR_REPAIR` + pasteable
  `OWNER_REVIEW_HANDOFF` for `/opsx-new` REPAIR
- owner_contract_reviewed: OCR `PASS` (soft precondition before continue/ff;
  not hard gate in continue/ff/apply/verify/supervisor v1)
- planning_package_reviewed: soft PASS from `/opsx-planning-review`
  (independent package coherence; not hard apply gate v1; READY markers
  alone insufficient — `.cursor/pipeline/contracts/PLANNING_REVIEW.md`)
- product_acceptance_required: PA kernel on
  (`.cursor/pipeline/contracts/PRODUCT_ACCEPTANCE.md`); DONE ≠ soft tooling
- product_acceptance_pass: PRODUCT_ACCEPTANCE_STATUS=PASS (or NOT_REQUIRED)
- product_acceptance_fail: PA FAIL/BLOCKED; archive blocked by pillar
- scenario_coverage_plan_ready: `/opsx-spec-scenario-coverage mode=plan`;
  **hard** when `PRODUCT_ACCEPTANCE_REQUIRED=true`; else legacy
  optional/versioned via `SCENARIO_COVERAGE_REQUIRED` alone
- impl_done: tasks complete; PRIMARY `/opsx-verify mode=impl` (VERIFY_PHASES);
  when PA required: scenario audit/certify toward product_acceptance_pass;
  then soft-recommend pyright → external-call → conditional performance-review
  when production `.py`, then antipattern-gate → `/opsx-test-env UP` (before
  destructive/FULL) → static-check → `/opsx-test-env DOWN` (after PASS) →
  `/opsx-verify mode=archive` (archive GO needs product_acceptance_pass;
  soft tooling cannot create DONE)
- impl_verified: `mode=impl` ✅ IMPL_OK (not archive-eligible)
- impl_gaps: `mode=impl` ❌ IMPL_GAPS → apply/update
- scenario_coverage_gaps: scenario audit FAIL; route TEST_ONLY to `/opsx-test`,
  PG/CH REFACTOR_AND_TEST or CERTIFY to `/opsx-close-external-gap`
- scenario_coverage_tests_authored: writer self-report; independent audit pending
- scenario_coverage_provider_ready: provider tests authored; independent
  live-ready re-audit / authorization pending
- scenario_coverage_receipt_ready: authorized provider run produced receipt;
  `/opsx-spec-scenario-coverage mode=certify`
- scenario_coverage_certified: fresh change-wide Scenario report PASS
- verify_pass: archive-eligible after `/opsx-verify mode=archive` ✅ GO
- verify_fail: back to apply/update (re-run mode=impl if DoD regressed)
- distribution_brief_ready: `/opsx-distribute-brief` produced client/CS distribution pack (soft post-archive; not a hard gate)
- command_defect_signal: Bugbot/review on process contracts
  (`.cursor/commands/**`, rules/skills/static-check, mirrors); route
  `/opsx-meta-fix-command-defects` (indexed; not product `/opsx-fix-bug`)
- process_lesson_candidate: after process FIXED / process Bugbot;
  soft `/opsx-admin-command-promote-process-lesson` (admin; not
  `/opsx-learn-from-bug`) or meta-design when DESIGN_BRIEF_READY
- local_test_env_ready: `/opsx-test-env UP` — PG:5433 + CH:8124 + Redis:6390 (compose `test_redis`) healthy
- local_test_env_stopped: `/opsx-test-env DOWN` — test compose torn down (PG+CH+Redis)
- local_test_env_degraded: PG/CH up but Redis:6390 missing (or partial health)
- local_test_env_blocked: Docker/compose/ports FAIL_CLOSED|UNAVAILABLE
### Meta / projectization / process plane
- meta_orientation: `/opsx-meta` READ_ONLY command-plane router
- bootstrap_in_progress: `/opsx-meta-bootstrap` STEP bind→meta→lifecycle→support
- projectization_required: lock ≠ COMPLETE → FAIL_CLOSED → `/opsx-projectize`
- projectization_complete: `.opsx/projectization.yaml` COMPLETE; normal commands on
- adapt_pending: `/opsx-adapt-project` read or `:GO` adapter refresh
- index_stale: central catalog index needs `/opsx-meta-update-index`
- snapshot_stale: local snapshot needs `/opsx-meta-update-snapshot`
- discovery_ready: `/opsx-meta-discover` candidates available
- import_packet_ready: `/opsx-meta-import-command` KEEP/merge in progress
- export_pack_ready: `/opsx-meta-export-pack` produced path/zip (not commit)
- process_consult: `/opsx-meta-consult` relationship/triage desk
- process_designing: `/opsx-meta-design-command` new/improve process command
- process_defect_fixing: `/opsx-meta-fix-command-defects` plan or APPLY
- chat_audit_recorded: `/opsx-meta-chat-command-audit` GO wrote `.tmp` registry
- process_dirty: process surfaces changed; need `/opsx-meta-commit`
- process_committed: process commits done
- dual_lane_commit: `/opsx-commit-all` product+process orchestration
### Evolution / devops / supervisor (side lanes)
- evolution_mapping: `/opsx-evolution` North Star / candidates
- evolution_handoff_ready: COPY_BLOCK ready → Owner new chat → new|ff|update
- devops_investigate: `/opsx-devops` INVESTIGATE (READ_ONLY)
- devops_plan_ready: DEVOPS_WRITE_PLAN from PLAN_WRITE
- devops_applied: allowlisted cluster mutate after GO
- supervisor_mission_active: `/opsx-supervisor` control-plane mission in flight
- purpose: CREATE scaffold + `owner-contract.md`, or REPAIR that file only from `OWNER_REVIEW_HANDOFF`
- input_state: change_idea | owner_contract_ready_for_repair
- artifacts_read: openspec status/instructions; optional EVOLUTION/EXPLORE handoffs; REPAIR requires `OWNER_REVIEW_HANDOFF`
- artifacts_written: CREATE change scaffold + owner-contract.md; REPAIR only owner-contract.md
- decision_owner: operator (sole writer of owner-contract.md; never emits OCR PASS)
- next_typical: /opsx-owner-contract-review change=<name> (soft; CREATE and after REPAIR)
- known_flaws: soft OCR only (not hard gate); ALSO_OK skip to continue/ff allowed
### /opsx-owner-contract-review
- purpose: READ_ONLY interactive semantic review of owner-contract.md; Owner dialog; emit OWNER_REVIEW_HANDOFF for /opsx-new REPAIR
- input_state: change_scaffolded | owner_contract_under_review | owner_contract_ready_for_repair
- output_state: owner_contract_under_review | owner_contract_ready_for_repair | owner_contract_reviewed
- artifacts_read: owner-contract.md; optional EVOLUTION_HANDOFF / EXPLORE_HANDOFF / prior OWNER_REVIEW_HANDOFF; bounded specs/decisions
- artifacts_written: none (FILES_CHANGED: none)
- decision_owner: Owner (semantics); reviewer (diagnosis + handoff only)
- next_typical: Owner supplies context/answers | /opsx-new + OWNER_REVIEW_HANDOFF (READY_FOR_REPAIR) | /opsx-continue | /opsx-ff (PASS, soft)
- known_flaws: soft recommend only v1 (not hard gate in continue/ff/apply/verify/supervisor)
- input_state: change_scaffolded | owner_contract_reviewed | artifacts_in_progress
- next_typical: /opsx-owner-contract-review (if OCR not PASS; soft) | /opsx-continue | /opsx-planning-review (when applyRequires complete) | /opsx-apply (ALSO_OK soft skip)
- known_flaws: OCR soft precondition may be skipped; NOT_OPENED_BUDGET deep body beyond grep
- input_state: change_idea | change_scaffolded | owner_contract_reviewed
- next_typical: /opsx-owner-contract-review (if OCR not PASS after new; soft) | /opsx-planning-review | /opsx-apply (ALSO_OK soft skip)
- known_flaws: OCR soft precondition may be skipped; NOT_OPENED_BUDGET deep body beyond grep
### /opsx-planning-review
- purpose: READ_ONLY independent coherence review of finished planning package before apply
- input_state: apply_ready | planning_revise
- output_state: planning_package_reviewed | planning_revise | apply_ready
- artifacts_read: owner-contract, proposal, decisions, design, specs, tasks, scenario plan evidence; PLANNING_REVIEW.md
- artifacts_written: none (FILES_CHANGED: none)
- decision_owner: verifier only (Owner for NEEDS_OWNER product forks)
- next_typical: /opsx-apply (on PASS) | /opsx-update + PLANNING_REVIEW_HANDOFF (on REPAIR_REQUIRED) | Owner question (NEEDS_OWNER)
- known_flaws: soft recommend only in v1 (not hard apply gate); earlier hop is /opsx-owner-contract-review (Owner Contract only), not this command
- purpose: revise existing planning artifacts coherently; on bug-episode spec route emit TASK_DELTA; consume PLANNING_REVIEW_HANDOFF (REPAIR_PLANNING_PACKAGE); owner-contract text repair stays /opsx-owner-contract-review + /opsx-new
- artifacts_read: change planning artifacts; optional case ROUTE_STATE; optional PLANNING_REVIEW_HANDOFF
- next_typical: /opsx-planning-review (after REPAIR_PLANNING_PACKAGE) | /opsx-apply (TASK_DELTA CHANGED) | /opsx-fix-bug GO path (TASK_DELTA UNCHANGED) | /opsx-bug-team handback (SECONDARY) | /opsx-continue | /opsx-owner-contract-review (owner-contract semantic path)
- input_state: apply_ready | planning_package_reviewed | implementing | verify_fail | task_delta_changed | production_go_ready
- known_flaws: soft recommend after apply (not hard archive gate); tests/** out of policy; bug-episode must not treat OpenSpec verify as card close; never silent team return; apply soft handoff may omit antipattern (F12 / NOT_OPENED_BUDGET); planning-review soft preflight only (v1, not hard gate)
- purpose: audit base..head production Python ⊆ pyrightconfig_strict.json include (not exclude)
- artifacts_read: git diff base...head; pyrightconfig_strict.json
- known_flaws: soft recommend after apply (not hard archive gate); tests/** out of policy; contract NEXT may lag antipattern insert (F12)
- purpose: audit base..head production external-call surfaces (HTTP/WB/PG/CH/Redis/…) ↔ adequate tests per testing-rules
- artifacts_read: git diff base...head; app/**; tests/**; testing-rules.mdc; optional EXTERNAL_CALL_COVERAGE_REPORT / change artifacts
- known_flaws: soft recommend (not hard archive gate alone); kind taxonomy inside one command (no per-dep audit front-doors); PG/CH require live integration; NEXT rules beyond opened budget may lag antipattern (F12)
### /opsx-spec-scenario-coverage
- purpose: change-wide Spec Scenario plan/audit/certification; maps every
  Scenario to scenario-seam, stub-contract and required provider evidence
- cli: required `mode=plan|audit|certify` + `change=`; fail-closed Arg gate
  (no silent default mode)
- input_state: apply_ready | scenario_coverage_plan_ready | impl_done |
  scenario_coverage_gaps | scenario_coverage_tests_authored |
  scenario_coverage_receipt_ready
- output_state: scenario_coverage_plan_ready | scenario_coverage_gaps |
  scenario_coverage_provider_ready | scenario_coverage_certified | blocked
- artifacts_read: change delta specs/design/tasks; code/tests; optional
  TEST_COVERAGE_PACKET; provider receipts; test-evidence taxonomy
- artifacts_written: `mode=plan` ONLY may write Change-local durable plan
  evidence under `openspec/changes/<id>/scenario-coverage/plan.md` +
  `plan.receipt.json` (see `SCENARIO_TEST_COVERAGE.md` DURABLE_PLAN_EVIDENCE);
  audit/certify reports remain chat (+ `.tmp` provider receipts); never
  product design/spec/tasks
- decision_owner: independent Scenario coverage auditor; not test/seam writer;
  archive remains `/opsx-verify`
- next_typical: `/opsx-apply` after `mode=plan` | `/opsx-test` with
  SCENARIO_TEST_ONLY_PACKET | `/opsx-close-external-gap` with Scenario
  REFACTOR/CERTIFY packet | `/opsx-verify` after `mode=certify` PASS
- known_flaws: durable plan/report persistence still chat-output in v1
  (receipts may live under `.opsx/runs/scenario-coverage/`); archive activation
  via `SCENARIO_COVERAGE_REQUIRED` **and** forced when
  `PRODUCT_ACCEPTANCE_REQUIRED=true` (legacy opt-out alone cannot waive PA)
- purpose: diff-scoped antipattern over-report (`base...head`); optional practice ledger via `accept|reject` + GO
- artifacts_read: git diff base...head; catalog; PRACTICE_LEDGER.jsonl; optional change context
- next_typical: /opsx-test-env UP (before FULL/destructive) | /opsx-static-check (unit-only/FAST or env already ready) | FIX_EXIT / re-scan (FAIL) | /opsx-verify
- known_flaws: soft gate (not hard archive); over-report intentional; MATCHES_ACCEPTED_PRACTICE ≠ testing-rules proof; contract may still omit test-env (F13)
- purpose: REFACTOR_AND_TEST closure for PG/CH gaps (minimal seam + provider
  integration) and authorized provider execution receipt; no base=
- input_state: external_call_gaps | scenario_coverage_gaps |
  scenario_coverage_provider_ready
- output_state: external_gap_closed | external_gap_closing |
  external_call_gaps | tests_authored | implementing |
  scenario_coverage_tests_authored | scenario_coverage_receipt_ready
- artifacts_read: pasted ECC or Scenario packets; testing-rules; ContractCase;
  gap PATH symbols
- artifacts_written: minimal app/** seam + tests/integration/** when
  REFACTOR_AND_TEST; provider receipt only after authorized run
- decision_owner: closure writer; TEST_ONLY redirects to /opsx-test; oversized
  seam → /opsx-apply; never owns Scenario coverage PASS
- next_typical: ECC focused re-audit | `/opsx-spec-scenario-coverage mode=audit`
  after authorship | `mode=certify` after receipt | `/opsx-test` | `/opsx-apply`
- known_flaws: must not accept base=; session-mock unit ≠ CLOSED for PG/CH;
  provider receipt ≠ final Scenario certification; pasteable only when
  ECC/Scenario packet fence is already in chat evidence — never
  `<paste that packet>` stubs from NAVIGATE
  F6: does not own process-contract defects → `/opsx-meta-fix-command-defects`;
- purpose: phased read-only audit (VERIFY_PHASES: mode=impl DoD | mode=archive gate);
  sole archive DONE consumer for Product Acceptance
- input_state: impl_done | static_check_done | impl_verified |
  product_acceptance_required | scenario_coverage_certified
- output_state: impl_verified | impl_gaps | product_acceptance_pass |
  product_acceptance_fail | verify_pass | verify_fail
- artifacts_read: change artifacts, code, VERIFY_PHASES, VERIFY_POLICY,
  PRODUCT_ACCEPTANCE, SEMANTIC_WRITE_TARGET, scenario report when applicable
- next_typical: /opsx-pyright-strict-coverage (after IMPL_OK+prod.py) | /opsx-static-check FULL CACHE_OFF (when prior FULL was cache-dev) | /opsx-verify mode=archive | /opsx-archive (after GO+PA) | /opsx-apply | /opsx-update | /opsx-spec-scenario-coverage (PA LIFECYCLE fail)
- known_flaws: bare /opsx-verify defaults archive (WARN); ≠ /opsx-test verify; archive soft WARN if last FULL CACHE_MODE=dev; soft tooling still advisory vs PA
- input_state: verify_pass | product_acceptance_pass
- artifacts_read: change + decisions to promote; PA status from archive verify
- next_typical: none | /opsx-distribute-brief | /opsx-commit | /opsx-create-pr
- known_flaws: NOT_OPENED_BUDGET detail; distribute-brief is soft suggest only
### /opsx-distribute-brief
- purpose: full completed-change description for client/CS distribution materials
- input_state: archived | verify_pass
- output_state: distribution_brief_ready
- artifacts_read: change proposal/design/tasks/specs (+ optional PR/commits)
- artifacts_written: optional DISTRIBUTION_BRIEF.md (archive root or .tmp)
- decision_owner: brief author (unevidenced claims → OWNER_DECISION / DO_NOT_PROMISE)
- next_typical: none (human adapts brief outside OPSX)
- known_flaws: verify_pass entry must stay DRAFT_BRIEF; not a hard archive gate
- input_state: tests_authored | static_check_done | local_test_env_degraded | local_test_env_blocked
- next_typical: /opsx-test-env UP (FLAKY_OR_ENV / connection refused) | /opsx-fix-types | /opsx-test
- known_flaws: NOT_OPENED_BUDGET detail; may omit test-env hint until companions (F13)
### /opsx-test-env
- purpose: laptop test compose UP (default) / DOWN / PROBE before destructive/full pytest
- input_state: antipattern_pass | antipattern_suspects | before_destructive_tests | static_check_done | local_test_env_degraded | local_test_env_blocked | local_test_env_stopped
- output_state: local_test_env_ready | local_test_env_stopped | local_test_env_degraded | local_test_env_blocked
- artifacts_read: tests/docker-compose.test.yml; env.sample (flag names only)
- artifacts_written: none in git; docker compose project for test file only
- decision_owner: test-env operator (LOCAL_TEST_ENV_STATUS only; not verify/archive)
- next_typical: /opsx-static-check FULL (after UP) | /opsx-test (destructive) | /opsx-test-env DOWN (after PASS) | /opsx-test-triage
- known_flaws: must use REDIS_PORT=6390 for pytest against compose Redis (host :6379 out of scope); not k8s (/opsx-devops); companion NEXT lag F13 partially closed by D4–D5
- input_state: implementing | impl_done | antipattern_pass | antipattern_suspects | local_test_env_ready | local_test_env_degraded | performance_pass | external_call_pass | static_check_done
- next_typical: /opsx-test-env DOWN (after FULL PASS; advisory) | /opsx-test-env UP (env-class FAIL) | one pasteable NEXT_ACTION from synthesis | /opsx-verify
- known_flaws: PREFLIGHT=tooling files only (not docker services); may omit test-env NEXT until companions (F13)
- purpose: atomic local commits for product/code/OpenSpec/docs
- next_typical: /opsx-project-bug-hunt | /opsx-create-pr | /opsx-admin-command-commit (process only; admin off-graph)
- purpose: open a pull request; product/runtime requires PROJECT_BUG_HUNT_RECEIPT unless OVERRIDE_SKIP_PROJECT_BUG_HUNT or docs/process-only; after successful gh pr create emit dual-channel BUGBOT_POST_PR — cursor_task (one Cursor Task bugbot, Diff branch changes, Base=PR base) plus bounded github_cursor_bot fetch of PR comments from cursor[bot] (pending≠zero; thin Task empty envelope=incomplete); escape SKIP_BUGBOT_POST_PR skips both; does not replace project-bug-hunt; does not auto-fix
- artifacts_read: commits/diff vs base; optional PROJECT_BUG_HUNT_RECEIPT; post-create gh PR cursor[bot] comments (bounded)
- artifacts_written: remote PR (via gh); chat dual-channel BUGBOT_POST_PR report
- next_typical: none | /opsx-project-bug-hunt (if receipt gate blocks) | residual Bugbot findings → intake/learn path if product/logic
- known_flaws: receipt gate is command-owned (not soft graph advice); cursor_task ≠ GitHub cursor[bot] — must not collapse channels into one silent zero; bounded fetch ≠ unbounded CI wait
### /opsx-propose
- purpose: scaffold change + generate applyRequires artifacts in one invoke (on disk; Owner wants indexed)
- output_state: apply_ready | change_scaffolded | planning_revise
- artifacts_read: openspec status/instructions; decisions context-first
- artifacts_written: change dir + proposal/design/tasks (when live path runs)
- next_typical: /opsx-apply | /opsx-new | /opsx-ff | /opsx-update
  contract body may still print OBSOLETE redirect (companion lag); graph
  indexes and may recommend; F5 graph-exclusion closed by Owner 2026-08-11;
  live semantics vs redirect = command contract authority until meta-fix
### /opsx-meta
- purpose: READ_ONLY orientation for `/opsx-meta-*` command plane → one NEXT_ACTION
- input_state: any | meta_orientation
- output_state: meta_orientation | projectization_required | bootstrap_in_progress | process_dirty | discovery_ready | index_stale | snapshot_stale
- artifacts_read: `.opsx/projectization.yaml`; snapshot/index freshness signals; pending `.tmp/opsx-*` ids only
- decision_owner: router
- next_typical: /opsx-meta-bootstrap | /opsx-projectize | /opsx-meta-commit | /opsx-meta-consult | /opsx-meta-discover | /opsx-meta-fix-command-defects
- known_flaws: NOT_OPENED_BUDGET deep routing table; F15 admin↔meta name remap in sibling prose
### /opsx-meta-bootstrap
- purpose: first-contact seed/bind OPSX; bare GO = one STEP (bind→meta→lifecycle→support); STEP=all opt-in; SAVE = central lessons
- input_state: change_idea | empty/partial `.opsx` | bootstrap_in_progress
- output_state: bootstrap_in_progress | projectization_required
- artifacts_read: central profile; `.opsx/runs/bootstrap/**`; ephemeral `.tmp/opsx-bootstrap/**`; local `.opsx/**`
- artifacts_written: staged bootstrap surfaces under allowlist; no product openspec wipe; no auto projectize:GO
- decision_owner: bootstrap operator (GO/SAVE exclusive)
- next_typical: /opsx-projectize | /opsx-meta-bootstrap GO (next STEP)
- known_flaws: contract_id still GAME-named; poetry remap via projectize
### /opsx-projectize
- purpose: projectize bootstrap/import for WB Sky/Poetry; `:GO` sets COMPLETE; forbid product openspec wipe
- input_state: projectization_required | bootstrap_in_progress
- output_state: projectization_complete | projectization_required
- artifacts_read: imported/raw/bootstrap surfaces; `pyproject.toml`; adapters
- artifacts_written: with `:GO` — `.opsx/**` activation/adapters/`projectization.yaml`; never `app/**`
- decision_owner: Owner `:GO`
- next_typical: /opsx-meta | /opsx-meta-import-command | /opsx-adapt-project
- known_flaws: second `:GO` without Owner reset fail-closed
### /opsx-adapt-project
- purpose: adapter/capability refresh after COMPLETE; read-only or `:GO`; not foreign command merge
- input_state: projectization_complete | adapt_pending
- output_state: adapt_pending | projectization_complete | process_dirty
- artifacts_read: `.opsx/adapters/**`; capability probes
- artifacts_written: with `:GO` adapter/project docs only
- decision_owner: Owner `:GO`
- next_typical: /opsx-meta-commit | /opsx-meta
### /opsx-meta-update-index
- purpose: plan/apply central catalog index refresh
- input_state: meta_orientation | index_stale | discovery_ready
- output_state: index_stale | discovery_ready | meta_orientation
- artifacts_read: central catalog tools / local index
- artifacts_written: index apply only with explicit apply mode per contract
- decision_owner: index operator
- next_typical: /opsx-meta-discover | /opsx-meta
### /opsx-meta-update-snapshot
- purpose: refresh local OPSX snapshot freshness after process commits / drift
- input_state: meta_orientation | snapshot_stale | process_committed
- output_state: snapshot_stale | meta_orientation
- artifacts_read: sources.yaml / snapshot inputs
- artifacts_written: local snapshot artifacts per contract
- decision_owner: snapshot operator
- next_typical: /opsx-meta | /opsx-meta-discover
### /opsx-meta-discover
- purpose: READ_ONLY what central catalog may help this repo
- input_state: meta_orientation | discovery_ready | index_stale
- output_state: discovery_ready | index_stale
- artifacts_read: central index
- decision_owner: discoverer
- next_typical: /opsx-meta-import-command OCCURRENCE=<id> | /opsx-meta-update-index | /opsx-meta
- known_flaws: NOT_OPENED_BUDGET detail; BLOCKED_NEEDS_FRESH_INDEX → update-index
### /opsx-meta-import-command
- purpose: sole command-import owner (index default / raw donor); KEEP-gated materialize
- input_state: discovery_ready | import_packet_ready | projectization_complete
- output_state: import_packet_ready | process_dirty | projectization_required
- artifacts_read: index OCCURRENCE / ADOPTION_PACKET / donor path; staging `.opsx/runs/inbound/**`
- artifacts_written: selected command packet + companions under allowlist (GO)
- decision_owner: Owner KEEP set + GO
- next_typical: /opsx-meta-commit | /opsx-adapt-project | /opsx-projectize | /opsx-meta-bootstrap
- known_flaws: NOT_OPENED_BUDGET deep KEEP matrix; no foreign product openspec import
### /opsx-meta-export-pack
- purpose: export BOOTSTRAP_PROFILE / process pack for peers; zip out of meta-commit scope
- input_state: projectization_complete | meta_orientation | process_consult
- output_state: export_pack_ready
- artifacts_read: local process surfaces / profile
- artifacts_written: export folder/zip under contract paths (not git commit by default)
- decision_owner: exporter
- next_typical: human path | peer `/opsx-meta-bootstrap` | peer `/opsx-meta-import-command` | /opsx-meta
- known_flaws: NOT_OPENED_BUDGET detail; do not confuse with `/opsx-archive`
### /opsx-meta-consult
- purpose: READ_ONLY process desk — relationships, triage, one pasteable next
- input_state: any | process_consult | command_defect_signal
- output_state: process_consult | process_defect_fixing | process_designing | meta_orientation
- artifacts_read: cited `/opsx-*` contracts; GRAPH/META read-only
- decision_owner: consult desk
- next_typical: /opsx-meta-fix-command-defects | /opsx-meta-design-command | /opsx-pipeline | /opsx-meta-commit | /opsx-fix-types | /opsx-fix-bug
- known_flaws: F15 — emits `/opsx-meta-*`; residual admin names may appear in upstream snapshots
### /opsx-meta-design-command
- purpose: design new/improved process command; GO may create NEW files only; committed IMPROVE → fix-defects
- input_state: process_consult | process_designing | process_lesson_candidate
- output_state: process_designing | process_dirty | process_defect_fixing
- artifacts_read: ecosystem commands; design packet
- artifacts_written: new command files after Owner GO OPTION_*; not committed-path IMPROVE
- decision_owner: designer + Owner GO
- next_typical: /opsx-meta-commit | /opsx-meta-fix-command-defects | /opsx-meta-import-command | /opsx-meta-update-index
- known_flaws: NOT_OPENED_BUDGET phase detail; F15 name remap
### /opsx-meta-fix-command-defects
- purpose: plan (READ_ONLY) or APPLY (GO) process-contract defects only; never product; never commit
- input_state: command_defect_signal | process_defect_fixing | process_consult | chat_audit_recorded
- output_state: process_defect_fixing | process_dirty
- artifacts_read: FIX_PLAN_READY / listed process paths
- artifacts_written: listed `.cursor/commands|rules|skills|…` only with GO
- decision_owner: fixer + Owner GO / AUTHORIZE_COMMAND_FIX
- next_typical: /opsx-meta-commit | /opsx-meta-consult | /opsx-pipeline UPDATE
- known_flaws: none recorded beyond F6 routing history
### /opsx-meta-chat-command-audit
- purpose: walk this-repo agent chats via `.tmp/opsx-chat-audit`; GO writes registry only; handoff fix/design
- input_state: meta_orientation | process_consult | after messy commit-all/evolution
- output_state: chat_audit_recorded | process_defect_fixing | process_designing
- artifacts_read: agent transcripts (READ_ONLY); registry
- artifacts_written: `.tmp/opsx-chat-audit/**` only with GO
- decision_owner: auditor
- next_typical: /opsx-meta-fix-command-defects | /opsx-meta-design-command | /opsx-meta-consult | /opsx-meta-commit
- known_flaws: NOT_OPENED_BUDGET detail; never APPLY contracts here
### /opsx-meta-commit
- purpose: sole process-commit front-door (allowlist `.opsx/sources.yaml`); default current-chat; `ALL` cleanup
- input_state: process_dirty | process_committed
- output_state: process_committed | process_dirty | snapshot_stale
- artifacts_read: git status/diff; sources.yaml allowlist
- artifacts_written: local git commits (process scope only); never push/PR
- decision_owner: committer (GO required)
- next_typical: /opsx-meta | /opsx-meta-update-snapshot | /opsx-create-pr | /opsx-commit-all
- known_flaws: admin-command-commit is thin redirect; prefer this name
### /opsx-commit-all
- purpose: orchestrate `/opsx-commit` + `/opsx-meta-commit` (parallel plan Tasks → serial child GO)
- input_state: product_dirty | process_dirty | dual_lane_commit
- output_state: dual_lane_commit | pr_ready | process_committed | product_dirty
- artifacts_read: child contracts; git status
- artifacts_written: none directly — children commit; SUMMARY only
- decision_owner: orchestrator (Owner GO / ALL GO)
- next_typical: /opsx-create-pr | /opsx-static-check FULL (if product blocked) | re-run failed child
- known_flaws: NOT_OPENED_BUDGET orchestration detail; does not launch static-check itself
### /opsx-evolution
- purpose: North Star registry + CHANGE_CANDIDATES + COPY_BLOCK handoff to Owner-chosen new|ff|update
- input_state: change_idea | planning_revise | evolution_mapping
- output_state: evolution_mapping | evolution_handoff_ready
- artifacts_read: `openspec/evolution/**`; EVOLUTION_POLICY; optional WORKLOG peek
- artifacts_written: star cards/index only with accepted draft + GO
- decision_owner: Owner pick + GO for persistence
- next_typical: Owner new chat → /opsx-new | /opsx-ff | /opsx-update
- known_flaws: NOT_OPENED_BUDGET deep STAR_ROUTE; must not auto-invoke downstream `/opsx-*`
### /opsx-devops
- purpose: k8s/infra side-lane; INVESTIGATE → PLAN_WRITE → GO allowlisted mutate; OPS_STATE memory
- input_state: any (side-lane) | devops_investigate | devops_plan_ready
- output_state: devops_investigate | devops_plan_ready | devops_applied
- artifacts_read: `.cursor/rules/devops.mdc`; `k8s/**`; `.cursor/devops/OPS_STATE.md`
- artifacts_written: OPS_STATE/LAST.json; cluster only under GO + allowlisted plan
- decision_owner: devops operator + Owner GO
- next_typical: none | re-invoke | REDIRECT_PRODUCT → /opsx-fix-bug
- known_flaws: not hard core-lifecycle edge; not laptop test-env; CSI apply forbidden
### /opsx-supervisor
- purpose: control-plane orchestrator; free-text DAG **or** BUG_MISSION sequential multi-finding reducer; dispatches `/opsx-*` via subagents; no direct repo tools
- input_state: any Owner free-text | supervisor_mission_active | durable bug case (BUG_MISSION)
- output_state: supervisor_mission_active | mission terminal | MISSION_COMPLETE (all findings terminal)
- artifacts_read: none directly (FORBIDDEN); workers return ROUTE_TRANSITION envelopes
- artifacts_written: none directly; mission ledger in chat; prefer ROUTE-TRACE supervisor_transition via workers
- decision_owner: supervisor control-plane + SUPERVISOR_POLICY; route authority = worker envelopes / ORCHESTRATION_MVP (not explore planner in BUG_MISSION)
- next_typical: BUG_MISSION → claim → classify → envelope NEXT_COMMAND …; free-text → mediated /opsx-explore then DAG workers
- known_flaws: F16 allowlist may lag for new soft-chain nodes; not GRAPH authority; not direct git/pytest; live PLANFIT regression needs durable case on disk
### Scope-excluded (not Commands; not inventory)
- opsx-admin-command-* / opsx-execution-preflight / opsx-source-resolution / opsx-pipeline
- `.cursor/opsx-review-commands` (admin review surface)
change_scaffolded --/opsx-owner-contract-review [soft recommend]--> owner_contract_under_review|owner_contract_ready_for_repair|owner_contract_reviewed
owner_contract_under_review --Owner context/answers + /opsx-owner-contract-review--> owner_contract_under_review|owner_contract_ready_for_repair|owner_contract_reviewed
owner_contract_ready_for_repair --/opsx-new [REPAIR + OWNER_REVIEW_HANDOFF]--> change_scaffolded
change_scaffolded --/opsx-new [REPAIR]--> change_scaffolded
owner_contract_reviewed --/opsx-continue|/opsx-ff [recommended]--> artifacts_in_progress|apply_ready
change_scaffolded --/opsx-continue [ALSO_OK skip OCR]--> artifacts_in_progress|apply_ready
change_scaffolded --/opsx-ff [ALSO_OK skip OCR]--> apply_ready
apply_ready --/opsx-planning-review [soft recommend]--> planning_package_reviewed|planning_revise|apply_ready
planning_package_reviewed --/opsx-apply--> implementing|impl_done
apply_ready --/opsx-apply [ALSO_OK soft skip]--> implementing|impl_done
planning_revise --/opsx-update [PLANNING_REVIEW_HANDOFF]--> apply_ready|planning_revise
antipattern_pass|antipattern_suspects --/opsx-test-env UP--> local_test_env_ready|local_test_env_degraded|local_test_env_blocked
local_test_env_ready --/opsx-static-check FULL--> static_check_done
local_test_env_degraded --/opsx-test-env UP--> local_test_env_ready|local_test_env_degraded|local_test_env_blocked
local_test_env_blocked --/opsx-test-env UP--> local_test_env_ready|local_test_env_degraded|local_test_env_blocked
# demoted for FULL/destructive when env not ready (unit-only / FAST / skip env OK):
antipattern_pass|antipattern_suspects --/opsx-static-check [unit-only/FAST / env skip]--> static_check_done
static_check_done --/opsx-test-env DOWN [after FULL PASS; advisory]--> local_test_env_stopped
impl_done --/opsx-verify mode=impl--> impl_verified|impl_gaps
impl_gaps --/opsx-apply|/opsx-update--> implementing|planning_revise
impl_verified --/opsx-pyright-strict-coverage--> coverage_pass|coverage_gaps
impl_verified --/opsx-verify mode=archive--> verify_pass|verify_fail
static_check_done --/opsx-static-check FULL CACHE_OFF [recommended when prior FULL was cache-dev]--> static_check_done
static_check_done --/opsx-verify mode=archive [soft WARN if last FULL CACHE_MODE=dev]--> verify_pass|verify_fail
impl_done --/opsx-verify mode=archive [legacy/skip-impl WARN]--> verify_pass|verify_fail
archived --/opsx-distribute-brief--> distribution_brief_ready
verify_pass --/opsx-distribute-brief [DRAFT only]--> distribution_brief_ready
product_dirty --/opsx-commit--> pr_ready
implementing|impl_done|coverage_pass|external_call_pass|performance_pass|antipattern_pass|antipattern_suspects|local_test_env_ready --/opsx-static-check--> static_check_done
# propose (indexed; contract may still redirect — command authority wins)
change_idea --/opsx-propose--> apply_ready|change_scaffolded|planning_revise
# meta / projectization plane
* --/opsx-meta--> meta_orientation
meta_orientation --/opsx-meta-bootstrap--> bootstrap_in_progress|projectization_required
bootstrap_in_progress --/opsx-projectize|:GO--> projectization_complete|projectization_required
projectization_required --/opsx-projectize:GO--> projectization_complete
projectization_complete --/opsx-adapt-project|:GO--> adapt_pending|projectization_complete|process_dirty
meta_orientation --/opsx-meta-update-index--> index_stale|discovery_ready|meta_orientation
meta_orientation|process_committed --/opsx-meta-update-snapshot--> snapshot_stale|meta_orientation
meta_orientation|index_stale --/opsx-meta-discover--> discovery_ready|index_stale
discovery_ready --/opsx-meta-import-command--> import_packet_ready|process_dirty|projectization_required
* --/opsx-meta-export-pack--> export_pack_ready
* --/opsx-meta-consult--> process_consult
process_consult --/opsx-meta-fix-command-defects--> process_defect_fixing|process_dirty
process_consult --/opsx-meta-design-command--> process_designing|process_dirty
command_defect_signal --/opsx-meta-fix-command-defects--> process_defect_fixing|process_dirty
process_dirty --/opsx-meta-commit--> process_committed|snapshot_stale
product_dirty|process_dirty --/opsx-commit-all--> dual_lane_commit|pr_ready|process_committed|product_dirty
* --/opsx-meta-chat-command-audit--> chat_audit_recorded|process_defect_fixing
# evolution / devops / supervisor (side / soft)
change_idea|planning_revise --/opsx-evolution--> evolution_mapping|evolution_handoff_ready
evolution_handoff_ready --Owner /opsx-new|/opsx-ff|/opsx-update--> change_scaffolded|apply_ready|planning_revise
* --/opsx-devops--> devops_investigate|devops_plan_ready|devops_applied
* --/opsx-supervisor--> supervisor_mission_active
# process lesson (admin remains soft/off-graph edge; recorded for orientation)
# process_dirty|FIXED --/opsx-admin-command-promote-process-lesson--> process_lesson_candidate
# process_lesson_candidate --DESIGN_BRIEF_READY--> /opsx-admin-command-design-command|/opsx-meta-design-command
# process_lesson_candidate --EXTEND_EXISTING--> /opsx-meta-fix-command-defects
`/opsx-antipattern-gate`, `/opsx-test-env UP` (FULL), `/opsx-static-check`,
and `/opsx-verify`.
`/opsx-performance-review`, `/opsx-antipattern-gate`, `/opsx-test-env UP`
(FULL), `/opsx-static-check`, and `/opsx-verify`. One command covers
HTTP/WB/PG/CH/Redis/OTHER via kind
### Scenario coverage → close-external-gap (packet provenance)
When PA LIFECYCLE / `SCENARIO_COVERAGE_REQUIRED` needs Scenario
REFACTOR_AND_TEST or CERTIFY provider work:
1. PRIMARY `NEXT_ACTION` = packet-producing hop for position
   (`/opsx-spec-scenario-coverage mode=plan|audit|certify` as required) —
   must be executable now with filled `change=` / `mode=`.
2. `/opsx-close-external-gap` is **not** current hop until
   `ROUTE_PACKETS` / `SCENARIO_REFACTOR_AND_TEST_PACKET` /
   `SCENARIO_CERTIFY_PACKET` fence exists in chat (or durable receipt path
   the consumer accepts). NAVIGATE must put the consumer only in
   sequenced `ALSO_OK` / `DO_NOT_DO_YET`
   (“after audit returns ROUTE_PACKETS, paste that fence into
   `/opsx-close-external-gap`”), never as `NEXT_ACTION` with
   `<paste that packet>`.
3. Emit `LOCAL_HOP_COPY_BLOCK` for the PRIMARY command only.
`/opsx-antipattern-gate` then `/opsx-test-env UP` (FULL) then
`/opsx-static-check`. Not every-diff mandatory. `FAIL` →
`/opsx-performance-fix` + FIX_PACKET → independent re-audit via review
(fixer self-report is never PASS). Measurement only under
`READY_FOR_ONE_AUTHORIZED_PERFORMANCE_RUN` inside fix — there is no
`/opsx-antipattern-gate base=<BASE>` before `/opsx-test-env UP` (when
FULL/destructive follows) then `/opsx-static-check` / `/opsx-verify`.
Over-report by design. `PASS|PASS_WITH_SUSPECTS` → test-env UP (FULL) or
static FAST/unit-only. `FAIL` → FIX_EXIT / re-scan; soft-block static until
Owner continues. Soft recommend — not a hard archive gate. Optional
practice ledger: `accept=` / `reject=` + GO.
### Local test env (before destructive / pytest-full)
After antipattern `PASS|PASS_WITH_SUSPECTS` (or when about to run
pytest-full / live PG|CH): soft recommend `/opsx-test-env UP` before
`/opsx-static-check FULL`. On connection refused / `FLAKY_OR_ENV` for
`5433`|`8124`|`6390`: paste `/opsx-test-env UP` (session `REDIS_PORT=6390`).
After FULL `PASS`: recommend `/opsx-test-env DOWN` to free resources
(including compose Redis). Not a hard archive gate. Unit-only / FAST may
skip. Does **not** replace static-check `PREFLIGHT` (tooling files only).
Not `/opsx-devops` (k8s). Compose owns Redis on host **6390** (never bind
host **6379** from `tests/docker-compose.test.yml`). Companion lag F13
closed for ports/Supervisor when D4–D5 applied.
Destructive execution default (all entry points that select
`destructive_local`): `CACHE_MODE=dev` via
`.cursor/static-check/contracts/destructive-selective-cache.md` — run
fingerprint `MUST_RUN` only. **INTERIM** (planner missing):
`CACHE_DEGRADED` = run-all destructive; no improvised skips.
Archive / pre-PR confidence → `/opsx-static-check FULL CACHE_OFF`
(or `CACHE_FORCE`). `/opsx-verify mode=archive` soft-WARNs if last FULL
was cache-dev. `CACHE_HIT` ≠ archive EXECUTED green. `authorized_live`
remains out of this cache.
### Pre-Bugbot primary hunt
Before `/opsx-create-pr` on product/runtime diffs: `/opsx-project-bug-hunt
base=<PR-base> head=<branch>`. Bugbot PR section = residual only.
3. **commands/process (F6)** → `/opsx-meta-fix-command-defects`
### Process-surface git conflicts (admin path — soft)
When merge/rebase leaves unmerged paths on process surfaces
(`.cursor/commands/**`, rules, skills, static-check, mirrors, …):
1. `/opsx-admin-command-resolve-conflicts` (plan, then Owner `GO`).
2. Then `/opsx-meta-commit` if ordinary process dirt remains
   (`/opsx-admin-command-commit` = obsolete alias only).
3. If merge created dual-authority / broken handoff →
   `/opsx-meta-fix-command-defects`.
Do **not** use `/opsx-meta-commit` (or obsolete `/opsx-admin-command-commit`)
or `/opsx-create-pr` while unmerged paths remain. Do **not** silent
`-X ours/theirs` on authority tokens. Prevention: avoid dual long-lived
edits of the same process file; serialize shared contracts before consumers.
- id: F5 PROPOSE_GRAPH_EXCLUSION
  where: opsx-propose.md + prior GRAPH exclusion
    historically excluded from GRAPH as obsolescent; contract body may still
    print OBSOLETE redirect while Owner wants propose indexed/recommendable
    graph indexes `/opsx-propose`; if contract redirects, follow redirect or
    `/opsx-meta-fix-command-defects` to restore live propose semantics
  do_not_pretend_fixed: false (graph-exclusion closed 2026-08-11 UPDATE GO;
    companion contract lag may remain)
    treat as `command_defect_signal`; `/opsx-meta-fix-command-defects`
    /opsx-meta-fix-command-defects on lagging contracts
- id: F13 TEST_ENV_COMPANION_LAG
  where: opsx-static-check.md PREFLIGHT / synthesis; opsx-supervisor.md
    allowlist; opsx-test.md; opsx-antipattern-gate.md NEXT prose
    /opsx-test-env exists and GRAPH indexes compose Redis :6390, but some
    sibling contracts may still jump antipattern→static FULL without UP;
    env fails look like product FAIL; Supervisor may omit /opsx-test-env
    until allowlist includes it (see F16 / D4)
    /opsx-test-env UP (REDIS_PORT=6390) then /opsx-static-check FULL;
    after PASS /opsx-test-env DOWN; remaining companions via
    /opsx-meta-fix-command-defects
- id: F14 GRAPH_MISSING_TEST_ENV
  where: .cursor/pipeline/GRAPH.md (pre 2026-08-09T05:34:03Z UPDATE)
    NAVIGATE could not recommend /opsx-test-env; soft chain jumped
    antipattern→static FULL without local compose stage
  operator_workaround: /opsx-test-env UP|DOWN directly; then UPDATE GO
- id: F15 META_ADMIN_NAME_REMAP
  where: meta-* TARGET OVERRIDE vs residual `/opsx-admin-command-*` prose
    user-facing plane is `/opsx-meta-*`, but upstream snapshots / soft docs
    still mention admin-command-* names
    prefer `/opsx-meta-*` pasteables; treat admin names as redirects/legacy
- id: F16 SUPERVISOR_ALLOWLIST_LAG
  where: opsx-supervisor.md dispatch allowlist vs GRAPH soft chain
    supervisor may omit newly indexed soft-chain nodes until §14 allowlist
    catches up; `/opsx-test-env` was added to §14.3 (2026-08-12 defect fix)
    Owner/policy include missing node; or run soft-chain command outside supervisor
- id: F17 GRAPH_MAX_INDEX_2026_08_11
  where: .cursor/pipeline/GRAPH.md (pre 2026-08-11T03:07:21Z UPDATE GO)
    meta/projectize/devops/evolution/supervisor/commit-all/propose were
    inventory-only (NOT_OPENED_BUDGET) — NAVIGATE could not orient on them
  do_not_pretend_fixed: false (closed by 2026-08-11T03:07:21Z materialization)
- id: F18 GRAPH_MISSING_OWNER_CONTRACT_REVIEW
  where: .cursor/pipeline/GRAPH.md (pre 2026-08-11T14:44:35Z UPDATE GO)
    /opsx-owner-contract-review lived in inventory but was unindexed;
    NAVIGATE after /opsx-new pointed at continue/ff and skipped soft OCR;
    META fingerprint lagged body (55 names vs 56 indexed)
    /opsx-owner-contract-review change=<name> directly; then UPDATE GO
## Post-implementation verification chain (impl → archive)
Advisory ordering from `impl_done` through archive. Operator may deviate;
command contracts own gates. Authority: `.cursor/pipeline/contracts/VERIFY_PHASES.md`.
### Primary sequence (typical)
| Step | Command | Role | Hard gate? |
|------|---------|------|------------|
| 0 | `/opsx-apply <change>` | implementation complete (`impl_done`) | apply GO |
| 1 | `/opsx-verify mode=impl <change>` | PHASE_IMPL DoD (`✅ IMPL_OK` / `❌ IMPL_GAPS`) | IMPL_GAPS blocks chain |
| 2a | `/opsx-pyright-strict-coverage base=<BASE>` | production `.py` ⊆ strict include | soft |
| 2b | `/opsx-external-call-coverage base=<BASE>` | external surfaces ↔ tests | soft |
| 2c | `/opsx-performance-review scope=base base=<BASE>` | performance verdict (when trigger) | soft conditional |
| 2d | `/opsx-performance-fix` + re-audit | only on performance FAIL | soft |
| 2e | `/opsx-antipattern-gate base=<BASE>` | diff-scoped antipattern scan | soft |
| 2f | `/opsx-test-env UP` | laptop PG/CH/Redis before FULL/destructive | soft (env-class) |
| 2g | `/opsx-static-check FULL` | orchestrated static checks | soft |
| 2h | `/opsx-test-env DOWN` | tear down test compose after FULL PASS | advisory |
| 2i | `/opsx-static-check FULL CACHE_OFF` | when prior FULL was cache-dev | soft WARN |
| 3 | `/opsx-verify mode=archive <change>` | PHASE_ARCHIVE (`✅ GO` / `❌ NO_GO`) | **archive authority** |
| 4 | `/opsx-archive <change>` | move change; promote decisions | needs archive verify GO |
Short path: `IMPL_OK` + no production `.py` → skip 2a–2i → step 3 directly.
### Product Acceptance (when `PRODUCT_ACCEPTANCE_REQUIRED=true`)
Runs in parallel with / before archive verify; archive verify consumes PA status.
| Command | When |
|---------|------|
| `/opsx-spec-scenario-coverage mode=plan change=<change>` | planning / hard when PA required |
| `/opsx-spec-scenario-coverage mode=audit change=<change>` | lifecycle coverage audit |
| `/opsx-test` | TEST_ONLY gaps from scenario audit |
| `/opsx-close-external-gap` | PG/CH REFACTOR_AND_TEST or CERTIFY packets |
| `/opsx-spec-scenario-coverage mode=certify change=<change>` | after authorized provider receipt |
PA `FAIL` / `BLOCKED` → archive blocker `product_acceptance_not_pass` in step 3.
### Recovery / branch commands (during chain)
| Command | Trigger |
|---------|---------|
| `/opsx-apply <change>` | `IMPL_GAPS` or archive `NO_GO` (DoD regressed) |
| `/opsx-update <change>` | spec/plan drift; `IMPL_GAPS` / `NO_GO` ALSO_OK |
| `/opsx-fix-types` | typing failures from static-check / test-triage |
| `/opsx-test-triage` | flaky/env-class test failures |
| `/opsx-test` | external-call TEST_ONLY; scenario gaps |
| `/opsx-bug-debt-board` | ALSO_OK anytime; `CLEAR` ≠ card-close |
### Not archive verify (do not substitute)
- `/opsx-test … verify` — bug-episode GREEN only
- bare `/opsx-verify` — defaults `mode=archive` (WARN); prefer explicit mode
- quality-chain PASS alone — does not authorize `/opsx-archive`
- `✅ IMPL_OK` alone — never authorizes archive
### Post-archive (soft, not verification)
| Command | Role |
|---------|------|
| `/opsx-distribute-brief` | client/CS distribution pack |
| `/opsx-sync` | delta specs → main specs (if not done earlier) |
| `/opsx-commit` / `/opsx-create-pr` | distribution (may happen earlier) |
- Pre-PR product/runtime: `/opsx-project-bug-hunt` receipt before `/opsx-create-pr`
  (or exact `OVERRIDE_SKIP_PROJECT_BUG_HUNT`); Bugbot = residual
- Process-contract defect (Bugbot on commands/rules/skills/static-check):
  `/opsx-meta-fix-command-defects` (F6; indexed); not `/opsx-fix-bug`
