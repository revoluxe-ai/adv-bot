# Shell for static-check workers

## Canonical human commands

```text
pyright-strict
mypy .
poetry run pytest -m unit <paths…>          # pytest-targeted unit bucket (≤1; prefilter destructive)
poetry run pytest -m integration <paths…>   # pytest-targeted integration bucket (≤1; skip if empty)
poetry run pytest -m unit -n 8 --dist=worksteal
poetry run pytest -m unit -x               # pytest-unit fallback classifier only
poetry run pytest -m integration
poetry run pytest -m destructive_local      # FULL only; requires ALLOW_*
```

## Mandatory agent invoke

```bash
bash .cursor/static-check/bin/run.sh -- pyright-strict
bash .cursor/static-check/bin/run.sh -- mypy .
bash .cursor/static-check/bin/run.sh -- poetry run pytest -m unit <paths…>
bash .cursor/static-check/bin/run.sh -- poetry run pytest -m integration <paths…>
bash .cursor/static-check/bin/run.sh -- poetry run pytest -m unit -n 8 --dist=worksteal
bash .cursor/static-check/bin/run.sh -- poetry run pytest -m unit -x
bash .cursor/static-check/bin/run.sh -- poetry run pytest -m integration
bash .cursor/static-check/bin/run.sh -- poetry run pytest -m destructive_local
```

From repo root. Works in **Git Bash and WSL**.

Runner resolves **absolute** `.venv/Scripts/*.exe` (or `.venv/bin/*`) and does **not** source `~/.bashrc` (avoids npm pyright/node).

Packet `COMMAND`: human form (`pyright-strict`, `mypy .`, `poetry run pytest -m …`, …).

Do **not** invoke `poetry run pytest .` — path `.` overrides `testpaths` and may
collect `.tmp/**`.

Do **not** invoke bare `poetry run pytest` (no marker) — retired with
`pytest-full`. Use the cascade markers above.

## Forbidden

- `bash -lc 'source ~/.bashrc; source .venv/Scripts/activate; …'`
- bare `pyright` / global npm shims
- durable Tee/log files by default
- `poetry run pytest .`
- bare `poetry run pytest` (no `-m`)

## Hard rules

- Missing venv tool → `STATUS=BLOCKED` (exit 127 from runner).
- Pytest cascade: targeted PASS → unit → integration → (FULL only) destructive.
  Later pytest waves SKIPPED on FAIL|BLOCKED|ERROR. Never deselect dirty paths
  from suite waves. Never schedule destructive in FAST.
- **xdist only on full unit:** `-n` / `--dist=worksteal` is allowed solely for
  `poetry run pytest -m unit -n 8 --dist=worksteal`. Never add xdist to
  targeted path runs, integration, or destructive.
- **unit fallback classifier:** `poetry run pytest -m unit -x` is allowed only
  after pytest-unit xdist INFRA retry is exhausted (see pytest-unit pack).
- **pytest-targeted:** prefilter `destructive_local` before Shell; ≤1 run per
  non-empty bucket; empty/exit 5 → PASS+note, never exclude+rerun.
- **Stale pytest:** before Wave U (and before pytest-unit INFRA retry), clear
  orphaned pytest/xdist for this REPO_ROOT (see pytest-unit instructions).
  Concurrent second `-n` suite on the same tree is unsupported.
  Kill only eligible pre-run orphans outside current run tree; ambiguous
  ownership => `blocked_hygiene_ambiguous` (do not blind-kill).
- **pytest-unit owner:** orchestrator Shell (`task_type: orchestrator`), not a
  nested Task.
