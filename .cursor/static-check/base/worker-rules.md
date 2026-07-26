# Shared worker rules (all static-check agents)

- READ_ONLY: do not edit repository files (including `.cursor/static-check/**`, agents, `bin/run.sh`).
- Do not fix code, tests, configs, or this check infrastructure.
- Do not “self-heal” the runner when a command fails → return BLOCKED/FAIL packet only.
- Run exactly one check from your pack `instructions.md`.
- Do not run sibling checks.
- Do not spawn nested subagents.
- Do not invent command fallbacks if the canonical tool is missing → `STATUS=BLOCKED`.
- Return only the worker packet from `contracts/worker-packet.md`.
- Do not invent findings; missing fields → `n/a`.
- Cap FINDINGS detail at 50; keep full FINDINGS_TOTAL; set FINDINGS_TRUNCATED: yes when needed.
- RAW_TAIL ≤ 40 lines.
