# Agent Task Ledger — Smart-Contract Security Pipeline

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
| P0 | Planning documents creation | Agent 1 | None | ✅ DONE | docs/ agent-task-ledger, verification-ledger, phase-acceptance; ARCHITECTURE, IMPLEMENTATION_PLAN, THREAT_MODEL, LICENSE_MATRIX, config/ | Review by Agent 1 |
| S1a | Intake subsystem | Agent 3 | P0 | 🔲 PENDING | orchestrator/intake/ | Tests by Agent 5 |
| S1b | Ecosystem/framework detection | Agent 3 | P0 | 🔲 PENDING | orchestrator/detect/ | Tests by Agent 5 |
| S1c | Build/compiler resolver | Agent 3 | P0 | 🔲 PENDING | orchestrator/build/ | Tests by Agent 5 |
| S1d | Shared findings schema | Agent 4 | P0 | 🔲 PENDING | schemas/ | Tests by Agent 5 |
| S1e | Slither adapter | Agent 3 | S1c, S1d | 🔲 PENDING | orchestrator/adapters/slither/ | Tests by Agent 5 |
| S1f | Artifact storage + manifests | Agent 3 | P0 | 🔲 PENDING | orchestrator/intake/ | Tests by Agent 5 |
| VS1 | Vertical slice 1 test | Agent 5 | S1a–S1f | 🔲 PENDING | tests/e2e/ | Runtime evidence |
| S2a | Program eligibility gate | Agent 3 | VS1 | 🔲 PENDING | orchestrator/eligibility/ | Tests by Agent 5 |
| S2b | Archetype classifier | Agent 4 | VS1 | 🔲 PENDING | orchestrator/classify/ | Tests by Agent 5 |
| S2c | Deduplication | Agent 4 | S1d | 🔲 PENDING | orchestrator/deduplicate/ | Tests by Agent 5 |
| S2d | Invariant registry | Agent 4 | S2b | 🔲 PENDING | invariants/registry.json | Tests by Agent 5 |
| S2e | Aderyn adapter | Agent 3 | VS1 | 🔲 PENDING | orchestrator/adapters/aderyn/ | Tests by Agent 5 |
| S2f | Confidence model | Agent 4 | S1d | 🔲 PENDING | orchestrator/classify/ | Tests by Agent 5 |
| S3a | Invariant selection/compat | Agent 4 | S2d, S2b | 🔲 PENDING | orchestrator/classify/ | Tests by Agent 5 |
| S3b | Harness generation | Agent 4 | S3a, S1c | 🔲 PENDING | orchestrator/harness/ | Tests by Agent 5 |
| S3c | Medusa adapter | Agent 3 | S3b | 🔲 PENDING | orchestrator/adapters/medusa/ | Tests by Agent 5 |
| S3d | Corpus preservation | Agent 3 | S3c | 🔲 PENDING | orchestrator/adapters/medusa/ | Tests by Agent 5 |
| S3e | Echidna adapter | Agent 3 | S3b | 🔲 PENDING | orchestrator/adapters/echidna/ | Tests by Agent 5 |
| S3f | PoC generation | Agent 4 | S3c | 🔲 PENDING | orchestrator/poc/ | Tests by Agent 5 |
| S3g | Human-review routing | Agent 3 | S3f | 🔲 PENDING | orchestrator/jobs/ | Tests by Agent 5 |
| S4a | Persistent job state | Agent 3 | VS1 | 🔲 PENDING | orchestrator/jobs/ | Tests by Agent 5 |
| S4b | Checkpointing | Agent 3 | S4a | 🔲 PENDING | orchestrator/jobs/ | Tests by Agent 5 |
| S4c | Sandboxing | Agent 3 | VS1 | 🔲 PENDING | docker/ | Tests by Agent 5 |
| S5 | Phase 1 acceptance | Agent 5 | All Phase 1 | 🔲 PENDING | docs/phase-acceptance.md | 19 acceptance criteria |

---

## Dependency Graph (Phase 1 first vertical slice)

```
P0 (planning docs)
  └─ S1a (intake)
  └─ S1b (ecosystem detection)
  └─ S1c (build resolver)
  └─ S1d (shared schema)
       ├─ S1e (Slither adapter) ── depends on S1c, S1d
       └─ S1f (artifact storage) ── depends on S1a
            └─ VS1 (vertical slice 1) ── depends on S1a, S1b, S1c, S1d, S1e, S1f
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
