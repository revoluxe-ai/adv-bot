## Context

A/B Hold уже в проде как отдельный paid режим со structural freeze. Пользователю нужен явный Emergency: остановить траты немедленно, не «тихо чиня» Hold. Hold ADL §18 запрещает emergency-stop / global refill suppression как часть Hold write-path — значит нужен новый change и proposed write-path decision.

Существующие кирпичи: `pause_adv`, keyword `hard_status` / bulk updates, `auto_budget_watchdog_enabled` / `ensure_budget` / `ensure_campaigns_active`, `const.SUPPORT_LINK`. Недостаёт: Hold-only UX + education + confirm + durable latch + carve-out для block-all под freeze + gate top-up/restart.

## Goals / Non-Goals

**Goals:**
- Hold-only Emergency UI + launch Confirm/ACK education + press confirm
- Pause + block-all keywords + durable latch (no top-up / no activity restart)
- Immediate support CTA via `SUPPORT_LINK`
- Idempotent latch; Keep Hold mode (no auto-EXIT to `OFF`)
- Proposed write-path ADL + tests

**Non-Goals:**
- Reopen `card-ab-hold-mode` DoD / smuggle into §18
- Self-serve clear latch / reset to ordinary (later + support)
- Pre-start picker, mid-sync UX, ordinary-campaign Emergency
- Rich audit/monitoring auto-stop

## Architecture Decision References

**Found (cite, do not amend as Hold ownership):**
- `openspec/changes/card-ab-hold-mode/decisions/card-ab-hold-write-path-ownership/decision.md` — §18 Forbidden emergency-stop / global refill-restart suppression **as A/B Hold write-path**; pause/restart activity-control orthogonal Allowed
- sibling Hold epoch / confirmed-params decisions (context only)

**Accepted registry:**
- `openspec/decisions/mode-defaults-policy-ownership/decision.md` — defaults ownership only; не закрывает Emergency write-path

**Architecture Decision Missing → proposed in this change:**
- `openspec/changes/ab-hold-emergency-kill-switch/decisions/ab-hold-emergency-kill-switch-write-path/decision.md`

## Ownership & Placement

| Concern | Owner layer | Forbidden |
|--------|-------------|-----------|
| Emergency UX (visibility, education, confirm, support CTA) | paid Telegram A/B Hold UI handlers/views | ordinary AdvSetting when Hold OFF; Free bot automation |
| Pause campaign | existing promotion/campaign pause adapters invoked by Emergency service | invent parallel WB pause client |
| Bulk keyword block | Emergency executor (carve-out) | ordinary `change_keyword_hard_status` / reset handlers under freeze |
| Latch SoT + gates | PG durable field on campaign/adv setting + reads in auto-budget / activity-control | toggle-only without SoT; hiding latch only in Redis without recovery story |
| Hold epoch/setup/freeze | остаётся у `card_ab_hold` | Emergency MUST NOT стать Hold financial safety model |

Placement matches proposed decision: Emergency capability owns kill switch; Hold keeps freeze; activity-control remains orthogonal but latch-aware.

## Decisions

1. **New change, not Hold update** — §18 + complete Hold DoD. Alternative (bound-scope reopen) отвергнут.
2. **Keep Hold + carve-out** вместо EXIT-then-block — сохраняет epoch/confirmed params; block-all только через Emergency executor.
3. **Durable latch field** (рекомендация: boolean/enum на `AdvSetting` или card_ab_hold state row) вместо «только выключить watchdog» — иначе нет идемпотентности/поддержки/later clear. Exact column name — apply task.
4. **ComplexAdv Search+Auto** — pause+block обе ноги пары. Single-leg out of MVP DoD.
5. **Support** — reuse `const.SUPPORT_LINK` (`https://t.me/sky_manager_1`).
6. **Education** — Confirm/ACK на launch; отдельно confirm на press (разрушительное действие).
7. **Serialize with dirty PBH WT** — apply не смешивать вслепую с незакоммиченными freeze gates; предпочесть после стабилизации PBH-009/010/011 или аккуратный non-overlapping touch list.

## Risks / Trade-offs

- [Partial keyword block / WB errors] → честный partial status; latch+pause всё равно ставить ASAP; не silent success
- [Activity-control fights pause] → latch gate обязателен в top-up/restart paths
- [Freeze vs block-all] → только Emergency carve-out; ordinary handlers остаются gated
- [Dirty WT collision] → не править те же freeze seams без нужды; tests-first
- [User expects undo] → MVP явно «пишите в поддержку»; later clear

## Migration Plan

1. Артефакты apply-ready (этот design + specs + decision + tasks)
2. Tests-first RED для visibility/education/confirm/latch gates
3. Implement UI + executor + latch + budget/activity gates
4. Bug hunt / soft verify
5. Rollout: hide behind Hold UI only (уже mode-gated); rollback = hide button + default latch false

## Open Questions

- ~~Точное PG поле latch (новое vs reuse flag)~~ — **Owner 2026-07-30:** KEEP оба PG columns
  `card_ab_hold_emergency_latch` + `card_ab_hold_emergency_educated`;
  NOT collapse to one column / Redis-only education in this change.
- Нужен ли prefilled `?text=` для support deep-link — желательно «Emergency / РК id», не блокер MVP

## Review Checklist

- [x] existing decisions searched
- [x] relevant decisions cited
- [x] new decision proposed if missing
- [x] implementation layer matches decision
