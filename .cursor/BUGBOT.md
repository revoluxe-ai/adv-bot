# WB Sky / OPSX Bugbot Review Rules

## Purpose

These rules are **additive project context** for Cursor Bugbot.

They MUST NOT replace, narrow, or disable Bugbot's normal review behavior.
Bugbot should continue reviewing the complete changed diff for its normal bug
classes, including logic errors, regressions, edge cases, error handling,
security issues, concurrency/state bugs, performance problems, data-loss risks,
test defects, configuration mistakes, and other concrete correctness problems.

OPSX/OpenSpec adds extra review context and additional defect classes. It is
not a substitute for normal code review.

## 1. Preserve native Bugbot coverage

- Review all changed file types that can affect repository behavior, not only
  production code.
- In particular, do not skip bugs in:
  - `app/**` and other runtime Python;
  - `tests/**`;
  - SQL and migrations;
  - configuration and deployment files;
  - `.cursor/commands/**`;
  - `.cursor/skills/**`;
  - `.cursor/rules/**`;
  - `.cursor/pipeline/**`;
  - `.cursor/static-check/**` and `.cursor/antipattern-gate/**`;
  - `.opsx/**`;
  - `openspec/**`;
  - `.github/prompts/**` and GitHub workflow/instruction surfaces;
  - documentation when the text itself is an executable workflow, contract,
    runbook, machine token definition, or source of runtime/operator behavior.
- A valid ordinary Bugbot finding must not be suppressed merely because it is
  unrelated to OPSX.
- Do not review only against the rules below. Use normal repository reasoning
  as well.
- Do not turn the review into a style/lint checklist. Prefer defects with a
  concrete failure condition and operational impact.

## 2. Repository/product invariants

Treat the following areas as high-risk when changed or affected transitively:

- bids and bidder behavior;
- CPO/CPA logic;
- V3/V2 updater logic;
- `ApplyManager` and equivalent write orchestration;
- campaign lifecycle;
- automatic campaign start/stop;
- WB API write actions;
- PostgreSQL/SQLAlchemy, Redis, ClickHouse, Neo4j persistence/state;
- DB migrations;
- Free/Paid access boundary;
- billing/payment state;
- keyword activity and traffic-shaping state;
- overspend/underspend controls;
- behavior that must remain correct for thousands or tens of thousands of
  campaigns/entities.

For Free/Paid behavior:

- Free mode must not silently expose paid automation core.
- WB-impacting automatic write actions must remain disabled in Free unless a
  durable product specification explicitly authorizes them.
- A manual self-service write in Free is not equivalent to automation. Where
  such a write is intentionally allowed, preserve the required preview,
  affected-record visibility, and explicit user confirmation semantics.
- Do not infer future product vision as current behavior. New production
  behavior needs an applicable OpenSpec change/specification.

## 3. OpenSpec / architecture context

When a changed implementation is governed by OpenSpec artifacts, use those
artifacts as correctness context when relevant and available.

Important distinctions:

- `spec` describes observable product behavior;
- `design` describes change-specific implementation architecture;
- `tasks` describes implementation work and required validation;
- `openspec/decisions/**` is the durable architecture decision registry for
  reusable ownership, layering, write-path placement, and domain invariants;
- a change-local proposed decision is not the same authority as an accepted
  durable decision;
- passing tests do not make code correct if its placement/write ownership
  contradicts an applicable accepted architecture decision.

Report a defect when the changed code clearly violates an applicable durable
invariant or specification. Do not invent an architecture requirement solely
from the absence of a decision or from ambiguous context.

## 4. Treat OPSX commands and process files as executable contracts

OPSX command/skill/pipeline text is behavior, not merely documentation.
Review it for real execution defects with the same seriousness as code.

Continue normal Bugbot review of each changed command or contract by itself,
and additionally inspect cross-file interactions when the changed behavior
produces or consumes state.

Look for, among other things:

- contradictory mandatory instructions;
- a required action that violates the command's own hard ban/read-only boundary;
- unauthorized widening of write authority;
- Owner authority being assumed, fabricated, inherited, or broadened;
- a `GO` authorizing more than the contract says it authorizes;
- a read-only/reviewer command that can mutate code, tasks, lifecycle state,
  git state, registry state, production state, or external systems;
- fail-open behavior where missing evidence/capability/identity should stop;
- impossible or unreachable gate branches;
- status values that can fall through without a defined transition;
- retry/resume/recursion loops with no valid termination path;
- next commands that cannot accept the emitted state;
- a producer emitting a token/value that its consumer does not accept;
- a consumer requiring state that no valid producer creates;
- loss or substitution of stable identity (`change`, case, finding, task,
  owner, claim, artifact path, branch/workspace identity, etc.);
- stale-context use after a state-changing hop;
- a second competing source of truth for lifecycle, routing, ownership,
  status, or write authority;
- machine-readable token drift hidden by equivalent-looking prose;
- prose prohibition without an enforcing gate/blocker;
- a blocker/gate table whose cells do not cover states the producer can emit;
- mismatch between command, skill, prompt mirror, pipeline contract, or
  consumer when they are intended to encode the same machine semantics;
- unsafe default/fallback behavior that turns ambiguity into mutation;
- unbounded repository discovery/full scans where the contract requires
  bounded/context-first resolution and the broad scan can cause hangs,
  ambiguity, or wrong-target selection.

Do not stop searching ordinary bugs in process files merely because one of the
OPSX-specific patterns above applies.

## 5. Producer -> consumer review is evidence-based

For stateful handoffs, reason about the producer and consumer as a pair.

Examples of machine-significant handoff state include:

- `GO` / `NO_GO` and Owner approval scope;
- `STATUS` / disposition values;
- `CHAT_REQUIRED`;
- `CLAIM_TOKEN` and durable ownership proof;
- blocker/reason tokens;
- `NEXT_COMMAND` and its required arguments;
- change/case/finding/task identifiers;
- durable artifact paths and existence/readiness markers;
- archive/verification/product-acceptance status.

When claiming a producer-consumer contradiction, establish the actual values
or conditions on both sides whenever the repository context makes both sides
available. Do not convert a one-sided suspicion into a high-confidence finding
without evidence that the other side is incompatible.

Exact state-machine cells matter. Similar prose is not sufficient if routing
uses exact tokens or predicates.

### Bug-episode claim invariants

When the bug-episode workflow is affected, preserve these exact semantics:

- a pre-claim working item is claimable only for the contract-defined
  claimable cell; in the current OPSX model this is
  `STATUS=available` AND `CHAT_REQUIRED=true`;
- pre-claim flow must route through the claim operation; it must not invent a
  `CLAIM_TOKEN` or pretend that an unclaimed item can directly satisfy a
  post-claim ownership gate;
- once `STATUS=claimed`, durable non-empty ownership proof is required;
  missing/empty durable claim proof must fail closed rather than weaken
  ownership;
- backlog, blocked, absorbed, closed, duplicate/promoted, or other
  non-claimable states must not accidentally fall into a claim/fix path merely
  because `CHAT_REQUIRED` or another field is present;
- producer eligibility, consumer blockers, prohibitions, acceptance text, and
  next-command generation must describe the same state cells.

A mismatch that creates an impossible next step, ownership bypass, claim loop,
or silent fall-through is a correctness bug.

## 6. Authority and fail-closed semantics

OPSX intentionally separates authorities. Review changes for accidental
collapse of these boundaries.

- Chat text by itself is not durable lifecycle/write authority when the
  governing contract requires durable materialization.
- Owner approval is scoped. Do not treat one `GO` as blanket authorization for
  unrelated writes, fixes, commits, archive, deployment, or production access.
- A reviewer/auditor must not become implementation or closure authority merely
  because it detected a defect.
- A planning artifact must not silently become runtime truth when the contract
  assigns authority elsewhere.
- Missing required capability, evidence, exact identity, durable artifact, or
  unresolved semantic write target must not be converted into PASS by absence.
- If projectization/activation is a prerequisite and the authoritative state
  says it is incomplete/disabled, normal execution must fail closed rather
  than proceed using assumptions.
- Do not introduce a second status system, route authority, ownership registry,
  or lifecycle source of truth when one already exists.

Bugbot itself does **not** issue Owner approval, archive `GO`, close OPSX
changes/cases, or mutate tasks. It should report defects that would cause the
repository workflow to do those things incorrectly.

## 7. Semantic write-target defects

For high-risk writes, distinguish business intent from the concrete runtime
write target.

Report defects where a change can:

- choose among materially different write targets by default when the product
  semantics are unresolved;
- write through an adapter/path explicitly forbidden by the applicable
  durable decision/change contract;
- treat a chat-only answer as durable authorization when durable
  materialization is required;
- prove only the allowed side effect while failing to preserve a required
  forbidden sibling non-effect;
- allow a write path that bypasses the selected ownership/access guard;
- weaken a MUST/MUST NOT product boundary into optional behavior without
  durable authority.

Do not demand an Owner decision for a genuinely read-only or already
unambiguous single-target change merely because the general mechanism exists.

## 8. Test correctness rules that expose real bugs

Review tests as executable evidence, not as decorative coverage.

Flag concrete defects such as:

- a regression test that would still pass if the intended guard were removed;
- a write-gate test that proves only a final mock was not called while the
  forbidden entity can still reach candidate/handler/write-boundary logic;
- a test that fully mocks the causal boundary whose behavior it claims to
  prove;
- a pipeline test that stubs away the real guard/path under test;
- an async test manually mutating shared module-level dependencies around
  `await` with manual restore, creating race/leakage risk;
- impossible synthetic state/model fields used as the basis of claimed
  coverage;
- a PG/CH persistence behavior being declared proven solely through a mocked
  store when the change depends on real query/session semantics;
- changed/new production `sm(...)` / `get_async_session_maker(...)` usage that
  omits explicit `read_only=` intent;
- a signature/shared-behavior change whose real call sites now violate the new
  contract even though the newly added targeted test passes;
- tests/tasks marked complete while their mandatory targeted validation is
  known to fail.

Do not require a specific test level when repository evidence does not make
that level necessary. The goal is correctness, not maximizing test weight.

## 9. Freeze / hold / experiment invariants

When a change affects freeze/hold/experiment behavior, look beyond one helper
or one write function.

A correct implementation may need to preserve the complete mutable-state
boundary, including as applicable:

- whitelist/blacklist/minus phrases;
- keyword enabled/status state;
- target places;
- bids/budgets;
- setup/hold writes;
- DB/Redis coordination;
- external WB writes;
- manual/user/external drift;
- empty or degenerate captured sets.

Look for sibling writers that can still mutate supposedly frozen causal state,
incorrect restoration/source-of-truth semantics, first-run-only correctness,
or an empty captured set being treated as successful/ready when the governing
spec forbids that.

Do not assume a sibling gated path proves protection of another runtime-reachable
writer.

## 10. Data, external effects, and scale

For changed production logic, continue normal review for:

- transaction/session mistakes;
- duplicate or non-idempotent side effects;
- retries that repeat destructive WB/API/DB actions;
- partial failure that leaves DB/Redis/external state inconsistent;
- stale cache/state used as write authority;
- race conditions between workers/tasks;
- batch/loop/query behavior that is acceptable for tens of entities but breaks
  at thousands or tens of thousands;
- N+1 queries, unbounded materialization, unbounded task fanout, or memory
  amplification;
- incorrect handling of empty sets, missing cache data, partial API responses,
  and retry exhaustion;
- logging/exception handling that converts a required hard failure into silent
  success or vice versa.

## 11. Finding quality / false-positive control

A Bugbot finding should normally identify:

1. the changed location or changed contract that exposes the issue;
2. the concrete execution/state condition;
3. what the current code/contract does;
4. what invariant/consumer/runtime behavior it conflicts with;
5. the practical impact.

Prefer a smaller number of proven bugs over speculative process criticism.

Do not report as a bug merely because:

- wording differs but machine semantics are compatible;
- a preferred style/pattern was not used;
- an optional artifact is absent without evidence that it is required here;
- a change is unusual but consistent with its applicable spec/decision;
- an OPSX file is not shaped exactly like another command when their roles are
  different;
- the full repository was not refactored while the changed slice remains
  correct.

For contract/gate findings, distinguish:

- **confirmed incompatibility**: both relevant semantics are known and conflict;
- **risk/evidence gap**: context suggests a problem but the counterpart or
  authority is not established.

Do not present an evidence gap as a confirmed bug.

## 12. Review priority

When several issues exist, prioritize findings that can cause:

1. unauthorized or wrong-target external writes;
2. billing/financial errors or uncontrolled spend;
3. security/privacy/secrets exposure;
4. data loss/corruption or irreversible state drift;
5. incorrect campaign lifecycle/start/stop/bid behavior;
6. Free/Paid boundary bypass;
7. false `GO` / false archive readiness / ownership bypass;
8. command handoff loops, impossible next steps, or lost durable identity;
9. concurrency/retry/idempotency defects;
10. performance/scale failure in realistic WB Sky workloads;
11. misleading tests that allow the above defects to pass validation.

This priority list is not exhaustive and must not suppress other valid native
Bugbot findings.
