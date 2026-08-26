# Git packaging contract tests

Process-only suite for CONTROL-PLANE COMMAND SIMPLIFICATION slice.

| ID | Command | Assertion |
|----|---------|-----------|
| C01 | opsx-commit | No static-check FULL receipt gate |
| C02 | opsx-commit | Stale receipt does not block |
| C03 | opsx-commit | Missing receipt does not block |
| C04 | opsx-commit | verification FAIL/PENDING allowed |
| C05 | opsx-commit | No ledger COMPLETE gate |
| C06 | opsx-commit | Does not run pytest |
| C07 | opsx-commit | Does not run build |
| C08 | opsx-commit | Does not run static-check |
| C09 | opsx-commit | Does not run browser/security/scenario |
| C10 | opsx-commit | Exact-path git safety preserved |
| C11 | opsx-commit | Unrelated dirt unstaged |
| P12 | opsx-create-pr | No verify PASS prerequisite |
| P13 | opsx-create-pr | No ledger COMPLETE prerequisite |
| P14 | opsx-create-pr | No static-check receipt gate |
| P15 | opsx-create-pr | No quality gate execution |
| P16 | opsx-create-pr | PR at verification PENDING |
| P17 | opsx-create-pr | PR at verification FAIL/ABSENT |
| P18 | opsx-create-pr | PR ≠ merge authorization |
| P19 | integration | verify/archive gates preserved |
| P20 | opsx-commit | No broad git reset |
| P21 | opsx-static-check | Unchanged |
| P22 | opsx-verify | Unchanged |
| P23 | scenario | Unchanged in slice |
| P24 | evidence | Unchanged in slice |
| G25 | GRAPH | No mandatory verify→commit/PR |

Run:

```bash
python .cursor/pipeline/control-plane-tests/run_git_packaging_contract_tests.py
```
