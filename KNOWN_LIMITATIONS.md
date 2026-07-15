# Known Limitations

## Phase 1 — EVM Production MVP

### Technical Limitations
1. **No hardened sandboxing yet** — Pipeline runs directly on host. Docker sandboxing configuration is defined but not enforced. Target code has host filesystem access. **Do not use on untrusted targets until sandboxing is active.**

2. **No PoC extraction yet** — Failing sequences from Medusa/Echidna are preserved but not automatically converted to Foundry tests. PoC generation is manual.

3. **No remote repository testing** — E2E tests use local fixtures only. Remote repo intake is implemented but not verified in CI.

4. **macOS-only development** — Pipeline was developed and tested on macOS ARM64. Production target is Ubuntu x86-64. Cross-platform issues may exist.

5. **No fuzzing in E2E test** — Vertical Slice 1 only covers intake→build→static analysis→normalization. Fuzzing adapters (Medusa, Echidna) are verified at the adapter level only.

### Feature Gaps
6. **No multi-contract analysis** — Classifier handles one contract at a time. Cross-contract attack paths are not analyzed.

7. **No Halmos/hevm/Kontrol adapters** — Phase 2 tools are not yet implemented.

8. **No non-EVM branches** — Solana and Move support is Phase 3.

9. **No automated invariant promotion** — Registry promotion from CANDIDATE to VERIFIED requires manual validation.

10. **No formal verification** — Phase 2 symbolic tools are needed for formal verification capabilities.

### Economic Limitations
11. **GATE ZERO requires manual data** — Program eligibility data must be provided or scraped. No automated web scraping is integrated.

12. **Market contraction risk** — DeFi TVL contracted ~50% (2025-2026). Fewer programs pay for Medium findings.

## Tool-Specific Limitations
13. **Slither exit code 255** — Slither returns 255 even on success (with findings). Adapter treats exit code 255 as success.

14. **Aderyn output format** — Aderyn's JSON output format may change between versions. Current adapter tested against v0.6.8 only.

15. **Medusa missing from PATH** — Installed at ~/go/bin/medusa, which may not be in PATH by default. Adapter searches common locations.