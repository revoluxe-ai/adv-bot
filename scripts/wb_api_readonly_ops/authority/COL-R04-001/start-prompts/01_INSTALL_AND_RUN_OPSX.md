# Install + run prompt for existing Owner OpsX control

Use the attached package `COL-R04-001_OPSX_INSTALL_PACKAGE.zip` as the complete non-secret install authority for this task.

TASK: install/upgrade and execute the existing Owner-local OpsX `wb_api_readonly_ops` contour for:

`COL-R04-001 — OWNER_LOCAL_READ_ONLY_PREFLIGHT_R04`

Requirements:
- do not route production cabinet/API access through ChatGPT or Local Cursor;
- credentials/tokens/cookies/session state/raw identifier maps remain Owner-local only and must never appear in ChatGPT-visible artifacts;
- enforce the r04 authority files under `sources/` exactly;
- perform only the NEW r04 cabinet B1 + API read-only preflight;
- POST is allowed only when documented and pre-classified as read-only under the r04 endpoint allowlist rules;
- no PUT/PATCH/DELETE/GraphQL mutation/undocumented POST/business-state mutation;
- do not reuse r03/r03b bytes as PASS evidence;
- fail closed on any mandatory-family, period semantics, timestamp, fingerprint, mutation-risk, secret-safety, or scope blocker;
- do not start mass collection in this run.

Output now, not later:
1. one preflight ZIP named `COL-R04-001_OWNER_LOCAL_READ_ONLY_PREFLIGHT_R04.zip` (or an equivalent unambiguous r04 name);
2. SHA-256 of that ZIP in plain text;
3. concise verdict: `READ_ONLY_PREFLIGHT_PASS` or exact fail-closed blocker;
4. a secret-safety statement confirming that no credential/cookie/token values/browser profiles/raw identifier maps are present in the return package.

Return destination after the preflight package is produced:
https://chatgpt.com/g/g-p-6a6a79c2150481918258d6db0ce5415b-wb-promotion-audit-research-lab/c/6a7588e6-03a8-83ed-a2b8-ecef47c99930
