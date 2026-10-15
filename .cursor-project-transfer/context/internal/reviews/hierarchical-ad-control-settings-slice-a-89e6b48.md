---
cursor:
  subagentId: "bc-17138680-dcc0-5391-8e8e-5bb6b1f8b4e9"
---

# Independent review — hierarchical-ad-control-settings Slice A @ 89e6b48

Scope: `app/modules/ad_control_settings/**`, `tests/unit/ad_control_settings/**`, `openspec/changes/hierarchical-ad-control-settings/**`.

Tests: not executed (no `python`/`poetry` on review VM); static review only.

## OVERALL: FAIL

Two HIGH semantics defects block acceptance without repair: (1) product adapter
`Blocked` terminates INHERIT at inactive PRODUCT instead of falling through to
SHOP; (2) headroom eligibility maps any non-hierarchical path to
`NOT_ENROLLED_FAIL_CLOSED`, including `LEGACY_PASSTHROUGH`.

## Findings

### CRITICAL

None (no silent production writes; slice is pure domain).

### HIGH

1. **Product blocked prevents SHOP fallthrough (E, D, N)**  
   `resolver.py:177-189` — `ProductDrrPolicyAdapterBlocked` returns
   `ResolvedFeaturePolicy(active=False)` instead of `None`, so INHERIT never
   reaches shop policy despite comment `CAMPAIGN > PRODUCT > SHOP > SYSTEM`.  
   **Fix:** return `None` from `_resolve_product_tier` on blocked (treat as
   non-applicable product tier); reserve `active=False` + `FEATURE_DISABLED_AT_PRODUCT`
   for explicit product disable when that contract exists.

2. **Legacy path mis-labeled in headroom eligibility (F, G, N)**  
   `headroom_eval.py:100-103` — `hierarchical_active=False` always appends
   `NOT_ENROLLED_FAIL_CLOSED`. For `LEGACY_PASSTHROUGH`, resolver correctly
   emits `LEGACY_PASSTHROUGH_ACTIVE`, but diagnostics eligibility contradicts.  
   **Fix:** pass `control_path` / blocked reason into eligibility; use
   `LEGACY_PASSTHROUGH_ACTIVE` for legacy, `NOT_ENROLLED_FAIL_CLOSED` only for
   `NOT_ENROLLED`.

### MEDIUM

3. **Misleading provenance on adapter block (I)**  
   `resolver.py:184` — `EffectiveSourceKind.PRODUCT_DISABLED` for adapter block;
   reason is `PRODUCT_DRR_ADAPTER_BLOCKED`. Conflates “product feature off” with
   “adapter could not map EffectiveControl”.  
   **Fix:** new `EffectiveSourceKind` or `NOT_APPLICABLE` + correct reason;
   do not use `PRODUCT_DISABLED` unless product tier is explicitly disabled.

4. **Diagnostics incomplete vs contract (N, P)**  
   `diagnostics_builder.py:168-169` — `configured_shop_features` and
   `configured_campaign_overrides` always empty; dynamic resolve `ResolverBlocked`
   adds `blockers` only (`:87`), not `reason_codes`.  
   **Fix:** populate configured slices from context slots; mirror resolver
   reason codes for all blocked features.

5. **Missing precedence tests (E)**  
   No unit test for PRODUCT success over SHOP or blocked→SHOP fallthrough
   (`test_resolver_drr_inheritance.py` covers shop/campaign only).

### LOW

6. **Dead reason codes** — `UNKNOWN_FEATURE`, `HEADROOM_ALLOCATOR_NOT_ACCEPTED`,
   `FEATURE_DISABLED_AT_PRODUCT` defined but unused (`reason_codes.py`).

7. **`min_data_sufficiency: str`** in CPO payloads (`configured.py:39,49`) —
   not tied to `DataSufficiency` enum; invalid strings pass registry validation.

8. **`derive_shop_effective_control_drr` placeholder** (`headroom_eval.py:30-31`)
   — documented baseline; acceptable for Slice A if Owner accepts explicit
   placeholder (L preserved in intent).

### Semantically impossible / inconsistent states

- `PRODUCT_DISABLED` provenance with `PRODUCT_DRR_ADAPTER_BLOCKED` reason (not a
  valid disable semantics).
- Headroom eligibility reason `NOT_ENROLLED_FAIL_CLOSED` while enrollment is
  `ENROLLED` and path is `LEGACY_PASSTHROUGH`.
- Shop `ENABLED` + `payload=None` → `active=False` with `reason_codes=(OK,)`
  (`resolver.py:137-148`) — inactive but OK; document or use distinct reason.

## OWNER_DECISIONS (A–Q)

| ID | Preserved | Notes |
|----|-----------|-------|
| A registry extensibility | yes | `FEATURE_REGISTRY`, `FeatureDefinition`, `configuration_identity` |
| B per-feature scopes | yes | `supported_scopes` per feature |
| C INHERIT/OVERRIDE/DISABLED | partial | Campaign/shop; product via adapter only, no product modes in resolver |
| D live inheritance | yes | Tests + resolver reads live shop slots |
| E precedence | **no** | Product blocked breaks SHOP leg |
| F LEGACY_PASSTHROUGH explicit | partial | Resolver yes; headroom eligibility no |
| G NOT_ENROLLED fail-closed | yes | `assert_hierarchical_path` |
| H campaign (shop_id, advert_id) | yes | `CampaignRef` validation |
| I configured/observed/derived | partial | Types separated; product blocked provenance muddy |
| J Product adapter | yes | `ProductDrrPolicyAdapter` → `EffectiveControlResult` |
| K stale actual_drr | yes | `control_action_allowed` + test |
| L no production allocator | yes | `HeadroomAllocator` protocol only |
| M no price-dependent CPO actuation | yes | `BoundedCpoProposal` withheld + test |
| N diagnostics resolver semantics | partial | Same resolver entry; legacy/eligibility mismatch |
| O unknown fail closed | partial | `FeatureValidationError`; `UNKNOWN_FEATURE` unused |
| P transport independence | yes | Pure domain |
| Q no global automation switch | yes | Per-feature; forbidden in decision |

## Architecture repair before acceptance?

**Yes.** Repair product-tier fallthrough on adapter block and align headroom
eligibility reason codes with enrollment/control path before calling Slice A
accepted for integration slices.
