## Context

LEGACY `app.dev_local.k8s_tunnels` (~kubectl port-forward PG/CH) уже deprecated: канон локали — публичный IP/NodePort из `.env`; автозапуск из settings отключён; unit-тесты модуля сняты. На ветке модуль всё ещё в `pyrightconfig_strict.json` include и даёт typing FAIL. Единственный Python-caller — debug `run_rec_bid_recommendations_debug.py`. Параллельно — `scripts/dev-tunnels.ps1`. Destructive fixtures используют `DEV_TUNNELS_*` как hard-fail denylist.

## Goals / Non-Goals

**Goals:**

- Удалить in-app LEGACY tunnel Python API и package re-export.
- Убрать debug-caller и обновить его unit-тесты.
- Удалить `scripts/dev-tunnels.ps1` и устаревшие tunnel setup-инструкции из env.sample / local-dev docs.
- Снять pyright include для `app/dev_local/*`.
- Сохранить destructive denylist на tunnel-env.

**Non-Goals:**

- Менять production DB topology / NodePort / credentials.
- Трогать A/B Hold, Emergency, shop-runner write paths.
- Вводить новый in-app tunnel.
- Ослаблять destructive safety.

## Architecture Decision References

- Context-first lookup: `openspec/decisions/index.md` — нет accepted decision про local-dev kubectl tunnels / port-forward ownership.
- Product write-path / Hold / Emergency ADL к этому change **не применимы**.
- Канон локального доступа уже зафиксирован operational docs/rules (`k8s/network/local-dev-external-access.md`, `.cursor/rules/local-production-entrypoints.mdc`, `.cursor/rules/debug-runtime.mdc`) — reusable product Architecture Decision для этого cleanup **не требуется**.
- Proposed `openspec/changes/.../decisions/` **не создаём** (optional decisions artifact skipped).

## Ownership & Placement

- **Owner layer:** local-dev tooling / debug entrypoints / test safety (не domain write-path).
- **Allowed:** удаление LEGACY modules/scripts; правка debug entrypoint; docs/env.sample; pyright allowlist; destructive denylist comments/keys.
- **Forbidden:** production automation handlers; WB write adapters; Hold/Emergency modules; ослабление destructive fixtures.
- Placement matches proposal: cleanup-only, без нового runtime ownership.

## Decisions

1. **Полное удаление Python LEGACY + ps1 в одном change**  
   Почему: WORKLOG явно перечисляет оба; оставлять ps1 как «тихий» параллельный путь продлевает drift.  
   Альтернатива: оставить `dev-tunnels.ps1` — отклонено для DoD этого change (можно откатить scope через bound-scope, если Owner передумает).

2. **Сохранить `DEV_TUNNELS_ENABLED` denylist в destructive tests**  
   Почему: safety против случайного live destructive через tunnel env; не зависит от наличия модуля.  
   Альтернатива: стереть все `DEV_TUNNEL_*` из fixtures — Forbidden (теряем guard).

3. **Не предлагать новый openspec/decisions entry**  
   Почему: нет gap по product ownership/write-path; канон уже в docs/rules.  
   Альтернатива: ADL «local-dev MUST use .env» — избыточно для cleanup.

## Risks / Trade-offs

- [Risk] Локальные workflow на port-forward сломаются → Mitigation: **BREAKING** в proposal; docs указывают `.env` IP; rollback через git.
- [Risk] Случайно удалить denylist → Mitigation: явная задача + regression tests на hard-fail.
- [Risk] Пустой пакет `app/dev_local` → Mitigation: удалить пакет целиком или оставить минимальный module docstring «removed» — предпочесть удаление пустого пакета.

## Migration Plan

1. Удалить код/скрипт/include; обновить caller/tests/docs.
2. Прогнать targeted unit (debug entrypoint + destructive denylist unit).
3. `poetry run pyright-strict` / static-check FAST — ожидать исчезновение ошибок `k8s_tunnels.py`.
4. Rollback: git restore удалённых путей.

## Open Questions

- Нет блокирующих: scope ps1 включён по WORKLOG; при необходимости Owner может сузить через `/opsx-bound-scope`.

## Review Checklist

- [x] existing decisions searched
- [x] relevant decisions cited (none applicable; docs/rules as operational canon)
- [x] new decision proposed if missing (not needed)
- [x] implementation layer matches decision (tooling cleanup only)
