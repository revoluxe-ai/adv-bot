# Merge review — lock compliance

- No new collectors or production WB writes.
- `encode.py` ZIP timestamps untouched.
- `zip_determinism_contract` = PAYLOAD_HASH_ONLY; tests compare payload hashes, not archive bytes across differing `generated_at`.
- Gap catalog and summary use canonical enum; shop feed GAP; settings PARTIAL; history/events GAP.
- Keyword join key includes `leg_role` in DATA_MAP, card grain, coverage.

**Independent review:** PASS
