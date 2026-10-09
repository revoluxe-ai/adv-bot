# ARCHIVE_CLOSE_RECEIPT

```yaml
CHANGE_ID: attribution-facts-contract
ARCHIVED_AT: 2026-10-09
ARCHIVE_PATH: openspec/changes/archive/2026-10-09-attribution-facts-contract
STAGE_MERGE_COMMIT_SLICE_D: 20cb16443
ARCHIVE_VERIFY: GO
PRODUCT_ACCEPTANCE_STATUS: PASS
DEPLOYMENT_PREREQUISITE: ClickHouse migration 008 must be applied via migration control plane under separate production GO before runtime deployment depending on ChAttributionFactsReader / attribution CH tables.
PRODUCTION_CH_MIGRATION_008_APPLIED: NO
```

## Command

```text
npx @fission-ai/openspec@1.6.0 archive attribution-facts-contract -y
```

## Outcome

| Item | Value |
|------|--------|
| Main spec | `openspec/specs/attribution-facts-contract/spec.md` |
| ADR | `openspec/changes/archive/2026-10-09-attribution-facts-contract/decisions/attribution-facts-collector-ownership/decision.md` |
| Full certify receipt | `scenario-coverage/certify.receipt.json` |
| Slice D cert subject | `5baf182f329665d995eccc729548f480eece021f` |
