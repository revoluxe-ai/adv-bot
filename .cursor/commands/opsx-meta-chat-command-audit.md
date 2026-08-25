---
component_id: opsx.commands.meta_chat_command_audit
component_version: 0.2.0
ownership: TARGET_ONLY
runtime_class: ACTIVE
canonical_source_body: adapted_target_native
required_adapters: ["opsx-lite"]
local_modification_note: "v0.2: repo-bound chat audit registry under .tmp/opsx-chat-audit; content-hash skip; archival walk; GO writes registry only"
local_override_policy: TARGET_OVERRIDE_HIGHEST_PRIORITY
contract_id: OPSX-WB-META-CHAT-COMMAND-AUDIT-01
newline_normalization: none
---

# TARGET OVERRIDE — HIGHEST PRIORITY

**Contract:** `OPSX-WB-META-CHAT-COMMAND-AUDIT-01`  
**Runtime class:** `ACTIVE`  
**Precedence:** This override wins for target paths, capabilities, safety stops, and authority.

### Target authority paths

- Command contract (this file): `.cursor/commands/opsx-meta-chat-command-audit.md`
- Agent transcripts (READ_ONLY evidence): Cursor project
  `agent-transcripts/**` for **this workspace / this repo only**
  (live parent chats + nested `subagents/` when cited + any archived /
  relocated transcript trees Owner names under the same project root)
- **Audit registry (writable, local-only):** `.tmp/opsx-chat-audit/**`
  — gitignored; never commit; never share across repos

### Hard target bans

- Never edit other `.cursor/**` contracts, `.opsx/**` (except reading
  projectization), `openspec/**`, `app/**`, `tests/**`, or git history.
- Never write a durable SoT under `.opsx/registry/**` for chat audit state —
  chat registry lives **only** in `.tmp/opsx-chat-audit/**`.
- Do not stage, commit, push, rebase, force, open PR, or deploy.
- Do not access production / Kubernetes / secrets.
- Do not install dependencies / modify Poetry lock / `pyproject.toml`.
- Do not copy / import process surfaces from sibling projects
  (cross-project import ban).
- Do not invent defects without transcript or git evidence.
- Do not treat chat answers as a second lifecycle authority.
- Do not scan another repo’s `agent-transcripts` or reuse another repo’s
  `.tmp/opsx-chat-audit` index.
- Missing undeclared capabilities => UNAVAILABLE or FAIL_CLOSED, never
  PASS-by-absence.
- Do not run `/opsx-meta-fix-command-defects` APPLY / `/opsx-meta-commit`
  GO as a side effect of this command.

### Projectization gate

Read `.opsx/projectization.yaml` before any work.
If `status` != `COMPLETE` or `normal_commands_enabled` is false:

```text
STATUS: FAIL_CLOSED
REASON: OPSX_PROJECTIZATION_REQUIRED
NEXT_COMMAND: /opsx-projectize
```

# BEGIN CANONICAL SOURCE BODY
---
name: /opsx-meta-chat-command-audit
id: opsx-meta-chat-command-audit
category: Workflow
description: "Walk this-repo agent chats (incl. archive) via .tmp hash registry; find multi-command defects; hand off fixes (never APPLY contracts)"
argument-hint: "[N=4|ALL|CHAT=<uuid>...] [ARCHIVE=1] [FORCE] [FOCUS=<token>] [GO] [incident note]"
---

# /opsx-meta-chat-command-audit

**Chat-history audit** for OPSX **command interaction** failures on **this
repo only**.

Walk Cursor agent transcripts (recent + archival under the same project),
maintain a **repo-bound** study registry in `.tmp/opsx-chat-audit/`, skip
chats whose **content hash** is unchanged, classify multi-command defects,
and emit one pasteable handoff (`FIX_PLAN_READY` /
`DESIGN_BRIEF_READY`).

Contract APPLY stays on `/opsx-meta-fix-command-defects` /
`/opsx-meta-design-command`. This command may write **only** its `.tmp`
registry after `GO`.

Follow `.cursor/commands/opsx-source-resolution.md` and
`.cursor/commands/opsx-execution-preflight.md` (Read / tool I/O budgets).

## Purpose

1. Walk agent chat JSONL for **this workspace/repo** (not sibling trees).
2. Include archival / older parent chats when in scope (`ALL` / `ARCHIVE=1`
   / named `CHAT=`).
3. Keep a local registry of studied chats keyed by
   `(repo_key, chat_id, content_hash)`.
4. If hash matches last study → `UNCHANGED` — no re-analysis, no “new data”.
5. If hash differs or chat is new → analyze, record findings fingerprint,
   update registry (with `GO`).
6. Hand off contract fixes; never apply them here.

## Repo binding (mandatory)

```text
REPO_KEY = lowercase(git rev-parse --show-toplevel basename)
  + "|" + short(git rev-parse HEAD)   # informational watermark only
WORKSPACE_ROOT = git rev-parse --show-toplevel
TRANSCRIPT_ROOT = <Cursor project agent-transcripts for THIS workspace>
REGISTRY_DIR = <WORKSPACE_ROOT>/.tmp/opsx-chat-audit/
REGISTRY_FILE = REGISTRY_DIR/registry.ndjson
STATE_FILE = REGISTRY_DIR/state.yaml
```

Rules:

- Every registry row MUST include `repo_key` matching this workspace.
- Rows with a different `repo_key` are **ignored** (never reused).
- Never read/write `.tmp/opsx-chat-audit` from another checkout.
- Never invent a global/cross-repo chat index.

## Registry layout (`.tmp` only)

### `state.yaml`

```yaml
schema_version: 1
repo_key: <REPO_KEY>
workspace_root: <WORKSPACE_ROOT>
transcript_root: <TRANSCRIPT_ROOT>
updated_at: <UTC ISO8601>
```

### `registry.ndjson` (one JSON object per line)

```json
{
  "repo_key": "...",
  "chat_id": "<parent uuid>",
  "transcript_relpath": "<uuid>/<uuid>.jsonl",
  "content_hash": "sha256:<hex>",
  "byte_size": 0,
  "mtime_utc": "...",
  "last_studied_at": "...",
  "study_status": "STUDIED|UNCHANGED|ERROR",
  "findings_fingerprint": "sha256:<hex>|none",
  "finding_classes": [],
  "audit_command_version": "0.2.0"
}
```

Hashing:

- `content_hash` = `sha256` of the **parent** transcript file bytes
  (`<chat_id>/<chat_id>.jsonl`) as on disk (UTF-8 / raw bytes).
- Do **not** fold subagent JSONL into the parent hash unless Owner later
  expands the contract; subagents are opened only when a parent finding
  cites them.
- `findings_fingerprint` = sha256 of normalized FINDINGS list for that chat
  (stable sort by `DEFECT_CLASS`+`SUMMARY`), or `none` if empty.

Skip rule:

```text
if row.repo_key == REPO_KEY
   and row.chat_id == chat_id
   and row.content_hash == current_hash
   and FORCE absent
→ STATUS_FOR_CHAT: UNCHANGED
  do not re-read body for analysis
  do not claim new findings from that chat
```

`FORCE` re-analyzes even when hash matches (still updates registry on `GO`).

## When to use

- Postmortem of multi-command sessions on this repo.
- Periodic sweep: “что нового в чатах с прошлого аудита?”
- After messy `/opsx-commit-all` / evolution / meta hops.
- Seed: process child committed product OpenSpec (scope bleed).

## When not to use

| Situation | Use instead |
|---|---|
| Relationship / which command? | `/opsx-meta-consult` |
| Defect FILES already known | `/opsx-meta-fix-command-defects` |
| New command without transcript walk | `/opsx-meta-design-command` |
| Lesson after FIXED/Bugbot | `/opsx-meta-promote-process-lesson` |
| Product bug | `/opsx-fix-bug` |
| Commit process files | `/opsx-meta-commit` |

## Authority boundary

| Surface | This command |
|---|---|
| Contract APPLY (`.cursor/commands/**` others) | **forbidden** |
| Durable `.opsx/registry/**` chat index | **forbidden** |
| `.tmp/opsx-chat-audit/**` | **allowed after `GO`** |
| Transcripts | READ_ONLY |
| Git history rewrite | forbidden |

`GO` authorizes **registry write only**, not fix APPLY.

Without `GO`: full analyze/report still runs (READ_ONLY); registry updates
are proposed but **not** written (`REGISTRY_WRITE: SKIPPED_NO_GO`).

## User input

```text
$ARGUMENTS
```

| Token | Effect |
|---|---|
| `N=<int>` | Newest N **parent** chats (default `4`, max `20` unless `ALL`) |
| `ALL` | All parent chats under transcript root for this repo project |
| `ARCHIVE=1` | Explicitly include older/archived parents beyond the default N window (implied by `ALL`) |
| `CHAT=<uuid>` | Force-include parent id (repeatable) |
| `FORCE` | Re-analyze even when `content_hash` matches |
| `FOCUS=<CLASS>` | Prefer one defect class |
| free text | Incident hint (SHA, command names) |
| `GO` | Write/update `.tmp/opsx-chat-audit/**` for studied/unchanged rows |

Empty args → `N=4` for this repo’s transcript root.

## Modes

| Input | Mode | Writes |
|---|---|---|
| no `GO` | `ANALYZE_ONLY` | none |
| `GO` | `ANALYZE_AND_RECORD` | only `.tmp/opsx-chat-audit/**` |

## Pattern library

| DEFECT_CLASS | Meaning |
|---|---|
| `SCOPE_BLEED` | Writer committed paths outside its authority |
| `WRONG_LANE_WRITER` | Process lane wrote product (or reverse) |
| `PARENT_GIT_WRITE` | Orchestrator parent performed git add/commit |
| `MISSING_SERIALIZE` | Parallel execute Tasks raced on git |
| `STALE_PLAN_EXECUTE` | Execute used a plan that no longer matched the tree |
| `CROSS_COMMAND_HANDOFF_GAP` | Producer token not consumed; no pasteable next |
| `PROCESS_CONTRACT_GAP` | Missing guard that would have blocked the failure |
| `FOREIGN_SURFACE_IMPORT` | Sibling/donor surface without Owner KEEP/import |
| `NEEDS_EVIDENCE` | Suspicion only |

## Evidence sources (bounded)

1. Transcripts under **this** `TRANSCRIPT_ROOT` (parents; subagents if cited).
2. Git for named SHAs/paths only.
3. Cited command contracts: Grep-first; parallel Read max **2**; section
   Read ≤ 120 lines; ≤ **5** substantive section-Reads unless `EVIDENCE_GAP`.

### Transcript I/O budgets

- Prefer inventory → hash → skip UNCHANGED before any deep extract.
- Deep extract only for `NEW` / `CHANGED` / `FORCE` chats.
- No full JSONL dump into the reply.
- Per analyzed chat: ≤ **12** hit snippets.
- Encoding: UTF-8.

## Steps

1. Projectization gate + resolve `REPO_KEY`, `TRANSCRIPT_ROOT`, registry paths.
2. Load registry if present; drop rows with foreign `repo_key`.
3. Inventory parent chats (mtime order). Apply `N` / `ALL` / `ARCHIVE=1` /
   `CHAT=`.
4. For each selected chat: compute `content_hash`; mark
   `UNCHANGED` | `CHANGED` | `NEW`.
5. Analyze only non-`UNCHANGED` (unless `FORCE`).
6. Classify findings; build handoff packet if needed.
7. If `GO`: mkdir `.tmp/opsx-chat-audit/` as needed; upsert registry rows +
   `state.yaml` for **this** `repo_key` only.
8. If no `GO`: report proposed registry deltas; do not write.
9. Never APPLY contract fixes in this turn.

## Route classes (exactly one primary)

| ROUTE_CLASS | Typical NEXT_ACTION |
|---|---|
| `route_fix_defects` | `/opsx-meta-fix-command-defects` |
| `route_design_command` | `/opsx-meta-design-command` |
| `route_promote_lesson` | `/opsx-meta-promote-process-lesson` |
| `route_consult` | `/opsx-meta-consult` |
| `route_meta_commit` | `/opsx-meta-commit` (command file only) |
| `answered_in_place` | `none` |
| `needs_evidence` | `none` + one question |

## Output contract (every run)

```text
STATUS: AUDITED | ROUTED | BLOCKED_NEEDS_EVIDENCE | FAIL_CLOSED
MODE: ANALYZE_ONLY | ANALYZE_AND_RECORD
REPO_KEY:
REGISTRY_PATH: .tmp/opsx-chat-audit/registry.ndjson
REGISTRY_WRITE: APPLIED | SKIPPED_NO_GO | FAILED
WHAT_HAPPENED:
WHY:
CHATS_INVENTORY:
  SELECTED:
  NEW:
  CHANGED:
  UNCHANGED_SKIPPED:
  ANALYZED:
FINDINGS:
- DEFECT_CLASS:
  SUMMARY:
  EVIDENCE_REFS:
  SUSPECT_COMMANDS:
  SUSPECT_FILES:
  CHAT_ID:
ROUTE_CLASS:
HANDOFF_PACKET:
OWNER_DECISION_REQUIRED:
NEXT_ACTION:
DO_NOT_DO_YET:
ORIENTATION_HINT:
  LANE: META
  STATUS:
  NEXT_META: /opsx-meta
  NEXT_ACTION:
```

### HANDOFF_PACKET shapes

```text
STATUS: FIX_PLAN_READY
SOURCE: opsx-meta-chat-command-audit
DEFECTS_TO_FIX:
FILES:
PROPOSED_BEHAVIOR:
EVIDENCE_REFS:
```

```text
STATUS: DESIGN_BRIEF_READY
SOURCE: opsx-meta-chat-command-audit
PROBLEM:
WHY_EXISTING_NOT_ENOUGH:
EVIDENCE_SEED:
CONSTRAINTS:
```

## Failure / recovery

| Condition | STATUS | NEXT_ACTION |
|---|---|---|
| No transcript root | `BLOCKED_NEEDS_EVIDENCE` | `none` |
| Registry IO error on `GO` | `AUDITED` + `REGISTRY_WRITE: FAILED` | retry `GO` or fix `.tmp` perms |
| All selected UNCHANGED, no findings | `AUDITED` | `none` |
| Clear FILES for contract fix | `ROUTED` | `/opsx-meta-fix-command-defects` |
| Projectization incomplete | `FAIL_CLOSED` | `/opsx-projectize` |

## Absolute prohibitions

- Writing chat audit state outside `.tmp/opsx-chat-audit/**`
- Reusing another repo’s registry rows
- Scanning sibling project transcripts
- Editing process/product contracts from this command
- `git add` / `git commit` of `.tmp/**`
- Full dump of all transcripts or all commands

## Seed regression (must remain detectable)

When transcripts/git still contain:

- `/opsx-commit-all` → child `/opsx-meta-commit GO`
- commit message process-only, tree includes product `openspec/changes/**`
  / `openspec/specs/**` / product decisions

→ MUST classify `SCOPE_BLEED` (often + `WRONG_LANE_WRITER` /
`PROCESS_CONTRACT_GAP`) on the **first** analyze of that chat; later runs
with matching `content_hash` may report `UNCHANGED_SKIPPED` unless `FORCE`.

# END CANONICAL SOURCE BODY

# TARGET ADAPTATION NOTES

- active_name: `/opsx-meta-chat-command-audit`
- contract_id: `OPSX-WB-META-CHAT-COMMAND-AUDIT-01`
- target: WB Sky / Poetry (`opsx-lite`; no `vue-npm`)
- write_boundary: `.tmp/opsx-chat-audit/**` only, and only with `GO`
- registry: gitignored via root `.tmp/`; repo-bound via `repo_key`
- transcript_root: Cursor project `agent-transcripts` for this workspace
- orientation: emit `ORIENTATION_HINT` with `NEXT_META: /opsx-meta`
- first_evidence_seed: commit `61ae744a7` / chat
  `c1eb3665-a2c6-4481-a6ea-2bb70c01491a` / child
  `37fb5542-9fce-4f5b-8edc-b109b38abdab`
