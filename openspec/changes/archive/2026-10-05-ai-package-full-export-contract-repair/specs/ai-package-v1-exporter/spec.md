# Delta — ai-package-v1-exporter

## ADDED Requirements

### Requirement: PACKAGE_SUMMARY.json

The exporter MUST emit root `PACKAGE_SUMMARY.json` included in manifest `files` with sha256. The document MUST include `package_summary_schema_version`, `package_schema_version`, shop identity, requested period, effective coverage, sorted `families` with `canonical_status`, `campaign_identity` with `campaign_id_equals_physical_adv_id: true`, `missing_zero_null`, and `zip_determinism_contract: "PAYLOAD_HASH_ONLY"`.

#### Scenario: Summary in hash set

- **WHEN** a full package ZIP is assembled
- **THEN** `PACKAGE_SUMMARY.json` MUST be listed in manifest files and validated with cards/gaps

### Requirement: Canonical family status

Family status in summary and gap catalog MUST use `COMPLETE|PARTIAL|GAP|UNSUPPORTED|FAILED` only. Shop product orders/sales feed MUST be `GAP`. Current settings MUST be `PARTIAL`. Settings history and change events MUST be `GAP` without collectors.

#### Scenario: Shop feed GAP in summary

- **WHEN** a full package is validated
- **THEN** `shop_product_orders_sales_feed` family `canonical_status` MUST be `GAP` with explicit reasons
