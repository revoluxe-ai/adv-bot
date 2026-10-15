# WB Sky — handoff в Cursor Project

**Источник Owner:** [Стратегия доработки](https://chatgpt.com/g/g-p-697378a716cc8191ae57b55d0538370d/c/6ab79cf8-6218-83eb-be18-c12ab40fceae) (Web ChatGPT).  
**Принято:** turn в [OPSX DevOps campaign investigation](bc-2b4a5d73-52a9-5463-9d04-00996d1a6147) **aborted** — полный текст в уведомлении **обрезан**; этот файл — якорь + снимок из начала handoff. Дополнить из чата при необходимости.

## Правила из handoff (USER_ASSERTED)

- Продолжать через **OPSX lifecycle**; один **change** = отдельный результат.
- Сначала: `git status`, HEAD, worktrees, `AGENTS.md`, OpenSpec, проверки.
- Снимок в handoff: **2026-10-03**; пути UTF-8; **не** смешивать незавершённые changes; не очищать dirty без Owner.
- Запуск агента / зелёные тесты / сообщение ≠ завершение change.

## Локальное состояние (из handoff, проверить на vkita-pc)

| Поле | Значение в handoff |
|------|---------------------|
| Repo | `C:\Users\vkita\my_code\meta-repo\adv-bot` |
| Branch | `stage` |
| HEAD (handoff) | `62c8d48b15498997b84357e015b0e688f44fd37b` |
| Dirty | A1/control-plane, AI package, OPSX (не переносить/не чистить вслепую) |

**FACT (cloud, 2026-10-01):** `origin/stage` = `4763b0a1602d00da285739f2be9af5a553ef3c0a` — **перепроверить** локальный HEAD vs remote после handoff.

## Уже в Project store (до полного handoff)

- Стратегия: [chatgpt-strategy-adv-bot-6abd1faa.md](chatgpt-strategy-adv-bot-6abd1faa.md)
- Роль: [adv-bot-strategic-coordinator-role.md](adv-bot-strategic-coordinator-role.md)
- Инцидент 138252141: RESOLVED; #447 merged — [deploy plan](/cursor/stores/self/internal/adv-bot-447-post-merge-deploy-plan-20261001.md)
- Next hops: [adv-bot-next-hop-menu-20260930.md](/cursor/stores/self/internal/adv-bot-next-hop-menu-20260930.md)

## Coordinator

Не перезапускать aborted [OPSX DevOps campaign investigation](bc-2b4a5d73-52a9-5463-9d04-00996d1a6147) без явной просьбы. Новые hops — новый worker / этот Project.
