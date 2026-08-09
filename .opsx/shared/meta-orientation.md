# OPSX meta orientation

Authoritative meta router: `.cursor/commands/opsx-meta.md`  
Top-level PRODUCT/META entry: `.cursor/commands/opsx.md`

## Lanes

```text
/opsx            → PRODUCT | META detection
/opsx-meta       → command-plane orientation (READ_ONLY)
/opsx-meta-*     → concrete meta workers
```

## Write owners (must not chain)

| Command | Writes |
|---|---|
| `/opsx-meta-bootstrap` | Owner-approved `BOOTSTRAP_PROFILE` seed/bind (exempt from projectization gate) |
| `/opsx-meta-commit` | local process surfaces only |
| `/opsx-meta-update-snapshot` | central `sources/<repo>/<branch>/` Git |
| `/opsx-meta-update-index` | central `catalog/` Git |
| `/opsx-meta-import-command` | selected local command packet + lock/activation/provenance |

## Bootstrap

Shared profile: `.opsx/shared/bootstrap-profile.md`  
First-contact (no `.opsx/`): `/opsx-meta-bootstrap` → then `/opsx-projectize`.

## Orientation output

Workers should end with:

```text
ORIENTATION_HINT:
  LANE: META
  STATUS: <token>
  NEXT_META: /opsx-meta
  NEXT_ACTION: <one pasteable /opsx-meta-* or /opsx>
```

## Discovery

Shared discovery schema: `.opsx/shared/command-discovery.md`
