---
cursor:
  subagentId: "bc-116735ee-0061-5be6-98db-812f9e6e25d7"
---

# AI_PACKAGE_SHOP_IDENTITY_REPAIR_REPORT

```text
PR:
#450

PR_HEAD_PRE:
1b636542a41e1dbfd66585c64d5c93dfff0bed18

ORIGIN_STAGE:
d2166b2d805b27a6656f46c6ccb8e56066b4e888

AUTHORITATIVE_SHOP_ID_SOURCE:
WBCabinet.shop_id

OLD_NUMERIC_ASSUMPTION:
app/modules/ai_package_v1/domain/shop_id.py manifest_shop_id() int(stripped) after isdigit()
app/modules/ai_package_v1/domain/export_inputs.py validate_export_shop_id/validate_export_inputs -> int
app/modules/ai_package_v1/domain/manifest.py ExportManifest.shop_id: int
app/modules/ai_package_v1/domain/campaign_stat.py CampaignStatRow.shop_id: int; rows_for_shop(shop_id: int)
app/modules/ai_package_v1/domain/funnel_stat.py FunnelStatRow.shop_id: int
app/modules/ai_package_v1/readers/ch_campaign_stat_reader.py shop_id: int (stamp only; SQL filters adv_id)
app/modules/ai_package_v1/readers/ch_funnel_reader.py shop_id: int (stamp only; SQL filters nmid)
app/modules/ai_package_v1/export/export_service.py manifest_shop_id: int
app/modules/ai_package_v1/export/payload_encode.py encode_pg_inventory_csv manifest_shop_id: int
app/modules/ai_package_v1/keyword_performance/domain/models.py eight row models shop_id: int
app/modules/ai_package_v1/keyword_performance/domain/export_field_registry.py shop_id units "int"
app/modules/ai_package_v1/keyword_performance/export/{daily,decision,position,keyword}_assembler.py manifest_shop_id: int
app/modules/ai_package_v1/keyword_performance/windows/position_engine.py identity key tuple[int, ...]
app/modules/ai_package_v1/validator/package_validator.py str(manifest_shop_id) coercion vs settings snapshot

NUMERIC_COERCION_REMOVED:
YES

MANIFEST_SHOP_ID_TYPE:
str

DATASET_SHOP_ID_TYPE:
str

KEYWORD_SHOP_ID_TYPE:
str

UUID_ROUNDTRIP:
PASS

DECIMAL_STRING_PRESERVED_AS_STRING:
PASS

BLANK_FAIL_CLOSED:
PASS

SHOP_ISOLATION_CHANGED:
NO

AUTO_SEARCH_SEMANTICS_CHANGED:
NO

TESTS:
PASS — poetry run pytest -m unit tests/unit/ai_package_v1/ -q (146 passed), including tests/unit/ai_package_v1/test_shop_identity_contract.py and tests/unit/ai_package_v1/test_full_package_acceptance.py

RUFF:
PASS — poetry run ruff check on changed Python paths

PYRIGHT:
PASS on changed paths (0 new errors). Canonical include of app/modules/ai_package_v1 + tests/unit/ai_package_v1 still reports 5 pre-existing errors in untouched tests/unit/ai_package_v1/test_campaign_settings_contract.py

OPENSPEC:
PASS — openspec validate ai-package-full-export-contract-repair --type change --strict

DIFF_CHECK:
PASS — git diff --check clean before commit

COMMIT:
a32e9ca584353de80b431d329a2e18d42935fc57 fix(ai-package): preserve authoritative shop identity

PR_HEAD_POST:
a32e9ca584353de80b431d329a2e18d42935fc57

PR_STATE:
DRAFT

PRODUCTION_WRITES:
NONE

FINAL_STATUS:
SHOP_IDENTITY_REPAIRED
```
