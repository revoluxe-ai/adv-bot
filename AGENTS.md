# Repository Guidelines

## Project Structure & Module Organization
- `app/` holds the main Python package and runtime code; most business logic lives under `app/modules/`.
- `tests/` contains pytest suites; shared fixtures live in `conftest.py`.
- `alembic_/` and `alembic.ini` manage database migrations.
- `docs/`, `docks/`, and `DEVOPS_*.md` include operational notes and runbooks.
- `k8s/`, `dockers/`, and `docker-compose.yaml` provide deployment and local service configs.
- Data directories like `redis-data/` and `clickhouse-data/` are local state and should not be edited manually.

## Build, Test, and Development Commands
- `poetry install` sets up the Python environment.
- Run project commands through Poetry: `poetry run ...`
- Default quality gates are targeted `pytest`, adjacent `pytest` when relevant, `poetry run pyright-strict`, and `git diff --check`.
- `ruff` and `black` are not mandatory gates unless a task explicitly asks for linting or formatting.
- `poetry run pyright-strict` runs strict pyright checks from `pyrightconfig_strict.json`.
- `docker-compose up -d redis clickhouse` starts local dependencies used in tests and dev workflows.
- `poetry run arq app.arq_workers.workers.WorkerSettings` starts the ARQ worker noted in `README.md`.

## Coding Style & Naming Conventions
- Python 3.11; follow Black formatting (line length 88) and Ruff lint rules.
- Type checking is strict; prefer explicit types for public APIs.
- If a call returns a value (typed return ≠ `None`) and the caller intentionally ignores it, assign `_ = ...` (do not leave a bare call). For `-> None` / only-ever-returns-None callees, use a bare call/`await` (no `_ =`) — mypy `[func-returns-value]`. Prefer using the return when it matters. Enforced by pyright `reportUnusedCallResult`. See `.cursor/rules/python-unused-call-result.mdc`.
- Tests and scripts use snake_case; classes use CapWords.
- Avoid modifying generated client code under excluded paths in `pyproject.toml`.

## Documentation (required)
- **Always** add docstrings to new or changed Python modules, public classes, and public functions/methods.
- **Always** add a header comment block to new or changed `.sql` files under service `sql/` dirs (purpose, tables, parameters, caller). See `.cursor/rules/documentation.mdc`.
- Module docstrings: what the unit does and how it fits the domain. Method docstrings: behavior, side effects (ClickHouse, Redis, WB API), Args/Returns where non-obvious.
- Business logic docstrings may be in Russian; keep them concise and accurate.

## Testing Guidelines
- Pytest is the standard framework; async tests use `pytest-asyncio`.
- File naming: `test_*.py`, `*_test.py`, or `tests.py`; functions `test_*`, classes `Test*`.
- Every test is exactly one type: **unit** or **integration**. Unit = no real DB/Redis/ClickHouse (mocks only). Integration = uses real or test DB/Redis/ClickHouse or multi-component flow.
- Markers are assigned by path (`tests/unit/` → unit, `tests/integration/` → integration) or default to unit; override with `@pytest.mark.unit` or `@pytest.mark.integration`.
- Full unit suite: `poetry run pytest -m unit -n 8 --dist=worksteal` (pytest-xdist; preferred on this repo). Integration: `poetry run pytest -m integration`. Optional markers: `slow`, `sandbox` (use with `-m`, e.g. `-m "integration and not slow"`).
- Unit run does not start Docker or DB; the first delay is from loading the app/conftest. For quick feedback run a subset without xdist, e.g. `poetry run pytest -m unit tests/app/modules/auto_budget_manager/ -v` or `poetry run pytest -m unit -x` (stop on first failure).

## Commit & Pull Request Guidelines
- Commit history follows Conventional Commits (e.g., `feat: add …`, `fix: …`, `refactor: …`).
- Keep subjects short and imperative; include context in the body if behavior changes.
- PRs should describe the change, list test commands run, and link relevant issues/tickets.

## Configuration & Security Notes
- Use `.env` and `env.sample` for configuration; do not commit secrets.
- Local state and logs (`logs/`, `redis-data/`, `clickhouse-data/`) are disposable.

## Snapshot updater & shop-runner data paths
- Runbook: `docks/snapshot_data_updater.md` — env flags, rollout, Redis keys, diagnostics.
- Prod order: Redis `active_shops` → snapshot updater (`SNAPSHOT_UPDATER_USE_LIVE=1`) → shop-runner.
- Keywords: shop-runner — strict Redis (`ComplexAdv.get_keywords`, miss → error); UI — `fetch_keywords_from_database` (CH/PG); warmup — snapshot updater `get_good_bad_phrases`. No `allow_miss` soft fallback.
  Miss in shop-runner → `ShopRunnerKeywordsCacheMissError`; retry — `SHOP_RUNNER_REQUIRED_DATA_MISS_*` in `env.sample`.
- **min_bids cache miss** on read-only path: log level **WARNING** (`min_bids cache miss`), not ERROR;
  WB refresh failures use ERROR (`refresh_min_bids_cache_miss`). See `README_min_bids.md`, `wb_manager.py`.

## Cursor Cloud specific instructions
Standard dev commands live in this file's "Build, Test, and Development Commands" section and in `env.sample`; the notes below are only the non-obvious cloud caveats. The startup `update_script` already runs `poetry install`.

- **Python 3.11 only.** The Poetry venv is built on `python3.11` (`pyproject` pins `>=3.11,<3.12`); the system default `python3` is 3.12 and must not be used. `poetry` lives at `~/.local/bin/poetry`.
- **Timezone must be `Europe/Moscow`.** Several tests are timezone-sensitive (e.g. cache-staleness math: a UTC run makes a fresh value look exactly 10800s/3h stale). The VM tz is set to Europe/Moscow (`/etc/localtime`); if a future VM resets it, run tests with `TZ=Europe/Moscow` or re-`ln -sf /usr/share/zoneinfo/Europe/Moscow /etc/localtime`.
- **A repo-root `.env` is required (gitignored).** `app/settings` and several pydantic configs call `dotenv.load_dotenv()` at import, so missing vars fail at import time, not lazily. A local dev `.env` is provisioned pointing at the local containers. Vars that MUST be present or unit tests fail: `TELEGRAM_WEB_PORT`, `REDIS_MASTER_HOST`, `REDIS_REPLICA_HOST`, `MIN_SUM`, `BIDDER_STEP_RUB`, `CH_MAX_THREAD`, all `NEO4J_*` (uri/name/password/port — required, no defaults), `TG_TOKENS_FOR_SENDING`, and `DEV_TUNNELS_KUBECONFIG`. If `.env` is missing, recreate it from `env.sample` plus those keys.
- **Docker has no systemd here.** Start the daemon manually once per session: `sudo dockerd &` (or a tmux session), then `sudo chmod 666 /var/run/docker.sock` so non-root `docker`/`docker compose` (used by `conftest.py`) works.
- **Local services:** the root `docker-compose.yaml` referenced above is NOT in the repo. Run Redis as a standalone container (`docker run -d --name adv-bot-redis -p 6379:6379 redis:7-alpine`). Integration Postgres (5433) + ClickHouse (8124) come from `tests/docker-compose.test.yml`, which `conftest.py` brings up/tears down automatically for `-m integration` (reuses an already-healthy stack). Its volume paths use Windows-style `.\tests\...` but the stack still works on Linux (credentials come from compose env).
- **Tests:** `poetry run pytest -m unit` (~2600 pass, no Docker needed) and `poetry run pytest -m "integration and not sandbox and not slow"` (137 pass; needs Docker). `sandbox`/`slow` need real WB/Telegram APIs. Pre-existing unit failures unrelated to env setup: `tests/unit/test_auto_shelf_bid_control_manager.py::test_first_update_after_initialize_sets_bid_via_centralized_sync_path` and `::test_mode_transition_defers_bid_apply_to_centralized_sync_path` (mock-await mismatch), `tests/unit/client_bot/test_sales_plan_settings_keyboard.py::test_sales_plan_settings_keyboard_ignores_fact_pfo_plumbing` (test uses a `SimpleNamespace` missing `substitute_fact_cpo_for_max`), and `tests/unit/dev_local/test_k8s_tunnels.py::test_start_dev_tunnels_monitor_accepts_occupied_ready_ports` (needs the real, uncommitted `k8s/new-cluster/new-cluster-config.yaml`).
- **Lint:** `poetry run ruff check .` works but reports many pre-existing findings (`preview=true`, newer ruff). `black` is NOT a Poetry dependency — it only runs via `pre-commit` (its own isolated env), so `poetry run black` will fail.
- **Schema:** `alembic upgrade head` does NOT build a schema from scratch (the migration chain assumes an existing prod DB and fails on an index before its table). For a fresh local schema use `BaseTable.metadata.create_all` (the model set imported in `alembic_/env.py`), which is what `conftest.py` does.
- **Running the app locally:** snapshot data pipeline runs without external secrets — `poetry run python -m app.snapshot_data_updater.cli smoke` (stub) and `SNAPSHOT_UPDATER_USE_LIVE=1 poetry run python -m app.snapshot_data_updater.cli live-once --shop-id <id>` (real PG+CH+Redis). The client bot (`client_bot_run.py`, k8s `wb-sky-bot`) boots as a FastAPI service (`poetry run uvicorn client_bot_run:app --port 8080`, serves `/health` `/ready`) but needs a real `TELEGRAM_BOT_TOKEN` for any live Telegram traffic; a syntactically valid placeholder token + `POLLING_MODE=true` is enough to boot the web service. `run_adv_bot_stack.py` is NOT usable in the cloud VM (it does `kubectl port-forward` to the prod cluster).
