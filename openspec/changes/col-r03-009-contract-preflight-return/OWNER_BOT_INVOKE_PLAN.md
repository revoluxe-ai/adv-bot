# Owner-bot invoke plan — COL-R03-009 contract_preflight

Apply DoD does **not** require live Job. After green unit + image publish,
Owner runs via `/opsx-scripts` (Owner-bot / vault). Local Cursor → prod API =
FORBIDDEN.

## Pasteable PLAN_RUN / RUN

```text
/opsx-scripts PLAN_RUN script=WB API read-only preflight/collect args=--mode preflight --contract COL-R03-009 --artifact-class contract_preflight --bound-alias WB-TEST-CABINET-001 --period-start 2026-07-04 --period-end 2026-08-02

/opsx-scripts RUN GO script=WB API read-only preflight/collect args=--mode preflight --contract COL-R03-009 --artifact-class contract_preflight --bound-alias WB-TEST-CABINET-001 --period-start 2026-07-04 --period-end 2026-08-02
```

CLI equivalent inside Job (shop_id from Owner vault binding):

```text
python scripts/wb_api_readonly_ops/run.py \
  --shop-id <uuid Owner-local Dilera> \
  --mode preflight \
  --contract COL-R03-009 \
  --artifact-class contract_preflight \
  --bound-alias WB-TEST-CABINET-001 \
  --period-start 2026-07-04 \
  --period-end 2026-08-02 \
  --output-dir <run_outputs>
```

## Expected outputs

- PRIMARY:
  `REQ-WBSKY-AUDIT-METHODOLOGY-V1-PILOT-DATA-COLLECTION-001_COL-R03-009_RETURN.zip`
- Sidecar: same name + `.sha256`
- `report.json` with `ARTIFACT_CLASS=contract_preflight`,
  `PRIMARY_SHA256`, `WEB_COLLECTOR_HANDOFF=YES` only if sha matches
- L0 `wb_readonly_research.zip` — not required; not Web handoff

## After Job

Navigator uploads PRIMARY to Web COLLECTOR. Do **not** upload L0.
