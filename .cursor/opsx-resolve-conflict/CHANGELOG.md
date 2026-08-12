# Changelog — OPSX_RESOLVE_CONFLICT_COMMAND_001

## 0.40.0 (R40) — independent review candidate

Author: **Cursor**

### Closure targeting BUGBOT-HIGH-002 (single-path PREVIEW contract)

- One PREVIEW invocation analyzes exactly one conflicted path
- Multiple unmerged paths without `--path` → typed STOP
  `PREVIEW_PATH_REQUIRED_MULTIPLE_CONFLICTS` with sorted inventory
- Successful report binds path / `paths_analyzed` / reasoning / evidence /
  recommendation to the selected path only
- `unmerged_paths_inventory` / `all_unmerged_paths` labeled inventory-only
- R34 `preview_readonly_git.py` remains byte-identical
- R37 `preview_context.py` remains byte-identical
- GO_CAPABILITY=false; SAFE_USAGE_SCOPE=PREVIEW_ONLY

### Deferred (unchanged)

- BUGBOT-HIGH-001 (commit routing ownership for `.cursor/opsx-resolve-conflict/**`)
- BUGBOT-MEDIUM-001 (stale `_preview_all.json`)
- BUGBOT-MEDIUM-002 (`process_surfaces.json` path gaps)
- R33-GATE-PROCESS-002
- R25-MEDIUM-002 / R25-PROCESS-001

## 0.39.0 (R39) — independent review candidate

Author: **Cursor**

### Closure targeting R38-GATE-PROCESS-001 (PREVIEW evidence path sanitization)

- Tokenize trusted-Git executable paths to `<TRUSTED_GIT_EXECUTABLE>` in shipped evidence
- Recursive JSON string-value path scan (closes R38 JSON-escaping validator bypass)
- Preserve expected/observed executable digests + `atomicity_claim=false`
- Rebuild real merge/rebase PREVIEW evidence without author-profile paths
- R37 preview runtime hashes remain byte-identical
- GO_CAPABILITY=false; SAFE_USAGE_SCOPE=PREVIEW_ONLY

### Deferred (unchanged)

- R33-GATE-PROCESS-002
- R25-MEDIUM-002 / R25-PROCESS-001

## 0.38.0 (R38) — independent review candidate

Author: **Cursor**

### Closure targeting R33-GATE-PROCESS-001 (immutable PREVIEW evidence)

- Ship real merge + rebase PREVIEW execution evidence in the review bundle
- Evidence generated from packaged ZIP runtime (`boot_opsx_conflict.py preview`)
- FIXTURE_SETUP ledger separated from PREVIEW command_ledger (R34 read-only ops)
- Before/after digests prove conflict state immutability under PREVIEW
- Post-build validator requires both evidence artifacts + digest binding
- R37 preview runtime hashes remain byte-identical
- GO_CAPABILITY=false; SAFE_USAGE_SCOPE=PREVIEW_ONLY

### Deferred (unchanged)

- R33-GATE-PROCESS-002
- R25-MEDIUM-002 / R25-PROCESS-001

## 0.37.0 (R37) — independent review candidate

Author: **Cursor**

### Closure targeting R36-GATE-AUTHORITY-002 (contract lifecycle precedence)

- CONTRACT verification evaluates explicit lifecycle **before** normative marker
- Explicit non-active lifecycle (`draft`/`proposed`/`rejected`/`superseded`/`unknown`/other) → `authority_verified=false`
- Accepted/active/current + canonical + normative marker may still verify
- No-status canonical normative contract behavior unchanged
- Unverified contracts excluded from `_strong_evidence` / RECOMMENDATION
- R34 `preview_readonly_git.py` remains byte-identical
- GO_CAPABILITY=false; SAFE_USAGE_SCOPE=PREVIEW_ONLY

### Deferred (unchanged)

- R33-GATE-PROCESS-001 / R33-GATE-PROCESS-002
- R25-MEDIUM-002 / R25-PROCESS-001

## 0.36.0 (R36) — independent review candidate

Author: **Cursor**

### Closure targeting R35-GATE-AUTHORITY-001 (proven authority)

- Separated provisional `authority_class` from `authority_verified` / `authority_basis`
- ACCEPTED_DECISION verified only with explicit `status: accepted` (+ index consistency)
- draft/proposed/rejected/superseded decisions never verify
- Change-local specs → `CHANGE_CONTEXT` (non-normative)
- Arbitrary `*contract*.md` not verified; canonical `openspec/contracts/` + marker only
- RECOMMENDATION uses only `authority_verified=true` strong classes
- Contradictory verified authorities → RECOMMENDATION=null
- Decision/spec discovery consumes bounded-reader budgets (no unbounded rglob)
- R34 `preview_readonly_git.py` remains byte-identical
- GO_CAPABILITY=false; SAFE_USAGE_SCOPE=PREVIEW_ONLY

### Deferred (unchanged)

- R33-GATE-PROCESS-001 / R33-GATE-PROCESS-002
- R25-MEDIUM-002 / R25-PROCESS-001

## 0.35.0 (R35) — independent review candidate

Author: **Cursor**

### Closure targeting R33-GATE-HIGH-002 (repository-context assistant)

- Split PREVIEW into evidence layer (`preview_context.py`) + advisory reasoning
- Bounded read-only context reader (no shell/rg; symlink/escape STOP; budgets)
- Authority-classified evidence (decisions/specs/tests/siblings/source)
- Removed unsafe textual-subset → keep_ours/keep_theirs heuristic
- Recommendation only from strong authority; else RECOMMENDATION=null + Owner Q
- Russian human report leads with behavioral disagreement, not OIDs
- R34 `preview_readonly_git.py` remains byte-identical
- GO_CAPABILITY=false; SAFE_USAGE_SCOPE=PREVIEW_ONLY

### Deferred (unchanged)

- R33-GATE-PROCESS-001 / R33-GATE-PROCESS-002
- R25-MEDIUM-002 / R25-PROCESS-001

## 0.34.0 (R34) — independent review candidate

Author: **Cursor**

### Closure targeting R33-GATE-HIGH-001 (PREVIEW read-only Git boundary)

- Replaced broad Git verb allowlist with exact operation IDs only:
  `resolve_git_dir`, `resolve_head`, `read_refs`, `read_unmerged_index`,
  `read_stage_blob`
- Each operation compiles to fixed argv; no public arbitrary `git_args`
- Removed preview capability for `config`, `symbolic-ref`, `diff`, `show`,
  `merge-base`, `status`
- Blob OID validation (full hex SHA-1/SHA-256 only; no revision expressions)
- Preview consumes package `resolve_trusted_git` / `git_safe_env` without
  modifying `git_typed.py`; no silent PATH Git fallback
- Sealed environment strips location/config redirect ambient variables
- Command ledger records operation ID, argv, exe path, expected/observed
  digests, sealed-env policy version, rc, stdout/stderr digests
- Explicit: no atomic verify-to-spawn claim; **R25-MEDIUM-002 remains open**
- GO_CAPABILITY=false

### Deferred (unchanged)

- R33-GATE-HIGH-002 (weak semantic recommendation)
- R33-GATE-PROCESS-001 / R33-GATE-PROCESS-002

## 0.33.0 (R33) — independent review candidate

Author: **Cursor**

### ADR-OPSX-RC-PLATFORM-001 / WINDOWS_PREVIEW_ONLY

- Windows is the only supported platform; Linux/macOS UNSUPPORTED
- Operational scope: PREVIEW_ONLY advisory conflict analysis
- Read-only Git allowlist + stage 1/2/3 preview report (RU + JSON)
- Missing authority producer / OS_VERIFIED sandbox → LIMITATIONS, not STOP
- Non-Windows CLI fails closed with `UNSUPPORTED_PLATFORM` before repo Git
- Platform matrix: windows `PREVIEW_ONLY_VERIFIED`; sealed in immutable bundle
- `git_typed` / validation / trust-store GO architecture remain frozen
- GO_CAPABILITY=false

### Explicit open findings (full disclosure)

1. BLOCKER_AUTHORITY_PRODUCER_MISSING
2. BLOCKER_OS_SANDBOX_RUNNER_MISSING
3. R25-MEDIUM-002 trusted-Git execution boundary (not claimed atomic)
4. R25-PROCESS-001

Architect-closed pending reviewer confirmation: R25-HIGH-001/002/003,
R25-MEDIUM-001, R25-MEDIUM-003, R25-MEDIUM-004 (Windows PREVIEW_ONLY).

## 0.32.0 (R32) — independent review candidate

Author: **Cursor**

### Closures targeting R25-MEDIUM-004 (process portability)

- Native artifact workspace via `tempfile.gettempdir()` / `OPSX_REVIEW_OUT_DIR`
- Path-flavor separation: native I/O vs normalized evidence vs Pure* synthetics
- Shipping/replay scripts no longer hardcode `Path(r"C:\\Temp")` for filesystem I/O
- R31 POSIX symlink fixture no longer recurses through patched `os.lstat`
- Platform capability matrix with Windows/Linux evidence; macOS `NOT_VERIFIED`
- Post-build validator rejects mixed-separator / foreign-path shipping I/O
- GO_CAPABILITY=false

### Explicit open findings (full disclosure)

1. BLOCKER_AUTHORITY_PRODUCER_MISSING
2. BLOCKER_OS_SANDBOX_RUNNER_MISSING
3. R25-MEDIUM-002 trusted-Git execution boundary (not claimed atomic)
4. R25-PROCESS-001

Architect-closed pending reviewer confirmation: R25-HIGH-001/002/003,
R25-MEDIUM-001, R25-MEDIUM-003, R25-MEDIUM-004.

## 0.31.0 (R31) — independent review candidate

Author: **Cursor**

### Closures targeting R25-MEDIUM-003 (AccessCheck correctness)

- Windows effective rights collected per forbidden right (no combined
  all-or-nothing AccessCheck)
- Drive/volume root included in fail-closed DACL/owner verification
- DACL-specific tests pass owner gate before asserting DACL reasons
- Deterministic AccessCheck seam for per-right negative matrix
- GO_CAPABILITY=false

### Explicit open findings (full disclosure)

1. BLOCKER_AUTHORITY_PRODUCER_MISSING
2. BLOCKER_OS_SANDBOX_RUNNER_MISSING
3. R25-MEDIUM-002 trusted-Git execution boundary (not claimed atomic)
4. R25-MEDIUM-004
5. R25-PROCESS-001

Architect-closed pending reviewer confirmation: R25-HIGH-001/002/003,
R25-MEDIUM-001, R25-MEDIUM-003.

## 0.30.0 (R30) — independent review candidate

Author: **Cursor**

### Closures targeting R25-MEDIUM-003

- OS trust-store component-by-component no-follow / no-reparse walk
- Installer-owned owner + POSIX mode / Windows DACL checks (agent must lack
  write/delete/DAC/owner rights on key and parents)
- Key bytes read from stable OS handle held through producer signature verify
- Identity recheck before verify and close; typed STOP reasons for drift/ACL
- `FILE_ATTRIBUTE_READONLY` / final-file mode alone is not a trust boundary
- GO_CAPABILITY=false

### Explicit open findings (full disclosure)

1. BLOCKER_AUTHORITY_PRODUCER_MISSING
2. BLOCKER_OS_SANDBOX_RUNNER_MISSING
3. R25-MEDIUM-002 trusted-Git execution boundary (not claimed atomic)
4. R25-MEDIUM-004
5. R25-PROCESS-001 pack/commit membership
6. Cross-platform shipping/home-path finding (out of R30 scope)

Architect-closed pending reviewer confirmation: R25-HIGH-001/002/003,
R25-MEDIUM-001, R25-MEDIUM-003.

## 0.29.0 (R29) — independent review candidate

Author: **Cursor**

### Closures targeting R25-MEDIUM-001

- Replay acceptance is exact-match AND (exit, status, STOP reason, operation,
  gate, Git immutability); nonzero exit alone never PASS
- `state` cases prove merge vs rebase detection with real stage OIDs
- Scoped `go` cases terminate at `PACKAGE_GO_CAPABILITY_DISABLED` with structured
  CLI STOP envelope (no traceback for typed StopRequired)
- Builder fails closed and does not emit final replay ZIP on assertion mismatch
- GO_CAPABILITY=false

### Explicit open findings (full disclosure)

1. BLOCKER_AUTHORITY_PRODUCER_MISSING
2. BLOCKER_OS_SANDBOX_RUNNER_MISSING
3. R25-MEDIUM-002 trusted-Git execution boundary (not claimed atomic)
4. R25-PROCESS-001 pack/commit membership
5. Cross-platform shipping/home-path finding (out of R29 scope)

## 0.28.0 (R28) — independent review candidate

Author: **Cursor**

### Closures targeting R25-HIGH-003

- FULL registry compilation uses actual OPSX `task_type` + `pack` (no `execution` field)
- Closed package-owned typed adapter table supplies exact argv / timeouts / success codes
- Pack trees are hash-bound contract identity only (never executed / never argv source)
- Four pack inventories frozen in host contracts (context.md + instructions.md)
- GO_CAPABILITY=false

### Explicit open blockers

1. BLOCKER_AUTHORITY_PRODUCER_MISSING
2. BLOCKER_OS_SANDBOX_RUNNER_MISSING

## 0.27.0 (R27) — independent review candidate

Author: **Cursor**

### Closures targeting R25-HIGH-002

- Authority declaration v5 requires authenticated capability evidence in the signed payload
- Producer issuer bindings must authorize role `capability_attestor` for completeness
- Exact path/stage/blob_oid stage_coverage; analysis_complete=true; empty unknown_targets
- Local AST symbol→capability_bindings mapping is diagnostic only
- Legacy v4 declarations rejected (no silent compatibility path)
- GO_CAPABILITY=false

### Explicit open blockers

1. BLOCKER_AUTHORITY_PRODUCER_MISSING
2. BLOCKER_OS_SANDBOX_RUNNER_MISSING

## 0.26.0 (R26) — independent review candidate

Author: **Cursor**

### Closures targeting R25-HIGH-001

- Authority declaration v4 requires issuer-key Ed25519 signature over canonical payload
- Authenticated producer binds issuer ID to key_id + public key
- Legacy unsigned v3 declarations rejected in strict/GO authority flow
- GO_CAPABILITY=false

### Explicit open blockers

1. BLOCKER_AUTHORITY_PRODUCER_MISSING
2. BLOCKER_OS_SANDBOX_RUNNER_MISSING

## 0.25.0 (R25) — independent review candidate

Author: **Cursor**

### Closures targeting R24 evidence defects

- Inner operator docs (including README_REVIEW) omit current-delivery archive hashes/test totals
- Post-build validator scans all operator/review documents for stale delivery claims
- Replay ships raw + normalized artifacts with machine-verifiable normalize(raw)==normalized
- Forbidden-path detection covers Windows/macOS/Linux home roots
- Retains trusted-Git sole launch primitive; GO_CAPABILITY=false

### Explicit open blockers

1. BLOCKER_AUTHORITY_PRODUCER_MISSING
2. BLOCKER_OS_SANDBOX_RUNNER_MISSING

## 0.23.0 (R23) — independent review candidate

Author: **Cursor**

### Closures targeting the R22 REVISION_REQUIRED findings

- Authority root authenticity requires OS-pinned Ed25519 public key
  (``C:\ProgramData\OPSX\conflict-authority\ed25519.pub`` /
  ``/etc/opsx/conflict-authority/ed25519.pub``) plus
  ``OPSX_CONFLICT_AUTHORITY_ROOT_SIGNATURE``; ambient path+digest alone STOP
- Mechanical symbols recomputed from stage 1/2/3 blobs; parse/markers → STOP;
  capabilities from producer ``capability_bindings`` (declaration schema v3)
- Rename lineage always probed via fixed-argv Git evidence; empty declaration
  does not skip verification
- Trusted-Git bind: component-by-component lstat, exclusive create, pre-exec
  re-hash
- Ship restores host contracts from origin; does **not** mint unsigned
  ``external signed provenance``
- Replay evidence uses real merge/rebase Git fixtures + boot entrypoint
- Clean-unpack ships ``pytest -ra`` + machine-readable ``SKIP_INVENTORY.json``
- ``GO_CAPABILITY=false``

### Explicit open blockers

1. ``BLOCKER_AUTHORITY_PRODUCER_MISSING``
2. ``BLOCKER_OS_SANDBOX_RUNNER_MISSING``
