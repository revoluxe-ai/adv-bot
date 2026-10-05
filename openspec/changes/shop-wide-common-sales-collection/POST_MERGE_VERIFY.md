# POST_MERGE_VERIFY

```yaml
TASK_ID: WB-SKY-COMMON-SALES-MERGE-POSTVERIFY-20261005-0470
ARCHIVE_VERIFY_TASK: WB-SKY-COMMON-SALES-ARCHIVE-VERIFY-20261005-0480
CHANGE_ID: shop-wide-common-sales-collection
MERGE_COMMIT: 58441b3589200e02f642628e05920e680e553355
STAGE_FINAL_HEAD: 58441b3589200e02f642628e05920e680e553355
VERDICT: PASS
PASS_SCOPE: CHANGE_SCOPED
CREATED_AT: 2026-10-05T05:16:22+03:00
```

## Gate summary (0480 independent re-assessment)

| Gate | Expected | Actual | Result |
|------|----------|--------|--------|
| Unit tests (74) | 74 passed, 0 skipped | 74 passed, 0 skipped | **PASS** |
| Integration CH (2) | 2 passed | 2 passed | **PASS** |
| Import sanity | IMPORT_OK | IMPORT_OK | **PASS** |
| `openspec validate --strict` | valid | Change valid | **PASS** |
| `git diff --check` (working tree) | 0 issues | exit 0 | **PASS** |
| Merge delta `--check` vs parent1 | 0 issues | exit 0 | **PASS** |
| `pyright-strict` committed merge (clean archive) | errorCount 0 | errorCount 0 | **PASS** |
| `pyright-strict` stage + foreign dirty (baseline) | pre-existing 4 | errorCount 4 (foreign only) | **BASELINE NOT GREEN** |
| Diagnostic parity vs premerge | no new diagnostics | parity true | **PASS** |
| Foreign dirty preserved | 92 paths byte-exact | 0 hash mismatches | **PASS** |
| Index empty post-verify | empty | empty | **PASS** |

## Unit tests — 74/74 PASS

Command (MAIN stage, PYTHONPATH=repo root, MAIN `.venv` via poetry):

```powershell
poetry run pytest -m unit `
  tests/modules/shop_runner/service_manager/test_shop_wide_common_sale_stat_coordinator.py `
  tests/modules/shop_runner/service_manager/test_common_sale_stat_updater.py `
  tests/test_wb_shop_run_coroutines.py -v
```

Result: **74 passed**, 1 warning (SQLAlchemy MovedIn20Warning), 0 skipped.

Log (in-repo): `scenario-coverage/logs/postmerge-unit74.log`
SHA256: `dabdc328345f73607d282e1de5ca8324201675e34260fbd5f399c5a4c6855d96`

Breakdown:
- `test_shop_wide_common_sale_stat_coordinator.py` — 68 tests
- `test_common_sale_stat_updater.py` — 4 tests
- `tests/test_wb_shop_run_coroutines.py` — 2 tests

## Integration CH — 2/2 PASS

Dedicated fixture env (process-scoped, no global compose):

```powershell
$env:DEV_TUNNELS_ENABLED = "0"
$env:WB_SKY_OWNED_CH_TASK = "WB-SKY-COMMON-SALES-20261005"
$env:ALLOW_DESTRUCTIVE_TEST_CLICKHOUSE = "1"
$env:CLICK_HOUSE_HOST = "127.0.0.1"
$env:CLICKHOUSE_PORT = "8124"
$env:CLICK_HOUSE_USER = "CLICK_HOUSE_USER"
$env:CLICK_HOUSE_PASSWORD = "password"
poetry run pytest -m "integration and destructive_local" `
  tests/integration/test_shop_wide_common_sale_stat_coverage.py -v
```

Result: **2 passed** (`test_shop_wide_coverage_read_write_roundtrip`, `test_collect_by_nmids_uses_production_writer`).

Log (in-repo): `scenario-coverage/logs/postmerge-integration-ch.log`
SHA256: `eb57f8a3fe9dab87c9b1ecb8e5ca1ca1091d83fafdec7a60a508c80bf1358a0d`

## pyright-strict — scoped assessment

### Canonical committed merge (change-scoped PASS)

Git archive @ `58441b358` (no dirty overlay, same MAIN venv):

| Metric | Value |
|--------|-------|
| filesAnalyzed | 755 |
| errorCount | **0** |
| warningCount | 0 |
| archive_sha256 | `ac27504299300147566f205be054186bd81a5cd7cc5fedae91f25964bacd8a23` |

Proof: `lifecycle-proof/comparison.json` → `merged_committed`.

### Actual stage + foreign dirty (baseline NOT GREEN)

| Metric | Value |
|--------|-------|
| filesAnalyzed | 755 |
| errorCount | **4** |
| warningCount | 0 |

All 4 errors exclusively in **foreign dirty** (pre-existing, preserved):

`app/core/mp/wb/api/adapter/promotion_client/campaigns_info_v2/adapter.py`

Rules: `reportUnknownVariableType`, `reportUnknownMemberType` (lines 85–93).

Log (in-repo): `scenario-coverage/logs/postmerge-pyright-foreign-dirty-baseline.json`
SHA256: `2f64f0755cccaf4837fba3ff9307406fa2728a558d4cef5b9f559a6513e04bf0`

### Diagnostic parity (no merge regression)

Premerge @ `37d0ec5` + 92 dirty overlay: 743 files, 4 errors (same adapter.py).
`diagnostic_parity=true`, `new_diagnostics=[]`.
Proof: `lifecycle-proof/diagnostic-parity.json`.

**No errors in any merge-introduced shop-wide-common-sales path.**

## openspec validate — PASS

```
poetry run openspec validate shop-wide-common-sales-collection --strict
→ Change 'shop-wide-common-sales-collection' is valid
```

Log: `scenario-coverage/logs/postmerge-openspec-validate.log`

## Plain checks — PASS

| Check | Result |
|-------|--------|
| `git diff --check` (working tree) | exit 0 |
| `git diff 58441b358^1..58441b358 --check` (merge delta) | exit 0 |
| `git diff --cached --name-only` | empty |

## Import sanity — PASS

```python
import app.modules.shop_runner.service_manager.services.shop_wide_common_sales.coordinator
import app.modules.shop_runner.service_manager.services.shop_wide_common_sales.fact_validator
import app.modules.shop_runner.service_manager.services.shop_wide_common_sales.shop_assortment_reader
# → IMPORT_OK (no network/WB calls)
```

Log: `scenario-coverage/logs/postmerge-import-sanity.log`

## Ancestor proofs (reconfirmed)

```
2ccff6321700499c22cbc1a1f5b5541cb8683fef ⊆ HEAD  ✓
3afdde673e667cc725131cab7f463db7e2b34b66 ⊆ HEAD  ✓
```

## Historical 0470 initial receipt (preserved)

Initial independent runner labeled **FAIL** on unscoped pyright gate (`errorCount 4`
on stage + foreign dirty). That result is **historical evidence**, not a change-scoped
regression:

| Field | 0470 initial | 0480 scoped |
|-------|--------------|-------------|
| Unscoped pyright | FAIL (4 foreign errors) | baseline NOT GREEN (unchanged) |
| Committed merge pyright | not separately archived | **0 errors** |
| Diagnostic parity | — | true (no new diagnostics) |
| Overall scoped verdict | FAIL | **PASS** |

Raw 0470 runner directory (external):
`C:\Users\vkita\my_code\cursor-sdk-task-runner\runs\WB-SKY-COMMON-SALES-MERGE-POSTVERIFY-20261005-0470\`

## Next step

Archive verify **GO** (0480). Closure command:

```
/opsx-archive shop-wide-common-sales-collection
```
