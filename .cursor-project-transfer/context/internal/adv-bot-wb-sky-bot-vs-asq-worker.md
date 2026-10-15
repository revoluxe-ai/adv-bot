# wb-sky-bot vs adv-bot-asq-worker (2026-09-30)

**FACT:** два Deployment в `prod-adv-bot`; «бот отвечает» ≠ «воркер выполнил create_complex_advs».

| | wb-sky-bot | adv-bot-asq-worker |
|---|------------|---------------------|
| Роль | FSM, callbacks, enqueue ARQ | `create_complex_advs`, WB API, outbound Telegram |
| Telegram | mostly inbound long poll | outbound via SOCKS (PAT-ADV-002) |
| Типичные сбои | FSM not handled / stale button (PAT-ADV-003) | pre-fix: ProxyTimeout on progress notify (PAT-ADV-001); post `3693e936e`: best-effort |

Check order: bot handler + enqueue → worker job start → first exception.
