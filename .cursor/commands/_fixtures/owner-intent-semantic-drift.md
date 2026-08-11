# Fixture: OWNER_INTENT semantic-drift (evolution → explore → new)

Process-only contract regression for the failure class where repository
inference silently replaces Owner product meaning before `owner-contract.md`
is written.

Commands under test: `/opsx-evolution`, `/opsx-explore`, `/opsx-new`.

## Given (Owner words)

```text
Если новое управление ставкой в полках включено,
старое управление ставкой для Auto должно игнорироваться.
```

Product entities (Owner language):

- старое «Управление ставкой» / «Включить управление ставкой для Авто»
- новое «Управление ставкой в полках»

## When — evolution

`/opsx-evolution` emits `EVOLUTION_HANDOFF` / COPY_BLOCK including
`OWNER_INTENT` that stays about the two bid-control modules and the
ignore-when-shelf-enabled behavior.

### PASS

```text
OWNER_INTENT:
Старое «Управление ставкой» → «Включить управление ставкой для Авто»
и новое «Управление ставкой в полках» не должны одновременно управлять
ставкой Auto. Когда новое управление включено, старое должно
игнорироваться. Когда новое выключено, старое может работать как раньше.
```

(Semantic-equivalent Owner wording is OK; technical reframe is not.)

### FAIL (forbidden without Owner correction)

```text
OWNER_INTENT:
cost watchdog / cost_rule_failed must coexist with Shelf Bid Control
```

## And when — explore

Explore finds repository-adjacent symbols (examples):

- `OLD_UPDATE_CPM_BIDDER`
- `cost_rule_failed`
- activity-control
- `AutoShelfBidControlManager`

### PASS

`EXPLORE_HANDOFF.OWNER_INTENT` is a **verbatim** copy of the evolution
`OWNER_INTENT`. Findings/mappings live under `REPOSITORY_FINDINGS` /
`RUNTIME_MAPPING` / `UNRESOLVED` / `CANDIDATE_MAPPING` only.

### FAIL

Explore returns a different `OWNER_INTENT` because evidence supports a
cost-watchdog reading.

## And when — new

`/opsx-new` receives `OWNER_INTENT` + evolution scope + explore findings and
writes `owner-contract.md`.

### PASS

`owner-contract.md` «Что хотим получить» / observable criteria still describe
the conflict between old Auto bid control and shelf bid control (Owner
language / UI labels). Cost-watchdog material may appear only as
constraint/context if it does not redefine the object of the task.

### FAIL

`owner-contract.md` primary meaning becomes «cost watchdog vs Shelf Bid
Control» without explicit Owner correction.

## Backward compatibility

Given an old handoff **without** `OWNER_INTENT`:

- explore may skip `EXPLORE_HANDOFF`
- new keeps prior fallback (Owner request + change context)

Absence of `OWNER_INTENT` alone MUST NOT invalidate the handoff.

## Static check matrix (dry-run)

| Check | Expected |
|---|---|
| evolution COPY_BLOCK template includes `OWNER_INTENT:` | yes |
| evolution forbids silent rewrite of `OWNER_INTENT` | yes |
| explore emits `EXPLORE_HANDOFF` when `OWNER_INTENT` present | yes |
| explore copies `OWNER_INTENT` verbatim | yes |
| explore puts code symbols under findings/mapping, not OWNER_INTENT | yes |
| new prioritizes `OWNER_INTENT` for owner-contract semantics | yes |
| new falls back when `OWNER_INTENT` absent | yes |
| continue / ff / apply / verify contracts unchanged by this fixture | n/a (out of scope) |

## E2E acceptance (primary)

```text
Given Owner intent about old Auto bid control vs shelf bid control
When evolution forms handoff
And explore finds cost watchdog / OLD_UPDATE_CPM_BIDDER / related paths
And explore output is passed to new
Then owner-contract.md still describes old vs new bid-control modules
And cost watchdog is NOT the new Owner intent without Owner correction
```
