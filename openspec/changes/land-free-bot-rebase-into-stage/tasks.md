## 1. Tests-first: scope, provenance и characterization

- [x] 1.1 Добавить characterization tests для branch-to-base snapshot: base identity, candidate identity и исключение unrelated dirty state; тесты должны падать при включении постороннего файла в readiness evidence.
- [x] 1.2 Добавить regression tests для смены candidate snapshot во время проверки: прежний verdict становится недействительным, а evidence требует повторного прогона.
- [x] 1.3 Добавить tests для provenance matrix: remote branch reachability, base reachability, proven database application, unproven application и conflicting evidence; для unknown/conflicting состояния проверить `EVIDENCE_GAP` и `NO_GO`.
- [x] 1.4 Зафиксировать в tests migration semantics до implementation: classifier `bot_active=True → true`, `bot_active=False → false`, default для новых записей, nullable transition и expected affected-record preview.
- [x] 1.5 Добавить paired tests для interrupted/partial data transition и повторного запуска, включая проверку отсутствия несовместимого повторного присваивания.
- [x] 1.6 Добавить tests для before/after compatibility baseline existing paid/free clients: automation flags, billing, WB writes и campaign lifecycle; broad backfill, меняющий baseline, должен давать `NO_GO`.
- [x] 1.7 Добавить regression tests, доказывающие отсутствие persistent `None → True` fallback и запрет broad backfill без `bot_active` classifier.

## 2. Architecture и выбор migration route

- [x] 2.1 Получить explicit owner confirmation для expected values existing/new records, допустимого backfill и recovery action; без подтверждения зафиксировать `NO_GO`.
- [x] 2.2 Получить acceptance или отдельное решение по `forward-only-data-migration-rollout`; проверить, что implementation placement соответствует `openspec/decisions/alembic-forward-only-head-convergence/decision.md`.
- [x] 2.3 Получить acceptance по production migration Job/write-path; до acceptance держать production rollout в `NO_GO`.
- [x] 2.4 Собрать provenance evidence и выбрать ровно один route: `rewrite-before-landing`, `forward-repair` или `NO_GO`; choice и rationale сохранить в readiness record.
- [x] 2.5 Получить explicit approval, что существующие paid/free клиенты не должны быть молча переведены в новую automation; намеренный behavior change вынести в отдельное принятое product decision.
- [x] 2.6 Зафиксировать stage/prod release sequence, обязательные migration/deployment receipts, monitoring window и forward recovery owner.

## 3. Реализация migration и landing-readiness path

- [x] 3.1 Реализовать scope-bounded readiness evaluation на одном base/candidate snapshot без изменения OPSX command contracts и без включения unrelated worktree state.
- [x] 3.2 Реализовать выбранный migration route: не переписывать proven published/applied revision, а при необходимости добавить forward repair; для unproven not-yet-landed revision разрешить rewrite только после provenance review.
- [x] 3.3 Сохранить topology-only merge revision без schema/data operations и не менять существующие опубликованные parent-ссылки.
- [x] 3.4 Разделить schema/data transition на безопасный schema step и approved one-time migration Job без blanket allowlist для `op.execute()`/`op.alter_column()`, dynamic SQL обхода или runtime fallback.
- [x] 3.5 Добавить или обновить regression tests для graph convergence, migration safety, affected-record preview, existing/new defaults, final constraint и retry behavior; каждый новый или изменённый тест снабдить русским docstring с названием spec и обоснованием.
- [x] 3.6 Добавить recovery evidence для test DB: backup/restore либо forward compensating action; не использовать destructive production downgrade как часть landing change.
- [x] 3.7 Реализовать compatibility guard для existing paid/free cohorts: не допускать silent drift automation, billing, WB writes или campaign lifecycle; при намеренном изменении остановиться на accepted product decision.
- [x] 3.8 Реализовать одноразовый idempotent release backfill по classifier `bot_active` с preview, affected-record report и проверкой отсутствия несовместимого остатка.

## 4. Верификация и readiness package

- [x] 4.1 Запустить focused Alembic head/convergence contract и подтвердить ровно одну итоговую head без переписывания истории.
- [x] 4.2 Запустить stage-diff migration safety tests и targeted data-transition tests на том же candidate snapshot; зафиксировать все findings.
- [x] 4.3 Запустить required targeted tests, unit tests, strict static checks и OpenSpec validation; отсутствующий или относящийся к другому snapshot результат считать gap.
- [x] 4.4 Сформировать readiness package с base/candidate SHA, scope, provenance matrix, preview affected records, test DB result, command outputs и rollback/recovery evidence.
- [x] 4.5 Проверить, что readiness, stage deployment, production rollout и database application имеют отдельные evidence и receipts.
- [x] 4.6 Выдать итоговый release `GO` только при прохождении всех требований spec; иначе выдать `NO_GO` с actionable gaps и не выполнять production actions вне approved path.
- [x] 4.7 Отдельно подтвердить compatibility existing clients в финальном readiness review; любой необъяснённый drift блокирует GO.
- [ ] 4.8 Выполнить stage deployment и сохранить schema, backfill, UI, smoke и compatibility receipts для одного candidate SHA.
- [ ] 4.9 Выполнить production migration/UI rollout только после approved release gate и сохранить database/deployment receipts.
- [ ] 4.10 Выполнить production smoke и paid/free compatibility verification в monitoring window; unexplained drift переводит release в `NO_GO`.
- [ ] 4.11 Зафиксировать production verification result, recovery evidence и окончательный release verdict.

## Telegram UI / Message Safety

Изменение не создаёт и не изменяет Telegram payload surfaces: сообщения,
captions, callback answers, keyboards, polls, invoices или checklist text.
