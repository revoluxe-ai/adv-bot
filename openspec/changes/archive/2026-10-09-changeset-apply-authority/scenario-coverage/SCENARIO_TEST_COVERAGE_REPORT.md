# Scenario test coverage — changeset-apply-authority (PG-only V1)

CHANGE_ID: changeset-apply-authority  
V1_SCOPE: Slices A–C (PG-only)  
OWNER_SCOPE: OPTION_A_PG_ONLY_V1  

## Summary

| Class | Count |
|-------|------:|
| PASS (V1) | 29 |
| MOVED_TO_FUTURE_CHANGE | 4 |
| NOT_APPLICABLE_TO_V1 | 2 |

Executable evidence: `slice-a-l1-audit.receipt.json`, `slice-b-l1-audit.receipt.json`,
`slice-c-l1-audit.receipt.json`, consolidated in `certify.receipt.json`.

## Moved to future changes

- **S10, S11** → `external-wb-apply-authority`
- **S15, S16** → `apply-transport-adapters`

## Not applicable to V1 implementation

- **S18, S19** — architectural boundaries only (history / decision memory SoT separation)

## S17 honesty

Repository insert-only immutability via `PostgresApplyEvidenceStore`; no DB trigger
immutability claimed (`IMMUTABILITY_BOUNDARY.md`).

## Commands (verify logs)

```bash
poetry run pytest -m unit tests/unit/wb_sky_control_plane/apply/ tests/unit/wb_sky_control_plane/
poetry run pytest -m 'integration and destructive_local' tests/integration/wb_sky_control_plane/apply/
```
