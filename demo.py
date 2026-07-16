#!/usr/bin/env python3
"""
Hermes Pipeline Demo — runs the full pipeline on all 3 ecosystems.
"""
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent
ENV = {**os.environ, "PYTHONPATH": str(ROOT / "src")}

def run(label, cmd):
    print(f"\n  ── {label} ──")
    print(f"  $ {' '.join(cmd)}")
    r = subprocess.run(cmd, capture_output=True, text=True, env=ENV, cwd=ROOT)
    out = r.stdout.strip()
    if r.returncode == 0:
        print(f"  ✅ exit 0")
    else:
        print(f"  ❌ exit {r.returncode}")
    # Show key output lines
    for line in out.split("\n")[-5:]:
        print(f"  {line}")
    return r.returncode

exit_code = 0

print("╔══════════════════════════════════════════╗")
print("║     Hermes Pipeline Demo                 ║")
print("╚══════════════════════════════════════════╝")

# 1. Ecosystem detection
exit_code += run("EVM: detect", [sys.executable, "-m", "orchestrator.cli", "detect", "fixtures/vulnerable"])
exit_code += run("Solana: detect", [sys.executable, "-m", "orchestrator.cli", "detect", "fixtures/solana_vulnerable"])
exit_code += run("Move: detect", [sys.executable, "-m", "orchestrator.cli", "detect", "fixtures/move_vulnerable"])

# 2. Tool inventory
exit_code += run("Available tools", [sys.executable, "-m", "orchestrator.cli", "list-tools"])

# 3. Full pipeline runs
exit_code += run("EVM vulnerable → pipeline", [sys.executable, "-m", "orchestrator.cli", "run", "fixtures/vulnerable", "--output", "/tmp/demo-evm.json"])
exit_code += run("EVM patched → pipeline", [sys.executable, "-m", "orchestrator.cli", "run", "fixtures/patched", "--output", "/tmp/demo-evm-patched.json"])

# 4. Compare findings
for label, path in [("Vulnerable", "/tmp/demo-evm.json"), ("Patched", "/tmp/demo-evm-patched.json")]:
    try:
        data = json.load(open(path))
        findings = data.get("findings", [])
        print(f"\n  {label} fixture: {len(findings)} findings")
        for f in findings[:5]:
            print(f"    🔍 {f.get('title', '??')[:80]}")
    except Exception as e:
        print(f"  {label}: could not read results — {e}")

print(f"\n{'─' * 50}")
if exit_code == 0:
    print("  ✅ Demo complete — all passes")
else:
    print(f"  ⚠️  Demo finished with {exit_code} exit codes")
print(f"{'─' * 50}")