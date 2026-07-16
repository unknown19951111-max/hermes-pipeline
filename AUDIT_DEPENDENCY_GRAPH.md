# Hermes Pipeline — Dependency Graph

**Audit date:** 2026-07-15T21:53:00-04:00
**Commit:** `aa1b60db3b90aae1709271d08bf66f2a750ba9a7`

---

## Component Dependency Map

### 1. CLI (`src/orchestrator/cli.py`)
- **Path:** `src/orchestrator/cli.py`
- **Used by:** Entry point (`hermes-pipeline` console script via `pyproject.toml:12`)
- **Integrates:** detection (`cmd_run`), build (`cmd_run`), Slither adapter (`cmd_run`), Aderyn adapter (`cmd_run`), Halmos adapter (`cmd_run`), Wake adapter (`cmd_run`), normalize (`cmd_run`), artifact_store (`cmd_run`), job_state (`cmd_run`)
- **NOT integrated:** intake, eligibility, classifier, invariant_registry, harness_generator, PoC generator, Medusa adapter, Echidna adapter, sandbox, review_queue, checkpoint_manager, circuit_breaker, failure_handler
- **Blocking findings:** F-014 (__main__ crash), F-015 (no sandbox), F-016 (host env)

### 2. Intake (`src/orchestrator/intake/__init__.py`)
- **Path:** `src/orchestrator/intake/__init__.py`
- **Used by:** E2E tests (`tests/e2e/test_vertical_slice_1.py:48,222`)
- **NOT used by:** CLI `cmd_run()`
- **Depends on:** git CLI (subprocess), `shutil`, `tempfile`, `uuid`, `hashlib`, `Path`
- **Broken:** `intake_remote()` - NameError on undefined `kwargs` (F-002, line 150)
- **Unsafe:** `intake_local()` - `shutil.copytree(symlinks=False)` follows symlinks (F-003, line 184)
- **Missing:** URL validation, commit verification, size limits, submodule pinning, manifest schema validation

### 3. Eligibility (`src/orchestrator/eligibility/__init__.py`)
- **Path:** `src/orchestrator/eligibility/__init__.py`
- **Used by:** Nothing (no integration with CLI or tests)
- **Depends on:** `json`, `re`, `datetime`, `Path`
- **Broken:** `EligibilitySnapshot.create()` always raises `EligibilityError` (F-001, lines 36 vs 55)

### 4. Detection (`src/orchestrator/detect/__init__.py`)
- **Path:** `src/orchestrator/detect/__init__.py`
- **Used by:** CLI `cmd_run()` (line 97), E2E tests (lines 62-63, 229-232)
- **Depends on:** `pathlib`, `re`
- **Status:** Working. Returns `DetectionResult` with ecosystem, framework, confidence, evidence.

### 5. Build (`src/orchestrator/build/__init__.py`)
- **Path:** `src/orchestrator/build/__init__.py`
- **Used by:** CLI `cmd_run()` (line 100), E2E tests (lines 67-69, 237-239)
- **Depends on:** `subprocess` (direct host execution), `os`, `Path`
- **Broken:** F-022 (`--via-ir` forced, line 46), F-023 (`build_env` created but not passed to subprocess, lines 30-31 vs 45-50)
- **Not integrated:** Sandbox (F-015)

### 6. Base Adapter (`src/orchestrator/adapters/base_adapter.py`)
- **Path:** `src/orchestrator/adapters/base_adapter.py`
- **Used by:** All concrete adapters (Slither, Aderyn, Echidna, Medusa, Halmos, Wake, etc.)
- **Depends on:** `subprocess` (direct host execution, line 127), `os`, `time`, `json`, `Path`
- **Broken:** F-004 (success=exit_code==0 or len(normalized)>0, line 172), F-015 (no sandbox), F-016 (host env inherited, no env parameter)

### 7. Slither Adapter (`src/orchestrator/adapters/`)
- **Used by:** CLI `cmd_run()`, E2E tests
- **Depends on:** BaseAdapter, `subprocess`, `json`
- **Status:** Adapter tests pass (5.3s parse test). But success logic wrong (F-004), no sandbox (F-015).

### 8. Aderyn Adapter (`src/orchestrator/adapters/`)
- **Used by:** CLI `cmd_run()`
- **Depends on:** BaseAdapter, `subprocess`, `json`
- **Status:** Adapter tests pass. But same F-004, F-015, F-016 issues.

### 9. Normalizer (`src/orchestrator/normalize/__init__.py`)
- **Path:** `src/orchestrator/normalize/__init__.py`
- **Used by:** CLI `cmd_run()`, E2E tests
- **Depends on:** `json`, `Path`
- **Broken:** F-005 (manual field checks, no `jsonschema.validate()` despite loading the schema file, lines 33-35 vs 37-74)
- **Also broken:** F-024 (schema tests don't use jsonschema)

### 10. Classifier (`src/orchestrator/classify/__init__.py`)
- **Path:** `src/orchestrator/classify/__init__.py`
- **Used by:** Unit tests only (`tests/unit/test_classifier.py`)
- **NOT used by:** CLI `cmd_run()`
- **Depends on:** `re`, `json`, invariant_registry.py
- **Depends on:** `invariant_registry.py` (for `select_for_archetype()`)
- **Issue:** References phantom invariant IDs not in registry

### 11. Invariant Registry (`src/orchestrator/classify/invariant_registry.py`)
- **Path:** `src/orchestrator/classify/invariant_registry.py`
- **Used by:** Classifier unit tests
- **NOT used by:** CLI `cmd_run()`
- **Data file:** `invariants/registry.json`
- **Broken:** F-006 (9/10 invariants falsely VERIFIED, no source commit, no validation history)

### 12. Harness Generator (`src/orchestrator/harness/__init__.py`)
- **Path:** `src/orchestrator/harness/__init__.py`
- **Used by:** Unit tests only (not directly, but indirectly through test imports)
- **NOT used by:** CLI `cmd_run()`
- **Depends on:** `Path`, `subprocess` (for compilation verification)
- **Broken:** F-007 (empty invariants for 4 archetypes, lines 133-160), F-008 (tautological assertion, line 129)

### 13. PoC Generator (`src/orchestrator/poc/__init__.py`)
- **Path:** `src/orchestrator/poc/__init__.py`
- **Used by:** Unit tests only (`tests/unit/test_phase1_remaining.py`)
- **NOT used by:** CLI `cmd_run()`
- **Depends on:** `subprocess` (forge test), `os`, `Path`, `json`, `tempfile`
- **Broken:** F-009 (both PASSED and FAILED return True, lines 212-220)

### 14. Sandbox (`src/orchestrator/jobs/sandbox.py`)
- **Path:** `src/orchestrator/jobs/sandbox.py`
- **Used by:** Nothing (not integrated)
- **Depends on:** Docker (`docker-py` or `docker compose`), `os`, `json`, `subprocess`
- **Broken:** F-015 (exists but never called from build or adapter code)

### 15. Job State (`src/orchestrator/jobs/__init__.py`)
- **Path:** `src/orchestrator/jobs/__init__.py`
- **Used by:** E2E tests
- **Depends on:** `json`, `os`, `Path`, `time`, `datetime`, `uuid`
- **Status:** Working. Includes `ArtifactStore`, `JobState`, `Deduplicator`.

### 16. Failure Isolation (`src/orchestrator/jobs/failure_isolation.py`)
- **Path:** `src/orchestrator/jobs/failure_isolation.py`
- **Used by:** Unit tests only (`tests/unit/test_phase1_remaining.py`)
- **NOT used by:** CLI `cmd_run()`, build, or adapters
- **Depends on:** `json`, `os`, `time`, `Path`, `collections`
- **Status:** Working in unit tests. Contains `CircuitBreaker`, `FailureHandler`, `CheckpointManager`.

### 17. CI/CD (`.github/workflows/ci.yml`)
- **Path:** `.github/workflows/ci.yml`
- **Used by:** GitHub Actions (never actually run — F-012)
- **Broken:** F-012 (working-directory: /workspace), F-013 (unconditional success echo), F-019 (package not installed)

### 18. E2E Test (`tests/e2e/test_vertical_slice_1.py`)
- **Path:** `tests/e2e/test_vertical_slice_1.py`
- **Integrates:** intake → detection → build → Slither → normalize → dedup → report
- **Depends on:** `RepositoryManager`, `FrameworkDetector`, `BuildExecutor`, `SlitherAdapter`, `FindingNormalizer`, `Deduplicator`, `ArtifactStore`, `JobState`
- **Broken:** F-010 (vulnerable test accepts any warning, lines 170-178), F-011 (patched test no assertion, lines 270-275), F-014 (__main__ crash, lines 199, 293, 311)

---

## Blocking Graph

```
F-001 (Eligibility) ─── F-017 (False phase claims) ─── F-018 (False ledger)
F-002 (Intake kwargs) ─┤
F-003 (Symlinks) ──────┤
F-004 (Adapter success) ┤
F-005 (Schema) ────────┤
F-006 (Invariants) ────┤
F-007 (Harness empty) ─┤
F-008 (Harness taut) ──┤
F-009 (PoC always True) ┤
F-010 (Vuln test) ─────┤
F-011 (Patched test) ──┤
F-012 (CI dir) ────────┤
F-013 (CI output) ─────┤
F-014 (E2E crash) ─────┤
F-015 (No sandbox) ────┼──→ PRODUCTION RELEASE: REJECTED
F-016 (Host env) ──────┤
F-022 (--via-ir) ──────┤
F-023 (build_env) ─────┤
F-024 (Schema tests) ──┤
                        │
F-019 (CI install) ───┐ │
F-020 (Dependencies) ─┘ │
F-021 (LICENSE) ────────┘
```

---

## Integration Status Summary

| Component | Integrated into CLI? | Has Working Tests? | Has Verified Fix? | Ready for Production? |
|-----------|--------------------|--------------------|-------------------|-------------------|
| Intake | No | E2E (local only) | No (F-002, F-003) | No |
| Eligibility | No | No | No (F-001) | No |
| Detection | Yes | Yes | Yes | Yes |
| Build | Yes | Yes | No (F-015, F-022, F-023) | No |
| Slither | Yes | Yes | No (F-004, F-015, F-016) | No |
| Aderyn | Yes | Yes | No (F-004, F-015, F-016) | No |
| Echidna | No | Dependency only | No (F-015) | No |
| Medusa | No | Dependency only | No (binary missing) | No |
| Halmos | Yes | Test construction | No (F-015) | No |
| Wake | Yes | Test construction | No (F-015) | No |
| Classifier | No | Yes | Yes | Prototype |
| Invariant Registry | No | Yes | No (F-006) | No |
| Harness Generator | No | No (indirect) | No (F-007, F-008) | No |
| PoC Generator | No | Unit only | No (F-009) | No |
| Human Review | No | Unit only | Yes | Prototype |
| Sandbox | No | Unit only | No (F-015) | No |
| Job State | No | E2E | Yes | Yes |
| Circuit Breaker | No | Yes | Yes | Yes |
| Failure Handler | No | Yes | Yes | Yes |
| CI/CD | No | No | No (F-012, F-013) | No |
| Normalizer | Yes | Yes | No (F-005) | No |
| Deduplicator | Yes | E2E | No (cross-tool) | Prototype |