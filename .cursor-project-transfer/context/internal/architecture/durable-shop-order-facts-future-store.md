---
cursor:
  subagentId: "bc-787c8d26-1c03-557c-acf0-f99bf2b65b62"
---

# Future durable shop-order facts (read-only architecture)

Independent future feature. Not part of `hierarchical-ad-control-settings` or `shop-wide-common-sales-collection`. No OpenSpec, code, migration, or PR in this hop.

Task 4.1 V1 stays a single bounded live read of statistics-api `GET /api/v1/supplier/orders` through `ReportsManager`. This store exists so runtime shop DRR does not depend on that live multi-page read forever.

Canonical family remains supplier orders. No funnel substitution. No campaign-attribution substitution. Collection stays off the advertising-write path.

## Return

RECOMMENDED_STORAGE: ClickHouse append-only observations in `default_db`.

RAW_GRAIN: one `OrdersItem` sighting plus provenance (`shop_id`, endpoint, `collect_run_id`, page cursor, `payload_sha256`, raw JSON).

LOGICAL_IDENTITY: order line `(shop_id, srid)`.

VERSIONING_MODEL: append-only. Latest state is max `lastChangeDate`, then ingest time, then payload hash. Physical key `(shop_id, srid, lastChangeDate, payload_sha256)`.

DEDUPE_MODEL: identical `payload_sha256` is a no-op. A changed body is a new observation. Destructive srid-only upsert is rejected (it erases provenance). Script first-seen-wins is rejected.

CANCELLATION_MODEL: a later sighting may set `isCancel`. Readers exclude cancelled lines from the latest projection. History is kept.

LATE_UPDATE_MODEL: a late price, cancel, or field change is a new observation. Latest projection is recomputed; prior rows stay.

CURSOR_MODEL: one `flag=0` watermark per shop. Next `dateFrom` is the last committed row `lastChangeDate`. The watermark advances only after the batch is durable. Restart does not advance it. Natural end is `NATURAL_EMPTY_PAGE` or `NATURAL_NO_NEXT_CURSOR` only.

BACKFILL_MODEL: a separate job. A later incremental tick does not close historical gaps.

COVERAGE_MODEL: per shop and window: `collection_outcome`, coverage, freshness, `reason_codes`, and gaps are separate. `COMPLETE` only after success, natural cursor end, anchor on or before window start, and no overlapping gap. A non-empty body is not complete. An empty natural scan can be complete.

FRESHNESS_MODEL: separate from coverage. Stale or unknown freshness blocks numeric shop DRR. Freshness does not upgrade incomplete coverage.

RETENTION_MODEL: no TTL until the Owner sets a horizon.

PG_OPTION: poor fit for the append-only fact log (row volume, late revisions, replay).

CH_OPTION: recommended. Qualified `default_db.*`. New tables via `scripts/clickhouse_migrations` and the ClickHouse control plane, not Alembic. Do not reuse `wb_common_stat`.

HYBRID_OPTION: unnecessary. Do not copy every raw row into PostgreSQL.

RECOMMENDED_ARCHITECTURE: one future collector, one shop cursor, ClickHouse observations plus a coverage/gap record and a watermark committed with the successful batch. Consumers use one whole-shop port.

WHY: immutable provenance, deterministic latest state, late cancel and update, idempotent replay, and one fail-closed whole-shop aggregate. Campaign economics stay on `AttributionFactsReader`.

FUTURE_MIGRATION_REQUIREMENTS: new ClickHouse migration for `default_db.supplier_order_observations`, coverage/gaps, and the per-shop watermark. SQL uses `default_db.*`. Not an Alembic revision. Not a reuse of funnel tables.

FUTURE_COLLECTOR_REQUIREMENTS: `ReportsManager.get_supplier_orders`, `flag=0`, shop-wide (not per campaign or nmID), page budget, natural-end proof, separate backfill, restart without watermark advance, off the advertising-write path. Idempotent ingest. Explicit incomplete coverage.

CONSUMER_INTERFACE: `WholeShopSupplierOrderFactsReader.query(shop_id, Europe/Moscow window)` returns lines, `whole_shop_order_gmv_rub` from the latest `priceWithDisc` on non-cancelled lines, coverage, and freshness. Numeric GMV is absent unless coverage is `COMPLETE`, the monetary field is present, and freshness is not stale. Shop DRR, the AI package, and diagnostics share this port. No per-campaign or per-nmID supplier-order read.

OWNER_DECISIONS_REQUIRED:

CRITICAL: none.

HIGH: none.

MEDIUM: retention horizon; staleness SLA; whether full raw JSON is kept; historical backfill floor; inclusive window edge. Srid-only upsert is rejected and is not an open option.

LOW: `flag=1` and script quantity / `gNumber` dedupe stay out of this store.

NO IMPLEMENTATION.
