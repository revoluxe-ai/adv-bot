# WB Sky maintenance mode — production cutover plan

Scope: \`prod-adv-bot\` only. Owner intent (2026-10-15): no advertising operations; show maintenance notice, collect a required phone number, notify one named administrator, minimize infrastructure cost. This document is a **PLAN, not an authorization to mutate production**.

## Application

Source: \`maintenance_leads_bot.py\` (Python stdlib; long polling; no PostgreSQL, Redis, ClickHouse or WB API).
Entrypoint in the normal \`dockers/Dockerfile\` image after the change has passed merge/build: \`python /app/maintenance_leads_bot.py\`. The normal Dockerfile uses \`COPY . .\`.
Environment: \`CLIENT_BOT_TOKEN\` (preferred) or \`TELEGRAM_BOT_TOKEN\`; \`MAINTENANCE_ADMIN_CHAT_ID\` (required). Never print tokens or hardcode a guessed administrator. Identify the real admin chat ID by the owner's confirmed operational channel.
Use **one** replica and **Recreate** deployment strategy; two Telegram long pollers using one token conflict.
Keep an existing outbound proxy **only if** Telegram access smoke proves direct traffic unavailable. Standard \`urllib\` honors HTTPS_PROXY if configured.
Runtime resources to trial: requests 10m CPU / 32Mi RAM; limits 250m CPU / 96Mi RAM. Confirm live memory/CPU and adjust from evidence. No Service/Ingress necessary for polling.

User text:
> 🔧 WB Sky обновляется
>
> В боте проходят масштабные обновления.
>
> Для продолжения работы потребуется короткий инструктаж и перенастройка системы.
>
> Оставьте заявку — мы свяжемся с вами и поможем продолжить работу.

Button \`📩 Оставить заявку\`; then \`📱 Поделиться номером\` (Telegram-native) or manual phone. No valid phone means no lead confirmation. Notice to admin contains normalized phone, sender name, username, Telegram ID, timestamp and update ID. Telegram API admin delivery precedes user success acknowledgment. A transient retry may duplicate an admin notification; update ID supports deduplication.

## OPSX gates and run sequence

1. **PLAN_WRITE, read-only:** read current live Deployment/ReplicaSets/Services and image digest, \`.cursor/devops/OPS_STATE.md\`, \`LAST.json\`, and safe-release procedure. Verify no unrelated user/automation still uses WB Sky resources. Confirm existing ingress, polling, token mapping without exposing secrets.
2. Materialize OpenSpec feature contract, run selected tests/Ruff/Pyright/OPSX verify, review and merge. Build/pin immutable production image. No release from a draft PR.
3. **SAFE_PROD_RELEASE plan:** ensure schema migration is a justified no-op. Follow \`/opsx-devops\` CONTROL → Migrate (when required) → image CAS → complete_release (when lease acquired) → OPS_STATE. Switch only \`wb-sky-bot\` to the maintenance entrypoint and \`Recreate\` policy; ensure only one poller owns token.
4. **Mandatory acceptance BEFORE shutting down legacy workloads:** real \`/start\`, CTA, own Telegram contact, manual phone, bad phone, legacy callback. Confirm the Owner actually receives a message with a working phone number; test delivery failure and no false success.
5. **SCALE plan:** after smoke PASS, scale to zero **only verified WB-specific** stateless deployments: \`adv-bot-asq-worker\`, \`adv-bot-updater\`, \`run-shop-update-worker\`, \`run-update-active-shop-ids\`, \`trunc-system-log-clickhouse\`. Classify \`xray-client\` and \`bebra-shared-proxy\` after verifying maintenance bot/other consumers do not use them. Keep \`wb-sky-bot\` as 1 replica. \`free-bot\` is already at zero.
6. **STATEFUL DATA gate:** before stopping \`prod-analytics/clickhouse-restore\`, \`redis2-master\`, \`prod-adv-bot/postgres-db\`, document dependencies from every namespace (particularly MAX/Tiriel/Stroy), validate restorability of full backups and migration metadata and retain credentials securely. Scaling DB StatefulSets to zero frees CPU/RAM but does **not** reduce PVC bills. Current PVCs: ClickHouse 100Gi NVMe; Redis 16Gi NVMe; WB PostgreSQL 30Gi NVMe. StorageClasses use reclaim policy \`Delete\`: never delete a PVC/PV before independently verified copies and explicit asset-deletion plan.
7. **NODE RESIZE plan:** cluster currently one worker 10 vCPU / approximately 32 GiB RAM. Record actual CPU/RAM and requests **after** workload reductions for all remaining namespaces. Trial smallest provider-available node with headroom, taking scheduling requests, spikes, stateful PV topology, ingress, monitoring and rolling restarts into account. A 2 vCPU / 8 GiB node is a hypothesis only, NOT an approved size. Migrate surviving MAX/Tiriel/Stroy workloads, verify health and data, then remove old node. Compare Timeweb worker price plus network disks and provider control-plane pricing before committing.
8. Preserve a rollback record: previously running deployment image, command, strategy, environment source refs, replica counts, StatefulSet PVC identities, last successful backups. Rollback on missing admin messages or loss of unrelated service.

## NO_GO without these proofs

- Unknown admin chat ID; bot cannot send a test lead to the Owner.
- Missing production image built from accepted commit / release gate.
- Missing evidence for PostgreSQL/ClickHouse/Redis data restores or cross-namespace dependencies.
- Missing \`DEVOPS_WRITE_PLAN\` with exact resources and matching explicit \`/opsx-devops GO\`.
- Missing post-cutover lead delivery smoke or any outage in MAX, Tiriel, or Stroy.

Status on writing: **implementation draft; no production changes performed**.
