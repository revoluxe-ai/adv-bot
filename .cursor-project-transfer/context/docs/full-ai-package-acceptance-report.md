# Full AI Package — acceptance

Source: [WB Sky — Full AI Package acceptance](bc-0a55fa12-200d-5dfa-b776-987fb4d86f8b). Read-only. Baseline `origin/stage` `23c0671f3`. Product code unchanged. Production writes: none.

Bounded ZIP generated twice via `PackageZipAssembler` fixture seam. Product CLI `scripts/ai_package_v1_export.py` was not run (needs PG/CH).

| Check | Result |
|---|---|
| MANIFEST | PASS |
| DATA_MAP | PASS |
| PACKAGE_SUMMARY | FAIL — file absent; spec has `PACKAGE_FAMILY_GAPS.json` |
| Family status one enum | NO |
| Current settings | PARTIAL |
| Settings history | GAP |
| Change events | GAP |
| Keyword history | PARTIAL |
| Common sales | GAP |
| Campaign advertising | PARTIAL |
| Joinability | FAIL |
| missing ≠ zero | FAIL (only keyword `coverage.json`) |
| Coverage metadata | PASS |
| Determinism | FAIL — ZIP SHA-256 changes across seconds; payload hash matches. `encode_package` stamps `ZipInfo.date_time` |
| AI readability | PARTIAL |

Follow-up, not this hop: root `PACKAGE_SUMMARY.json` (one status enum per family, shop-sales id, `campaign_id` = physical `adv_id`, keyword primary key includes `leg_role`, settings slices labeled current vs history vs change-event, missing≠zero on every family). Do not reopen closed collectors. ZIP timestamp normalization is a separate defect.
