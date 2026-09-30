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

## Scripts / ops lane (non-blocking product CI)
- Operational collectors and registry live under `scripts/`, `tools/scripts/`, and related k8s templates (e.g. `k8s/jobs/ops-script-runner.yaml`). They are outside core product runtime and **must not** block urgent `app/` hotfixes when absent from the PR.
- Keep incident fixes narrow; land large `scripts` merges separately. See `.cursor/rules/scripts-ops-lane.mdc`.
- `migration-gates` runs only for DB/migration paths and named migration jobs—not for ops script runner manifests.

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
