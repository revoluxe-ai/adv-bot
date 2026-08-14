---

name: /opsx-verify
id: opsx-verify
category: Workflow
description: Phased read-only OpenSpec audit (mode=impl DoD | mode=archive pre-archive GO)
-----------------------------------------------------------------

Verify является read-only audit command после `/opsx-apply` и до `/opsx-archive`.

Никогда не меняй production code, planning artifacts, tasks, decisions или tests во время verify.

## Verify phase (mandatory — thin switch)

Перед аудитом прочитай и выполни
`.cursor/pipeline/contracts/VERIFY_PHASES.md`:

1. Parse `mode=impl` | `mode=archive` (default **`archive`** if omitted; WARN to prefer explicit mode).
2. If `mode=impl` → выполни только **PHASE_IMPL** из модуля; остановись; **не**
   эмитируй `✅ GO` / `❌ NO_GO`; не продолжай archive-секции ниже.
   Output shape + markers + **LOCAL_HOP_COPY_BLOCK** — из VERIFY_PHASES
   (bare `NEXT_ACTION` / `## Следующая команда` alone insufficient for
   Owner-local hop).
3. If `mode=archive` → выполни **PHASE_ARCHIVE** из модуля, затем полный
   archive-audit **этого** файла (секции ниже) + маркеры `✅ GO` / `❌ NO_GO`
   + **LOCAL_HOP_COPY_BLOCK** из VERIFY_PHASES.

Не путать с `/opsx-test … verify` (bug GREEN). `✅ IMPL_OK` **никогда** не
авторизует `/opsx-archive`.

### Destructive cache soft gate (`mode=archive` only)

Contract:
`.cursor/static-check/contracts/destructive-selective-cache.md`.

During PHASE_ARCHIVE / archive-audit, if chat or last `/opsx-static-check`
FULL report shows `CACHE_MODE=dev`, `DESTRUCTIVE_CACHED>0`, or lacks an
explicit `CACHE_OFF` / `CACHE_FORCE` receipt for the pre-archive FULL:

1. Emit **WARN** (soft — not automatic `NO_GO` by itself):
   `DESTRUCTIVE_CACHE_DEV_BEFORE_ARCHIVE`.
2. Paste next confidence step:
   `/opsx-static-check FULL CACHE_OFF`
   (or `CACHE_FORCE`).
3. Continue archive audit; Owner may still reach `✅ GO`, but the WARN MUST
   appear in the verify report under readiness / caveats.
4. `CACHE_HIT` / skipped destructive ≠ EXECUTED green evidence for archive.

If last FULL was already `CACHE_OFF` / `CACHE_FORCE` / `CACHE_DEGRADED`
(run-all) → no WARN.

## Source resolution (mandatory)

Follow `.cursor/commands/opsx-source-resolution.md` and `.cursor/commands/opsx-execution-preflight.md`.

When a change name/id is known:

* read `openspec/changes/<change>/...` exact artifacts first via `openspec` CLI / canonical paths;
* read decision paths listed in change context/`artifactPaths` before any `openspec/decisions/**` glob;
* do not re-list the whole OpenSpec tree to rediscover the selected change;
* do not require `git status` before verify unless dirty-tree risk is REQUIRED_FOR the archive verdict;
* include `SOURCE_RESOLUTION` / `EXECUTION_PREFLIGHT` in the final verify output.

## Additive test-coverage assurance

Если в change artifacts, context files или явно переданном invariant output присутствует `TEST_COVERAGE_PACKET`, verify должен независимо проверить соответствие фактических tests этому packet.

`TEST_COVERAGE_PACKET` является дополнительным evidence contract.

Он не меняет:

* существующие inputs команды;
* выбор change;
* основной verdict contract;
* archive routing;
* eligibility verify;
* существующие archive blockers;
* legacy behavior для changes, созданных до появления packet;
* существующие output sections;
* финальные маркеры `✅ GO` и `❌ NO_GO`.

Отсутствие `TEST_COVERAGE_PACKET` не даёт автоматический `NO_GO`.

Статус:

```text
provisional
not_materialized
not_applicable
```

сам по себе не даёт автоматический `NO_GO`.

Verify блокирует archive только при доказанном test-coverage mismatch, слабом тестовом evidence либо отсутствии обязательного behavioral scenario, которое следует из specification, invariant или materialized `TEST_COVERAGE_PACKET`.

## Scenario coverage report assurance

Authority:
`.cursor/pipeline/contracts/SCENARIO_TEST_COVERAGE.md`.
Taxonomy:
`.cursor/pipeline/contracts/TEST_EVIDENCE_TAXONOMY.md`.

`SCENARIO_TEST_COVERAGE_REPORT` — change-wide independent evidence:

- каждый exact Spec Scenario имеет строку;
- `scenario_seam` проходит causal production logic;
- использованные stubs имеют executable contract parity;
- требуемые provider integrations выполнены;
- `PROVIDER_EXECUTION_RECEIPT` свежи по hashes.

Verify не пересчитывает всю матрицу и не становится scenario coverage
planner. Он проверяет identity/freshness, spot-checks acceptance-relevant rows
и применяет activation:

```text
PRODUCT_ACCEPTANCE_REQUIRED=true
→ LIFECYCLE_COVERAGE requires durable Derived Lifecycle
  (LIFECYCLE_STATUS: DERIVED; prefer design.md) from reviewed Owner Contract
  OR legacy OWNER_LIFECYCLE_ECHO + CONFIRM_LIFECYCLE when no reviewed
  owner-contract
→ AND fresh report VERDICT=PASS with rows mapped to lifecycle steps (mode=archive)
→ missing Derived Lifecycle (primary) / missing legacy echo+CONFIRM (legacy) /
  UNRESOLVED / unmapped / stale/FAIL/BLOCKED is archive blocker
→ do NOT fail solely for absent CONFIRM_LIFECYCLE when Derived Lifecycle is
  present under reviewed Owner Contract
→ scenario PASS alone does NOT clear LIFECYCLE without Derived Lifecycle
  (or legacy confirmed echo)
→ SCENARIO_COVERAGE_REQUIRED absent|false does NOT waive this

SCENARIO_COVERAGE_REQUIRED=true
→ fresh report VERDICT=PASS is required for mode=archive
→ missing/stale/FAIL/BLOCKED report is archive blocker

PRODUCT_ACCEPTANCE_REQUIRED=false|NOT_REQUIRED
AND SCENARIO_COVERAGE_REQUIRED absent|false
→ absence report is not automatic NO_GO (legacy compatibility only)
```

Kernel DONE contract:
`.cursor/pipeline/contracts/PRODUCT_ACCEPTANCE.md`. Soft tooling
PASS/waive never creates archive DONE without
`PRODUCT_ACCEPTANCE_STATUS=PASS` (or `NOT_REQUIRED`).

Provider receipt не равен final Scenario coverage PASS. Self-report writer-а
из `/opsx-test` или `/opsx-close-external-gap` не заменяет independent report.

## Additive external-call coverage assurance

Если в change artifacts, context files или явно переданном output присутствует
блок `EXTERNAL_CALL_COVERAGE_REPORT` (из `/opsx-external-call-coverage`),
verify должен независимо проверить, что перечисленные `GAPS` с
`MISSING_TEST` / `WEAK_EVIDENCE` / `UNTESTABLE_SEAM` закрыты актуальными
tests (или owner-deferral явно задокументирован вне archive path).
Включая PG session-mode WEAK: `PG_IMPLICIT_SESSION_MODE` (bare `sm()`) и
`PG_WRONG_SESSION_MODE` — SoT `.cursor/rules/testing-rules.mdc` § PG session
mode (явный `read_only=` обязателен).

`EXTERNAL_CALL_COVERAGE_REPORT` — additive evidence contract (sibling к
`TEST_COVERAGE_PACKET`, но diff/base-owned, не invariant-owned).

Он не меняет:

* legacy eligibility verify при absence report;
* основной verdict contract / archive routing markers;
* право verify не становиться general bug hunter / полным re-scan diff.

Отсутствие `EXTERNAL_CALL_COVERAGE_REPORT` не даёт автоматический `NO_GO`.
Наличие report со всё ещё открытыми FAIL-gaps → учитывай как test-coverage
/ weak-evidence blocker (как packet mismatch), со ссылкой на surface.

Verify не должен заново изобретать полный external-call inventory, если
report отсутствует; soft recommend владельцу:
`/opsx-external-call-coverage base=<BASE>` когда production `.py` в change
и report не передан.

Verify не должен превращаться в общий bug hunter.

Он проверяет, доказано ли тестами уже сформулированное требование или invariant.

## Additive performance review assurance

Если в change artifacts, context files или явно переданном output присутствует
блок `PERFORMANCE_REVIEW_REPORT` (из `/opsx-performance-review`), verify
должен независимо проверить, что открытые blocking findings
(`STATUS=FAIL` / незакрытый `DATA_GAP` с обязательным measurement) закрыты
актуальным независимым review `PASS` | `PASS_WITH_RISK` (или owner-deferral
явно вне archive path).

`PERFORMANCE_REVIEW_REPORT` — additive evidence contract (sibling к
`EXTERNAL_CALL_COVERAGE_REPORT`; diff/base-owned performance gate).

Он не меняет:

* legacy eligibility verify при absence report;
* основной verdict contract / archive routing markers;
* право verify не становиться general performance hunter / полным re-scan.

Отсутствие `PERFORMANCE_REVIEW_REPORT` не даёт автоматический `NO_GO`.
Наличие report со всё ещё открытыми FAIL / blocking DATA_GAP → archive
`NO_GO` со ссылкой на finding.

Verify не должен заново изобретать полный performance inventory, если
report отсутствует; soft recommend владельцу:
`/opsx-performance-review scope=base base=<BASE>` когда production hot-path
(DB/query/queue/concurrency/pool/retry) в change и report не передан.

## Additive linked bug-card audit (soft)

Authority: `.cursor/pipeline/contracts/bug-episode/CLOSE_POLICY.md`.

When the change is tied to a durable bug case (`case=` in request, design,
ROUTE_STATE, or tasks mention `BUGCASE-…`):

1. Read `.tmp/opsx-bug-cases/INDEX.md` and the case LEDGER/finding rows
   (bounded; do not invent IDs).
2. Soft-report `OPEN_LINKED_FINDINGS`, `CLOSE_FINDING_INTENT`,
   `POST_GREEN_OWNER`, whether GREEN exists, and pasteable handback if
   cards still open.
3. **Do not** write `closed_fixed` from verify.
4. **Default:** open cards are a **warn / soft recommend**, not automatic
   archive `NO_GO` (hard `archive_requires_bug_cards_settled` is out of
   scope for this increment).
5. Pasteable ALSO_OK examples:
   `/opsx-test case=… finding=… verify` or
   `/opsx-bug-team case=… mode=resume-family-fanout` or
   `/opsx-materialize-bug-queue mode=update … close=fixed` (solo only).
6. Soft recommend cross-case debt inventory (does not change GO/NO_GO alone):
   `/opsx-bug-debt-board case=<CASE_ID>` when a linked case is known, else
   `/opsx-bug-debt-board` when `.tmp/opsx-bug-cases/INDEX.md` exists.
   Surface CLOSED_WITH_RESIDUAL / OPEN_CANDIDATE / HARD_BLOCK_READY debt
   in the soft linked-cards section if the board would show rows.

Absence of a linked case → skip this section (still soft-recommend
`/opsx-bug-debt-board` when INDEX exists and change is bug-adjacent).

**Store selection:** Если пользователь называет store или работа находится в standalone OpenSpec store, сначала запусти `openspec store list --json`, выбери registered store id и передавай `--store <id>` в команды, которые читают specs/changes: `status`, `instructions`, `list`, `show`, `validate`, `archive`, `doctor`, `context`. Остальные команды не принимают этот флаг. Без store команды работают от ближайшего локального `openspec/` root.

**OpenSpec config contract:** перед чтением `openspec/config.yaml` запусти из repository root:

```bash
python openspec/tools/check_config_contract.py
```

Если команда возвращает non-zero, выведи unknown top-level keys / rules contract violations из output, не продолжай verify и ставь `NO_GO`.

**Обязательная настройка:** перед выводом результата прочитай:

* `openspec/config.yaml` для shared OpenSpec context и `rules.verify`;
* `openspec/policies/VERIFY_POLICY.md` для Verify command policy.

Примени `rules.verify` из config и `verify` policy из `VERIFY_POLICY.md`.

Если настройки отсутствуют или неполные, явно напиши это в разделе `Итоговый вердикт` и используй strict fallback:

* язык ответа: русский;
* единый verdict: `GO` или `NO_GO`;
* последняя строка: ровно `✅ GO` или `❌ NO_GO`;
* failed targeted tests, archive blockers, placement violations и task validation mismatch дают `NO_GO`.

**Input:** optionally specify a change name after `/opsx-verify` (example: `/opsx-verify add-auth`). Если имя не указано, infer только когда контекст однозначен; иначе запусти `openspec list --json` и попроси пользователя выбрать change.

## Steps

### 1. Select the change

Если change name указан, используй его. Иначе:

* infer from conversation context only when unambiguous;
* если ambiguous, запусти `openspec list --json` и попроси выбрать.

Всегда сообщи:

```text
Проверяю change: <name>
```

Для override:

```text
/opsx-verify <other>
```

### 2. Load verify settings

Сначала проверь contract `openspec/config.yaml`:

```bash
python openspec/tools/check_config_contract.py
```

Если contract check падает:

* зафиксируй unknown keys / rules contract violations;
* не продолжай verify;
* верни `NO_GO`.

Прочитай `openspec/config.yaml` как UTF-8.

Извлеки:

* `rules.verify`.

Прочитай `openspec/policies/VERIFY_POLICY.md` как UTF-8.

Извлеки:

* `verify.default_mode`;
* `verify.language`;
* `verify.final_marker`;
* `verify.verdict`;
* `verify.archive_blockers`;
* `verify.output`.

Используй эти настройки как source of truth для verdict и формата ответа.

### 3. Resolve change context

Run:

```bash
openspec status --change "<name>" --json
openspec instructions apply --change "<name>" --json
```

Parse:

* `schemaName`;
* `changeRoot`;
* `artifactPaths`;
* `actionContext`;
* `contextFiles`;
* tasks progress;
* task statuses.

Use concrete paths from:

```text
artifactPaths.<id>.existingOutputPaths
```

and:

```text
contextFiles
```

Do not assume artifact names beyond command output.

### 4. Read planning artifacts

Read:

* proposal;
* design;
* specs;
* tasks;
* optional decisions;
* any other existing artifacts reported by status/apply instructions.

Extract:

* required observable behavior;
* completed and remaining tasks;
* declared architecture decision references;
* ownership and placement claims;
* validation plan and targeted checks;
* open questions.

#### TEST_COVERAGE_PACKET discovery

Если среди прочитанных artifacts или context files найден блок `TEST_COVERAGE_PACKET`, извлеки:

* `TEST_COVERAGE_STATUS`;
* `SOURCE_REQUIREMENTS`;
* `INVARIANT`;
* `PRODUCTION_ENTRYPOINTS`;
* `ORCHESTRATION_SEAMS`;
* `PROTECTED_BOUNDARIES`;
* `REQUIRED_BEHAVIORAL_SCENARIOS`;
* `REQUIRED_ALLOWED_SIBLING_SCENARIOS`;
* `REQUIRED_RESIDUAL_OR_REPEATED_INVOCATION_SCENARIOS`;
* `REQUIRED_FAILURE_OR_EMPTY_STATE_SCENARIOS`;
* `REALITY_CONSTRAINTS`;
* `MOCKING_CONSTRAINTS`;
* `MINIMUM_TEST_LEVEL`;
* `UNIT_SUFFICIENCY`;
* `EXISTING_TESTS_TO_INSPECT`;
* `COVERAGE_GAPS`;
* `WEAK_TEST_PATTERNS`;
* `EVIDENCE_STATUS`;
* `MISSING_EVIDENCE`.

Не реконструируй packet по distant chat history.

Не объявляй packet существующим только потому, что change содержит tests или invariant.

Если packet отсутствует, зафиксируй:

```text
Test coverage packet: absent
Compatibility mode: legacy
```

и продолжай обычный verify.

Отсутствие packet не отменяет существующую обязанность verify сопоставить implementation и tests со specification.

#### SCENARIO_TEST_COVERAGE_REPORT discovery

Если report передан явно или найден по declared path, извлеки:

```text
SCHEMA_VERSION
CHANGE_ID
SOURCE_SPEC_SHA
WORKTREE_FINGERPRINT
ACTIVATION.SCENARIO_COVERAGE_REQUIRED
ACTIVATION.ACTIVATION_VERSION
VERDICT
SCENARIOS_TOTAL/PASS/FAIL/BLOCKED
ROWS
PROVIDER_RECEIPTS
ROUTE_PACKETS
```

Проверь:

- `CHANGE_ID` совпадает;
- `SOURCE_SPEC_SHA` соответствует текущим delta specs;
- worktree/test/contract/provider/schema hashes не stale;
- rows покрывают все exact Scenarios;
- receipts имеют `RESULT=PASS` и `SECRETS_REDACTED=YES`;
- report producer — независимый `/opsx-spec-scenario-coverage`.

Если report отсутствует:

```text
Scenario coverage report: absent
Scenario coverage required: true | false | not_declared
```

Не восстанавливай report из chat summary или похожих test names.

#### EXTERNAL_CALL_COVERAGE_REPORT discovery

Если среди прочитанных artifacts или context files найден блок
`EXTERNAL_CALL_COVERAGE_REPORT`, извлеки:

* `STATUS`;
* `BASE` / `HEAD` / `FOCUS`;
* `EXTERNAL_SURFACES`;
* `GAPS` (KIND / SYMBOL / DISPOSITION);
* `EVIDENCE_SUMMARY` если есть.

Не реконструируй полный diff-inventory заново, если report отсутствует.

Если report отсутствует, зафиксируй:

```text
External-call coverage report: absent
Compatibility mode: legacy
Soft recommend: /opsx-external-call-coverage base=<BASE> (when production .py changed)
```

и продолжай обычный verify (absence ≠ auto `NO_GO`).

Если report присутствует со STATUS=FAIL или незакрытыми GAPS — проверь,
закрыты ли они сейчас; открытые FAIL-gaps → archive `NO_GO` с точными
surface references.

#### PERFORMANCE_REVIEW_REPORT discovery

Если среди прочитанных artifacts или context files найден блок
`PERFORMANCE_REVIEW_REPORT`, извлеки:

* `STATUS`;
* `BASE` / `HEAD` / `FOCUS`;
* `FINDINGS_OPEN`;
* `EVIDENCE_SUMMARY`;
* `SERIALIZATION_CONTRACTS_NOTED` если есть.

Не реконструируй полный performance inventory заново, если report отсутствует.

Если report отсутствует, зафиксируй:

```text
Performance review report: absent
Compatibility mode: legacy
Soft recommend: /opsx-performance-review scope=base base=<BASE>
  (when DB/query/queue/concurrency/pool/retry hot-path changed)
```

и продолжай обычный verify (absence ≠ auto `NO_GO`).

Если report присутствует со STATUS=FAIL или blocking DATA_GAP /
незакрытыми FINDINGS_OPEN — проверь актуальность; открытые blockers →
archive `NO_GO` с точными finding references.

### 5. Architecture Decision Lookup

* Resolve decision paths from change context/`artifactPaths` / user-supplied paths first.
* Read `openspec/decisions/index.md` only if still needed to locate candidates.
* Further search under `openspec/decisions/` only for remaining gaps (budget ≤ 3 targeted lookups unless `EVIDENCE_GAP` is recorded). Never dump the full tree.
* If the ≤ 3 fallback budget is exhausted while ownership / layering / write-path / domain-invariant gaps remain unresolved (a relevant accepted decision may still be unread), record `EVIDENCE_GAP` and return `NO_GO`. Budget exhaustion is not proof that no decision exists; do **not** mark `Architecture Decision Missing`.
* Read proposed decisions from `contextFiles.decisions` or `artifactPaths.decisions.existingOutputPaths`, if any.
* Output relevant decisions by path and status in `Архитектурное размещение`.
* If the change touches ownership, layering, write paths, or domain invariants and lookup within budget (or after a recorded `EVIDENCE_GAP` expansion) concludes no relevant decision, mark `Architecture Decision Missing`.
* If proposed decisions exist, get:

```bash
openspec instructions decisions --change "<name>" --json
```

and apply `rules.decisions`.

Compare implementation placement against accepted/proposed decisions.

### 5a. Semantic write-target gate

Follow `.cursor/pipeline/contracts/SEMANTIC_WRITE_TARGET.md`.

* If the change is a high-risk multi-target write and artifacts do not durably
  resolve `TARGET_ENTITY_OR_LEG` / `ALLOWED_ADAPTERS` / `FORBIDDEN_ADAPTERS`
  (or status is `BLOCKED_NEEDS_OWNER_SEMANTIC_DECISION`) → archive blocker
  `unresolved_semantic_write_target` → overall `NO_GO`.
* If implementation uses a symbol in `FORBIDDEN_ADAPTERS` (or outside
  `ALLOWED_ADAPTERS`) → placement/behavior violation → `NO_GO`.
* When paired proof is required: verify the allowed target side effect **and**
  that the forbidden sibling target is not mutated. Green tests against an
  ambiguous or wrong-target plan do not clear this gate.
* Competing legs/adapters MUST NOT be closed with SEMANTIC `NOT_APPLICABLE`
  (Product Acceptance MEANING_LOCK anti-abuse).

Passing tests не являются proof, если placement нарушает accepted decision.

### 5b. Product Acceptance (kernel DONE)

Follow `.cursor/pipeline/contracts/PRODUCT_ACCEPTANCE.md` in `mode=archive`.

* Decide `PRODUCT_ACCEPTANCE_REQUIRED` (high-risk multi-leg, evolution-linked,
  material user-visible lifecycle write, or explicit flag).
* Emit `PRODUCT_ACCEPTANCE_STATUS` and, on failure,
  `PRODUCT_ACCEPTANCE_FAIL_PILLAR` (`MEANING_LOCK` | `LIFECYCLE_COVERAGE` |
  `SIDE_EFFECT_PROOF` | `MULTI`).
* When required: `PASS` only if MEANING_LOCK ∧ LIFECYCLE_COVERAGE ∧
  SIDE_EFFECT_PROOF. Else archive blocker `product_acceptance_not_pass` →
  overall `NO_GO`.
* LIFECYCLE_COVERAGE under PA requires durable Derived Lifecycle
  (`LIFECYCLE_STATUS: DERIVED`, prefer `design.md`) from reviewed Owner
  Contract — **or** legacy `OWNER_LIFECYCLE_ECHO` + Owner `CONFIRM_LIFECYCLE`
  when no reviewed owner-contract — **and** fresh scenario report
  `VERDICT=PASS` with acceptance rows mapped to lifecycle steps. Do **not**
  FAIL solely for absent `CONFIRM_LIFECYCLE` when Derived Lifecycle is
  present under reviewed Owner Contract. Scenario PASS alone with missing
  Derived Lifecycle (or legacy unconfirmed echo) ⇒
  `PRODUCT_ACCEPTANCE_STATUS=FAIL` pillar `LIFECYCLE_COVERAGE`. Soft waive
  cannot clear this.
* Soft sections (ECC / performance / antipattern / static / destructive-cache
  WARN / Owner soft-waive) MUST state they do **not** authorize archive
  without PA PASS / NOT_REQUIRED.
* Intent-only / OR-armed acceptance tests without this-run external effect →
  SIDE_EFFECT_PROOF fail (taxonomy `side_effect_proof`).

Passing tests также не доказывают автоматически:

* production wiring;
* full spec conformity;
* корректность source-of-truth ownership;
* покрытие residual state;
* отсутствие соседнего allowed behavior regression.

### 6. Verify implementation read-only

Inspect implemented code paths, local diff, and relevant tests without editing.

Check:

* behavior matches proposal/specs;
* tasks are accurately checked off;
* implementation layer matches cited architecture decisions;
* forbidden layers do not own logic reserved for another layer;
* tests prove behavior and do not hide placement violations;
* async tests do not manually mutate shared module-level dependencies around awaited code;
* tests do not stub the pipeline so the real guard is never exercised;
* write-gate regression tests prove the guarded entity is filtered before candidate/handler/write boundary, not only that a final mock was not called;
* regression tests fail if the intended guard is removed;
* gates with both blocked and allowed behavior have a paired positive case;
* archive blockers from `verify.archive_blockers`.

#### Additive packet-aware inspection

Если `TEST_COVERAGE_PACKET` присутствует, дополнительно проверь:

* каждый обязательный behavioral scenario сопоставлен хотя бы с одним фактическим test path или иным допустимым validation evidence;
* test воспроизводит правильный starting state и trigger;
* test проверяет observable allowed и forbidden result;
* production model, DTO, enum, callback payload и identity shape не заменены выдуманными synthetic fields;
* test не создаёт attribute, column или state combination, которых нет в production schema;
* source-of-truth invariant не доказывается fixture value из неправильного storage или ownership layer;
* causal boundary не замокана полностью;
* mocks расположены за проверяемой causal boundary либо сохраняют реальную input shape и orchestration path;
* runtime wiring не считается доказанным pure helper test;
* lifecycle и retry invariants имеют residual, repeated invocation или next-tick scenario, когда packet требует такой scenario;
* forbidden case имеет allowed sibling case, когда packet требует sibling coverage;
* pending, partial, retry, OFF, paid, valid-source или другой allowed sibling не был случайно заблокирован слишком широким guard;
* failure, empty, NULL, stale или missing-source scenario проверяется только когда он указан packet или прямо следует из invariant;
* пустая или degenerate collection, достигающая success, terminal, transition или write boundary, не трактуется как safe no-op без behavioral evidence;
* выбранный test level соответствует `MINIMUM_TEST_LEVEL`;
* unit test не объявлен достаточным, если `UNIT_SUFFICIENCY=insufficient`;
* похожее имя test не используется как доказательство покрытия без чтения setup, mocks и assertions;
* existing green tests не используются как доказательство полного production wiring;
* coverage gap классифицирован как confirmed только при наличии конкретного required scenario без достаточного evidence.

Для каждого required scenario зафиксируй внутреннюю traceability:

```text
source requirement / invariant
→ production entrypoint or orchestration seam
→ protected boundary
→ test file and test function
→ starting state
→ trigger
→ observable assertions
→ mocking boundary
→ coverage verdict
```

Разрешённые coverage verdict для отдельного scenario:

```text
covered
partially_covered
not_covered
not_applicable
unknown
```

`unknown` не превращай автоматически в `not_covered`.

При недостатке evidence укажи точный пробел.

### 6A. Verify additive test coverage contract

Этот step применяется только когда найден `TEST_COVERAGE_PACKET`.

#### A. Behavioral coverage

Для каждого `REQUIRED_BEHAVIORAL_SCENARIO` установи:

* `covered`;
* `partially_covered`;
* `not_covered`;
* `not_applicable`;
* `unknown`.

`covered` требует проверки:

* реального test setup;
* trigger;
* causal path;
* assertions;
* protected boundary;
* observable result.

Название test, комментарий или task checkbox не являются достаточным evidence.

#### B. Allowed sibling coverage

Если packet содержит `REQUIRED_ALLOWED_SIBLING_SCENARIOS`, проверь, что tests доказывают не только блокировку forbidden behavior, но и сохранение разрешённого sibling behavior.

Примеры:

* `complete` не повторяет sync, но `pending/partial` сохраняют retry;
* protected state блокирует mutation, но `OFF` сохраняет разрешённое поведение;
* free path блокирует paid automation, но paid path остаётся рабочим;
* missing source data блокирует переход, но valid source data проходит.

Отсутствие sibling test является blocker только когда:

* allowed sibling прямо материализован в specification, invariant или packet;
* guard может затронуть этот sibling;
* другого достаточного evidence нет.

#### C. Residual and repeated invocation coverage

Для lifecycle, scheduler, retry, idempotency и state-machine invariants проверь применимые scenarios:

* следующий tick;
* повторный callback;
* durable intermediate state;
* partial completion;
* skipped activation или finalization;
* crash/restart window;
* repeated processing одного generation или event;
* retry after persisted status;
* terminal status with incomplete secondary transition.

Не требуй все варианты автоматически.

Проверяй только применимые варианты из packet, specification и invariant.

Happy-path test первого invocation не доказывает корректность residual state на следующем invocation.

#### D. Reality constraints

Проверь, что test:

* использует реальные model/DTO fields;
* использует реальные enum values;
* сохраняет production data types;
* не создаёт phantom attributes;
* получает identity из фактического owner object;
* не подменяет live read model durable field;
* строит runtime-reachable state combination;
* использует реальную форму callback payload;
* не передаёт напрямую значение, которое должна вычислить проверяемая production boundary.

Нарушение reality constraint означает, что test не доказывает заявленный scenario.

#### E. Mocking constraints

Проверь, что causal boundary не скрыта mock-ом.

Допустимо замокать external destructive dependency, если test:

* проходит через реальную orchestration seam;
* сохраняет production input shape;
* проверяет правильное достижение или недостижение protected boundary;
* проверяет observable result.

Недостаточно:

* напрямую вызвать helper ниже causal gate;
* замокать manager, который должен выполнять routing;
* заранее передать результат, который должна вычислять проверяемая boundary;
* создать fake object с удобными полями, отсутствующими в production model;
* замокать source-of-truth loader, если invariant касается именно выбора source of truth;
* замокать state transition, если invariant касается именно перехода.

#### F. Minimum test level

Сравни фактический test level с `MINIMUM_TEST_LEVEL`.

Допустимые уровни:

```text
unit_component
orchestration_seam
runtime_entrypoint
boundary_adapter
integration
manual_only
unknown
```

Не требуй full E2E автоматически.

Применяй минимальный достаточный уровень, который способен доказать:

* observable behavior;
* production wiring;
* causal path;
* protected boundary;
* required sibling behavior.

Если packet требует `runtime_entrypoint`, pure helper unit test недостаточен.

Если packet допускает `orchestration_seam`, не блокируй archive только из-за отсутствия full integration test.

Если packet требует несколько уровней, объясни роль каждого уровня.

#### G. Unit sufficiency

Если `UNIT_SUFFICIENCY=sufficient`, проверь, выполнены ли условия sufficiency.

Если `UNIT_SUFFICIENCY=conditionally_sufficient`, проверь указанные условия.

Если `UNIT_SUFFICIENCY=insufficient`, unit-component test сам по себе не может закрыть required scenario.

Unit test может считаться достаточным на orchestration seam, если:

* seam реально используется production path;
* production state воспроизводится без synthetic fields;
* causal boundary не замокана;
* external destructive dependency замокана после causal boundary;
* observable allowed и forbidden results проверяются.

#### H. Packet compatibility

Не блокируй archive только потому, что:

* packet отсутствует;
* packet имеет `provisional`;
* packet имеет `not_materialized`;
* packet имеет `not_applicable`;
* `EXISTING_TESTS_TO_INSPECT` неполон;
* packet содержит `MISSING_EVIDENCE`;
* legacy change не формировал packet;
* отсутствует full E2E при достаточной lower-level seam.

Блокируй только подтверждённый coverage defect относительно materialized requirement, invariant или scenario.

### 7. Run relevant checks

Run targeted tests or validation commands appropriate for the changed files and validation plan.

At minimum, run OpenSpec validation for the change when available:

```bash
openspec validate "<name>" --type change --strict --json
```

If a check cannot run:

* report it explicitly;
* state the exact command that could not run;
* state why;
* decide verdict using strict mode.

If a task is `[x]` but its validation/test/check fails, write:

```text
Task completion mismatch: yes
```

#### Packet-aware targeted checks

Если `TEST_COVERAGE_PACKET` присутствует:

* запусти targeted tests, сопоставленные required scenarios;
* по возможности запускай минимальный набор, покрывающий packet;
* не запускай весь repository suite без необходимости;
* если packet требует repeated invocation, проверь test, который действительно вызывает production seam повторно;
* если packet требует runtime wiring, не заменяй его pure helper test;
* если packet требует allowed sibling, запусти blocked и allowed cases вместе;
* если test не может быть запущен, укажи exact command и причину;
* не создавай новый test во время verify;
* не исправляй существующий test во время verify.

Не выполняй destructive mutation testing.

Guard-removal sensitivity может проверяться:

* read-only inspection;
* существующим dedicated test;
* безопасным targeted mechanism, если он уже существует в repository.

Не редактируй test для доказательства coverage.

### 8. Compute one overall verdict

Produce exactly one overall verdict:

```text
GO
```

or:

```text
NO_GO
```

The overall verdict MUST be `NO_GO` when any configured condition is true:

* targeted/focused test failed;
* task is checked `[x]` but validation/test/check failed;
* archive blocker exists;
* placement violation exists;
* unresolved `EVIDENCE_GAP` after Architecture Decision Lookup budget exhaust (do not collapse this into Missing);
* `Architecture Decision Missing` after conclusive in-budget lookup (or after a recorded `EVIDENCE_GAP` expansion);
* unresolved open question blocks archive;
* unresolved semantic write target (`unresolved_semantic_write_target`) blocks archive;
* implementation uses a forbidden sibling write adapter after a resolved semantic target;
* required paired positive/negative semantic-target proof is missing;
* stale reference model blocks archive;
* async test manually mutates module-level state around `await` with `module.attr = fake` and manual `try/finally` restore;
* test stubs the pipeline so the real guard is never exercised;
* write-gate regression only asserts `assert_not_called()` or `count == 0` without proving the guarded entity was filtered before candidate/handler/write boundary;
* regression test would still pass if the intended guard were removed;
* gate has both blocked and allowed behavior but lacks a paired positive case;
* materialized required behavioral scenario has no sufficient test or validation evidence;
* lifecycle/retry invariant requires residual or repeated-invocation coverage, but tests cover only the first happy-path invocation;
* required allowed sibling scenario is missing and the guard may be over-broad;
* test uses a synthetic model/DTO field or impossible state combination as the basis of claimed coverage;
* test replaces the invariant source of truth with a fixture value from the wrong storage or ownership layer;
* test fully mocks the causal boundary whose behavior it claims to prove;
* packet requires production wiring or runtime-entrypoint coverage, but only a pure helper/component test exists;
* actual test level is below the materialized `MINIMUM_TEST_LEVEL`;
* `UNIT_SUFFICIENCY=insufficient`, but only unit-component evidence is provided;
* packet and tests materially contradict each other.
* `SCENARIO_COVERAGE_REQUIRED=true`, но report missing/stale либо
  `VERDICT=FAIL|BLOCKED`;
* scenario report заявляет PASS, но Scenario rows/receipts/hashes неполны или
  относятся к другому snapshot.

Do not set `NO_GO` only because:

* `TEST_COVERAGE_PACKET` is absent;
* `TEST_COVERAGE_STATUS=provisional`;
* `TEST_COVERAGE_STATUS=not_materialized`;
* `TEST_COVERAGE_STATUS=not_applicable`;
* full E2E is absent when the minimum required seam is covered;
* test inventory is incomplete but no mandatory scenario gap is proven;
* a scenario verdict is `unknown` without evidence that it is actually missing.

Do not write a success claim that conflicts with the overall verdict.

`Archive ready: yes` is forbidden when:

* tests failed;
* placement violations exist;
* architecture blockers are unresolved;
* unresolved semantic write target remains;
* a confirmed mandatory test-coverage blocker exists.

## Output

Ответ должен быть на русском языке, кроме:

* paths;
* commands;
* file names;
* class/function names;
* OpenSpec keywords.

Use exactly these sections:

```text
## Итоговый вердикт
GO — archive можно продолжать.
```

or:

```text
## Итоговый вердикт
NO_GO — archive пока нельзя.
```

Then:

```text
## Поведение
Behavior matches spec: yes / no / partial

## Архитектурное размещение
Implementation matches architecture decisions: yes / no / partial
Placement violations: none / список нарушений

## Тесты
Targeted tests: passed / failed / not run
Failed tests: none / список
Test coverage packet: absent / ready / provisional / not_materialized / not_applicable
Compatibility mode: legacy / packet-aware
Scenario coverage report: absent / PASS / FAIL / BLOCKED / stale
Scenario coverage required: true / false / not_declared
Behavioral scenarios: covered / partial / not covered / unknown / not applicable
Allowed sibling scenarios: covered / partial / not covered / unknown / not applicable
Residual/repeated invocation: covered / partial / not covered / unknown / not applicable
Reality constraints: satisfied / violated / unknown / not applicable
Mocking constraints: satisfied / violated / unknown / not applicable
Minimum test level: satisfied / not satisfied / unknown / not applicable
Coverage gaps:
- none / exact gaps

## Согласованность tasks
Task completion mismatch: yes / no
Причина: ...

## Готовность к archive
Archive ready: yes / no
Blockers:
- ...

## Linked bug cards (soft)
- none | OPEN_LINKED_FINDINGS: …
- ALSO_OK handback/close pasteables if any:
- Soft debt board: /opsx-bug-debt-board [case=<CASE_ID>] (if INDEX/case present)

## Следующая команда
/opsx-archive <change-name>
```

or for `NO_GO`:

```text
## Следующая команда
/opsx-apply <change-name>
```

Other allowed next commands for blockers:

```text
/opsx-update <change-name>
manual fix
/opsx-bug-team case=<CASE_ID> mode=resume-family-fanout
/opsx-test case=<CASE_ID> finding=<FINDING_ID> verify
/opsx-bug-debt-board case=<CASE_ID>
```

### LOCAL_HOP_COPY_BLOCK (mandatory — mode=archive Output)

Authority: `.cursor/pipeline/contracts/VERIFY_PHASES.md`
(`LOCAL_HOP_COPY_BLOCK` after PHASE_ARCHIVE).

After `## Следующая команда` and **before** the final marker
(`✅ GO` / `❌ NO_GO`), when the next step is a local `/opsx-*` hop in this
Cursor workspace, emit exactly **one** fenced copy-paste prompt containing
workspace path, change name, `mode=archive` + marker, blockers (on `NO_GO`),
exact next Command, and applicable `DO_NOT_DO_YET` / `ALSO_OK`. Outside the
fence (except the required final marker): ≤1 status line. No Web four-block
(`Ссылка` / `Папка`) for this hop. Bare `## Следующая команда` alone is
**not** a sufficient Owner-local handoff. Final marker stays the last line.

(`mode=impl` uses the PHASE_IMPL Output + LOCAL_HOP_COPY_BLOCK from
VERIFY_PHASES only — do not emit archive GO/NO_GO sections.)

Не создавай новый top-level output section для test coverage.

Вся additive coverage-информация должна находиться внутри существующего раздела:

```text
## Тесты
```

Все подтверждённые coverage gaps должны также попасть в:

```text
## Готовность к archive
Blockers:
```

The final line must be exactly one configured marker and nothing after it:

```text
✅ GO
```

or:

```text
❌ NO_GO
```

## Guardrails

* Read-only only. Do not edit files.
* Do not offer to fix code with a follow-up question like `Want me to fix?`.
* Instead of offering a write action, state the next command: `/opsx-apply`, `/opsx-update`, or `manual fix`.
* Do not mark verification successful when placement violates an accepted decision.
* Do not treat passing tests as sufficient architecture proof.
* Do not treat green tests as proof when the semantic write target is unresolved
  or implementation hits a forbidden sibling adapter.
* Treat `unresolved_semantic_write_target` as a hard archive blocker.
* Treat `product_acceptance_not_pass` as a hard archive blocker when
  `PRODUCT_ACCEPTANCE_REQUIRED=true`. Soft tooling waive cannot clear PA.
* Do not invent a `/opsx-product-acceptance` command; verify owns archive DONE.
* Block async tests that manually mutate shared module-level dependencies around awaited code, especially shared executors, `run_tasks`, manager module functions, runtime services, WB write adapters, settings, and global flags.
* Block tests that stub the pipeline so the real guard is never exercised.
* Block write-gate tests that only assert `assert_not_called()` or `count == 0` without proving candidate/handler/write-boundary filtering.
* Block regression tests that would still pass if the intended guard were removed.
* Use exact file/function references for placement findings.
* Keep one overall verdict. No mixed top-level success plus archive `NO_GO`.
* Treat `TEST_COVERAGE_PACKET` as additive evidence only.
* Treat `EXTERNAL_CALL_COVERAGE_REPORT` as additive evidence only (diff/base-owned; not a substitute for packet).
* Treat `PERFORMANCE_REVIEW_REPORT` as additive evidence only (diff/base-owned; not a substitute for external-call or packet).
* Soft-audit linked bug cards when case-tied; do not close cards from verify; open cards ≠ default archive NO_GO.
* Do not change legacy verify eligibility when the packet, external-call report, or performance report is absent.
* Do not issue `NO_GO` from packet status alone.
* Do not invent a full external-call inventory during verify when the report is absent; soft-recommend `/opsx-external-call-coverage` instead.
* Do not invent a full performance inventory during verify when `PERFORMANCE_REVIEW_REPORT` is absent; soft-recommend `/opsx-performance-review` when hot-path applies.
* When the external-call report is present, do not ignore still-open `MISSING_TEST` / `WEAK_EVIDENCE` / `UNTESTABLE_SEAM` gaps (включая `PG_IMPLICIT_SESSION_MODE` / `PG_WRONG_SESSION_MODE`).
* When `PERFORMANCE_REVIEW_REPORT` is present, do not ignore still-open FAIL / blocking DATA_GAP findings; fixer self-report is not independent PASS.
* Do not infer coverage from test names, task checkboxes, or green suite status.
* Do not accept synthetic production fields, impossible states, or wrong-owner identity as realistic test setup.
* Do not accept a test that fully mocks the causal boundary it claims to verify.
* Do not require full E2E when an orchestration seam or runtime-entrypoint test is sufficient.
* For lifecycle, retry, scheduler, idempotency, and state-machine invariants, inspect residual and repeated invocation coverage when required by packet, specification, or invariant.
* Do not require every failure mode mechanically; require only invariant-relevant cases.
* Preserve one overall verdict and the existing final marker.
* Do not turn verify into a general repository review or random bug hunt.
* Do not modify `TEST_COVERAGE_PACKET`, `EXTERNAL_CALL_COVERAGE_REPORT`, or `PERFORMANCE_REVIEW_REPORT` during verify.
* Do not silently promote a provisional scenario to a mandatory blocker without specification or invariant evidence.
* Do not treat an `unknown` scenario as automatically `not_covered`.
* Do not treat absence of packet as proof that coverage is sufficient.
* Do not treat presence of packet as proof that its scenarios are implemented.
* Do not treat absence of `EXTERNAL_CALL_COVERAGE_REPORT` as proof that external surfaces are covered.
* Do not treat presence of the report as proof that its gaps are closed.
* Do not treat absence of `PERFORMANCE_REVIEW_REPORT` as proof that performance is adequate.
* Do not treat presence of the performance report as proof that its findings are closed.
