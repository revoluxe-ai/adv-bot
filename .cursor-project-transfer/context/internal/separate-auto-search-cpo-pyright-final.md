---
cursor:
  subagentId: "bc-32bdaafb-bc6f-532c-901a-2eb4845c2b03"
---

# separate-auto-search-cpo — pyright final (read-only)

**Branch:** `separate-auto-search-cpo`  
**Checked:** 2026-10-05 (UTC)

## Git

| Item | Value |
|------|--------|
| HEAD | `9b97462b16120c6b900b9e57b93bda515b33787c` |
| `origin/stage` | `1443649281543bc00411d9940a047037ed6d3ffd` |
| merge-base(HEAD, origin/stage) | `1443649281543bc00411d9940a047037ed6d3ffd` |
| `origin/stage` ancestor of HEAD | yes (`git merge-base --is-ancestor` exit 0) |
| STAGE_MOVED | no — stage tip unchanged from expected `144364928` |

## Pyright (`poetry run pyright-strict`)

- **Exit code:** 1
- **Error count:** 19
- **Feature-owned (leg-CPO) paths in error list:** none — all errors under `ai_package_v1` (app + tests)

### Errors (file:line: message)

```
app/modules/ai_package_v1/export/package_summary.py:24:5 - Import "GAP_SCHEMA_VERSION" is not accessed (reportUnusedImport)
app/modules/ai_package_v1/export/package_summary.py:239:34 - Argument of type "dict[str, Any] | FamilyGapEntry" cannot be assigned to parameter "gap" of type "dict[str, Any]" in function "_gap_status" (reportArgumentType)
app/modules/ai_package_v1/export/package_summary.py:240:33 - Argument of type "dict[str, Any] | FamilyGapEntry" cannot be assigned to parameter "gap" of type "dict[str, Any]" in function "_gap_status" (reportArgumentType)
app/modules/ai_package_v1/export/package_summary.py:330:54 - Could not access item in TypedDict — "family_id" is not a required key in "_FamilyEntry" (reportTypedDictNotRequiredAccess)
app/modules/ai_package_v1/export/package_summary.py:349:38 - Could not access item in TypedDict — "canonical_status" is not a required key in "_FamilyEntry" (reportTypedDictNotRequiredAccess)
app/modules/ai_package_v1/validator/package_validator.py:408:53 - Argument type is partially unknown — len(list[Unknown]) (reportUnknownArgumentType)
app/modules/ai_package_v1/validator/package_validator.py:412:9 - Type of "join_keys" is partially unknown — Any | list[Unknown] (reportUnknownVariableType)
tests/unit/ai_package_v1/test_campaign_settings_contract.py:88:50 - Type of parameter "assembler_factory" is unknown (reportUnknownParameterType)
tests/unit/ai_package_v1/test_campaign_settings_contract.py:88:50 - Type annotation is missing for parameter "assembler_factory" (reportMissingParameterType)
tests/unit/ai_package_v1/test_campaign_settings_contract.py:116:5 - Type of "detailed_payload" is unknown (reportUnknownVariableType)
tests/unit/ai_package_v1/test_campaign_settings_contract.py:116:30 - Type of "assemble" is unknown (reportUnknownMemberType)
tests/unit/ai_package_v1/test_campaign_settings_contract.py:117:59 - Argument type is unknown (reportUnknownArgumentType)
tests/unit/ai_package_v1/test_full_package_acceptance.py:26:5 - "_export_service" is private and used outside of the module (reportPrivateUsage)
tests/unit/ai_package_v1/test_full_package_acceptance.py:28:71 - "_scope_for_shop" is private and used outside of the module (reportPrivateUsage)
tests/unit/ai_package_v1/test_full_package_acceptance.py:72:5 - Variable "manifest" is not accessed (reportUnusedVariable)
tests/unit/ai_package_v1/test_package_summary.py:17:71 - "_scope_for_shop" is private and used outside of the module (reportPrivateUsage)
tests/unit/ai_package_v1/test_package_summary.py:22:5 - "_export_service" is private and used outside of the module (reportPrivateUsage)
tests/unit/ai_package_v1/test_package_zip_assembler.py:26:5 - "_NoOpReader" is private and used outside of the module (reportPrivateUsage)
tests/unit/ai_package_v1/test_package_zip_assembler.py:27:5 - "_scope_for_shop" is private and used outside of the module (reportPrivateUsage)
```

**Classification:** Pre-existing / stage-adjacent `ai_package_v1` only. No hits on `leg_cpo.py`, adv_keyword messages, `data_manager`, `full_wb_adv_stat`, `wb_adv_dto`, tests under `leg_cpo`, or the integration seam file.
