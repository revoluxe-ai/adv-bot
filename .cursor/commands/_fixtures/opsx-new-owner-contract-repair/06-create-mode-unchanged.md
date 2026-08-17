# Fixture 06 — T12 CREATE MODE unchanged (backward compatible)

## Given

```text
Input is a normal new-change name or description.
NO OWNER_REVIEW_HANDOFF block.
NO MODE: REPAIR_EXISTING_OWNER_CONTRACT.
Change name does not already exist.
```

## Expected

```text
CREATE MODE (legacy path)
openspec new change "<name>"
write owner-contract.md companion
STOP before schema artifacts
show status + first artifact template
do NOT enter REPAIR MODE from vague phrasing
do NOT require OWNER_REVIEW_HANDOFF for CREATE
```

## Negative variant

```text
Change name already exists AND no REPAIR handoff
→ suggest /opsx:continue
→ do NOT silently REPAIR
→ do NOT recreate scaffold
```
