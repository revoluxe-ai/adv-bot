# adv-bot `scripts/` — ops-lane (Owner 2026-09-30)

**USER_ASSERTED:** `scripts/` (и связанные ops-артефакты) — **вне OPSX product gates**; быстрые одноразовые скрипты, не участвуют в product merge policy как обязательные проверки.

**FACT (#443):** ветка hotfix вмержила **`scripts`** (`merge(scripts): b79534379`) — сотни файлов `scripts/`, `tools/`, generated WB API, openspec, `k8s/jobs/ops-script-runner`. **Hotfix инцидента** — один коммит `93669ece7` (`tasks.py` + test). Не смешивать merge #443 с выкатом только фикса.

**CI:** path filter `migration-gates` может сработать из‑за `k8s/jobs/` (ops-script-runner), не из‑за alembic в фиксе.

**После split ([PR443 split and scripts policy](bc-d10119a7-57d6-59fe-bf62-d79ef813b286)):** фикс на `stage` (`3693e936e`); политика/CI — draft [#446](https://github.com/revoluxe-ai/adv-bot/pull/446); категоризация — [pr443-diff-categorization-6147.md](pr443-diff-categorization-6147.md). **Не merge #443** для выката инцидента.
