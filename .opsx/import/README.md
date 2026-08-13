# Import lineage

Bootstrap donor snapshot:
`opsx-central/sources/unknown/pause-on-empty-keuywords-and-free-on-it`

This directory is documentation-only. Do not drop raw source dumps here.

## Inbound peer OPSX (post-projectization)

To compare or selectively merge OPSX process surfaces from another repo or
extracted archive, use `/opsx-meta-import-command` (contract
`OPSX-WB-META-IMPORT-01`).

Staging and evidence live under `.tmp/opsx-inbound/<UTC>/` (`DIFF_PACKET.md`,
`MERGE_RECEIPT.md`). Do **not** stage donor trees in `.opsx/import/`.
Do **not** use this directory as a dump zone for foreign archives.
