---
cursor:
  subagentId: "bc-dd262017-6b2a-5442-8d0b-efc3b81054ca"
---

# #447 post-merge — CAS `wb-sky-bot` (worker offline)

**Verified (cloud, 2026-10-01T00:24Z):**

| Field | Value |
|-------|--------|
| PR | [#447](https://github.com/revoluxe-ai/adv-bot/pull/447) **MERGED** → `stage` |
| Merge commit | `7f38008208dd915217fafb40d1487b3a3cbd9757` |
| Title | `fix(bot): message on stale create-both confirm (PAT-ADV-003)` |
| `origin/stage` tip | same as merge commit |
| Self-hosted workers | **0** (`cursor-cloud list-self-hosted-workers`) — `vkita-pc` offline |
| Stage deploy workflow | run `36795987990` — **success** (2026-10-01); image tag `7f3800820…` ready for CAS |

**Prod posture (from store + OPS_STATE):** entrypoints on `3693e936ea95871004749a9af688ba040afd6f1f` after `3693e936e-r1`; schema `d7e3c9f1a204` — **no migrate** for #447 (bot UX only).

## Blocker

`/opsx-devops` requires kubectl on **vkita-pc** (PowerShell, `prod-adv-bot`). Cloud agent cannot execute GO.

## CH verify (deferred)

Worktree: `C:\Users\vkita\my_code\meta-repo\clickhouse-migrations-control-plane`

When worker online, **read-only first:**

```text
/opsx-verify mode=impl clickhouse-migrations-control-plane
```

(Do not run on cloud VM.)

---

## Exact PLAN_WRITE packet (copy on vkita-pc)

**Pre-step (INVESTIGATE):** confirm stage CI green for `7f3800820…`; resolve platform digest (Harbor pull-through or `PROVENANCE_MODE=registry_manifest` per `DEVOPS_DB_MIGRATIONS.md`). Registry path from OPS_STATE:

`harbor.skyline360.ru/git-registry-cache/revoluxe-ai/adv-bot:7f38008208dd915217fafb40d1487b3a3cbd9757`

**PLAN_WRITE** (scoped image CAS — **only** `wb-sky-bot`; skip CONTROL/Migrate — schema unchanged):

```text
/opsx-devops INVESTIGATE ns=prod-adv-bot focus=deploy/wb-sky-bot symptom=post-447-stale-confirm-ux
/opsx-devops PLAN_WRITE intent=image_cas ns=prod-adv-bot resource=deploy/wb-sky-bot image=harbor.skyline360.ru/git-registry-cache/revoluxe-ai/adv-bot:7f38008208dd915217fafb40d1487b3a3cbd9757 digest=sha256:<RESOLVE_ON_PC>
```

Plan body must state:

1. **SKIP** CONTROL acquire / migrate Job (`alembic` already `d7e3c9f1a204` @ prod).
2. **CAS** JSON Patch `test`+`replace` image on Deployment `wb-sky-bot` only (not phased all-entrypoints).
3. **SKIP** `complete_release` unless an open lease exists (tech-debt: pending from `3693e936e-r1` — reconcile in same hop if INVESTIGATE shows held lease).
4. **VERIFY:** pod Running; stale `ce_create_both:confirm` → user-visible PAT-ADV-003 message (not silent not-handled).
5. **OPS_STATE:** append action log line for partial CAS; do **not** claim all entrypoints on `7f3800820…` unless intentionally rolling others. Full LKG/meta-commit → `/opsx-meta-commit` when Owner wants durable drift fixed ([#444](https://github.com/revoluxe-ai/adv-bot/pull/444) policy).

**GO** (only after PLAN_WRITE + Owner GO gate):

```text
/opsx-devops GO intent=image_cas ns=prod-adv-bot resource=deploy/wb-sky-bot image=harbor.skyline360.ru/git-registry-cache/revoluxe-ai/adv-bot:7f38008208dd915217fafb40d1487b3a3cbd9757 digest=sha256:<SAME_AS_PLAN>
```

**Rollback:** failed CAS → master LKG from OPS_STATE (`4d5fae43…` / prepared fallback) per [deploy-rollback-policy.md](/cursor/stores/self/internal/deploy-rollback-policy.md).

## Related

- [adv-bot-incident-138252141-campaigns.md](/cursor/stores/self/docs/adv-bot-incident-138252141-campaigns.md)
- [adv-bot-next-hop-menu-20260930.md](/cursor/stores/self/internal/adv-bot-next-hop-menu-20260930.md)
