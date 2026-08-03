# pytest-unit — context

- Marker `unit` = no real DB/Redis/ClickHouse (see AGENTS.md / testing-rules).
- Unit run should not require Docker.
- Full suite uses pytest-xdist: `-n 8 --dist=worksteal` (measured fastest on Windows for this repo).
- Collection node ids must be deterministic across workers (no time-based parametrize at collect).
- First delay is often app/conftest import cost — still report honest STATUS.
- Runs after `pytest-targeted` PASS; must re-include dirty/related tests already
  exercised in targeted (no deselect).
