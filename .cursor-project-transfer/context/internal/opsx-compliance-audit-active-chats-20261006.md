# OPSX compliance audit — active feature chats (read-only)

**Дата:** 2026-10-06  
**Метод:** transcript tail + coordinator knowledge; не полный grep всех ходов.

## Verdict summary

| Change | Chat (authority) | Compliance | Typical bypass |
|--------|------------------|------------|----------------|
| `telegram-ai-package-export` / #454 | [Telegram ai package export](bc-ee363d78) | **FAIL** | Full implementation: direct edits, `npx openspec validate`, manual `pytest`/`ruff`/`pyright` — **no** `/opsx-apply` |
| `telegram-ai-package-export` (historical) | [telegram-ai-package-export](bc-ddffe2e5) | **FAIL** | Same; prose `OWNER GO bounded repair` → direct commit without `/opsx-apply` |
| `wb-sky-mcp-read-interface` / #452 | [wb-sky-mcp-read-interface — predeploy hardening](bc-1334b977) | **PARTIAL** | User prompts cite `/opsx-spec-scenario-coverage`, `/opsx-test`, `opsx-close-external-gap`; execution often **manual pytest** + subagent prose, not always `Read(opsx-*.md)` as PRIMARY |
| `ai-package-multi-window-analysis` / #453 | [ai-package-multi-window-analysis — implementation](bc-f1a938ec) | **PARTIAL** | Prompts name `/opsx-spec-scenario-coverage mode=certify` and `/opsx-verify mode=impl`; agent runs **manual** pytest/hash scripts; cites verify policy files but **PRIMARY_COMMAND** not invoked as slash turn |
| `campaign-settings-changeset-contract` / #449 | [campaign-settings-changeset-contract — implementation](bc-fec0e994) | **UNKNOWN** | Independent verify requested as prose; no transcript slice in this audit |

## Systemic pattern (architect → feature)

1. Long prompts with `MODE:`, `TASK:`, `WRITE AUTHORIZATION:` — **mimic** OPSX gates without binding to `.cursor/commands/*.md`.
2. **Gates reimplemented ad hoc** (`poetry run pytest`, `npx openspec validate`) instead of `/opsx-test`, `/opsx-verify`, `/opsx-static-check` where applicable.
3. **Implementation** delivered without `/opsx-new` → `/opsx-continue` → `/opsx-apply` chain (notably #454).

## What already aligns

- OpenSpec change dirs + `openspec validate` often run (good artifact discipline).
- MCP / multi-window: scenario plan receipts, certify vocabulary, read-only modes respected in **intent**.
- Project `preferences.md` already states command-only (2026-09-30).

## Coordinator actions (no repo writes)

1. Enforce [opsx-command-only-enforcement](/cursor/stores/self/docs/opsx-command-only-enforcement.md) on all dispatches.
2. Reject architect prose-TASK for execution; emit single-line `/opsx-*` hop.
3. Feature chats: reopen turn with PRIMARY only when Owner sends work.

## Gaps to fix in OPSX spine (not product)

- Architect handoff template requiring leading `/opsx-*`.
- Missing command for «bounded UP035 repair only» without full `/opsx-apply` — today invites bypass (#454).
- Provider run: must be `/opsx-close-external-gap` or documented certify path, not raw `pytest` in prose.
