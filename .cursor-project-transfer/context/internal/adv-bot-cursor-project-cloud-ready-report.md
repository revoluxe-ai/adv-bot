---
cursor:
  subagentId: "bc-6eb42fe6-562d-5111-9d07-0ad300478b4b"
---

# ADV_BOT_CURSOR_PROJECT_CLOUD_READY_REPORT

Cloud bootstrap hop on certified `origin/stage` `751e7bd2965a2d35941c5827a13cfab0ad6fc588`. No product code. No production writes.

## Summary

| Field | Value |
|---|---|
| CLOUD_HEAD | `751e7bd2965a2d35941c5827a13cfab0ad6fc588` |
| ORIGIN_STAGE | `751e7bd2965a2d35941c5827a13cfab0ad6fc588` |
| BASELINE_MATCH | YES |
| ROUTING_RULE_STATUS | ADDED `.cursor/rules/opsx-cloud-local-routing.mdc`; AGENTS.md pointer |
| ENVIRONMENT_STATUS | CREATED `.cursor/environment.json` (Python 3.11 via deadsnakes, Poetry, check-openspec) |
| OPSX_STATUS | 69 `opsx-*` commands; 23 skills; `poetry run check-openspec` PASS on baseline |
| PROJECT_CLOUD_READY | YES |
| BLOCKERS | none for cloud-first config; full-repo pyright-strict not run in this hop (bounded smoke only) |

## Closed features located on baseline

All six areas have `openspec/changes/archive/2026-10-05-*` plus promoted specs where applicable. `app/modules/ai_package_v1/export/export_service.py` present for full ZIP export.

## Smoke (read-only / bounded)

- `git fetch origin`; HEAD == origin/stage == certified SHA
- `git diff --check` PASS
- `poetry run check-openspec` PASS
- `poetry run pytest tests/unit/tools/test_compose_runtime.py` — 14 passed
- `poetry run pyright-strict openspec/tools/check_openspec.py` — 0 errors

## Repo change

Branch `cursor/cloud-project-bootstrap-8b4b` — config-only PR to `stage`.
