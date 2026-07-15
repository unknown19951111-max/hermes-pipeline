# installation.md

**Hermes Agent — Smart-Contract Security-Auditing Pipeline: Installation & Integration Guide**

Deterministic, bottleneck-resistant deployment of the verified toolchain, invariant libraries, and orchestration layer.

---

## Verification legend

Every claim in this guide carries one of these tags:

- **`VERIFIED`** — confirmed against official docs / repo / release / package manifest.
- **`PARTIALLY VERIFIED`** — official source exists but a specific detail (exact flag, version) should be confirmed against the live page at install time.
- **`REQUIRES IMPLEMENTATION`** — no off-the-shelf artifact exists; you build this. Presented as a reference design, not an install step.
- **`REQUIRES MANUAL VALIDATION`** — must be checked in your environment before trusting.
- **`NOT SUPPORTED`** — cannot be done with the stated components; do not attempt.

**Read this first — the honest shape of the system:** The *tools* (§9) and *invariant libraries* (§10) install from verified commands. The *orchestration bridge and classifier* (§6 / §14) **do not exist as installable software** — no end-to-end system for protocol-archetype classification → invariant selection → pipeline orchestration ships today. Those sections are `REQUIRES IMPLEMENTATION` reference architecture you build on top of the installed tools. This guide does not pretend otherwise.

---

## 1. System architecture overview `VERIFIED (design)`

```
                          ┌─────────────────────────────────────────────┐
                          │  HERMES ORCHESTRATOR  (REQUIRES IMPLEMENTATION)│
                          │  intake → detect → dispatch → collect → report │
                          └───────────────┬─────────────────────────────┘
                                          │ job queue (per-target)
        ┌─────────────────────────────────┼─────────────────────────────────┐
        │                                 │                                 │
   ECOSYSTEM BRANCH: EVM            ECOSYSTEM BRANCH: Solana         ECOSYSTEM BRANCH: Move
        │                                 │                                 │
  ┌─────┴──────┐                    ┌─────┴─────┐                     ┌─────┴─────┐
  │ Static     │ Slither, Aderyn    │ sec3 X-Ray│ (static)            │ Move/Sui  │
  │ Fuzz       │ Medusa, Echidna    │ Trident   │ (fuzz)              │ Prover    │
  │ Symbolic   │ Halmos, hevm, Kontrol                               │           │
  │ Recon      │ heimdall-rs                                          └───────────┘
  └─────┬──────┘
        │  raw tool outputs (JSON/SARIF/corpus/counterexamples)
        ▼
  ┌───────────────────────────────────────────────┐
  │ NORMALIZER → DEDUP → CLASSIFIER → CONFIDENCE    │  (REQUIRES IMPLEMENTATION)
  │ → PoC VALIDATION (Foundry fork) → HUMAN GATE    │
  └───────────────────────────────────────────────┘
        │
        ▼   final report + provenance
  ┌───────────────────────────────────────────────┐
  │ INVARIANT LIBRARY  (Tier1 code / Tier2 findings │
  │  / Tier3 PoCs / Tier4 post-mortems)             │  feeds classifier + fuzzers
  └───────────────────────────────────────────────┘
```

Data flow is one-directional per job: intake → build → static → symbolic/fuzz → normalize → classify → PoC-validate → human gate → report. The invariant library is a shared read source for the fuzz stage and a shared write target for the post-mortem intake process.

## 2. Supported operating systems and environments `VERIFIED`

- **Primary: Ubuntu 22.04 / 24.04 LTS (x86-64).** All core tools ship Linux x86-64 binaries. This is the reference platform.
- **macOS (Apple Silicon & Intel):** supported for Foundry, Slither, Aderyn, Halmos, Wake, Echidna (brew). Wake docs note **Rosetta must be enabled on Apple Silicon**. `PARTIALLY VERIFIED` — some Haskell/Go binaries are x86-only; run under Rosetta or use Docker.
- **Docker:** recommended for reproducibility and sandboxing. Trail of Bits ships `eth-security-toolbox`; individual tools ship official images (see §9). `VERIFIED`.
- **Windows:** `NOT SUPPORTED` natively for the full pipeline. Use WSL2 (Ubuntu) or Docker. hevm added Windows library builds but the orchestration assumes a POSIX shell. `PARTIALLY VERIFIED`.

## 3. Minimum and recommended hardware `REQUIRES MANUAL VALIDATION`

These are operational guidance, not vendor specs — validate against your workloads.

| Resource | Minimum (quick-scan tier) | Recommended (depth tier) |
|---|---|---|
| CPU | 4 cores | 16+ cores (Medusa parallelism scales with cores) |
| RAM | 8 GB | 32–64 GB (symbolic execution + parallel fuzzing are memory-heavy) |
| Disk | 40 GB SSD | 200+ GB NVMe (corpora, forks, build caches, PoC repos) |
| Network | stable (RPC forking) | archive-node RPC or paid provider (fork reliability) |

Symbolic tools (Halmos/hevm/Kontrol) and deep fuzzing are the resource sinks; size for those if you run the depth tier.

## 4. Required package managers and runtimes `VERIFIED`

| Runtime / manager | Purpose | Install source |
|---|---|---|
| **Rust + cargo** | Foundry (optional build), Aderyn, heimdall-rs, Trident | https://rustup.rs |
| **Python 3.10–3.12** | Slither, Halmos, Wake | system / pyenv |
| **uv** | fast Python tool installer (Slither, Halmos) | https://astral.sh/uv |
| **Go 1.21+** | Medusa (from source) | https://go.dev |
| **Node.js 20+** | 4naly3er, sol2uml, Aderyn npm fallback | https://nodejs.org |
| **Nix** | hevm, Kontrol (kup) | https://nixos.org/download |
| **solc-select** | Solidity compiler version management | `uv tool install solc-select` (AGPL-3.0, `VERIFIED`) |
| **z3** | SMT solver for Halmos / hevm | `apt install z3` / `brew install z3` |
| **Docker** | sandboxing, reproducible runs | https://docs.docker.com |

## 5. Repository directory structure `REQUIRES IMPLEMENTATION (convention)`

```
hermes-pipeline/
├── orchestrator/            # the bridge you build (§6/§14)
│   ├── intake/              # target repo cloning, scope parsing
│   ├── detect/              # ecosystem/framework classifier
│   ├── dispatch/            # per-tool job runners
│   ├── normalize/           # tool-output → unified schema
│   ├── classify/            # finding classifier
│   └── report/             # final report generation
├── tools/                   # pinned tool versions / lockfiles
├── invariants/              # Tier-1 library (see §10)
│   ├── erc20/  erc721/  erc4626/  lending/  dex/  vault/  governance/  bridge/
│   └── registry.json        # metadata index (schema in §10)
├── datasets/
│   ├── findings/            # Tier-2 aggregator dumps (Solodit, C4, Sherlock)
│   ├── poc/                 # Tier-3 DeFiHackLabs, DeFiVulnLabs (submodules)
│   └── postmortems/         # Tier-4 rekt/SlowMist ingested records
├── work/                    # per-job scratch (ephemeral, sandboxed)
│   └── <job-id>/            # cloned target, build artifacts, corpus, outputs
├── artifacts/               # durable outputs + provenance (see §10 schema)
├── cache/                   # build cache, dependency cache, fork cache
├── logs/                    # rotated logs + evidence
└── config/
    ├── versions.lock        # §7 pin-list
    └── env                  # §8 environment variables
```

## 6. The Bridge — orchestration & the classifier `REQUIRES IMPLEMENTATION`

**No off-the-shelf system does this.** Verified as absent: protocol-archetype classification → CodeGraph-to-invariant bridging → template adaptation → pipeline orchestration. Build it from these **verified building blocks**:

| Building block | Role | Source | Tag |
|---|---|---|---|
| **CodeGraph** | AST/symbol/call-graph index over MCP; lists Hermes as a client; supports Solidity | https://github.com/colbymchenry/codegraph | `PARTIALLY VERIFIED` (license unconfirmed; pre-1.0) |
| **ToB `entry-point-analyzer`** | extract state-changing entry points by access level | https://github.com/trailofbits/skills | `VERIFIED` (repo) / license unconfirmed |
| **ToB `property-based-testing`** | scaffold Echidna/Medusa invariants | same repo | `VERIFIED` (repo) |
| **Recon Handler Builder** | scaffold a Chimera suite from a contract ABI | https://github.com/Recon-Fuzz/recon-extension | `VERIFIED` (repo) |

**The classifier you must build** (`REQUIRES IMPLEMENTATION`, ~200–400 lines): input = CodeGraph/Slither AST + signatures + inheritance + state vars + external calls; output = one archetype label + a `pays-for-Medium` gate decision. Rule-based heuristics (deterministic) with an LLM fallback (non-deterministic — gate behind compile-check + PoC).

Heuristic routing (all `REQUIRES IMPLEMENTATION`):
- inherits ERC-4626 → vault/yield → 37 ERC-4626 properties
- inherits ERC-20 only → token → 25 ERC-20 properties
- `borrow`/`repay`/`liquidate`/collateral math → lending → health-factor-on-every-balance-change invariants
- `swap`/`getReserves`/x*y=k → DEX/AMM → swap/LP/fee invariants
- OZ `Governor` / timelock + vote-weight → governance → flash-loan-resistant snapshot invariants
- cross-chain `mint`/`burn`/message-passing → bridge → mint-backed-by-locked-collateral + signature-set-validation invariants

**Classifier output taxonomy** — every finding must be labeled as exactly one of: confirmed vulnerability · reproducible suspicious behavior · invariant violation · tool-generated warning · duplicate finding · informational observation · unsupported hypothesis · false positive · analysis failure. Each label must preserve: provenance (tool + version), raw tool output, source location (file:line), execution evidence (command + exit + artifact path), confidence level, reproduction status (PoC pass/fail/none).

---

## 7. Version pinning and dependency-lock strategy `REQUIRES MANUAL VALIDATION`

Determinism depends on pinning. Record every value in `config/versions.lock` before a production run:

```
foundry_nightly_hash = <foundryup --version hash>
slither = <pip show slither-analyzer>        # e.g. 0.11.x
aderyn  = <aderyn --version>                 # e.g. 0.6.x
medusa  = <medusa --version>
echidna = <echidna --version>
halmos  = <halmos --version>                 # e.g. 0.3.x
hevm    = <hevm version>                      # e.g. 0.58.0
kontrol = <kontrol version>
wake    = <wake --version>                    # eth-wake, e.g. 4.21.x
solc    = <solc-select versions>              # pin per target
z3      = <z3 --version>
crytic_properties_commit = <git rev-parse HEAD>
create_chimera_app_commit = <git rev-parse HEAD>
fork_block_number = <target-specific>
corpus_dir = <path>                           # reproducibility anchor for fuzzers
```

**Reproducibility note (`VERIFIED`):** static tools (Slither/Aderyn) are deterministic. **Fuzzers (Medusa/Echidna) are NOT bit-for-bit deterministic** — they are coverage-guided/mutational/parallel; reproducibility comes from **pinning the corpus directory**, not an RNG seed. Halmos is bounded-deterministic (its FAQ: "no random elements... external solvers with unpredictable timings" are the only nondeterminism source; mitigate with `--solver-timeout-branching 0`).

## 8. Environment-variable configuration `REQUIRES IMPLEMENTATION (convention)`

```bash
# config/env
export HERMES_ROOT=/opt/hermes-pipeline
export HERMES_WORK=$HERMES_ROOT/work
export HERMES_ARTIFACTS=$HERMES_ROOT/artifacts
export ETH_RPC_URL=<archive-node-or-provider>        # required for forking
export FOUNDRY_PROFILE=ci
export SOLC_SELECT_HOME=$HOME/.solc-select
# per-tool timeouts (seconds) — see §12
export T_SLITHER=120 T_ADERYN=60 T_MEDUSA_QUICK=1200 T_ECHIDNA=3600 T_HALMOS=1800
# resource caps — see §12
export MAX_WORKERS=$(nproc) MEM_LIMIT_MB=8192
```

---

## 9. Tool-specific installation `VERIFIED (per-tool below)`

### 9.1 Core Toolchain — Five Essential Tools

#### Foundry — harness / reproduction / PoC / invariant fuzzing `VERIFIED`
- **Source:** https://github.com/foundry-rs/foundry · docs https://getfoundry.sh · **License:** MIT/Apache-2.0
- **Role:** the substrate. Every other tool targets a Foundry project; PoCs are Foundry fork tests. **Runtime:** Rust binaries (forge/cast/anvil/chisel).
- **Install:** `curl -L https://foundry.paradigm.xyz | bash && foundryup`
- **Validate:** `forge --version && anvil --version`
- **Inputs:** Solidity sources, tests, RPC URL. **Outputs:** test results, traces, gas reports, JSON artifacts, broadcast files.
- **Integration:** provides the compiled project + fork environment consumed by Slither, Medusa, Echidna, Halmos, hevm, Kontrol.
- **Known limits:** anvil fork edge-cases; fuzzer is random (not exhaustive). **Common failure:** `foundryup` PATH not updated → add `~/.foundry/bin` to PATH, re-source shell.

#### Slither — static analysis (first pass) `VERIFIED`
- **Source:** https://github.com/crytic/slither · PyPI https://pypi.org/project/slither-analyzer/ · **License: AGPL-3.0 (VERIFIED — PyPI: "licensed and distributed under the AGPLv3")**
- **Role:** 95+ detectors, SlithIR dataflow, recon printers (inheritance/CFG/call-graph). **Runtime:** Python 3.10+, needs solc via solc-select.
- **Install:** `uv tool install slither-analyzer` (or `pipx install slither-analyzer`)
- **Validate:** `slither --version`
- **Inputs:** compiled project. **Outputs:** terminal, `--checklist` Markdown, `--json`, SARIF.
- **Integration:** JSON/SARIF → normalizer (§6). Slither analysis also informs Medusa/Echidna value generation. GitHub Action + Python API available.
- **Common failure:** compilation fails → set correct solc (`solc-select use <ver>`) and remappings; Slither requires a compilable project.

#### Aderyn — fast static pass / CI gate `VERIFIED (command)` / license `PARTIALLY VERIFIED`
- **Source:** https://github.com/Cyfrin/aderyn · docs https://cyfrin.gitbook.io/cyfrin-docs · **License:** stated GPL-3.0 but **not confirmed against LICENSE file — verify with `gh repo view Cyfrin/aderyn --json licenseInfo`**
- **Role:** Rust AST analyzer, sub-second, Markdown/JSON/SARIF, custom detectors. Auto-detects Foundry/Hardhat.
- **Install (CORRECTED — primary):** `curl --proto '=https' --tlsv1.2 -LsSf https://github.com/cyfrin/aderyn/releases/latest/download/aderyn-installer.sh | bash` then `cyfrinup`. **Fallback only:** `npm i -g @cyfrin/aderyn` (npm publishing has failed on some releases; the old `~/.cyfrin/bin/aderyn` path is deprecated — remove stale binaries).
- **Validate:** `aderyn --version` (expect v0.6.x)
- **Integration:** SARIF/JSON → normalizer; use for known-issue exclusion lists and CI fail-on-high gating (`Cyfrin/aderyn-ci@v0`).

#### Medusa — parallel coverage-guided fuzzer (primary) `VERIFIED`
- **Source:** https://github.com/crytic/medusa · **License: AGPL-3.0 (VERIFIED — repo: "medusa is licensed and distributed under the AGPLv3")**
- **Role:** parallel mutational fuzzing on go-ethereum; Go API. **Runtime:** precompiled binary, Docker, or `go install`.
- **Install:** download precompiled release binary from the repo Releases page (Linux/macOS), or build with Go 1.21+. CI: `crytic/medusa-action@v2`.
- **Validate:** `medusa --version`
- **Inputs:** contracts + invariants (Chimera/assertion). **Outputs:** HTML coverage report, corpus (the reproducibility anchor), failing call sequences.
- **Integration:** consumes crytic/properties + Chimera-adapted invariants; failing sequences → normalizer → PoC-validation. Config: `medusa.json` (from `medusa init`); `--workers`, `--timeout`, `--test-limit`, `--config`.
- **Common failure:** OOM on large corpora → cap workers, cap sequence length, raise MEM_LIMIT.

#### Echidna — property fuzzer (differential coverage) `VERIFIED`
- **Source:** https://github.com/crytic/echidna · **License: AGPL-3.0 (VERIFIED — repo: "licensed and distributed under the AGPLv3 license")**
- **Role:** Haskell property/assertion fuzzer; run alongside Medusa for differential coverage. **Runtime:** precompiled binary / Docker / brew.
- **Install:** `brew install echidna` (mac/Linux) OR Docker `ghcr.io/crytic/echidna/echidna` OR precompiled release binary.
- **Validate:** `echidna --version`
- **Config:** YAML (`testMode: assertion`, `testLimit`, `corpusDir`, `deployer`, `sender`). **Integration:** shares Chimera invariants with Medusa; consumes Slither.
- **$1K-tier note:** depth-tier only — Medusa alone suffices for quick scans.

#### heimdall-rs — bytecode decompilation (unverified targets) `VERIFIED (command)` / license `PARTIALLY VERIFIED`
- **Source:** https://github.com/Jon-Becker/heimdall-rs · **License: not confirmed — verify with `gh repo view`**
- **Role:** decompile/disassemble/CFG/decode for unverified on-chain contracts. **Runtime:** Rust, RPC-driven.
- **Install:** install `bifrost` from the repo, then `bifrost` → `heimdall`. **Validate:** `heimdall --version` (v0.8.x)
- **Integration:** only when target source is unverified; output is approximate — a hint, never authority (never feed decompiled source to the classifier as ground truth).

### 9.2 Optional-but-Powerful — Depth Tier

Enable **only** for high-value scopes ($5M+ bounties). At the $1K tier they cost more time than the payout justifies (skip by default).

#### Halmos — bounded symbolic proof `VERIFIED`
- **Source:** https://github.com/a16z/halmos · **License: AGPL-3.0 (VERIFIED — repo sidebar)** · latest v0.3.x
- **Adds:** proves/refutes assertions over all inputs within bounds; counterexamples reproducible as Foundry tests. **When:** critical math/access invariants pre-audit. **Cost:** slow (SMT); run **conditionally** on classifier-flagged critical functions only.
- **Install:** `uv tool install --python 3.12 halmos` (needs z3). Docker: `ghcr.io/a16z/halmos:latest`. **Validate:** `halmos --version`
- **Determinism:** bounded-deterministic; mitigate solver nondeterminism with `--solver-timeout-branching 0`. **Output normalization:** counterexample → Foundry test → PoC-validation stage.

#### hevm — bytecode equivalence checking `VERIFIED`
- **Source:** https://github.com/argotorg/hevm (moved from ethereum/hevm) · **License: AGPL-3.0 (VERIFIED — repo sidebar)** · latest 0.58.0
- **Adds:** symbolic equivalence between two bytecode objects (upgrade/refactor diffs); can run Forge suites symbolically. **When:** verifying an upgrade didn't change semantics. **Cost:** high; **manual** invocation.
- **Install:** `nix profile install github:argotorg/hevm` OR static binaries from Releases (need z3). **Validate:** `hevm version`

#### Kontrol — full formal verification `VERIFIED (command)` / license `PARTIALLY VERIFIED`
- **Source:** https://github.com/runtimeverification/kontrol · docs https://docs.runtimeverification.com/kontrol · **License:** stated BSD-3-Clause, **verify with `gh repo view`**
- **Adds:** KEVM+Foundry formal proofs of the highest-value mechanisms (as Optimism did for pausability). **When:** rare, top-tier scopes. **Cost:** very high (first run 30m–1h compile; steep K learning curve); **manual** only.
- **Install:** install `kup` (K package manager), then `kup install kontrol`. CI: `runtimeverification/install-kontrol@v1.0.2`. **Validate:** `kontrol version`

#### Wake — Python-native static + MGF `VERIFIED`
- **Source:** https://github.com/Ackee-Blockchain/wake · docs https://ackee.xyz/wake/docs/latest/ · **License: ISC (VERIFIED — PyPI "OSI Approved (ISC)")**
- **Adds:** Python-native detectors + manually-guided fuzzing; LSP; solc manager. **When:** if you prefer a Python-native alternative stack; non-redundant only for MGF workflows. **Cost:** medium.
- **Install (CORRECTED):** `pip3 install eth-wake` (NOT `wake`; the `woke` package is deprecated). Python 3.8+. Docker: `ackeeblockchain/wake`. **Validate:** `wake --version`

### 9.3 Non-EVM Extensions

**Do not imply EVM tooling analyzes non-EVM targets.** Each ecosystem is a separate branch with its own build system, parser, and execution environment. The orchestrator selects the branch by ecosystem detection (§6). `REQUIRES IMPLEMENTATION` for the detection/branch-selection logic.

#### Solana — Trident (fuzzing) `PARTIALLY VERIFIED`
- **Source:** https://github.com/Ackee-Blockchain/trident · docs https://ackee.xyz/trident/docs/latest/basics/installation/ · **License: verify with `gh repo view`**
- **Adds:** Rust coverage-guided fuzzing of Solana/Anchor programs; generates fuzz tests from Anchor IDL; TridentSVM execution. **Runtime:** Rust + Anchor workspace (Anchor 0.29.0+). **Dependencies:** Solana toolchain, Anchor, honggfuzz backend.
- **Install:** cargo-based per official installation docs (confirm the exact `cargo install` command on the linked page — `PARTIALLY VERIFIED`). **Validate:** `trident --version`
- **Adapter note:** Solana programs are NOT Foundry-compatible — Trident output normalizes to the shared schema (§10) via a Solana-specific adapter you build (`REQUIRES IMPLEMENTATION`).

#### Solana — sec3 X-Ray (static) `PARTIALLY VERIFIED`
- **Source:** https://github.com/sec3-product/x-ray · **License: verify with `gh repo view`**
- **Adds:** Rust→AST→LLVM-IR static analysis; 50+ Solana vuln types (missing signer/owner checks, overflow, account cosplay). Docker + GitHub Action. **Install:** per repo README (`PARTIALLY VERIFIED`).

#### Move — Aptos Move Prover `VERIFIED (command)`
- **Source:** https://aptos.dev/build/smart-contracts/prover · **License:** Apache-2.0 (`PARTIALLY VERIFIED` against repo)
- **Adds:** formal verification via Boogie + Z3 with MSL specs. **Install:** part of the Aptos CLI; run `aptos move prove`. **Dependencies:** Aptos CLI, Boogie, Z3.

#### Move — Sui Prover `PARTIALLY VERIFIED`
- **Source:** https://github.com/asymptotic-code/sui-prover · **License: verify with `gh repo view`**
- **Adds:** Boogie+Z3 formal verification for Move on Sui. **Install:** Homebrew per repo (`PARTIALLY VERIFIED`).

---

## 10. Invariant Library + shared output/artifact schema

### 10.1 Tier 1 — Reusable properties & invariant code `VERIFIED`

| Resource | Role | Source | Install |
|---|---|---|---|
| **crytic/properties** | 168 properties: ERC-20 (25), ERC-721 (19), ERC-4626 (37), ABDKMath (106) | https://github.com/crytic/properties | `forge install crytic/properties` (`VERIFIED`); License **AGPL-3.0** |
| **create-chimera-app** | invariant harness skeleton; one suite → Foundry/Echidna/Medusa/Halmos | https://github.com/Recon-Fuzz/create-chimera-app | fork + `forge install` |
| **Recon Chimera** | multi-tool property framework | https://github.com/Recon-Fuzz/chimera | `forge install Recon-Fuzz/chimera` |
| **a16z/erc4626-tests** | implementation-independent ERC-4626 property tests | https://github.com/a16z/erc4626-tests | `forge install a16z/erc4626-tests` |

**Directory + metadata schema** (`REQUIRES IMPLEMENTATION`): store each invariant set under `invariants/<archetype>/` and index in `invariants/registry.json`:

```json
{
  "id": "lending-health-factor-001",
  "archetype": "lending",
  "vuln_category": "insolvency / missing-health-check",
  "frameworks": ["foundry","medusa","echidna","halmos"],
  "source": "derived-from:DeFiHackLabs/euler",
  "status": "VERIFIED",           // VERIFIED | CANDIDATE | DEPRECATED
  "version": "1.0.0",
  "compat_solc": ">=0.8.0",
  "commit": "<git-sha>"
}
```

**Assertion-mode note (`VERIFIED`):** crytic/properties runs in `testMode: assertion` by default — it covers ERC-standard + fixed security properties, NOT protocol-specific logic. Quick-scan tier uses this stock set; depth tier adds authored invariants. **Update rule:** new invariant versions are additive; never overwrite a `VERIFIED` set — bump `version`, keep the old commit, re-run the validation dataset (§10.3) before promoting.

### 10.2 Tier 2 — Categorized findings aggregators `VERIFIED (sources)`

| Source | Role | URL | Note |
|---|---|---|---|
| **Solodit** | 50,000+ aggregated findings, filterable | https://solodit.cyfrin.io | secondary — follow to primary report |
| **Code4rena** | contest findings | https://github.com/code-423n4 · https://code4rena.com/reports | **[WINDING DOWN May 13 2026 — mirror now]** |
| **Sherlock** | contest reports | https://github.com/sherlock-audit · https://audits.sherlock.xyz | primary |
| **Immunefi** | bugfix reviews + PoCs | https://github.com/immunefi-team/bugfix-reviews-pocs | primary |

**Promotion pipeline** (`REQUIRES IMPLEMENTATION`): discovery → classify (confirmed-reusable | protocol-specific | heuristic | duplicate | unsupported | needs-manual-review) → encode as candidate invariant (`status: CANDIDATE`) → test against Tier-3 PoCs → human approve → promote to `status: VERIFIED`. Never let an aggregator finding enter Tier 1 without passing the Tier-3 validation gate.

### 10.3 Tier 3 — Reproducible PoC exploit code (validation dataset) `VERIFIED (sources)`

| Source | Role | URL |
|---|---|---|
| **DeFiHackLabs** | ~691 runnable `forge test` hack reproductions | https://github.com/SunWeb3Sec/DeFiHackLabs |
| **DeFiVulnLabs** | 48 vuln-class Foundry PoCs | https://github.com/SunWeb3Sec/DeFiVulnLabs |

Add as git submodules under `datasets/poc/`. Per-PoC requirements (from repo READMEs): pinned vulnerable commit/block, solc version, **fork URL + fork-block-number**, `forge test` command, expected exploit result (test passes = exploit reproduced). **Isolation:** run every PoC in a sandboxed container with no secrets mounted (§20). **Use:** defensive validation, regression testing, classifier evaluation, benchmarking — your invariant suite must flag the property violation in each reproduced hack it claims to cover.

### 10.4 Tier 4 — Post-mortems & incident databases `VERIFIED (sources)`

| Source | Role | URL | Authority |
|---|---|---|---|
| **rekt.news** | exploit post-mortems + loss leaderboard | https://rekt.news | secondary/editorial |
| **SlowMist Hacked** | ~2,154 incidents, attack-method classified | https://hacked.slowmist.io | security-firm primary |
| **BlockSec Phalcon** | tx replay/trace for dissecting exploits | https://app.blocksec.com/phalcon/explorer | tooling |

**Ingestion** (`REQUIRES IMPLEMENTATION`): verify source authority → dedup against existing records → track updates/corrections → extract affected components + broken assumption → emit `CANDIDATE` invariant → link to related Tier-2 finding + Tier-3 PoC → hold at `CANDIDATE` until a reproducing PoC exists (prevents unverified incident claims entering the validated base).

### 10.5 Shared artifact schema `REQUIRES IMPLEMENTATION`

Every finding written to `artifacts/<job-id>/findings/` uses one record shape:

```json
{
  "finding_id": "uuid",
  "classification": "invariant_violation",   // §6 taxonomy
  "confidence": 0.0,                           // 0–1
  "tool": {"name":"medusa","version":"..."},
  "location": {"file":"src/Vault.sol","line":142},
  "evidence": {"command":"...","exit_code":1,"artifact":"corpus/seq-17.json"},
  "reproduction": {"status":"pass|fail|none","poc":"test/Poc.t.sol"},
  "provenance": {"job_id":"...","git_sha":"...","fork_block":123456}
}
```

---

## 11. Pipeline wiring & orchestration `REQUIRES IMPLEMENTATION`

Per-integration contract (upstream → downstream, format, adapter, trigger, failure, validation, storage, provenance):

| Upstream | Downstream | In → Out | Adapter | Trigger | On failure | Validation |
|---|---|---|---|---|---|---|
| Intake | Detect | repo → framework/ecosystem | crytic-compile / CodeGraph | new job | mark `analysis_failure`, stop | compiles |
| Detect | Static | project → tool jobs | classifier (§6) | ecosystem=EVM | skip branch | archetype set |
| Slither/Aderyn | Normalizer | JSON/SARIF → schema | SARIF parser | tool exit | isolate tool, continue | non-empty parseable |
| Classifier | Fuzz | archetype → invariant set | Chimera Handler Builder | pays-for-Medium=true | fall back to stock props | compiles |
| Medusa/Echidna | Normalizer | corpus/seq → schema | trace parser | tool exit/timeout | preserve partial corpus | seq minimized |
| Normalizer | Classifier | records → labeled records | dedup + rules | all tools done | classify `analysis_failure` | provenance present |
| Classifier | PoC-validate | candidate → Foundry test | Recon/echidna-trace-parser | High/Critical | downgrade to `unconfirmed` | PoC reproduces on fork |
| PoC-validate | Human gate | confirmed PoC → review queue | — | PoC pass | — | reviewer sign-off |

**Sequential vs parallel:** Static (Slither ∥ Aderyn) run in parallel. Fuzzers (Medusa ∥ Echidna) run in parallel on separate cores. Symbolic (Halmos ∥ per-property) parallel. **Sequential gates:** build → static → fuzz/symbolic → normalize → classify → PoC-validate → human gate. PoC validation is a **mandatory sequential human gate** — nothing ships as confirmed without a reproducing Foundry fork test.

## 12. Queueing, concurrency & resource controls `REQUIRES IMPLEMENTATION`

- **Worker queue** per stage; `MAX_WORKERS = nproc`. Fuzzers get dedicated cores; symbolic jobs are memory-gated (cap concurrent Halmos/hevm to RAM/8GB).
- **Per-tool timeouts** (env, §8): Slither 120s, Aderyn 60s, Medusa quick 1200s, Echidna 3600s, Halmos 1800s/property. Timeout → partial-result preserved, tool marked timed-out, pipeline continues.
- **Memory/CPU limits:** run each tool in a cgroup/container with `--memory` and `--cpus`. OOM kills the tool, not the job.
- **Concurrency limits:** cap parallel jobs so aggregate RAM < physical. Symbolic tools are the constraint.

## 13. Failure isolation & retry `REQUIRES IMPLEMENTATION`

- **Circuit breaker:** if a tool fails N consecutive jobs, disable it and route around it (its stage is marked `NOT SUPPORTED` for the run, not fatal).
- **Retry policy:** transient failures (RPC timeout, network) → exponential backoff, max 3. Deterministic failures (compile error) → no retry, mark `analysis_failure`.
- **Checkpointing / resumable jobs:** persist stage completion + corpus after each stage; a killed job resumes from the last checkpoint (corpus + completed-stage marker).
- **Partial-result preservation:** every stage writes outputs before signalling completion, so a downstream crash never loses upstream work.
- **Tool failure isolation:** one tool crashing (Echidna OOM) never blocks the others — the orchestrator collects whatever completed and classifies the rest as `analysis_failure`.

## 14. Logging, evidence & provenance `REQUIRES IMPLEMENTATION`

- Structured JSON logs per job under `logs/<job-id>/`, rotated (§ logrotate, 100MB/file, keep 10).
- Every finding record (§10.5) carries full provenance: tool+version, command, exit code, artifact path, git SHA, fork block. This is non-negotiable — a finding without reproducible provenance is downgraded to `informational`.
- Durable artifacts in `artifacts/<job-id>/`; ephemeral scratch in `work/<job-id>/` (wiped after archival).

---

## 15. Validation & smoke testing `REQUIRES MANUAL VALIDATION`

Per-tool smoke test after install:
```bash
forge --version && anvil --version
slither --version && aderyn --version
medusa --version && echidna --version
halmos --version && hevm version && kontrol version && wake --version
solc-select versions && z3 --version
```
Each must print a version and exit 0. A missing PATH entry is the most common failure — re-source the shell.

## 16. End-to-end pipeline test `REQUIRES MANUAL VALIDATION`

1. Pick one DeFiHackLabs PoC (Tier 3) as a known-positive target.
2. Run intake → detect (should classify EVM + archetype) → static → fuzz with the matching invariant set → normalize → classify.
3. **Success criterion:** the pipeline flags the known vulnerability class for that hack and the PoC-validation stage reproduces it on the pinned fork block. If your invariant claims to cover Euler-class insolvency, the Euler PoC must trip it.
4. Confirm the final report record carries full provenance (§10.5) and the human-gate queue receives the confirmed finding.

## 17. Upgrade procedure `REQUIRES MANUAL VALIDATION`

1. Upgrade one tool at a time (`foundryup`, `uv tool upgrade halmos`, `cyfrinup`, `pip3 install -U eth-wake`, etc.).
2. Re-run §15 smoke + §16 end-to-end **before** the new version touches production jobs.
3. Bump the value in `config/versions.lock`. Never upgrade mid-batch.
4. Re-validate the invariant library against Tier-3 PoCs after any fuzzer/symbolic upgrade (detector/semantics changes can shift results).

## 18. Rollback procedure `REQUIRES MANUAL VALIDATION`

1. Tools are version-pinned binaries — keep the previous binary/venv/toolchain.
2. Roll back by restoring the prior pinned version and reverting `config/versions.lock`.
3. Invariant library: because updates are additive (§10.1), roll back by checking out the prior `registry.json` commit — `VERIFIED` sets are never overwritten, so no data loss.
4. Re-run §15 + §16 to confirm the rolled-back state matches the last known-good.

## 19. Troubleshooting matrix `VERIFIED (per-tool failure modes)`

| Symptom | Likely cause | Verified remediation |
|---|---|---|
| Slither "compilation failed" | wrong solc / bad remappings | `solc-select use <ver>`; fix foundry remappings; ensure project compiles with `forge build` first |
| `foundryup`/`aderyn`/`heimdall` "command not found" | PATH not updated | add `~/.foundry/bin`, `~/.cyfrin/bin`(new location), cargo bin to PATH; re-source shell |
| Aderyn npm install stale/missing | npm publish gaps | use `cyfrinup`/curl installer instead of npm |
| Medusa OOM | corpus/worker count too high | lower `--workers`, cap sequence length, raise container `--memory` |
| Echidna build heavy / slow | Haskell toolchain | use `brew install echidna` or Docker image instead of source |
| Halmos timeout / path explosion | unbounded loops / solver | set `--loop`, `--solver-timeout-*`; scope to critical functions |
| hevm loop blowup | eager exploration | tune `--ask-smt-iterations`; ensure z3 installed |
| Kontrol first run very slow | K framework compile (30m–1h) | expected once; use `install-kontrol` action + cachix in CI |
| Wake `wake: not found` after `pip install wake` | wrong package | install `eth-wake` (the `wake` name is wrong; `woke` is deprecated) |
| Fuzzer "not reproducible" | expecting seed determinism | pin the **corpus directory**, not a seed; fuzzers are not bit-for-bit deterministic |

## 20. Security & sandboxing `REQUIRES IMPLEMENTATION`

- **Run every target and every PoC in an isolated container** — untrusted target code and exploit PoCs must never touch host secrets. No RPC keys, no wallet keys mounted into the analysis container beyond a read-only public RPC.
- **Network:** fuzzers/forks need RPC egress; deny all other egress from analysis containers. Use an allowlist for the RPC endpoint only.
- **Filesystem:** target/scratch dirs mounted read-write and ephemeral; invariant library and datasets mounted **read-only**.
- **PoC isolation:** Tier-3 exploit code runs in a throwaway container, no persistence, wiped after result capture. Treat all PoC repos as defensive/educational per their disclaimers.
- **AGPL §13 note (`VERIFIED`):** Slither, Medusa, Echidna, Halmos, hevm are AGPL-3.0. Running the pipeline **privately** does not trigger §13. Exposing it as a **hosted/SaaS service** triggers source-disclosure obligations — get legal review before any external offering.

## 21. Final installation verification checklist

- [ ] All §15 smoke commands print a version and exit 0
- [ ] `config/versions.lock` fully populated (§7) incl. corpus dir + fork block
- [ ] solc-select has the target's solc version installed and selected
- [ ] z3 installed (Halmos/hevm) `z3 --version`
- [ ] crytic/properties + create-chimera-app forked and building green
- [ ] Tier-3 PoC submodules cloned; one PoC runs and reproduces on fork (§16)
- [ ] Invariant `registry.json` present; `VERIFIED` sets load
- [ ] Per-tool timeouts + memory caps configured (§8/§12)
- [ ] Analysis containers sandboxed; datasets mounted read-only; no secrets in target container (§20)
- [ ] End-to-end test (§16) flags a known hack class and PoC-validates it
- [ ] Human-gate queue receives confirmed findings with full provenance
- [ ] License verification run for `PARTIALLY VERIFIED` tools (`gh repo view <repo> --json licenseInfo` for Aderyn, heimdall-rs, Kontrol, Trident, sec3 X-Ray, Sui Prover, CodeGraph, ToB skills)

---

## Verification status summary

- **`VERIFIED` (official source):** Foundry, Slither (AGPL-3.0), Medusa (AGPL-3.0), Echidna (AGPL-3.0), Halmos (AGPL-3.0), hevm (AGPL-3.0), Wake (ISC; install `eth-wake`), Kontrol install (`kup install kontrol`), crytic/properties (168, AGPL-3.0, `forge install`), solc-select (AGPL-3.0), Code4rena wind-down, DeFiHackLabs/DeFiVulnLabs sources, determinism model (Halmos FAQ).
- **`PARTIALLY VERIFIED` (confirm at install):** Aderyn license, heimdall-rs license, Kontrol license, Trident install command + license, sec3 X-Ray, Move/Sui Prover, CodeGraph license, ToB skills license.
- **`REQUIRES IMPLEMENTATION` (you build):** the orchestrator/bridge, ecosystem-detection + branch selection, the archetype classifier, findings normalizer/dedup/severity/confidence, invariant registry + promotion pipeline, Tier-2/Tier-4 ingestion, per-tool timeout/queue/circuit-breaker/checkpoint machinery, shared artifact schema wiring, sandboxing.
- **`NOT SUPPORTED`:** native Windows full pipeline (use WSL2/Docker); EVM tools analyzing non-EVM targets directly (require the separate Solana/Move branches + adapters).

**The core truth this guide preserves:** you can install and validate every *tool* today from verified commands. The *pipeline that connects them* is yours to build — this document gives you the verified components, the integration contracts, and the honest boundaries so nothing is presented as working that doesn't exist yet.
