# Запрос Диспетчеру — специализированный runtime COL-R04-001

## Нужно

Новый чат ИЛИ проект (или явный reuse существующего OpsX control) для:
OWNER_LOCAL_READ_ONLY_PREFLIGHT_R04 / COL-R04-001

Это НЕ Web COLLECTOR. Credentialed runtime = Owner-local / OpsX.
Local Cursor → production cabinet/API ЗАПРЕЩЁН.

## Контекст

- Pilot reopen YES (r04), r03b PARK sealed
- Lab first gate: AUTHORIZED_NOT_PREFLIGHTED
- Lab chat: https://chatgpt.com/g/g-p-6a6a79c2150481918258d6db0ce5415b-wb-promotion-audit-research-lab/c/6a7588e6-03a8-83ed-a2b8-ecef47c99930
- Historical: WB API Preflight Control — COL-R03-008 was GET-only; r04 amends to GET_OR_DOCUMENTED_POST_AS_READ + new cabinet B1

## Deliverables from Dispatcher

1) Выбор: ЧАТ / ПРОЕКТ / REUSE_OPSX_WITH_INSTALL
2) Exact title
3) Install prompt or project package
4) First Owner step to produce the preflight ZIP that Lab expects
5) Confirm secrets never enter ChatGPT

## Attachments in ZIP

- OWNER_REQUEST_DISPATCHER_COL_R04_001.md (this)
- COL-R04-001_OWNER_LOCAL_PREFLIGHT_TZ.md (exact Lab TZ)
- R04_EXECUTION_SCOPE.yaml
- TOWER_PILOT_REOPEN_DECISION_r04.md (summary authority)
