# Threat Model — Smart-Contract Security Pipeline

## Asset Inventory

| Asset | Sensitivity | Description |
|---|---|---|
| ETH_RPC_URL / API keys | HIGH | Provider credential; could be abused for unpaid compute |
| Target source code | VARIABLE | Untrusted third-party code; may be malicious |
| PoC exploit code | HIGH | Working exploit PoCs; must be sandboxed |
| Pipeline output (findings) | MEDIUM | Confidential until disclosed per bounty terms |
| Invariant library | HIGH | Proprietary competitive advantage; must be immutable |
| Container images | MEDIUM | Supply-chain risk from unofficial images |
| Job artifacts | MEDIUM | Evidence trail; must be tamper-proof |

## Threat Scenarios

### T1: Malicious Target Code
- **Scenario**: Target repository contains malicious code designed to compromise the pipeline
- **Attack vectors**: Executable scripts in package.json/scripts, Makefile targets, git hooks, postinstall scripts
- **Impact**: Host compromise, data exfiltration, credential theft
- **Mitigations**:
  - Run all target code in isolated containers (no host access)
  - Read-only base filesystem in containers
  - No SSH agent, Docker socket, or credentials in containers
  - Network egress restricted to RPC allowlist only
  - Process/fork/memory limits enforced
  - Archive extraction protections (symlinks, path traversal)

### T2: Exploit PoC Leakage
- **Scenario**: Working PoC exploit code from Tier-3 datasets or in-house generation leaked via output
- **Attack vectors**: Log output containing private keys, traces containing exploit steps
- **Impact**: Responsible disclosure bypass, reputational damage, legal liability
- **Mitigations**:
  - PoC code runs in throwaway containers; no persistence
  - Output sanitization (secret redaction)
  - Log rotation with bounded retention
  - Artifact access controls

### T3: Supply-Chain Attack on Toolchain
- **Scenario**: Compromised upstream dependency (PyPI package, Nix package, GitHub release)
- **Attack vectors**: Malicious release of Slither/Aderyn/Medusa via package manager
- **Impact**: Malicious analysis results, data exfiltration, credential theft
- **Mitigations**:
  - Version-pinned tool installations (no `latest` tags)
  - Container image digest pinning
  - Dependency provenance records
  - Verification of checksums where available

### T4: Resource Exhaustion (DoS)
- **Scenario**: Malicious target triggers unbounded compilation, fuzzing, or symbolic execution
- **Attack vectors**: Fork bomb, disk fill, memory exhaustion, long compilation
- **Impact**: Pipeline denial of service, host instability
- **Mitigations**:
  - Per-tool timeouts (env-configured)
  - cgroup memory/CPU limits
  - Disk size limits per job workspace
  - Process count limits
  - Circuit breakers after N consecutive failures

### T5: Eligibility Gate Bypass
- **Scenario**: Classification error allows ineligible target to pass GATE ZERO
- **Attack vectors**: Ambiguous payout table, stale program data, LLM guess
- **Impact**: Wasted compute on non-paying targets, missed GATE ZERO filter
- **Mitigations**:
  - Deterministic eligibility check (not LLM-based)
  - `AMBIGUOUS_REQUIRES_REVIEW` enters manual review
  - Immutable eligibility snapshot preserved with job
  - Expensive fuzzing blocked for `INELIGIBLE`

### T6: Cross-Job Contamination
- **Scenario**: One job's artifacts affect another job's results
- **Attack vectors**: Shared corpus directory, shared build cache, shared workspace
- **Impact**: False findings, corpus corruption, non-reproducible results
- **Mitigations**:
  - Per-job workspace isolation
  - Read-only invariant/dataset mounts
  - Job-scoped artifact storage

### T7: Configuration Injection
- **Scenario**: Target code influences pipeline configuration
- **Attack vectors**: foundry.toml with malicious parameters, hardhat.config.js
- **Impact**: Tool misconfiguration, code execution
- **Mitigations**:
  - Pipeline config is fixed per job
  - Target config files are NOT sourced by the orchestrator
  - Only compiler/build config is read from target

## Trust Boundaries

```
[External Internet] ──→ [Container] ──→ [Host]
       │                    │                │
  Target repo            Analysis        Artifacts
  RPC endpoint           Sandbox         Config files
  Program page           No host net     RPC key
```

1. **External → Container**: Untrusted target code enters sandbox
2. **Container → Host**: Only normalized findings + artifacts (no raw target execution)
3. **Container → Network**: RPC endpoint only (allowlisted)
4. **Host → Container**: Config + invariant library (read-only), RPC key (limited)

## Assumptions

- Container runtime (Docker/Podman) is properly configured and isolated
- Host kernel is up-to-date with container escape mitigations
- RPC provider enforces rate limits; key exposure is limited
- No persistent state in work/ directory (ephemeral)
- Logs are not confidential but should not expose RPC keys