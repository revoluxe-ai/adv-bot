# MERGE_RECEIPT — opsx-meta-bootstrap APPLY step 1

- UTC: 20260812T212312Z
- MODE: APPLY
- APPLY_STEP: 1
- CENTRAL: <CENTRAL>
- CENTRAL_RESOLVE: arg
- REQUIREMENTS_SOURCE: CENTRAL (bootstrap/profile/.opsx/shared/bootstrap-profile.md)
- SOURCE_TREE_COMMANDS: sources/unknown/fix-error-on-stop-auction-on-emptry-active-keywords
- LOCAL_STATE_BEFORE: OPSX_ABSENT

## Actions
- SKIP (TARGET OVERRIDE preserve): .cursor/commands/opsx-meta-bootstrap.md
- NEW: .cursor/commands/opsx-meta-import-command.md ← <CENTRAL>/sources/unknown/fix-error-on-stop-auction-on-emptry-active-keywords/.cursor/commands/opsx-meta-import-command.md
- NEW: .cursor/commands/opsx-projectize.md ← <CENTRAL>/sources/unknown/fix-error-on-stop-auction-on-emptry-active-keywords/.cursor/commands/opsx-projectize.md
- NEW: .cursor/commands/opsx.md ← <CENTRAL>/sources/unknown/fix-error-on-stop-auction-on-emptry-active-keywords/.cursor/commands/opsx.md
- NEW: .cursor/commands/opsx-meta.md ← <CENTRAL>/sources/unknown/fix-error-on-stop-auction-on-emptry-active-keywords/.cursor/commands/opsx-meta.md
- NEW: .opsx/shared/bootstrap-profile.md ← <CENTRAL>/bootstrap/profile/.opsx/shared/bootstrap-profile.md
- NEW: .opsx/shared/meta-orientation.md ← <CENTRAL>/sources/unknown/fix-error-on-stop-auction-on-emptry-active-keywords/.opsx/shared/meta-orientation.md
- NEW: .opsx/shared/command-discovery.md ← <CENTRAL>/sources/unknown/fix-error-on-stop-auction-on-emptry-active-keywords/.opsx/shared/command-discovery.md
- NEW (bind): .opsx/sources.yaml (central_root=<CENTRAL>, repo_family_id=adv-bot)
- NEW (seed REQUIRED): .opsx/projectization.yaml
- NEW (stub): .opsx/lock.yaml
- NEW (stub): .opsx/manifest.yaml (wb-sky-poetry-python / opsx-lite)
- NEW (stub CORE-only): .opsx/registry/command_activation.ndjson
- NEW (stub): .opsx/registry/provenance.ndjson
