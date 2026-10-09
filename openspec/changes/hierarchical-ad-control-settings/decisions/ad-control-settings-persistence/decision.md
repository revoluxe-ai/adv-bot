# Decision: ad-control-settings-persistence

## Status

Proposed (change `hierarchical-ad-control-settings`, Slice B)

## Context

Slice A delivered pure domain resolver with configured payloads typed in Python.
Owner contract requires separate persistence for configured policy vs derived state;
logical slot identity excludes `schema_version` (row attribute only); JSONB as
representation only.

## Decision

1. **Configured shop/campaign rows** persist in
   `app/modules/ad_control_settings/persistence/` (SQLAlchemy + Alembic).
2. **Logical identity**: shop `(shop_id, feature_id)`; campaign
   `(shop_id, advert_id, feature_id)`. ``schema_version`` is a row attribute only.
3. **INHERIT** at campaign scope = **row absent**; use `campaign.clear_ad_control_feature`.
4. **Monotonic `revision`** (BIGINT) on authoritative rows, allocated from
   `AdControlSlotMutationLedger` (survives CLEAR/recreate); `state_token` is content
   fingerprint only.
5. **Precondition**: `expected_revision=None` => absent slot; `int` => must match row.
6. **ChangeSet** ops: `shop.set_ad_control_feature`, `campaign.set_ad_control_override`,
   `campaign.disable_ad_control_feature`, `campaign.clear_ad_control_feature`.
7. **Idempotency**: bind `compute_ad_control_semantic_digest` to Apply Authority
   `build_idempotency_fingerprint` — no second ledger (runtime Apply unwired in Slice B).
8. Campaign authority in persistence and ChangeSet: `(shop_id, advert_id)`.

## Forbidden

- Storing shop target DRR on campaign rows for INHERIT authority.
- Runtime CPO actuation in Slice B (persistence only; see `drr-cpo-price-semantics` for V1 order-value acceptance on stage).
- Second parallel ChangeSet owner outside `wb_sky_control_plane`.

## Related

- `openspec/decisions/campaign-settings-changeset-ownership/decision.md`
- `openspec/changes/hierarchical-ad-control-settings/decisions/hierarchical-ad-control-settings-ownership/decision.md`
