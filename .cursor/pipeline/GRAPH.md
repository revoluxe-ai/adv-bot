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
- artifacts_read: `.tmp/opsx-bug-cases/INDEX.md` + case LEDGER/FANIN/findings/HC-*
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
- artifacts_read: .tmp/opsx-bug-cases/**
- artifacts_written: .tmp/opsx-bug-cases/** ; fanin_assemble writes ONLY results/FANIN.md ; may append ROUTE-TRACE
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
- artifacts_written: .tmp/opsx-bug-cases/** without GO; production only with GO+fix_now+RED gate; tests forbidden under GO; ROUTE-TRACE
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
- purpose: atomic local commits for product/code/OpenSpec/docs
- input_state: product_dirty
- output_state: product_dirty | pr_ready
- artifacts_read: git status/diff
- artifacts_written: git commits (product scope)
- decision_owner: committer
- next_typical: /opsx-project-bug-hunt | /opsx-create-pr | /opsx-admin-command-commit (process only; admin off-graph)
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
- purpose: open a pull request; product/runtime requires PROJECT_BUG_HUNT_RECEIPT unless OVERRIDE_SKIP_PROJECT_BUG_HUNT or docs/process-only
- input_state: pr_ready
- output_state: pr_ready
- artifacts_read: commits/diff vs base; optional PROJECT_BUG_HUNT_RECEIPT
- artifacts_written: remote PR (via gh)
- decision_owner: PR author
- next_typical: none | /opsx-project-bug-hunt (if receipt gate blocks)
- known_flaws: receipt gate is command-owned (not soft graph advice)

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
product_dirty --/opsx-commit--> pr_ready
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

### Pre-Bugbot primary hunt

Before `/opsx-create-pr` on product/runtime diffs: `/opsx-project-bug-hunt
base=<PR-base> head=<branch>`. Bugbot PR section = residual only.
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
- Bug recovery: `.tmp/opsx-bug-cases/INDEX.md` pasteable NEXT_ACTION
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
- Pre-PR product/runtime: `/opsx-project-bug-hunt` receipt before `/opsx-create-pr`
  (or exact `OVERRIDE_SKIP_PROJECT_BUG_HUNT`); Bugbot = residual
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
- Uncommitted process edits after design/fix/pipeline UPDATE GO: `/opsx-admin-command-commit` (not `/opsx-commit`)
