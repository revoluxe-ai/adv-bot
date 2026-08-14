# Verify Phases (shared module)

## Purpose

Общий READ_ONLY модуль фаз проверки OpenSpec change.

Не отдельная пользовательская команда. Его вызывают:

- `/opsx-verify` (тонкий switch `mode=`);
- будущая отдельная команда post-apply DoD (на базе этого модуля).

Authority split:

- этот файл — **фаза / маркеры / что проверять / NEXT_ACTION**;
- `openspec/policies/VERIFY_POLICY.md` — archive policy + blockers;
- `.cursor/commands/opsx-verify.md` — полный archive-audit procedure
  (вызывается только в `PHASE_ARCHIVE`);
- `/opsx-test … verify` — **другой** verify (bug GREEN); не путать.

## Mode selection

Parse from user args / command text:

```text
mode=impl | mode=archive
```

Rules:

- omitted `mode=` → **default `archive`** (backward compatible) + one-line WARN:
  prefer explicit `mode=impl` or `mode=archive`;
- unknown mode → stop; ask Owner to pick `impl` or `archive`;
- `mode=impl` MUST NOT emit `✅ GO` / `❌ NO_GO`;
- `mode=archive` MUST NOT emit `✅ IMPL_OK` / `❌ IMPL_GAPS` as final markers;
- only `mode=archive` + `✅ GO` authorizes `/opsx-archive`.

## PHASE_IMPL — post-apply DoD

### Question

Сделали ли owed Current Increment (tasks / spec / design / decision)?

### When

Immediately after `/opsx-apply` `all_done` / `impl_done`.
Before long quality chain (pyright / ecc / …) when production `.py` changed.

### Read (bounded)

Change `proposal`, `design`, `tasks`, delta/main specs, proposed/accepted
decisions cited by the change; SEMANTIC_WRITE_TARGET fields if high-risk write;
targeted tests named by tasks.

Do **not** require `EXTERNAL_CALL_COVERAGE_REPORT` /
`PERFORMANCE_REVIEW_REPORT` / static-check PASS as blockers in this phase
(absence → note soft; not IMPL_GAPS alone).

### Must check

1. Tasks checked `[x]` match evidence (no checkbox theater).
2. Behavior vs IN_SCOPE / delta-or-main spec scenarios owed by the change.
3. Architecture placement vs cited decisions; no FORBIDDEN adapter on planned path.
4. SEMANTIC_WRITE_TARGET: `RESOLVED` durable fields when applicable; unresolved →
   `IMPL_GAPS` (same class as archive blocker, but phase marker differs).
5. Paired tests required by tasks/spec/decision exist and targeted run is green
   (or explicitly deferred with Owner note — else gaps).
6. OUT_OF_SCOPE / FUTURE_INCREMENTS not implemented as DoD creep
   (`EVOLUTION_SCOPE_DRIFT` → gaps).

### Must not

- Claim archive ready.
- Emit `✅ GO` / `❌ NO_GO`.
- Edit files.
- Run full quality-chain re-audit as hard blockers.

### Output (required)

```text
## Verify phase
mode=impl

## Итоговый вердикт
IMPL_OK — DoD change выглядит выполненным; archive ещё нельзя.
```

or:

```text
## Итоговый вердикт
IMPL_GAPS — DoD не закрыт; сначала apply/update.
```

Sections (short):

```text
## Поведение
## Архитектурное размещение
## Тесты (DoD slice)
## Согласованность tasks
## Archive
Archive ready: no
Reason: mode=impl never authorizes archive

## Следующая команда
```

Then **LOCAL_HOP_COPY_BLOCK** (required — see below) **before** the final
marker. Bare `NEXT_ACTION` / `## Следующая команда` alone is **not** a
sufficient Owner-local hop.

Final line exactly one of:

```text
✅ IMPL_OK
```

```text
❌ IMPL_GAPS
```

### NEXT_ACTION after PHASE_IMPL

`IMPL_OK` + in-policy production `.py` changed:

```text
NEXT_ACTION: /opsx-pyright-strict-coverage base=<BASE>
THEN: … → /opsx-verify mode=archive <change>
DO_NOT_DO_YET: /opsx-archive
```

`IMPL_OK` + no production `.py`:

```text
NEXT_ACTION: /opsx-verify mode=archive <change>
DO_NOT_DO_YET: /opsx-archive
```

`IMPL_GAPS`:

```text
NEXT_ACTION: /opsx-apply <change>
ALSO_OK: /opsx-update <change>
DO_NOT_DO_YET: /opsx-archive ; quality chain as substitute for DoD
```

### LOCAL_HOP_COPY_BLOCK (mandatory after PHASE_IMPL)

When the recommended next step is another `/opsx-*` hop in **this** Cursor
workspace (typical after `IMPL_OK` or `IMPL_GAPS`):

1. Keep verify report sections as above.
2. After `## Следующая команда` / bare `NEXT_ACTION` lines, and **before**
   the final marker (`✅ IMPL_OK` / `❌ IMPL_GAPS`), emit exactly **one**
   fenced copy-paste prompt (`LOCAL_HOP_COPY_BLOCK`) whose body is plain
   text and already contains:
   - workspace path (absolute);
   - change name;
   - verify `mode=` + marker (`IMPL_OK` | `IMPL_GAPS`);
   - 1–3 gap/blocker lines when `IMPL_GAPS` (or notable caveats on `IMPL_OK`);
   - exact next command (from NEXT_ACTION above);
   - `DO_NOT_DO_YET` / `ALSO_OK` lines when applicable.
3. Outside that fence (except the required final marker line): at most
   **one** status line.
4. Forbidden for this local hop: Web four-block form (`Ссылка` / `Папка` /
   separate path blocks outside the fence).
5. Bare `NEXT_ACTION:` remains inside the verify report for machine/scan
   readers; it **does not replace** `LOCAL_HOP_COPY_BLOCK`.
6. Final marker stays the **last line** of the verify report (VERIFY_POLICY
   `final_marker.position: last_line` / PHASE_IMPL markers).

Example shape (values filled from the run — do not leave placeholders):

````text
```text
Workspace: <abs-path>
Change: <change-name>
Prior: /opsx-verify mode=impl → <IMPL_OK|IMPL_GAPS>
Gaps: <1–3 lines or none>
Command: <exact next /opsx-…>
DO_NOT_DO_YET: /opsx-archive
```
````

Then the final line:

```text
✅ IMPL_OK
```

or:

```text
❌ IMPL_GAPS
```

## PHASE_ARCHIVE — pre-archive gate

### Question

Можно ли archive? (спек после фиксов в quality chain + blockers + reports)

### When

After quality chain (or short path when no prod `.py` after `IMPL_OK`),
before `/opsx-archive`.

### Procedure

1. Announce `## Verify phase` / `mode=archive`.
2. **Destructive cache soft gate** (see `/opsx-verify`): if last FULL was
   `CACHE_MODE=dev` / `DESTRUCTIVE_CACHED>0` / no `CACHE_OFF|FORCE`
   receipt → WARN `DESTRUCTIVE_CACHE_DEV_BEFORE_ARCHIVE` + paste
   `/opsx-static-check FULL CACHE_OFF` (soft; not sole `NO_GO`).
3. Execute the full archive audit already defined in
   `.cursor/commands/opsx-verify.md` (behavior, placement, tests, tasks,
   additive packet/reports, SWT, VERIFY_POLICY blockers).
4. **Product Acceptance (kernel DONE):** follow
   `.cursor/pipeline/contracts/PRODUCT_ACCEPTANCE.md`. Compute
   `PRODUCT_ACCEPTANCE_REQUIRED` / `PRODUCT_ACCEPTANCE_STATUS`. When required,
   `PASS` needs MEANING_LOCK ∧ LIFECYCLE_COVERAGE ∧ SIDE_EFFECT_PROOF.
   `FAIL` / `BLOCKED` / missing required evidence → archive blocker
   `product_acceptance_not_pass` (pillar in output). Soft tooling PASS/waive
   does **not** clear PA.
5. Re-check spec/tasks coherence after any fixes done during quality chain
   (drift since `mode=impl` → `NO_GO`).
6. Final markers only from VERIFY_POLICY: `✅ GO` / `❌ NO_GO`.
7. `## Готовность к archive` + pasteable next command (include cache WARN
   and PA status/pillar if raised).

### NEXT_ACTION after PHASE_ARCHIVE

`✅ GO`:

```text
NEXT_ACTION: /opsx-archive <change>
```

`❌ NO_GO`:

```text
NEXT_ACTION: /opsx-apply <change>
ALSO_OK: /opsx-update <change>
```

If DoD itself regressed, after repair prefer re-run
`/opsx-verify mode=impl <change>` before another archive verify.

### LOCAL_HOP_COPY_BLOCK (mandatory after PHASE_ARCHIVE)

Same rules as PHASE_IMPL `LOCAL_HOP_COPY_BLOCK`: when the next hop is a local
`/opsx-*` in this workspace (`/opsx-archive` on `✅ GO`, or `/opsx-apply` /
`/opsx-update` on `❌ NO_GO`), emit one fenced Owner-local prompt **before**
the final marker, with workspace, change, `mode=archive` + marker, blockers
(on `NO_GO`), exact Command, and applicable `DO_NOT_DO_YET` / `ALSO_OK`.
Bare `NEXT_ACTION` / `## Следующая команда` alone is insufficient. No Web
four-block for this hop. Final marker remains the last line.

## Consumer hint matrix (embed in companion commands)

| Producer | Pasteable NEXT when success |
|---|---|
| `/opsx-apply` all_done | `/opsx-verify mode=impl <change>` |
| verify `mode=impl` IMPL_OK + prod `.py` | `/opsx-pyright-strict-coverage base=<BASE>` |
| verify `mode=impl` IMPL_OK + no prod `.py` | `/opsx-verify mode=archive <change>` |
| verify `mode=impl` IMPL_GAPS | `/opsx-apply <change>` |
| pyright / ecc / perf / antipattern PASS | continue chain (soft); final verify = `mode=archive` (PA still required when applicable) |
| `/opsx-static-check` PASS + cache-dev / cached>0 | `/opsx-static-check FULL CACHE_OFF` then `/opsx-verify mode=archive <change>` |
| `/opsx-static-check` PASS + CACHE_OFF/FORCE/DEGRADED | `/opsx-verify mode=archive <change>` |
| verify `mode=archive` GO | `/opsx-archive <change>` |
| `/opsx-archive` saw only IMPL_OK | `/opsx-verify mode=archive <change>` |

Never point quality-chain success at bare `/opsx-verify` without `mode=`
when the phase is known; prefer `mode=archive`.

## Future separate command

A dedicated post-apply DoD command MAY later wrap **only** `PHASE_IMPL`
from this module without duplicating rules. Until then `/opsx-verify mode=impl`
is the sole front-door for PHASE_IMPL.
