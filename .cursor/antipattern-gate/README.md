# Antipattern gate

Human front-door: `/opsx-antipattern-gate base=<ref>`.

| Path | Role |
|------|------|
| `catalog.md` | Class ID definitions |
| `PRACTICE_LEDGER.jsonl` | Append-only Owner/agent accept/reject decisions |
| `../commands/opsx-antipattern-gate.md` | Command contract |

## Practice memory

```text
/opsx-antipattern-gate base=stage accept=AP_PROD_TEST_DOUBLE_SNIFF GO
/opsx-antipattern-gate base=stage reject=AP_SOURCE_TOKEN_PROOF GO
```

Ledger is triage memory (`TEMPORARY_SAFETY_NET`), not a replacement for
`.cursor/rules/testing-rules.mdc`. Promote lasting rules separately.
