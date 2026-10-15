# Deploy rollback reserve (adv-bot prod)

**Owner rule (2026-09-30):** если раскатка нового образа падает (пример: `adv-bot-asq-worker` после PR #443), резерв отката — **master / last known good на master** («резерв на мастер перекидываем»). Не откатываться на stage-tip и не делать bare `kubectl set image`.

## Источник образа для CAS

Читать на каждом `/opsx-devops` hop (обязательно по `.cursor/rules/devops.mdc`):

| Поле | Значение (снимок 2026-09-25, `adv-bot/.cursor/devops/OPS_STATE.md`) |
|------|------------------------------------------------------------------------|
| **Last known good (prod LKG)** | tag `4d5fae43576d290ca8324424b29772ce0eb1a5f5` |
| **Prepared fallback (prior LKG)** | tag `01e29e36fa539e8bdf4307516af922e176c8a0d6` |
| **Prepared fallback digest** | `sha256:f33349f2c163727b356ae3039ef5f2c73dfa08cde67758260cd5f77b1335b207` |
| **Registry (cluster pull)** | `harbor.skyline360.ru/git-registry-cache/revoluxe-ai/adv-bot` |
| **Schema at rollback** | `alembic_version` `d7e3c9f1a204` — image-only rollback unless forward-fix (`LAST.json` notes) |

**Выбор тега:** после неудачного forward-deploy откатывать на **prod LKG** (`4d5fae43…`) или **Prepared fallback** (`01e29e36…`) из OPS_STATE — что соответствует последнему стабильному master-line до сбоя; не выдумывать тег из чата.

## Процедура

1. `INVESTIGATE` — подтвердить сбой rollout / CrashLoop на целевом Deployment.
2. `PLAN_WRITE intent=image_cas` (или scoped CAS внутри `safe_prod_release`, если lease/schema требуют) — JSON Patch `test`+`replace`, namespace `prod-adv-bot`.
3. Owner `GO` на тот же scope.
4. Обновить `OPS_STATE` / `LAST.json` только после успешного GO (`/opsx-meta-commit`).

Частичный откат (только `adv-bot-asq-worker`) допустим по прецеденту shop-runner/UI rollback в OPS_STATE action log.

## OPS_STATE vs live drift (2026-09-30)

**FACT ([Check prod deploy status](bc-809f24f4-673f-594f-96ba-87d470ad418d)):** entrypoints на `c5d3ecd88…`; в repo `OPS_STATE` LKG `4d5fae43…`. Перед rollback/CAS не подставлять LKG «вслепую» — `/opsx-devops INVESTIGATE` + при необходимости meta-commit; риск описан в [#444](https://github.com/revoluxe-ai/adv-bot/pull/444).

## Subagent deploy / #443 (2026-09-30)

| Статус | Деталь |
|--------|--------|
| **WIP** | **Нет** — deploy-turn в [bc-2b4a5d73](https://cursor.com/agents/bc-2b4a5d73-52a9-5463-9d04-00996d1a6147) остановлен Owner |
| **При возобновлении** | CAS rollback target = OPS_STATE **prepared fallback** / **master LKG** (таблица выше), не образ с ветки stage |
| **Связанный инцидент** | [adv-bot-incident-138252141-campaigns.md](/cursor/stores/self/docs/adv-bot-incident-138252141-campaigns.md), PAT-ADV-001 |

## PLAN_WRITE rollback hint (pasteable)

```text
/opsx-devops PLAN_WRITE intent=image_cas ns=prod-adv-bot resource=deployment/adv-bot-asq-worker image=harbor.skyline360.ru/git-registry-cache/revoluxe-ai/adv-bot:4d5fae43576d290ca8324424b29772ce0eb1a5f5 digest=sha256:51a966e5434421b7c858169cdb44521afe1bf485e82d24ead7ec55e3d317da28 symptom=failed_rollout_PR443 rollback_reserve=master_LKG_OPS_STATE prepared_fallback=01e29e36fa539e8bdf4307516af922e176c8a0d6 schema=d7e3c9f1a204 image_only
```

Для отката на **prepared fallback** заменить `image`/`digest` на `01e29e36…` / `sha256:f33349f2…` в том же PLAN_WRITE.
