# ARCHITECT_HANDOFF — portfolio reconciliation (coordinator)

**Baseline:** `origin/stage` = `d2166b2d805b27a6656f46c6ccb8e56066b4e888`  
**Reconciled:** 2026-10-06 (GitHub PR heads)

## Canonical active changes

| Change ID | Authority | HEAD (GitHub) | Lifecycle | Blocker | Next allowed action |
|-----------|-----------|---------------|-----------|---------|---------------------|
| `campaign-settings-changeset-contract` | PR [#449](https://github.com/revoluxe-ai/adv-bot/pull/449) | `bf0abd01ab036e7227013fb1e01df325f66bc42c` | **CURRENT_HEAD_UNVERIFIED** | Independent verify not executed on cloud (fetch/DNS); not a code defect claim | HOME-PC: read-only independent verify on exact HEAD; no Apply |
| `wb-sky-mcp-read-interface` | PR [#452](https://github.com/revoluxe-ai/adv-bot/pull/452) | `fb5410ad2815e3529d55058d729ac6ac27dc84b0` | **PROVIDER_CERT_BLOCKED** | `c2cb978` = ancestor (+2 commits to HEAD); uncommitted PG tests; live run ERROR (no Docker); one-shot auth consumed; fingerprint fail-closed | Re-audit on `fb5410ad`; fix run-block semantics; new `AUTHORIZE_ONE_LIVE_RUN`; push tests then certify |
| `ai-package-multi-window-analysis` | PR [#453](https://github.com/revoluxe-ai/adv-bot/pull/453) | `e55d94cdd07a7cd2b0cb198a97a37a6a24f6dcac` | **IMPL_OK** | Merge blocked until OPSX chain | `/opsx-pyright-strict-coverage` → `/opsx-verify`; no attribution/shop collectors |
| `ai-package-full-export-contract-repair` | PR [#450](https://github.com/revoluxe-ai/adv-bot/pull/450) | `19ec4bf5ac0a6e16a1c43699a01232dc2d55cbd9` | **ACCEPTANCE_REPORTED** | Not merged; no fresh reconcile in this run beyond HEAD match | Confirm still current; Owner GO for merge when ready |
| `telegram-ai-package-export` (PR) | PR [#454](https://github.com/revoluxe-ai/adv-bot/pull/454) | `f33d32587e0e3684b791357152bf76664bd668d8` | **READY_FOR_REVIEW** (draft=false) | Not merged; scope vs #450 | Review; merge after #450 policy clear; HOME-PC re-verify if needed |
| `telegram-ai-package-export` (local) | Worker-only | `381fb1d2` **not on GitHub** | **STALE / NON-AUTHORITY** | Duplicate implementation path | Do not merge; close worker chat after abandoning local tree or cherry-pick diff into #454 only via new PR |
| `separate-auto-search-cpo` | Branch `cursor/separate-auto-search-cpo-clean-a089` | `f6c18bb76843a73a0ec929d087592d50d6dcedad` | **STATIC_OK / LIVE_BLOCKED** | Live ClickHouse | Read-only live CH cert on this HEAD only; not `origin/separate-auto-search-cpo` @ `9b97462` |

## Planning-only (no PR authority)

| Change | State | Blocks |
|--------|-------|--------|
| `campaign-attribution-facts` | Planning doc ready | DIRECT/LINKED CPO/DRR; shop DRR narrative in #453 |
| `changeset-apply-authority` | Planning doc ready | Future PG-only Apply V1; **not** #449 |

## MCP HEAD reconciliation

- **Authoritative:** `fb5410ad` (PR #452).
- **`c2cb978`:** protocol/OAuth repair — **included** (compare: 2 commits ahead, 0 behind).
- **`347edeb`:** parent of plan refresh commit on branch.
- Do not certify against `c2cb978` alone; do not treat ERROR receipts from failed Docker run as certifying.

## Duplicate scope: #454 vs `381fb1d2`

| | [#454](https://github.com/revoluxe-ai/adv-bot/pull/454) `f33d325` | Local `381fb1d2` |
|---|-----|-----|
| On GitHub | Yes | **No** |
| ADR `ai-package-telegram-export-surface` | Accepted in PR path | Reported local only |
| Authority | **Use this** | Historical worker attempt; risk of drift |

**Rule:** One feature `telegram-ai-package-export` → one authority = **#454**. Close or archive chats tied only to `381fb1d2` push path.

## Suggested merge / dependency order (architecture; Owner GO each)

1. **#450** — export contract (enables external AI package semantics).
2. **#454** — Telegram transport (depends on canonical `PackageZipAssembler`; no second exporter; after #450 conflict check).
3. **#453** — multi-window (after pyright-coverage + verify; independent of attribution for in-scope metrics).
4. **#449** — ChangeSet dry-run validation.
5. **#452** — MCP read (after PG provider certify on `fb5410ad`).
6. **`separate-auto-search-cpo-clean`** — after live CH read-only cert.
7. **Attribution facts** — new change after planning GO (unblocks shop/direct-linked economics).
8. **Apply authority** — separate from #449.

## Chats

**Keep open (active execution):**

- `wb-sky-mcp-read-interface` — [bc-1334b977](bc-1334b977-28ff-5e36-8226-4f0b5f5822ef)
- `ai-package-multi-window-analysis` — [bc-f1a938ec](bc-f1a938ec-b96c-542b-a160-d4eed30cd108)
- `campaign-settings-changeset-contract` — [bc-fec0e994](bc-fec0e994-47b5-5444-a715-50af2fa4d241) (verify pending)

**Safe to close / historical:**

- Chats only for `381fb1d2` local telegram path (superseded by #454).
- Stopped duplicate workers (HEAD_CHANGED multi-window, blocked cloud MCP test-only clone) once no uncommitted work needed.
- `wt-ai-*` decomposition chats — design-only unless reactivated.
- Closed: campaign settings history/snapshot; ai-package-v1-contract archive.

**Coordinator / Web:**

- This Project = execution portfolio; Web = priority/architecture only.

## No writes

Coordinator performed **read-only** GitHub reconciliation. No merge, deploy, or repo edits.
