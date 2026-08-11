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

## OpenSpec history layers (explore context)

When `OWNER_INTENT` is present, explore MUST do a **targeted** OpenSpec pass:

1. current `openspec/specs/**`
2. Accepted `openspec/decisions/**` (ADL budgets intact)
3. relevant `openspec/changes/archive/**` as **history only**
4. then current code/tests

### PASS

- Lookup keyed from OWNER_INTENT / capability / UI terms / related specs /
  known IDs / runtime entities — **not** a broad archive scan.
- `EXPLORE_HANDOFF` separates `CURRENT_CONTRACT`, `ACCEPTED_DECISIONS`,
  `HISTORICAL_EVIDENCE`, `REPOSITORY_FINDINGS`, and `CONTRACT_VS_REPO`.
- On `current main spec` vs `archived change`: main spec is acting contract;
  archive stays under `HISTORICAL_EVIDENCE`.
- On contract vs code mismatch: `CONTRACT_VS_REPO` is explicit (not silent).
- Archive / OpenSpec interpretation does **not** rewrite `OWNER_INTENT`.

### FAIL

- Broad recursive dump of `openspec/changes/archive/**`.
- Archive used as acting SoT over current main spec.
- Silent choice when contract and repo disagree.
- Historical reading folded into `OWNER_INTENT`.

## Static check matrix (dry-run)

| Check | Expected |
|---|---|
| evolution COPY_BLOCK template includes `OWNER_INTENT:` | yes |
| evolution forbids silent rewrite of `OWNER_INTENT` | yes |
| explore emits `EXPLORE_HANDOFF` when `OWNER_INTENT` present | yes |
| explore copies `OWNER_INTENT` verbatim | yes |
| explore puts code symbols under findings/mapping, not OWNER_INTENT | yes |
| explore requires targeted specs + decisions + relevant archive | yes |
| explore forbids broad archive scan | yes |
| EXPLORE_HANDOFF has CURRENT_CONTRACT / HISTORICAL_EVIDENCE / CONTRACT_VS_REPO | yes |
| main spec > archive on conflict | yes |
| archive must not rewrite OWNER_INTENT | yes |
| new prioritizes `OWNER_INTENT` for owner-contract semantics | yes |
| new falls back when `OWNER_INTENT` absent | yes |
| continue / ff / apply / verify contracts unchanged by this fixture | n/a (out of scope) |

## E2E acceptance (primary)

```text
Given Owner intent about old Auto bid control vs shelf bid control
When evolution forms handoff
And explore finds cost watchdog / OLD_UPDATE_CPM_BIDDER / related paths
And explore also checks relevant current specs / Accepted decisions /
    targeted archive history
And explore output is passed to new
Then owner-contract.md still describes old vs new bid-control modules
And cost watchdog is NOT the new Owner intent without Owner correction
And archive history did not become OWNER_INTENT or acting SoT over main spec
```
