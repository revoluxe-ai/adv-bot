# Semantic Write Target / Owner Knowledge Gap

## Purpose

Этот контракт запрещает OPSX угадывать material product semantics, когда
high-risk write может быть направлен в несколько разных runtime-сущностей,
ног или adapters.

Контракт не является отдельной пользовательской командой. Его вызывают как
preflight planning, implementation, verify, archive и supervisor surfaces.

## Applicability

Gate применяется только когда одновременно выполняются условия:

1. планируется external/destructive mutation;
2. зона high-risk (WB API, campaign lifecycle, billing, DB mutation или
   эквивалентный materially consequential write);
3. repository evidence показывает не менее двух правдоподобных concrete
   targets/entities/legs/adapters;
4. выбор materially меняет traffic, money, state или ownership.

Read-only работа, единственный доказанный target и несколько read adapters
дают `NOT_APPLICABLE` или `RESOLVED`, не вопрос Owner.

## Evidence order

До обращения к Owner выполни bounded evidence pass:

1. точная формулировка Owner;
2. change artifacts;
3. accepted/proposed decisions;
4. минимальная проверка runtime model и competing adapters.

Naming similarity, agent preference и passing tests против
недоопределённого spec не являются proof.

## Result contract

```text
SEMANTIC_WRITE_TARGET_STATUS:
  NOT_APPLICABLE
  RESOLVED
  BLOCKED_NEEDS_OWNER_SEMANTIC_DECISION
```

`RESOLVED` требует durable evidence:

```text
BUSINESS_TERM:
TARGET_ENTITY_OR_LEG:
ALLOWED_ADAPTERS:
FORBIDDEN_ADAPTERS:
TARGET_EVIDENCE:
OWNER_DECISION_SOURCE:
REQUIRED_PAIRED_TESTS:
```

Owner answer только в chat не является durable evidence. Planning writer
должен сохранить выбор в spec/design/decision/tasks до production apply.

## Owner question

При `BLOCKED_NEEDS_OWNER_SEMANTIC_DECISION` верни один конкретный вопрос:

```text
STATUS: BLOCKED_NEEDS_OWNER_SEMANTIC_DECISION
BUSINESS_TERM:
RUNTIME_CANDIDATES:
TARGET_EVIDENCE:
QUESTION:
OPTIONS:
RECOMMENDATION:
CONSEQUENCES:
NEXT_ACTION: /opsx-update <change>
```

Запрещено выбирать default, скрывать competing target или продолжать write.

## Stage behavior

### Planning (`/opsx-ff`, `/opsx-update`)

- materialize все `RESOLVED` fields в artifacts;
- при blocker спросить Owner и не объявлять apply-ready;
- после ответа сохранить allowed и forbidden adapters и paired tests.

### Apply

- повторно проверить target после context/decision read и до production edit;
- planned symbol должен входить в `ALLOWED_ADAPTERS`;
- любой `FORBIDDEN_ADAPTERS` symbol в planned write path даёт `NO_GO`;
- unresolved/chat-only answer маршрутизируется в planning writer.

### Verify

- unresolved target является archive blocker;
- проверь allowed side effect и forbidden sibling non-effect;
- green tests не закрывают ambiguity автоматически.

### Archive

- unresolved target запрещает sync, decision promotion и archive move;
- это hard stop, не overridable warning.

## Supervisor propagation

Если child возвращает `BLOCKED_NEEDS_OWNER_SEMANTIC_DECISION`:

```text
SUPERVISOR_STATUS: BLOCKED_OWNER_DECISION
DOWNSTREAM_DISPATCH: FORBIDDEN
QUESTION_PROPAGATION: VERBATIM_REQUIRED
GENERIC_SUMMARY_ONLY: FORBIDDEN
ALTERNATE_WORKER_GUESS: FORBIDDEN
ONE_NEXT_ACTION: OWNER_DECISION_REQUIRED
```

Supervisor обязан донести Owner поля `BUSINESS_TERM`,
`RUNTIME_CANDIDATES`, `TARGET_EVIDENCE`, `QUESTION`, `OPTIONS`,
`RECOMMENDATION`, `CONSEQUENCES`. Он не может продолжить apply из chat-only
ответа: сначала dispatch planning writer для durable materialization.

Независимые read-only DAG tasks могут завершиться, но mission не становится
successful, а зависимые write/verify/archive tasks остаются blocked.

## Required regression matrix

1. ambiguous destructive multi-target → blocker;
2. explicit single/`BOTH` target → resolved;
3. read-only or single-target → no Owner question;
4. forbidden adapter used after resolution → apply/verify `NO_GO`;
5. allowed target lacks forbidden-sibling proof → verify `NO_GO` when paired
   proof required;
6. chat-only resolution → route to planning, not apply;
7. unresolved target → archive hard stop;
8. supervisor propagates the exact Owner question and stops downstream.
