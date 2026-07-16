# Hermes Pipeline

Automated smart-contract security auditing. EVM + Solana + Move in one pipeline.

```
hermes-pipeline detect /path/to/project    # What ecosystem + framework?
hermes-pipeline list-tools                 # What's installed?
hermes-pipeline run /path/to/project       # Audit it
```

## Quickstart

```bash
# detect + run on the vulnerable EVM fixture
cd hermes-pipeline
PYTHONPATH=src python3 -m orchestrator.cli detect fixtures/vulnerable
PYTHONPATH=src python3 -m orchestrator.cli run fixtures/vulnerable

# list what's available
PYTHONPATH=src python3 -m orchestrator.cli list-tools
```

## Installation

```bash
pip3 install -e .                          # install the CLI
hermes-pipeline list-tools                 # verify installation
```

### Dependencies

| Layer | Tools |
|---|---|
| **EVM core** | Foundry, Slither, Aderyn, Medusa, Echidna |
| **EVM depth** | Halmos, hevm, Wake |
| **Solana** | solana-cli, Trident (Anchor graceful) |
| **Move** | Aptos CLI, Sui CLI, Move Prover (all graceful) |
| **Infra** | Python 3.10+, Docker (optional), Go 1.21+ (optional) |

## Architecture

```
src/orchestrator/
├── cli.py                 # CLI entry point
├── detect/                # ecosystem + framework detection
├── adapters/              # tool adapters (EVM + Solana + Move)
│   ├── base_adapter.py    # abstract base + AdapterResult
│   ├── slither_adapter.py
│   ├── aderyn_adapter.py
│   ├── medusa_adapter.py
│   ├── echidna_adapter.py
│   ├── halmos_adapter.py
│   ├── hevm_adapter.py
│   ├── wake_adapter.py
│   ├── solana_adapter.py  # Anchor, SolanaCLI, Trident
│   ├── move_adapter.py    # Aptos, Sui, MoveProver
│   ├── kontrol_adapter.py # graceful
│   └── heimdall_adapter.py# graceful
├── classify/              # archetype classifier + invariant registry
├── jobs/                  # sandbox, failure isolation, checkpoints
├── normalize/             # finding normalization + dedup
├── poc/                   # PoC generation scaffolding
├── intake/                # remote + local target intake
├── harness/               # Chimera-compatible harness gen
└── eligibility/           # program eligibility (GATE ZERO)
```

## Phase Status

| Phase | Criteria | Suites | Status |
|---|---|---|---|
| 1 — EVM Production MVP | 45 | 5 (39 tests) | ✅ |
| 2 — EVM Depth Tier | 13 | 1 (19 tests) | ✅ |
| 3 — Non-EVM Branches (Solana + Move) | 24 (12 each) | 1 (25 tests) | ✅ |
| **Total** | **82** | **7 (~83 tests)** | ✅ |

## CLI

```
Usage: hermes-pipeline COMMAND [ARGS]...

Commands:
  detect      Detect ecosystem + framework for a target directory
  list-tools  List installed tools with versions
  run         Run the full pipeline and output findings

Options:
  --json      JSON output
  -o, --output FILE  Write results to file (run only)
```

## Fixtures

| Directory | Ecosystem | What it demonstrates |
|---|---|---|
| `fixtures/vulnerable/` | EVM (Foundry) | reentrancy-eth vulnerability |
| `fixtures/patched/` | EVM (Foundry) | same code, reentrancy fixed |
| `fixtures/solana_vulnerable/` | Solana (Anchor) | missing signer check |
| `fixtures/solana_patched/` | Solana (Anchor) | signer enforced via `#[account(signer)]` |
| `fixtures/move_vulnerable/` | Move (Aptos) | missing access control on withdraw |
| `fixtures/move_patched/` | Move (Aptos) | owner check enforced via `assert!` |

## License

ISC — see [LICENSE_MATRIX.md](LICENSE_MATRIX.md).