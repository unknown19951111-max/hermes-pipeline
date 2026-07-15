# License Matrix — Smart-Contract Security Pipeline

## Phase 1 Tools

| Tool | License | Status | Commercial Use | SaaS Exposure | Notes |
|---|---|---|---|---|---|
| Foundry | MIT/Apache-2.0 | ✅ VERIFIED | ✅ Permissive | ✅ Permissive | Dual-licensed; no restrictions |
| Slither | AGPL-3.0 | ✅ PREVIOUSLY VERIFIED | ⚠️ See §13 | ⚠️ AGPL §13 triggers | Private use OK; SaaS → source disclosure |
| Aderyn | GPL-3.0 (stated) | ⚠️ PARTIALLY VERIFIED | ⚠️ GPL-3.0 | ⚠️ GPL-3.0 | Verify LICENSE file with `gh repo view` |
| Medusa | AGPL-3.0 | ✅ PREVIOUSLY VERIFIED | ⚠️ See Slither | ⚠️ AGPL §13 triggers | |
| Echidna | AGPL-3.0 | ✅ PREVIOUSLY VERIFIED | ⚠️ See Slither | ⚠️ AGPL §13 triggers | Installed via Homebrew v2.3.2 |
| crytic/properties | AGPL-3.0 | ✅ PREVIOUSLY VERIFIED | ⚠️ See Slither | ⚠️ AGPL §13 triggers | |
| Chimera | (repo license) | ⚠️ PARTIALLY VERIFIED | ⚠️ PENDING | ⚠️ PENDING | Verify with `gh repo view` |
| solc-select | AGPL-3.0 | ⚠️ PARTIALLY VERIFIED | ⚠️ See Slither | ⚠️ AGPL §13 triggers | |

## Phase 2 Tools

| Tool | License | Status | Commercial Use | Notes |
|---|---|---|---|---|
| Halmos | AGPL-3.0 | ✅ PREVIOUSLY VERIFIED | ⚠️ AGPL | Repo sidebar confirms |
| hevm | AGPL-3.0 | ✅ PREVIOUSLY VERIFIED | ⚠️ AGPL | Repo moved to argotorg/hevm |
| Kontrol | BSD-3-Clause (stated) | ⚠️ PARTIALLY VERIFIED | ✅ Permissive | Verify with `gh repo view` |
| Wake | ISC | ✅ PREVIOUSLY VERIFIED | ✅ Permissive | PyPI confirms ISC |
| heimdall-rs | — | ⚠️ NOT YET VERIFIED | ⚠️ PENDING | Verify with `gh repo view` |

## Phase 3 Tools

| Tool | License | Status | Notes |
|---|---|---|---|
| Trident (Solana) | — | ⚠️ NOT YET VERIFIED | Verify with `gh repo view` |
| sec3 X-Ray (Solana) | — | ⚠️ NOT YET VERIFIED | Verify with `gh repo view` |
| Aptos Move Prover | Apache-2.0 | ⚠️ PARTIALLY VERIFIED | Stated; verify |
| Sui Prover | — | ⚠️ NOT YET VERIFIED | Verify with `gh repo view` |

## Orchestrator (Self-Developed)

| Component | License | Notes |
|---|---|---|
| All orchestrator code | Proprietary / MIT (choice) | Own implementation; no external license constraints |
| schemas/ | MIT / CC0 | Intended as open formats |
| fixtures/ | MIT | Educational/demonstration use |

## AGPL-3.0 Exposure (Section 13)

**Affected tools**: Slither, Medusa, Echidna, Halmos, hevm, crytic/properties, solc-select

**AGPL §13 ("Remote Network Interaction")** treats network access to AGPL-licensed software as distribution — triggering source-disclosure obligations for derivative works.

- **Private bug-bounty work**: No distribution. Pipeline runs on own infrastructure. §13 does NOT trigger. Safe.
- **Hosted SaaS/API service for third parties**: §13 likely triggers. Would owe source for AGPL-derivative components.
- **Mitigation**: CLI invocation as separate processes (arm's-length). Get legal review before any external offering.

**Action**: Before commercial launch, read each LICENSE file and get legal review of the §13 boundary.