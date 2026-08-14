---
name: openspec-verify-change
description: Read-only audit of an OpenSpec change before archive using openspec/config.yaml rules and VERIFY_POLICY.md settings.
allowed-tools: Bash(openspec:*), Bash(python openspec/tools/check_config_contract.py:*), Bash(poetry run pytest:*), Bash(git diff:*), Bash(rg:*)
license: MIT
compatibility: Requires openspec CLI.
metadata:
  author: openspec
  version: "1.1"
  generatedBy: "1.6.0"
---

Verify является read-only audit command после `/opsx-apply` и до `/opsx-archive`.
Никогда не меняй production code, planning artifacts, tasks, decisions или tests во время verify.

**Verify phases:** Read and follow
`.cursor/pipeline/contracts/VERIFY_PHASES.md` first (`mode=impl` | `mode=archive`,
default archive). `mode=impl` → PHASE_IMPL only (`✅ IMPL_OK` / `❌ IMPL_GAPS`);
never archive. `mode=archive` → PHASE_ARCHIVE + full `.cursor/commands/opsx-verify.md`
audit (`✅ GO` / `❌ NO_GO`). Not the same as `/opsx-test … verify`.
After either phase, when the next step is a local `/opsx-*` hop in this
workspace, emit **LOCAL_HOP_COPY_BLOCK** (one fenced Owner-local prompt) per
VERIFY_PHASES — bare `NEXT_ACTION` / `## Следующая команда` alone is
insufficient.

**Semantic write-target authority:** Read and follow
`.cursor/commands/opsx-verify.md`, `openspec/policies/VERIFY_POLICY.md`, and
`.cursor/pipeline/contracts/SEMANTIC_WRITE_TARGET.md`. Unresolved high-risk
multi-target writes are archive blocker `unresolved_semantic_write_target`
(`NO_GO`). Forbidden sibling adapters and missing paired positive/negative
proof also fail verify; green tests against an ambiguous target are insufficient.

**Product Acceptance (kernel DONE, `mode=archive`):** Follow
`.cursor/pipeline/contracts/PRODUCT_ACCEPTANCE.md` via `opsx-verify.md`.
When `PRODUCT_ACCEPTANCE_REQUIRED=true`, `LIFECYCLE_COVERAGE` needs durable
`OWNER_LIFECYCLE_ECHO` + Owner `CONFIRM_LIFECYCLE` **and** scenario
`VERDICT=PASS` with acceptance rows mapped 1:1 to echo steps. Scenario PASS
alone does not clear LIFECYCLE; soft tooling waive cannot clear PA. Details
remain in `.cursor/commands/opsx-verify.md`.

**Store selection:** Если пользователь называет store или работа находится в standalone OpenSpec store, сначала запусти `openspec store list --json`, выбери registered store id и передавай `--store <id>` в команды, которые читают specs/changes: `status`, `instructions`, `list`, `show`, `validate`, `archive`, `doctor`, `context`. Остальные команды не принимают этот флаг. Без store команды работают от ближайшего локального `openspec/` root.

**OpenSpec config contract:** перед чтением `openspec/config.yaml` запусти из repository root:
```bash
python openspec/tools/check_config_contract.py
```
Если команда возвращает non-zero, выведи unknown top-level keys / rules contract violations из output, не продолжай verify и ставь `NO_GO`.

**Обязательная настройка:** перед выводом результата прочитай:
- `openspec/config.yaml` для shared OpenSpec context и `rules.verify`
- `openspec/policies/VERIFY_POLICY.md` для Verify command policy

Примени `rules.verify` из config и `verify` policy из `VERIFY_POLICY.md`.

Если настройки отсутствуют или неполные, явно напиши это в разделе `Итоговый вердикт` и используй strict fallback:
- язык ответа: русский
- единый verdict: `GO` или `NO_GO`
- последняя строка: ровно `✅ GO` или `❌ NO_GO`
- failed targeted tests, archive blockers, placement violations и task validation mismatch дают `NO_GO`

**Input:** optionally specify a change name. Если имя не указано, infer только когда контекст однозначен; иначе запусти `openspec list --json` и попроси пользователя выбрать change.

## Steps

1. **Select the change**

   Если change name указан, используй его. Иначе:
   - infer from conversation context only when unambiguous
   - если ambiguous, запусти `openspec list --json` и попроси выбрать

   Всегда сообщи: `Проверяю change: <name>`. Для override: `/opsx-verify <other>`.

2. **Load verify settings**

   Сначала проверь contract `openspec/config.yaml`:
   ```bash
   python openspec/tools/check_config_contract.py
   ```

   Если contract check падает, зафиксируй unknown keys / rules contract violations, не продолжай verify и верни `NO_GO`.

   Прочитай `openspec/config.yaml` как UTF-8. Извлеки:
   - `rules.verify`

   Прочитай `openspec/policies/VERIFY_POLICY.md` как UTF-8. Извлеки:
   - `verify.default_mode`
   - `verify.language`
   - `verify.final_marker`
   - `verify.verdict`
   - `verify.archive_blockers`
   - `verify.output`

   Используй эти настройки как источник truth для verdict и формата ответа.

3. **Resolve change context**

   Run:
   ```bash
   openspec status --change "<name>" --json
   openspec instructions apply --change "<name>" --json
   ```

   Parse `schemaName`, `changeRoot`, `artifactPaths`, `actionContext`, `contextFiles`, tasks progress and task statuses. Use concrete paths from `artifactPaths.<id>.existingOutputPaths` and `contextFiles`; do not assume artifact names beyond command output.

4. **Read planning artifacts**

   Read proposal, design, specs, tasks, optional decisions, and any other existing artifacts reported by status/apply instructions. Extract:
   - required observable behavior
   - completed and remaining tasks
   - declared architecture decision references
   - ownership and placement claims
   - validation plan and targeted checks
   - open questions

5. **Architecture Decision Lookup**

   - Resolve decision paths context-first (`artifactPaths.decisions` / user paths / index); further `openspec/decisions/` lookup only for remaining gaps (budget ? 3 unless `EVIDENCE_GAP`). Never dump the full tree.
   - Read proposed decisions from `contextFiles.decisions` or `artifactPaths.decisions.existingOutputPaths`, if any.
   - Output relevant decisions by path and status in `Архитектурное размещение`.
   - If the change touches ownership, layering, write paths, or domain invariants and no relevant decision exists, mark `Architecture Decision Missing`.
   - If proposed decisions exist, get `openspec instructions decisions --change "<name>" --json` and apply `rules.decisions`.
   - Compare implementation placement against accepted/proposed decisions.
   - Passing tests не являются proof, если placement нарушает accepted decision.

6. **Verify implementation read-only**

   Inspect implemented code paths, local diff, and relevant tests without editing. Check:
   - behavior matches proposal/specs
   - tasks are accurately checked off
   - implementation layer matches cited architecture decisions
   - forbidden layers do not own logic reserved for another layer
   - tests prove behavior and do not hide placement violations
   - async tests do not manually mutate shared module-level dependencies around awaited code
   - tests do not stub the pipeline so the real guard is never exercised
   - write-gate regression tests prove the guarded entity is filtered before candidate/handler/write boundary, not only that a final mock was not called
   - regression tests fail if the intended guard is removed
   - gates with both blocked and allowed behavior have a paired positive case
   - archive blockers from `verify.archive_blockers`

7. **Run relevant checks**

   Run targeted tests or validation commands appropriate for the changed files and validation plan. At minimum, run OpenSpec validation for the change when available:
   ```bash
   openspec validate "<name>" --type change --strict --json
   ```

   If a check cannot run, report it explicitly and decide verdict using strict mode. If a task is `[x]` but its validation/test/check fails, write `Task completion mismatch: yes`.

8. **Compute one overall verdict**

   Produce exactly one overall verdict: `GO` or `NO_GO`.

   The overall verdict MUST be `NO_GO` when any configured condition is true:
   - targeted/focused test failed
   - task is checked `[x]` but validation/test/check failed
   - archive blocker exists
   - placement violation exists
   - required architecture decision is missing
   - unresolved open question blocks archive
   - stale reference model blocks archive
   - async test manually mutates module-level state around `await` with `module.attr = fake` and manual `try/finally` restore
   - test stubs the pipeline so the real guard is never exercised
   - write-gate regression only asserts `assert_not_called()` or `count == 0` without proving the guarded entity was filtered before candidate/handler/write boundary
   - regression test would still pass if the intended guard were removed
   - gate has both blocked and allowed behavior but lacks a paired positive case

   Do not write a success claim that conflicts with the overall verdict. `Archive ready: yes` is forbidden when tests failed, placement violations exist, or architecture blockers are unresolved.

## Output

Ответ должен быть на русском языке, кроме paths, commands, file names, class/function names and OpenSpec keywords.

Use exactly these sections:

```text
## Итоговый вердикт
GO — archive можно продолжать.
```

or

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

## Согласованность tasks
Task completion mismatch: yes / no
Причина: ...

## Готовность к archive
Archive ready: yes / no
Blockers:
- ...

## Следующая команда
/opsx-archive <change-name>
```

or for `NO_GO`:

```text
## Следующая команда
/opsx-apply <change-name>
```

Other allowed next commands for blockers: `/opsx-update <change-name>` or `manual fix`.

### LOCAL_HOP_COPY_BLOCK (mandatory)

Authority: `.cursor/pipeline/contracts/VERIFY_PHASES.md`.

After `## Следующая команда` and **before** the final marker, when the next
step is a local `/opsx-*` hop in this workspace, emit exactly **one** fenced
Owner-local copy-paste prompt (workspace, change, mode+marker, gaps/blockers,
exact Command, `DO_NOT_DO_YET` / `ALSO_OK` as applicable). Bare next-command
line alone is insufficient. No Web four-block for this hop.

The final line must be exactly one configured marker and nothing after it:

```text
✅ GO
```

or

```text
❌ NO_GO
```

(`mode=impl`: use PHASE_IMPL markers `✅ IMPL_OK` / `❌ IMPL_GAPS` and the
LOCAL_HOP_COPY_BLOCK rules from VERIFY_PHASES — do not emit archive GO/NO_GO.)

## Guardrails

- Read-only only. Do not edit files.
- Do not offer to fix code with a follow-up question like `Want me to fix?`.
- Instead of offering a write action, state the next command: `/opsx-apply`, `/opsx-update`, or `manual fix`.
- Do not mark verification successful when placement violates an accepted decision.
- Do not treat passing tests as sufficient architecture proof.
- Block async tests that manually mutate shared module-level dependencies around awaited code, especially shared executors, `run_tasks`, manager module functions, runtime services, WB write adapters, settings, and global flags.
- Block tests that stub the pipeline so the real guard is never exercised.
- Block write-gate tests that only assert `assert_not_called()` or `count == 0` without proving candidate/handler/write-boundary filtering.
- Block regression tests that would still pass if the intended guard were removed.
- Use exact file/function references for placement findings.
- Keep one overall verdict. No mixed top-level success plus archive `NO_GO`.
