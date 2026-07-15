# Security Policy

## Reporting Vulnerabilities

If you discover a security vulnerability in the pipeline itself (not a detected vulnerability in target code), please contact the maintainers directly. Do not file public issues.

## Sandboxing Policy

**Untrusted target code must be run in an isolated container.** The pipeline is not safe for running untrusted target code directly on a host with secrets.

Before production use:
1. Enable Docker sandboxing (`USE_SANDBOX=true` in config/env)
2. Mount only read-only volumes for invariant and dataset directories
3. Restrict network egress to RPC endpoint only
4. Never mount SSH keys, wallet keys, or cloud credentials into analysis containers

## AGPL-3.0 Note

Slither, Medusa, Echidna, Halmos, and hevm are AGPL-3.0 licensed. Running the pipeline privately for bug-bounty work does not trigger §13. Exposing the pipeline as a hosted/SaaS service triggers source-disclosure obligations. Get legal review before any external offering.

## Secret Management

- RPC URLs use short-lived or rate-limited credentials
- No wallet keys or private keys are stored in the pipeline
- Logs are sanitized to prevent secret leakage
- Container images are digest-pinned

## Supply Chain

- All tool versions are pinned in `config/versions.lock`
- Container image digests are verified before use
- Dependency provenance is recorded in `docs/verification-ledger.md`