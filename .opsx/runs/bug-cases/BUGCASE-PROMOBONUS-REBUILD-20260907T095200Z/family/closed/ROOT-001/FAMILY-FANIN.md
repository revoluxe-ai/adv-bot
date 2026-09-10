# Family fan-in: ROOT-001

## Verdict

- FANIN_STATUS: `READY_FOR_FAMILY_CLOSURE`
- FAMILY_STATUS: `FANIN_READY`
- BUG_FAMILY_ID: `BFAM/BUGCASE-PROMOBONUS-REBUILD-20260907T095200Z/ROOT-001/PROMO-OVERLAY-REC-BID`
- INVARIANT_ID: `INV/BUGCASE-PROMOBONUS-REBUILD-20260907T095200Z/ROOT-001/PROMO-OVERLAY-REC-BID`

## Conditions

- Root fixed and green: PASS. `results/GREEN-ROOT-001.md` is `GREEN_CONFIRMED`. Frozen Telegram rec-bid `plan_context` node uses overlay target/max pay when live `promo_fraction > 0`.
- Same-invariant hunt: CLEAR. `results/PROOF-HUNT-BOUNDED-HUNTER-001.md` records `HUNT_RESULT: CLEAR` and `CANDIDATE_COUNT: 0`. Hunter OUT `CANDIDATES=[]`. `findings/` contains only `ROOT-001.md` (no `HUNT-*`). `family/BRANCHES.jsonl` is empty.
- Integration: `PASS_NO_BRANCH_INTEGRATION_REQUIRED`. Family contains only the fixed root finding; no same-invariant branch patch to apply.
- Family-wide green: PASS. Root GREEN evidence plus the CLEAR hunt satisfy the family-wide verification condition. No `FAMILY-GREEN-REPORT.md` was written this hop (not in allowlist); family-wide green is derived from root GREEN + CLEAR hunt.
- Blocking findings: none. `OPEN_SAME_INVARIANT_CANDIDATES=[]`. `SAME_INVARIANT_COUNT=0`.

## Evidence

- `results/GREEN-ROOT-001.md`
- `results/PROOF-HUNT-BOUNDED-HUNTER-001.md`
- `results/TASK-COMPLETION-ROOT-001.md` (`NO_TASK_UPDATE`)
- `team/packets/WEX_BOUNDED_HUNTER_266277452c.out.json` (`CANDIDATES=[]`, `HUNT_RESULT: CLEAR`)
- `team/packets/WEX_GREEN_VERIFIER_c633e1549e.out.json` (`GREEN_STATUS: GREEN_CONFIRMED`)
- `family/INVARIANT.md`
- `family/INVARIANT.json`
- `family/BRANCHES.jsonl` (empty)
- `findings/ROOT-001.md`

Learning and family closure remain separate later hops. This hop does not write `HUMAN_SUMMARY`, `LEARNING_*`, or set `FAMILY_STATUS=CLOSED`.
