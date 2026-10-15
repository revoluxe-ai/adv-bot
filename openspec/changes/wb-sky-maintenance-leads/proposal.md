# Proposal: WB Sky maintenance lead intake and resource pause

## Problem
WB Sky no longer has paying users. The advertising engine, campaign updates, metrics collectors and three data services still consume a Kubernetes worker plus billable network volumes. Existing customers must be routed to a contact request with mandatory phone, not exposed to an inactive advertising control plane.

## Proposed change
- A separate standard-library Telegram polling entrypoint, reusing the existing bot identity, displays an exclusive maintenance notice and collects a validated phone number.
- The configured admin chat receives the phone and sender details before the user sees success.
- Legacy buttons do not invoke old feature handlers.
- After confirmed on-production smoke, the old ad-specific Deployments can be scaled down through OPSX DevOps.
- Redis, ClickHouse and PostgreSQL are retained until dependency and recoverable backup proof; PVC removal and node resizing require separately scoped reversible operations.

## Tradeoffs
- Telegram API delivery is used as the acknowledgment boundary, no extra database. If the API reports success but the process fails before recording the update offset, the admin may receive a duplicate lead; its update ID enables detection.
- A single running replica and Recreate strategy avoid competing getUpdates consumers.
- The first iteration can reuse the built application image with a different process entrypoint; a minimal container image is a later optimization, not a reason to delay safe cutover.

## Success criterion
A live contact and manually entered phone both reach the Owner, no ads can be modified, and verified billable infrastructure is reduced without impacting unrelated projects or destroying recovery assets.
