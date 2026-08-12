# 04_REVISION_CLOSURE_MATRIX

Immediate baseline: independent R19 rejection
(`archive_sha256=6b2c053ca5084f13eac6eccb13ad2d307738e569bf4857ee5a35badea9762ebc`).

Historical baselines: R15/R14/R13/R12/R10 archives remain REJECTED.

## R10 → R11 mandatory closure

| Finding | R11 change | Acceptance evidence |
|---|---|---|
| R10-CRIT-001 | Namespace hooks stop; every comment token is exact-base-only. | `tests/test_resolution_proof.py` module-hook and unknown-directive cases |
| R10-CRIT-002 | Registry/descriptors are read from startup-hash-bound bytes; each check ID has exact argv. | `tests/test_execution_policy.py` arbitrary-command and frozen-byte cases |
| R10-CRIT-003 | Post-add and terminal checks bind stage-0 OID/mode and worktree SHA-256. | `tests/test_orchestrator_go.py` before/during/after-add injections |
| R10-HIGH-001 | External plaintext original backup removed; hash-only transaction journal added. | `tests/test_state_and_restart.py`; no `*.original` under state root |
| R10-HIGH-003 | Strict GO requires explicit change ID, commit trailers, and exact path authority manifest. | authority-binding GO tests |
| R10-HIGH-004 | GO requires a digest-bound external sandbox runner. | compatibility gate + sandbox receipt evidence |
| R10-HIGH-005 | Write-ahead PREPARED → ORIGINAL_CLAIMED → CANDIDATE_INSTALLED → VERIFIED → RECOVERY_RELEASED. | transition recovery matrix |
| R10-HIGH-006 | Atomic terminal bundle is sole success authority; ledger seals PREPARED only. | terminal publication fault tests |

| Finding | Revision in r05 | Evidence |
|---|---|---|
| CF-001 | Prompt-only execution removed. All reads/writes/checks/staging/continue go through typed runtime. Raw shell, wrappers, subagents, workers and nested OPSX commands are forbidden. Validation runs in a `.git`-free tracked-file snapshot. Process groups are joined/killed on timeout. Continuation disables hooks. Hash-chain ledger records actions. | `command/.cursor/commands/opsx-resolve-conflict.md` §§4–5; `runtime/opsx_conflict/runtime.py`; `tests/test_execution_policy.py`; `tests/test_validation_snapshot.py`; `tests/test_hook_and_process_barrier.py` |
| HF-001 | Added normative OID-based matrix for merge, rebase and cherry-pick, including missing-stage cells. Runtime verifies actual stage OIDs against normative Git objects. | Command §6; runtime `stage_role_matrix`; `tests/test_stage_role_matrix.py` |
| HF-002 | Added deterministic operation state machine and fingerprint over heads, sequencer files, index, stage map, staged map, tracked worktree hashes and untracked inventory. Fingerprint checked around mutations. | Command §7; runtime `detect_operation_state`; `tests/test_state_and_restart.py` |
| HF-003 | Added full source/target operation graph and cross-file Python contract candidate detector for auto-merged paths. | Command §11; runtime `detect_logical_conflict_candidates`; `tests/test_logical_conflict_detection.py` |
| HF-004 | Added durable external run manifest, exact fingerprint resume gate, unit statuses and no-repeat rule. | Command §9; runtime `RunManifest`, `resume_guard`; restart tests |
| HF-005 | Default fail-closed for every untracked path. Only exact path+hash inert allowlist can pass. | Command §8; runtime `untracked_gate`; `tests/test_untracked_and_scope.py` |
| HF-006 | Removed plaintext recovery snapshot. Persist only metadata, object OIDs and hashes. User-only permissions/Windows ACL gate required. | Command §9; runtime `create_metadata_snapshot`, `_secure_path`; `tests/test_snapshot_security.py` |
| HF-007 | Removed `git restore --staged` rollback. Contamination causes STOP with no further index mutation. | Command §§5,14; runtime has no unstage action; source-policy test |
| HF-008 | Removed `FINAL=FAST`. Final validation is FULL or stronger; runtime rejects FAST. | Command §§2,17; runtime `effective_final_gate`; execution-policy test |
| MF-001 | Removed temporary worktree baseline mechanism. Validation snapshot is a plain tracked-file copy without `.git`. | Command §§4.2,15; runtime `build_validation_snapshot` |
| MF-002 | Removed `base=<REF>`. Operation metadata is normative. | Front matter and command §2 |
| MF-003 | Added versioned run/unit/scope/ledger JSON Schemas, exact OIDs, source hashes, argv, exit codes, timeouts and output hashes. | `schemas/**`; command §19 |
| MF-004 | Added immutable pre-edit scope manifest. Only already-conflicted paths may be written. Non-conflicted production/tests require STOP. | Command §13; runtime `ScopeManifest`; scope tests |
| MF-005 | Expanded normative taxonomy to directory rename, rename/add, rename/modify, file/symlink, mode and submodule; requires `-M` path identity and mode evidence. | Command §12; taxonomy tests and scenario matrix |
| PF-001 | Added package version, schema version, runner/capability compatibility fields, source commit pin, manifest, changelog and SHA-256 inventory. | front matter; `MANIFEST.json`; `CHANGELOG.md`; `SHA256SUMS` |


## R11 → R12 mandatory closure

| Finding | R12 change | Acceptance evidence |
|---------|------------|---------------------|
| R11-CRIT-001 self-attested sandbox | `trusted_sandbox_runners` allowlist + `OPSX_CONFLICT_SANDBOX_TRUST_DIGEST` + handshake + re-hash | hostile self-hash runner rejected |
| R11-CRIT-002 filters/hooks/staged bytes | sealed Git env; `hash-object --no-filters` + `update-index --cacheinfo`; `cat-file` byte compare | staged blob bytes == validated bytes |
| R11-CRIT-003 validation STOP loses worktree | VERIFIED txn retains `.git` backup until staging release; STOP recovers | pre-run bytes restored after CHECK_FAILED |
| R11-HIGH-001 authority completeness | `external_authority` attestation + omission scan | incomplete/omitted authority STOP |
| R11-HIGH-002 terminal bundle recovery | startup recovers `*.terminal.json` before ACTIVE resume | cache refresh after hard crash |
| R11-HIGH-003 stale journals | RETIRED after release/terminal; no drift blockers | Owner edit after success does not STOP |
| R11-HIGH-004 reserved module names | closed reserved module bindings | `__name__` etc. STOP |

## R12 → R13 closures (superseded by R14)

| Finding | R13 change | Acceptance evidence |
|---------|------------|---------------------|
| R12-CRIT-001 fake sandbox capabilities | Packaged runner `BEST_EFFORT`; GO requires `OS_VERIFIED` + admission probes | `attestation.py` / GO gate STOP |
| R12-CRIT-002 forged terminal bundle | Recover verifies component hashes, ledger finality, fingerprint, stage evidence | forged/missing ledger STOP |
| R12-CRIT-003 namespace observers | AST proof rejects `globals`/`locals`/`__dict__` observation | `tests/test_resolution_proof.py` |
| R12-CRIT-004 early rollback release | `mark_write_transaction_staged`; release only after terminal bundle | staging journals remain until terminal |
| R12-HIGH-002 plaintext claim contradiction | Write proofs report git-dir transactional backup honestly | command §9.2 |
| R12-HIGH-003 read path mkdir | `resolve_under_repo` no mkdir; `prepare_new_path_under_repo` for writes | `tests/test_path_safety.py` |

## R14 → R15 mandatory closure

| Finding | R15 change | Acceptance evidence |
|---------|------------|---------------------|
| R14-CRIT-001 PREVIEW external openspec | Removed host PATH `openspec` execution; static authority only | `authority.py`; adversarial PATH replay |
| R14-CRIT-002 import-alias semantic bypass | Alias-aware import/assignment tracking of dynamic callables | `tests/test_r15_closures.py` |
| R14-CRIT-003 false-complete FULL inventory | Unknown applicability → `BLOCKED`; adjacent nodes derived | `validation.py` / `test_missing_targeted_tests_block_inventory` |
| R14-HIGH-001 terminal without fsync | `persist_private_json` + journals: flush/fsync/replace/fsync-dir | `receipts.py` / `write_atomic.py` |
| R14-HIGH-002 go_capability not gated | `PACKAGE_GO_CAPABILITY_DISABLED` when `go_capability != true` | `attestation.package_compatibility_gate` |
| R14-HIGH-004 backup ACL not verified | Fail-closed POSIX mode + Windows owner-only DACL verify | `write_atomic._secure_backup_*` |
| R14-MED-001 PREVIEW creates state dir | PREVIEW does not mkdir state root | `effective_acl_ok(create=False)` |

## R15 → R16 mandatory closure

| Finding | R16 change | Acceptance evidence |
|---------|------------|---------------------|
| R15-CRIT-001 container aliases | Any Load/first-class use of dynamic primitives STOP | `tests/test_r16_closures.py` container cases |
| R15-CRIT-002 one-test multi-role | Role metadata required; separate pytest-* checks | `validation.py` / `test_r16_closures.py` |
| R15-HIGH-001 PREVIEW not RO | Packaged hooks; `GIT_OPTIONAL_LOCKS=0`; index SHA gate | `git_typed.py` / preview index check |
| R15-HIGH-002 hard-coded universe | Unmapped registry checks → BLOCKED inventory row | `registry_discovered_unclassified` |
| R15-HIGH-003 no GO | Keep `go_capability=false` until OS_VERIFIED | `PACKAGE_GO_CAPABILITY_DISABLED` |
| R15-MED-003 git identity | Path/version/sha256 in PREVIEW payload | `git_executable_identity()` |

## R18 → R19 (superseded; R19 REJECTED)

| Finding | R19 change | Acceptance evidence |
|---------|------------|---------------------|
| R18-CRIT-001 fake behavioral coverage | Qualified import + protected assert + monkeypatch/homonym rejection | `validation.py` / `tests/test_r19_closures.py` |
| R18-CRIT-002 Git check-then-exec TOCTOU | Immutable bound executable copy for all typed Git subprocesses | `git_typed.py` / `tests/test_r19_closures.py` |
| R18-CRIT-003 launcher outside trust closure | Boot launcher included in inventory and mandatory entrypoint policy | `attestation.py` / manifest entrypoints |
| R18-MED PREVIEW plan gap | PREVIEW emits per-path `validation_preflight` build result | `orchestrator.py` |

## R19 → R20 mandatory closure

| Finding | R20 change | Acceptance evidence |
|---------|------------|---------------------|
| R19-CRIT evidence digest drift | In-ZIP CLEAN_UNPACK/PACKAGE_INDEX digest == MANIFEST/TRUST; archive SHA only in external report | `scripts/ship_review_package.py` / `tests/test_r20_closures.py` |
| R19-CRIT archive SHA self-reference | `archive_sha256=null` + `archive_binding=external_test_report_only` inside ZIP | CLEAN_UNPACK / PACKAGE_INDEX / ship verify |
| R19-CRIT clean-unpack poetry dependency | GO fixtures stub poetry which; ship run hides host poetry | `test_orchestrator_go._patch_gate` / ship PATH isolation |
| R19-HIGH pass-count drift | External report records exact pytest summary from delivered ZIP unpack | `*.TEST_REPORT.json` |

## Residual limitations disclosed for review (R20)

1. SAFE_TO_USE=NO / NONE_EXECUTION until ACCEPTED and GO capability enabled.
2. No bundled OS_VERIFIED sandbox; `go_capability=false`.
3. Host contracts are hash-bound; full contextual review needs host repo or bundled contract bodies.
4. Autonomous GO is single-file only; multi-file units STOP before write.
5. Partial-spec authority still uses path/stem lineage heuristics (not full capability graph).
6. PREVIEW proves index + bytecode policy; not full filesystem/temp attestation.
7. Trust is hash-bound via SHA256SUMS + external digest; not a cryptographic signature.

## R20 → R21 mandatory closure

| Finding | R21 change | Acceptance evidence |
|---------|------------|---------------------|
| R20 path/stem authority heuristic | Removed; `none_applicable` requires external declaration | `authority.py` / `tests/test_r21_closures.py` |
| R20 self-attestable local JSON | Consumer verifier + issuer allowlist from external producer contract | schema + `verify_external_authority_declaration` |
| R20 missing producer | `BLOCKER_AUTHORITY_PRODUCER_MISSING` → `STOP_AUTHORITY_UNPROVEN` | review docs / MANIFEST limitations |
| R20 BEST_EFFORT GO risk | GO admission `STOP_SANDBOX_UNAVAILABLE` / `BLOCKER_OS_SANDBOX_RUNNER_MISSING` | `attestation.py` / orchestrator |
| R20 evidence completeness | External TEST_REPORT.json/log + SIDECAR; ZIP immutable post-test | `scripts/ship_review_package.py` |
| R20 lineage gap | `context/SOURCE_LINEAGE.json` host-contract mapping | `scripts/build_lineage_mapping.py` |

## Residual limitations disclosed for review (R21)

1. SAFE_TO_USE=NO / NONE_EXECUTION; `GO_CAPABILITY=false`.
2. **Open blocker:** `BLOCKER_AUTHORITY_PRODUCER_MISSING` (no external OPSX declaration producer).
3. **Open blocker:** `BLOCKER_OS_SANDBOX_RUNNER_MISSING` (no independently supplied OS_VERIFIED runner).
4. Host contracts are hash-bound; lineage mapping may mark working-tree-only pins.
5. Autonomous GO is single-file only; multi-file units STOP before write.
6. Replay evidence shows fail-closed STOP under unavailable gates — not production GO.
7. Trust is hash-bound via SHA256SUMS + external digest; not a cryptographic signature.

## R21 → R22 mandatory closure

| Finding | R22 change | Acceptance evidence |
|---------|------------|---------------------|
| R21-HIGH-001 forgeable producer trust | External `OPSX_CONFLICT_AUTHORITY_ROOT_*` only; MANIFEST cannot mint trust | `authority.py` / `tests/test_r22_closures.py` |
| R21-MEDIUM-001 untyped Git bind errors | Atomic bind + ACL/TOCTOU → typed `StopRequired` | `git_typed.py` / R22 bind tests |
| R21-PROCESS-001 lineage confusion | `origin_source_commit` vs `host_contract_snapshot_commit` + dual OIDs | `build_lineage_mapping.py` / `SOURCE_LINEAGE.json` v2 |
| R21-PROCESS-002 non-reproducible replay | Hash-bound fixtures + raw logs + process-tree + ledger | `build_replay_evidence.py` |
| R21-PROCESS-003 producer blocker | Remains open external blocker | review docs / MANIFEST limitations |
| R21-PROCESS-004 OS sandbox blocker | Remains open external blocker | review docs / MANIFEST limitations |

## Residual limitations disclosed for review (R22)

1. SAFE_TO_USE=NO / NONE_EXECUTION; `GO_CAPABILITY=false`.
2. Consumer-side trust enforcement implemented; operational producer trust unavailable.
3. **Open blocker:** `BLOCKER_AUTHORITY_PRODUCER_MISSING`.
4. **Open blocker:** `BLOCKER_OS_SANDBOX_RUNNER_MISSING`.
5. Host-contract snapshot commit proves packaged-byte immutability only — not OPSX origin.
6. Autonomous GO is single-file only; multi-file units STOP before write.
7. Trust is hash-bound via SHA256SUMS + external digest; not a cryptographic signature.

## R22 → R23 mandatory closure

| Finding | R23 change | Acceptance evidence |
|---------|------------|---------------------|
| R22-HIGH-001 ambient env as auth | OS-pinned Ed25519 pubkey + `OPSX_CONFLICT_AUTHORITY_ROOT_SIGNATURE`; path+digest alone STOP | `authority.py` / `tests/test_r23_closures.py` |
| R22-HIGH-002 worktree symbols / incomplete caps | Stage 1/2/3 blob symbols; parse/markers STOP; `capability_bindings` | `authority.py` / R23 symbol tests |
| R22-HIGH-003 empty rename skips probe | Always run rename probe; empty OK only after proven absence | `verify_rename_lineage_evidence` / R23 rename tests |
| R22-MEDIUM-001 Git bind TOCTOU | Component lstat, `O_EXCL`, pre-exec re-verify | `git_typed.py` / R23 bind tests |
| R22-PROCESS-001 ship-minted provenance | Restore host contracts from origin; no unsigned provenance mint | `ship_review_package.py` / R23 process tests |
| R22-PROCESS-002 function-level replay | Real merge/rebase fixtures + `boot_opsx_conflict.py` | `build_replay_evidence.py` |
| R22-PROCESS-003 unclassified skips | `pytest -ra` + `SKIP_INVENTORY.json` | ship clean-unpack / skip inventory |

## Residual limitations disclosed for review (R23)

1. SAFE_TO_USE=NO / NONE_EXECUTION; `GO_CAPABILITY=false`.
2. OS-pinned trust pubkey + authenticated producer remain deployment-external.
3. **Open blocker:** `BLOCKER_AUTHORITY_PRODUCER_MISSING`.
4. **Open blocker:** `BLOCKER_OS_SANDBOX_RUNNER_MISSING`.
5. Host-contract snapshot commit proves packaged-byte immutability only — not OPSX origin.
6. Autonomous GO is single-file only; multi-file units STOP before write.
7. Package digests are SHA-256 inventory; authority authenticity uses Ed25519 over OS pubkey.


<!-- HISTORICAL_BASELINE_ALLOWLIST: prior-revision closure rows below are
historical findings, not current-delivery digests/test totals. -->

## R23 → R24 mandatory closure (HISTORICAL_BASELINE_ALLOWLIST)

| Finding | R24 change | Acceptance evidence |
|---------|------------|---------------------|
| Author-path leak in replay | Stage packaged boot under `C:\Temp`; normalize evidence paths | `build_replay_evidence.py` / portability tests |
| Self-referential inner REVIEW_REQUEST digests | Inner request omits bundle/inner/test totals | `write_inner_review_request` / validator |
| Missing post-build claim checks | `validate_review_bundle` fail-closed | `ship_review_package.py` / fault-injection tests |

## R24 → R25 mandatory closure

| Finding | R25 change | Acceptance evidence |
|---------|------------|---------------------|
| Stale current-delivery claims in README_REVIEW | Inner operator docs omit archive hashes/test totals | `README_REVIEW.md` / operator claim scanner |
| Validator missed operator docs | Claim scan covers README*/REVIEW_REQUEST/summaries | `is_operator_review_document` / fault injection |
| Raw bytes not shipped | Raw + normalized + mapping + verification per file | `build_replay_evidence.py` v5 |
| Linux profile paths undetected | Cross-platform forbidden-path patterns | synthetic Win/macOS/Linux tests |

## R25 → R26 mandatory closure

| Finding | R26 change | Acceptance evidence |
|---------|------------|---------------------|
| R25-HIGH-001 unsigned declaration accepted by issuer ID | Declaration v4 + issuer-key signature over canonical payload | `authority.py` / `tests/test_r26_declaration_auth.py` |
| Bare issuer string in producer | Producer requires `id`/`key_id`/`public_key_ed25519` binding | `_normalize_producer_issuers` |
| Legacy v3 compatibility | Unsigned/flat v3 rejected in strict/GO flow | `legacy_unsigned_declaration_rejected` |

## R26 → R27 mandatory closure

| Finding | R27 change | Acceptance evidence |
|---------|------------|---------------------|
| R25-HIGH-002 local AST empty caps → false none_applicable | Declaration v5 + signed capability evidence | `authority.py` / `tests/test_r27_capability_evidence.py` |
| Completeness without attestor role | Producer issuer must include `capability_attestor` | `_normalize_producer_issuers` / `verify_capability_evidence` |
| Incomplete stage coverage / unknown targets | Exact stage_coverage + analysis_complete + empty unknown_targets | stage-coverage mismatch / unknown_targets STOP |
| Local symbol→bindings as proof | Diagnostic only; cannot replace authenticated evidence | `capability_diagnostic_bindings_exceed_evidence` |

## R27 → R28 mandatory closure

| Finding | R28 change | Acceptance evidence |
|---------|------------|---------------------|
| R25-HIGH-003 synthetic `execution` registry field | Actual `task_type`+`pack` registry compilation | `validation.py` / `tests/test_r28_registry_pack.py` |
| Pack markdown treated as executable authority | Closed typed adapter table owns argv | `TYPED_CHECK_ADAPTERS` |
| Missing pack inventory in host freeze | Four pack trees in host_frozen_contracts | MANIFEST / lineage / archive scripts |

## Residual limitations disclosed for review (R28)

1. SAFE_TO_USE=NO / NONE_EXECUTION; `GO_CAPABILITY=false`.
2. **Open blocker:** `BLOCKER_AUTHORITY_PRODUCER_MISSING`.
3. **Open blocker:** `BLOCKER_OS_SANDBOX_RUNNER_MISSING`.
4. **Open finding (not falsely closed):** R25-PROCESS-001 pack/commit membership.

## R28 → R29 mandatory closure

| Finding | R29 change | Acceptance evidence |
|---------|------------|---------------------|
| R25-MEDIUM-001 broad nonzero replay PASS | Exact-match expectation contract + assertion AND | `scripts/build_replay_evidence.py` / `tests/test_r29_replay_terminal.py` |
| Missing scope / SCOPE_FILE_REQUIRED false PASS | Scoped GO fixtures + reject SCOPE_FILE_REQUIRED as target | replay cases + negative matrix |
| Traceback instead of STOP envelope | CLI `run_cli` StopRequired envelope | `runtime.py` / `cli-stop-envelope.schema.json` |

## Residual limitations disclosed for review (R29)

1. SAFE_TO_USE=NO / NONE_EXECUTION; `GO_CAPABILITY=false`.
2. **Open blocker:** `BLOCKER_AUTHORITY_PRODUCER_MISSING`.
3. **Open blocker:** `BLOCKER_OS_SANDBOX_RUNNER_MISSING`.
4. **Open finding (not falsely closed):** R25-MEDIUM-002 trusted-Git execution
   boundary — **must not be claimed atomic**.
5. **Open finding (not falsely closed):** R25-PROCESS-001 pack/commit membership.
6. **Open finding (out of R29 scope):** cross-platform shipping / home-path
   portability.



## R29 → R30 mandatory closure

| Finding | R30 change | Acceptance evidence |
|---|---|---|
| R25-MEDIUM-003 | OS trust-store component walk + owner/DACL + stable handle | `tests/test_r30_trust_store.py` + runtime `os_trust_store.py` |

## Residual limitations disclosed for review (R30)

1. BLOCKER_AUTHORITY_PRODUCER_MISSING
2. BLOCKER_OS_SANDBOX_RUNNER_MISSING
3. R25-MEDIUM-002 trusted-Git execution boundary (not claimed atomic)
4. R25-MEDIUM-004
5. R25-PROCESS-001
6. Cross-platform shipping / home-path finding (out of R30 scope)

## R30 → R31 mandatory closure

| Finding | R31 change | Acceptance evidence |
|---|---|---|
| R25-MEDIUM-003 AccessCheck | Per-right effective mask; drive-root DACL | `tests/test_r31_trust_store_dacl.py` |

## Residual limitations disclosed for review (R31)

1. BLOCKER_AUTHORITY_PRODUCER_MISSING
2. BLOCKER_OS_SANDBOX_RUNNER_MISSING
3. R25-MEDIUM-002 trusted-Git execution boundary (not claimed atomic)
4. R25-MEDIUM-004
5. R25-PROCESS-001
6. Cross-platform shipping / home-path finding (out of R31 scope)

## R31 → R32 mandatory closure

| Finding | R32 change | Acceptance evidence |
|---|---|---|
| R25-MEDIUM-004 portability | Native workspace; Pure* synthetics; platform matrix | `scripts/path_workspace.py`, `tests/test_r25_evidence_portability.py`, PLATFORM_CAPABILITY_MATRIX |

## Residual limitations disclosed for review (R32)

1. BLOCKER_AUTHORITY_PRODUCER_MISSING
2. BLOCKER_OS_SANDBOX_RUNNER_MISSING
3. R25-MEDIUM-002 trusted-Git execution boundary (not claimed atomic)
4. R25-PROCESS-001
5. macOS clean-unpack support is `NOT_VERIFIED` (no native macOS runner evidence)

## R32 → R33 mandatory closure

| Finding / decision | R33 change | Acceptance evidence |
|---|---|---|
| ADR-OPSX-RC-PLATFORM-001 | APPROVE_WINDOWS_ONLY; Linux/macOS UNSUPPORTED | `assert_supported_platform`, PLATFORM_CAPABILITY_MATRIX v2 |
| R25-MEDIUM-004 (scope) | Windows-only consolidated review path | matrix in inner ZIP + review bundle |

## Residual limitations disclosed for review (R33)

1. BLOCKER_AUTHORITY_PRODUCER_MISSING
2. BLOCKER_OS_SANDBOX_RUNNER_MISSING
3. R25-MEDIUM-002 trusted-Git execution boundary (not claimed atomic)
4. R25-PROCESS-001
5. Linux/macOS explicitly UNSUPPORTED (separate architecture request required)
6. R33-GATE-HIGH-001 PREVIEW read-only Git boundary (broad allowlist) — closed in R34
7. R33-GATE-HIGH-002 weak semantic recommendation (deferred)
8. R33-GATE-PROCESS-001 / R33-GATE-PROCESS-002 (deferred)

## R33 → R34 mandatory closure

| Finding | R34 change | Acceptance evidence |
|---|---|---|
| R33-GATE-HIGH-001 | Exact preview operation IDs → fixed argv; sealed env; trusted Git bind; OID validation; no public arbitrary argv | `preview_readonly_git.py`; `tests/test_r34_preview_readonly_git.py` |

## Residual limitations disclosed for review (R34)

1. BLOCKER_AUTHORITY_PRODUCER_MISSING
2. BLOCKER_OS_SANDBOX_RUNNER_MISSING
3. R25-MEDIUM-002 trusted-Git execution boundary (not claimed atomic) — **explicitly open**
4. R25-PROCESS-001
5. Linux/macOS explicitly UNSUPPORTED
6. R33-GATE-HIGH-002 weak semantic recommendation — closed in R35
7. R33-GATE-PROCESS-001 / R33-GATE-PROCESS-002 (deferred)

## R34 → R35 mandatory closure

| Finding | R35 change | Acceptance evidence |
|---|---|---|
| R33-GATE-HIGH-002 | Evidence+advisory layers; bounded context; no textual-subset recommendation | `preview_context.py`, `preview_advisory.py`, `tests/test_r35_preview_context.py` |

## Residual limitations disclosed for review (R35)

1. BLOCKER_AUTHORITY_PRODUCER_MISSING
2. BLOCKER_OS_SANDBOX_RUNNER_MISSING
3. R25-MEDIUM-002 trusted-Git execution boundary (not claimed atomic) — **explicitly open**
4. R25-PROCESS-001
5. Linux/macOS explicitly UNSUPPORTED
6. R33-GATE-PROCESS-001 / R33-GATE-PROCESS-002 (deferred)
7. R35-GATE-AUTHORITY-001 pathname-as-authority — closed in R36
8. R36-GATE-AUTHORITY-002 contract lifecycle precedence — closed in R37
9. R33-GATE-PROCESS-001 immutable PREVIEW evidence — closed in R38
10. R38-GATE-PROCESS-001 PREVIEW evidence path sanitization — closed in R39

## R35 → R36 mandatory closure

| Finding | R36 change | Acceptance evidence |
|---|---|---|
| R35-GATE-AUTHORITY-001 | Proven authority_verified gate; lifecycle matrix; bounded authority search | `preview_context.py`, `preview_advisory.py`, `tests/test_r36_authority_verification.py` |

## R36 → R37 mandatory closure

| Finding | R37 change | Acceptance evidence |
|---|---|---|
| R36-GATE-AUTHORITY-002 | CONTRACT: explicit non-active lifecycle vetoes before normative marker | `preview_context.py` CONTRACT branch; `tests/test_r37_contract_lifecycle.py` |

## R37 → R38 mandatory closure

| Finding | R38 change | Acceptance evidence |
|---|---|---|
| R33-GATE-PROCESS-001 | Immutable real merge/rebase PREVIEW evidence in review bundle | `scripts/build_preview_evidence.py`; ship/bundle validator; `tests/test_r38_preview_evidence.py` |

## R38 → R39 mandatory closure

| Finding | R39 change | Acceptance evidence |
|---|---|---|
| R38-GATE-PROCESS-001 | Recursive JSON path scan + `<TRUSTED_GIT_EXECUTABLE>` tokenization | `build_preview_evidence.py`; `tests/test_r39_preview_evidence_paths.py` |

## R39 → R40 mandatory closure

| Finding | R40 change | Acceptance evidence |
|---|---|---|
| BUGBOT-HIGH-002 | Explicit single-path PREVIEW; multi-conflict without `--path` STOPs | `preview_advisory.py`; `tests/test_r40_single_path_preview.py` |
| BUGBOT-MEDIUM-001 | Delete stale committed `_preview_all.json` workspace dump | file removed; not in MANIFEST/runtime |

## Residual limitations disclosed for review (R40)

1. BLOCKER_AUTHORITY_PRODUCER_MISSING
2. BLOCKER_OS_SANDBOX_RUNNER_MISSING
3. R25-MEDIUM-002 trusted-Git execution boundary (not claimed atomic) — **explicitly open**
4. R25-PROCESS-001
5. Linux/macOS explicitly UNSUPPORTED
6. R33-GATE-PROCESS-002 (deferred — inner/outer platform matrix evidence-identical)
7. BUGBOT-HIGH-001 commit routing ownership (deferred)
8. BUGBOT-MEDIUM-002 `process_surfaces.json` path gaps (deferred)
