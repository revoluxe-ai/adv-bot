# Coordinator snapshot (2026-10-15)

Сжатый перенос контекста чата WB Sky Project. Детали — в `context/notes.md` и linked docs.

## Authority

- `origin/stage` at export: `85fcfb85457bf589801be198cda7381206a29c06` (pull before trusting)
- Merge authority for certified PRs; no prod/GHCR without Owner

## Recently on stage (verify on remote)

- #479 task 4.1 shop-runner facts, #478 separate-auto-search-cpo, #477 4.2A Telegram ad control (dry-run), hierarchical A+B persistence, #475 opsx_verify rebaseline, and related merges listed in `notes.md`

## Active / blocked

| Workstream | Status |
| --- | --- |
| **wb-sky-mcp-read-interface** [#452](https://github.com/revoluxe-ai/adv-bot/pull/452) | Draft @ `ade611797`; CI green; HOME-PC v8r2 **BLOCKED_OWNER_MANUAL_RUN** — `docker_daemon_from_venv_python` from agent shell; token **unused**; packet `context/internal/wb-sky-mcp-cert-v8r2-packet.md` |
| **hierarchical 4.2B** | Blocked on Owner: snapshot store (Redis TTL recommended), enrollment predicate, scope; readiness `context/internal/architecture/task-42b-readiness-report.md` |
| **4.3 allocator** | Design only; **no** param/impl GO |
| **AI Package prod canary** | GHCR push 403; **READY_FOR_OWNER_PROD_CANARY_GO** |
| **durable shop-order facts** | Arch doc only; no impl GO |

## HOME-PC / self-hosted

- Owner machine online; MCP cert needs **Start-menu Git Bash** (Medium), not Cursor agent terminal
- Agent store **not** mounted on HOME-PC — paste packet paths/content in worker prompts

## OPSX

- Command-only enforcement: `context/docs/opsx-command-only-enforcement.md`
- Canonical dev workflow: `context/docs/adv-bot-canonical-development-workflow.md`

## Child agents (historical IDs — not auto-resume)

MCP: bc-1334b977 (hardening), bc-f400b3f3 (v8r2 run). Hierarchical UI: bc-67d4fbe8 **stopped by Owner** — no 4.2B without GO. Do not duplicate writers on same feature.
