# pytest-full — RETIRED

**Retired.** Do not launch this check.

Replaced by the pytest cascade in `.cursor/static-check/registry.yaml`:

1. `pytest-targeted` — dirty/related paths (working tree)
2. `pytest-unit` — `-m unit`
3. `pytest-integration` — `-m integration`
4. `pytest-destructive` — `-m destructive_local` (FULL only)

Bare `poetry run pytest` (no marker) is forbidden in `/opsx-static-check`.

If an orchestrator still references `pytest-full` → treat as ERROR/misconfig;
use the cascade packs instead.
