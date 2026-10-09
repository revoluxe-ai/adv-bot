# Decision: ad-control-settings-persistence

## Status

Proposed (change `hierarchical-ad-control-settings`, Slice B)

## Context

Slice A delivered pure domain resolver with configured payloads typed in Python.
Owner contract requires separate persistence for configured policy vs derived state,
identity `(scope, feature_id, schema_version)`, JSONB as representation only.

## Decision

1. **Configured shop/campaign rows** persist in
   `app/modules/ad_control_settings/persistence/` (SQLAlchemy + Alembic).
2. **PRODUCT** scope remains adapter-only; no new ProductControl tables.
3. **ChangeSet** for mutations: `AdControlChangeSetV1` in `wb_sky_control_plane`
   with dry-run validator `validate_ad_control_changeset` — no production PG writes
   in validator (Apply Authority wiring = later slice).
4. Campaign authority in persistence and ChangeSet: `(shop_id, advert_id)`.

## Forbidden

- Storing shop target DRR on campaign rows for INHERIT authority.
- CPO production actuation paths while `PRICE_SEMANTICS_ACCEPTED = NO`.
- Second parallel ChangeSet owner outside `wb_sky_control_plane`.

## Related

- `openspec/decisions/campaign-settings-changeset-ownership/decision.md`
- `openspec/changes/hierarchical-ad-control-settings/decisions/hierarchical-ad-control-settings-ownership/decision.md`
