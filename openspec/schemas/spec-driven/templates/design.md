## Context

<!-- Background and current state -->

## Goals / Non-Goals

**Goals:**
<!-- What this design aims to achieve -->

**Non-Goals:**
<!-- What is explicitly out of scope -->

## Architecture Decision References

<!--
List relevant decisions from openspec/decisions/**/*.md by path.
If none exist but ownership/layering/write-path/domain-invariant placement is
needed, write Architecture Decision Missing and describe the proposed decision.
-->

## Ownership & Placement

<!--
Name the owner layer, allowed layers, forbidden layers, and rationale.
Explain how implementation placement matches the cited architecture decisions.
-->

## Decisions

<!--
Key design decisions and rationale.
Implementation-critical architecture (SoT, ownership, write authority,
recovery) MUST be resolved here — never deferred to apply.
See .cursor/pipeline/contracts/DESIGN_GENERATION.md
-->

## Risks / Trade-offs

<!-- Known risks and trade-offs -->

## Migration Plan

<!-- Deployment, rollout, and rollback strategy if applicable -->

## Open Questions

<!--
Allowed: harmless naming only (exact enum/field/helper names) AFTER
state authority, write/recovery contract, and product semantics are fixed.

Forbidden here (keep design BLOCKED instead):
SoT / PG vs Redis / ownership / write authority / epoch-start semantics /
implementation-critical architecture deferred to apply.
See .cursor/pipeline/contracts/DESIGN_GENERATION.md
-->

## Review Checklist

- [ ] existing decisions searched
- [ ] relevant decisions cited
- [ ] new decision proposed if missing
- [ ] implementation layer matches decision
