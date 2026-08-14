# T13 — scenario plan evidence current

## Given

Durable CURRENT pair exists:

```text
openspec/changes/<change>/scenario-coverage/plan.md
openspec/changes/<change>/scenario-coverage/plan.receipt.json
```

Receipt: `PLAN_STATUS: ready`, `PLAN_CONTENT_HASH` matches `plan.md`,
`INPUTS.*` hashes match current design/specs. Tasks draft covers the
material scenarios from that exact `PLAN_EVIDENCE_ID`.

## When

Task generation readiness runs (`/opsx-continue` ≡ `/opsx-ff`).

## Expected

```text
SCENARIO_REQUIREMENTS_CONSUMED: yes
SCENARIO_PLAN_EVIDENCE_ID: <receipt PLAN_EVIDENCE_ID>
SCENARIO_PLAN_STATUS: ready
SCENARIO_PLAN_FRESHNESS: current
TASKS_STATUS: READY   # when other readiness pillars also pass
```

## Forbidden

```text
yes without SCENARIO_PLAN_EVIDENCE_ID
yes with mismatched / invented evidence id
consumer writing scenario-coverage artifacts
```
