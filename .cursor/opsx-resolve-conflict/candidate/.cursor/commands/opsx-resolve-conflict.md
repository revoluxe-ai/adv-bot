---
name: /opsx-resolve-conflict
id: opsx-resolve-conflict
package_version: 0.39.0
contract_schema_version: opsx-resolve-conflict/v2
status: candidate_for_independent_review
author: Cursor
supported_runner: Cursor Agent with Python 3.11+ and packaged typed runtime
required_capabilities:
  - direct Python process execution without shell interpolation
  - filesystem write access limited by frozen scope manifest
  - Git executable
  - Poetry executable for mandatory Wave A/B validation
  - externally attested OS sandbox runner
  - durable user-state directory outside repository
  - process-group cancellation
description: "Fail-closed Git conflict resolution with applicable authority, race-safe writes, durable receipts, and mandatory Wave A/B validation."
argument-hint: "[PREVIEW|GO] [change=<CHANGE_ID>] [store=<STORE_ID>]"
---

# /opsx-resolve-conflict

## 0. Status and installation boundary

This file is one component of package
`OPSX_RESOLVE_CONFLICT_COMMAND_001_R39`.

Packages `0.5.0` / R05 through `0.13.0` / R13 are **REJECTED** and must not be
used for GO.

R12 restricts autonomous resolution to a single-file, namespace-closed,
comment-exact append-only Python AST union. It freezes validation bytes and
exact argv, verifies the actual staged blob/mode, uses hash-only write-ahead
recovery, and commits success through one atomic terminal bundle.
Independent review still required.

Do not run `GO` unless all packaged files are installed and the startup
compatibility gate passes:

```text
.cursor/commands/opsx-resolve-conflict.md
.cursor/opsx-resolve-conflict/runtime/opsx_conflict/**
.cursor/opsx-resolve-conflict/MANIFEST.json
.cursor/opsx-resolve-conflict/schemas/**
```

A Markdown prompt alone is not an enforceable execution boundary.

R12 GO additionally requires `OPSX_CONFLICT_TRUST_DIGEST`, supplied by an
independent installer/reviewer from outside the mutable package tree. The
value is the exact 64-hex `package_digest` published in the review sidecar.
Missing, malformed, or mismatched external trust causes STOP before Git-state
mutation.

Autonomous text resolution is limited to Python modules where stage 2 and
stage 3 each append only simple undecorated functions to an unchanged base
AST, and the candidate is the exact AST union. Added functions may use only
arguments, locals, constants, and pure operators: module globals, calls,
attributes, subscripts, mutation, shared effects, imports, and nested scopes
STOP. Every comment token must equal base exactly, so unknown tool directives
cannot enter the autonomous class. Module namespace hooks (`__getattr__`,
`__dir__`, and `__all__`) STOP.
All modifications of existing logic, non-Python files, decorators/defaults,
binary content, and ambiguous transformations STOP before write.

If the runtime, manifest, schema, required repository contracts, durable
state directory, ACL enforcement, or process cancellation support is
missing:

```text
STATUS=STOP_FOR_OWNER
STOP_REASON=EXECUTION_CAPABILITY_OR_COMPATIBILITY_MISSING
```

Only PREVIEW remains allowed.

## 1. Purpose

Resolve the currently active Git `merge`, `rebase`, or `cherry-pick`
conflict with maximum bounded autonomy and minimum risk of silently losing
behavior.

The command must reconstruct both sides from Git object identity, bind the
result to applicable OPSX/OpenSpec authority, discover textual and logical
conflicts, resolve one frozen atomic scope at a time, run relevant tests,
and **stage** verified resolutions. The Owner continues the Git sequencer
out-of-band; this package does not run `git … --continue`.

Speed is subordinate to correctness.

## 2. Mode and authorization

Parse exact tokens.

### PREVIEW

Default when `GO` is absent or `PREVIEW` is present.

PREVIEW is a **repository-context conflict assistant** (not an autonomous
resolver and not a line-diff chooser). It is read-only:

- load stage 1/2/3 blobs via the sealed R34 exact Git operation grammar;
- collect a bounded structured context packet (siblings, callers/usages,
  tests, accepted decisions/specs) without shell/rg subprocesses;
- separate FACTS from INTERPRETATIONS; attach evidence IDs;
- list coherent resolution options and Owner questions;
- recommend a side **only** when evidence has both a strong
  `authority_class` **and** `authority_verified=true` (explicit accepted
  status / canonical current-spec / verified contract / API invariant);
- path location alone never proves normative authority; draft/proposed/
  rejected/superseded decisions and change-local specs do not recommend;
- never recommend `keep_ours`/`keep_theirs` from textual subset alone;
- never edit, stage, continue, abort, skip, commit, or push.

Human output leads with Russian behavioral explanation; Git OIDs/hashes are
secondary evidence below.

### GO

Exact token `GO` authorizes only the bounded execution described by this
contract.

It does not authorize:

- abort, skip, reset, clean, stash;
- commit outside the active sequencer operation;
- push, fetch, pull, remote mutation, deployment;
- specification, decision, task, bug-case, pipeline, or process-policy edits;
- scope expansion;
- test weakening;
- use of arbitrary shell, scripts, subagents, workers, hooks, nested OPSX
  commands, or direct Cursor file-edit tools.

All repository reads, writes, checks, staging, and continuation must go
through the packaged typed runtime. If an operation is not represented by
a typed runtime action, it is forbidden.

Unknown or contradictory arguments:

```text
STATUS=STOP_FOR_OWNER
STOP_REASON=INVALID_OR_AMBIGUOUS_ARGUMENTS
```

`base=` and `FINAL=FAST` are not supported. Git operation metadata defines
the base. Final validation is always FULL or stronger when an authority
source requires more.

## 3. Incorporated repository contracts

Resolve these exact paths at startup and include their hashes in the run
receipt:

```text
.cursor/commands/opsx-source-resolution.md
.cursor/commands/opsx-execution-preflight.md
.cursor/rules/testing-rules.mdc
openspec/config.yaml
openspec/policies/VERIFY_POLICY.md
openspec/decisions/index.md
.cursor/static-check/registry.yaml
.cursor/static-check/checks/pyright-strict/context.md
.cursor/static-check/checks/pyright-strict/instructions.md
.cursor/static-check/checks/mypy/context.md
.cursor/static-check/checks/mypy/instructions.md
.cursor/static-check/checks/pytest-unit/context.md
.cursor/static-check/checks/pytest-unit/instructions.md
.cursor/static-check/checks/pytest-full/context.md
.cursor/static-check/checks/pytest-full/instructions.md
.cursor/static-check/contracts/synthesis.md
.cursor/pipeline/GRAPH.md
.cursor/pipeline/META.md
.cursor/opsx-review-commands
```

Rules:

- exact path or stable ID before search;
- fallback search only after `EVIDENCE_GAP`;
- at most three targeted searches per unresolved source;
- parallel reads at most two;
- purpose, budget, skip rule, and failure behavior before every operation;
- Poetry-only project checks;
- hash every incorporated contract at startup and recheck before write, stage,
  and terminal publication;
- contract symlinks, non-files, path escapes, or hash drift are mandatory STOP;
- `.cursor/pipeline/GRAPH.md` is advisory navigation material, not semantic,
  GO/NO_GO, lifecycle, archive, or conflict-resolution authority;
- command contracts, accepted decisions, current specs, exact change context,
  durable bug evidence, and Git object identity retain their own authority.

Do not invent a second OPSX lifecycle or global status taxonomy.

## 4. Typed execution and transitive safety policy

### 4.1 Central executor

The packaged runtime is the only executor.

The command must not call:

- raw shell;
- `bash -c`, `sh -c`, PowerShell, `cmd`;
- Python/Node/Ruby/Perl as an arbitrary command wrapper;
- repository wrapper executables;
- Cursor subagents or Task workers;
- nested `/opsx-*` commands;
- direct Cursor edit/apply tools;
- Git hooks.

Typed runtime actions are limited to:

```text
PACKAGE_COMPATIBILITY
STATE_CAPTURE
STAGE_ROLE_VERIFY
AUTHORITY_READ
CHANGE_GRAPH_BUILD
SCOPE_FREEZE
WRITE_SCOPED_FILE
RUN_TYPED_CHECK
STAGE_EXACT_PATHS
STATE_VERIFY
LEDGER_VERIFY
```

`CONTINUE_ACTIVE_OPERATION` is **not** part of the default GO contract in
package 0.29.0 (CF-003). Staging verified resolutions is the terminal GO
mutation; the Owner continues the Git sequencer out-of-band after review.

### 4.2 Validation-process isolation

Tests and static checks run through a package-allowlisted sandbox runner.
GO requires `OPSX_CONFLICT_SANDBOX_TRUST_DIGEST` to match an allowlist entry
with `enforcement_level=OS_VERIFIED`, a matching handshake, and live admission
probes that prove filesystem escape and network are blocked. The packaged
`sandbox_runner.py` is `BEST_EFFORT` path-confinement only and is never
sufficient for GO. Optional `OPSX_CONFLICT_SANDBOX_RUNNER` may point at the
same digest only; self-supplied path+hash pairs outside the allowlist are
rejected. The tracked-file snapshot:

- is outside the repository;
- contains no `.git`;
- contains no untracked files;
- receives no original repository path in environment;
- is mounted through the runner with network denied;
- runs only exact typed `poetry run pytest|pyright|pyright-strict|mypy`
  argv without shell interpolation;
- runs in one controlled process group;
- is joined before the next action;
- is terminated as a process tree on timeout or STOP.

Any check requiring network, credentials, production services, an arbitrary
interpreter command, or the original `.git` directory is not run here and
causes a precise STOP when mandatory.

### 4.3 Continuation and hooks

Default GO **must not** invoke `git merge|rebase|cherry-pick --continue`.
Those operations create commits and may run filters/signing helpers.

If a future Owner-authorized contract re-enables continuation, it must be a
separate typed action with an explicit GO token and sealed Git-config
neutralization. Until then, `_continue` is a hard `PolicyViolation`.

### 4.4 Cancellation barrier

On STOP:

1. set durable run state to `STOPPING`;
2. reject new actions;
3. terminate every registered process group;
4. join all processes;
5. verify that no registered process remains;
6. append and fsync `CANCELLATION_BARRIER_CLOSED`;
7. only then return the final response.

The final response must be generated after the barrier, never from a worker
notification.

### 4.5 Execution ledger

Every action is appended to a UTF-8 JSONL hash chain outside the repository.

Each record contains:

```text
schema
timestamp
run_id
event
typed_action
argv when applicable
cwd
state_fingerprint_before
state_fingerprint_after
input hashes
output hashes
exit code
timeout
previous record hash
record hash
```

`FORBIDDEN_COMMANDS_EXECUTED=0` and `PUSH_PERFORMED=NO` may be claimed only
from an independently verified finalized ledger.

## 5. Explicit forbidden operations

The runtime must reject direct or indirect requests for:

```text
git reset
git clean
git stash
git checkout
git switch
git restore
git rebase --abort
git rebase --skip
git cherry-pick --abort
git cherry-pick --skip
git merge --abort
git commit
git commit --amend
git push
git fetch
git pull
git remote
git update-ref
git worktree
git add .
git add -A
```

Also forbidden:

- mechanical `Accept Both`;
- whole-file `ours` or `theirs`;
- mass marker removal;
- whole-repository formatting;
- arbitrary wrapper/script execution;
- modification of tests to fit the selected implementation;
- modification of non-conflicted files;
- staging rollback through `git restore --staged`;
- automatic cleanup or deletion of recovery evidence.

If staged contamination is detected, STOP without further index mutation.

## 6. Normative operation and stage-role matrix

Every side must be named by role and object ID. Bare `ours` and `theirs`
are prohibited in analysis and receipts.

### 6.1 Merge

```text
operation_head = MERGE_HEAD
stage 1 = blob at merge-base(HEAD, MERGE_HEAD)
          role: MERGE_BASE
stage 2 = blob at HEAD
          role: CURRENT_HEAD
stage 3 = blob at MERGE_HEAD
          role: INCOMING_MERGE_HEAD
```

### 6.2 Rebase

```text
operation_head = REBASE_HEAD / stopped-sha
stage 1 = blob at parent(operation_head)
          role: PARENT_OF_REPLAYED_COMMIT
stage 2 = blob at current HEAD
          role: ACCUMULATED_ONTO_PLUS_ALREADY_REPLAYED_COMMITS
stage 3 = blob at operation_head
          role: CURRENT_REPLAYED_COMMIT
```

This is the normative rebase meaning even though Git labels stage 2 as
`ours` and stage 3 as `theirs`.

### 6.3 Cherry-pick

```text
operation_head = CHERRY_PICK_HEAD
stage 1 = blob at parent(CHERRY_PICK_HEAD)
          role: PARENT_OF_CHERRY_PICKED_COMMIT
stage 2 = blob at current HEAD
          role: CURRENT_HEAD
stage 3 = blob at CHERRY_PICK_HEAD
          role: CHERRY_PICKED_COMMIT
```

### 6.4 Missing stages

```text
stages 2+3 without stage 1 = add/add
stages 1+2 without stage 3 = modify/delete
stages 1+3 without stage 2 = delete/modify
different modes/types = file-mode-or-type
```

For every path, compare actual index blob OIDs with the normative Git object
OIDs. Any mismatch or unprovable origin:

```text
STOP_REASON=STAGE_ROLE_MATRIX_MISMATCH
```

## 7. Deterministic Git operation state machine

Recognize only:

```text
MERGE_ACTIVE
REBASE_MERGE_ACTIVE
REBASE_APPLY_ACTIVE
CHERRY_PICK_ACTIVE
```

Inspect exact Git-dir markers:

```text
MERGE_HEAD
CHERRY_PICK_HEAD
REBASE_HEAD
rebase-merge/**
rebase-apply/**
sequencer/**
```

A rebase backend may expose `CHERRY_PICK_HEAD`; treat it as rebase only when
rebase metadata exists and identities are consistent.

Zero, multiple, contradictory, stale, or incomplete states cause STOP.

### State fingerprint

Compute an immutable fingerprint over:

```text
repository identity
HEAD
ORIG_HEAD
operation heads
rebase backend
onto
head-name
stopped-sha
hashes of sequencer files
.git/index SHA-256
complete stage map: path/mode/stage/blob OID
staged name-status map
tracked porcelain state
SHA-256 of every tracked changed worktree path
complete untracked inventory with path/type/size/hash
```

Verify the fingerprint:

- before every edit;
- after every edit;
- before and after staging;
- before and after every check wave.

Unexplained drift:

```text
STOP_REASON=CONCURRENT_OR_EXTERNAL_GIT_STATE_DRIFT
```

## 8. Untracked contamination gate

Default policy: any untracked path is blocking.

An exception is allowed only when an exact path and SHA-256 were frozen in
PREVIEW with an evidence-backed inert classification. Directories, symlinks,
`.env`, Python modules, tests, manifests, lock collisions, generated files,
runtime config, and unknown paths are never inert by default.

The successful receipt must include the complete untracked inventory and the
exact allowlist. It must never claim only `UNRELATED_CHANGES=0`.

## 9. Secure recovery and restart

### 9.1 Durable external run state

Store under:

```text
Windows: %LOCALAPPDATA%\OPSX\resolve-conflict\<repo-id>\<run-id>\
POSIX:   $XDG_STATE_HOME/opsx/resolve-conflict/<repo-id>/<run-id>/
```

The runtime enforces current-user-only permissions. On Windows it must apply
and verify ACLs; failure disables GO.

### 9.2 Transactional worktree backup (git-dir only)

Do not copy conflict files, diffs, credentials, secrets, or blob contents to
the external run/state directory.

A short-lived plaintext original may exist only under
`.git/opsx-resolve-conflict/backups/` for the active write transaction. Write
proofs must report `plaintext_backup_persisted=true` with location
`git_dir_transactional`. The backup is deleted on terminal success or after
successful rollback restore. It must never be copied into OPSX state roots.

Persist externally only:

```text
object OIDs
path and mode metadata
state fingerprints
content SHA-256 values
scope manifest
unit receipts
test result hashes
ledger
```

Git object OIDs remain the recovery source for stages. A partially edited
worktree is resumed only when its full state fingerprint matches the last
receipt.

### 9.3 Durable manifest

Persist and fsync:

```text
RUN_ID
package version
repository identity
operation
initial fingerprint
last verified fingerprint
initial stage OIDs
frozen scope
unit states
edited paths
staged paths
test receipts
Owner-decision state
ledger hash
```

At startup, detect unfinished runs for the same repository and operation.

Resume only when:

- package version is compatible;
- repository identity matches;
- operation matches;
- current fingerprint equals the last verified fingerprint.

Otherwise STOP. Do not repeat an edit, stage action, or continuation already
recorded as complete.

## 10. OPSX authority resolution

### 10.1 Authority lanes

Classify each semantic unit:

```text
A: OpenSpec/product change
B: durable bug episode
C: OPSX/process surface
D: ordinary product history without discoverable OPSX binding
```

### 10.2 OpenSpec binding

When `change=<ID>` is supplied, resolve exact canonical paths and do not
rediscover it.

Use:

```text
openspec status --change "<ID>" --json [--store <id>]
openspec instructions apply --change "<ID>" --json [--store <id>]
```

Read exact `contextFiles` and `artifactPaths`.

Do not equate `active` with `authoritative`.

R12 GO requires exact `change=<ID>`; automatic active-change selection is not
allowed. Both conflicting commits must contain the exact
`OPSX-Change: <ID>` trailer. The committed
`openspec/changes/<ID>/conflict-authority.json` must bind the exact conflict
path set to explicit authority files, the autonomous strategy, and the fixed
precedence `accepted_decision → main_spec → active_change`. Missing or
ambiguous lineage/applicability is STOP.

R21: ``external_authority=none_applicable`` is never proven by path/stem
filename heuristics or by a declaration JSON authored by this command.
Completeness requires an external OPSX authority declaration whose issuer is
allowlisted by a producer contract outside this package
(``openspec/policies/CONFLICT_AUTHORITY_PRODUCER.md`` or equivalent). Absence
of that producer is ``BLOCKER_AUTHORITY_PRODUCER_MISSING`` →
``STOP_AUTHORITY_UNPROVEN``. Fixture-only declarations are test doubles, not
production proof. Packaged ``sandbox_runner.py`` remains ``BEST_EFFORT``;
missing OS-enforced runner is ``BLOCKER_OS_SANDBOX_RUNNER_MISSING`` →
``STOP_SANDBOX_UNAVAILABLE``. ``GO_CAPABILITY`` stays false until both blockers
close.


Per conflict, construct:

```text
accepted applicable architecture decisions
current main specs
approved target-side change artifacts
approved source-side artifacts linked to replayed/merged commits
archived change artifacts as historical intent evidence
durable bug authorization evidence
runtime/public contracts
Git history
```

Explicit accepted supersession beats recency and lifecycle labels.

### 10.3 Decision lookup

Order:

1. exact paths from context;
2. `openspec/decisions/index.md`;
3. at most three targeted lookups.

Passing tests do not override an accepted decision. Unresolved decision
placement or ownership is STOP.

### 10.4 Durable bug episodes

Bug-case artifacts are read-only. Extract exact route, RED evidence, Owner
production GO, and approved fix boundary. Do not classify, reroute, create
RED/GREEN, or close findings.

A conflict that changes the authorized fix semantics is STOP.

### 10.5 Process surfaces

These paths are process authority:

```text
.cursor/**
.agents/**
.github/prompts/**
.github/skills/**
.github/copilot-instructions.md
.github/git-commit-instructions.md
AGENTS.md
```

Any conflict affecting GO/NO_GO, ownership, status, disposition, producer /
consumer fields, handoff, archive, verify, commit authority, or pipeline
authority is HIGH and STOP unless one exact approved process packet determines
the only valid text.

A successful process-surface resolution requires independent
`/opsx-review-commands REGRESSION_REVIEW` afterwards. This command never
self-attests that review.

## 11. Full operation change graph and logical conflicts

Do not inventory only `git ls-files -u`.

Before editing, build two complete path/symbol sets.

### Merge

```text
base = merge-base(HEAD, MERGE_HEAD)
target delta = base..HEAD
source delta = base..MERGE_HEAD
```

### Rebase/cherry-pick

```text
source delta = parent(operation_head)..operation_head
target state = current HEAD relative to the replayed commit parent
```

Include:

- every source-side changed path;
- every target-side changed path;
- unmerged paths;
- paths Git merged automatically;
- renames, copies, deletions, type/mode changes;
- Python definitions, calls, imports, signatures;
- schemas, models, migrations, persistence boundaries;
- external write boundaries;
- tests and fixtures;
- process producer/consumer tokens.

R12 inventories this graph but does not autonomously write multi-file units.
GO is limited to exactly one unmerged Python path and stops before write when
the graph contains an auto-merged/renamed/related path outside that scope.
Multi-file atomic resolution remains an explicit declared limitation, not a
claimed capability.

Examples requiring a logical-conflict candidate:

- one side changes a return contract and the other changes a caller;
- model/schema and consumer change in separate files;
- a guard is removed by a clean merge;
- two write paths change the same invariant;
- one side renames a directory while the other adds or modifies files below
  the old path.

Every candidate receives the same authority, risk, scope, and test gates as a
textual conflict.

## 12. Conflict taxonomy and risk

Normative taxonomy includes:

```text
modify/modify
add/add
modify/delete
delete/modify
rename/rename
rename/delete
rename/add
rename/modify
directory-rename
directory/file
file/symlink
file-mode
submodule
binary
generated
lock
migration/schema
logical-without-markers
other
```

Use stage metadata plus `git diff --name-status -M`, mode metadata, and
source/target path identity. Do not infer directory rename merely from
add/delete text; group consistent file renames by old/new directory prefix.

Mandatory HIGH/STOP:

- add/add with two meaningful implementations;
- modify/delete or delete/modify;
- nontrivial rename/directory rename;
- symlink, mode, binary, submodule;
- migration/schema;
- lock/generated with unknown canonical regeneration;
- security, secrets, permissions, billing, payments, privacy;
- data loss, transaction, idempotency, concurrency, retry semantics;
- public API or external protocol ambiguity;
- product requirement or accepted-decision contradiction;
- process authority/gate/handoff conflict;
- more than one defensible result;
- insufficient critical test evidence.

## 13. Immutable scope manifest

Freeze before the first edit:

```text
path
conflict/logical-unit ID
reason
authority source and hash
allowed operation
expected semantic change
initial stage OIDs
initial worktree hash
required tests
```

Autonomous writes are limited to conflicted paths already in this manifest.

Do not modify:

- non-conflicted production callers;
- non-conflicted tests;
- specs, tasks, decisions, bug-case or process-policy artifacts;
- a newly discovered path.

If another path must change, STOP and request exactly one Owner decision.
This prevents hidden refactors and test adaptation during conflict resolution.

## 14. Atomic resolution loop

For each frozen unit:

1. verify package and current state fingerprint;
2. re-read exact stage blobs and object roles;
3. re-read exact authority sources;
4. re-evaluate logical-unit graph;
5. state required behavior from both sides;
6. prove supersession for any intentionally removed behavior;
7. classify risk and confidence;
8. in PREVIEW, report and stop before write;
9. in GO, submit complete UTF-8 content to `WRITE_SCOPED_FILE`;
10. verify only the authorized path changed;
11. parse/syntax check;
12. `git diff --check`;
13. run targeted tests;
14. run adjacent/feature tests required by the contract graph;
15. run relevant type/static checks;
16. compare result to stage 1/2/3, authority, and behavior inventory;
17. stage exact paths through `STAGE_EXACT_PATHS`;
18. inspect staged diff and state fingerprint;
19. append and fsync unit receipt;
20. continue to the next unit.

No staging rollback is attempted. Contamination produces STOP with the index
preserved for inspection.

## 15. Test policy

Read `.cursor/rules/testing-rules.mdc`.

Project checks are `poetry run ...` only.

Per unit, materialize:

```text
DIRECT_TESTS
ADJACENT_TESTS
FEATURE_TESTS
TYPE_CHECKS
EXTERNAL_BOUNDARY_CHECKS
OPSX_ACCEPTANCE_CHECKS
```

When applicable, test:

```text
happy path
recoverable failure
non-recoverable failure
idempotency
repeat/next tick
partial completion
forbidden side effects
allowed sibling behavior
observable user/runtime result
```

Reject evidence that:

- mocks the causal boundary;
- invents impossible state or phantom fields;
- mutates shared module dependencies around `await`;
- proves only final mock non-invocation;
- omits the paired positive case;
- would still pass if the intended guard were removed.

Tests run only in the validation snapshot. If faithful validation requires
the original `.git`, network, credentials, PG/CH live service, or production
access, STOP when that check is mandatory.

## 16. Current-step staging gate (no sequencer continue)

Before declaring `READY_FOR_OWNER_CONTINUE` prove:

```text
package compatibility PASS
ledger chain PASS
cancellation registry empty
state fingerprint expected
stage-role matrix PASS
untracked gate PASS
scope manifest runtime-bound to conflict inventory
git ls-files -u empty
markers absent in scoped text paths
only scoped verified paths staged
per-unit trusted checks PASS
required adjacent/feature tests PASS when runnable
required type/static checks PASS when runnable
logical conflict candidates resolved or STOPPED
OPSX acceptance satisfied
confidence HIGH
git --continue NOT executed
```

The Owner may then continue the active Git operation manually. This command
must not claim `STATUS=RESOLVED` for a history-advancing completion.

## 17. Final validation

Final mode is always FULL.

Read `.cursor/static-check/registry.yaml` for check composition, Wave A/B,
dependencies, `task_type`, and `pack` identity. Pack trees are hash-bound
OPSX contract identity only. Markdown, shell snippets, and agent instructions
inside packs are **not** executable authority and must never supply argv.

Exact argv / timeouts / success exit codes come from a closed package-owned
typed adapter table keyed by `(check_id, task_type, normalized pack path)`.
Synthetic `execution.json` descriptors are not required
(HISTORICAL_BASELINE_ALLOWLIST: pre-R28).

At the repository snapshot pinned for this package, the expected default
matrix is:

```text
Wave A:
  pyright-strict
  mypy
  pytest-unit
Wave B:
  pytest-full only after pytest-unit PASS
```

The current registry at execution time is authoritative for the sealed FULL
matrix. If a selected check lacks a closed typed adapter, GO stops with
`FULL_VALIDATION_ADAPTER_UNAVAILABLE`; no argument may remove a mandatory
check or inject caller argv.

Malformed YAML, unknown/duplicate checks, invalid dependencies, missing or
wrong `task_type`/`pack`, pack path escape/symlink, pack inventory drift
(missing/extra/changed files), or adapter key mismatch STOP before mutation.

Registry and every pack file must match the startup-frozen host-contract
hashes. The plan is compiled before worktree mutation and then executed from
immutable in-memory bytes through the digest-bound sandbox runner.

The command may return `STATUS=READY_FOR_OWNER_CONTINUE` only when the
selected and mandatory matrix for the staged scope passes. It must never claim
history-advancing `RESOLVED`, `/opsx-verify` GO, or archive readiness.

## 18. Mandatory STOP conditions

Stop when any applies:

1. package or compatibility mismatch;
2. runtime/ACL/cancellation or external sandbox capability missing;
3. ambiguous or inconsistent Git operation;
4. stage-role OID mismatch;
5. external state drift;
6. unknown or unapproved untracked path;
7. unfinished run cannot resume exactly;
8. authority missing, contradictory, or stale;
9. decision lookup unresolved;
10. HIGH-risk taxonomy;
11. logical conflict cannot be proven safe;
12. required behavior cannot be preserved or explicitly superseded;
13. frozen scope would expand;
14. non-conflicted test or production path must change;
15. mandatory test/check fails or cannot run faithfully;
16. validation environment, VPN, service, credential, or timeout blocks proof;
17. staged blob OID/mode differs from validated candidate, or completed
    worktree bytes drift;
18. process remains after cancellation/join;
19. commit intent/message becomes false;
20. confidence is not HIGH.

Ask exactly one concrete Owner decision.

## 19. Versioned receipts

Write receipts conforming to the packaged JSON Schemas.

Every unit receipt includes:

```text
run and step IDs
operation and all relevant commit OIDs
path
stage 1/2/3 OIDs and roles
authority path + SHA-256
scope item hash
before/after state fingerprints
before/after worktree hashes
diff SHA-256
behavior preservation/supersession evidence
exact test argv
exit codes
timeouts
stdout/stderr hashes
remaining risks
ledger record hash
```

The run receipt includes all unit receipt hashes and final Git-state evidence.
The ledger is sealed with terminal state `PREPARED`. Success exists only when
the atomic `<run-id>.terminal.json` bundle is durably published; standalone
ledger, manifest, or receipt caches are not success authority.

A reviewer without chat history must be able to reconstruct the operation from
the package, repository objects, and receipts.

## 20. PREVIEW output

PREVIEW returns an advisory report (`preview-report/v2`) plus Russian human
sections: Коротко / Факты / OURS / THEIRS / Контекст / Расхождение /
Интерпретации / Вопросы владельцу / Варианты / Рекомендация / Как проверить /
Ограничения. Machine JSON preserves `CONTEXT_EVIDENCE` with authority-classified
items and evidence IDs.

```text
STATUS=PREVIEW_READY
COMMAND=/opsx-resolve-conflict
PACKAGE_VERSION=0.39.0
SAFE_USAGE_SCOPE=PREVIEW_ONLY
GO_CAPABILITY=false
OPERATION=
PATH=
CONTEXT_EVIDENCE=
CONTRACT_SIGNAL=
OWNER_DECISION_REQUIRED=
RECOMMENDATION=null|<option_id with evidence_refs>
NEXT_ACTION=Owner verifies analysis, edits files manually, accepts responsibility
DO_NOT_DO_YET=edit-by-runtime, stage, continue, abort, skip, commit, push, GO
```

## 21. Success output

```text
STATUS=READY_FOR_OWNER_CONTINUE
COMMAND=/opsx-resolve-conflict
PACKAGE_VERSION=0.39.0
RUN_ID=
OPERATION=
START_HEAD=
FINAL_HEAD=
STATE_RECEIPT=
UNIT_RECEIPTS=
LEDGER_PATH=
LEDGER_FINAL_HASH=
TERMINAL_BUNDLE_PATH=
TERMINAL_BUNDLE_SHA256=
AUTHORITY_SOURCES=
STAGED_PATHS=
LOGICAL_CONFLICTS_FOUND=
LOGICAL_CONFLICTS_RESOLVED=
FINAL_CHECKS=
UNMERGED_ENTRIES=0
CONFLICT_MARKERS=0
GIT_CONTINUE=FORBIDDEN
RESOLVED_CLAIMED=NO
UNTRACKED_INVENTORY=
UNRELATED_TRACKED_CHANGES=0
FORBIDDEN_COMMANDS_EXECUTED=0
PUSH_PERFORMED=NO
BACKGROUND_PROCESSES=0
OPSX_VERIFY_CLAIMED=NO
ARCHIVE_READY_CLAIMED=NO
OWNER_ACTION_REQUIRED=YES
NEXT_ACTION=Owner reviews staged resolutions then continues Git operation manually
```

Next action after Owner continue (out of band):

- product/OpenSpec context: `/opsx-pipeline NAVIGATE <CHANGE_ID>`;
- process surface: `/opsx-review-commands REGRESSION_REVIEW`;
- no OPSX context: `none`.

## 22. Stop output

```text
STATUS=STOP_FOR_OWNER
COMMAND=/opsx-resolve-conflict
PACKAGE_VERSION=0.39.0
RUN_ID=
OPERATION=
CURRENT_HEAD=
CURRENT_OPERATION_HEAD=
STATE_FINGERPRINT=
STOP_REASON=
AFFECTED_UNITS=
COMPLETED_SAFE_WORK=
STAGED_PATHS=
UNSTAGED_PATHS=
UNMERGED_ENTRIES=
UNTRACKED_INVENTORY=
FAILED_OR_MISSING_GATES=
EVIDENCE_RECEIPTS=
LEDGER_FINAL_HASH=
BACKGROUND_PROCESSES=0
OWNER_DECISION_REQUIRED=<exactly one decision>
SAFE_NEXT_OPTIONS=<non-destructive only>
NEXT_ACTION=none
```

## 23. Final self-review

Before any final response:

- package compatibility was checked;
- all operations used typed runtime;
- no raw shell, subagent, worker, nested OPSX command, or direct edit tool ran;
- stage roles were verified by OID;
- full operation graph included auto-merged paths;
- untracked gate passed;
- durable resume state is exact;
- no plaintext conflict content was written to the external state root;
  git-dir transactional backups were released or rolled back;
- frozen scope never expanded;
- no staging rollback ran;
- mandatory FULL checks completed;
- ledger chain and cancellation barrier passed;
- no OPSX verify/archive claim was made;
- exactly one next action or one Owner decision is present.


### R26/R27 authority root and signed declarations (external; not MANIFEST)

Producer trust requires an independently authenticated channel:

- OS-pinned Ed25519 public key (not env-overridable; R30/R31 path protection):
  - Windows: `C:\ProgramData\OPSX\conflict-authority\ed25519.pub`
  - Unix: `/etc/opsx/conflict-authority/ed25519.pub`
  - component-by-component no-follow / no-reparse walk from filesystem root
  - installer-owned owner + POSIX mode / Windows DACL (agent must lack
    write/delete/DAC/owner rights on key and parents)
  - key bytes read from a stable OS handle held open through producer
    signature verification; identity rechecked before verify and close
  - `FILE_ATTRIBUTE_READONLY` / final-file mode alone is **not** a trust boundary
  - caller path, repo-relative fallback, and env override are forbidden
- `OPSX_CONFLICT_AUTHORITY_ROOT_PATH` — path to producer contract bytes
- `OPSX_CONFLICT_AUTHORITY_ROOT_SIGNATURE` — hex Ed25519 signature over those bytes
- optional `OPSX_CONFLICT_AUTHORITY_ROOT_DIGEST` — integrity check only (not authentication)

Authenticated producer contracts must bind each issuer as an object:

```text
{
  "id": "<issuer-id>",
  "key_id": "<key-id>",
  "public_key_ed25519": "<64-hex>",
  "roles": ["capability_attestor", ...]
}
```

Bare issuer ID strings are insufficient. Capability completeness may be
attested only by an issuer whose producer binding includes role
`capability_attestor`.

Authority declarations use schema
`opsx-resolve-conflict/authority-declaration/v5`:

- `payload` — canonical semantic fields (snapshot / OIDs / capabilities /
  `capability_evidence` / …)
- `issuer_key_id` — must match the producer binding for `payload.issuer.id`
- `signature` — Ed25519 over deterministic canonical JSON of `payload`

`capability_evidence` (schema `opsx-resolve-conflict/capability-evidence/v1`)
is mandatory in the signed payload. It must:

- be issued under a producer-authorized `capability_attestor`;
- bind the exact conflict snapshot + every path/stage/blob_oid row;
- set `analysis_complete=true` with empty `unknown_targets`;
- carry a unique sorted capability list identical to declaration
  `capabilities`.

Local AST symbol→`capability_bindings` mapping is diagnostic only and never
proves completeness or `none_applicable`. Missing/incomplete evidence →
typed STOP. Legacy v4 (and unsigned v3) declarations are rejected with no
silent compatibility path.

Canonicalization (stdlib only): UTF-8 JSON, `sort_keys=True`,
separators `(",", ":")`, `ensure_ascii=True`, exact payload field set.

Unsigned / legacy v3 flat declarations are rejected in strict/GO authority
flow (`legacy_unsigned_declaration_rejected`). Allowed issuer ID without a
valid signature is always STOP. Signature errors are typed
`StopRequired` with no issuer-ID fallback.

Ambient path+digest alone is **not** a trust root. `MANIFEST.json` /
`host_frozen_contracts` detect host drift only and **cannot** mint producer
trust. Without OS pubkey + valid signature: always
`STOP_AUTHORITY_UNPROVEN` / `BLOCKER_AUTHORITY_PRODUCER_MISSING`.

