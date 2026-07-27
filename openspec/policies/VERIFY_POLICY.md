# Verify Command Policy

This file owns custom `/opsx-verify` command policy. Shared OpenSpec context and `rules.verify` stay in `openspec/config.yaml`.

```yaml
verify:
  default_mode: strict
  language: ru
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
    - unsafe_async_test_patch
    - stubbed_guard_pipeline
    - weak_write_gate_regression
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
