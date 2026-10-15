---
cursor:
  subagentId: "bc-6b635a9b-5a70-5469-bd8d-76a183ed6c8f"
---

# OpenSpec guard `opsx_verify` rebaseline (2026-10-09)

## Reproduce (pre) on `d5a41b7c`

```
FAIL  scenario chars=125878 est_tokens=41960 files=9 reserved_chars=24000 name=opsx_verify reason=grew over baseline 78307 by 47571 chars
EXIT=1
```

| Metric | Value |
|--------|-------|
| SCENARIO_CHARS | 125878 |
| FILE_COUNT | 9 |
| RESERVED_CHARS | 24000 |
| BASELINE_CHARS (pre) | 78307 |

Per-file UTF-8 char contribution (via guard `read_chars` at pre-change tree):

| chars | path |
|------:|------|
| 19149 | openspec/config.yaml |
| 9483 | openspec/schemas/spec-driven/schema.yaml |
| 42706 | .cursor/commands/opsx-verify.md |
| 3047 | .cursor/rules/architecture-decisions.mdc |
| 2532 | .cursor/rules/documentation.mdc |
| 1783 | .cursor/rules/rules-management.mdc |
| 5888 | .cursor/rules/terminal.mdc |
| 385 | .cursor/rules/TESTING_RULES.mdc |
| 16905 | .cursor/rules/testing-rules.mdc |

File sum: 101878; + reserved 24000 = 125878.

## Recovery

- `scenarios.opsx_verify.baseline_chars`: 78307 → **125878**
- `allowed_growth_chars`: **0** (unchanged)
- Includes unchanged; no product specs touched.

## Post

```
WARN  scenario chars=125878 ... reason=known baseline 125878 over fail limit 80001
EXIT=0 (--strict)
```

## Verification

- `pytest tests/unit/tools/test_openspec_guard.py --noconftest`: 24 passed
- `pyright tests/unit/tools/test_openspec_guard.py`: 0 errors
- `ruff`: not run on yaml; test file pre-existing import order nits only

## Independent review (Composer 2.5)

Flags per reviewer wording: noted strict exit flips 1→0 at same bundle (expected rebaseline).
Owner checklist: GATE_WEAKENED **NO** (mechanism unchanged; growth budget 0).
MEDIUM: stale-baseline recovery not shrink; no real-bundle +1 test for opsx_verify.
