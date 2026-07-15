# Implementation Plan — Smart-Contract Security Pipeline

## Overview
Phase-gated implementation of the EVM static+fuzz auditing pipeline as specified in installation.md. Phase 1 = Production MVP for EVM. Phase 2 = depth tier. Phase 3 = non-EVM branches. This document tracks the dependency graph, phase boundaries, and critical path.

## Architecture Principles
1. **Deterministic where possible** — static analysis, scaffolding, normalization, dedup, classification. Non-deterministic fuzzing stages are reproducible via pinned corpus, not seed.
2. **Fail-safe isolation** — tool crash never kills the job. Partial results preserved.
3. **Immutable evidence** — raw tool outputs + execution context preserved for every finding.
4. **Configuration-driven** — no hardcoded resource limits, concurrency, or timeouts.
5. **Security-first** — every target and PoC runs sandboxed. No host secrets exposed.

## Phase 1 — EVM Production MVP

### Scope
```
Build → Static Analysis (Slither, Aderyn) → Normalization → Classification → 
Invariant Selection → Harness Gen → Fuzzing (Medusa, Echidna) → 
PoC Gen → Human Review → Report
```

### Vertical Slice 1 (Minimum Complete Pipeline)
```
Intake → Framework Detection → Deterministic Build → Slither Adapter → 
Normalized Finding → Schema Validation → Artifact Storage → Test Report
```

Target: One intentionally vulnerable Foundry fixture + one patched equivalent.

### Component Dependency Graph

```
P0 (planning docs)
  ├─ S1a: Intake Subsystem
  │     src/orchestrator/intake/
  │     - RepositoryManager (clone, pin, validate)
  │     - ScopeParser (target manifests)
  │     - IntakeManifest (schema + JSON output)
  │
  ├─ S1b: Detection
  │     src/orchestrator/detect/
  │     - FrameworkDetector (Foundry, Hardhat, Solidity)
  │     - EcosystemDetector (EVM, Solana, Move, Wasm)
  │     - Evidence-based deterministic detection
  │
  ├─ S1c: Build Resolver
  │     src/orchestrator/build/
  │     - CompilerResolver (solc versions via solc-select)
  │     - BuildExecutor (forge build or npx hardhat compile)
  │     - BuildManifest (compiler versions, artifacts, logs)
  │
  ├─ S1d: Shared Schema
  │     schemas/finding.json
  │     schemas/intake-manifest.json
  │     schemas/execution-manifest.json
  │     schemas/report.json
  │
  ├─ S1e: Slither Adapter
  │     src/orchestrator/adapters/slither/
  │     - SlitherRunner (version check, cmd gen, exec, timeout)
  │     - SlitherParser (JSON output → normalized findings)
  │     - SlitherSchema (tool-specific → shared schema)
  │
  ├─ S1f: Artifact Storage
  │     src/orchestrator/jobs/
  │     - ArtifactStore (persistent + ephemeral separation)
  │     - ExecutionManifest (provenance for every stage)
  │
  └─ VS1: Vertical Slice 1 Test
        tests/e2e/test_vertical_slice_1.py
```

### Phase 1 Component Sequence

```
S1a (Intake) ─┐
S1b (Detect) ─┤
S1c (Build) ──┤
S1d (Schema) ─┤
S1e (Slither)─┤
S1f (Storage)─┤
               └── VS1 (Test)
                               ┐
S2a (Eligibility gate)         │
S2b (Archetype Classifier)     ├── Parallel
S2c (Dedup)                    │   (after VS1)
S2d (Invariant Registry)       │
S2e (Aderyn Adapter)           │
S2f (Confidence Model)         ┘
                               ┐
S3a (Invariant Selection)      │
S3b (Harness Generation)       ├── Sequential
S3c (Medusa Adapter)           │   (depends on above)
S3d (Corpus Preservation)      │
S3e (Echidna Adapter)          │
S3f (PoC Generation)           │
S3g (Human Review)             ┘
                               ┐
S4a (Persistent Jobs)          │
S4b (Checkpoints)              ├── Infrastructure
S4c (Sandboxing)               │   (can overlap)
                               ┘
S5 (Phase 1 Acceptance) ──────→ Verify all 45 criteria
```

## Phase 2 — EVM Depth Tier (Future Scope)
- Halmos adapter (bounded symbolic execution)
- hevm adapter (bytecode equivalence checking)
- Kontrol adapter (full formal verification)
- Wake adapter (Python-native static + MGF)
- heimdall-rs adapter (bytecode decompilation for unverified targets)

## Phase 3 — Non-EVM Branches (Future Scope)
- Solana branch: Trident (fuzz) + sec3 X-Ray (static)
- Move branch: Aptos Move Prover + Sui Prover

## Key Milestones

| Milestone | Components | Acceptance Evidence |
|---|---|---|
| M1 (Planning) | All docs, schemas, config | Files reviewed, committed |
| M2 (VS1) | Intake→Detect→Build→Slither→Normalize→Schema→Store→Test | E2E test passes |
| M3 (Static Pipeline) | +Aderyn, +Dedup, +Confidence | Both static tools produce normalized output |
| M4 (Classification) | +Archetype classifier, +Invariant registry | Classifier selects archetype + compatible invariants |
| M5 (Fuzz Pipeline) | +Harness gen, +Medusa, +Echidna, +Corpus preservation | Fuzzer runs, corpus preserved, failing sequences captured |
| M6 (PoC Pipeline) | +PoC gen, +Human review | Qualifying result reaches human review with full provenance |
| M7 (Infrastructure) | +Persistent jobs, +Checkpoints, +Sandboxing | All resilience patterns tested |
| M8 (Phase 1 Complete) | All 45 acceptance criteria | Phase-acceptance.md updated |

## Repository Tree (Target)

```
hermes-pipeline/
├── README.md
├── ARCHITECTURE.md
├── IMPLEMENTATION_PLAN.md
├── THREAT_MODEL.md
├── LICENSE_MATRIX.md
├── KNOWN_LIMITATIONS.md
├── SECURITY.md
├── CONTRIBUTING.md
├── docs/
│   ├── verification-ledger.md
│   ├── agent-task-ledger.md
│   ├── phase-acceptance.md
│   ├── resource-calibration.md
│   └── program-eligibility.md
├── config/
│   ├── versions.lock
│   ├── env.example
│   ├── machine-profile.yaml
│   └── tools/
├── schemas/
│   ├── finding.json
│   ├── intake-manifest.json
│   ├── execution-manifest.json
│   └── report.json
├── src/orchestrator/
│   ├── __init__.py
│   ├── intake/
│   ├── eligibility/
│   ├── detect/
│   ├── build/
│   ├── adapters/
│   │   ├── base.py
│   │   ├── slither/
│   │   ├── aderyn/
│   │   └── medusa/ (Phase 1)
│   │   └── echidna/ (Phase 1)
│   ├── normalize/
│   ├── classify/
│   ├── deduplicate/
│   ├── harness/
│   ├── poc/
│   ├── report/
│   └── jobs/
├── invariants/
│   ├── registry.json
│   └── <archetype>/
├── datasets/
│   ├── findings/
│   ├── poc/
│   └── postmortems/
├── tests/
│   ├── unit/
│   ├── adapters/
│   ├── integration/
│   ├── e2e/
│   └── security/
├── fixtures/
│   ├── vulnerable/
│   └── patched/
├── docker/
│   ├── Dockerfile
│   ├── docker-compose.yml
│   └── entrypoint.sh
├── work/ (gitignored)
├── .cache/ (gitignored)
└── .gitignore
```

## Build and Test Commands

```bash
# Install project dependencies
pip install -e ".[dev]"

# Run tests (from project root)
pytest tests/unit/
pytest tests/adapters/
pytest tests/integration/
pytest tests/e2e/

# Run specific vertical slice
pytest tests/e2e/test_vertical_slice_1.py -v

# Lint
ruff check src/
mypy src/
```