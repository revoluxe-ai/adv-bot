# pytest-integration — context

- Safe multi-module / real-dependency tests that are **not** marked
  `destructive_local`.
- May need Docker for some services depending on fixtures; honest environment
  failures beat fake test-failure labels.
- Runs after `pytest-unit` PASS in both FAST and FULL.
- Must re-run the full `-m integration` set (including tests already covered
  by `pytest-targeted`).
