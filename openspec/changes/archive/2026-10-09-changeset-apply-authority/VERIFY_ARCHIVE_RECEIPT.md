# VERIFY_ARCHIVE_RECEIPT

```yaml
CHANGE_ID: changeset-apply-authority
MODE: archive
OWNER_SCOPE_DECISION: OPTION_A_PG_ONLY_V1
ARCHIVE_VERIFY: GO
PRODUCT_ACCEPTANCE_STATUS: PASS
PRODUCT_ACCEPTANCE_REQUIRED: true
STAGE_HEAD: c9fdf9ce1a00a70d8535877ef618229d48754fca
```

## Verdict

**GO** — PG-only V1 docs reconciled; normative delta excludes S10/S11/S15/S16;
change-level `certify.receipt.json` PASS_SCOPE=V1_PG_ONLY; ADR promoted.

## PRODUCT_ACCEPTANCE

| Pillar | Verdict |
|--------|---------|
| MEANING_LOCK | PASS — `changeset-apply-authority-ownership` RESOLVED PG-only |
| LIFECYCLE_COVERAGE | PASS — 29/29 V1 scenarios PASS; 4 MOVED; 2 N/A |
| SIDE_EFFECT_PROOF | PASS — disposable PG apply integration (34 tests) |

## Tests (this verify)

- Unit wb_sky + apply: PASS
- Integration apply destructive_local: 34 PASS (incl. S22)
- Alembic head: `f9c0a1b2d3e4`
- Ruff apply paths: PASS
- `npx openspec validate changeset-apply-authority --strict`: PASS
