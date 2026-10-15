# Техдолг (не P0) после инцидента 138252141

Owner 2026-09-30 — не в первую очередь.

| Item | Route |
|------|--------|
| Stale `ce_create_both:confirm` UX | [#447](https://github.com/revoluxe-ai/adv-bot/pull/447) merged → deploy `wb-sky-bot` pending — [plan](adv-bot-447-post-merge-deploy-plan-20261001.md), [PAT-ADV-003](recurring-patterns.md) |
| OPS_STATE / LAST.json после `3693e936e-r1` | `/opsx-meta-commit` |
| `complete_release` lease (Job pending) | `/opsx-devops` |
| OPS_STATE LKG drift vs live | INVESTIGATE + [#444](https://github.com/revoluxe-ai/adv-bot/pull/446) policy |

Repo mirror: `DOTO/WORKLOG.md` (local adv-bot).

**WORKLOG encoding (2026-09-30):** верх INBOX (~стр. 2–40) — исторический mojibake в git; низ (~850+) UTF-8 OK, техдолг 138252141 читаем. Не prod; repair — отдельная не-P0 задача (не править 800+ строк вслепую).
