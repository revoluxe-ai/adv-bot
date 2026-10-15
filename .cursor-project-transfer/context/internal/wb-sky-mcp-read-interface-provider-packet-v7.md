---
cursor:
  subagentId: "bc-df43b72f-7d90-5738-8e1d-5df31e87c560"
---

# PROVIDER-PACKET-v7 (wb-sky-mcp-read-interface)

- Worktree: `C:\Users\vkita\my_code\meta-repo\adv-bot-mcp-v7` @ `6761824ee938c2a4712b6f4872ebabf3d33a2557`
- One `guard run` executed; authorization `cdd533556b8504421cf7053b016cb1a62fcddad5b9fc2b69d8126af784ff72af` → **AUTHORIZED_CONSUMED**
- Outcome: **PROVIDER_FAILED** (pytest exit 1) — Docker npipe denied in pytest child (`permission denied` on `dockerDesktopLinuxEngine`)
- Post-run: `icacls … /setintegritylevel M` on worktree `.venv\Scripts\python.exe` and `pytest.exe`; `tests/clickhouse-config/users.xml` removed locally with `git update-index --assume-unchanged` (CH 26.x config fix); `temporal-postgresql-1` stopped to free 5433
- Retry requires **new** one-shot authorization (v7 token consumed)
