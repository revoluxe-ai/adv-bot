# JOB_EVIDENCE_PLAN — INC-RO-07 (prepare only; no cluster mutate)

Owner must authorize `/opsx-scripts RUN GO` separately.

```text
SCRIPTS_RUN_PLAN (draft):
SCRIPT_TITLE: WB API read-only preflight/collect
SCRIPT_PATH: scripts/wb_api_readonly_ops/run.py
SCRIPT_DISPLAY: WB API read-only preflight/collect (scripts/wb_api_readonly_ops/run.py)
MODE: collect
ARGS: --shop-id <Dilera-or-Owner> --mode collect
NS: (from k8s/jobs/ops-script-runner.yaml)
TEMPLATE_PATH: k8s/jobs/ops-script-runner.yaml
KNOWN_OUTPUTS: report + L0 archive (secret-strip)
DoD_CHECK:
- Job successful terminal on prod Owner-bot contour
- Archive has non-empty ORDERS and/or sales rows from Stage A Reports stack
- Ledger updated from evidence
- Empty ORDERS+sales → retry dateFrom/shop_id; do not close INC-RO-07
PASTEABLE:
/opsx-scripts PLAN_RUN script=WB API read-only preflight/collect args=--shop-id <id> --mode collect
/opsx-scripts RUN GO script=WB API read-only preflight/collect args=--shop-id <id> --mode collect
```
