# Tasks: wb-sky-maintenance-leads

- [x] Owner GO and exact maintenance text captured.
- [x] Read-only Kubernetes inventory (node 10 vCPU / 32 GiB; current workloads and PVCs).
- [x] Isolated GitHub branch and minimal Python entrypoint.
- [x] Unit tests for required contact, manual phone, third-party rejection, no false success.
- [x] Reversible resource cutover plan with database retention and other-project protection.
- [x] Unit tests (14), Ruff, and Pyright on `maintenance_leads_bot.py` in the feature worktree. No live Telegram smoke.
- [ ] OpenSpec schema/spec validate and independent `/opsx-verify`.
- [x] Determine Owner ID from `const.py`: `MAIN_PRESENTATION_NOTIFY_TELEGRAM_ID` equals first `_BASE_ADMINS` (`# я`).
- [ ] Prove live notification delivery to Owner after cutover.
- [ ] Merge via normal PR/CI, build immutable release image.
- [ ] OPSX scoped PLAN_WRITE / GO for safe production image/command cutover.
- [ ] Real Telegram acceptance using self-contact and manual phone (Owner confirms receipt).
- [ ] OPSX scoped PLAN_WRITE / GO for 5 ad-only Deployment scales to zero.
- [ ] Cross-namespace dependency and tested backup/restore for ClickHouse, Redis, PostgreSQL.
- [ ] OPSX scoped PLAN_WRITE / GO for database scale-down.
- [ ] Record post-shutdown peak and request usage; select cheapest supported node with required reserve.
- [ ] Transfer all remaining unrelated workloads and validate functionality; remove previous worker only after proof.
- [ ] Check resulting provider bill (compute + block volumes + ancillary costs).
