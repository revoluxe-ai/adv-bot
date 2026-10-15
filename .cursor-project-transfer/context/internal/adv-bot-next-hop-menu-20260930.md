# adv-bot — меню следующего hop (Owner choice)

Зафиксировано в [OPSX DevOps campaign investigation](bc-2b4a5d73-52a9-5463-9d04-00996d1a6147) 2026-09-30.

**Хвост инцидента:** [#447](https://github.com/revoluxe-ai/adv-bot/pull/447) **merged** (`7f3800820`) → CAS `wb-sky-bot` **pending** ([plan](/cursor/stores/self/internal/adv-bot-447-post-merge-deploy-plan-20261001.md)). Опц. [#446](https://github.com/revoluxe-ai/adv-bot/pull/446), [#444](https://github.com/revoluxe-ai/adv-bot/pull/444). Закрыть #443. Ops: complete_release, OPS_STATE meta-commit.

**Близость к готовности (2026-09-30):**

1. **CH control plane** — apply 31/31 → `/opsx-verify mode=impl clickhouse-migrations-control-plane` (самый зрелый крупный change)
2. **#447** — merge + CAS `wb-sky-bot` (быстрый UX hotfix)
3. **fix-search-cpc** — 36/39; блокеры §8.3 CH, §8.5 audit до verify
4. **#446 / #444** — process/docs, лёгкий merge

Далеко: web-admin-v0, shop-wide, #443, drr-percent-cpo, ai-package-v1.

**Owner 2026-09-30:** закрывать с самого готового → **только `stage`**, **master не трогать**.

**Порядок старта:**
1. **#447** — **MERGED** (`7f3800820`) → выкат `wb-sky-bot` по [deploy plan](adv-bot-447-post-merge-deploy-plan-20261001.md) ([Finish #447 and CH verify](bc-dd262017-6b2a-5442-8d0b-efc3b81054ca))
2. **#446 / #444** → merge в `stage` (process, опционально параллельно)
3. **CH control plane** → `/opsx-verify` в worktree → merge в `stage` (крупный P0)
4. Закрыть/игнорировать **#443**

**Primary (один hop):** начать с **`#447`**

Карта: [safe-continue-plan.md](/cursor/stores/self/docs/safe-continue-plan.md), [strategic role](/cursor/stores/self/docs/adv-bot-strategic-coordinator-role.md).
