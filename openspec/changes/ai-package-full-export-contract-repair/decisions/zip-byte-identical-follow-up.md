# Follow-up defect: byte-identical ZIP (out of scope)

## Status

Proposed follow-up (not implemented in `ai-package-full-export-contract-repair`)

## Context

v1 export contract accepts `PAYLOAD_HASH_ONLY` determinism. Normalizing ZIP
container timestamps/metadata for byte-identical archives is a separate change.

## Decision

Do **not** normalize ZIP bytes in the contract-repair change. Track byte-identical
ZIP as a follow-up defect if product requires it.
