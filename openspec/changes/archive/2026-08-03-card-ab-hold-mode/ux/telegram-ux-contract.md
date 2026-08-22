# Telegram UX Contract — A/B Hold WARM_UP / Confirm / Epoch Flow

## 0. Status and scope

This is a **planning-level UX contract** (`/opsx-continue` continuation of `DEFERRED_TO_OPSX_CONTINUE` from
`proposal.md` / `design.md`). It is **not** implementation and does not authorize `/opsx:apply` for
`tasks.md` §19–25 (still blocked on owner authorization). It does not reopen financial scope: no hard
cap, no epoch spend cap, no velocity cap, no financial latch is introduced anywhere in this document.
It does not close **OD-05** (broad-enablement gate) and does not create monitoring/alerting or
emergency-stop artifacts — those remain `OUT_OF_SCOPE_FOLLOW_ON` per `proposal.md`.

Semantic source of truth for this contract: owner-approved product requirements as already encoded in
`specs/card-ab-hold-mode/spec.md`, `design.md`, and the decisions
`ab-hold-epoch-lifecycle-and-generation-ownership` and `ab-hold-confirmed-epoch-parameters-sot` (both
`Proposed`). Where this contract must choose a concrete screen/keyboard/callback shape not dictated by
those documents, the choice is UX planning detail, consistent with — and traceable to — those documents.

**The existing `card_ab_hold` MVP-1 Telegram screen (`app/modules/shop_runner/service_manager/services/auto_updater_v3/card_ab_hold/telegram/`) is explicitly NOT the reference for this contract.** It is
cited below only to name the concrete anti-patterns this contract must not repeat (§14).

Durable field/migration names for WARM_UP timer, epoch/generation, confirmed-parameter storage, and
PENDING-intent storage are **implementation detail of a future `/opsx:apply`** (design.md Open Question
1) and are intentionally not fixed by this contract. This contract fixes the **screen, state, keyboard,
callback, and transition contract** the implementation must satisfy, independent of exact schema.

## 1. Terminology

| Term | Meaning in this contract |
|---|---|
| **Mode** | Existing durable coarse state of the campaign: `OFF` / `PENDING_SETUP` / `ACTIVE` (`CardAbHoldMode`, applied MVP-1). Unchanged by this contract. |
| **Phase** | New, finer-grained UX-facing sub-state that exists *within* `PENDING_SETUP` (and, for the read-only view, within `ACTIVE`) added by this contract to represent WARM_UP/confirm/epoch progress. See §3. Whether a phase is persisted as its own PG column, packed into an existing field, or derived is implementation detail; the **set of phases and their transitions are not**. |
| **Epoch attempt** | One run through keyword-set confirm → WARM_UP → TP confirm → Auto participation confirm → Auto bid confirm, up to (but not including) generation assignment. Not yet durable-immutable; may be aborted via Cancel or EXIT without WB side effects (`proposal.md` Rollback idea). |
| **Generation** | Monotonic identifier assigned once all four confirmations are complete, immediately before the durable PENDING intent write (decision `ab-hold-epoch-lifecycle-and-generation-ownership` §5). Not assigned by the UI; UI only reads it. |
| **Draft** | The user's in-progress, not-yet-confirmed edit for the *current* screen only (e.g. toggled keyword inclusion before pressing "Подтвердить набор ключей"). A draft is always scoped to exactly one screen/step. |
| **Revision** | A monotonically increasing counter attached to every screen render, used for stale-callback detection (§10). Distinct from `generation`: revision changes on every draft edit or page turn; generation only changes on a brand-new epoch attempt. |
| **Fact position** | Read-model: the keyword's current observed WB position. Never a confirmed parameter. Always labeled "факт" / "текущая позиция". |
| **Target place (TP)** | Write-model: the epoch's confirmed parameter, proposed by `ab_hold_target_place_from_keyword(position)` and only durable after explicit confirmation. Always labeled "цель" / "целевая позиция", never merged with fact position even when numerically equal. |

## 2. Non-goals restated (do not re-derive elsewhere)

- No absolute test budget, epoch spend cap, velocity cap, financial latch, emergency-stop subsystem
  (`design.md` Non-Goals, decision §18).
- No monitoring/alerting artifact (`OUT_OF_SCOPE_FOLLOW_ON`).
- No change to OD-05 status; OD-05 stays the sole open owner decision gating broad enablement.
- No change to daily-budget/activity-control controller behavior or wording beyond what decision §18
  already specifies (stop threshold, honest overshoot, daily reset — see §11.4 below).
- No hard-cap or `лимит × дни` framing anywhere in copy (§14, §11.4).

## 3. Screen and phase inventory

| Phase | Screen ID | Screen name | Draft? | Paginated? | Backend mode (coarse) |
|---|---|---|---|---|---|
| `OFF` | **S0** | Entry / instruction | No | No | `OFF` |
| `AWAITING_KEYWORD_CONFIRM` | **S1** | Keyword-set confirm | Yes | Yes (10/page) | `PENDING_SETUP` |
| `AWAITING_KEYWORD_CONFIRM` (mid-WARM_UP edit) | **S1b** | Keyword-set edit during WARM_UP | Yes | Yes (10/page) | `PENDING_SETUP` |
| `WARM_UP` (config) | **S2** | WARM_UP duration config | Yes | No | `PENDING_SETUP` |
| `WARM_UP` (running) | **S3** | WARM_UP progress/status | No | No | `PENDING_SETUP` |
| `AWAITING_TP_CONFIRM` | **W3-propose** | Fact vs proposed target place | Yes | Yes (10/page) | `PENDING_SETUP` |
| `TP_CONFIRMED` (read-only) | **W3-confirmed** | Confirmed target places (read-only) | No | Yes (10/page) | `PENDING_SETUP` |
| `AWAITING_AUTO_PARTICIPATION_CONFIRM` | **A1** | Auto participation confirm | Yes | No | `PENDING_SETUP` |
| `AWAITING_AUTO_BID_CONFIRM` | **A2** | Auto bid confirm | Yes | No | `PENDING_SETUP` |
| `SYNCING` | **P1** | PENDING intent recorded / WB sync in progress | No | No | `PENDING_SETUP` |
| `SYNC_PARTIAL` | **P2** | Partial sync, recoverable, same generation | No | No | `PENDING_SETUP` |
| `ACTIVE` | **H1** | Active hold status (read-only) | No | Yes (10/page, optional detail) | `ACTIVE` |

Every phase screen except S0 and H1 belongs to exactly one **epoch attempt**. EXIT (Disable) is reachable
from every phase and always returns to S0/`OFF` (§6).

## 4. Phase transition table

| From | Action | To | Durable effect |
|---|---|---|---|
| `OFF` (S0) | Enable | *(gates: §2a freshness, §12 V3, §14a max CPO, §2c volume — all unchanged MVP-1 behavior)* | mode → `PENDING_SETUP`, Redis ENTER signal written (existing) |
| `PENDING_SETUP`, gates passed | shop-runner setup tick classifies eligible keywords (`pay_for_order ≤ max CPO`, `views ≥ 100`) | `AWAITING_KEYWORD_CONFIRM` (S1) | eligible-candidate read-model available; no snapshot yet |
| S1 draft | Confirm keyword set | `WARM_UP` config (**S2**) | confirmed keyword set becomes durable; populates the allowed-set snapshot (decision `ab-hold-confirmed-epoch-parameters-sot` §1); phase enters WARM_UP duration-configuration; `warmup_started_at` MUST remain NULL (timer MUST NOT start) |
| S2 (WARM_UP duration) | Confirm duration (`warmup_duration_confirm`) | `WARM_UP` running (**S3**) | selected/default duration (≥24h) persisted; `warmup_started_at` set; WARM_UP timer starts at that duration |
| S1 draft | Back | S1 (still `AWAITING_KEYWORD_CONFIRM`, closed to a summary view) | draft preserved |
| S1 draft | Cancel → confirm dialog → Yes | `OFF` (S0) | epoch attempt aborted; no snapshot existed yet, nothing durable to clear (§8) |
| S3 (WARM_UP running) | user manually edits keyword set (S1b) | S1b draft, then on confirm → **S2** (duration config) | prior confirmed keyword set replaced; running timer ends (`warmup_started_at` cleared); next screen is S2; timer restarts only on subsequent `warmup_duration_confirm` (decision §4) |
| S3 | WARM_UP timer elapses (≥ configured duration, min 24h) | `AWAITING_TP_CONFIRM` (W3-propose) | fact/proposed-TP read-model computed per keyword |
| S3 | EXIT (Disable) | `OFF` (S0) | mode → `OFF`; WARM_UP timer discarded; allowed-set snapshot cleared (existing EXIT contract) |
| W3-propose draft | Confirm all target places | `TP_CONFIRMED` (W3-confirmed), then `AWAITING_AUTO_PARTICIPATION_CONFIRM` (A1) | confirmed target places become durable and immutable for this epoch attempt (until a new epoch) |
| W3-propose draft | Back | S3-style summary preserving per-keyword draft state | draft preserved |
| W3-propose draft | Cancel → confirm dialog → Yes | `OFF` (S0) | epoch attempt aborted; confirmed keyword set / WARM_UP timer discarded together with the attempt |
| A1 (confirmed) | Confirm Auto participation | `AWAITING_AUTO_BID_CONFIRM` (A2) if participation = yes; skip A2 directly to generation assignment if participation = no | Auto participation becomes durable for this epoch |
| A2 draft | Confirm Auto bid | generation assigned → durable PENDING intent written → `SYNCING` (P1) | generation N created; PENDING intent (keyword set + TP + Auto participation + Auto bid) persisted **before** any WB write |
| P1 (syncing) | WB sync fully succeeds | `ACTIVE` (H1) | mode → `ACTIVE`; UI may now say "можно запускать A/B" |
| P1 (syncing) | WB sync partially completes / fails | `SYNC_PARTIAL` (P2) | mode stays `PENDING_SETUP`; same generation and same durable intent preserved |
| P2 (partial) | automatic retry, same generation, fully succeeds | `ACTIVE` (H1) | no recalculation of TP/Auto bid; no new generation |
| P2 (partial) | EXIT (Disable) | `OFF` (S0) | mode → `OFF`; durable intent/generation for this epoch discarded; no WB rollback needed (no confirmed parameter was ever mutated in WB before a *full* success) |
| `ACTIVE` (H1) | EXIT (Disable) | `OFF` (S0) | existing EXIT contract: allowed-set snapshot cleared; ordinary automation restored; no keyword-profile restore |

No transition table row allows moving from any phase directly to `ACTIVE` except via a fully successful
WB sync of a generation whose PENDING intent was durably recorded first (spec "ACTIVE without ENTER setup
snapshot is forbidden", MODIFIED).

## 5. Keyboard catalog

Every keyboard row set below is exhaustive for its screen — the implementation MUST NOT add or omit rows,
because the copy in the storyboard (`telegram-storyboard.md`) is written to match exactly these actions
(fixes the S0 "text vs keyboard mismatch" anti-pattern, §14).

| Screen | Rows (top → bottom) |
|---|---|
| S0, mode `OFF` | `[Включить A/B тест]` / `[← Назад]` |
| S0, mode ≠ `OFF` (any later phase reachable from status poll) | `[Открыть текущий шаг]` (deep-links to the current phase screen) / `[Выключить A/B тест]` / `[← Назад]` |
| S1 (keyword confirm) | per-page: `[✓/✗ <keyword 1>]` … `[✓/✗ <keyword 10>]` / `[◀ Стр.]` `[Стр. ▶]` (only if >1 page) / `[Подтвердить набор]` / `[← Назад]` `[Отмена]` |
| S1b (mid-WARM_UP edit) | same rows as S1, with a header line stating this edit ends the running timer and returns to duration configuration (S2); timer restarts only after duration confirm |
| S2 (WARM_UP duration) | `[24ч (по умолчанию)]` / `[Увеличить: +24ч]` `[Увеличить: +48ч]` / `[Подтвердить длительность]` / `[← Назад]` `[Отмена]` |
| S3 (WARM_UP progress) | `[Обновить статус]` / `[Изменить набор ключей]` / `[Выключить A/B тест]` / `[← Назад]` |
| W3-propose | per-page: `[<keyword i>: факт K → цель N]` (display-only row) … / `[◀ Стр.]` `[Стр. ▶]` (only if >1 page) / `[Подтвердить целевые позиции]` / `[← Назад]` `[Отмена]` |
| W3-confirmed (read-only) | per-page: `[<keyword i>: факт K → цель N (зафиксировано)]` (display-only) / `[◀ Стр.]` `[Стр. ▶]` / `[Выключить A/B тест]` / `[← Назад]` |
| A1 (Auto participation) | `[Да, участвует]` `[Нет, не участвует]` / `[← Назад]` `[Отмена]` |
| A2 (Auto bid) | `[Подтвердить ставку Auto: <value>]` / `[Изменить значение]` / `[← Назад]` `[Отмена]` |
| P1 (syncing) | `[Обновить статус]` / `[← Назад]` *(no Disable while a first-ever sync for this generation is in flight; Disable reappears once P2 or ACTIVE is reached)* |
| P2 (sync partial) | `[Обновить статус]` / `[Выключить A/B тест]` / `[← Назад]` |
| H1 (ACTIVE) | `[Подробности по ключам]` (optional, paginated detail) / `[Выключить A/B тест]` / `[← Назад]` |

`Отмена` (Cancel) appears **only** on draft-bearing screens (S1, S1b, S2, W3-propose, A1, A2) and is never
the same button object, callback prefix, or label as `← Назад` (Back) or `Выключить A/B тест` (EXIT/
Disable). This directly satisfies "Cancel does not masquerade as Back" and "Cancel is a separate action".

## 6. Callback/action catalog

Every callback payload for phases S1 onward MUST carry: `adv_setting_original_id`, a `step` discriminator,
and a `revision` (or, once assigned, `generation`) token used for stale-callback rejection (§10). Exact
Python `CallbackData` class names are implementation detail; the **action ids and payload fields below are
the contract**.

| Action id | Applicable screens | Extra payload | Precondition | Effect |
|---|---|---|---|---|
| `enable` | S0 | — | mode `OFF`, gates unchanged (§2a/§2c/§12/§14a) | existing MVP-1 Enable behavior, then leads to S1 once setup classification completes |
| `disable` (EXIT) | any phase screen | — | none (always available) | mode → `OFF`; see §4 table per-phase durable effect |
| `keyword_toggle` | S1, S1b | `keyword_id`, `page` | screen shows a draft | flips one keyword's draft inclusion state; redraws same page; does not move phase |
| `page_prev` / `page_next` | S1, S1b, W3-propose, W3-confirmed, H1-detail | `page` | more than one page exists | redraws same screen at `page ± 1`; never a phase transition; never touches Back/Cancel state |
| `keyword_set_confirm` | S1, S1b | — | at least one keyword included | commits draft → durable confirmed keyword set; enters WARM_UP duration-configuration (**S2**); MUST NOT set `warmup_started_at` / MUST NOT start the timer. On S1b: also ends any running timer (`warmup_started_at` cleared) before returning to S2 |
| `warmup_duration_preset` | S2 | `hours` (≥24) | screen shows a draft | sets draft duration; redraws S2 |
| `warmup_duration_confirm` | S2 | — | draft duration ≥ 24h | commits WARM_UP duration; sets `warmup_started_at`; WARM_UP timer starts (or restarts after S1b) at that duration; next screen is **S3** |
| `warmup_status_refresh` | S3 | — | phase `WARM_UP` | redraws S3 from durable timer state; never mutates |
| `keyword_edit_open` | S3 | — | phase `WARM_UP` | opens S1b (draft = current confirmed keyword set) |
| `tp_confirm_all` | W3-propose | — | all keywords reviewed | commits confirmed target places (durable, immutable this epoch); moves to A1 |
| `auto_participation_confirm` | A1 | `participates: bool` | screen shows a draft | commits Auto participation; moves to A2 if `participates=true`, else skips A2 |
| `auto_bid_edit` | A2 | — | screen shows a draft | opens numeric-entry sub-flow for Auto bid draft value (details: implementation, not fixed here) |
| `auto_bid_confirm` | A2 | — | draft value present | commits Auto bid; **assigns generation**; writes durable PENDING intent; triggers WB sync; moves to P1 |
| `sync_status_refresh` | P1, P2 | — | phase `SYNCING`/`SYNC_PARTIAL` | redraws from durable sync status; never mutates; never re-triggers a WB write itself (retry is owned by shop-runner scheduling, decision §7/§8) |
| `back` | S1, S1b, S2, W3-propose, A1, A2 (draft screens); S3, P1, P2, H1 (status screens, navigation-only) | — | none | draft screens: preserve draft, redraw a one-level-up summary. Status screens: navigate away without any draft to preserve. See §7. |
| `cancel_open` | S1, S1b, S2, W3-propose, A1, A2 | — | screen shows a draft | opens the Cancel confirmation sub-dialog (`Да, отменить` / `Нет, продолжить`) over the same message; no state change yet |
| `cancel_confirm_yes` | Cancel sub-dialog | — | opened via `cancel_open` | aborts the epoch attempt per §8 resolution rule; returns to `OFF` (S0) unless resolved to a prior durable state per §8 |
| `cancel_confirm_no` | Cancel sub-dialog | — | opened via `cancel_open` | closes the sub-dialog, redraws the original draft screen unchanged |

## 7. Back semantics

**Back always preserves the draft of the screen it is pressed on and never triggers any WB write, any
mode transition, any generation assignment, or any clearing of durable state.**

| Screen class | What "draft" means | Where Back goes |
|---|---|---|
| S1 / S1b (keyword confirm/edit) | per-keyword include/exclude toggles not yet committed by `keyword_set_confirm` | A one-level-up status summary for the current phase (e.g. "Подготовка A/B теста…" screen with an "Открыть текущий шаг" button that resumes exactly at the preserved page/toggles) |
| S2 (WARM_UP duration) | chosen duration not yet committed | same one-level-up summary; resuming reopens S2 with the preserved duration choice |
| W3-propose | per-keyword "reviewed" checkmarks not yet committed by `tp_confirm_all` | same one-level-up summary; resuming reopens W3-propose at the preserved page/review state |
| A1 / A2 | chosen participation / bid value not yet committed | same one-level-up summary; resuming reopens A1/A2 with the preserved draft |
| S3 / P1 / P2 / H1 (status/read-only, no draft) | none | campaign menu (there is nothing to preserve; Back here is plain navigation, matching existing S0 Back behavior) |
| **W3-confirmed (read-only, after TP confirm)** | none — TP is committed, not a draft | Back from **any later screen (A1, A2, P1, P2, H1)** that the user navigates backward through MUST land on **W3-confirmed**, never on W3-propose. The confirmed target places are never shown as editable again inside this epoch. This fixes the "after W3 confirm, Back → read-only W3" contradiction (§14). |

Back never needs a confirmation dialog, because it never discards anything.

## 8. Cancel semantics

Cancel is a **separate, explicit action** from Back (§14), never reachable via the same button, and always
requires confirmation when it would discard a draft (which is always true on the screens where Cancel
appears, since those screens always show a draft).

**Resolution rule** (fixes "Cancel does not clear durable epoch params on screens before snapshot exists"):

1. On `cancel_open`, the handler determines whether a **prior confirmed/durable value already exists for
   the item being drafted** (e.g. S1b editing an already-confirmed keyword set mid-WARM_UP has a prior
   durable value; a first-time S1 for a fresh epoch attempt does not).
2. If **no prior durable value exists** for this attempt: `cancel_confirm_yes` discards the in-progress
   draft **and aborts the whole epoch attempt**, returning to `OFF` (S0). Because no snapshot, WARM_UP
   timer, confirmed TP, confirmed Auto participation/bid, generation, or PENDING intent was ever written
   for this attempt, the abort path performs **no clearing write** of any of those — there is nothing to
   clear. The abort path MUST NOT unconditionally call the same "clear snapshot" mutation EXIT uses; it
   MUST only clear what this attempt itself created (which, at these pre-snapshot screens, is nothing
   durable).
3. If **a prior durable value exists** (S1b only, per §4): `cancel_confirm_yes` discards only the
   in-progress edit-draft and **restores/keeps the prior durable value untouched** (the previously
   confirmed keyword set stays confirmed, the running WARM_UP timer keeps running unaffected). The epoch
   attempt is **not** aborted in this case.
4. `cancel_confirm_no` always just closes the sub-dialog and redraws the original draft screen, unchanged.

| Screen | Cancel available? | Prior durable value exists? | `cancel_confirm_yes` effect |
|---|---|---|---|
| S1 (first confirm of a fresh epoch attempt) | Yes | No | Abort attempt → `OFF`. Nothing durable to clear. |
| S1b (mid-WARM_UP edit) | Yes | Yes (current confirmed keyword set + running timer) | Discard edit only; keep current keyword set and timer running, untouched. |
| S2 | Yes | No (duration not yet committed for this attempt) | Abort attempt → `OFF`. |
| S3, P1, P2, H1 (status, no draft) | **No** — only `Выключить A/B тест` (EXIT) is offered | n/a | n/a — EXIT is the only abort path here, and it is a distinct, always-available action, not styled as Cancel |
| W3-propose | Yes | No (TP not yet committed for this attempt) | Abort attempt → `OFF`. Confirmed keyword set / WARM_UP timer of this attempt are discarded together with the attempt. |
| W3-confirmed (read-only) | **No** (nothing to draft — TP already committed) | n/a | n/a |
| A1 | Yes | No (participation not yet committed for this attempt) | Abort attempt → `OFF`. |
| A2 | Yes | No (bid not yet committed for this attempt) | Abort attempt → `OFF`. |

Once `auto_bid_confirm` succeeds and a generation/PENDING intent exists (P1/P2/H1), there is no more
Cancel — the only way back to `OFF` is the always-available EXIT action, matching decision
`ab-hold-epoch-lifecycle-and-generation-ownership` (retry/abort of a recorded generation is a shop-runner
concern, not a user Cancel of a draft).

## 9. Pagination contract

- **Page size is fixed at 10 items per page** on every screen that lists keywords: S1, S1b, W3-propose,
  W3-confirmed, and the optional H1 detail view (spec "Confirmation screens paginate keyword lists at a
  fixed page size").
- Pagination controls (`◀ Стр.` / `Стр. ▶`) are shown only when the list has more than one page, and are
  a **distinct control pair from Back/Cancel** — turning a page never counts as Back, never opens the
  Cancel dialog, and never changes `revision` in a way that invalidates the user's already-made per-item
  draft toggles on other pages (toggles on page 1 survive navigating to page 2 and back).
- The current page number is part of the screen's draft state and is preserved by Back exactly like any
  other draft field (§7).

## 10. Stale callback handling (fail-closed)

**Invariant: a stale callback never changes state. It is only ever detected, logged, and answered with a
redraw of the current, durable/draft screen.**

Every screen render embeds a `revision` token (pre-generation phases) or the assigned `generation`
(P1/P2/H1) into every outgoing callback_data on that screen. Algorithm on every incoming callback:

1. Load the campaign's current durable phase and, if applicable, current draft revision or generation from
   storage (never trust the callback payload's implied phase).
2. Compare the callback's embedded `revision`/`generation` against the freshly loaded current one.
3. **If they do not match** (user pressed a button on an old rendering of the screen — e.g. after another
   device/session advanced the phase, after a page was already turned, after WARM_UP already completed,
   after a retry already reached ACTIVE, or after EXIT already reset to `OFF`):
   - **Reject the action.** Do not apply any toggle, confirm, page turn, or cancel.
   - **Redraw the current screen** from durable/draft state (which may be an entirely different screen
     than the one the stale callback was sent from — e.g. redraw H1 if the stale callback was for A2).
   - **Answer the callback** with a short, non-alarming toast, e.g. `"Экран обновился — показываю
     актуальный шаг."` (not a scary `show_alert=True` error).
   - **Log at WARNING** with `adv_id`, `action_id`, `expected_revision_or_generation`,
     `received_revision_or_generation`, and current phase — diagnosable without leaking internal
     identifiers to the user (no raw generation id / internal phase enum value in user-facing text).
4. **If they match:** process normally (§6).
5. This applies uniformly to every action in §6, including `disable` (EXIT): a stale EXIT callback from an
   already-`OFF` campaign is a no-op redraw of S0, not an error.

This closes the same class of race the applied MVP-1 already partially covers for Enable idempotency
(decision §10) and extends it uniformly to every new screen/action introduced by this contract.

## 11. Error / recoverable state display

| Category | Where shown | Behavior |
|---|---|---|
| Hard gate block (freshness §2a, V3-only §12, max CPO §14a) | S0 | Unchanged from applied MVP-1: mode stays `OFF`, reason + recommended action shown immediately, `SUPPORT_LINK` for freshness. |
| Soft volume warning / CH volume error (§2c) | S0 (pre-ENTER dialog) | Unchanged from applied MVP-1: distinct soft reason for CH error vs measured-low-volume warning with launch-anyway/cancel choice. |
| Deterministic setup block (empty allowed-set / max CPO vanished post-enable, §14b) | S1 (in place of the keyword list) | Actionable reason + recommended action, exactly as `setup_block_reason_line` already renders for PENDING_SETUP; transient causes (lock contention, single stale tick, cache warmup) keep the existing generic "Подготовка…" line. |
| Stale/missing statistics freeze (decision §17) | S1/S1b (keyword include/exclude), S3 (Search/Auto bid mutation freeze), W3-propose (if TP proposal input is stale) | Shown as an inline **freeze banner**, e.g. `"Заморожено: статистика по ключу устарела — решение о включении/ставке отложено до свежих данных."` This is explicitly **not** an error and explicitly **not** a "campaign stopped" message — the campaign continues; only the affected decision is frozen. WARM_UP's timer keeps counting during a freeze (freeze pauses decisions, not time). |
| Soft-policy stats disclaimer (decision §17 soft MVP / bound 2026-07-30) | S0 Enable instruction and/or in-test status (S3/H1) | Informed-consent line: temporary stats gaps are usually harmless; for a stable test the bot does **not** change keyword set / bids on unknown data (freeze decide); the user monitors the test. **Forbidden** wording: «ослабим защиту» when behavior is freeze-decide. Not a three-way hard\|soft\|self picker (parked WORKLOG). |
| Partial WB sync (P2) | P2 | `"Синхронизация с WB завершена частично. Кампания ещё не активна. Повтор произойдёт автоматически на следующем тике — параметры и настройки эпохи не пересчитываются."` No numeric ETA promise; no claim of a guaranteed retry count/time. |
| Daily budget / activity-control disclosure (decision §18) | S0 instruction (mode-independent) and H1 (ACTIVE) | Honest, bounded copy only: stop-threshold, no guaranteed numeric overshoot bound, daily reset. **Never**: "немного" (a little overshoot), "лимит × дни" (limit × days) framing, or any implied hard cap. See §14 fixes and `telegram-storyboard.md` §S0/§H1 for exact illustrative copy. |

## 12. Read-only states after confirmation

| State | Screen | What is locked | What remains actionable |
|---|---|---|---|
| Confirmed keyword set (post-`keyword_set_confirm`, before a new S1b edit) | S3 status | Keyword set is durable; not directly editable from S3 | `keyword_edit_open` reopens it as a **new S1b draft** (which, on confirm, ends the running timer and returns to **S2** duration configuration per §4/§6; the new timer starts only after `warmup_duration_confirm`) — editing is explicit and never silently mutates the running timer |
| Confirmed target places (post-`tp_confirm_all`) | **W3-confirmed** | Every keyword's TP is immutable for this epoch; no edit control exists anywhere in the UI for a confirmed TP within the same epoch | Pagination (view-only), Back destinations point here (§7), EXIT |
| Confirmed Auto participation / Auto bid (post `auto_participation_confirm` / `auto_bid_confirm`) | A1/A2 status lines shown on P1/P2/H1 | Not editable within this epoch; ordinary Auto bid auto-update MUST NOT change it while `ACTIVE` (decision §16 / spec) | EXIT (starts a new epoch attempt from scratch after re-enable) |
| `ACTIVE` hold (H1) | H1 | Target places, keyword set, Auto participation/bid, structural ACT paths all frozen (existing spec requirements) | Bidder keeps running (existing); EXIT; optional read-only detail pagination |

A confirmed value never has an "edit" control rendered next to it anywhere after its own confirm step; the
**only** way to change a confirmed keyword set is the explicit `keyword_edit_open` re-draft path (S1b
confirm ends the current timer and returns to S2; the new timer starts only after duration confirmation),
and the **only** way to change a confirmed TP/Auto participation/Auto bid is a brand
new epoch (EXIT → re-enable, or the keyword-set-edit-during-WARM_UP path before TP was ever confirmed).

## 13. Mapping: UI phase ↔ PENDING intent / WB sync / ACTIVE / partial-sync recovery

| UI phase/screen | PENDING intent state | WB mutation state | Mode | Notes |
|---|---|---|---|---|
| S0 `OFF` | none | none | `OFF` | — |
| S1/S1b `AWAITING_KEYWORD_CONFIRM` | none | none | `PENDING_SETUP` | Confirmed keyword set feeds the allowed-set snapshot, but this is not yet the epoch's PENDING intent (decision §5/§6 of `ab-hold-epoch-lifecycle-and-generation-ownership`). |
| S2/S3 `WARM_UP` | none | none | `PENDING_SETUP` | No WB write of any confirmed parameter happens during WARM_UP (spec "Target place is not fixed during WARM_UP"). |
| W3-propose `AWAITING_TP_CONFIRM` | none | none | `PENDING_SETUP` | Proposed TP is display-only until confirmed. |
| W3-confirmed / A1 / A2 | none | none | `PENDING_SETUP` | Confirmed TP/Auto values are durable but generation is **not yet assigned** and **no PENDING intent exists** until Auto bid confirm completes (decision §5/§6). |
| P1 `SYNCING` | **written** (generation N, all four confirmed parameter groups) | first WB mutation attempt for generation N begins **after** the intent write | `PENDING_SETUP` | Spec "Activation requires a durable PENDING intent recorded before any WB mutation." |
| P2 `SYNC_PARTIAL` | preserved, same generation N | partially applied; retry reuses generation N and the same parameters, no recalculation | `PENDING_SETUP` (non-ACTIVE) | Spec "Partial Wildberries synchronization is recoverable and keeps the campaign non-ACTIVE"; decision §7/§8. |
| H1 `ACTIVE` | fulfilled (generation N fully synced) | fully applied | `ACTIVE` | Only reachable after a **fully** successful sync of the currently recorded generation; UI first says "можно запускать A/B" here (spec MODIFIED "ACTIVE without ENTER setup snapshot is forbidden"). |

## 14. Contradiction fixes (traceable to prior manual UX / anti-pattern)

| Contradiction (prior manual UX / anti-pattern) | Fix in this contract |
|---|---|
| Daily-budget copy implying "overshoot will be small" ("немного") or a computable upper bound via `лимит × дни` | §11.4 and `telegram-storyboard.md` S0/H1 copy state stop-threshold + unbounded overshoot honestly, no minimizing language, no threshold×days arithmetic anywhere. |
| S0 text promising things the keyboard does not offer (or vice versa) | §5 fixes the exact keyboard row set per S0 mode; storyboard §S0 copy is written to describe only what that exact keyboard offers. |
| Existing MVP-1 `CardAbHoldBack` closes the screen with no draft-preservation concept, and Cancel exists only for the §2c volume warning (pre-ENTER), conflating "close" with both Back and Cancel | §7/§8 define Back (always preserves draft, never destructive) and Cancel (separate, confirmed, resolution-rule-bound) as two independently reachable, differently-labeled, differently-behaving actions on every draft screen. |
| Risk of a Cancel/EXIT handler unconditionally calling the same "clear allowed-set snapshot" mutation regardless of whether anything was ever written for the current attempt | §8 resolution rule: abort-with-nothing-durable clears nothing; abort/edit-with-prior-durable-value only discards the new edit, never touches the existing durable value. |
| Merging factual position and target place into one number (`"Позиция: 12"`) | §1 terminology + §12 read-only table + storyboard W3 copy always render two labeled fields, even when numerically equal after rounding/clamping (decision `ab-hold-confirmed-epoch-parameters-sot` §2). |
| Re-showing an editable TP-propose screen after confirmation (re-opening the "old" screen via Back) | §7 last row + §12: Back destinations after TP confirm always resolve to **W3-confirmed** (read-only), never W3-propose; there is no edit control on a confirmed TP within the epoch. |
| No defined behavior for a callback sent against a screen that has since moved on (stale button, race, multi-device) | §10 fail-closed algorithm: reject, redraw current state, log, never mutate. |

## 15. Applies to / Related

- `openspec/changes/card-ab-hold-mode/specs/card-ab-hold-mode/spec.md` — requirements "Confirmation
  screens paginate keyword lists at a fixed page size", "Back preserves the confirmation draft; Cancel is
  a separate explicit action", and all WARM_UP/TP/Auto/epoch requirements this contract's screens realize.
- `openspec/changes/card-ab-hold-mode/decisions/ab-hold-epoch-lifecycle-and-generation-ownership/decision.md`
- `openspec/changes/card-ab-hold-mode/decisions/ab-hold-confirmed-epoch-parameters-sot/decision.md`
- `openspec/changes/card-ab-hold-mode/decisions/card-ab-hold-write-path-ownership/decision.md` §15–§18
- `openspec/changes/card-ab-hold-mode/tasks.md` §19–§25 (implementation, blocked on owner authorization)
- `openspec/changes/card-ab-hold-mode/ux/telegram-storyboard.md` (scene-by-scene walkthrough using this
  contract)
- `openspec/policies/telegram_bot_api_limits.md` (payload-limit tests required at implementation time for
  every screen introduced here — not satisfied by this planning document; see tasks §24's dedicated
  "Telegram UI / Message Safety" checklist).
