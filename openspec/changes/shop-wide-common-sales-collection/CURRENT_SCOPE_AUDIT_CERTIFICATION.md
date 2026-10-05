# CURRENT_SCOPE_AUDIT_CERTIFICATION

```yaml
TASK_ID: WB-SKY-COMMON-SALES-ARCHIVE-VERIFY-20261005-0480
CHANGE_ID: shop-wide-common-sales-collection
MODE: independent archive-scope audit bridge
SUPERSEDES_BINDING: SCPV1-shop-wide-common-sales-20261005-certify-0260
PRESERVES_HISTORICAL: certify.receipt.json + SCENARIO_TEST_COVERAGE_REPORT.md (0260) byte-exact in Git history
HEAD: 58441b3589200e02f642628e05920e680e553355
MERGE_COMMIT: 58441b3589200e02f642628e05920e680e553355
IMPLEMENTATION_COMMIT: 3afdde673e667cc725131cab7f463db7e2b34b66
CREATED_AT: 2026-10-05T05:16:22+03:00
VERDICT: PASS
PASS_SCOPE: POST_MERGE_STAGE_ACCEPTANCE
```

Independent reviewer bridge (0480). Runtime / implementation paths unchanged since
`3afdde673`; only HEAD / log / provider bindings refreshed for post-merge stage.

## Deterministic content manifest (merge HEAD)

| Artifact | SHA256 (git blob @ `58441b358`) |
|----------|----------------------------------|
| `specs/shop-wide-common-sales-collection/spec.md` | `4697e648d76f3efcf22b269c51db9048a6ef22e8` |
| `scenario-coverage/plan.md` | `375e136f3d48864b4e8c77567b37bbb9edea40f7` |
| `scenario-coverage/SCENARIO_TEST_COVERAGE_REPORT.md` (0260 historical) | `7bf22d434832dc8a2459de2dbc82d21f9f2cde74` @ HEAD (doc-only deltas after 0260; matrix unchanged) |

Historical 0260 bindings (`SOURCE_SPEC_SHA=5e24eab…`, `WORKTREE_FINGERPRINT=7ccebe8a…`) refer to
pre-implementation planning worktree. Post-implementation spec blob stabilized at `4697e648…` from
`3afdde673` through merge HEAD (`git diff 3afdde673 58441b358 -- specs/` empty).

## Implementation immutability (15 paths)

`git diff 3afdde673 58441b358` — **empty** for all shop-wide implementation and targeted test paths.
Blob SHAs @ merge HEAD (authoritative for archive):

| Path | SHA256 |
|------|--------|
| `app/modules/shop_runner/service_manager/manager.py` | `b953b0b49cf26a10a06b0b2e1ca342093a892f43` |
| `app/modules/shop_runner/service_manager/services/common_sale_stat_updater/common_sale_stat_updater.py` | `8ab3c3b9d2fb64b2f1f633ad40f0d32b866e75ef` |
| `app/modules/shop_runner/wb_shop.py` | `50a34600dffd1faefa6da4f87ef7dfd8d81043e0` |
| `pyrightconfig_strict.json` | `a84a2cfcf34ccfffbbdff6e4c801e45f411b1aa2` |
| `tests/modules/shop_runner/service_manager/test_common_sale_stat_updater.py` | `4205a73b107b1fe39f87ff8ff4ed71a27f08895e` |
| `tests/modules/shop_runner/service_manager/test_shop_wide_common_sale_stat_coordinator.py` | `6a3ae270f61dc8e4a41d6f824b348ff9d565bd89` |
| `tests/integration/test_shop_wide_common_sale_stat_coverage.py` | `ae00ec17a40a6599237a833610a022426263c76e` |
| `tests/test_wb_shop_run_coroutines.py` | `98e39d10670d33d8db29d7ce46f8ad0494b64bc8` |
| `app/modules/shop_runner/service_manager/services/shop_wide_common_sales/__init__.py` | `183cdc98dce233e029aa10dbe6edcb507356cc05` |
| `app/modules/shop_runner/service_manager/services/shop_wide_common_sales/collect_types.py` | `abcbd663f1cd883edababc9c70c16cace9ecc879` |
| `app/modules/shop_runner/service_manager/services/shop_wide_common_sales/coordinator.py` | `ec6ff1a8f83399e96a5dd57ab2a3e9c17469cc55` |
| `app/modules/shop_runner/service_manager/services/shop_wide_common_sales/coverage_evidence.py` | `35ee2e7d09a16777413aeb3982ba7b0ed38aa758` |
| `app/modules/shop_runner/service_manager/services/shop_wide_common_sales/fact_validator.py` | `066accd18b588f5aeb6bbea6c3c073e590c3c309` |
| `app/modules/shop_runner/service_manager/services/shop_wide_common_sales/legacy_assigned_nmids.py` | `52b1937e0799505aba7b4a561b3b34e49f72cc19` |
| `app/modules/shop_runner/service_manager/services/shop_wide_common_sales/shop_assortment_reader.py` | `1d66ad0f5986eddc6b941c5ec51d80713cf29afd` |
| `app/modules/shop_runner/service_manager/services/shop_wide_common_sales/taskgroup_no_ad_supervisor.py` | `06fa76390946e67a6b77d92b90528a2d6ec00867` |

## Post-merge execution bindings (0470 — SHA256 verified on disk)

| Suite | Log (in-repo) | SHA256 | Result |
|-------|---------------|--------|--------|
| Unit coordinator+updater+coroutines | `scenario-coverage/logs/postmerge-unit74.log` | `dabdc328345f73607d282e1de5ca8324201675e34260fbd5f399c5a4c6855d96` | **74 passed** |
| Integration CH destructive_local | `scenario-coverage/logs/postmerge-integration-ch.log` | `eb57f8a3fe9dab87c9b1ecb8e5ca1ca1091d83fafdec7a60a508c80bf1358a0d` | **2 passed** |
| Import sanity | `scenario-coverage/logs/postmerge-import-sanity.log` | `d3f9cbb8281216b975959ad1c04ae109cde871c4ee35ef911675cd6492ed29ca` | IMPORT_OK |
| openspec validate | `scenario-coverage/logs/postmerge-openspec-validate.log` | `2f85097fd2b8146d79dc24c9a34695e32482056381c39da96a154b7bfb69aa1b` | valid |

CH provider (S12): task `WB-SKY-COMMON-SALES-LIFECYCLE-20261005`, container
`wb-sky-common-sales-lifecycle-20261005-0470`, `127.0.0.1:8124`, user `CLICK_HOUSE_USER`,
password `password`, DB `test_adv_bot_clickhouse`. Fresh 0470 integration log supersedes
0260 log binding for post-merge freshness only.

## Scenario matrix lineage (33/33)

All 33 rows from historical `SCENARIO_TEST_COVERAGE_REPORT.md` (0260) remain **PASS** at merge HEAD:

- Test function names and production seams unchanged (`git diff 3afdde673 58441b358` empty on tests).
- L1–L8 lifecycle mapping unchanged (`design.md` Derived Lifecycle).
- S13/S14 caveats from 0260 audit notes preserved: static boundary + coordinator tick seams +
  S12 CH writer integration; placebo dedicated test not sole evidence.
- OUT_OF_SCOPE explicit: `METRICS_SOURCE_CURRENCY=unknown`, `STORE_DRR_NUMERATOR=BLOCKED`,
  `HISTORY_BACKFILL=DEFERRED`, live WB, prod CH DDL — not archive blockers.

## Pyright strict comparison (0475)

| Snapshot | filesAnalyzed | errorCount | archive_sha256 |
|----------|---------------|------------|----------------|
| premerge + 92 dirty overlay (`37d0ec5`) | 743 | 4 | `8374fc94…` |
| merged committed clean (`58441b358`) | 755 | **0** | `ac275042…` |
| actual stage + foreign dirty | 755 | 4 (foreign only) | — |

`diagnostic_parity=true`, `new_diagnostics=[]`. See `lifecycle-proof/comparison.json`.

## VERDICT

**PASS** — post-merge acceptance bridge. Historical 0260 certification preserved;
current bindings authoritative for archive verify at `58441b358`.
