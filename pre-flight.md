# pre-flight.md — v2 (forensic-audit corrected)

**Web3 Smart-Contract Bug-Bounty Automation Pipeline — Pre-Flight Checklist**

Target tier: **$1,000 mediums (volume strategy)**
Ecosystem: **Solidity / EVM primary; Solana + Move secondary**
Operating mode: **Quick-scan triage (12–22 min/target), scale to depth only on high-value scopes**

> **v2 changelog (what the audit changed):** Wormhole invariant reframed from "replay" to signature-set/collateral-backing (§4). Aderyn install switched from npm to `cyfrinup` (§1). §7 renamed from "Deterministic" to "Staged" — fuzzer reproducibility now pinned to **corpus, not seed** (§7/§8). Quick-mode Medusa clarified as **assertion-mode + stock properties, not custom invariants** (§9). AGPL §13 SaaS exposure flagged (§1d). "Does this program pay for Medium?" promoted to a **hard pre-scan filter** (§0). Weekly-revenue funnel relabeled illustrative + DeFi-TVL-contraction caveat added (§9).

All links verified against primary sources July 2026. Version numbers, star counts, and self-reported statistics drift — re-verify live before relying on any single figure. Status flags: **[ACTIVE]** maintained, **[FROZEN]** unmaintained-but-usable, **[REJECT]** do not use, **[NO-LICENSE]** reuse rights unclear, **[LICENSE-UNVERIFIED]** license not confirmed in this audit — check before commercial use.

---

## ⚠️ TOP-OF-DOC WARNING (read before building anything)

**1. Most Immunefi programs pay NOTHING below High severity.** A $1K-medium volume strategy has a far smaller addressable target set than "100+ programs" implies. **Before any scan runs, the classifier MUST hard-filter on "does this program's payout table actually pay for Medium?"** This single filter typically cuts the target list by more than half. Scanning a program that won't pay for Medium is pure wasted compute. This is the biggest threat to the whole strategy — treat it as gate zero.

**2. The bounty market is contracting in 2026.** DeFi TVL fell from ~$160B (Oct 2025) to ~$83B (May 2026) per The Block. Shrinking TVL = shrinking bounty budgets and pool sizes, while more automated scanners chase them. The $1K-tier economics are under pressure. Plan accordingly; the revenue figures in §9 are illustrative targets, not forecasts.

**3. Five core tools are AGPL-3.0 (Slither, Medusa, Echidna, Halmos, hevm).** If this pipeline ever becomes a network service / SaaS, AGPL §13 treats network use as distribution and triggers source-disclosure obligations. See §1d before commercializing.

---

## 0. Pre-Flight Gate (run before every scan)

- [ ] **GATE ZERO — payout check:** program's official payout table confirms it **pays for Medium** (and Low, if you're targeting lows). If Medium is out-of-scope / won't-fix → **skip the target entirely, do not scan.**
- [ ] Target scope confirmed in-bounds against the program's official scope page
- [ ] KYC completed in advance for KYC-gated programs (LayerZero, etc.) — do this BEFORE finding a bug, not after
- [ ] Program arbitration status checked (prefer arbitration-enabled / coverage-backed programs)
- [ ] Target recency checked — prioritize contracts deployed or upgraded in the last 30–90 days (easy bugs on stale scopes are already gone)
- [ ] Tool versions pinned (see §8) — solc via solc-select, fork block number fixed, **corpus directory pinned** (see §7 for why corpus, not seed)
- [ ] The classifier's go/no-go filter has approved the target (pays-for-Medium confirmed, archetype identified, scope non-trivial, payout history acceptable)

**Hard rule: no finding is real until reproduced with a deterministic Foundry test on a mainnet fork. Scanners and fuzzers produce hypotheses, not confirmed bugs. The PoC is the deliverable.**

---

## 1. Core Toolchain — The 5 Essential Tools

| Tool | Role | GitHub | License | Status |
|---|---|---|---|---|
| **Foundry** | Harness / repro / PoC / invariant fuzzing / diff testing | https://github.com/foundry-rs/foundry | MIT/Apache-2.0 | [ACTIVE] nightly |
| **Slither** | Static analysis (95+ detectors, SlithIR dataflow, printers) | https://github.com/crytic/slither | **AGPL-3.0** | [ACTIVE] |
| **Aderyn** | Fast Rust static pass / CI gate / known-issue lists | https://github.com/Cyfrin/aderyn | GPL-3.0 [LICENSE-UNVERIFIED] | [ACTIVE] v0.6.x |
| **Medusa** | Parallel coverage-guided fuzzer (primary) | https://github.com/crytic/medusa | **AGPL-3.0** | [ACTIVE] |
| **Echidna** | Property-based fuzzer (differential coverage vs Medusa) | https://github.com/crytic/echidna | **AGPL-3.0** | [ACTIVE] maint+ |
| **heimdall-rs** | Bytecode decompilation for unverified targets | https://github.com/Jon-Becker/heimdall-rs | [LICENSE-UNVERIFIED] | [ACTIVE] |

- Foundry install: `curl -L https://foundry.paradigm.xyz | bash && foundryup` — docs https://getfoundry.sh
- Slither install: `uv tool install slither-analyzer` — verify current release on https://pypi.org/project/slither-analyzer/
- **Aderyn install (CORRECTED): primary = `cyfrinup`** or the curl installer `https://github.com/cyfrin/aderyn/releases/latest/download/aderyn-installer.sh`. **npm (`npm i -g @cyfrin/aderyn`) is a fallback only** — the npm package has had publishing failures (e.g. v0.6.6) and the old `~/.cyfrin/bin/aderyn` path is deprecated (remove any stale binary there). Docs https://cyfrin.gitbook.io/cyfrin-docs
- **$1K-tier note:** Medusa alone in quick mode is sufficient (see §9 for exactly what "quick mode" catches and what it doesn't). Echidna is a depth play — enable only on high-value targets. heimdall-rs only when source is unverified.

## 1a. Optional-But-Powerful (depth tier — skip for $1K targets)

| Tool | Role | GitHub | License | Status |
|---|---|---|---|---|
| **Halmos** | Bounded symbolic proof of critical invariants (reuses Foundry tests) | https://github.com/a16z/halmos | **AGPL-3.0** | [ACTIVE] |
| **Kontrol** | Full formal verification of highest-value mechanisms | https://github.com/runtimeverification/kontrol | BSD-3-Clause | [ACTIVE] |
| **hevm** | Bytecode equivalence checking (upgrade/refactor diffs) | https://github.com/argotorg/hevm | **AGPL-3.0** | [ACTIVE] |
| **Wake** | Python-native static + manually-guided fuzzing alternative | https://github.com/Ackee-Blockchain/wake | ISC | [ACTIVE] |

**Reserve Halmos/Kontrol/hevm for $5M+ bounty scopes.** At the $1K tier they cost more time than the payout justifies. Note: hevm's canonical repo moved to **github.com/argotorg/hevm** (the repo's own release notes confirm the move; `github.com/ethereum/hevm` is the predecessor).

## 1b. Non-EVM Extensions

| Ecosystem | Tool | GitHub | License | Status |
|---|---|---|---|---|
| Solana (fuzzing) | **Trident** (Ackee) | https://github.com/Ackee-Blockchain/trident | [LICENSE-UNVERIFIED] | [ACTIVE] |
| Solana (static) | **sec3 X-Ray** | https://github.com/sec3-product/x-ray | [LICENSE-UNVERIFIED] | [ACTIVE] |
| Move / Aptos | **Move Prover** (`aptos move prove`) | https://aptos.dev/build/smart-contracts/prover | Apache-2.0 | [ACTIVE] |
| Move / Sui | **Sui Prover** (Asymptotic) | https://github.com/asymptotic-code/sui-prover | [LICENSE-UNVERIFIED] | [ACTIVE] |

## 1c. REJECTED — Do Not Use

| Tool | Reason | Status |
|---|---|---|
| **Manticore** | Archived read-only June 24 2026; "no longer developed" | [REJECT] |
| **Oyente** | Archived May 2023; Solidity 0.4.x only | [REJECT] |
| **Securify2** | No meaningful maintenance since ~2020; old solc only | [REJECT] |
| **Mythril** | Dependency-only updates, slower, higher FP than alternatives | [REJECT for new work] |

## 1d. ⚠️ AGPL-3.0 LICENSE EXPOSURE (read before commercializing)

**Slither, Medusa, Echidna, Halmos, and hevm are all AGPL-3.0.** AGPL §13 ("Remote Network Interaction") treats making the software available to users over a network as equivalent to distribution — which triggers the obligation to offer users the complete corresponding source of your modified version.

- **Running the pipeline privately for your own bug-bounty work:** no distribution, no §13 trigger. Fine.
- **Exposing the pipeline as a hosted service / SaaS / API to third parties:** §13 likely triggers. You would owe source disclosure of AGPL-derivative components.
- **Mitigation options:** keep it internal-only; or architect AGPL tools as separate processes invoked via CLI (arm's-length, not linked into your proprietary code — reduces but does not eliminate obligations; get legal review); or negotiate a commercial/dual license (Trail of Bits offers this for Slither).
- **Action:** before any commercial launch, read each LICENSE file and get a lawyer to review the §13 boundary. This is real legal exposure, not a formality.

**License-verification TODO (unconfirmed in this audit):** confirm Aderyn is actually GPL-3.0 as labeled; confirm licenses for heimdall-rs, Trident, sec3 X-Ray, Sui Prover. Run `gh repo view <repo> --json licenseInfo` or read each LICENSE file directly.

---

## 2. Invariant Library — Tier 1: Reusable Property/Invariant Code

**These are the fuel. Without them, Medusa/Echidna/Halmos run at ~15% capability. This is the single most critical addition to the pipeline.**

**IMPORTANT — how these actually run:** crytic/properties runs in **assertion mode** by default (repo config: `testMode: assertion`). The stock set covers ERC-standard compliance + a fixed set of security properties (share inflation, approval checks, etc.). It does **not** cover protocol-specific business logic — that requires invariants you author yourself. See §9 for what this means at the $1K tier.

| Resource | What it gives | GitHub / URL | License | Status |
|---|---|---|---|---|
| **crytic/properties** | 168 pre-built properties: ERC-20 (25), ERC-721 (19), ERC-4626 (37), ABDKMath64x64 (106). *Verified against ToB blog + repo.* | https://github.com/crytic/properties | **AGPL-3.0** | [ACTIVE] |
| ↳ full property list | Itemized catalog | https://github.com/crytic/properties/blob/main/PROPERTIES.md | — | — |
| **Recon Chimera** | "Write once, run everywhere" — one invariant suite → Foundry + Echidna + Medusa + **Halmos + Kontrol** | https://github.com/Recon-Fuzz/chimera | (repo) | [ACTIVE] |
| **create-chimera-app** | Invariant fuzzing starter/harness skeleton (fork this first) | https://github.com/Recon-Fuzz/create-chimera-app | (repo) | [ACTIVE] |
| **Recon org** | StakingRewards-invariants + other example invariant repos | https://github.com/Recon-Fuzz | — | [ACTIVE] |
| **Recon Book** | Framework docs + English→Solidity invariant conversion | https://book.getrecon.xyz | — | [ACTIVE] |
| **a16z/erc4626-tests** | Implementation-independent ERC-4626 property tests | https://github.com/a16z/erc4626-tests | (repo) | [ACTIVE] |
| **properties-chimera** | Pre-built ERC-4626 properties adapted for Chimera | https://github.com/giovannidisiena/properties-chimera | (repo) | [ACTIVE] |
| **Building Secure Contracts** | Canonical invariant-development methodology (Echidna/Medusa/Slither tutorials) | https://github.com/crytic/building-secure-contracts (mirror: https://secure-contracts.com) | (repo) | [ACTIVE] |
| **not-so-smart-contracts** | Vulnerability-class examples (now inside building-secure-contracts) | https://github.com/crytic/building-secure-contracts/tree/master/not-so-smart-contracts | (repo) | [ACTIVE] |

**Seed order:** fork `create-chimera-app` → `forge install crytic/properties` → add `a16z/erc4626-tests` → CI baseline that runs the ERC-20/4626 suite green.

---

## 3. Invariant Library — Tier 2: Categorized Findings Aggregators (mine for new invariants)

| Resource | What it gives | URL | Maintainer | Status |
|---|---|---|---|---|
| **Solodit** | 50,000+ aggregated findings, filterable by impact/category/tag/source. Largest dataset of SC vulns. | https://solodit.cyfrin.io | Cyfrin | [ACTIVE] |
| ↳ Solodit Checklist | Categorized audit checklist | https://solodit.cyfrin.io/checklist | Cyfrin | [ACTIVE] |
| ↳ checklist repo | Backing repo | https://github.com/Cyfrin/audit-checklist | Cyfrin | [ACTIVE] |
| ↳ Solodit docs | API / usage | https://docs.solodit.cyfrin.io | Cyfrin | [ACTIVE] |
| **Code4rena findings** | Per-contest findings repos + consolidated report library | https://github.com/code-423n4 · https://code4rena.com/reports | Code4rena | **[WINDING DOWN — mirror now]** |
| **Sherlock reports** | Audit & coverage reports from past contests | https://github.com/sherlock-protocol/sherlock-reports | Sherlock | [ACTIVE] |
| ↳ Sherlock contest repos | Per-contest source + findings | https://github.com/sherlock-audit | Sherlock | [ACTIVE] |
| ↳ Sherlock judging UI | Live reports | https://audits.sherlock.xyz | Sherlock | [ACTIVE] |
| **Immunefi bugfix reviews** | Write-ups of paid, fixed bounty bugs | https://immunefi.com/blog/bug-fix-reviews/ | Immunefi | [ACTIVE] |
| ↳ bugfix PoC repo | Foundry PoCs reproducing them | https://github.com/immunefi-team/bugfix-reviews-pocs | Immunefi | [ACTIVE] |
| ↳ Web3 Security Library | Curated reference | https://github.com/immunefi-team/Web3-Security-Library | Immunefi | [ACTIVE] |
| ↳ Immunefi Top 10 | Most common/high-value bug classes | https://immunefi.com/immunefi-top-10/ | Immunefi | [ACTIVE] |

**Action:** work Solodit by protocol category; for each recurring finding class, encode a negative test / invariant into your library. **Mirror Code4rena findings immediately — the platform is winding down** (confirmed: May 13 2026, Immunefi absorbing clients).

---

## 4. Invariant Library — Tier 3: Reproducing PoC Exploit Code (validation set)

| Resource | What it gives | GitHub | Maintainer | Status |
|---|---|---|---|---|
| **DeFiHackLabs** | ~691 incidents (mid-2026, drifts up) — runnable `forge test` PoC per hack + tx hash + post-mortem links. The single best executable-exploit library. | https://github.com/SunWeb3Sec/DeFiHackLabs | SunWeb3Sec | [ACTIVE] |
| **DeFiVulnLabs** | 48 vulnerability-class Foundry PoCs (reentrancy, delegatecall, storage collision, phantom permit, read-only reentrancy, etc.) | https://github.com/SunWeb3Sec/DeFiVulnLabs | SunWeb3Sec | [ACTIVE] |
| **Defi-Hack-Analysis-POC** | Curated major-hack Foundry PoCs (supplement) | https://github.com/abdulsamijay/Defi-Hack-Analysis-POC | community | [ACTIVE] |

**Action:** run your invariant suite against these PoCs to confirm it would have caught the historical bug. Extract each exploit → the property that would have caught it → add to library.

**Verified exploit→invariant mappings (corrected):**
- **Euler ($197M, Mar 2023)** — `donateToReserves` performed no solvency/liquidity check, letting the attacker force their own position insolvent then self-liquidate at a discount. → **collateral-ratio / health-factor invariant** (a position's health check must run on every balance-reducing operation). *Verified: BlockSec, Chainalysis, Coinbase, Euler post-mortem.*
- **Beanstalk ($182M, Apr 2022)** — flash-loan governance attack; no flash-loan-resistant measure on vote weight, so the attacker borrowed ~$1B, passed BIP-18 via emergency supermajority in one tx, drained the treasury. → **flash-loan-resistant vote-weight / snapshot invariant** (voting power must be measured against a pre-proposal snapshot, immune to same-tx borrowing). *Verified: CoinDesk, Merkle Science, Omniscia post-mortem.*
- **Wormhole (~$320–325M, Feb 2022) — CORRECTED FRAMING** — this was a **signature-verification bypass**, not a message replay. A deprecated function failed to validate the guardian signature set, letting the attacker forge validation and mint 120,000 wETH with no deposit. → the testable invariant is **mint-backed-by-locked-collateral** (total minted on destination ≤ total locked on source) and/or **guardian-signature-set validation** on every mint. *Verified: CoinMarketCap, Cryptopolitan, multiple post-mortems.* (Prior versions of this doc mislabeled this a "message-replay invariant" — that was wrong.)

---

## 5. Invariant Library — Tier 4: Post-Mortems & Incident Databases (continuous intake)

| Resource | What it gives | URL | Maintainer | Status |
|---|---|---|---|---|
| **rekt.news** | Exploit/rug post-mortems since 2020 + ranked loss leaderboard (#1: ByBit ~$1.43B, 2/21/2025) | https://rekt.news · https://rekt.news/leaderboard | rekt editorial | [ACTIVE] |
| **SlowMist Hacked** | ~2,154 hack events, ~$37.86B cumulative loss (self-reported, drifts), each with attack-method classification | https://hacked.slowmist.io | SlowMist | [ACTIVE] |
| **BlockSec Phalcon** | Investigation-grade tx explorer/replay/simulation — trace & dissect any exploit tx | https://app.blocksec.com/phalcon/explorer | BlockSec | [ACTIVE] |

**Action:** subscribe to rekt.news + SlowMist Hacked. When a novel bug class appears, add a PoC + invariant within the week.

## 5a. Historical Taxonomies — Reference Only (NOT actively maintained)

| Resource | URL | Status |
|---|---|---|
| **SWC Registry** | https://swcregistry.io · https://github.com/SmartContractSecurity/SWC-registry | [FROZEN since 2020 — superseded by EEA EthTrust Security Levels] |
| **Consensys Best Practices / Known Attacks** | https://consensysdiligence.github.io/smart-contract-best-practices/attacks/ | [FROZEN — lightly maintained] |
| **OpenZeppelin advisories** | https://github.com/OpenZeppelin/openzeppelin-contracts/security/advisories | [ACTIVE] |
| ↳ OZ audit reports | https://github.com/OpenZeppelin/openzeppelin-contracts/tree/master/audits | [ACTIVE] |

## 5b. Curated Datasets & Awesome-Lists (discovery indexes)

- Awesome-Smart-Contract-Security — https://github.com/saeidshirazi/Awesome-Smart-Contract-Security
- SCV-List (CVE-like on-chain vuln list) — https://github.com/sirhashalot/SCV-List
- smart-contract-vulnerabilities — https://github.com/kadenzipfel/smart-contract-vulnerabilities
- awesome-smart-contract-datasets — https://github.com/acorn421/awesome-smart-contract-datasets
- smartbugs-curated (annotated vulnerable contracts) — https://github.com/smartbugs/smartbugs-curated
- Forta detection patterns: https://github.com/forta-network/forta-bot-examples · https://github.com/forta-network/forta-bot-templates · https://github.com/NethermindEth/Forta-Agents

---

## 6. The Bridge — Orchestration & The Missing Classifier

**Verified finding: NO end-to-end system exists** for protocol-archetype classification → CodeGraph-to-invariant bridging → template adaptation → audit-pipeline orchestration. The classifier is the component you must build. Below are the verified building blocks it connects.

### Verified building blocks

| Component | What it does | GitHub / URL | License | Status |
|---|---|---|---|---|
| **CodeGraph** | Code knowledge graph over MCP; tree-sitter AST; symbols + call/import/extends edges; **explicitly lists Hermes Agent as a supported client**; supports Solidity | https://github.com/colbymchenry/codegraph | MIT | [ACTIVE] pre-1.0 |
| **Trail of Bits `skills`** | Agent-skill marketplace (Claude Code + Codex sidecar). Install: `/plugin marketplace add trailofbits/skills` | https://github.com/trailofbits/skills | CC-BY-SA-4.0 | [ACTIVE] |
| ↳ **entry-point-analyzer** | Identifies state-changing entry points by access level (Solidity/Vyper/Solana/Move/TON/CosmWasm). Nearest analog to the "extract signatures" stage. | https://github.com/trailofbits/skills/tree/main/plugins/entry-point-analyzer | CC-BY-SA-4.0 | [ACTIVE] |
| ↳ **property-based-testing** | Writes Echidna/Medusa invariants. Install: `/plugin install trailofbits/skills/plugins/property-based-testing` | https://github.com/trailofbits/skills/tree/main/plugins/property-based-testing | CC-BY-SA-4.0 | [ACTIVE] |
| **Recon Handler Builder** | Auto-scaffolds a Chimera invariant suite from a contract's ABI — nearest verified match to "adapt templates to function signatures" | (via https://getrecon.xyz + recon-extension) | — | [ACTIVE] |
| ↳ **recon-extension** | VS Code: install Chimera templates, run Echidna/Medusa/Halmos, generate Foundry repros, visualize coverage | https://github.com/Recon-Fuzz/recon-extension | — | [ACTIVE] |

### Academic analogs (research prototypes — study the approach, verify licensing before reuse)

| System | Contribution | Link | Caveat |
|---|---|---|---|
| **PropertyGPT** (NDSS 2025, Distinguished Paper) | Retrieval-augmented property generation: 623 human-written properties in a vector DB, retrieves/adapts to unseen code + prover. **Closest analog to auto invariant selection+adaptation.** | arXiv:2405.02580 | **Self-reported metrics only** (80% recall, CVE/zero-day/bounty figures are the authors' own eval, no independent reproduction — do NOT use the dollar figure for planning) |
| **PromFuzz** (ASE 2025) | Dual-agent (Auditor/Attacker) + invariant-checker templates + bug-oriented fuzzing | https://github.com/PROMFUZZ/promfuzz · arXiv:2503.23718 | **[NO-LICENSE] — no LICENSE file, do not reuse code without contacting authors** |
| **SmartInv** (IEEE S&P 2024) | Tier-of-Thought prompting; detects transactional context + critical program points (implicit archetype awareness) → generates + prioritizes invariants | (paper) | Research prototype |
| **FLAMES** (2025) | Fine-tuned LLM synthesizes `require`-style invariants; up to 96.7% compile rate (self-reported) | arXiv:2510.21401 | Research prototype |
| **LLM4Fuzz** | Contract→AST→static analysis→LLM-guided fuzz prioritization on user-defined invariants | arXiv:2401.11108 | Research prototype |

### The classifier you must build (the connector, ~200–400 lines of logic)

Input: CodeGraph/Slither output (AST, function signatures, inheritance tree, state variables, external calls).
Output: one archetype label + the function/variable mapping needed to adapt templates.
**First-pass output must also include the GATE ZERO decision: does this program pay for Medium? If no → abort before any tooling runs.**

Heuristic core (interface + signature pattern-matching):
- inherits ERC-4626 → **vault/yield** → pull 37 ERC-4626 properties
- inherits ERC-20 only → **token** → pull 25 ERC-20 properties
- has `borrow`/`repay`/`liquidate`/`collateral`/utilization math → **lending** → pull lending invariant set (health-factor-on-every-balance-change, per Euler)
- has `swap`/`getReserves`/constant-product (x*y=k) → **DEX/AMM** → pull swap/LP/fee invariants
- inherits OZ `Governor` / has timelock + proposal + vote-weight → **governance** → pull governance invariants (flash-loan-resistant snapshot, per Beanstalk)
- cross-chain `mint`/`burn`/message-passing → **bridge** → pull mint-backed-by-locked-collateral + signature-set-validation invariants (per Wormhole)
- LLM fallback only for ambiguous/hybrid cases

Then: Recon Handler Builder scaffolds the harness → wire selected templates to the target's actual signatures → `forge build` (compile check) → run.

**Determinism caveat (corrected):** only static analysis (Slither/Aderyn), scaffolding, and result parsing are truly deterministic. **Fuzzers (Medusa/Echidna) are coverage-guided, mutational, and parallelized — they are NOT bit-for-bit deterministic per run.** Reproducibility comes from pinning the **corpus directory** (replaying known coverage-increasing sequences), not from an RNG seed. Implement the classifier as pure rule-based heuristics wherever possible; treat any LLM path as non-deterministic and gate its output behind the compile check + PoC confirmation.

---

## 7. The Staged Pipeline Sequence

*(Renamed from "Deterministic Pipeline" — see determinism breakdown below. The sequence is staged and mostly automatable, but the fuzzing stages are statistically reproducible via corpus, not bit-for-bit deterministic.)*

```
Stage 0  Pre-flight gate (incl. GATE ZERO pays-for-Medium) + classifier   (seconds)   [auto]
Stage 1  Slither --checklist --json  +  aderyn                             (15–45 s)    [auto, DETERMINISTIC]
Stage 2  CodeGraph index → classify archetype                              (60–90 s)    [auto, heuristic = deterministic; LLM fallback = not]
Stage 3  Select invariant set → Chimera adapt → forge build                (30–60 s)    [auto, DETERMINISTIC]
Stage 4  Medusa quick fuzz (1–3M iters, ASSERTION MODE + stock properties) (10–20 min)  [auto; REPRODUCIBLE VIA PINNED CORPUS, not seed]
         [depth tier only: + Echidna, + authored invariants, + 24–48h fuzz]
Stage 5  [depth tier only] Halmos on critical props                        (skip @ $1K) [expert; BOUNDED-deterministic within --loop/--depth]
Stage 6  Reproduce candidate as Foundry fork test                          (manual)     [MANDATORY HUMAN GATE]
Stage 7  Dedup + rank + severity + report                                  (min)        [scaffold auto, DETERMINISTIC; judgment manual]
```

**$1K quick-mode total: 12–22 min/target.** Drop Echidna, drop Halmos, use crytic/properties stock set in assertion mode + lightweight archetype template only.

### Determinism, honestly (the corrected model)
- **Truly deterministic (same input → same output, always):** Slither, Aderyn, compilation, SARIF merge, result parsing, dedup-by-location.
- **Reproducible via pinned CORPUS, not seed:** Medusa, Echidna. Parallel + mutational fuzzing can find different bugs in different order across runs. Pin the **corpus directory** to replay coverage-increasing sequences — that is the actual reproducibility mechanism. (Medusa does not expose a single top-level RNG seed the way a "fuzz seed" pin would imply.)
- **Bounded-deterministic:** Halmos, Kontrol — deterministic *within* their `--loop`/`--depth` bounds; solver timeouts can still vary by hardware.

### What must NEVER be trusted to automation without verification
1. Any static/symbolic/fuzz finding treated as confirmed — **all require a reproducing Foundry fork PoC**
2. Any "formally verified" claim beyond its documented bounds (Halmos `--loop`, Kontrol spec scope)
3. LLM/agent-generated findings (classifier output, property generation) — ground-truth everything
4. Decompiled source from heimdall — it is approximate, a hint not authority
5. Business-logic / economic-attack / specification correctness — **human domain, not catchable by any tool in this stack**

---

## 8. Reproducibility Pin-List (fill before each run)

- [ ] Foundry version (nightly hash): `________`
- [ ] Slither version: `________`  · Aderyn version (v0.6.x): `________`
- [ ] Medusa version: `________`  · Echidna version: `________`
- [ ] solc version (via solc-select): `________`
- [ ] Fork RPC + fork block number: `________`
- [ ] **Corpus directory path (THE reproducibility anchor for fuzzing): `________`**  ⟵ *corrected: pin corpus, not seed*
- [ ] crytic/properties commit: `________`  · create-chimera-app commit: `________`

*Note: "fuzz seed" was removed as the reproducibility mechanism — Medusa's parallel mutational engine is not seed-reproducible. The pinned corpus is what lets you replay coverage and re-hit findings.*

---

## 9. $1K-Tier Operating Doctrine (the actual strategy)

1. **GATE ZERO first — does the program pay for Medium?** A perfect scan of a program that won't pay for Medium is $0. Filter this BEFORE scanning. This is the single highest-leverage filter and typically removes >50% of candidates.
2. **Target selection beats analysis depth.** Prioritize recently-updated scopes, new Immunefi listings, just-pushed upgrades — among the programs that survived Gate Zero.
3. **Quick mode = stock properties in assertion mode, NOT custom invariants.** Be honest about what this catches: ERC-standard violations, unexpected reverts, and the first-depositor/share-inflation class (via the ERC-4626 properties). It does **NOT** catch protocol-specific business-logic bugs — those need authored invariants (depth tier). So quick mode is a fast filter for the "obvious implementation mistake" class, not a substitute for real invariant work.
4. **The classifier is a go/no-go filter first, an archetype router second.** Auto-skip: programs that don't pay for Medium (Gate Zero), tiny scopes, stale scopes, bad-payout-history programs.
5. **Confirm in-scope before submitting.** The Trust Security / Immunefi dispute is the cautionary tale — a valid bug that's out-of-scope pays nothing and burns goodwill.
6. **Feed the library weekly.** Every novel pattern → new invariant. The library compounds; over months you accumulate a protocol-archetype-organized invariant set deployed systematically on every target.
7. **Revenue expectation — ILLUSTRATIVE, NOT A FORECAST.** A plausible funnel *if* enough programs pay for Medium and target selection is good: high volume of quick scans → a handful of candidates/week → fewer valid, in-scope submissions → occasional payout. **Do not treat any specific weekly dollar figure as promised.** Two forces cut against it: (a) most programs don't pay below High, shrinking the addressable set (Gate Zero); (b) DeFi TVL contracted from ~$160B to ~$83B in 2026, shrinking bounty budgets while more scanners compete. Calibrate against your own first-month actuals before assuming any run-rate.

---

## Caveats (read once)

- **Determinism:** the pipeline is staged, not fully deterministic. Fuzzers are reproducible via pinned corpus, not seed. Static/parsing stages are deterministic; symbolic stages are bounded-deterministic.
- **Payout reality:** most Immunefi programs pay nothing below High. Gate Zero (pays-for-Medium check) is mandatory before scanning.
- **Market contraction:** DeFi TVL ~$160B→~$83B in 2026 (The Block). Bounty economics are under pressure.
- **AGPL exposure:** Slither/Medusa/Echidna/Halmos/hevm are AGPL-3.0. A hosted/SaaS pipeline triggers §13 source-disclosure. Get legal review before commercializing.
- **Unverified licenses:** Aderyn (labeled GPL-3.0), heimdall-rs, Trident, sec3 X-Ray, Sui Prover — confirm each LICENSE file before commercial use.
- **Self-reported figures** (Solodit 50,000+, SlowMist ~2,154/~$37.86B, DeFiHackLabs ~691, crytic/properties 168, Code4rena findings counts, PropertyGPT metrics) drift and/or are single-sourced. Cite live READMEs; don't use PropertyGPT's dollar figure for planning.
- **Aggregators** (Solodit, rekt.news, awesome-lists) are secondary — always follow through to the primary audit report / on-chain tx.
- **PromFuzz** has no license — do not reuse its code without author permission.
- **SWC Registry / Consensys Best Practices** are frozen references, not living taxonomies.
- **Code4rena** is winding down (May 13 2026) — mirror findings now.
- **Verified-correct anchors** (trust these): crytic/properties 168/37/106 counts; Chimera multi-tool support; Code4rena wind-down; hevm@argotorg; Euler/Beanstalk exploit mechanics; Medusa-as-primary-fuzzer. All confirmed against primary sources in the July 2026 audit.
- Use all PoC repositories strictly for defensive/educational purposes per their stated disclaimers.
- Re-audit tool maintenance and licenses quarterly. Manticore's June-2026 archival proves even flagship tools go read-only.
