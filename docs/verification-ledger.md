# Verification Ledger — Smart-Contract Security Pipeline
# Last updated: 2026-07-15

## Status

| Claim ID | Claim | Status | Source | URL | Version | Verified | Agent |
|---|---|---|---|---|---|---|---|
| V001 | Foundry available as CLI | ✅ VERIFIED | Local install | — | 1.7.1 (4072e48705af9d93e3c0f6e29e93b5e9a40caed8) | 2026-07-15 | Agent 1 |
| V002 | Forge version check works | ✅ VERIFIED | `forge --version` | — | 1.7.1 | 2026-07-15 | Agent 1 |
| V003 | Echidna available as CLI | ✅ VERIFIED | `echidna --version` | — | 2.3.2 | 2026-07-15 | Agent 1 |
| V004 | Slither available as CLI | ✅ VERIFIED | `slither --version` | — | 0.11.4 | 2026-07-15 | Agent 1 |
| V005 | Aderyn installed | ✅ VERIFIED | `aderyn --version` | — | 0.6.8 | 2026-07-15 | Agent 1 |
| V006 | Medusa installed | ✅ VERIFIED | `medusa --version` via go install | — | 1.5.1 | 2026-07-15 | Agent 1 |
| V007 | Aderyn npm install working | ✅ VERIFIED | npm i -g @cyfrin/aderyn | — | 0.6.8 | 2026-07-15 | Agent 1 |
| V008 | Medusa go install working | ✅ VERIFIED | `go install github.com/crytic/medusa@latest` | — | 1.5.1 | 2026-07-15 | Agent 1 |
| V009 | Slither JSON output format | ✅ VERIFIED | `slither . --json` output | github.com/crytic/slither | 0.11.4 | 2026-07-15 | Agent 1 |
| V010 | Aderyn JSON output format | ✅ VERIFIED | `aderyn -o file.json` output | github.com/cyfrin/aderyn | 0.6.8 | 2026-07-15 | Agent 1 |
| V011 | Solc version management | ✅ VERIFIED | solc-select versions | — | 0.8.35 | 2026-07-15 | Agent 1 |
| V012 | Slither detects reentrancy-eth | ✅ VERIFIED | vs vulnerable fixture | Runtime | 0.11.4 | 2026-07-15 | Agent 1 |
| V013 | Aderyn detects reentrancy-state-change | ✅ VERIFIED | vs vulnerable fixture | Runtime | 0.6.8 | 2026-07-15 | Agent 1 |
| V014 | Patched fixture suppresses reentrancy-eth | ✅ VERIFIED | vs patched fixture | Runtime | 0.11.4 | 2026-07-15 | Agent 1 |
| V015 | E2E pipeline passes (VS1) | ✅ VERIFIED | `test_vertical_slice_1.py` | Runtime | v0.1.0 | 2026-07-15 | Agent 1 |
| V016 | Adapter tests all pass (7 tests) | ✅ VERIFIED | `test_all_adapters.py` | Runtime | v0.1.0 | 2026-07-15 | Agent 1 |
| V017 | Classifier tests all pass (10 tests) | ✅ VERIFIED | `test_classifier.py` | Runtime | v0.1.0 | 2026-07-15 | Agent 1 |
| V018 | Registry tests all pass (9 tests) | ✅ VERIFIED | `test_invariant_registry.py` | Runtime | v0.1.0 | 2026-07-15 | Agent 1 |

## License Verification TODO

- Aderyn: stated GPL-3.0 — verify with `gh repo view Cyfrin/aderyn --json licenseInfo`
- Medusa: AGPL-3.0 — PREVIOUSLY VERIFIED
- heimdall-rs: unverified
- Trident: unverified
- sec3 X-Ray: unverified
- Sui Prover: unverified

## Known Platform Contradictions

- Development on macOS ARM64 (contradicts production target of Ubuntu x86-64)
- Production deployment will use Docker for platform abstraction
- E2E test verified on macOS ARM64; Ubuntu deployment pending

## Phased Verification Scope

Phase 1 critical-path verification (all PASSED):
- ✅ Foundry (v1.7.1)
- ✅ Slither (v0.11.4)
- ✅ Aderyn (v0.6.8)
- ✅ Medusa (v1.5.1)
- ✅ Echidna (v2.3.2)
- ✅ Solc (v0.8.35)
- ✅ Shared findings schema
- ✅ Artifact storage
- ✅ Intake + detection
- ✅ Build resolution
- ✅ Archetype classifier
- ✅ Invariant registry
- ✅ Sandbox design (implementation pending)
