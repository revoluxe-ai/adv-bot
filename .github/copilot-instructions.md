# GitHub Copilot Instructions for adv-bot

## Project Overview

This is a Python-based advertising bot application built with FastAPI, aiogram (Telegram bot), and various integrations with Wildberries marketplace, databases, and ML services.

## Technology Stack

- **Language**: Python 3.11
- **Package Manager**: Poetry
- **Web Framework**: FastAPI
- **Bot Framework**: aiogram 3.4.1
- **Databases**: PostgreSQL (asyncpg, SQLAlchemy 2.0), Redis, Neo4j, ClickHouse
- **Task Queue**: Celery, arq
- **ML/AI**: TensorFlow, Keras, scikit-learn, XGBoost, Faiss, Gensim
- **Testing**: pytest, pytest-asyncio
- **Code Quality**: mypy, ruff, pre-commit hooks

## Build and Development

### Setting Up the Environment

```bash
# Install dependencies using Poetry
poetry install

# Activate virtual environment
poetry env activate
```

### Running Linters and Type Checkers

```bash
# Run ruff linter
poetry run ruff check .

# Run ruff formatter
poetry run ruff format .

# Run mypy type checker
poetry run mypy --config-file=mypy.ini .

# Run pre-commit hooks
poetry run pre-commit run --all-files
```

### Running Tests

```bash
# Run all tests
poetry run pytest

# Run specific test markers
poetry run pytest -m unit -n 8 --dist=worksteal
poetry run pytest -m integration
poetry run pytest -m asyncio

# Run with coverage
poetry run pytest --cov=app --cov-report=html

# Run circular import tests
poetry run pytest tests/test_circular_imports.py -v
```

### Running the Application

```bash
# Run arq worker (for creating advertising campaigns)
arq app.arq_workers.workers.WorkerSettings

# Test advertising campaign creation
python create_adv.py
```

## Code Style and Standards

### Python Code Style

- **Line Length**: 88 characters (Black/Ruff standard)
- **Python Version**: 3.11
- **Type Hints**: Use type hints for all function signatures and public APIs
- **Unused call results**: If a function/method returns a value (typed return ≠ `None`) and the caller intentionally ignores it, assign `_ = ...` (never leave a bare call). For `-> None` / only-ever-returns-None callees, use a bare call/`await` (no `_ =`) — mypy `[func-returns-value]`. Prefer using the return when it matters. Enforced by pyright `reportUnusedCallResult`. See `.cursor/rules/python-unused-call-result.mdc`.
- **Async/Await**: Prefer async/await for I/O operations (database, API calls, etc.)

### Import Organization

- Standard library imports first
- Third-party imports second
- Local application imports last
- Avoid wildcard imports (`from x import *`)
- Use absolute imports where possible

### Naming Conventions

- **Functions/Variables**: snake_case
- **Classes**: PascalCase
- **Constants**: UPPER_SNAKE_CASE
- **Private members**: prefix with underscore `_`

### Ruff Configuration

The project uses ruff for linting with these key rules:
- Excludes: `app/core/mp/wb/_api_client/clients/promotion/generated/`, `alembic/versions`, `k8s/*`, `tests/*`
- Ignores: F821 (undefined name), F401 (unused imports in `__init__.py`)
- Per-file ignores: E722, F841 in test files

## Database and Migrations

### Alembic Migrations

```bash
# Create a new migration
poetry run alembic revision --autogenerate -m "description"

# Apply migrations
poetry run alembic upgrade head

# Rollback migrations
poetry run alembic downgrade -1
```

### SQLAlchemy Usage

- Use SQLAlchemy 2.0 async style
- Session management via `app.utils.db.session_maker`
- Models defined in `app.utils.db.models`

## Testing Guidelines

### Test Structure

- Every test has exactly one type: **unit** or **integration**. Full unit suite: `poetry run pytest -m unit -n 8 --dist=worksteal`; integration: `poetry run pytest -m integration`. Targeted path suites omit `-n`.
- Type is set by path (`tests/unit/` → unit, `tests/integration/` → integration) or by explicit `@pytest.mark.unit` / `@pytest.mark.integration`; tests without either default to unit (see `conftest.py`).
- Unit tests: isolated, mocks only (no real PostgreSQL/Redis/ClickHouse). Integration tests: use test DB/Redis/ClickHouse or multi-component flow.
- Async tests are detected via `asyncio_mode = auto`. Slow tests use `@pytest.mark.slow`; combine with type if needed (e.g. `-m "integration and not slow"`).

### Writing Tests

```python
import pytest
from unittest.mock import AsyncMock, MagicMock

@pytest.mark.unit
@pytest.mark.asyncio
async def test_example_async_function():
    # Arrange
    mock_service = AsyncMock()
    
    # Act
    result = await function_under_test(mock_service)
    
    # Assert
    assert result is not None
    mock_service.some_method.assert_called_once()
```

### Circular Import Testing

- All entry points must be tested for circular imports
- Entry points listed in `docs/entry_points.md` and in the `ENTRY_POINTS` list in `tests/test_circular_imports.py`
- Add new entry points to both `docs/entry_points.md` and `tests/test_circular_imports.py`

## Dependency Management

### Adding Dependencies

```bash
# Add production dependency
poetry add package-name

# Add development dependency
poetry add --group dev package-name

# Update dependencies
poetry update
```

### Security Considerations

- Always check for security vulnerabilities before adding dependencies
- Keep dependencies up to date
- Use specific version constraints for critical packages

## Common Patterns

### Async Database Operations

```python
from app.utils.db.session_maker import get_session

async def example_db_operation():
    async with get_session() as session:
        result = await session.execute(query)
        return result.scalars().all()
```

### Dependency Injection

The project uses `dependency-injector` for DI patterns. Follow existing container configurations.

### Configuration Management

- Use `pydantic-settings` for configuration
- Store sensitive data in environment variables
- Never commit secrets to the repository

## Documentation

- Update `README.md` for user-facing changes
- Update relevant docs in `docs/` and `docks/` directories for internal documentation
- Use docstrings for all public functions and classes
- Follow Google-style docstrings

## Git Workflow

- Create feature branches for new work
- Run pre-commit hooks before committing
- Ensure all tests pass before creating PR
- Keep commits atomic and well-described

## Special Considerations

### Generated Code

Do not modify files in these directories (they are auto-generated):
- `app/core/mp/wb/_api_client/clients/promotion/generated/`
- `alembic/versions/` (unless creating new migrations)

### Kubernetes and DevOps

- K8s configurations in `k8s/` directory
- Deployment workflows in `.github/workflows/`
- Docker configurations available for containerization

### Monitoring and Logging

- Use structured logging via `logging_config.json`
- Prometheus/Grafana setup documented in project docs
- Memory profiling available via `memory-profiler`

## Before Submitting Changes

1. Run linters: `poetry run ruff check .`
2. Run type checker: `poetry run mypy --config-file=mypy.ini .`
3. Run tests: `poetry run pytest`
4. Verify pre-commit hooks pass: `poetry run pre-commit run --all-files`
5. Check that no circular imports were introduced
6. Update documentation if needed
7. Ensure no secrets are committed

## Getting Help

- Check existing documentation in the repository
- Review similar code patterns in the codebase
- Check test files for usage examples
- Review DevOps guides: `DEVOPS_QUICK_START.md`, `MONITORING_QUICK_START.md`
