# Tasks — ai-package-campaign-settings-snapshot

Planning artifact. Implementation via `/opsx-apply` after owner-contract review
and planning package coherent. Tests-first; slice 1 isolated from dirty A1 overlap.

```text
TASKS_STATUS: READY_FOR_MERGE_REVIEW
TASKS_CHECKED: 23/29 (§0.1–§0.3, §1–§3, §6.1–§6.2 complete; §4–§5 optional open; §6.3 ADR separate)
PLANNING_READY: yes
APPLY_READY: yes
APPLY_PLANNING_GATE: PASS (independent `/opsx-planning-review change=ai-package-campaign-settings-snapshot`
  task WB-SKY-AIPKG-CAMPAIGN-SNAPSHOT-PLANNING-REVIEW-20261004-0022; 2026-10-04)
PLANNING_REVIEW_STATUS: PASS (independent 2026-10-04; task WB-SKY-AIPKG-CAMPAIGN-SNAPSHOT-PLANNING-REVIEW-20261004-0022)
PLANNING_REVIEW_PILLARS: PASS (APPLY_PLANNING_GATE PASS; no blocking findings)
OWNER_CONTRACT_STATUS: REVIEWED (owner-contract-review PASS 2026-10-04;
  task WB-SKY-AIPKG-CAMPAIGN-SNAPSHOT-OWNER-REVIEW-20261004-0018; D-001..D-003)
OPSX_VERIFY_STATUS: IMPL_OK (2026-10-04; `/opsx-verify mode=impl` task
  WB-SKY-AIPKG-CAMPAIGN-SNAPSHOT-VERIFY-IMPL-20261004-0030; merge-review gate only — not archive authorization)
OPEN_ITEMS: OPEN-01..OPEN-04 (design.md; OPEN-01 narrowed via PG UNKNOWN/PARTIAL in §2.4)
A1_DEPENDENCY: slice 1 none; slice 2 optional after A1 normalizer extract lands (§4 not started)
```

## LEGACY_BASELINE

- v1 exporter spec: `campaign_settings_snapshot` = minimal PG inventory only.
- Repo has `AdvSettingsSnapshotDTO`, `CampaignResourceSnapshotV1`, A1 normalizer —
  none are AI export contract (see proposed ADR).
- `app/modules/ai_package_v1/` may be partial/absent in branch — slice 0 verifies.

## TARGET_REGRESSION

- Must not alias A1 or Redis DTOs as export payload.
- Must not merge Auto/Search legs.
- Must not invoke WB API or snapshot_data_updater scope on export path.
- Must not mutate PG/Redis/bot_active from export.

## FINAL_ACCEPTANCE

- `CampaignSettingsSnapshotV1` golden fixtures + contract tests pass under
  `poetry run pytest -m unit tests/unit/ai_package_v1/`.
- `openspec validate ai-package-campaign-settings-snapshot --type change --strict` passes.
- Manifest card declares detailed settings semantics; four completeness dimensions present.
- OPEN-01..OPEN-02 either closed by discovery tasks or remain explicit PARTIAL/UNKNOWN in export.

---

## 0. Planning gates (this change)

- [x] 0.1 Scaffold change + proposal, owner-contract, design, specs, ADR, tasks
- [x] 0.2 `/opsx-owner-contract-review change=ai-package-campaign-settings-snapshot`
      (PASS 2026-10-04; task WB-SKY-AIPKG-CAMPAIGN-SNAPSHOT-OWNER-REVIEW-20261004-0018)
- [x] 0.3 `/opsx-planning-review change=ai-package-campaign-settings-snapshot` (independent)
      (PASS 2026-10-04; APPLY_PLANNING_GATE PASS;
      task WB-SKY-AIPKG-CAMPAIGN-SNAPSHOT-PLANNING-REVIEW-20261004-0022)
- [ ] 0.4 §0.3 `openspec_guard.yaml` debt — **out of scope** (never waive in this change)

---

## 1. Discovery and contract skeleton (apply slice 0 — no A1 dependency)

- [x] 1.1 Verify `app/modules/ai_package_v1/` baseline from archived v1 contract apply
      (or land minimal scaffold if missing) — **read-only module only**
- [x] 1.2 **OPEN-02 discovery:** produce allowlisted LOCAL_POLICY + INVENTORY +
      WB-sync PG column list from `AdvSetting` with authority_class tags (design matrix
      update in apply notes; no fabricated WB fields)
- [x] 1.3 Add `domain/campaign_settings_snapshot_v1.py` — Pydantic/dataclass contract:
      `schema_version`, `shop_id`, `snapshot_assembled_at`, `records[]`, card-level
      completeness block, leg enums, provenance types
- [x] 1.4 Unit tests: schema validation, leg nesting, UNKNOWN/null serialization rules

---

## 2. PG read path (apply slice 1 — isolated from A1)

- [x] 2.1 Implement `readers/pg_campaign_settings_reader.py` — read-only session,
      scope = v1 inventory query (`active_status != done`, `only_bot_active=False`)
- [x] 2.2 Implement `export/campaign_settings_assembler.py` — map PG columns to
      contract fields with `field_provenance`; PG NULL → JSON null
- [x] 2.3 Wire manifest card builder: `detailed_settings_export: true`, payload file +
      sha256; keep transport decoupled
- [x] 2.4 **OPEN-01:** mark WB-authoritative fields beyond PG sync as UNKNOWN/PARTIAL
      with `reason_codes` — no live WB fetch
- [x] 2.5 Contract tests (delta spec):
      - Auto/Search legs distinguishable
      - No WB API spy calls on settings path
      - Non-aliasing vs `CampaignResourceSnapshotV1` / `AdvSettingsSnapshotDTO`
      - Fail-closed UNKNOWN fixtures

---

## 3. Exporter integration (depends on §2)

- [x] 3.1 Integrate assembler into `ExportService` / manifest orchestration
- [x] 3.2 Update validator for `CampaignSettingsSnapshotV1` required fields + provenance
- [x] 3.3 Golden ZIP fixture with detailed settings payload; deterministic hash test
- [x] 3.4 Regression: other dataset cards unchanged; shop isolation preserved

---

## 4. Optional shared normalizer extract (apply slice 2 — **depends on A1 landing**)

- [ ] 4.1 Gate: A1 `normalize_wb_campaign_leg` stable + no import cycle with apply path
- [ ] 4.2 Extract read-only normalizer to shared module consumed by `ai_package_v1`
      (copy-first acceptable; control-plane imports forbidden on default export path)
- [ ] 4.3 Populate additional WB_AUTHORITATIVE leg fields from accumulated evidence only
- [ ] 4.4 Close or narrow OPEN-01; update provenance and coverage claims accordingly

---

## 5. Optional registry cross-ref (non-blocking — OPEN-03)

- [ ] 5.1 When `WbSkyCampaignResourceRegistry` row exists, attach optional `a1_resource_id`
      metadata on export record — never required for export success
- [ ] 5.2 Contract test: export succeeds without registry rows (`A1_REGISTRY_GAP` non-fatal)

---

## 6. Documentation and verify boundary

- [x] 6.1 Module docstrings (RU) for new public readers/assembler/domain types
- [x] 6.2 `/opsx-verify change=ai-package-campaign-settings-snapshot mode=impl`
      (implementation verify / merge-review gate PASS 2026-10-04;
      task WB-SKY-AIPKG-CAMPAIGN-SNAPSHOT-VERIFY-IMPL-20261004-0030; not archive authorization)
- [ ] 6.3 Promote proposed ADR to Accepted registry — **separate Owner change** (not this hop)

---

## Explicitly not tasked here

- WB API accumulation of full settings into PG (future accumulation change).
- Keyword-level settings in this card (OPEN-04 out of scope).
- Control-plane apply/resolver/registry writes.
- snapshot_data_updater / Redis schema changes.
- Alembic migrations.
- Canonical spec promotion / `openspec/decisions/index.md` edits.
