# Decision: DDL only via migration Job + migrator role

## Status

Proposed

## Context

Application runtime previously shared a privileged DB role. Schema changes must not run from app pods or developer laptops against production.

## Decision

- DDL write-path: Kubernetes migration Job using `app_migrator` (+ optional `SET ROLE app_owner`).
- Object owner: `app_owner` (NOLOGIN).
- Runtime `advupdater`: DML only.
- Control-plane tables owned by `migration_control_owner`; transitions via SECURITY DEFINER functions.
- Production activation requires reconciled APPLICATION baseline and CONTROL baseline.

## Consequences

- Deploy image only after successful migrate Job (or SUCCESS_NOOP) for schema releases.
- Expand–Contract required; Contract only after old images gone.
