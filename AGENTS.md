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
- `poetry run pytest` runs the full test suite (see markers in `pytest.ini`).
- `poetry run black .` formats code to the repo standard.
- `poetry run ruff .` runs linting (auto-fix enabled in pre-commit).
- `poetry run mypy --strict` runs type checks (mirrors pre-commit).
- `poetry run pyright-strict` runs strict pyright checks from `pyrightconfig_strict.json`.
- `docker-compose up -d redis clickhouse` starts local dependencies used in tests and dev workflows.
- `poetry run arq app.arq_workers.workers.WorkerSettings` starts the ARQ worker noted in `README.md`.

## Coding Style & Naming Conventions
- Python 3.11; follow Black formatting (line length 88) and Ruff lint rules.
- Type checking is strict; prefer explicit types for public APIs.
- Tests and scripts use snake_case; classes use CapWords.
- Avoid modifying generated client code under excluded paths in `pyproject.toml`.

## Testing Guidelines
- Pytest is the standard framework; async tests use `pytest-asyncio`.
- File naming: `test_*.py`, `*_test.py`, or `tests.py`; functions `test_*`, classes `Test*`.
- Use markers (`unit`, `integration`, `slow`, `sandbox`) and select via `-m`.

## Commit & Pull Request Guidelines
- Commit history follows Conventional Commits (e.g., `feat: add …`, `fix: …`, `refactor: …`).
- Keep subjects short and imperative; include context in the body if behavior changes.
- PRs should describe the change, list test commands run, and link relevant issues/tickets.

## Configuration & Security Notes
- Use `.env` and `env.sample` for configuration; do not commit secrets.
- Local state and logs (`logs/`, `redis-data/`, `clickhouse-data/`) are disposable.
