# DOC_FORMAT_PROVENANCE

TASK_ID: WB-SKY-COMMON-SALES-LIFECYCLE-DOC-FIX-20261005-0452
CHANGE_ID: shop-wide-common-sales-collection
MODE: documentation formatting only (no runtime/test/config/log changes)

## Purpose

Record preimage SHA256 values from implementation commit `3afdde673e667cc725131cab7f463db7e2b34b66`
(2026-10-05T04:47:58+03:00, `feat: collect shop-wide common sales`) and the post-normalization
SHA256 values after trailing-whitespace removal. Semantic content is unchanged; only whitespace
and truthful provenance metadata differ.

Implementation commit `3afdde6` is preserved in history — no amend, rebase, or evidence removal.

## Gate failure (real, feature-introduced)

Plain `git diff 62c8d48..3afdde6 --check` exited **2** on trailing whitespace in 10 files.
All were new tracked files introduced by the feature commit; none existed on base `62c8d48`.
This was not a pre-existing waiver.

## File preimage → post-normalization

| File | `3afdde6` SHA256 | Post-normalization SHA256 |
|------|------------------|---------------------------|
| `.opsx/runs/scenario-coverage/shop-wide-common-sales-collection/receipts/PROVIDER-a3f8c2e1b904d7a6.md` | `accdc98d979367c85ab2ad5ea05f4c5ab946ad2b473b93cfbb0c8287ea932ed9` | `ab85e96bef0209db7a9e220f7aaa3ef578d5fb9cde366a93ff4b8951c3ccd97d` |
| `openspec/changes/shop-wide-common-sales-collection/PREMERGE_SCOPE_RECEIPT.md` | `1dca828f5e8d5097cb22108755dfa4e5d8722b6c9fa488d362c0b59b984025c5` | see doc-fix commit |
| `openspec/changes/shop-wide-common-sales-collection/SHOP_WIDE_COMMON_SALES_PLANNING_REPORT.md` | `48f476553239f421ac718bb063d640486effca0538b7a5ea270fe783ff0d7956` | `6885d96fc6e21cbc02dae427e91a49a6767747f26f271476f62e19250b1845ed` |
| `openspec/changes/shop-wide-common-sales-collection/decisions/shop-wide-common-sales-ownership/decision.md` | `24ef9a0cca8ee38c19911d85f7bf729cc769bc67562a4b13d0e88116a7b456fc` | `8ed38b4409e0fadf6828a66e571ca3bea7a7d647bf727fe1c2bef4ebd14167a6` |
| `openspec/changes/shop-wide-common-sales-collection/design.md` | `ecf4921d8a77812bc3e3baeee6f43efe2093b2d7ec271126cc68b156d91df874` | `288fd52afd0a7c6df06f232520e18c50cf0aaf4ed7ce17d7a22926d19a56fa18` |
| `openspec/changes/shop-wide-common-sales-collection/scenario-coverage/case-to-test-index.md` | `1f9d9d8adad5c9fbe9e3283ae81cdb4a65a43d205dad44a0414473ee3a35e607` | `437c85c27d22e05b5ecf699d86b75bec1a50122219e8589df299f348b5c915a6` |
| `openspec/changes/shop-wide-common-sales-collection/scenario-coverage/execution-envelope.md` | `01b788afa7d5e891e87fff514a09a0275de3d8aea4bae5f1e304ad8caba7054a` | see doc-fix commit |
| `openspec/changes/shop-wide-common-sales-collection/scenario-coverage/log-manifest.md` | `ca7e3144a3fd47350137307a42e51c828e670386172b17e2990af13c902e9f85` | `56fbd29f86fb89ef41ffc118dc590dabe163de1b13586c703d85699671b26eaf` |
| `openspec/changes/shop-wide-common-sales-collection/scenario-coverage/verify-impl.receipt.md` | `ba0690e07ce8ef2e0005b862df934f92c6856ffed68c6139be36d2d329995162` | `f439870cd2bf5cb847404e5e7247763dd7c4841a2da0ae4a9f03b206ee69b592` |
| `openspec/changes/shop-wide-common-sales-collection/tasks.md` | `327feab54339ba3cbd7de5b214648789bc8024fb30b9f4298dcd98e8b4643db9` | `78afd56fda899208d85d99c0a915234ed9d6546b1a8103863bb740f12a5ccbe6` |

Whitespace-only files: trailing spaces removed from metadata header lines and `design.md` footer.
Additional provenance corrections in `PREMERGE_SCOPE_RECEIPT.md` and `execution-envelope.md`
(section symbol replaced with plain "section"; design hash lineage documented; timestamps corrected
to observed implementation commit time 2026-10-05T04:47:58+03:00).

## design.md hash lineage

| Stage | SHA256 | Delta |
|-------|--------|-------|
| evidence-close envelope (`execution-envelope.md` original binding) | `07ea6d4d241eae80785b53ee3b7ae2d36f750b8ed3def29e5eeb4dd03c4929c9` | pre-implementation footer |
| `3afdde6` implementation commit | `ecf4921d8a77812bc3e3baeee6f43efe2093b2d7ec271126cc68b156d91df874` | +DESIGN_STATUS footer with trailing ws |
| post doc-format normalization | `288fd52afd0a7c6df06f232520e18c50cf0aaf4ed7ce17d7a22926d19a56fa18` | trailing ws removed only |

## Immutable certified core (byte-unchanged by this task)

| Artifact | SHA256 |
|----------|--------|
| `specs/shop-wide-common-sales-collection/spec.md` | `5e24eabdaa2f6bf4daaa494ea6bbca5da73dd443e0540d7568acbca78b508253` |
| `scenario-coverage/plan.md` | `c7e5882345385f9f1c39dc2e252b58c0b10a2c9319efab9a1ad16cb1f834d4a0` |
| `scenario-coverage/SCENARIO_TEST_COVERAGE_REPORT.md` | `d145f7816dd556176f29b375db820f2b49c9803c4f480ec6dffc0cd9794e6bf0` |
| `scenario-coverage/certify.receipt.json` | `4e4ac8c69108054e29e056ca999c2a8daa148c2d07135c3da34a12a4de89f106` |

## Implementation paths and logs (byte-unchanged)

15 implementation source/test/config paths and 4 raw execution logs retain exact bytes from
`3afdde6`. See `PREMERGE_SCOPE_RECEIPT.md` for SHA256 table.

## Acceptance target

- `git diff 62c8d48..HEAD --check` → exit 0
- `git diff HEAD^..HEAD --check` → exit 0 (doc-fix commit only)
- No Git whitespace config / `.gitattributes` weakening
