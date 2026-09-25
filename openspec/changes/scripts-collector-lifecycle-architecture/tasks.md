## 1. Tests-first — mandatory resolver

- [x] 1.1 Добавить unit fixtures для outcomes `REUSE`, `COMPOSE`,
  `FORMAL_CHANGE_REQUIRED` и `BLOCKED` (spec: scripts-collector-resolution).
- [x] 1.2 Зафиксировать и протестировать CLI:
  canonical `<canonical-root>/tools/scripts/resolver.py`
  `PLAN_RUN|RUN --request-file <absolute-path>
  --caller-root <absolute-path> --canonical-root <absolute-path>`, request
  schema, stdout result schema и exit codes `0/10/20/2/30`.
- [x] 1.3 Добавить тест malformed request → machine-readable `BLOCKED`,
  `error.code=INVALID_REQUEST`, exit `2`, без write path.
- [x] 1.4 Добавить тесты ordered acyclic child plan: child order, args, outputs,
  required/optional status и отсутствие semantic merge.
- [x] 1.5 Добавить тесты composite artifact/checksum gates, exact manifest fields,
  запись manifest после каждого child gate, concurrent-run isolation и
  partial-run `EXTERNAL_HANDOFF_READY=NO`.
- [x] 1.6 Добавить coverage tests:
  `request.required_fields ⊆ entry.provided_fields` для REUSE и union
  `provided_fields` children для COMPOSE.
- [x] 1.7 Добавить paired tests для `resolution_enabled` и
  `explicit_invocation_enabled`, включая explicit cabinet401 selection с
  `selection_mode=EXPLICIT`.

## 2. Machine registry SoT

- [x] 2.1 Создать `scripts/REGISTRY.yaml` с exact top-level schema/version,
  strict unknown/missing-field validation и minimal Registry v2 row schema.
- [x] 2.2 Реализовать exact commands:
  `registry.py validate`, `registry.py render`, `registry.py check-drift`;
  render writes only generated `scripts/REGISTRY.md`, ordering deterministic.
- [x] 2.3 Добавить только четыре R1 reference rows с обязательными
  `provided_fields` и `explicit_invocation_enabled`; cabinet401 v1/v2 оформить
  как `resolution_enabled: false`, `explicit_invocation_enabled: true`.
- [x] 2.4 Оставить ledger-only legacy rows с обоими флагами `false` без
  invocation metadata; не выполнять полный backfill.
- [x] 2.5 Добавить `deprecated_by` для cabinet401 v1/v2 с сохранением explicit
  `script=` access и replacement через multi-client reference.

## 3. Canonical worktree and provenance

- [x] 3.1 Реализовать в `tools/scripts/resolver.py` parsing
  `git worktree list --porcelain`, exact `refs/heads/scripts` и common-directory
  validation и tracked clean check.
- [x] 3.2 Реализовать precedence `--canonical-root` →
  `SCRIPTS_CANONICAL_ROOT` → topology → `BLOCKED`; invalid explicit roots do
  not fall back; читать registry/execution contract из fixed HEAD.
- [x] 3.3 Реализовать thin read-only bootstrap в `/opsx-scripts`: зафиксировать
  caller root/worktree/branch/SHA, выбрать exact `refs/heads/scripts` candidate
  и запускать resolver только абсолютным canonical path с
  `--caller-root`; matching/Registry/outcome остаются resolver responsibility.
- [x] 3.4 Добавить additive `CALLER_*`, `EXECUTION_SHA`, `REGISTRY_SHA`,
  `RESOLUTION_OUTCOME` и `RESOLUTION_PLAN` в SCRIPTS_REPORT.
- [x] 3.5 Зафиксировать canonical working directory/Poetry environment,
  absolute request path и запрет caller-local/stale resolver execution.
- [x] 3.6 Зафиксировать, что RUN GO не пишет, не коммитит, не пушит и не
  stash-ит code/registry/tests/commands/branches.

## 4. Command contract and runtime

- [x] 4.1 Обновить `/opsx-scripts` так, чтобы PLAN_RUN/RUN выполняли
  bootstrap-first, вызывали resolver и использовали только четыре operational
  outcomes; добавить search-gate против operational CREATE/EXTEND.
- [x] 4.2 Реализовать `.tmp/opsx-scripts/<run_id>/FORMAL_CHANGE_REQUIRED.json`
  с exact `opsx.formal-change-handoff.v1` schema и deterministic `/opsx-ff` vs
  `/opsx-update` selection, сохранив полный pasteable prompt.
- [x] 4.3 Реализовать sequential COMPOSE child Jobs; каждый child проходит
  свой primary/checksum gate до запуска следующего обязательного child.
- [x] 4.4 Реализовать `COMPOSE_MANIFEST.json` как primary composite artifact с
  exact `opsx.compose-manifest.v1` schema, Git-commit `registry_sha`,
  optional-child failure semantics и semantic merge prohibition.
- [x] 4.5 Убрать self-referential manifest hash: `primary_artifact` содержит
  только `path`/`accepted`; финальный digest писать в
  `COMPOSE_MANIFEST.json.sha256` и SCRIPTS_REPORT после финализации.
- [x] 4.6 Покрыть RUNNING nullability и terminal non-null/sentinel rules для
  child `job_name`, `artifact_path`, `sha256`, `failure`.

## 5. Reference migration R1

- [x] 5.1 Обновить resolution metadata и parameterization для
  `a1_strict_read_only_contract_collect.py`; завершить bind-parameter audit
  для изменённых PG/CH query builders в `ch_a1_evidence.py`.
- [x] 5.2 Оставить cabinet401 v1 и v2 доступными при explicit `script=`;
  resolver всё равно выполняется и применяет все safety gates.
- [x] 5.3 Нормализовать generic artifact naming и resolution metadata в
  `multi_client_ad_preflight_collect.py`.
- [x] 5.4 Добавить hardcoding gate только для новых/изменённых R1 rows с
  `resolution_enabled: true`; disabled legacy rows не должны блокировать R1.

## 6. Verification

- [x] 6.1 Запустить targeted unit/security/bootstrap tests для resolver,
  registry, provenance, composition и четырёх R1 entrypoints, включая
  canonical-root precedence без fallback, два параллельных COMPOSE run и
  manifest-after-each-gate evidence.
- [x] 6.2 Выполнить `openspec validate scripts-collector-lifecycle-architecture`.
- [x] 6.3 Выполнить apply-stage integration test во временном Git fixture с
  feature и exact `scripts` worktrees: clean HEAD, tracked dirty, wrong branch
  и different common directory; feature worktree не содержит актуальных
  resolver/REGISTRY.yaml, отдельный вариант fixture содержит stale resolver,
  а bootstrap запускает canonical resolver и фиксирует caller provenance без
  caller writes.
- [x] 6.4 После закрытия implementation blockers зафиксировать correction
  handoff status `READY_FOR_REVERIFY` в
  `verification/READY_FOR_REVERIFY.json`; `READY_FOR_MERGE_REVIEW` и
  post-merge real PLAN_RUN smoke разрешены только после независимого reverify
  и отдельной merge/deploy authorization.

## 7. Controlled correction после независимого reverify

- [x] 7.1 Сделать canonical topology ambiguity fail-closed для zero/one/multiple
  valid exact `refs/heads/scripts` candidates с executable tests.
- [x] 7.2 Добавить executable command-surface coverage для пользовательских
  `PLAN_RUN` и `RUN` через canonical bootstrap и machine resolver.
- [x] 7.3 Перед terminal success child проверять artifact path, existence и
  symlink/traversal safety внутри invocation artifact root.
- [x] 7.4 Самостоятельно вычислять SHA-256 child artifact, отклонять missing и
  mismatch, сохранять только verified digest в manifest.
- [x] 7.5 Добавить Git-backed proof, что `REGISTRY_SHA` является commit SHA
  Registry snapshot, а не content digest.
- [x] 7.6 Сохранить regression coverage partial artifacts, failed handoff,
  unbounded COMPOSE и no semantic merge; обновить verification evidence с
  разделением `CALLER_IMPLEMENTATION_VERIFIED` /
  `CANONICAL_INTEGRATION_PENDING`.

## Telegram UI / Message Safety

N/A — change не затрагивает Telegram payloads.
