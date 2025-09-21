# Adv-Bot Project

## Overview
Advanced advertising bot for Wildberries platform automation.

## Code Quality & Pre-commit Setup

This project uses a comprehensive pre-commit pipeline to ensure code quality and consistency. The pipeline includes:

- **isort**: Import sorting compatible with Black
- **Black**: Code formatting (88 character line length)
- **Ruff**: Fast linting with auto-fix (E, F, B, SIM, UP rules)
- **Flake8**: Additional validation with bugbear (temporary, until Ruff covers all rules)
- **Basic checks**: End-of-file fixer, trailing whitespace removal, merge conflict detection

### Installation & Setup

1. **Install pre-commit**:
   ```bash
   pip install pre-commit
   ```

2. **Install the git hook**:
   ```bash
   pre-commit install
   ```

3. **Run on all files** (initial setup):
   ```bash
   pre-commit run --all-files
   ```

### Usage

- **Automatic execution**: Pre-commit hooks run automatically on `git commit`
- **Manual execution**: `pre-commit run` (staged files) or `pre-commit run --all-files`
- **Run specific hook**: `pre-commit run <hook-id>` (e.g., `pre-commit run black`)

### Configuration Files

- **`.pre-commit-config.yaml`**: Hook configuration and versions
- **`pyproject.toml`**: Tool-specific configurations (Black, isort, Ruff)
- **`setup.cfg`**: Flake8 configuration
- **`.yamllint`**: YAML linting rules (currently disabled due to encoding issues)

### Tool Configuration Details

#### Black (Code Formatter)
- Line length: 88 characters
- Target Python version: 3.11
- Single source of truth for code formatting

#### isort (Import Sorting)
- Profile: black (compatible with Black formatting)
- Line length: 88 characters

#### Ruff (Fast Linter)
- Enabled rule sets: E (pycodestyle errors), F (Pyflakes), B (flake8-bugbear), SIM (flake8-simplify), UP (pyupgrade)
- Disabled: I (isort rules, handled by separate isort hook)
- Ignored: E203 (Black compatibility)

#### Flake8 (Additional Validation)
- Max line length: 88 characters
- Ignored: E203, W503 (Black compatibility)
- Includes flake8-bugbear for additional checks

### Excluded Directories

The following directories are excluded from all tools to improve performance and avoid issues with generated/legacy code:

- `alembic/`, `migrations/`, `generated/`
- `build/`, `dist/`, `__pycache__/`
- `.venv/`, `venv/`, `.git/`
- `.mypy_cache/`, `.pytest_cache/`, `.tox/`, `.eggs/`
- `node_modules/`
- `app/modules/shop_runner/service_manager/old_modules/`

### Updating Tool Versions

Update pre-commit hook versions quarterly:
```bash
pre-commit autoupdate
```

### Troubleshooting Common Issues

#### Black vs isort Conflicts
If you encounter formatting conflicts between Black and isort:
1. Ensure isort is configured with `profile = "black"`
2. Run isort first, then Black: `pre-commit run isort && pre-commit run black`

#### Long Lines
- Black will not automatically break long lines in all cases
- Manually break lines where needed, especially in comments and strings
- Consider refactoring complex expressions

#### Import Ordering
- isort handles import sorting automatically
- If imports look wrong after auto-fix, check for relative import issues

#### Performance
- First run takes longer due to environment setup
- Subsequent runs are cached and much faster
- Use `--show-diff-on-failure` to see what changed

### Development Workflow

1. **Before committing**:
   ```bash
   # Optional: Run pre-commit manually to see what will be fixed
   pre-commit run

   # Commit your changes (pre-commit runs automatically)
   git add .
   git commit -m "Your commit message"
   ```

2. **If pre-commit fails**:
   - Review the output and fix any remaining issues manually
   - Stage the auto-fixed files: `git add .`
   - Commit again: `git commit -m "Your commit message"`

3. **Emergency bypass** (use sparingly):
   ```bash
   git commit --no-verify -m "Emergency commit message"
   ```

### Current Status

✅ **Working**: isort, Black, Ruff, Flake8, basic file checks
⚠️ **Temporary issues**: Some Python files have linting violations that need manual fixes
❌ **Disabled**: YAML linting (encoding issues with some project files)

### Next Steps

1. **Short term**: Gradually fix linting violations in active development files
2. **Medium term**: Re-enable YAML linting after resolving encoding issues
3. **Long term**: Remove Flake8 once Ruff covers all required rules (estimated Q2 2024)

### Performance Expectations

- **Typical changeset**: < 30 seconds on development machine
- **Full repository**: ~1 minute initially, then cached
- **CI/CD**: Caching enabled for faster builds

## Development Setup

[Add other development setup instructions here...]

## Project Structure

[Add project structure documentation here...]
