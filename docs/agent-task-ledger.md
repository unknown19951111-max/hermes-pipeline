# Agent Task Ledger — Smart-Contract Security Pipeline

> **Last updated:** 2026-07-15 (audit: aa1b60db)
> **Status generated from:** `AUDIT_FINDINGS.json` — per-component evidence, not global test count

## Agent Identities

| # | Role | Owner | Description |
|---|------|-------|-------------|
| 1 | **Lead Orchestrator** | Hermes Agent (current session) | Owns implementation plan, dependency graph, task ledger, phase gates, architectural decisions |
| 2 | **Official-Source Verification Agent** | Delegated subagent (phase-gated) | Verifies dependencies against official docs/repos. Maintains verification-ledger.md |
| 3 | **Pipeline Implementation Agent** | Delegated subagent (phase-gated) | Implements intake, build, adapters, orchestration, jobs, state, reporting |
| 4 | **Classifier and Invariant Agent** | Delegated subagent (phase-gated) | Implements archetype classifier, invariant registry, finding normalization/dedup, harness gen |
| 5 | **Validation and Security Agent** | Delegated subagent (phase-gated) | Tests, fixtures, sandbox validation, security review, phase acceptance |

**Hard limit**: Maximum 5 agent identities across the entire project. No nested delegation hierarchies.

---

## File Ownership

| Path Pattern | Owner | Notes |
|---|---|---|
| `orchestrator/intake/` | Agent 3 | Intake subsystem |
| `orchestrator/eligibility/` | Agent 3 | Program eligibility gate |
| `orchestrator/detect/` | Agent 3 | Ecosystem/framework detection |
| `orchestrator/build/` | Agent 3 | Compiler resolution + build |
| `orchestrator/adapters/` | Agent 3 | Tool adapters (Phase 1-2) |
| `orchestrator/normalize/` | Agent 4 | Finding normalization |
| `orchestrator/classify/` | Agent 4 | Archetype classifier |
| `orchestrator/deduplicate/` | Agent 4 | Deduplication |
| `orchestrator/harness/` | Agent 4 | Harness generation |
| `orchestrator/poc/` | Agent 4 | PoC generation/validation |
| `orchestrator/report/` | Agent 4 | Reporting |
| `orchestrator/jobs/` | Agent 3 | Job state/queueing |
| `invariants/` | Agent 4 | Invariant registry + code |
| `datasets/` | Agent 2/Agent 5 | Verified external datasets |
| `tests/` | Agent 5 | All tests |
| `fixtures/` | Agent 5 | Test fixtures |
| `docker/` | Agent 3 | Container definitions |
| `config/` | Agent 3 | Configuration |
| `docs/` | Lead Orchestrator | Documentation |
| `schemas/` | Shared | Shared schemas — finalized sequentially |

**Rules:**
- Only one agent may own a shared file at a time.
- Shared schemas must be finalized sequentially.
- No agent may modify a file owned by another agent without Lead Orchestrator approval.

---

## Task Ledger

| ID | Description | Owner | Dependencies | Status | Files Owned | Verification |
|---|---|---|---|---|---|---|
| P0 | Planning documents creation | Agent 1 | None | ✅ DONE | docs/, config/ | Review by Agent 1 |
| S1a | Intake subsystem | Agent 3 | P0 | ❌ BLOCKED | orchestrator/intake/ | F-002: `kwargs` undefined NameError. F-003: symlink disclosure. Remote intake unusable. |
| S1b | Ecosystem/framework detection | Agent 3 | P0 | ✅ DONE | orchestrator/detect/ | E2E: evm @ 1.00, foundry @ 0.95. Unit tests: detect, ecosystem, framework, fallback. |
| S1c | Build/compiler resolver | Agent 3 | P0 | 🔶 PARTIAL | orchestrator/build/ | F-022: `--via-ir` forced. F-023: `build_env` not passed to subprocess. F-015: no sandbox. |
| S1d | Shared findings schema | Agent 4 | P0 | ❌ BLOCKED | schemas/ | F-005: `jsonschema.validate()` never called. F-024: tests use manual checks only. |
| S1e | Slither adapter | Agent 3 | S1c, S1d | ❌ BLOCKED | orchestrator/adapters/slither/ | F-004: `success=exit_code==0 or len(normalized)>0`. F-015: no sandbox. F-016: host env. |
| S1f | Artifact storage + manifests | Agent 3 | P0 | ✅ DONE | orchestrator/intake/ | E2E: manifest generated, commit SHA recorded, artifact store works. |
| VS1 | Vertical slice 1 test | Agent 5 | S1a–S1f | ❌ BLOCKED | tests/e2e/ | F-010: accepts any warning. F-011: no patched assertion. F-014: `__main__` crashes. |
| S2a | Program eligibility gate | Agent 3 | VS1 | ❌ FAILED | orchestrator/eligibility/ | F-001: `_validate()` requires `status`, `create()` writes `program_status`. Always raises. |
| S2b | Archetype classifier | Agent 4 | VS1 | ✅ DONE | orchestrator/classify/ | 9 unit tests pass. 12 archetypes, rule-based, multi-label works. |
| S2c | Deduplication | Agent 4 | S1d | 🔶 PARTIAL | orchestrator/deduplicate/ | Dedup works per-tool. Cross-tool grouping untested (keys use tool-specific rule IDs). |
| S2d | Invariant registry | Agent 4 | S2b | ❌ BLOCKED | invariants/registry.json | F-006: 9/10 invariants falsely VERIFIED (no source commit, no validation history). |
| S2e | Aderyn adapter | Agent 3 | VS1 | ❌ BLOCKED | orchestrator/adapters/aderyn/ | Same F-004, F-015, F-016 as Slither. Not run in E2E test. |
| S2f | Confidence model | Agent 4 | S1d | ✅ DONE | orchestrator/classify/ | 0-5 rubric in `finding.json` schema. Unit tested. |
| S3a | Invariant selection/compat | Agent 4 | S2d, S2b | ❌ BLOCKED | orchestrator/classify/ | F-006: registry references phantom invariant IDs not in registry. |
| S3b | Harness generation | Agent 4 | S3a, S1c | ❌ BLOCKED | orchestrator/harness/ | F-007: 4 archetypes produce empty no-op functions. F-008: tautological ERC-4626. |
| S3c | Medusa adapter | Agent 3 | S3b | 🔶 PARTIAL | orchestrator/adapters/medusa/ | Adapter exists. `medusa` binary not installed. Dependency check only. |
| S3d | Corpus preservation | Agent 3 | S3c | 🔶 NOT_IMPLEMENTED | orchestrator/adapters/medusa/ | Not implemented in execution path. |
| S3e | Echidna adapter | Agent 3 | S3b | 🔶 PARTIAL | orchestrator/adapters/echidna/ | Adapter exists. Dependency check only. No actual fuzzing tested. |
| S3f | PoC generation | Agent 4 | S3c | ❌ BLOCKED | orchestrator/poc/ | F-009: both PASSED and FAILED return `reproduction=True`. |
| S3g | Human-review routing | Agent 3 | S3f | 🔶 PARTIAL | orchestrator/jobs/ | `HumanReviewQueue` exists. Not integrated into CLI. |
| S4a | Persistent job state | Agent 3 | VS1 | ✅ DONE | orchestrator/jobs/ | `JobState` with JSON file persistence. Unit tested. |
| S4b | Checkpointing | Agent 3 | S4a | ✅ DONE | orchestrator/jobs/ | `CheckpointManager` save/load/resume. Unit tested. |
| S4c | Sandboxing | Agent 3 | VS1 | ❌ BLOCKED | docker/ | F-015: `SandboxManager` exists but never called from build or adapter code. |
| S5 | Phase 1 acceptance | Agent 5 | All Phase 1 | ❌ BLOCKED | docs/phase-acceptance.md | 20 P0 findings. Phase 1: 45 criteria, only 15 passing. |

---

## Dependency Graph (Phase 1 first vertical slice)

```
P0 (planning docs)
  ├─ S1a (intake) ─── ❌ BLOCKED (F-002, F-003)
  ├─ S1b (ecosystem detection) ─── ✅ DONE
  ├─ S1c (build resolver) ─── 🔶 PARTIAL (F-022, F-023)
  ├─ S1d (shared schema) ─── ❌ BLOCKED (F-005)
  │    ├─ S1e (Slither adapter) ─── ❌ BLOCKED (F-004, F-015, F-016)
  │    └─ S1f (artifact storage) ─── ✅ DONE
  │         └─ VS1 (vertical slice 1) ─── ❌ BLOCKED (F-010, F-011, F-014)
  │              ├─ S2a (eligibility) ─── ❌ FAILED (F-001)
  │              ├─ S2b (classifier) ─── ✅ DONE
  │              ├─ S2e (Aderyn) ─── ❌ BLOCKED (F-004, F-015, F-016)
  │              ├─ S4a (job state) ─── ✅ DONE
  │              ├─ S4b (checkpointing) ─── ✅ DONE
  │              └─ S4c (sandbox) ─── ❌ BLOCKED (F-015)
  │
  ├─ S2c (dedup) ─── 🔶 PARTIAL
  ├─ S2d (invariant registry) ─── ❌ BLOCKED (F-006)
  │    └─ S3a (invariant selection) ─── ❌ BLOCKED (F-006)
  │         ├─ S3b (harness) ─── ❌ BLOCKED (F-007, F-008)
  │         │    ├─ S3c (Medusa) ─── 🔶 PARTIAL
  │         │    │    ├─ S3d (corpus) ─── 🔶 NOT_IMPLEMENTED
  │         │    │    └─ S3f (PoC) ─── ❌ BLOCKED (F-009)
  │         │    │         └─ S3g (human review) ─── 🔶 PARTIAL
  │         │    └─ S3e (Echidna) ─── 🔶 PARTIAL
  │         └─ S2f (confidence) ─── ✅ DONE
  │
  └─ S5 (Phase 1 acceptance) ─── ❌ BLOCKED (20 P0)
```

---

## Handoff Format

When a task completes:
```
HANDOFF: <TASK_ID> → <DOWNSTREAM_AGENT>
STATUS: COMPLETED | FAILED | BLOCKED
EVIDENCE: <path to test output / artifact>
FILES: <list of files created/modified>
SCHEMA VERSION: <version>
BLOCKING ISSUES: <any>
```

## Escalation Procedure

1. Agent identifies block → logs in task ledger with `BLOCKED`
2. Notifies Lead Orchestrator
3. Lead Orchestrator resolves conflict or reassigns
4. If dependency requires architecture change → Agent 1 approves
5. If file ownership conflict → Agent 1 resolves
6. If scope expansion → Agent 1 approves
7. Blocked agent does NOT create a new agent