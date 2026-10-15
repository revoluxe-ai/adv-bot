# PR #443 diff categorization (2026-09-30)

| Категория | Содержимое |
|-----------|------------|
| **Hotfix (инцидент 138252141)** | `93669ece7` / `3693e936e` on `stage` — `tasks.py` best-effort Telegram + unit test |
| **Scripts ops-lane** | merge `scripts` branch — `scripts/`, `tools/`, generated WB API, openspec, `k8s/jobs/ops-script-runner` |
| **Не hotfix** | migration-gates triggered by k8s paths, not alembic in fix |

**Track after split ([PR443 split and scripts policy](bc-d10119a7-57d6-59fe-bf62-d79ef813b286)):**

- Deploy fix: **build from `stage` tip** (`3693e936e`), **не** merge fat #443
- [#445](https://github.com/revoluxe-ai/adv-bot/pull/445) — narrow PR draft; fix already on `stage` → close #445 optional
- [#446](https://github.com/revoluxe-ai/adv-bot/pull/446) — `AGENTS.md` scripts ops-lane + migration-gates path fix
- [#443](https://github.com/revoluxe-ai/adv-bot/pull/443) — superseded; avoid merge
