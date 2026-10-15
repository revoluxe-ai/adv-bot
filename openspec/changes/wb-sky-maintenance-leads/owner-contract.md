# Owner contract: wb-sky-maintenance-leads

Status: OWNER_GO_RECEIVED (2026-10-15); IMPLEMENTATION_DRAFT, NO_PRODUCTION_CUTOVER.

## Owner intent
- Existing Telegram WB Sky bot must display a maintenance notice instead of advertising controls.
- Exact user-facing text:
  - 🔧 WB Sky обновляется
  - В боте проходят масштабные обновления.
  - Для продолжения работы потребуется короткий инструктаж и перенастройка системы.
  - Оставьте заявку — мы свяжемся с вами и поможем продолжить работу.
- CTA: «📩 Оставить заявку».
- A submitted lead MUST contain a valid phone number. Accept own Telegram contact or manual phone. The Owner MUST receive the phone in a Telegram notification.
- Retain recoverable advertising data, then minimize billable Kubernetes CPU, memory and persistent storage.
- Do not impact MAX bots, Tiriel, Stroy, or other non-WB Sky workloads.

## Authority and safety
- User GO authorizes implementation work, not speculative deletion of volumes or substitution of unverified administrator IDs.
- LLM never controls production advertising writes.
- Maintenance bot has no WB API, database, queue or advertisement write adapter.
- Admin notification succeeds before user is told their lead is received; failure remains retryable.
- Resolve the single Owner notification recipient via `app/client_bot/const.py::MAIN_PRESENTATION_NOTIFY_TELEGRAM_ID`, and verify it matches `_BASE_ADMINS[0]` (annotated `# я`); any discrepancy fails closed. Do not introduce a separate recipient ID environment variable.
- Operations: separate scoped OPSX DevOps plan with exact resources, backup evidence, dry-run, rollback and matched Owner GO before Kubernetes mutations.
- Do not delete PVCs or a worker node until service dependencies, backup restore and migration are verified.

## Acceptance
1. /start and legacy callbacks only show maintenance screen.
2. Contact sharing must match Telegram user_id; third-party contacts rejected.
3. 10-digit RU mobile, 8/7 mobile and valid international number accepted; malformed phone rejected.
4. Owner notification recipient from const.py receives readable phone, username, sender id, time and update ID.
5. No false success when admin delivery fails.
6. Only one long poller for this Telegram token.
7. After runtime smoke, verified ad-only processes scaled to 0.
8. New cheapest available worker proven to schedule and serve all other applications.
9. Backups and recovery instructions validated; no permanent data deletion without explicit asset approval.

## Scope boundaries
Included: maintenance lead bot; dependency-minimizing runtime; controlled scale-down plan; node right-sizing plan.
Excluded: marketing campaigns, new lead CRM, removal of databases before backup proof, architecture of unrelated features.
