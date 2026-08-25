# Verify Command Policy

This file owns custom `/opsx-verify` command policy. Shared OpenSpec context and `rules.verify` stay in `openspec/config.yaml`.

Phase selection and DoD vs archive split live in
`.cursor/pipeline/contracts/VERIFY_PHASES.md` (shared module). This policy
owns **archive-phase** markers and blockers; `mode=impl` markers are defined
in VERIFY_PHASES and MUST NOT be used as archive GO.

```yaml
verify:
  default_mode: archive
  language: ru
  phases:
    module: .cursor/pipeline/contracts/VERIFY_PHASES.md
    impl:
      final_marker:
        ok: "✅ IMPL_OK"
        gaps: "❌ IMPL_GAPS"
      authorizes_archive: false
    archive:
      final_marker:
        enabled: true
        go: "✅ GO"
        no_go: "❌ NO_GO"
        position: "last_line"
      authorizes_archive: true
  # legacy alias: strict archive audit settings
  final_marker:
    enabled: true
    go: "✅ GO"
    no_go: "❌ NO_GO"
    position: "last_line"
  verdict:
    require_single_overall_verdict: true
    no_go_if_targeted_test_fails: true
    no_go_if_task_checked_but_validation_fails: true
    no_go_if_archive_blocker_exists: true
    no_go_if_placement_violation_exists: true
  archive_blockers:
    - failed_targeted_tests
    - placement_violations
    - missing_required_decision
    - task_validation_mismatch
    - stale_reference_model
    - unresolved_open_questions
    - unresolved_semantic_write_target
    - unsafe_async_test_patch
    - stubbed_guard_pipeline
    - weak_write_gate_regression
    - required_scenario_coverage_not_pass
    - product_acceptance_not_pass
  product_acceptance:
    contract: .cursor/pipeline/contracts/PRODUCT_ACCEPTANCE.md
    # Kernel DONE: PA PASS (or NOT_REQUIRED). Soft tooling waive cannot clear.
    required_for_archive_when: PRODUCT_ACCEPTANCE_REQUIRED
    status_field: PRODUCT_ACCEPTANCE_STATUS
    pass_values: [PASS, NOT_REQUIRED]
    fail_is_archive_blocker: true
    soft_waive_clears_pa: false
    # LIFECYCLE_COVERAGE under PA: durable OWNER_LIFECYCLE_ECHO + Owner
    # CONFIRM_LIFECYCLE required; scenario VERDICT=PASS alone is insufficient.
    lifecycle_requires_owner_echo_and_confirm: true
  scenario_coverage:
    contract: .cursor/pipeline/contracts/SCENARIO_TEST_COVERAGE.md
    taxonomy: .cursor/pipeline/contracts/TEST_EVIDENCE_TAXONOMY.md
    activation_field: SCENARIO_COVERAGE_REQUIRED
    # Also forced when PRODUCT_ACCEPTANCE_REQUIRED=true (see PRODUCT_ACCEPTANCE.md)
    product_acceptance_forces_lifecycle: true
    legacy_absence_is_blocker: false
    required_verdict: PASS
    require_fresh_source_spec_sha: true
    require_fresh_worktree_fingerprint: true
    require_fresh_provider_receipts: true
    writer_self_report_is_sufficient: false
  output:
    language: ru
    require_sections:
      - Итоговый вердикт
      - Поведение
      - Архитектурное размещение
      - Тесты
      - Согласованность tasks
      - Готовность к archive
      - Следующая команда
    forbid_followup_write_offer: true
```
