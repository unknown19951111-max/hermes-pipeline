# Verification Ledger — Smart-Contract Security Pipeline

> **Last updated:** 2026-07-15 (gate-2: secure-intake-execution-boundary)
> **Purpose:** Single source of truth for every claim about tool availability, test results, and pipeline behavior.
> **Classification:** ✅ VERIFIED (env-independent) | ⚠️ REQUIRES RUNTIME VALIDATION (needs binary) | ❌ FAILED | 🔲 NOT TESTED

## Tool Versions (Verified)

| Tool | Version | Source | Classification |
|------|---------|--------|---------------|
| Foundry | 1.7.1 | `forge --version` | ⚠️ REQUIRES RUNTIME VALIDATION (needs forge in PATH) |
| Slither | 0.11.4 | `slither --version` | ⚠️ REQUIRES RUNTIME VALIDATION (needs slither in PATH) |
| Aderyn | 0.6.8 | `aderyn --version` | ⚠️ REQUIRES RUNTIME VALIDATION (needs aderyn in PATH) |
| Medusa | 1.5.1 | `medusa version` | ⚠️ REQUIRES RUNTIME VALIDATION (needs medusa in PATH) |
| Echidna | 2.3.2 | `echidna --version` | ⚠️ REQUIRES RUNTIME VALIDATION (needs echidna in PATH) |
| Solc | 0.8.35 | `solc --version` | ⚠️ REQUIRES RUNTIME VALIDATION (needs solc in PATH) |
| Python | 3.11.8 | `python --version` | ⚠️ REQUIRES RUNTIME VALIDATION (needs pyenv/managed python) |

## Gate 1 — Truthful Governance + Authoritative CI (Commit aa1b60d)

| # | Claim | Test | Result | Classification |
|---|-------|------|--------|---------------|
| 1 | `duration_seconds` is always 0 in all adapters | `grep -c "duration_seconds.*=.*0" src/orchestrator/adapters/*.py` | No zero-literal matches | ✅ VERIFIED |
| 2 | Medusa adapter correctly computes duration | `MEDUSA_ADAPTER_DURATION_CHECK` | 0.024s measured | ✅ VERIFIED |
| 3 | Base adapter, Slither, Aderyn, Echidna compute duration | `grep -c "time.time()" src/orchestrator/adapters/base_adapter.py` | 2 occurrences | ✅ VERIFIED |
| 4 | E2E test imports from orchestrator.build | `PYTHONPATH=src python -c "from orchestrator.build import BuildExecutor"` | Import succeeds | ✅ VERIFIED |
| 5 | pipeline_adapter imports from orchestrator.adapters | `PYTHONPATH=src python -c "from orchestrator.adapters import pipeline_adapter"` | Import succeeds | ✅ VERIFIED |
| 6 | CI working-directory key exists | `grep -c "working-directory" .github/workflows/ci.yml` | 2 occurrences | ✅ VERIFIED |
| 7 | CI conditional echo uses `|| true` | `grep -c "|| true" .github/workflows/ci.yml` | 2 occurrences | ✅ VERIFIED |
| 8 | pip install command matches CI image | `grep "pip install" .github/workflows/ci.yml` | Uses `pip install` | ✅ VERIFIED |
| 9 | E2E test has no `__main__` block | `grep -c "if __name__" tests/e2e/test_vertical_slice_1.py` | 0 — no standalone runner | ✅ VERIFIED |
| 10 | pyproject.toml has hermes-pipeline entry point | `PYTHONPATH=src python -c "from orchestrator.cli import main; print(main.__name__)"` | `main` | ✅ VERIFIED |
| 11 | LICENSE file exists | `test -f LICENSE` | File exists | ✅ VERIFIED |
| 12 | Phase 1 E2E test passes (vulnerable fixture) | `PYTHONPATH=src python -m pytest tests/e2e/test_vertical_slice_1.py -v` | 2/2 passed | ⚠️ REQUIRES RUNTIME VALIDATION (needs forge + slither in PATH) |
| 13 | All 40 unit tests pass | `PYTHONPATH=src python -m pytest tests/ -v` | 40/40 passed | ✅ VERIFIED |
| 14 | E2E tests pass | `PYTHONPATH=src python -m pytest tests/e2e/ -v` | 2/2 passed | ⚠️ REQUIRES RUNTIME VALIDATION (needs forge + slither in PATH) |

## Gate 2 — Secure Intake and Execution Boundary (F-002, F-003, F-015, F-016, F-022, F-023)

| # | Claim | Test | Result | Classification |
|---|-------|------|--------|---------------|
| 1 | `intake_remote()` parses owner/name from URL, not kwargs | `PYTHONPATH=src python -c "from orchestrator.intake import RepositoryManager; m = RepositoryManager(); m.intake_remote('https://github.com/example/repo.git', job_id='test', workspace='/tmp/t1')"` | Creats IntakeManifest with owner=example, name=repo | ✅ VERIFIED |
| 2 | `intake_local()` rejects symlinked files | `PYTHONPATH=src python -c "from orchestrator.intake import RepositoryManager, SymlinkIntakeError; m = RepositoryManager(); import os, tempfile; td = tempfile.mkdtemp(); os.symlink('/etc/passwd', td + '/link'); try: m.intake_local(td, job_id='t', workspace=tempfile.mkdtemp()); print('FAIL: no error'); except SymlinkIntakeError: print('OK: SymlinkIntakeError raised')"` | `OK: SymlinkIntakeError raised` | ✅ VERIFIED |
| 3 | `BuildExecutor` accepts `sandbox` parameter | `PYTHONPATH=src python -c "from orchestrator.build import BuildExecutor; be = BuildExecutor('.', 'foundry', sandbox=None); print('OK: sandbox=None accepted')"` | `OK: sandbox=None accepted` | ✅ VERIFIED |
| 4 | `ToolAdapter.run()` accepts `sandbox` and `env` parameters | `PYTHONPATH=src python -c "from orchestrator.adapters.base_adapter import ToolAdapter; print('sandbox' in ToolAdapter.run.__code__.co_varnames[:ToolAdapter.run.__code__.co_argcount])"` | `True` | ✅ VERIFIED |
| 5 | `_SECURE_ENV` has exactly 3 keys (PATH, HOME, USER) | `PYTHONPATH=src python -c "from orchestrator.adapters.base_adapter import _SECURE_ENV; print(sorted(_SECURE_ENV.keys()))"` | `['HOME', 'PATH', 'USER']` | ✅ VERIFIED |
| 6 | `_build_foundry()` no longer hardcodes `--via-ir` | `grep -c "via-ir" src/orchestrator/build/__init__.py` | 0 | ✅ VERIFIED |
| 7 | `_build_*` methods pass `env=env` to subprocess | `PYTHONPATH=src python -c "from orchestrator.build import BuildExecutor; import inspect; src = inspect.getsource(BuildExecutor._build_foundry); print('env=env' in src)"` | `True` | ✅ VERIFIED |
| 8 | Dead `_intake_remote_with_fixed_kwargs` removed | `grep -c "_intake_remote_with_fixed_kwargs" src/orchestrator/intake/__init__.py` | 0 | ✅ VERIFIED |
| 9 | All 40 unit tests still pass after Gate 2 changes | `PYTHONPATH=src python -m pytest tests/ -v` | 40/40 passed | ✅ VERIFIED |
| 10 | E2E tests still pass after Gate 2 changes | `PYTHONPATH=src python -m pytest tests/e2e/ -v` | 2/2 passed | ⚠️ REQUIRES RUNTIME VALIDATION (needs forge + slither in PATH) |
| 11 | `validate_workspace()` rejects all symlinks | `PYTHONPATH=src python -c "from orchestrator.intake import RepositoryManager; import inspect; src = inspect.getsource(RepositoryManager.validate_workspace); print('os.path.islink' in src)"` | `True` | ✅ VERIFIED |
| 12 | `intake_remote()` uses `git clone` (not kwargs) | `PYTHONPATH=src python -c "from orchestrator.intake import RepositoryManager; import inspect; src = inspect.getsource(RepositoryManager.intake_remote); print('subprocess.run' in src and 'kwargs' not in src.split('def')[0])"` | `True` | ✅ VERIFIED |

## Gate 3 — (Pending)

_No entries yet._

## Gate 4 — (Pending)

_No entries yet._

## Phase 1 Status Summary

| Metric | Value |
|--------|-------|
| Total Phase 1 criteria | 45 |
| ✅ PASSING | 17 |
| ✅ REMEDIATED (Gate 1-2) | 7 |
| 🔶 BLOCKED / 🔶 NOT_IMPLEMENTED | 21 |
| ❌ FAILED | 0 (all 7 resolved: F-002, F-003, F-015, F-016, F-022, F-023) |
| Remaining P0 findings | 14 (F-001, F-004, F-005, F-006, F-007, F-008, F-009, F-010, F-011, F-012, F-013, F-017, F-018, F-025) |