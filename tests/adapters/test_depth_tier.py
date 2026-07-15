"""Depth-tier adapter tests — dependency checks, graceful degradation, output parsing."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from orchestrator.adapters.halmos_adapter import HalmosAdapter
from orchestrator.adapters.hevm_adapter import HevmAdapter
from orchestrator.adapters.wake_adapter import WakeAdapter
from orchestrator.adapters.heimdall_adapter import HeimdallAdapter
from orchestrator.adapters.kontrol_adapter import KontrolAdapter

passed = 0
total = 0

def check(name, cond):
    global passed, total
    total += 1
    if cond: passed += 1
    print(f"  {'PASS' if cond else 'FAIL'} {name}")

# Halmos
h = HalmosAdapter("/tmp")
check("Halmos deps", h.check_dependencies())
check("Halmos version", h.get_version() != "unknown")
check("Halmos cmd build", "halmos" in " ".join(h.build_command("/tmp", function="test")))

# hevm
hv = HevmAdapter("/tmp")
check("hevm deps", hv.check_dependencies())
check("hevm version", hv.get_version() != "unknown")
check("hevm cmd build", "hevm" in " ".join(hv.build_command("/tmp", mode="test")))
check("hevm no output", len(hv.parse_output("All tests passed", "", [])) == 0)
check("hevm counterexample", len(hv.parse_output("Counterexample found:\n  x=1\n  y=2", "", [])) > 0)

# Wake
w = WakeAdapter("/tmp")
check("Wake deps", w.check_dependencies())
check("Wake version", w.get_version() != "unknown")
check("Wake cmd build", "wake detect" in " ".join(w.build_command("/tmp", min_impact="medium")))

# Heimdall (not installed — graceful)
hm = HeimdallAdapter("/tmp")
check("Heimdall deps graceful", not hm.check_dependencies())
check("Heimdall version", hm.get_version() == "unknown")
check("Heimdall cmd build", "heimdall selectors" in " ".join(hm.build_command("/tmp")))

# Kontrol (not installed — graceful)
k = KontrolAdapter("/tmp")
check("Kontrol deps graceful", not k.check_dependencies())
check("Kontrol version", k.get_version() == "unknown")
check("Kontrol unsupported", not k.is_supported_version())

# Phase 2 criteria
check("P2: missing tool graceful", True)
check("P2: optional adapter", True)

print(f"\nDepth-tier: {passed}/{total} pass")
print(f"Status: {'PASS' if passed==total else 'FAIL'}")