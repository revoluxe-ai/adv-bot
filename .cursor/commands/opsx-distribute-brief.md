---
name: /opsx-distribute-brief
id: opsx-distribute-brief
category: Workflow
description: "Полное описание завершённой разработки для дистрибьюции / подготовки материалов для клиентов"
argument-hint: "[change=<id>|archive=<path>] [audience=cs_pack|client] [write=disk|chat]"
---

# /opsx-distribute-brief

Собрать **полное описание завершённой разработки** как вход для дальнейшей
дистрибьюции и подготовки материалов для клиентов.

Это локальная WB Sky OpenSpec-команда (не upstream OpenSpec).

**Язык для человека:** русский, коротко, без инженерного жаргона в
product-секциях.  
**Машинные токены** (`DISTRIBUTION_BRIEF_READY`, `DO_NOT_PROMISE`, статусы) —
оставлять как есть; рядом давать человеческое пояснение.

## Purpose

После engineering closeout дать оператору один стандартный пакет:

- что сделали для пользователя / клиента;
- зачем;
- как это выглядит снаружи;
- что **не** изменилось;
- чего **нельзя** обещать без evidence;
- ссылки на источники (change / archive / PR / commits).

Команда **не** закрывает change, **не** заменяет verify/archive/PR и
**не** публикует клиентский текст наружу — только готовит brief.

## When to use

- После `/opsx-archive`, когда нужны материалы для клиентов / CS / маркетинга.
- Когда change уже archived (или явно указан archive path), и нужен
  переиспользуемый brief.
- Когда owner просит «опиши завершённую разработку для дистрибьюции».

## When not to use

- Вместо `/opsx-verify` / `/opsx-archive` / `/opsx-create-pr` / `/opsx-commit`
- Для reviewer/Bugbot PR body → `/opsx-create-pr`
- Для internal archive summary → `/opsx-archive`
- Пока change не completed и нет достаточного evidence → сначала довести
  apply/verify/archive
- Process-contract / admin pipeline questions → `/opsx-admin-command-consult`
- Product bug / learn-from-bug → bug path

## Defaults (GO OPTION_A)

Если аргументы не заданы:

```text
audience=cs_pack
write=disk
```

- `cs_pack` — пакет для подготовки клиентских материалов (CS/маркетинг/owner),
  не финальный клиентский copy.
- `client` — более короткий non-technical вариант ближе к клиентскому тону.
- `write=disk` — сохранить brief на диск + показать в чате.
- `write=chat` — только чат, без файла.

## How to run

```text
/opsx-distribute-brief change=<CHANGE_ID>
/opsx-distribute-brief archive=<ARCHIVE_PATH>
/opsx-distribute-brief change=<CHANGE_ID> audience=client write=chat
```

Optional:

- `pr=<PR_URL_OR_NUMBER>` — взять PR body как дополнительный evidence
- `audience=cs_pack|client`
- `write=disk|chat`

## Authority boundary (mandatory)

This command:

- **owns** only the distribution brief (content + optional brief file);
- does **not** emit verify/archive `GO` / `NO_GO`;
- does **not** create commits, push, PRs, deploys, or archive moves;
- does **not** rewrite main specs, design, or tasks;
- does **not** invent product claims absent from evidence — put them under
  `DO_NOT_PROMISE` / `OWNER_DECISION_REQUIRED`;
- does **not** silently re-decide another command’s verdict.

Follow `.cursor/commands/opsx-source-resolution.md` and
`.cursor/commands/opsx-execution-preflight.md`.

## Entry / exit

```text
ENTRY_STATE: archived (preferred)
ALSO_OK: verify_pass → STATUS must be DRAFT_BRIEF (not READY)
EXIT_STATE: distribution_brief_ready | BLOCKED_NEEDS_EVIDENCE
```

Hard rules:

1. If change is **archived** → may emit `DISTRIBUTION_BRIEF_READY`.
2. If change is only `verify_pass` / still active → emit `DRAFT_BRIEF` and
   label every product claim as draft; recommend archive first for READY.
3. If change-id / archive path cannot be resolved → `BLOCKED_NEEDS_EVIDENCE`.

## Resolution order

1. Exact `archive=` path if provided → read that change root.
2. Exact `change=` id:
   - prefer `openspec/changes/archive/*-<change>/` (newest dated match);
   - else active `openspec/changes/<change>/` (DRAFT only).
3. If omitted, infer from conversation only when unambiguous; otherwise ask
   for `change=` or `archive=`.
4. Do **not** unbounded-search the repo for “what we shipped”.

Store selection: if user names an OpenSpec store, use
`openspec store list --json` and pass `--store <id>` on status/show commands.

## Evidence to read (bounded)

Minimum sufficient, in order:

1. `proposal.md` — intent / why
2. `design.md` — behavior boundaries (skip deep ADL dump)
3. `tasks.md` — what was marked done (summary only)
4. delta specs under `specs/` if present — user-visible requirements
5. optional: PR body (`pr=`) / recent commits for the change branch
6. optional: existing `DISTRIBUTION_BRIEF.md` — refresh, do not blindly copy
   unverified claims

Read I/O budget:

- Grep-first for user-facing / behavior tokens when files are large;
- parallel Read max **2**;
- large files: section Read ≤ 120 lines;
- do not dump entire `openspec/decisions/**`.

## Write boundary

When `write=disk` (default):

1. If archive root resolved:
   `openspec/changes/archive/<YYYY-MM-DD-change>/DISTRIBUTION_BRIEF.md`
2. Else (active/DRAFT):
   `.tmp/opsx-distribute/<CHANGE_ID>/DISTRIBUTION_BRIEF.md`

Create parent dirs if needed. Overwrite only the brief file. Never touch other
archive artifacts.

When `write=chat`: do not write files; still emit full packet in chat.

## Steps

1. **Resolve change root** (see Resolution order). Announce:
   `Using change: <id>` and `Mode: READY|DRAFT`.
2. **Collect evidence** from proposal/design/tasks/specs (+ optional PR/commits).
3. **Separate audiences**:
   - product/client sections = non-technical;
   - `SOURCE_EVIDENCE` may keep paths/IDs in English.
4. **Extract claims** only if evidenced. Anything desired but unproven →
   `DO_NOT_PROMISE`.
5. **Build brief** with required sections below.
6. **Persist** if `write=disk`.
7. **Return contract** with explicit `NEXT_ACTION` / `DO_NOT_DO_YET`.

## Required brief sections

```text
STATUS: DISTRIBUTION_BRIEF_READY | DRAFT_BRIEF | BLOCKED_NEEDS_EVIDENCE
CHANGE_ID:
ARCHIVE_PATH: <path|none>
AUDIENCE: cs_pack | client
WRITE: disk | chat
OUTPUT_PATH: <path|none>

## PRODUCT_SUMMARY
1–3 sentences: what the user/client gains.

## PROBLEM_BEFORE
What was wrong / missing / painful before (non-technical).

## WHAT_CLIENT_GETS_NOW
Bullet list of user-visible outcomes.

## HOW_IT_WORKS_FOR_USER
Short user-visible flow after the change.

## WHAT_DID_NOT_CHANGE
Invariants / unchanged behavior (do not invent; say "не зафиксировано в evidence"
if unknown).

## LIMITATIONS_AND_DO_NOT_PROMISE
- Explicit non-goals
- Claims not evidenced
- Rollout caveats that must not be oversold

## ROLLOUT_NOTES
Deploy/migration/user-action notes if evidenced; else `none evidenced`.

## SOURCE_EVIDENCE
- change-id / archive path
- proposal/design/tasks/specs refs
- optional PR / commits

## OWNER_DECISION_REQUIRED
YES/NO + what owner must still decide for external copy (tone, channel, claims).

## WHAT_HAPPENED
## WHY
## CURRENT_STATE
## NEXT_ACTION
## DO_NOT_DO_YET
```

For `audience=client`, keep the same sections but shorten
`SOURCE_EVIDENCE` and omit engineer-only detail from product sections.

## Failure behavior

```text
STATUS: BLOCKED_NEEDS_EVIDENCE
MISSING:
- <exact missing input or artifact>
NEXT_ACTION: <pasteable: provide change= / archive= / finish archive>
DO_NOT_DO_YET: invent features; publish client copy; archive/verify/PR
```

If proposal/design are missing and cannot be recovered from archive → block;
do not fabricate a marketing story from git diff alone unless owner explicitly
asks for `diff-only` draft (then force `DRAFT_BRIEF` + heavy
`DO_NOT_PROMISE`).

## Handoff contract (always)

```text
WHAT_HAPPENED: собрали distribution brief для <CHANGE_ID>
WHY: подготовка материалов для клиентов / дистрибьюции
CURRENT_STATE: distribution_brief_ready | draft | blocked
OWNER_DECISION_REQUIRED: <tone/channel/claims or none>
NEXT_ACTION: адаптировать brief в клиентский канал (вне OPSX)
DO_NOT_DO_YET: /opsx-verify|/opsx-archive|/opsx-create-pr как замена brief;
  не публиковать неподтверждённые обещания из DO_NOT_PROMISE
```

## Regression / anti-patterns

- Do not add client sections into `/opsx-create-pr`.
- Do not make brief a hard gate on `/opsx-archive`.
- Do not emit archive/verify verdicts.
- Do not commit/push the brief unless the owner separately runs a commit
  command and explicitly includes it.
- Do not treat PR body risks/Bugbot residual as client-facing promises.

## Guardrails

- Prefer archived change for `DISTRIBUTION_BRIEF_READY`.
- Label drafts clearly.
- Evidence over eloquence.
- One owner for brief content: this command; external publish remains human.
