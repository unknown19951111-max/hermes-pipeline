# Contributing

## Development Setup

```bash
pip install -e ".[dev]"
```

## Running Tests

```bash
# Unit tests
python3 tests/unit/test_classifier.py
python3 tests/unit/test_invariant_registry.py

# Adapter tests
python3 tests/adapters/test_all_adapters.py

# E2E test (requires Foundry, Slither, Aderyn, Medusa, Echidna)
python3 tests/e2e/test_vertical_slice_1.py
```

## Phase Boundaries

- Phase 1 (EVM Production MVP) must pass all 45 acceptance criteria
- Phase 2 (EVM Depth Tier) adds optional symbolic/formal tools
- Phase 3 (Non-EVM Branches) adds Solana/Move support

See `docs/phase-acceptance.md` for detailed acceptance criteria.

## Commit Convention

- Each commit represents one coherent implementation change
- Small, testable, reviewable commits preferred
- Test evidence preserved with implementation
- Failed tests are never hidden