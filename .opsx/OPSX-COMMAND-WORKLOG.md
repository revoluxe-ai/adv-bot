# OPSX Command Worklog

Журнал отложенных и найденных дефектов в process-surface commands
(`.cursor/commands/`, meta/admin lane). Product-код (`app/**`) сюда не входит.

## Метаданные

| Поле | Значение |
|------|----------|
| Репозиторий | `implement-free-bot-rebase` |
| Ветка | `implement-free-bot-rebase` |
| Base | `stage` |
| Источник | Bugbot (`branch changes` vs `stage`) |
| Дата | 2026-08-22 |
| Статус ревью | Завершено (6 findings); app-код не покрыт |

---

## Открытые findings

### CMD-001 — Meta-consult routes missing commands

| | |
|---|---|
| Severity | **high** |
| Location | `.cursor/commands/opsx-meta-consult.md:165` |
| Category | LOGIC_BUG |
| Status | open |

`route_analyze_pipeline` и `route_promote_lesson` ведут на `/opsx-meta-analyze-pipeline` и
`/opsx-meta-promote-process-lesson`, но таких command-файлов в репо нет — только
`/opsx-admin-command-analyze-pipeline` и `/opsx-admin-command-promote-process-lesson`.
Операторы по `NEXT_ACTION` из consult или handoff из
`/opsx-admin-command-resolve-conflicts` попадают в dead routes.

**Fix hint:** выровнять routing table с реальными slash-именами или добавить missing
meta-command artifacts.

---

### CMD-002 — Meta-commit omits opsx-export scope

| | |
|---|---|
| Severity | **medium** |
| Location | `.cursor/commands/opsx-meta-commit.md:211` |
| Category | LOGIC_BUG |
| Status | open |

В diff добавлены `.cursor/opsx-export/**` в `/opsx-admin-command-commit` и
`/opsx-admin-command-export-bundle`, но canonical `/opsx-meta-commit` не включает
`.cursor/opsx-export/**` в in-scope list. `/opsx-commit-all` и resolve-conflicts
считают meta-commit authority; export-изменения не коммитятся через primary path.

**Fix hint:** добавить `.cursor/opsx-export/**` в scope `/opsx-meta-commit` (parity с
admin-commit).

---

### CMD-003 — Meta-commit mandates npm build

| | |
|---|---|
| Severity | **medium** |
| Location | `.cursor/commands/opsx-meta-commit.md:41` |
| Category | LOGIC_BUG |
| Status | open |

TARGET OVERRIDE требует mandatory `npm run build`, тогда как repo — Poetry/Python
(`local_modification_note` / sibling commands банят vue-npm). Agents могут FAIL_CLOSED
или запускать несуществующий frontend build при meta-commits.

**Fix hint:** заменить check на poetry-python gates или убрать npm из OVERRIDE.

---

### CMD-004 — Commit-all stale verification claims

| | |
|---|---|
| Severity | **medium** |
| Location | `.cursor/commands/opsx-commit-all.md:39` |
| Category | LOGIC_BUG |
| Status | open |

`/opsx-commit-all` ссылается на verification gates в `/opsx-commit` (pytest/pyright,
static-check FULL receipt), но переписанный `/opsx-commit` gates убрал и forbids
static-check receipts. Orchestrator вводит в заблуждение → ложные BLOCKED или пропуск
commits при `FAST_CHECK`/`FULL_CHECK`.

**Fix hint:** синхронизировать override с актуальным контрактом `/opsx-commit`.

---

### CMD-005 — Antipattern gate head resolution conflict

| | |
|---|---|
| Severity | **medium** |
| Location | `.cursor/commands/opsx-antipattern-gate.md:117` |
| Category | LOGIC_BUG |
| Status | open |

Default audit target = dirty worktree при omitted `head`, но scan algorithm step 1
всё ещё `git rev-parse head` и fail on error — конфликт с **Target resolution**
(`WORKTREE` vs immutable ref). Sibling `/opsx-external-call-coverage` уже исправлен
аналогично.

**Fix hint:** step 1 — «Resolve the target using Target resolution above», как в
external-call-coverage.

---

### CMD-006 — Commit-all frontmatter misplaced

| | |
|---|---|
| Severity | **low** |
| Location | `.cursor/commands/opsx-commit-all.md:64` |
| Category | LOGIC_BUG |
| Status | open |

`description` и `argument-hint` в mid-file `---` block (после TARGET OVERRIDE), не в
top frontmatter. Cursor/slash loaders не подхватят metadata — `/opsx-commit-all` может
зарегистрироваться без description и token contract.

**Fix hint:** перенести `description` / `argument-hint` в единственный top-level
frontmatter block.

---

## Сводка

| Severity | Count |
|----------|-------|
| high | 1 |
| medium | 4 |
| low | 1 |
| **Total open** | **6** |

## Следующие шаги (deferred)

- [ ] CMD-001 … CMD-006 — правки в `.cursor/commands/`
- [ ] Повторный Bugbot на `app/client_bot/` + `tests/unit/client_bot/` (узкий scope)
