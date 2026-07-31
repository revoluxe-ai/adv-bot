# pytest-full — context

- Includes unit + integration and may need Docker/DB/local services.
- Honest environment failures beat fake "test-failure" labels.
- Heavier than unit; expected only in MODE=FULL.
- Invoke `poetry run pytest` (no path arg) so `testpaths = tests` applies.
  Do **not** pass `.` — that overrides testpaths and may collect `.tmp/**`
  harness / docker-volume trees (collection errors, not missing libs).
