# Decision: ab-hold-emergency-kill-switch-write-path

## Status

Proposed

## Context

A/B Hold (`card-ab-hold-mode`) вводит structural freeze и в ADL §18 явно запрещает новую emergency-stop / global refill-restart suppression подсистему **как часть** Hold write-path. Anti-drain kill switch нужен продукту, но reusable ownership не должен «протаскиваться» через reopen Hold DoD. Нужен отдельный write-path decision: кто пишет pause / bulk keyword block / durable latch, и как это соотносится с Hold freeze.

Accepted registry не содержит emergency kill-switch ownership (`Architecture Decision Missing` до этого proposed artifact).

## Decision

Emergency kill switch для кампаний в A/B Hold принадлежит **отдельному owned write-path** capability `ab-hold-emergency-kill-switch`, а не A/B Hold epoch/setup/freeze ownership.

1. **Visibility / UX** — paid Telegram UI слоя A/B Hold (Hold-only screens + launch education); ordinary AdvSetting при Hold `OFF` MUST NOT владеть Emergency.
2. **Pause campaign** — переиспользует существующий campaign pause adapter (`pause_adv` / promotion pause), ортогонально Hold freeze.
3. **Bulk keyword block** — owned Emergency carve-out относительно Hold structural freeze: обычные Telegram/handlers hard_status/reset пути остаются Forbidden under freeze; Emergency executor MAY писать block-all как единственный разрешённый structural block path при активном Emergency.
4. **No top-up / no restart** — durable Emergency latch в SoT кампании/настройки; activity-control и auto-budget MUST читать latch и MUST NOT top-up/restart пока latch ACTIVE.
5. **Hold mode** — Emergency MUST NOT означать автоматический EXIT Hold в `OFF`; снятие latch / возврат в ordinary — отдельный later/support path, не silent resume.
6. **Support contact** — UI MUST использовать `const.SUPPORT_LINK` (чат администратора), без нового support-канала в этом decision.

Этот decision **не** отменяет и **не** расширяет Hold §18: Hold по-прежнему MUST NOT владеть emergency как своим financial safety model; Emergency — follow-on capability со своим ownership.

## Applies to

- Capability `ab-hold-emergency-kill-switch`
- Paid Telegram A/B Hold menus / launch education / Emergency handlers
- Campaign pause adapters
- Keyword hard_status / bulk block executor used by Emergency
- Auto-budget / activity-control gates that consult Emergency latch
- Durable SoT поля latch (PG или эквивалент, выбранный в design)

## Allowed

- Hold-only кнопка Emergency при mode ≠ `OFF`
- Confirm-on-press → pause + block-all + set latch
- Emergency executor как единственный freeze carve-out для block-all under Hold
- Чтение latch в `ensure_budget` / `ensure_campaigns_active` (или эквивалентных gate-точках)
- Показ `SUPPORT_LINK` на результате Emergency
- Идемпотентный no-op при уже ACTIVE latch

## Forbidden

- Добавлять emergency-stop / global refill suppression **внутрь** A/B Hold write-path ADL как owned Hold behavior (нарушение §18)
- Показывать Emergency при Hold `OFF`
- Разрешать ordinary Telegram hard_status/reset/add-phrases paths под видом Emergency
- Считать одной паузы РК достаточным без latch (activity-control может снова start+top-up)
- Тихий resume / auto-clear latch без явного later/support сценария
- Прятать ownership только в design.md без decision artifact

## Examples

**Good:** Telegram Emergency confirm → Emergency service ставит pause через `pause_adv`, пишет block-all через owned executor, ставит `emergency_latch=ACTIVE`; `ensure_budget` видит latch и пропускает top-up.

**Bad:** Вшить «emergency» в `process_ab_setup` / Hold §18 как financial safety Hold; или выключить только watchdog toggle без durable latch; или дать `change_keyword_hard_status` пользователю под freeze «потому что emergency».

## Related specs

- `openspec/changes/ab-hold-emergency-kill-switch/specs/ab-hold-emergency-kill-switch/spec.md`

## Related changes

- `openspec/changes/ab-hold-emergency-kill-switch` (этот change)
- `openspec/changes/card-ab-hold-mode` — источник §18 Forbidden; не reopen DoD

## Review checklist

- [x] existing decisions searched
- [x] relevant decisions cited (`card-ab-hold-mode/decisions/card-ab-hold-write-path-ownership` §18)
- [x] new decision proposed because accepted decision was missing
- [x] implementation layer matches decision
  (Emergency owns `emergency.py` + telegram handlers + latch PG;
  Hold §18 untouched; activity-control/auto-budget only read latch gates)
