---
description: "Primary project-tuned bug discovery (Bugbot analogue for WB Sky): grounded in domain ADLs, write boundaries, and learning checklist; feeds durable intake before PR; Bugbot is residual safety net only."
argument-hint: "base=<branch> head=<branch> [change=<id>] [scope=<paths>] [focus=<theme>] [deep] [GO]"
---

# /opsx-project-bug-hunt

You are the **primary** project-tuned bug hunter for WB Sky.

This command is the OPSX analogue of Bugbot for **this** repository: it must
catch product/behavioral defects **before** they reach external Bugbot.

External Bugbot is a **residual safety net** only. If Bugbot still finds a
product/logic bug, that is a **hunter miss** → feed
`/opsx-learn-from-bug` (or hunter feedback from `/opsx-fix-bug`) to improve
**this** command's checklist and grounding — not to invent a second free-form
audit command.

## What this is

* Primary pre-PR / pre-Bugbot discovery for the current `base..head` (or change).
* Grounded in **this** project's architecture decisions, write-path rules,
  shop-runner / Redis / ClickHouse / WB / Telegram contracts, and the learning
  checklist below.
* Producer of structured findings that enter the durable case map. Primary
  entry when bug-team is ACTIVE: `/opsx-bug-team` (free-form / RAW_REPORT;
  team materializes). Else: `/opsx-materialize-bug-queue mode=intake` or
  `/opsx-fix-bug` WITHOUT GO (first-run intake) — same consumer case map.

## What this is NOT

* NOT `/opsx-bug-hunt` (that command is **root-aware**, single-invariant
  sibling hunt after a known root packet).
* NOT a general style / formatting / drive-by refactor audit.
* NOT process-contract Bugbot on `.cursor/commands/**` (F6 →
  `/opsx-meta-fix-command-defects`).
* NOT `/opsx-verify`, `/opsx-static-check`, or `/opsx-fix-types`.
* NOT a guarantee that Bugbot will always be empty — honesty: residual risk
  remains; the contract is **maximize catch + learn from misses**.

## User input

```text
$ARGUMENTS
```

## Required inputs

Extract from `$ARGUMENTS`:

* `base`: comparison base branch or commit.
* `head`: branch or commit under inspection (usually current work).
* `change`: optional OpenSpec change id (preferred when hunting a change).
* `scope`: optional path allow-list.
* `focus`: optional theme hint (e.g. `card_ab_hold`, `min_bids`, `telegram`,
  `shop-runner`, `keywords-cache`).
* `deep`: optional deeper pass after cheap scan.
* `GO`: optional permission for **minimal** fixes of
  `confirmed production bug` only.

If `base` or `head` is missing, stop and ask for them. Do not invent refs.

Do **not** require a known `root_finding` (that is `/opsx-bug-hunt`).

## Modes

### Default (no `GO`)

READ_ONLY discovery:

* do not modify production code;
* do not stage / commit / push;
* do not create branches or worktrees;
* output structured findings + pasteable next actions;
* may write nothing to disk except what the human later pastes into
  `/opsx-bug-team` or alternate intake (prefer chat-structured finding
  packets).

### `GO`

Only after a complete READ_ONLY pass in the same chat (or explicit replay of
that finding list):

* apply **minimal** fixes solely for `confirmed production bug`;
* never patch `dead legacy`, `tests-only`, `unreachable`,
  `unclear reachability`, `adjacent`, or `false positive` just to silence
  reviewers;
* re-run the cheapest confirming checks for touched paths.

## Source resolution & budgets

Follow `.cursor/commands/opsx-source-resolution.md` and
`.cursor/commands/opsx-execution-preflight.md`.

Hard I/O rules:

1. Prefer `git diff base...head` (or equivalent) + Grep over full-repo Read.
2. Parallel `Read` max **2**.
3. Do **not** dump all of `.cursor/commands/**` or all decisions.
4. Context-first ADLs: paths from change design / `artifactPaths` / user
   `focus` / `openspec/decisions/index.md` when ownership/write-path is at
   stake; bounded fallback ≤ 3 decision lookups unless `EVIDENCE_GAP`.
5. Time-budget every git/rg op; on hang → `blocked_preflight_timeout`, do not
   stack unbounded scans.
6. `deep` widens **within** touched modules + same write-boundary families —
   never into unrelated business domains.

## LOC_LINK contract (mandatory)

Authority: `.cursor/rules/opsx-clickable-loc-link-contract.mdc`.

For every finding that references concrete code location, include:

`LOC_LINK: <repo-relative-path>:<line>`

Rules:

* Use plain `path:line` (Cursor-clickable), not `file://` as the only format.
* Keep `EVIDENCE` for paths/symbols, but location-specific finding fields must
  include `LOC_LINK`.
* If exact line is unavailable, fallback to symbol definition line with short
  fallback note in finding text.

## Project grounding (mandatory load order)

Load only what the diff/focus requires; skip irrelevant layers.

1. **Diff truth** — `git diff --stat` + focused diff for `base...head`.
2. **Change packet** (if `change=`) — proposal/design/tasks/specs relevant
   sections only.
3. **Architecture decisions** — context-first from change or index; cite paths.
4. **Domain runbooks / AGENTS notes** when keywords/shop-runner/min_bids/CH
   appear in the diff (exact known paths only; no repo-wide rediscovery).
5. **Learning checklist** — section
   `## Project hunt checklist (learning target)` in **this** file
   (authoritative hunter improvements from prior Bugbot misses).
6. **Testing rules** — `.cursor/rules/testing-rules.mdc` when test realism /
   write-gates are implicated.

If a required grounding path is missing → `EVIDENCE_GAP` for that theme; do
not invent ADLs.

## Authority split vs other hunters

| Signal | Owner |
|---|---|
| Primary project discovery pre-PR | **`/opsx-project-bug-hunt`** (this) |
| Same-invariant siblings after known root | `/opsx-bug-hunt` |
| Fan-out of root-aware hunt | `/opsx-fanout-bug-hunt` |
| Orchestrated full bug entry (when ACTIVE) | **`/opsx-bug-team`** (`DEFAULT_FULL_BUG_ENTRY`) |
| Raw durable record (alternate / team-off) | `/opsx-materialize-bug-queue` or `/opsx-fix-bug` WITHOUT GO intake |
| Claim / fix (manual queue path) | `/opsx-claim-next-bug` → `/opsx-fix-bug` |
| Residual external review | **Bugbot** (safety net) |
| Miss reached Bugbot (product/logic) | `/opsx-learn-from-bug` → update **this** checklist |
| Process-contract Bugbot (F6) | `/opsx-meta-fix-command-defects` |

Never re-decide another command's GO/NO_GO. Never treat chat paraphrase as
durable case map.

## When to use

* Before `/opsx-create-pr` on product/behavior changes.
* After substantial `/opsx-apply` when the change touches runtime write paths.
* When the owner wants a **powerful project-aware** sweep of `base..head`
  without a single known root packet.
* After Bugbot found a miss — once learning updated this checklist, re-run
  on the same class of change.

## When not to use

* Known root + single invariant sibling search → `/opsx-bug-hunt`.
* Typing-only → `/opsx-fix-types` / static-check.
* Process command/rule defects → admin fix-command-defects.
* Day-to-day “what next?” without hunting → `/opsx-pipeline`.
* Replacing Bugbot on process files or inventing a second lifecycle authority.

## Analysis order (cheap-first)

### Pass 0 — receipt + scope lock

Record `base`, `head`, `change`, `scope`, `focus`. Refuse unbounded
whole-monorepo walks when `scope` is absent **and** the diff is empty/huge
without `focus` — ask for `scope` or `focus`.

### Pass 1 — diff-anchored suspects

From the diff, list every touched:

* write / mutation / external API / Redis / CH / PG path;
* Telegram handler / callback / parse_mode / button contract;
* campaign / mode / paid-free / bot_active gate;
* shop-runner / snapshot / keywords / min_bids cache path;
* scheduler / worker / ARQ entry;
* auth / token / secrets boundary.

Map each to a candidate invariant or ADL (cite path or `Architecture Decision Missing`).

### Pass 2 — project checklist

For every item in `## Project hunt checklist (learning target)` that matches
the diff/focus, execute the check. Record hit / miss / N/A.

### Pass 3 — reachability proof

For each suspect, prove production reachability (scheduler, bot, API, CLI,
tests-only, dead). No reachability → not `confirmed production bug`.

### Pass 4 — deep (optional)

Only with `deep` or explicit user ask. Expand to sibling adapters in the
**same** write-boundary family. Stop at budget; emit `NOT_OPENED_BUDGET`
rather than pretend completeness.

### Pass 5 — classify + handoff

Every finding gets exactly one production classification (same vocabulary as
`/opsx-bug-hunt`):

```text
confirmed production bug
reachable but low-risk
unclear reachability
dead legacy
tests-only
unreachable
adjacent
false positive
```

## Output contract (every run)

```text
STATUS: HUNT_COMPLETE | BLOCKED_NEEDS_INPUT | BLOCKED_PREFLIGHT | EVIDENCE_GAP
MODE: READ_ONLY | GO_MINIMAL_FIX
COMMAND: /opsx-project-bug-hunt

PROJECT_BUG_HUNT_RECEIPT:
- base:
- head:
- change:
- scope:
- focus:
- deep: true|false
- timestamp_utc:
- grounding_cited: [paths]
- checklist_items_evaluated:
- checklist_hits:
- findings_total:
- confirmed_production_bug_count:
- residual_risk_for_bugbot: [short bullets Bugbot may still see]

FINDINGS:
### FINDING_ID: PBH-001
- TITLE:
- LOC_LINK:
- LITERAL_CLAIM:
- PRODUCTION_CLASSIFICATION:
- RUNTIME_PATH:
- CAUSAL_BOUNDARY:
- WRITE_BOUNDARY:
- EVIDENCE: [paths + symbols]
- ADL_OR_INVARIANT_REF:
- WHY_PROJECT_HUNT_NOT_BUGBOT_FIRST: (how project grounding caught this)
- SEPARATE_ADJUDICATION_REQUIRED: true|false
- SUGGESTED_INTAKE_TITLE:

BUG_TEAM_HANDOFF (PRIMARY when ACTIVE):
- Read `.cursor/pipeline/bug-team/ACTIVATION.json` (exact path).
- If `RUNTIME_STATUS == ACTIVE`, for each SEPARATE_ADJUDICATION_REQUIRED=true
  finding, pasteable primary:
  /opsx-bug-team
  (RAW_REPORT / structured finding block as free-form raw envelope;
  team materializes — no prerequisite materialize or fix-bug)
- **First-intake paste fence (CMD-IX-002):** that paste MUST be RAW_REPORT-only —
  no `case=` resume lines, no `ALSO_OK` `/opsx-explore` templates, no
  angle-bracket `case=<CASE_ID>` placeholders (CMD-IX-001). Explore handbacks
  only after a durable CASE_ID exists, in a separate message.

ALTERNATE_INTAKE_HANDOFF (when team not ACTIVE, or owner escape hatch):
- for each SEPARATE_ADJUDICATION_REQUIRED=true finding, pasteable either:
  /opsx-materialize-bug-queue mode=intake
  or
  /opsx-fix-bug
  WITHOUT GO (first-run / intake mode only; with RAW_REPORT)
  Never `/opsx-fix-bug GO` from this hunt.

ROOT_AWARE_FOLLOWUP:
- if a finding needs same-invariant sibling expansion after first fix:
  /opsx-bug-hunt base=… head=… invariant=… root_finding=…

LEARNING_HINT:
- if this run was triggered after a Bugbot miss: cite checklist gaps still open

WHAT_HAPPENED:
WHY:
OWNER_DECISION_REQUIRED:
NEXT_ACTION:
DO_NOT_DO_YET:
```

### Handoff rules

* Ranked next for new discoveries (`SEPARATE_ADJUDICATION_REQUIRED`):
  1. **PRIMARY** — if `.cursor/pipeline/bug-team/ACTIVATION.json` has
     `RUNTIME_STATUS == ACTIVE` → `/opsx-bug-team` with structured finding
     as raw envelope (team owns materialize/claim/route). Missing file or
     non-ACTIVE → treat as not ACTIVE.
  2. **ALTERNATE** (team not ACTIVE, or explicit owner escape hatch) —
     `/opsx-materialize-bug-queue mode=intake` **or** `/opsx-fix-bug`
     WITHOUT GO (first-run / intake only).
  3. **Forbidden from this hunt** — `/opsx-fix-bug GO` (production GO only
     after durable claim/classify/RED on the fix-bug path).
* After durable intake on the **manual** queue path + `CHAT_REQUIRED`:
  `/opsx-claim-next-bug case=… chat_label=…`
* Do **not** skip claim-first for chat-required findings on the manual path.
* Do **not** emit `/opsx-fanout-bug-hunt` unless a prior root-aware
  `/opsx-bug-hunt` result exists (fanout is not for this command's output).

## Failure / recovery

| Condition | STATUS | NEXT |
|---|---|---|
| Missing base/head | `BLOCKED_NEEDS_INPUT` | ask refs |
| Diff empty and no focus/scope | `BLOCKED_NEEDS_INPUT` | ask scope/focus |
| Preflight hang/timeout | `BLOCKED_PREFLIGHT` | narrow scope; retry |
| ADL gap on ownership/write-path | `EVIDENCE_GAP` | stop NO_GO-style; do not invent decision |
| Only residual/uncertain items | `HUNT_COMPLETE` | create-pr may proceed; Bugbot section = residual |

## Relationship to Bugbot

1. Run **this** command before `/opsx-create-pr`.
2. Put only **residual** risks into PR «Что проверить Bugbot / reviewer».
3. If Bugbot reports a **product/logic** bug this hunt missed:
   - intake + fix via normal bug path;
   - then `/opsx-learn-from-bug` with preferred target =
     `.cursor/commands/opsx-project-bug-hunt.md` checklist section
     (or hunter feedback note from `/opsx-fix-bug`);
   - re-run `/opsx-project-bug-hunt` on a similar diff class to verify the
     new check would have caught it.

## Project hunt checklist (learning target)

Authoritative list of **project-specific** checks. Prefer extending this
section via `/opsx-learn-from-bug GO` (existing target) when Bugbot or a
human finds a miss. Keep items concrete and falsifiable.

### Cache / data paths

* [ ] shop-runner required Redis data miss must not soft-fallback when contract
      is strict (`ShopRunnerKeywordsCacheMissError` class paths).
* [ ] min_bids read-only cache miss logs WARNING (not ERROR); WB refresh
      failures remain ERROR — do not “fix” by silencing.
* [ ] UI keyword fetch vs shop-runner keyword path not confused
      (`fetch_keywords_from_database` vs `ComplexAdv.get_keywords`).

### Mode / paid-free / campaign

* [ ] free / paid / common mode defaults respect
      `openspec/decisions/mode-defaults-policy-ownership` (or cited ADL).
* [ ] free flow cannot reach paid automation entrypoints.
* [ ] campaign state transitions do not skip setup / activation gates
      touched by the diff.

### A/B Hold / structural writes

* [ ] structural WB writes blocked for freeze states when A/B Hold invariants
      appear in diff or focus=`card_ab_hold`.
* [ ] Telegram parse_mode / message length / callback contracts preserved for
      touched handlers.

### Persistence consistency

* [ ] Redis / PostgreSQL / ClickHouse writes touched by the diff preserve
      cross-store consistency expectations cited from design/ADL.
* [ ] no silent no-op that still reports user-visible success.

### Tests realism

* [ ] new/changed tests do not mock away the causal boundary they claim to
      protect (testing-rules).
* [ ] unit vs integration placement matches `tests/unit` vs `tests/integration`.

### Process surface (do not hunt as product)

* [ ] If diff only touches `.cursor/commands/**` / rules / skills — stop and
      route to F6 admin path; do not invent product findings.

<!-- LEARNING_APPEND: add new checkbox items above this line; never delete
     historical miss lessons without owner approval. -->

## Hard rules

* Diff- or focus-anchored — no aimless whole-repo tourism.
* No production classification without reachability reasoning.
* No `/opsx-fix-bug GO` handoff from this hunt. Intake WITHOUT GO is allowed
  only as **alternate** when bug-team is not ACTIVE (or owner escape hatch).
* When `ACTIVATION.json` `RUNTIME_STATUS == ACTIVE`, primary next is
  `/opsx-bug-team` — do not demote team to residual after materialize advice.
* No process-contract hunting in this command (F6).
* Do not claim Bugbot is obsolete; claim **this** is primary discovery.
* Do not weaken `/opsx-bug-hunt` root+invariant requirements by routing
  sibling hunts here.
* Checklist updates are learning writes — not silent mid-hunt edits unless
  `/opsx-learn-from-bug GO` (or explicit owner edit) authorized them.
* Do not emit finding blocks with code-location but without `LOC_LINK`.

## Anti-patterns

* Renaming Bugbot noise into “findings” without project grounding.
* Turning `deep` into a repository-wide style pass.
* Fixing dead code to impress Bugbot.
* Using this command as `/opsx-explore` or pipeline navigator.
* Creating a parallel case-map layout outside materialize / bug-team.
* Recommending materialize-first while bug-team `RUNTIME_STATUS` is ACTIVE.
