# FULL_AI_PACKAGE_ACCEPTANCE_REPORT

Evidence from `tests/unit/ai_package_v1/test_full_package_acceptance.py` (unit fixtures).

```text
PACKAGE_GENERATED: YES
MANIFEST: PASS
DATA_MAP: PASS
PACKAGE_SUMMARY: PASS
FAMILY_STATUS_EXPLICIT: YES
CURRENT_SETTINGS: PARTIAL (by design — PG PARTIAL sync)
SETTINGS_HISTORY: GAP
CHANGE_EVENTS: GAP
KEYWORD_HISTORY: PARTIAL (fixture-bound keyword export)
COMMON_SALES: GAP
CAMPAIGN_ADVERTISING: PARTIAL (empty CH rows in fixture)
JOINABILITY: PASS (campaign_identity + join_keys in summary/DATA_MAP)
MISSING_ZERO_NULL: PASS
COVERAGE_METADATA: PASS
DETERMINISM: PASS (PAYLOAD_HASH_ONLY — per-file sha256 stable across reruns)
AI_READABILITY: PASS
```

## Shop identity follow-up

The fixture above used shop id `"1"`, which passed the former numeric gate.
HOME-PC export of real `WBCabinet.shop_id`
`155c426c-0c58-59d2-9578-ec9747ecbc90` failed in `manifest_shop_id()` before
any ZIP was written. Repair keeps that value as `str` end to end
(`tests/unit/ai_package_v1/test_shop_identity_contract.py`). No production DB
export is part of this evidence.
