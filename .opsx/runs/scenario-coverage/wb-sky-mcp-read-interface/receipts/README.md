# Provider execution receipts — `wb-sky-mcp-read-interface`

Green `PROVIDER_EXECUTION_RECEIPT` files in this directory are certification
evidence for PostgreSQL boundary scenarios.

Historical ERROR receipts from failed environment setup (e.g. missing Docker)
are **not** certification evidence and must not be rewritten as PASS.

`one_shot_authorization.json` (parent directory) records consumed
`AUTHORIZE_ONE_LIVE_RUN` and is local runtime state, not merge evidence.
