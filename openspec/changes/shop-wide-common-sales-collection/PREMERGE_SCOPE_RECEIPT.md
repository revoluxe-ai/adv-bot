# PREMERGE_SCOPE_RECEIPT

TASK_ID: WB-SKY-COMMON-SALES-LIFECYCLE-COMMIT-20261005-0450  
CHANGE_ID: shop-wide-common-sales-collection  
MODE: scoped feature commit (docs metadata closure + certified implementation)  
PREFLIGHT: `WB-SKY-COMMON-SALES-LIFECYCLE-PREFLIGHT-20261005-0445`

## Verdict

| Field | Value |
|-------|-------|
| FEATURE_COMMIT_SCOPE | **PASS** (pending commit execution) |
| MERGE_REVIEW | **NOT_CLAIMED** — separate independent reviewer required |
| PARENT_HEAD | `62c8d48b15498997b84357e015b0e688f44fd37b` |
| BRANCH | `shop-wide-common-sales-collection` |

## Source byte equality (15 implementation paths)

All native current bytes match certified overlay (preflight + re-verified 2026-10-05T04:50 MSK):

| Path | SHA256 |
|------|--------|
| `app/modules/shop_runner/service_manager/manager.py` | `be44073e96c2ab2235aa1663059c6083c4820ccb9e20f30d64e6b6549465f6f5` |
| `app/modules/shop_runner/service_manager/services/common_sale_stat_updater/common_sale_stat_updater.py` | `007686f50d45a8cf8d333df78ec50b68587da0fc08c7e1f9f5faffa6cf388721` |
| `app/modules/shop_runner/wb_shop.py` | `bfa49122b6405b131521b4da16b82f150434bd8f2903143f1502193169ac9ac5` |
| `pyrightconfig_strict.json` | `73cf2f13412c6d5d622fcf7382e146fa12783895e828860924928545c084b459` |
| `tests/modules/shop_runner/service_manager/test_common_sale_stat_updater.py` | `f0d7df6a41073c9d8e54d59220e3e6e00b11ed23f471ff2a2129347aa1221153` |
| `tests/modules/shop_runner/service_manager/test_shop_wide_common_sale_stat_coordinator.py` | `6993c21ec9b18a43b2fa4575ed7a913657076b2a739cfc2012ca5b1165251f57` |
| `tests/integration/test_shop_wide_common_sale_stat_coverage.py` | `bed51317808bb27c38943d0b676b8865a3750607567ac6cc74f9bd66007d63ff` |
| `app/modules/shop_runner/service_manager/services/shop_wide_common_sales/__init__.py` | `a1c98ca8c137be2011fcf5a32fb599b75670f11597e4559d66e11fd24e29c7d3` |
| `app/modules/shop_runner/service_manager/services/shop_wide_common_sales/collect_types.py` | `3a10195b9307a678498130c8b98bcc585491a1f211408e5b20947601c72c7964` |
| `app/modules/shop_runner/service_manager/services/shop_wide_common_sales/coordinator.py` | `948a7dc958c53479cfc71b748a8cceacc094b5a1adb99b620514b2e9bbfe3e38` |
| `app/modules/shop_runner/service_manager/services/shop_wide_common_sales/coverage_evidence.py` | `d1da292707d46de70ed64a3acb44eeba50dd94da65604eb4ca6f30e30bff483c` |
| `app/modules/shop_runner/service_manager/services/shop_wide_common_sales/fact_validator.py` | `582a0cb0adf46ea1f92dc10c8e4559709a0a3308c1258655caef2999888f5015` |
| `app/modules/shop_runner/service_manager/services/shop_wide_common_sales/legacy_assigned_nmids.py` | `2996cb0d7ec938caf5ebfd1500053a87a3f0e376bdb92d3f851e110280fb621b` |
| `app/modules/shop_runner/service_manager/services/shop_wide_common_sales/shop_assortment_reader.py` | `c7fab52381b20760868da97e12e8584c3c7138611b15d7b22f4d9c83d2a7ed64` |
| `app/modules/shop_runner/service_manager/services/shop_wide_common_sales/taskgroup_no_ad_supervisor.py` | `c091af08093325abebdb50ba2bc74c059fb3f1aed39bae39235b96285396d07a` |

## Certified bindings (immutable — unchanged)

| Artifact | SHA256 |
|----------|--------|
| `specs/shop-wide-common-sales-collection/spec.md` | `5e24eabdaa2f6bf4daaa494ea6bbca5da73dd443e0540d7568acbca78b508253` |
| `scenario-coverage/plan.md` | `c7e5882345385f9f1c39dc2e252b58c0b10a2c9319efab9a1ad16cb1f834d4a0` |
| `scenario-coverage/SCENARIO_TEST_COVERAGE_REPORT.md` | `d145f7816dd556176f29b375db820f2b49c9803c4f480ec6dffc0cd9794e6bf0` |
| `scenario-coverage/certify.receipt.json` | `4e4ac8c69108054e29e056ca999c2a8daa148c2d07135c3da34a12a4de89f106` |
| `design.md` | `ecf4921d8a77812bc3e3baeee6f43efe2093b2d7ec271126cc68b156d91df874` |

## EXECUTION_BINDINGS_VERIFIED logs (git add -f)

| Log | SHA256 | Result |
|-----|--------|--------|
| `logs/unit-coordinator-updater.log` | `aebe39a8831d923dec5176a2c8d668b7d7bae70f3c0747840d4c2b1752021315` | 72 passed |
| `logs/integration-ch-coverage.log` | `47bff5dc48a30bf3916324a98a72618d968a3d69681859a190024fbec3f87a8d` | 2 passed |
| `logs/wb-shop-coroutines.log` | `6997e0eba891fb63258a494a65b08c8dd6bb8ef6508b56256d284906a14ac81f` | 2 passed |
| `logs/pyright-strict-full-repo.json.log` | `af3260c309e77096686b7a867a42757163a5f88f4fc9bb87a3728160a2a83f1a` | 755 files 0 errors |

Certification: `WB-SKY-COMMON-SALES-SCENARIO-CERTIFY-20261005-0260` — PASS 33/33.

## Docs metadata closure (this commit only)

| File | Change |
|------|--------|
| `tasks.md` | §4.1 NOT_RUN removed; §4.4 marked executed (CH 2/2); §7.4 clarified 19 supervised loaders |
| `scenario-coverage/log-manifest.md` | Replaced stale "report not authored" with certify 0260 receipt |
| `PREMERGE_SCOPE_RECEIPT.md` | This receipt |

Historical certification bindings remain valid; no fake new PASS introduced.

## Staged allowlist provenance

Source: `commit-allowlist.json` from preflight (37 paths) + this receipt (38 total).

Stage worktree (`adv-bot` / `stage` HEAD `37d0ec5fce9acae46eb0b35dda7c0fea7b9845a0`) — **READ ONLY**; 92 dirty files, no implementation overlap with feature (preflight confirmed).

## Historical fingerprint

| Field | Value |
|-------|-------|
| WORKTREE_FINGERPRINT | `7ccebe8a8c0d5455d39d28f406ca7031b1d7a9b54c3c3734d45964a795d48c8c` |
| CERTIFY_EVIDENCE_ID | `SCPV1-shop-wide-common-sales-20261005-certify-0260` |
| PROVIDER_GAP | `a3f8c2e1b904d7a6` |
