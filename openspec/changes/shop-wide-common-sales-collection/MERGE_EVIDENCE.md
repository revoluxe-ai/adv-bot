# MERGE_EVIDENCE

```yaml
TASK_ID: WB-SKY-COMMON-SALES-MERGE-POSTVERIFY-20261005-0470
CHANGE_ID: shop-wide-common-sales-collection
MODE: bounded local merge + post-merge verify
EXECUTOR: lifecycle-merge-postverify-0470
CREATED_AT: 2026-10-05T05:15:00+03:00
```

## Pre-merge state (verified)

| Check | Result | Evidence |
|-------|--------|----------|
| Branch | **PASS** | `stage` |
| Pre-merge HEAD | **PASS** | `37d0ec5fce9acae46eb0b35dda7c0fea7b9845a0` (unchanged from preflight snapshot) |
| Index empty | **PASS** | `git diff --cached` empty; snapshot `premerge-index-diff.txt` empty |
| Feature tip exact | **PASS** | `shop-wide-common-sales-collection` → `2ccff6321700499c22cbc1a1f5b5541cb8683fef` |
| Foreign dirty count | **PASS** | 92 lines (`git status --porcelain=v1 -uall`); matches preflight JSON |
| MERGE_HEAD absent | **PASS** | `NO_MERGE_HEAD` before merge |
| Feature worktree clean | **PASS** | worktree HEAD `2ccff6321`, `git status` empty |

## Provenance correction (92 vs 29)

Prior independent review receipt (`FINAL_MERGE_REVIEW_RECEIPT.json`) records `STAGE_DIRTY_COUNT: 29` alongside `STAGE_DIRTY_COUNT_PREFLIGHT: 92`. These are **not** concurrent deltas:

- **29** — ordinary `git status` directory aggregation (collapses untracked directories to one line each).
- **92** — authoritative preflight count with `git status --porcelain=v1 -uall` (every file enumerated).

Root fresh snapshot: `C:\Users\vkita\my_code\cursor-sdk-task-runner\runs\WB-SKY-COMMON-SALES-LIFECYCLE-PREFLIGHT-20261005-0445\stage-premerge-snapshot.json` — 92 entries, byte hashes recorded. Post-merge re-verification: **0 hash mismatches** across all 92 foreign paths.

## Overlap

| Scope | Overlap with stage dirty | Result |
|-------|--------------------------|--------|
| Feature paths (39, shop-wide-common-sales) | 0 | **PASS** (per FINAL_MERGE_REVIEW) |
| Full branch delta vs dirty | ai-package spec/test paths overlap dirty M-files; merge succeeded without conflict resolution | **PASS** (ort auto-merge) |

## Merge execution

```
git merge --no-ff --no-edit shop-wide-common-sales-collection
→ Merge made by the 'ort' strategy. (no conflicts)
```

| Field | Value |
|-------|-------|
| Merge commit | `58441b3589200e02f642628e05920e680e553355` |
| Parent 1 (stage) | `37d0ec5fce9acae46eb0b35dda7c0fea7b9845a0` |
| Parent 2 (feature tip) | `2ccff6321700499c22cbc1a1f5b5541cb8683fef` |
| Merge message | `Merge branch 'shop-wide-common-sales-collection' into stage` |

## Ancestor proofs (post-merge)

```powershell
git merge-base --is-ancestor 2ccff6321700499c22cbc1a1f5b5541cb8683fef HEAD  # exit 0
git merge-base --is-ancestor 3afdde673e667cc725131cab7f463db7e2b34b66 HEAD  # exit 0
```

| Commit | Role | SHA |
|--------|------|-----|
| Feature tip (QA docfix) | `2ccff6321700499c22cbc1a1f5b5541cb8683fef` | ancestor of merge HEAD ✓ |
| Implementation | `3afdde673e667cc725131cab7f463db7e2b34b66` | ancestor of merge HEAD ✓ |

## Stage log (last 10 post-merge)

```
58441b358 Merge branch 'shop-wide-common-sales-collection' into stage
2ccff6321 docs: independent final merge review PASS for shop-wide common sales
0945a5d52 docs: normalize common sales lifecycle evidence
3afdde673 feat: collect shop-wide common sales
37d0ec5fc Merge branch 'ai-package-campaign-settings-snapshot' into stage
e5e3a7126 feat(ai-package): add campaign settings snapshot export
62c8d48b1 Merge WORKLOG
481e9f639 Update TODO
905bb6034 docs(doto): log clickhouse migration control plane work
08cff2844 chore(ci): extend strict pyright to migration package
```

## Foreign dirty preservation (post-merge)

| Check | Result |
|-------|--------|
| Status line count | 92 (unchanged vs pre-merge snapshot) |
| `Compare-Object` pre/post porcelain | **identical** (no diff lines) |
| SHA256 vs preflight JSON (92 entries) | **0 mismatches** |
| Index staged | **empty** |
| HEAD changed | yes → `58441b358…` (expected merge commit) |

## Artifacts (outside repo)

Run directory: `C:\Users\vkita\my_code\cursor-sdk-task-runner\runs\WB-SKY-COMMON-SALES-MERGE-POSTVERIFY-20261005-0470\`

- `premerge-status-porcelain.txt`
- `premerge-index-diff.txt`
- `premerge-head.txt`
- `premerge-branch.txt`
- `premerge-merge-head.txt`
- `premerge-status-linecount.txt` (92)

## Archive verify addendum (0480)

| Field | Value |
|-------|-------|
| TASK_ID | `WB-SKY-COMMON-SALES-ARCHIVE-VERIFY-20261005-0480` |
| ARCHIVE_VERIFY | **GO** |
| POST_MERGE_VERIFY | **PASS** (CHANGE_SCOPED) |
| PRODUCT_ACCEPTANCE | **PASS** (MEANING_LOCK + LIFECYCLE + SIDE_EFFECT) |
| Pyright committed merge | 755 files, **0 errors** (`lifecycle-proof/comparison.json`) |
| Pyright foreign baseline | 4 errors, adapter.py only — **no new diagnostics** |
| QA evidence | `VERIFY_ARCHIVE_RECEIPT.md`, `CURRENT_SCOPE_AUDIT_CERTIFICATION.md` |

Durable in-repo logs copied from 0470 runner → `scenario-coverage/logs/postmerge-*`.
Strict comparison JSON → `lifecycle-proof/`.

## Constraints honored

- No stash / reset / clean / commit-all / force / push / rebase
- No conflict resolution performed (clean ort merge)
- Feature worktree unchanged at `2ccff6321`
- No archive / decision promotion (0480 verify only; archive awaits `/opsx-archive`)
