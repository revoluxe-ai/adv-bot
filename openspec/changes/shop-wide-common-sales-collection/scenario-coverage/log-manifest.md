# Scenario coverage — log manifest

TASK_ID: WB-SKY-COMMON-SALES-EVIDENCE-CLOSE-20261005-0250  
CHANGE_ID: shop-wide-common-sales-collection  
MODE: evidence closure (docs only; no self-certify)

Durable logs under `scenario-coverage/logs/`. External provenance copies remain at
`C:\Users\vkita\my_code\cursor-sdk-task-runner\.runner-temp\common-sales-native-baseline-0230\`
(not git-tracked; archive `head.zip` SHA256 below).

## Authoritative suite logs (independent PASS — writer does not re-claim verdict)

| Log | SHA256 | Result | Executed (local file mtime MSK) |
|-----|--------|--------|----------------------------------|
| `logs/unit-coordinator-updater.log` | `aebe39a8831d923dec5176a2c8d668b7d7bae70f3c0747840d4c2b1752021315` | 72 passed | 2026-10-05T01:58:12+03:00 |
| `logs/integration-ch-coverage.log` | `47bff5dc48a30bf3916324a98a72618d968a3d69681859a190024fbec3f87a8d` | 2 passed | 2026-10-05T01:58:25+03:00 |
| `logs/wb-shop-coroutines.log` | `6997e0eba891fb63258a494a65b08c8dd6bb8ef6508b56256d284906a14ac81f` | 2 passed | 2026-10-05T01:58:38+03:00 |

Command bindings match `exec.receipt.json` `EXECUTION_BINDINGS`.

## Typecheck logs

| Log | SHA256 | Result | Executed (local file mtime MSK) |
|-----|--------|--------|----------------------------------|
| `logs/pyright-shop-wide-common-sales.log` | `2181295a08254d02d5113a1f6379c4d2732b61dfb05a62f5f31c98ffe1be1a69` | 0 errors (package scope) | 2026-10-05T01:58:46+03:00 |
| `logs/pyright-strict-full-repo.json.log` | `af3260c309e77096686b7a867a42757163a5f88f4fc9bb87a3728160a2a83f1a` | **755 files, 0 errors, 0 warnings** | 2026-10-05T02:27:22+03:00 |
| `logs/pyright-strict-comparison.json` | `09fae9bb3fc6980ea50eb84f242d6a6fce6df98421a6a441d04208b30a92b3a5` | baseline 743→current 755; introduced 0 | 2026-10-05T02:21:33+03:00 |

Canonical full strict source (identical bytes copied):
`cursor-sdk-task-runner\.runner-temp\common-sales-native-baseline-0230\canonical_feature_strict.json.log`

Env: feature CWD `.venv` Junction → `shop-wide-campaign-data-collection\.venv`; command
`poetry run pyright-strict --outputjson` in feature worktree.

## Legacy WBShop unfiltered logs (limitations — not authoritative PASS proof)

Both baseline archive and current feature **2 failed** (same primary:
`parsing_keywords_run` never called). Secondary unlaunched coroutine lists differ
because current feature adds `taskgroup_no_ad_supervisor` (`FakeTaskGroup` does not
execute wrapped coroutines). **Do not** label these as green regression proof.

| Log | SHA256 | Note |
|-----|--------|------|
| `logs/wbshop-unfiltered-baseline-archive.log` | `d84bafe408641594345660afc38f4aef87d766337a45a6ce3d6e881cb65a356b` | archive head checkout |
| `logs/wbshop-unfiltered-current-feature.log` | `7465ef002d90a8d5d85cb467f65911cc13988338c60331b88ccb8dc632a186fb` | current feature tree |

Authoritative wb_shop adjacent proof: `tests/test_wb_shop_run_coroutines.py` (2/2 PASS)
via `logs/wb-shop-coroutines.log`.

## Archive provenance

| Artifact | Value |
|----------|-------|
| `head.zip` SHA256 | `519d1acf42296cefca178b897c5996b8a630428f572019bd0bbe762e3a3710ed` |
| git archive HEAD | `62c8d48b15498997b84357e015b0e688f44fd37b` |
| runner-temp `git rev-parse` parent | `e045b20…` (walks up to runner parent — **does not** define archive contents) |

## Independent scenario certification (0260)

| Artifact | Value |
|----------|-------|
| TASK_ID | `WB-SKY-COMMON-SALES-SCENARIO-CERTIFY-20261005-0260` |
| CERTIFY_EVIDENCE_ID | `SCPV1-shop-wide-common-sales-20261005-certify-0260` |
| VERDICT | **PASS** 33/33 |
| REPORT | `SCENARIO_TEST_COVERAGE_REPORT.md` SHA256 `d145f7816dd556176f29b375db820f2b49c9803c4f480ec6dffc0cd9794e6bf0` |
| Receipt | `certify.receipt.json` (immutable; independent reviewer REVIEWER0240) |

Historical evidence-close manifest (0250) superseded for scenario verdict; certification receipt is authoritative.
