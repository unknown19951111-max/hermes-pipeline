# Hermes Pipeline — Corrected Remediation Specification

> **Audit date:** 2026-07-15T21:53:00-04:00
> **Repository:** `/Users/vusek/Documents/Automation_pipeline`
> **Remote:** `git@github.com:unknown19951111-max/hermes-pipeline.git`
> **Commit:** `aa1b60db3b90aae1709271d08bf66f2a750ba9a7`
> **Branch:** `master`
> **Working tree:** Clean (1 untracked file: `AUDIT_REMEDIATION.md` from prior audit, excluded)
> **Python:** 3.13.2 (CPython) | **pytest:** 7.4.4 | **OS:** macOS 13.7.8 (Darwin x86_64)
> **Agents:** 5 (auditor, verifier, evidence_collector, remediation_writer, QA)
> **Previous audit corrected:** Yes — removed unsupported claims (wrong test-failure count, wrong depth-tier/non-EVM status, time estimates, speculative invariant counts)

---

## Test Evidence

| Suite | Result | Detail |
|-------|--------|--------|
| `pytest` (40 tests) | **VERIFIED_PASS** | 40/40 pass, 0 fail, 0 errors, 0 skipped, 22.0s |
| Depth-tier (19 tests) | **VERIFIED_PASS** | 19/19 pass, exits 0 |
| Non-EVM (25 tests) | **VERIFIED_PASS** | 25/25 pass, exits 0 |
| E2E test functions (2) | **VERIFIED_PASS** | Both pass via pytest |
| E2E `__main__` section | **VERIFIED_FAIL** | Exits 1: `TypeError: len(None)` (F-014) |

**Previous audit claim corrected:** The prior audit incorrectly stated "9 tests failed" and "depth-tier reports FAIL exits 0". These claims were from an earlier code revision. The current state is 40/40 pytest pass, depth-tier 19/19 PASS exits 0, non-EVM 25/25 PASS exits 0.

---

## Confirmed Findings

### P0 (CRITICAL) — 20 findings

| ID | Section | Title | Status |
|----|---------|-------|--------|
| F-001 | Eligibility | `_validate()` requires `"status"`, `create()` writes `"program_status"` | CONFIRMED |
| F-002 | Intake | Remote intake uses undefined `kwargs` variable | CONFIRMED |
| F-003 | Intake | `shutil.copytree(symlinks=False)` copies external symlink targets | CONFIRMED |
| F-004 | Adapters | `success = exit_code == 0 or len(normalized) > 0` masks parse failures | CONFIRMED |
| F-005 | Schema | JSON Schema loaded but never used for validation | CONFIRMED |
| F-006 | Invariants | 8/10 invariants VERIFIED without source commit, validation, or implementation | CONFIRMED |
| F-007 | Harness | Lending/DEX/governance/bridge invariants are empty function bodies | CONFIRMED |
| F-008 | Harness | ERC-4626 `totalAssets() >= 0` is tautologically true for uint256 | CONFIRMED |
| F-009 | PoC | Both PASSED and FAILED test outcomes return `reproduction=True` | CONFIRMED |
| F-010 | Tests | Vulnerable fixture test accepts any Slither warning as reentrancy | CONFIRMED |
| F-011 | Tests | Patched fixture test does not assert reentrancy absence | CONFIRMED |
| F-012 | CI | `working-directory: /workspace` does not exist in GitHub Actions | CONFIRMED |
| F-013 | CI | Unconditional `echo "CI ✅ — all tests passed"` | CONFIRMED |
| F-014 | CLI | E2E `__main__` crashes: `TypeError: len(None)` | CONFIRMED |
| F-015 | Sandbox | Sandbox module exists but is never called from build or adapter code | CONFIRMED |
| F-016 | Adapters | Full host environment inherited by target-controlled subprocesses | CONFIRMED |
| F-017 | Docs | All 45 phase-acceptance criteria marked ✅ despite broken components | CONFIRMED |
| F-018 | Docs | Agent task ledger uses global test count, not component evidence | CONFIRMED |
| F-022 | Build | `forge build --via-ir` forced, altering native compilation | CONFIRMED |
| F-024 | Tests | Schema test does not invoke JSON Schema validator | CONFIRMED |

### P1 (HIGH) — 4 findings

| ID | Section | Title | Status |
|----|---------|-------|--------|
| F-019 | CI | CI does not install the application package | CONFIRMED |
| F-020 | Packaging | No runtime dependencies declared in `pyproject.toml` | CONFIRMED |
| F-021 | Packaging | No root `LICENSE` file despite ISC claim | CONFIRMED |
| F-023 | Build | `build_env` created but never passed to `subprocess.run()` | CONFIRMED |

### Unresolved / Missing Evidence

| Issue | Reason |
|-------|--------|
| Depth-tier formal-analysis adapters (Halmos, hevm, Wake, Heimdall, Kontrol) | Runtime compatibility with real contracts not tested; tests validate command construction only |
| Medusa fuzzer integration | `medusa` binary not installed in audit environment; adapter tests verify dependency check only |
| Anchor/Solana CLI adapter | `anchor` binary not installed in audit environment; adapter tests verify command construction |
| Live remote repository intake | Requires network access; not tested in audit environment |
| Container sandbox execution | Requires Docker; not available in audit environment |
| Real PoC exploit reproduction | Requires a working exploit PoC; not tested in audit environment |
| Cross-tool deduplication (Slither vs Aderyn) | Dedup keys use tool-specific rule IDs; cross-tool grouping not tested |

---

## Production Status

| Area | Status |
|------|--------|
| Documentation and status | **BLOCKED** (F-017, F-018) |
| CI/CD | **BLOCKED** (F-012, F-013, F-019) |
| CLI orchestration | **BLOCKED** (F-014, F-015, F-016) |
| Repository intake | **CRITICAL BLOCKER** (F-002, F-003) |
| Eligibility | **BLOCKED** (F-001) |
| Build execution | **BLOCKED** (F-015, F-022, F-023) |
| Adapter execution | **CRITICAL BLOCKER** (F-004, F-015, F-016) |
| Schema enforcement | **CRITICAL BLOCKER** (F-005, F-024) |
| Invariant registry | **CRITICAL BLOCKER** (F-006) |
| Harness generation | **CRITICAL BLOCKER** (F-007, F-008) |
| PoC validation | **CRITICAL BLOCKER** (F-009) |
| Testing | **BLOCKED** (F-010, F-011, F-014, F-024) |
| Sandbox | **CRITICAL BLOCKER** (F-015) |
| Configuration | INCOMPLETE (F-020, F-021) |
| **Overall** | **PRODUCTION RELEASE REJECTED** |

---

## Dependency-Ordered Remediation Gates

### Gate 1 — Truthful Governance and Authoritative CI

**Purpose:** Restore truthful documentation and make CI reliable.

| Order | Issue | File | Fix |
|-------|-------|------|-----|
| 1 | F-017 | `docs/phase-acceptance.md` | Replace all ✅ with actual status from acceptance ledger. Mark Phase 1 as BLOCKED. |
| 2 | F-018 | `docs/agent-task-ledger.md` | Replace global test count with per-component evidence. |
| 3 | F-012 | `.github/workflows/ci.yml:14` | Change `working-directory: /workspace` to `working-directory: ${{ github.workspace }}` or remove it. |
| 4 | F-013 | `.github/workflows/ci.yml:64` | Remove unconditional `echo "CI ✅ — all tests passed"`. Use conditional step if summary needed. |
| 5 | F-019 | `.github/workflows/ci.yml:26-27` | Add `pip install -e .` to install step. |
| 6 | F-014 | `tests/e2e/test_vertical_slice_1.py:295-314` | Remove the `__main__` section. Run via pytest only. |
| 7 | F-020 | `pyproject.toml` | Add `dependencies = ["jsonschema>=4.0"]` and `[project.optional-dependencies] dev = [...]`. |
| 8 | F-021 | Root | Create `LICENSE` file with ISC text. Add `license = {file = "LICENSE"}` to `pyproject.toml`. |

**Acceptance:** `pytest` exits 0. CI workflow runs without hardcoded success output. No ✅ markers in documentation without verifiable evidence.

---

### Gate 2 — Secure Intake and Execution Boundary

**Purpose:** Fix remote intake, reject symlinks, and route all execution through the sandbox.

| Order | Issue | File | Fix |
|-------|-------|------|-----|
| 9 | F-002 | `src/orchestrator/intake/__init__.py:88,150-151` | Replace `kwargs.get()` with URL-derived owner/name. Add typed `RemoteTarget` dataclass. Validate URL. |
| 10 | F-003 | `src/orchestrator/intake/__init__.py:184` | Add symlink detection before `copytree`. Reject intake if any symlink exists. |
| 11 | F-015 | `src/orchestrator/build/__init__.py`, `src/orchestrator/adapters/base_adapter.py` | Route all build and adapter execution through `SandboxManager.run_in_sandbox()`. |
| 12 | F-016 | `src/orchestrator/adapters/base_adapter.py:127-131`, `src/orchestrator/build/__init__.py:45-50` | Add environment allowlist. Pass only allowlisted vars to `subprocess.run()`. |
| 13 | F-023 | `src/orchestrator/build/__init__.py:30-31` | Pass `env=build_env` to each `subprocess.run()` call. |
| 14 | F-022 | `src/orchestrator/build/__init__.py:46` | Remove `--via-ir` from default build. Make override explicit and recorded. |

**Acceptance:** Remote intake succeeds with valid URL. Symlinks are rejected. All target-controlled code runs inside sandbox. Host environment is not inherited.

---

### Gate 3 — First Exact EVM Vertical Slice

**Purpose:** Complete a verifiable end-to-end analysis of a known vulnerable fixture.

| Order | Issue | File | Fix |
|-------|-------|------|-----|
| 15 | F-004 | `src/orchestrator/adapters/base_adapter.py:172` | Track three success flags: `process_success`, `parse_success`, `overall_success`. |
| 16 | F-005 | `src/orchestrator/normalize/__init__.py:37-74` | Replace manual validation with `jsonschema.validate(finding, self.schema)`. |
| 17 | F-024 | `tests/adapters/test_all_adapters.py:114-124` | Add `jsonschema.validate()` test against `schemas/finding.json`. |
| 18 | F-010 | `tests/e2e/test_vertical_slice_1.py:170-178` | Assert `"reentrancy-eth"` in exact rule IDs. Remove soft-pass fallback. |
| 19 | F-011 | `tests/e2e/test_vertical_slice_1.py:270-275` | Assert `"reentrancy-eth"` not in patched findings. |

**Acceptance:** `intake → native forge build → Slither → JSON Schema validation → normalized finding → exact reentrancy-eth assertion → exact patched absence → validated report`.

---

### Gate 4 — Restore Finding and Invariant Trust

**Purpose:** Enforce schema validation, correct invariant registry, fix PoC verification.

| Order | Issue | File | Fix |
|-------|-------|------|-----|
| 20 | F-006 | `invariants/registry.json` | Demote 8 VERIFIED invariants to CANDIDATE. Add promotion function requiring full evidence. |
| 21 | F-007 | `src/orchestrator/harness/__init__.py:133-160` | Remove empty invariant functions. Add real assertions or emit INCOMPATIBLE_INVARIANT. |
| 22 | F-008 | `src/orchestrator/harness/__init__.py:129` | Replace `totalAssets() >= 0` with meaningful assertion. |
| 23 | F-009 | `src/orchestrator/poc/__init__.py:212-220` | PASSED must return False. FAILED must verify expected assertion failure. |
| 24 | F-001 | `src/orchestrator/eligibility/__init__.py:36,55` | Align field names: change `_validate()` to require `"program_status"`, update `_evaluate_from_data()`. |

**Acceptance:** No VERIFIED invariant without evidence. Every generated invariant has assertions. PoC reproduction=false for invalid scenarios. Eligibility gate works.

---

### Gate 5 — Build One Real Fuzzing and PoC Path

**Purpose:** Implement a complete fuzzing-to-PoC pipeline for one archetype.

| Order | Work | Detail |
|-------|------|--------|
| 25 | Medusa integration | Ensure Medusa adapter can run against a real invariant-bearing harness |
| 26 | Corpus preservation | Capture and hash complete corpus after fuzzing run |
| 27 | Failure sequence | Extract minimized failing sequence from corpus |
| 28 | Foundry reproduction | Convert failing sequence to Foundry PoC test |
| 29 | Patched negative | Run PoC against patched fixture; verify absence |
| 30 | Human approval | Route through HumanReviewQueue; require reviewer approval for confirmed_vulnerability |

**Acceptance:** Vulnerable fixture fails the exact invariant. Patched fixture does not. Complete corpus is hashed. Failing sequence independently reproduces. Report does not claim bit-for-bit determinism.

---

### Gate 6 — Reconsider Phase 2 and Phase 3

**Do not resume formal-analysis expansion or non-EVM acceptance until all previous gates pass.**

---

## Remediation Quality Checks

Each proposed fix must pass adversarial review:

| Reject if... | Example |
|--------------|---------|
| Adds broad `**kwargs` to suppress failure | Adding `**kwargs` to `intake_remote()` without typed target |
| Preserves hostile symlinks in workspace | Keeping symlinks and validating them post-copy |
| Converts missing data to safe-looking defaults | Defaulting `program_status` to `"unknown"` without validation |
| Treats `analysis_failure` record as adapter success | Current F-004 behavior |
| Treats any failed PoC test as reproduction | Current F-009 behavior |
| Marks metadata-only invariants as verified | Current F-006 behavior |
| Validates documentation through text matching | `grep -c '✅'` as acceptance check |
| Declares phase completion from global test counts | Current F-017/F-018 behavior |
| Uses direct host subprocess for untrusted code | Current F-015/F-016 behavior |
| Adds distributed infrastructure before single-node works | Adding Kubernetes before fixing sandbox |

---

## Residual Risk Summary

After all gates pass, the following residual risks remain:

1. **Tool version drift:** External tools (Slither, Aderyn, Medusa, etc.) evolve independently. Pipeline must pin versions and run compatibility tests.
2. **False negatives in static analysis:** No static analyzer finds all vulnerabilities. Pipeline coverage is limited to supported detectors.
3. **Network-dependent fork testing:** Fork-based PoC validation depends on RPC availability and state consistency.
4. **Single-node bottleneck:** The architecture is single-node. Horizontal scaling requires additional design.
5. **Non-EVM gap:** Solana and Move branches are not production-ready. Formal-analysis tier is experimental.

These risks are acceptable for a Phase 1 production MVP. They must be documented in the deployment readiness checklist.

---

## Reference: Previous Audit Corrections

| Previous Claim | Corrected | Reason |
|----------------|-----------|--------|
| "9 tests failed" | "40 tests passed, 0 failed" | Tests were run against earlier code revision; P0 remediation commits fixed them |
| "Depth-tier reports FAIL, exits 0" | "19/19 PASS, exits 0" | Code was updated; test suite now passes |
| "Non-EVM reports FAIL, exits 0" | "25/25 PASS, exits 0" | Code was updated; test suite now passes |
| "1 hour for Phase 1 fixes" | Removed | Implementation duration predictions are unsupported |
| "8 invariants falsely verified" | 8 of 10 invariants | Exact count verified from registry audit |
| "`**kwargs` fix for `intake_remote()`" | Rejected | Typed `RemoteTarget` required; `**kwargs` would suppress the error without fixing the contract |
| "Preserve symlinks and validate" | Rejected | Phase 1 policy: reject ALL symlinks during intake; do not preserve untrusted symlinks |
| "`grep -c '✅'` as verification" | Rejected | Acceptance ledger requires structured evidence, not text matching |
| "40 tests pass" without evidence | 40/40 verified with JUnit XML evidence | Full test output preserved as audit artifact |