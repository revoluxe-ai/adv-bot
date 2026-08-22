# SCENARIO_COVERAGE_PLAN

```text
CHANGE_ID: auto-shelf-exhausted-pause-retest
MODE: plan
PLAN_STATUS: ready
PLAN_EVIDENCE_ID: sceplan-0d02836f9141d9c2
SCENARIO_COUNT: 18
LIFECYCLE_STATUS: DERIVED
PRODUCT_ACCEPTANCE_REQUIRED: true
```

## GENERATED_FROM

```text
DESIGN_REVISION:
  path: openspec/changes/auto-shelf-exhausted-pause-retest/design.md
  content_hash: ca1fd3bd429019d5c3710234bcfb7379036fb6f933a53211b3056524f9ad2899
SPEC_REVISION:
  - path: openspec/changes/auto-shelf-exhausted-pause-retest/specs/auto-shelf-exhausted-pause/spec.md
    content_hash: 521a356de8d306cdbcd64f0a5ed4fd4514ec72e6298b9e71da1c23f9a241366e
LIFECYCLE_REVISION:
  source: design.md##Lifecycle (LIFECYCLE_STATUS: DERIVED L1–L6)
  content_hash: ca1fd3bd429019d5c3710234bcfb7379036fb6f933a53211b3056524f9ad2899
OWNER_CONTRACT_REVISION:
  path: openspec/changes/auto-shelf-exhausted-pause-retest/owner-contract.md
  content_hash: 2b8d664d901b826f85f8d40c1c9b1e280b4be1b098e898703dd6a5efe6c3501e
TASKS_ARTIFACT: present (consumed for entrypoint hints only; not SoT)
```

## LIFECYCLE_COVERAGE

| L* | Spec Scenarios |
|---|---|
| L1 Gate + mid-cycle cost | Module off — no shelf-exhausted pause; Non-Best plan mode — no shelf-exhausted pause; Shelf module on — mid-cycle cost does not pause Auto; Shelf module off — legacy cost pause may apply |
| L2 Terminal detect / latch | Still have bids to test — no terminal pause; Exhausted epoch and no resolve-CPO fit → Auto pause; Already-exhausted on reconcile tick arms Auto pause |
| L3 Auto pause write | Exhausted epoch…; Already-exhausted…; Search leg not paused by shelf-exhausted; Reason is not masked as cost or empty-keywords; Resolve CPO used for terminal is visible |
| L4 Notify | Notify explains why and when; Resolve CPO used for terminal is visible; Default interval is seven days |
| L5 Clear / keep block | Calendar due clears our block only; Reset pause button clears our block only; Pass points on tick clear our block without forced start; No fit on tick keeps our pause block |
| L6 Conditional start + epoch | Auto starts and new epoch when only our block held pause |
| Orth coexistence | Shelves on — legacy Auto bid path still ignored |

Steady-state / already-true: covered by «Already-exhausted on reconcile tick…», «No fit on tick keeps…», «Pass points on tick…», mid-cycle ON/OFF.

## UNRESOLVED_GAPS / OPEN_QUESTIONS

```text
none
```

Prior provisional gaps (missing steady-state terminal arm; keep-block) closed in spec (18 scenarios). Design apply-time naming of reason enum remains non-blocking for coverage plan.

## SCENARIO_COVERAGE_PLAN

```text
SCHEMA_VERSION: 1
CHANGE_ID: auto-shelf-exhausted-pause-retest
SOURCE_SPEC_SHA: 521a356de8d306cdbcd64f0a5ed4fd4514ec72e6298b9e71da1c23f9a241366e
PLAN_STATUS: ready
SHARED_ENTRYPOINTS:
  - AutoShelfBidControlManager (detect / epoch / clear / resolve CPO)
  - AutoAdvActiveControlService (pause_auto_campaign / Auto start / cost gate)
  - auto_shelf_bid_control_telegram_service / shelf UX
  - bidder_func coexistence gate (orth)
SHARED_THIN_ENDS:
  - WB: pause_auto_campaign; matching Auto start; FORBIDDEN pause_auction_campaign for this reason
  - Telegram transport (paid notify / «Сбросить паузу»)
  - PG: durable our-block / epoch / interval / resolve CPO (write + read)
  - Redis: Auto-lane reason mirror (fakeredis OK)
  - CH: only if detect outcome depends on live stats read
```

### Rows (required evidence — tests not claimed)

Spec prefix: `openspec/changes/auto-shelf-exhausted-pause-retest/specs/auto-shelf-exhausted-pause/spec.md`

**S1** `::Module off — no shelf-exhausted pause` — L1  
GIVEN module OFF / WHEN terminal-like / THEN no Auto shelf-exhausted pause  
REQ: scenario_seam forbidden pause_auto; stub_contract if stubbed; UNIT gate additive

**S2** `::Non-Best plan mode — no shelf-exhausted pause` — L1  
GIVEN shelves ON + non–Best plan / WHEN epoch could exhaust / THEN no terminal path  
REQ: scenario_seam gate

**S3** `::Exhausted epoch and no resolve-CPO fit → Auto pause` — L2→L3  
GIVEN exhausted+no fit+Auto running / WHEN terminal path (incl. tick detect) / THEN Auto paused + module ON  
REQ: scenario_seam detect→activity; SIDE_EFFECT_PROOF pause_auto; PG WRITE+READ if SoT; STUB_CONTRACT pause_auto

**S4** `::Already-exhausted on reconcile tick arms Auto pause` — L2→L3 **steady-state**  
GIVEN already-true exhausted (no fresh producer) / WHEN periodic reconcile tick / THEN Auto pause + module ON  
REQ: scenario_seam tick entry; same thin ends as S3; must fail if only post-event producer covered

**S5** `::Search leg not paused by shelf-exhausted` — L3  
WHEN terminal / THEN Search NOT paused  
REQ: scenario_seam + forbidden pause_auction; stub_contract both adapters if stubbed

**S6** `::Still have bids to test — no terminal pause` — L2  
GIVEN next test bid / WHEN shelf cycle / THEN no shelf-exhausted pause  
REQ: scenario_seam negative

**S7** `::Reason is not masked as cost or empty-keywords` — L3  
GIVEN paused / WHEN read reason / THEN distinct ≠ empty-keywords/cost_rule_failed/schedule/budget  
REQ: scenario_seam; Redis/PG read boundary for reason/block

**S8** `::Resolve CPO used for terminal is visible` — L3/L4  
GIVEN terminal / WHEN notify or reason account / THEN CPO kind+value visible  
REQ: scenario_seam; Telegram stub_contract

**S9** `::Calendar due clears our block only` — L5  
GIVEN our block + other blocker / WHEN interval due / THEN clear only + no forced start  
REQ: scenario_seam; FORBIDDEN Auto start; PG clear WRITE (+ READ)

**S10** `::Reset pause button clears our block only` — L5  
GIVEN our block + other blocker / WHEN «Сбросить паузу» / THEN clear only + Auto stays paused  
REQ: scenario_seam callback→clear; Telegram stub_contract

**S11** `::Pass points on tick clear our block without forced start` — L5 **steady-state clear**  
GIVEN hung block + fit + other blocker / WHEN tick resolve / THEN clear only / no forced start  
REQ: scenario_seam tick

**S12** `::No fit on tick keeps our pause block` — L5 **steady-state keep**  
GIVEN hung block + no fit + interval not due / WHEN tick resolve / THEN block persists  
REQ: scenario_seam tick; assert no clear / no start

**S13** `::Auto starts and new epoch when only our block held pause` — L6  
GIVEN only our block / WHEN cleared + no other blockers / THEN Auto MAY start + new epoch coverage clamp  
REQ: scenario_seam; stub_contract Auto start; epoch/date_from assert; PG epoch WRITE+READ

**S14** `::Default interval is seven days` — L4  
GIVEN no override / WHEN default / THEN 7 days  
REQ: scenario_seam or strong unit + wiring seam; PG settings if durable

**S15** `::Notify explains why and when` — L4  
GIVEN enter pause / WHEN paid notify / THEN why + CPO + next retest + button; Free forbidden  
REQ: scenario_seam; Telegram stub_contract + boundary shape

**S16** `::Shelf module on — mid-cycle cost does not pause Auto` — L1  
GIVEN module ON + mid-cycle cost would trip / WHEN activity cost / THEN no ordinary cost Auto pause  
REQ: scenario_seam through **real** cost branch (do not patch away gate)

**S17** `::Shelf module off — legacy cost pause may apply` — L1  
GIVEN module OFF + cost conditions / WHEN activity cost / THEN Auto MAY ordinary cost pause  
REQ: paired scenario_seam with S16

**S18** `::Shelves on — legacy Auto bid path still ignored` — Orth  
GIVEN shelves ON + legacy bidder ON / WHEN bid automation / THEN legacy Auto bid MUST NOT succeed  
REQ: scenario_seam coexistence; not substitute for S3–S17

## Notes for consumers

- This plan does **not** claim tests exist or PASS.
- Downstream: `/opsx-planning-review` / task readiness may consume this pair; `/opsx-apply` implements; `/opsx-spec-scenario-coverage mode=audit` after evidence authored.
- `PLAN_STATUS: ready` is durable only with matching `plan.receipt.json` CURRENT.
