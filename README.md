# Hermes Smart-Contract Security Pipeline

Automated smart-contract security auditing pipeline targeting bug-bounty programs. Phase-gated implementation: EVM Production MVP → EVM Depth Tier → Non-EVM Branches.

## Quick Start

```bash
# Prerequisites: Foundry, Python 3.10+, Docker, Go 1.21+, Node 20+
git clone <repo> && cd hermes-pipeline

# Run the E2E test (verifies full pipeline on vulnerable + patched fixtures)
python3 tests/e2e/test_vertical_slice_1.py
```

## Current Status: Phase 1 — EVM Production MVP

### ✅ Complete
- [x] Planning documents (9 deliverables)
- [x] Shared schemas (4 JSON Schemas)
- [x] Intake subsystem (remote + local)
- [x] Ecosystem/framework detection
- [x] Build resolver (Foundry, Hardhat, standard)
- [x] Slither adapter (version-check, run, parse, normalize)
- [x] Aderyn adapter (version-check, run, parse, normalize)
- [x] Medusa adapter (run, corpus preservation)
- [x] Echidna adapter (dependency check)
- [x] Archetype classifier (12 archetypes, rule-based)
- [x] Invariant registry (10 invariants, versioned, immutable)
- [x] Finding normalizer (schema validation)
- [x] Deterministic deduplication
- [x] Program eligibility gate (GATE ZERO)
- [x] Harness generation (Chimera-compatible)
- [x] Job state management (persistent + checkpoints)
- [x] Artifact storage
- [x] Reporting (final report with provenance)
- [x] Vertical Slice 1 (intake→build→Slither→normalize→schema→store→test)
- [x] Unit tests (17 tests, classifier + registry)
- [x] Adapter tests (7 tests, all adapters)
- [x] E2E test (vulnerable + patched fixtures)

### 🔲 In Progress
- Hardened sandboxing (Docker)
- PoC generation (scaffolding)
- Additional security tests

### Key Results
- **Vulnerable fixture**: 4 findings detected (reentrancy-eth at High)
- **Patched fixture**: 3 findings (reentrancy-eth correctly suppressed)
- **E2E runtime**: ~8.4 seconds for full pipeline

## Architecture

```
Intake → Detect → Build → Static Analysis (Slither + Aderyn)
  → Normalize → Dedup → Classify → Invariant Selection
  → Harness Gen → Fuzz (Medusa + Echidna) → PoC Gen
  → Human Review → Report
```

See `ARCHITECTURE.md` and `IMPLEMENTATION_PLAN.md` for full details.

## License

Orchestrator code: MIT. Toolchain tools have individual licenses (see `LICENSE_MATRIX.md`). AGPL-3.0 exposure from Slither, Medusa, Echidna, Halmos, hevm. Private use is fine; SaaS/hosted deployment requires legal review of AGPL §13.