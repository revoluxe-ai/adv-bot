## 1. Characterization / regression first

- [x] 1.1 Зафиксировать текущие unit-тесты denylist `DEV_TUNNELS_ENABLED` (destructive PG/CH) — они MUST остаться зелёными после удаления модуля (spec: Destructive tests reject tunnel environment)
- [x] 1.2 Обновить/сузить `tests/unit/test_run_rec_bid_recommendations_debug.py`: убрать ожидания `_ensure_dev_tunnels` / tunnel bootstrap; entrypoint MUST стартовать без in-app tunnel API (spec: Local database connectivity uses env hosts)

## 2. Remove LEGACY Python surface

- [x] 2.1 Удалить `app/dev_local/k8s_tunnels.py` и package `app/dev_local` (re-export `__init__.py` / пустой пакет)
- [x] 2.2 Убрать import и вызов tunnel bootstrap из `run_rec_bid_recommendations_debug.py`
- [x] 2.3 Удалить `scripts/dev-tunnels.ps1`

## 3. Allowlist, env, docs

- [x] 3.1 Убрать `app/dev_local/**` из `pyrightconfig_strict.json` include
- [x] 3.2 Очистить `env.sample` от инструкций setup `DEV_TUNNEL_*` / `dev-tunnels.ps1`, сохранив комментарий/контракт denylist для destructive tests
- [x] 3.3 Обновить local-dev / debug docs и docstring `settings_master.run_local`: не ссылаться на Python `k8s_tunnels` / ps1 как поддерживаемый путь; канон = `.env` IP/NodePort
- [x] 3.4 Пройти `.cursor/rules` упоминания `k8s_tunnels` / `dev-tunnels.ps1` — заменить на канон `.env` или «Forbidden без отдельного GO» без отсылки к удалённому API

## 4. Verification

- [x] 4.1 `poetry run pytest` targeted: destructive denylist units + `test_run_rec_bid_recommendations_debug.py`
- [x] 4.2 `poetry run pyright-strict` — нет diagnostics по удалённому `k8s_tunnels.py`
- [x] 4.3 Подтвердить, что production entrypoints не импортируют `app.dev_local` (grep/import check)
