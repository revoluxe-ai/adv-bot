---
description: "Shared OPSX command-role ownership: plain text cannot transition roles or expand writes. Cite-only — not a standalone user command."
---

# OPSX Command Role Ownership Contract

Shared mandatory **role ownership** contract for all `/opsx-*` commands in one chat.

This file is **not** a user-facing `/opsx-*` workflow command.
Do **not** invoke it as `/opsx-command-role-ownership`.
Commands and always-applied rules that govern OPSX sessions MUST cite and follow it.

Companion contracts:

* `.cursor/commands/opsx-source-resolution.md` — artifact path resolution
* `.cursor/commands/opsx-execution-preflight.md` — execution cost / hang risk
* `.cursor/commands/opsx-human-label-display.md` — human Title (id) display

This contract covers **who may write what after a slash command**, not artifact
lookup budgets and not product ownership decisions.

## Problem solved

In a multi-command chat, a plain-text follow-up (e.g. «подключи», «сделай»,
«GO») must not silently leave the active command's write boundary and perform
another command's work. Same-chat full lifecycle is allowed; role leakage is not.

## Definitions

```text
ACTIVE_COMMAND = the most recent explicitly invoked /opsx-* command in this chat
ROLE           = that command's declared mode / write boundary
ALLOWED_WRITES = paths/surfaces that command may mutate under its own gates
```

Examples of explicit invocation (role transition allowed):

```text
/opsx-explore …
/opsx-apply <change>
/opsx-scripts TEST_LOCAL …
```

Not an invocation / not a role transition:

* ordinary chat messages without a leading `/opsx-*` command;
* acknowledgements («да», «ок», «продолжай», «сделай»);
* bare `GO` that does not satisfy the **active** command's own GO gate;
* a `GO` that belonged to a previous command in chat history.

## Hard rules (fail-closed)

1. **Role persistence.** After an explicit `/opsx-*` invocation, subsequent
   plain-text messages are handled **under that ACTIVE_COMMAND** until another
   explicit `/opsx-*` is invoked.
2. **No silent role expansion.** Plain text may clarify arguments for the
   ACTIVE_COMMAND. It MUST NOT expand `ALLOWED_WRITES`, switch to another
   command's authority, or authorize product/process edits owned elsewhere.
3. **Out-of-scope request → handoff only.** If the user asks for work outside
   the ACTIVE_COMMAND's contract (even urgently), the agent MUST:
   - refuse the out-of-scope mutation;
   - explain one line why (role boundary);
   - emit a pasteable next `/opsx-*` command that owns that work;
   - **not** perform that work in the same turn.
4. **GO is command-local.** A `GO` / authorize token authorizes only the
   ACTIVE_COMMAND's allowlisted mutate path for that invocation. Historical
   `GO` from earlier commands in the same chat is invalid for a different
   command. Acknowledgement alone is never GO.
5. **Durable state outside chat.** Lifecycle truth lives in OpenSpec artifacts,
   ledgers, and command receipts — not only in chat memory. Commands MUST
   re-read durable sources when deciding state; they MUST NOT invent missing
   tasks/decisions from conversation alone.
6. **Same chat is allowed.** One chat may run a full change lifecycle. Separate
   chats are optional recovery/isolation, not a required safety mechanism.
   Safety is role ownership + durable artifacts.

## Canonical refusal shape (when out of role)

```text
STATUS: ROLE_BOUNDARY_REFUSAL
ACTIVE_COMMAND: /opsx-<current>
REFUSED: <what was asked that exceeds this command>
WHY: command must not perform another command's work
NEXT_ACTION:
/opsx-<owner-command> <args>
```

Do **not** require a verbose `OPSX_CONTEXT` banner on every turn unless the
ACTIVE_COMMAND already mandates its own receipt. Visibility of the slash
command in the UI is enough for humans; agents still enforce this contract.

## Regression case (must stay closed)

```text
/opsx-explore
> Подключи sales к скрипту и сделай smoke

FORBIDDEN:
- edit scripts/** or app/**
- run implementation tests as if /opsx-apply
- treat the request as silent apply authorization

REQUIRED:
STATUS: ROLE_BOUNDARY_REFUSAL
NEXT_ACTION pasteable /opsx-new|/opsx-ff|/opsx-update (then /opsx-apply)
```

## Where product/process writes are owned (examples)

| Work | Owning command(s) |
|------|-------------------|
| Product/code implementation from change tasks | `/opsx-apply` |
| Planning artifact create/revise | `/opsx-new`, `/opsx-ff`, `/opsx-continue`, `/opsx-update` |
| Explore / analyze / consult thinking | `/opsx-explore`, analyze/consult siblings (READ_ONLY) |
| Script Job / ledger ops | `/opsx-scripts` (not product OpenSpec apply) |
| Process-contract defect edits | `/opsx-admin-command-fix-command-defects` (+ authorize token) |
| Verify / archive gates | `/opsx-verify`, `/opsx-archive` |

If a request is ambiguous between owners → ask once or emit `BLOCKED` with
candidate pasteable commands; never guess into writes.

## Self-check for command authors

When editing an `/opsx-*` contract, ensure:

- [ ] Write boundary / READ_ONLY is explicit
- [ ] Out-of-scope asks redirect with pasteable owner command
- [ ] GO gate names this command only
- [ ] Plain-text follow-ups cannot widen that gate
- [ ] This contract is cited where the command already cites shared OPSX contracts
  (or covered by the always-applied rule)
