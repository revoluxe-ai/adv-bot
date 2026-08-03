# pytest-unit — context

- Marker `unit` = no real DB/Redis/ClickHouse (see AGENTS.md / testing-rules).
- Unit run should not require Docker.
- Full suite uses pytest-xdist: `-n 8 --dist=worksteal` (measured fastest on Windows for this repo).
- xdist is **only** for this full unit suite — targeted / integration /
  destructive must not use `-n` / `--dist`.
- Collection node ids must be deterministic across workers (no time-based parametrize at collect).
- First delay is often app/conftest import cost — still report honest STATUS.
- Runs after `pytest-targeted` PASS; must re-include dirty/related tests already
  exercised in targeted (no deselect).
- Owned by orchestrator Shell (no nested Task) to avoid Agent Looping /
  mid-flight empty packets on long suites.
- Stale concurrent pytest/xdist on the same tree is a known cause of
  `Unexpectedly no active workers available` — hygiene before run + one
  INFRA recovery (see instructions). Treat worker-death without failed
  node ids as `ERROR infra_suite`, not product FAIL.
- Hygiene must avoid false-positive kills: only pre-run-orphan processes
  outside current run tree are eligible; ambiguous ownership should block
  (`blocked_hygiene_ambiguous`) instead of blind terminate.
- After one xdist infra retry, this pack performs an in-run fallback classifier
  (`pytest -m unit -x`) to produce a deterministic product verdict and avoid
  manual kill/re-run loops.
