# pytest-unit — context

- Marker `unit` = no real DB/Redis/ClickHouse (see AGENTS.md / testing-rules).
- Unit run should not require Docker.
- First delay is often app/conftest import cost — still report honest STATUS.
