# Architecture Decision Registry

This directory is the permanent registry for architecture decisions that must
outlive a single OpenSpec change. It is the source of truth for ownership,
layering, write-path placement, and domain invariants that future changes must
respect.

Design files may explain how one change applies a decision, but reusable
architecture decisions belong here.

## Existing Decisions

- [mode-defaults-policy-ownership](mode-defaults-policy-ownership/decision.md)
  - Status: Accepted
  - Scope: ownership and placement of mode-specific defaults for paid, free,
    and common policy overlays.

## Change Requirements

- Every change that touches ownership, layering, write paths, or domain
  invariants must search `openspec/decisions/**/*.md`.
- Relevant decisions must be cited by path from proposal/design artifacts and
  implementation/verification summaries.
- If a relevant decision is missing, create a proposed decision artifact before
  declaring the change implementation-ready.
- Passing tests are not enough when implementation placement conflicts with an
  accepted architecture decision.
