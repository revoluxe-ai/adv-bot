---
description: "Shared OPSX execution-preflight contract: purpose-driven, bounded, timeout-safe shell/tool ops. Not a standalone user command."
---

# OPSX Execution Preflight Contract

Shared mandatory contract for shell/tool operations that OPSX commands run before or beside their main work.

This file is **not** a user-facing `/opsx-*` workflow command.
Any OPSX command that references it MUST follow it for git/status/diff/find/rg/test-discovery and similar preflight operations.

Companion contract: `.cursor/commands/opsx-source-resolution.md` (artifact resolution).
This contract covers **execution cost / hang risk**, not path rediscovery.

## TOPIC_INTENT / Owner-message re-anchor (mandatory)

**Defect class:** sticky prior-turn topic hijacks a new Owner ask
(`PF-TOPIC-INTENT-REANCHOR-001`; pattern donor:
`opsx-admin-command-analyze-pipeline.md` /
`CMD-ANALYZE-PIPELINE-TOPIC-STICKY-001`).

Authority cited (enforce, do not invent a parallel DONE gate):

```text
.cursor/pipeline/contracts/PRODUCT_ACCEPTANCE.md  (MEANING_LOCK)
.cursor/pipeline/contracts/SEMANTIC_WRITE_TARGET.md
```

Any OPSX command that references this preflight contract MUST, **before**
interpreting Owner text, choosing a branch (product vs process/learning),
or running transcript/history search as the primary frame:

1. Resolve exactly one topic from the **current** user message first.
   Prior turns are hints only; they MUST NOT become the default topic.

```text
TOPIC_INTENT: PRODUCT_BRIEF | PROCESS_PIPELINE | AMBIGUOUS
```

   Commands MAY use an equivalent local enum that preserves
   **current-message-first** (same sticky-topic ban).

2. Forbidden: treat «обучение» / learning / promote / `DEFERRED` from an
   earlier turn as the topic of a new ask that never names those.

3. If `AMBIGUOUS` (e.g. bare «задача», «найди чаты где я объяснял») → ask
   **one** narrow disambiguation question and stop; do not answer from the
   sticky prior topic yet.

4. For product-touching work: when the current message does not name
   learning/promote/process, prefer durable product SoT
   (`openspec/evolution/**` / active STAR when applicable) over the last-chat
   learning / promote / `DEFERRED` thread.

5. Emit `TOPIC_INTENT:` (and, when product-touching and a STAR is known,
   a one-line `ACTIVE_PRODUCT_INTENT` echo from that durable path) in the
   **first** status block of the run.

This section does **not** authorize creating a new `/opsx-*` command file;
consumers extend behavior by following this shared contract.

## Goal

Prevent hangs on unconditional preflight shells when those results are not required for the current command decision.

Do **not** delete necessary checks.
Make every operation purpose-driven, bounded, timeout-safe, and skippable when irrelevant.

## Hard principle

Never run an operation only because it traditionally appears in a preflight checklist.

Before every shell/tool operation, the command MUST be able to fill:

```text
OPERATION_REASON:
REQUIRED_FOR:
SKIP_IF:
TIME_BUDGET:
FAILURE_BEHAVIOR:
```

If `REQUIRED_FOR` is empty or not needed for the current decision, **skip** the operation.

### REQUIRED_GATE_INPUT materialization (pointer)

When a command output is a later independent gate input (not merely chat
narration), prefer durable evidence over chat history as SoT. Canonical
cross-cutting rule:

```text
.cursor/pipeline/GRAPH.md → ## Process invariants
  → REQUIRED_GATE_INPUT must materialize
```

Do not invent a second competing rule here. Do not materialize every
transient preflight/shell result under that invariant.

## Default time budgets

| Operation class | Default TIME_BUDGET | Notes |
|---|---|---|
| `git branch --show-current` | 5s | local metadata |
| `git status --short` | 10s | can hang on huge/dirty trees or locks |
| `git diff` / `git diff --stat` (unstaged/staged) | 15s | defer until staging/commit/PR decision |
| `git rev-parse` / short `git log` | 10s | required only when refs matter |
| `git fetch` / remote checks | 30s | never for read-only classify |
| `rg` / targeted search | per source-resolution budget | not a default preflight |
| `find` inventories | forbidden by default | fallback only with EVIDENCE_GAP |
| test discovery / pytest collect | defer until test command needs it | |
| `Read` / file open | see **Read / tool I/O budgets** below | hang class separate from git |
| parallel `Read` batch | max **2** concurrent | never dump whole command-set |

Commands MAY tighten these budgets; they MUST NOT remove budgets for optional ops.

## Read / tool I/O budgets

Third hang class (after unbounded search and unconditional git): **mass or stuck file Reads**.

Hard rules for every OPSX command:

1. Prefer `Grep` / path inventory over full-file `Read` when only a token, gate, or section is needed.
2. Read **exact listed paths** first (defect FILES, `artifactPaths`, user paths, receipt paths).
3. Do **not** preload sibling process docs “for context” unless a field in the current decision requires them.
4. Parallel `Read`: at most **2** concurrent calls. Never open an entire `.cursor/commands/opsx-*.md` set in one turn.
5. Large process files (`opsx-invariant`, `opsx-fix-bug`, `opsx-verify`, `opsx-materialize-bug-queue`, `opsx-learn-from-bug`, `opsx-admin-command-design-command`, `opsx-admin-command-analyze-pipeline`, …): use `Read` with `limit`/`offset` (default first pass ≤ **120** lines or a Grep hit ± context). Full-file read only when REQUIRED_FOR the decision.
6. After each required file is understood, **act** (patch / classify / extract) before opening the next unrelated file.
7. If a `Read` does not return within ~**30s**, stop waiting; do not stack more Reads on the same turn. Record:

```text
READ_IO_RESULT:
- path:
- status: ok | timeout | deferred | skipped
- required_for_decision: true | false
```

8. Timeout on optional context → continue. Timeout on a required defect/artifact path → command-compatible blocker (`blocked_preflight_timeout` / `EVIDENCE_GAP`), not silent hang.
9. Subagents that extract “ALL opsx commands” MUST use Grep-first + sequential bounded Read, not parallel full-file dumps.

`FULL_OPSX_AUDIT` / pipeline analysis / command-set review are **not** exemptions.
Reserved high-risk gate-pair section-Reads inside `/opsx-review-commands`
(checklist / two-pass FULL) still count toward that command’s mode Read cap
and still obey parallel `Read` ≤ **2** — they are prioritization, not a
budget exemption.

## Shell payload I/O (anti-heredoc)

Fourth failure class (after unbounded search, unconditional git, mass Reads):
**fragile multi-line Shell payloads via bash heredoc**.

Hard rules for every OPSX command that runs Shell:

1. **Forbidden for multi-line / nested-quote payloads** (JSON, Python, scripts,
   multi-paragraph commit/PR bodies, nested quotes):
   - bash heredoc: `cat <<EOF`, `cat <<'EOF'`, `$(cat <<'EOF' ...)`
   - embedding the full body as one quoted Shell argument when quotes or
     truncation regularly break the run
2. **Required pattern:** write the payload with the **Write** tool (or an
   equivalent file write) to a workspace path, then invoke by path:
   - `python path\to\script.py`
   - `git commit -F path\to\COMMIT_MSG.txt`
   - `gh pr create ... --body-file path\to\pr_body.md`
3. Single-line Shell args with no nested quotes remain OK.
4. Do not teach bash-heredoc recipes in command bodies for those payloads;
   prefer Write → path / `--body-file` / `-F`.
5. If a Shell heredoc truncates or fails quoting → stop retrying heredoc;
   switch to Write→path once and continue (do not loop).

Defect class id (for learn/promote): `HEREDOC-SHELL-PAYLOAD-001`.

## Failure / timeout behavior

When a preflight operation times out, hangs, or fails:

1. stop waiting;
2. do **not** retry the same op in a loop;
3. record:

```text
PREFLIGHT_RESULT:
- operation:
- status: skipped | ok | timeout | failed | deferred
- required_for_decision: true | false
```

4. if `required_for_decision=false` → continue the main command;
5. if `required_for_decision=true` → return a command-compatible blocker such as:

```text
RESULT: blocked_preflight_timeout
```

or existing `blocked` / `NO_GO` with the missing fact named.

Never block a read-only classification solely because optional git metadata was slow.

## Command-class defaults

### A. Read-only classification / routing
Examples: `/opsx-classify-bug`, read-only portions of `/opsx-fix-bug` without `GO`, `/opsx-fanout-bug-hunt` source ingest.

Default:

* resolve durable/exact sources first;
* **skip** `git status` / `git branch` / `git diff` unless the decision explicitly depends on dirty-tree or branch identity;
* output fields like `branch:` / `dirty files:` may be:

```text
deferred_not_required
```

### B. Adjudication / forensics with code evidence
Examples: `/opsx-fix-bug` forensics, `/opsx-invariant`, `/opsx-bug-hunt`.

Default:

* git metadata only when needed for `base`/`head`/dirty interaction with the claim;
* `rg` only after packet/source resolution and only for packet symbols;
* never run git status as step 0 before reading known case/finding.

### C. Git-mutating / PR / split / commit workflows
Examples: `/opsx-commit`, `/opsx-meta-commit`, `/opsx-create-pr`, `/opsx-split-for-pr`.

Default:

* git status/diff/log **are** usually required for the decision;
* still apply TIME_BUDGET and FAILURE_BEHAVIOR;
* prefer the smallest git command that answers the required fact;
* `git fetch` only when remote freshness is REQUIRED_FOR the decision.

### D. OpenSpec lifecycle CLI workflows
Examples: `/opsx-apply`, `/opsx-verify`, `/opsx-sync`, `/opsx-continue`.

Default:

* prefer `openspec ... --change "<name>"` over git preflight;
* git only when dirty-tree or branch identity is REQUIRED_FOR apply/verify safety.

## Output fragment

Affected commands SHOULD include (or embed equivalently):

```text
EXECUTION_PREFLIGHT:
- git_branch: skipped | ok | timeout | failed | deferred_not_required
- git_status: skipped | ok | timeout | failed | deferred_not_required
- other_ops:
- blocked_on_preflight: true | false
```

## Hard rules

* No unconditional “always run git status first”.
* Optional preflight must not gate the main read-only decision.
* Timeout → continue or blocker by `required_for_decision`, never silent hang.
* No mass parallel file Reads; Grep/section-first; parallel Read max 2.
* Do not invent a second status taxonomy when the command already has blockers.
* Keep companion source-resolution rules for artifact rediscovery.

## Windows Shell JSON / JSONL write safety (mandatory)

Applies whenever an agent appends or writes JSON/JSONL via Shell/Python
(including `DISPATCH.jsonl`, `ROUTE-TRACE.jsonl`, team packets, and similar
durable case artifacts) instead of an authoritative runtime helper.

On Windows the default locale/console encoding is often `cp1251` /
`charmap`. `json.dumps(..., ensure_ascii=False)` plus a non-UTF-8 stream
fails with `UnicodeEncodeError` on characters such as `→` (`U+2192`) when
those appear in payload fields copied from command prose.

### Required recipe (ad-hoc Shell / stdin Python)

1. Always open/write with explicit UTF-8:
   `Path.open(..., encoding="utf-8")` or `Path.write_text(..., encoding="utf-8")`.
2. For agent-authored recipes: `json.dumps(obj, ensure_ascii=True)`
   (ASCII-safe even if a debug `print` or a missing encoding slips in).
3. Do **not** `print()` the JSON/JSONL line to the console unless stdout is
   UTF-8 (`PYTHONIOENCODING=utf-8` or `sys.stdout.reconfigure(encoding="utf-8")`).
   Prefer no print of the payload line.
4. In machine-written string fields prefer ASCII `->` over Unicode `→`.
5. When a bug-team / route-trace runtime helper exists (e.g.
   `live_task_hop`, `route_trace.append`), prefer it over ad-hoc stdin append.

### Forbidden (ad-hoc recipes)

```text
open(path, "a") without encoding="utf-8"
json.dumps(..., ensure_ascii=False) in agent Shell/stdin recipes
print(json.dumps(..., ensure_ascii=False)) to a cp1251 console
relying on Windows default locale for JSONL bytes
```

Cite this section from DISPATCH / ROUTE_TRACE SoTs and from commands that
require durable JSONL append. Do not invent a second incompatible recipe.
