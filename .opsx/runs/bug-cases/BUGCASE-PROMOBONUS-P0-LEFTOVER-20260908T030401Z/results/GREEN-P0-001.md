# GREEN P0-001

BUG_CASE_ID: BUGCASE-PROMOBONUS-P0-LEFTOVER-20260908T030401Z
FINDING_ID: P0-001
WORKER_EXECUTION_ID: WEX_TEST_GREEN_P0
DISPATCH_ID: D-024
ATTEMPT: 1

## Verification

TEST_ID: `tests/unit/wb/utils/test_promo_accounting.py::test_campaign_ledger_multi_tranche_fraction_uses_package_percent_not_leftover_over_last_tranche`
TEST_CONTENT_SHA256: `85afc836e48c62f8f9a0d7f390d43e93d814e54a2abdb2faf78ac116e46b3933`
RED_TEST_CONTENT_SHA256: `85afc836e48c62f8f9a0d7f390d43e93d814e54a2abdb2faf78ac116e46b3933`
TEST_CONTENT_MATCH: YES
NON_WEAKEN_DELTA: (none — exact match)

COMMAND:

```text
poetry run pytest -m unit tests/unit/wb/utils/test_promo_accounting.py::test_campaign_ledger_multi_tranche_fraction_uses_package_percent_not_leftover_over_last_tranche -vv
```

PYTEST_EXIT: 0
TESTS_EXECUTED: PASS (1/1)
DURABLE_FILE_WRITTEN: YES

## Production hash

PRODUCTION_PATH: `app/shared/domains/wb/utils/promo_accounting.py`
PRODUCTION_HASH_AFTER: `07692511e3db22dc58cd3e77e31a696697c6042802ba4ed8c91da8dbdbc1ca57`
PRODUCTION_HASH_BEFORE: (not recorded in RED; fix applied per results/FIX-P0-001.md)

## Invariant verified

Multi-tranche campaign ledger: `remaining==1000`, `fraction==0.5`,
`promo_multiplier(fraction)==2.000000`, `fraction < 0.9`. Package percent
drives overlay fraction; no leftover/last_tranche explosion.

## Targeted regressions

- `tests/unit/wb/utils/test_promo_accounting.py::test_campaign_ledger_multi_tranche_fraction_uses_package_percent_not_leftover_over_last_tranche`

STATUS: GREEN_CONFIRMED
RED_EVIDENCE_PATH: results/RED-P0-001.md
FIX_EVIDENCE_PATH: results/FIX-P0-001.md
GREEN_WRITER: /opsx-test verify mode
