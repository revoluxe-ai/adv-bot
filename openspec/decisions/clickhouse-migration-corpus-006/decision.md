# Decision: Reviewed ClickHouse migration 006 extends the canonical corpus

## Status

Accepted

## Context

The accepted ClickHouse migration lifecycle decision established an immutable reviewed corpus `001`–`005`, explicitly kept an unrelated/unreviewed `006` out, and allowed schema execution only for reviewed schema DDL `001`–`004`. Campaign settings history now requires one new ClickHouse table. Adding its DDL outside that control plane would violate the accepted migration ownership rule.

## Decision

The migration lifecycle remains owned by the existing ClickHouse migration control plane. This change reviews one new immutable version `006_create_campaign_settings_history.sql` and extends the canonical corpus from `001`–`005` to `001`–`006`.

`006` is ordinary schema DDL for `default_db.campaign_settings_history`. It is eligible for the same isolated-target schema writer and the same checksum, baseline, authorization, coordinator-lock, statement-event, partial-state, and production-refusal gates as `001`–`004`.

`005` remains a privileged GRANT and MUST NOT enter the schema writer. No privileged writer is added.

The old rule "missing 006 stays out" is superseded only for this exact reviewed `006` and its accepted raw-byte SHA-256. Every numeric prefix outside the reviewed corpus remains unreviewed and fail-closed. Future `007+` versions require another reviewed change; dropping a file into the directory never extends the corpus by itself.

## Applies to

- `clickhouse-migration-lifecycle` canonical corpus and fingerprint.
- The schema-writer eligibility set.
- The new campaign settings history table migration.

## Allowed

- Add exactly reviewed `006` with `default_db` qualification.
- Update corpus fingerprints/tests from `001`–`005` to `001`–`006`.
- Apply `006` only on an isolated target under all existing gates.

## Forbidden

- Ad-hoc CREATE TABLE from application startup or history collector.
- Auto-discovery that accepts any numeric SQL file without review.
- Sending `005` through the schema writer.
- Using production apply as acceptance evidence for this change.

## Examples

Good: control-plane validate recognizes the exact `006` hash and isolated apply records normal statement events.

Bad: history service starts and runs CREATE TABLE IF NOT EXISTS itself.

## Related specs

- `openspec/changes/campaign-settings-history/specs/clickhouse-migration-lifecycle/spec.md`
- `openspec/changes/campaign-settings-history/specs/campaign-settings-history/spec.md`

## Related changes

- `openspec/changes/campaign-settings-history`

## Review checklist

- [x] existing decisions searched
- [x] relevant decisions cited
- [x] new decision proposed because accepted decision's exact corpus is being extended
- [x] implementation layer matches decision
