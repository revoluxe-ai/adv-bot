---
cursor:
  subagentId: "bc-5466b72c-9c33-5557-9109-d094d809b6da"
---

# attribution-facts-contract — planning evidence

Planning-only worker output for OPSX feature `attribution-facts-contract`. No repo writes.

## Evidence consulted (bounded)

| Area | Path / artifact |
|------|-----------------|
| Grain / sources | `openspec/decisions/shop-data-source-strategy/decision.md` |
| Orders identity | `openspec/decisions/orders-or-sales-reports-read-identity/decision.md` |
| Audit attribution | `openspec/decisions/strict-single-nmid-audit-evidence/decision.md`, `openspec/specs/strict-single-nmid-read-only-audit/spec.md` |
| Auto/Search legs | `openspec/specs/grain-preservation/spec.md`, `openspec/decisions/billing-fair-leg-metering-write-path/decision.md` |
| AI export boundary | `openspec/decisions/ai-package-v1-exporter-ownership/decision.md` |
| Fullstats loss | `app/core/mp/wb/api/adapter/promotion_client/fullstats/mapper.py`, `app/modules/full_stat_adv_updater/types/full_adv_stat.py` |
| CH campaign stat | `default_db.full_adv_wb_stat` (test DDL), `app/modules/ai_package_v1/sql/campaign_full_stat_by_adv_ids.sql` |
| Script classification | `scripts/wb_a1_associated_conversions.py`, `scripts/a1_strict_read_only_contract_collect.py`, `scripts/strict_single_nmid_audit_owner_bot_plane.py` |
| Multi-window blocker | `origin/cursor/ai-package-multi-window-analysis-34f8` → `openspec/changes/ai-package-multi-window-analysis/design.md` |
| Prior planning | Project store `docs/campaign-attribution-facts-planning.md` |

Deferred catalog (not re-litigated): authoritative endpoint family registry (`prod-adv-bot-strict-read-only-gap` design §Open Questions).

---

## Phase 2 — implementation-ready contract (2026-10-07)

See coordinator RETURN block in turn output. Summary: `PLANNING_READY`, `IMPLEMENTATION_READY: true` for OpenSpec encode; proposed ADR `attribution-facts-collector-ownership` required before Slice B apply.
