# R9 — regression sample: auto-shelf-exhausted-pause-retest

## Pointer (do not edit product artifacts in this fix)

```text
openspec/changes/auto-shelf-exhausted-pause-retest/
```

Historical generator defects observed in that Change’s `design.md`:

```text
Точная схема PG/Redis — apply-time
Минимальный PG vs Redis для нашего block — выбрать в apply
Activity-control MAY start Auto только если нет других blockers
```

## When

New design generator (continue or ff) regenerates design for equivalent
upstream semantics.

## Expected

Either:

### A — resolve

```text
DESIGN_STATUS: READY
chosen durable SoT + owner + write/read/recovery + rationale
Auto MUST start when our block clear AND no other blockers
MUST NOT force-start when other blockers remain
new epoch MUST begin only after actual Auto start
```

or:

### B — block

```text
DESIGN_STATUS: BLOCKED
REASON: TECHNICAL_DESIGN_UNRESOLVED
```

if evidence truly insufficient.

## Forbidden

```text
DESIGN_STATUS: READY
+ PG/Redis / SoT deferred to apply
+ MUST start weakened to MAY start
```

## Note

This fixture does **not** authorize editing the product `design.md` as
part of `/opsx-meta-fix-command-defects`. Regenerate later via
`/opsx-update` or continue/ff after the gate exists.
