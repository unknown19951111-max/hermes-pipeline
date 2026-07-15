# Architecture — Smart-Contract Security Pipeline

## System Overview

A modular, phase-gated pipeline for automated smart-contract security auditing. The system accepts a repository target, analyzes it through a staged toolchain, and produces provenance-backed findings with deterministic classification.

## Core Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                         HERMES ORCHESTRATOR                         │
│                                                                     │
│  Intake ─→ Detect ─→ Build ─→ Static ─→ Classify ─→ Fuzz ─→ PoC    │
│     │         │         │         │          │        │      │      │
│     └─── Eligibility gate (GATE ZERO) ──────┘        │      │      │
│                                                       │      │      │
│  ┌────────────────────────────────────────────────────┘      │      │
│  │  Raw tool outputs → Normalizer → Dedup → Classifier       │      │
│  │                                    → Confidence → Report   │      │
│  └────────────────────────────────────────────────────────────┘      │
│                                                                     │
│  ┌────────────────────────────────────────────────────────────┐     │
│  │  Invariant Registry ←─── Tier-2/3/4 intake (manual)        │     │
│  │  Harness Generator ←──── Select + adapt invariants          │     │
│  └────────────────────────────────────────────────────────────┘     │
└─────────────────────────────────────────────────────────────────────┘
```

## Stage Contracts

### Intake → Detect
- **In**: Repository URL or local path, optional scope/eligibility metadata
- **Out**: Pinned commit SHA, intake manifest (JSON), program eligibility snapshot
- **Adapter**: Git clone + branch/commit capture + scope file parsing
- **Failure**: Mark `analysis_failure`, stop pipeline

### Detect → Build
- **In**: Target filesystem root
- **Out**: Ecosystem (EVM/Solana/Move/Unknown), framework (Foundry/Hardhat/Standard), confidence, evidence
- **Adapter**: File-pattern detection, manifest parsing, extension analysis
- **Failure**: Ambiguous detection → `analysis_failure`; no detection without deterministic evidence

### Build → Static
- **In**: Target root, compiler version, framework type
- **Out**: Compiled artifacts (JSON ABI/bytecode), build logs, compiler version record, build manifest
- **Adapter**: solc-select + forge build / npx hardhat compile
- **Failure**: Compilation error → mark `analysis_failure`, stop analysis stages

### Static → Normalize
- **In**: Tool-specific JSON/SARIF output
- **Out**: Unified finding records conforming to shared schema
- **Adapter**: Tool-specific parser (one per tool), validating against JSON Schema
- **Failure**: Malformed output → quarantine, preserve raw, mark `analysis_failure`

### Normalize → Classify
- **In**: Normalized finding records
- **Out**: Labeled findings (taxonomy from §9.9), confidence scores (0-5 rubric), dedup groups
- **Adapter**: Rule-based classification + confidence rubric, deterministic dedup
- **Failure**: Unclassifiable → `unsupported_hypothesis`

### Classify → Fuzz (conditional)
- **In**: Protocol archetype, invariant registry, target source
- **Out**: Compatible invariant set, Chimera harness, fuzzer config
- **Adapter**: Archetype→invariant mapping, compatibility validation, harness generation
- **GATE**: Only if eligibility passes + archetype maps to invariants

### Fuzz → PoC
- **In**: Failing sequences, corpus, execution context
- **Out**: Minimized failing sequence, Foundry test scaffolding
- **Adapter**: Sequence minimization, test generation, pinned-fork reproduction
- **Failure**: Sequence not reproducible → downgrade confidence

### PoC → Human Review
- **In**: Confirmed PoC candidate with full provenance
- **Out**: Review queue entry (no automation beyond this point)
- **Gate**: Only promoted to `confirmed_vulnerability` by human reviewer

## Data Flow

```
┌────────────┐    ┌───────────┐    ┌──────────┐    ┌──────────────┐
│ Repository  │───→│ Intake    │───→│ Detect   │───→│ Build        │
│ (remote/    │    │ (clone,   │    │ (eco +   │    │ (forge/hard  │
│  local)     │    │  pin)     │    │  framework)│    │  + solc)    │
└────────────┘    └───────────┘    └──────────┘    └──────┬───────┘
                                                          │
                     ┌────────────────────────────────────┘
                     ▼
              ┌──────────────┐
              │ Static       │ ← Slither (JSON)
              │ Analysis     │ ← Aderyn (SARIF/JSON)
              │ (parallel)   │
              └──────┬───────┘
                     ▼
              ┌──────────────┐
              │ Normalizer   │ → Shared finding records
              │ + Dedup      │ → Dedup groups
              │ + Classifier │ → Labels + confidence
              └──────┬───────┘
                     ▼
              ┌──────────────┐
              │ Eligibility  │─── If INELIGIBLE → stop or flag
              │ Gate         │─── If ELIGIBLE → continue
              └──────┬───────┘
                     ▼
              ┌──────────────┐
              │ Archetype    │─── Token? → ERC-20 props
              │ Classifier   │─── Vault? → ERC-4626 props
              │              │─── Lending? → health-factor props
              │              │─── Hybrid? → multi-label
              └──────┬───────┘
                     ▼
              ┌──────────────┐
              │ Invariant    │─── Select compatible props
              │ Selection    │─── Reject incompatible
              └──────┬───────┘
                     ▼
              ┌──────────────┐
              │ Harness      │─── Generate/adapt Chimera suite
              │ Generator    │─── Compile check
              └──────┬───────┘
                     ▼
              ┌──────────────┐
              │ Fuzz         │ ← Medusa (primary)
              │ (parallel)   │ ← Echidna (differential)
              └──────┬───────┘
                     ▼
              ┌──────────────┐
              │ PoC Gen      │─── Minimize sequence
              │              │─── Scaffold Foundry test
              └──────┬───────┘
                     ▼
              ┌──────────────┐
              │ Human Review │─── Final confirmation
              └──────┬───────┘
                     ▼
              ┌──────────────┐
              │ Report       │─── Full provenance
              └──────────────┘
```

## Security Architecture

```
┌─ Container 1 (Analysis Container) ──────────────────┐
│                                                      │
│  Writable: work/<job-id>/    (ephemeral)            │
│  Read-only: invariants/      (immutable library)    │
│  Read-only: datasets/        (immutable PoCs)       │
│  Network:   RPC endpoint only (allowlisted)         │
│  No access: host SSH, Docker socket, credentials    │
│                                                      │
│  ┌─ Orchestrator Process ──────────────────────┐    │
│  │  │
│  │  ├── Repository Manager (git clone)         │    │
│  │  ├── Build Executor (forge/hardhat)         │    │
│  │  ├── Tool Adapters (isolated subprocesses)  │    │
│  │  └── Job State Manager (persistent JSON)    │    │
│  └─────────────────────────────────────────────┘    │
└──────────────────────────────────────────────────────┘

┌─ Host System ────────────────────────────────────────┐
│  artifacts/    → Durable persistent findings storage │
│  config/       → Read-only config + license files    │
│  ETH_RPC_URL   → Short-lived or rate-limited key     │
│  No wallet/SSH/cloud keys in target containers       │
└──────────────────────────────────────────────────────┘
```

## Configuration Model

```yaml
# config/machine-profile.yaml
machine:
  architecture: x86_64
  cpus_configured: 16
  ram_gb: 32
  storage_gb: 200
  
reserved:
  os_cpus: 1
  os_ram_gb: 4
  
limits:
  max_concurrent_containers: 4
  max_concurrent_static: 2
  max_concurrent_fuzz: 2
  max_concurrent_symbolic: 1
  max_job_workspace_gb: 20
  max_artifact_gb: 10
  max_corpus_gb: 5

per_tool:
  slither: { cpus: 1, ram_gb: 2, timeout_s: 120 }
  aderyn: { cpus: 1, ram_gb: 1, timeout_s: 60 }
  medusa: { cpus: 4, ram_gb: 8, timeout_s: 1200 }
  echidna: { cpus: 2, ram_gb: 4, timeout_s: 3600 }
  halmos: { cpus: 2, ram_gb: 8, timeout_s: 1800 }
```