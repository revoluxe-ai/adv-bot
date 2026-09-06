# Import lineage

Bootstrap donor snapshot:
`opsx-central/sources/unknown/pause-on-empty-keuywords-and-free-on-it`

This directory is documentation-only. Do not drop raw source dumps here.

## Inbound peer OPSX (post-projectization)

To compare or selectively merge OPSX process surfaces from another repo or
extracted archive, use `/opsx-meta-import-command` (contract
`OPSX-WB-META-IMPORT-01`).

Staging and evidence live under `.opsx/runs/inbound/<UTC>/` (`DIFF_PACKET.md`,
`MERGE_RECEIPT.md`). Do **not** stage donor trees in `.opsx/import/`.
Do **not** use this directory as a dump zone for foreign archives.Source OPSX commit: `a71601dba3b9f5cd0076ea7185bdbbe56eaf2e3f`
Raw source inventory lives in the evidence package **outside** this repository
(`raw_source_inventory.ndjson`). Source product changes, archives, WB specs,
and accepted source decisions were **not** copied into the active tree.
`OPSX-GAME-INBOUND-OPSX-01`).
