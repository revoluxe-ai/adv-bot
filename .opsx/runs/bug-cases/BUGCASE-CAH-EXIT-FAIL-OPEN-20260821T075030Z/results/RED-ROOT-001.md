# RED evidence: ROOT-001

- RED status: RED_CONFIRMED
- Test IDs:
  - tests/unit/auto_updater_v3/card_ab_hold/test_exit_rejects_missing_actor.py::test_public_disable_rejects_missing_actor_before_commit[no_from_user]
  - tests/unit/auto_updater_v3/card_ab_hold/test_exit_rejects_missing_actor.py::test_public_disable_rejects_missing_actor_before_commit[id_none]
  - tests/unit/auto_updater_v3/card_ab_hold/test_exit_rejects_missing_actor.py::test_public_disable_rejects_missing_actor_before_commit[id_str]
  - tests/unit/auto_updater_v3/card_ab_hold/test_exit_rejects_missing_actor.py::test_public_disable_rejects_missing_actor_before_commit[id_bool]
- Test content SHA-256: dfecfb3e51d1a771dbe4750f742de6ae0133216b3f0a692981e2cd4dba0a360e
- Command: poetry run pytest -q tests/unit/auto_updater_v3/card_ab_hold/test_exit_rejects_missing_actor.py --tb=line
- Result: 4 failed, 1 warning; exit code 1.
- Invariant: the public EXIT path must fail closed and must not turn card A/B mode OFF when the actor is missing or invalid.
