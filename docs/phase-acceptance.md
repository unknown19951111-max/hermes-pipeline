# Phase Acceptance — Smart-Contract Security Pipeline

> **Last updated:** 2026-07-15 (audit: aa1b60db)
> **Status generated from:** `AUDIT_ACCEPTANCE_LEDGER.json` — do not edit manually
> **Production status:** ❌ BLOCKED — 20 P0 findings prevent release

## Phase 1 — EVM Production MVP

### Phase 1 Acceptance Criteria

Phase 1 is complete only when ALL of the following pass:

| # | Criterion | Status | Evidence Required |
|---|---|---|---|
| 1 | Remote repository can be submitted | ❌ FAILED | `RepositoryManager.intake_remote()` — F-002: `kwargs` undefined NameError |
| 2 | Local project can be submitted | 🔶 BLOCKED | `intake_local()` works but F-003: symlink disclosure |
| 3 | Target commit is pinned | ✅ UNIT_VALIDATED | `IntakeManifest.commit_sha` recorded in E2E test |
| 4 | Intake manifest generated | 🔶 BLOCKED | Manifest generated but F-005: no JSON Schema validation |
| 5 | Program eligibility can be captured | ❌ FAILED | `EligibilitySnapshot.create()` — F-001: field mismatch `status` vs `program_status` |
| 6 | Ecosystem detection works | ✅ INTEGRATION_VALIDATED | E2E: evm @ 1.00 confidence |
| 7 | Framework detection works | ✅ INTEGRATION_VALIDATED | E2E: foundry @ 0.95 confidence |
| 8 | Ambiguous detection fails safely | ✅ UNIT_VALIDATED | Returns `unknown` @ 0.0 confidence |
| 9 | Target compiles with pinned compiler | 🔶 BLOCKED | `BuildExecutor._build_foundry()` — F-022: `--via-ir` forced, F-023: env not passed, F-015: no sandbox |
| 10 | Compiler logs preserved | ✅ UNIT_VALIDATED | `artifact_store.store_build_log()` works |
| 11 | Slither runs through its own adapter | 🔶 BLOCKED | Adapter runs but F-004: success calc wrong, F-015: no sandbox, F-016: host env |
| 12 | Aderyn runs through its own adapter | 🔶 BLOCKED | Same F-004, F-015, F-016 issues as Slither |
| 13 | Tool versions recorded | ✅ UNIT_VALIDATED | `AdapterResult.tool_version` in manifest |
| 14 | Raw outputs preserved | ✅ UNIT_VALIDATED | `artifact_store.store_raw_output()` |
| 15 | Outputs normalize against shared schema | 🔶 BLOCKED | F-005: no `jsonschema.validate()` call, F-024: tests don't use schema |
| 16 | Malformed outputs quarantined | 🔶 BLOCKED | F-005: schema validation ineffective |
| 17 | At least one archetype selected from evidence | ✅ UNIT_VALIDATED | Classifier: 12 archetypes, rule-based |
| 18 | Multi-label classification works | ✅ UNIT_VALIDATED | Test: erc4626+staking detected |
| 19 | Compatible invariant set selected | 🔶 BLOCKED | F-006: registry references phantom invariant IDs |
| 20 | Incompatible invariants rejected | ✅ UNIT_VALIDATED | Test: compiler 0.6.0 correctly rejected |
| 21 | Chimera-compatible harness generated | 🔶 BLOCKED | F-007: 4 archetypes produce empty no-op functions, F-008: tautological assertion |
| 22 | Harness compiles | 🔶 BLOCKED | Empty invariants compile successfully as no-ops (F-007, F-008) |
| 23 | Medusa executes | 🔶 NOT_IMPLEMENTED | `medusa` binary not installed. Dependency check passes (graceful) |
| 24 | Medusa corpus preserved | 🔶 NOT_IMPLEMENTED | No corpus preservation in execution path |
| 25 | Initial corpus hash recorded | 🔶 NOT_IMPLEMENTED | Not implemented |
| 26 | Final corpus hash recorded | 🔶 NOT_IMPLEMENTED | Not implemented |
| 27 | Worker count recorded | 🔶 NOT_IMPLEMENTED | Not implemented |
| 28 | Machine profile recorded | 🔶 NOT_IMPLEMENTED | Not implemented |
| 29 | Failing sequences preserved | 🔶 NOT_IMPLEMENTED | Not implemented |
| 30 | Echidna can be enabled independently | 🔶 IMPLEMENTED_UNTESTED | Adapter exists, dependency check passes, no actual fuzzing tested |
| 31 | Echidna failure does not destroy job | ✅ UNIT_VALIDATED | `AdapterResult` preserves partial results |
| 32 | Duplicates grouped deterministically | 🔶 IMPLEMENTED_UNTESTED | Dedup exists but cross-tool grouping untested |
| 33 | Confidence follows documented rubric | ✅ UNIT_VALIDATED | 0-5 rubric in `finding.json` schema |
| 34 | Known-positive fixture detected | 🔶 BLOCKED | F-010: accepts any Slither warning, not exact `reentrancy-eth` |
| 35 | Patched fixture does not produce same confirmed result | 🔶 BLOCKED | F-011: no assertion that `reentrancy-eth` is absent |
| 36 | Qualifying result reproduced via Foundry PoC | 🔶 BLOCKED | F-009: PoC returns True for both PASSED and FAILED |
| 37 | PoC uses pinned target state | 🔶 NOT_IMPLEMENTED | Not enforced in PoC generation |
| 38 | Human-review queue receives qualifying result | 🔶 IMPLEMENTED_UNTESTED | `HumanReviewQueue` exists but not integrated into CLI |
| 39 | Final report includes full provenance | ✅ INTEGRATION_VALIDATED | Report generator: stage_results, timestamps |
| 40 | Failed tool isolated | ✅ UNIT_VALIDATED | `CircuitBreaker` per-tool isolation tested |
| 41 | Partial results survive tool failure | ✅ UNIT_VALIDATED | `FailureHandler` preserves partial findings |
| 42 | Job resumes from checkpoint | ✅ UNIT_VALIDATED | `CheckpointManager` save/load/resume tested |
| 43 | Target code cannot access host secrets | ❌ FAILED | F-015: no sandbox integration, F-016: host env inherited by subprocess |
| 44 | Verification ledger complete for Phase 1 deps | ❌ FAILED | F-017, F-018: false claims in ledger |
| 45 | All Phase 1 tests pass | ✅ INTEGRATION_VALIDATED | 40 tests, 4 suites, all exit 0 (pytest: 22s) |

### Phase 1 does NOT pass if:
- ✅ Pipeline runs (verified)
- ✅ Outputs are normalized (verified)
- 🔶 Invariants are compatibility-checked (registry works but phantom IDs — F-006)
- ❌ Corpora are discarded (not implemented)
- 🔶 Known-positive validation fails (soft-fallback — F-010)
- 🔶 Known-negative validation fails (no assertion — F-011)
- ❌ PoC reproduction is absent (POCGenerator scaffolded but F-009: always returns True)
- ✅ Provenance is complete (verified)

### Phase 1 Status: ❌ BLOCKED

**20 P0 findings prevent Phase 1 completion.** Critical blockers: intake (F-002, F-003), eligibility (F-001), adapter success (F-004), schema validation (F-005), invariant registry (F-006), harness generation (F-007, F-008), PoC verification (F-009), E2E tests (F-010, F-011), CI (F-012, F-013), sandbox (F-015, F-016), documentation (F-017, F-018).

---

## Phase 2 — EVM Depth Tier

### Phase 2 Acceptance Criteria

Phase 2 is complete only when ALL of the following pass:

| # | Criterion | Status | Evidence Required |
|---|---|---|---|
| 1 | Each depth-tier tool has independent adapter | 🔶 BLOCKED | Adapters exist but F-015: no sandbox, F-016: host env |
| 2 | Every depth-tier adapter is optional | 🔶 BLOCKED | Missing tools produce graceful degradation, but F-004: success calc wrong |
| 3 | Missing depth-tier tools do not break Phase 1 | 🔶 BLOCKED | Phase 1 must pass first (P1-45: 40 tests pass at unit level, but e2e F-014) |
| 4 | Unsupported versions fail safely | ✅ UNIT_VALIDATED | Test: `is_supported_version()` returns False |
| 5 | Symbolic outputs normalize into shared schema | 🔶 BLOCKED | F-005: no JSON Schema validation |
| 6 | Counterexamples route to PoC validation where applicable | 🔶 BLOCKED | F-009: PoC returns True for both pass and fail |
| 7 | Resource-heavy jobs are memory-gated | 🔶 BLOCKED | F-015: sandbox not integrated |
| 8 | Per-property timeouts enforced | 🔶 BLOCKED | F-015: no sandbox timeout enforcement |
| 9 | Depth-tier coverage distinguished from core coverage | ✅ UNIT_VALIDATED | Separate adapter tests, separate `detection_method` field |
| 10 | Known-positive regressions pass | 🔶 BLOCKED | F-010: vulnerable test accepts any warning |
| 11 | Known-negative regressions pass | 🔶 BLOCKED | F-011: patched test has no assertion |
| 12 | Licences and installation methods verified | 🔶 BLOCKED | F-021: no LICENSE file |
| 13 | Upgrade and rollback procedures tested | 🔶 BLOCKED | F-012: CI broken, cannot verify |

### Phase 2 Status: ❌ BLOCKED

All 13 criteria depend on Phase 1 passing first. Phase 1 is BLOCKED (20 P0 findings).

---

## Phase 3 — Non-EVM Branches

### Phase 3 Acceptance Criteria

Each non-EVM branch is evaluated independently. Phase 3 is complete when ALL of the following pass:

| # | Criterion | Solana | Move | Evidence Required |
|---|---|---|---|---|
| 1 | Ecosystem detection deterministic | 🔶 BLOCKED | 🔶 BLOCKED | `FrameworkDetector` works but Phase 1 must pass |
| 2 | Native build system supported | 🔶 BLOCKED | 🔶 BLOCKED | F-015: no sandbox, F-016: host env |
| 3 | Official toolchain version-pinned | 🔶 BLOCKED | 🔶 BLOCKED | `versions.lock` exists but Phase 1 must pass |
| 4 | Adapters independent of EVM assumptions | ✅ UNIT_VALIDATED | ✅ UNIT_VALIDATED | Separate adapter files, no EVM imports |
| 5 | Native output normalized through ecosystem-specific adapter | 🔶 BLOCKED | 🔶 BLOCKED | F-005: no JSON Schema validation |
| 6 | Property model technically compatible | 🔶 BLOCKED | 🔶 BLOCKED | F-007: empty invariants, F-008: tautological |
| 7 | Known-positive examples exist | 🔶 BLOCKED | 🔶 BLOCKED | Fixtures exist but F-010: no exact assertion |
| 8 | Known-negative examples exist | 🔶 BLOCKED | 🔶 BLOCKED | Fixtures exist but F-011: no assertion |
| 9 | Sandboxing enforced | ❌ FAILED | ❌ FAILED | F-015: no sandbox integration at all |
| 10 | Failure isolation enforced | 🔶 BLOCKED | 🔶 BLOCKED | F-015: sandbox not integrated |
| 11 | Reports identify ecosystem-specific limitations | 🔶 BLOCKED | 🔶 BLOCKED | F-005: no schema validation |
| 12 | Does not claim Foundry PoC support unless officially available | ✅ UNIT_VALIDATED | ✅ UNIT_VALIDATED | No Foundry PoC claims for non-EVM |

### Phase 3 Status: ❌ BLOCKED

All 12 criteria depend on Phase 1 and Phase 2 passing first. Both are BLOCKED.

---

## Phase Transition Rules

- Phase 1 must pass ALL 45 criteria before Phase 2 begins — **Phase 1: ❌ BLOCKED (20 P0)**
- Phase 2 must pass ALL 13 criteria before Phase 3 begins
- Each Phase 3 branch evaluated independently
- Phase advancement requires Lead Orchestrator approval
- Phase advancement requires verification ledger up-to-date
- Phase regression discovered later → halt, fix, re-verify