"""Non-EVM (Phase 3) adapter tests — Solana, Move ecosystem detection, graceful degradation."""
import sys, os, tempfile
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from orchestrator.detect import FrameworkDetector
from orchestrator.adapters.solana_adapter import AnchorAdapter, SolanaCLIAdapter, TridentAdapter
from orchestrator.adapters.move_adapter import AptosAdapter, SuiAdapter, MoveProverAdapter

passed = 0
total = 0

def check(name, cond):
    global passed, total
    total += 1
    if cond: passed += 1
    print(f"  {'PASS' if cond else 'FAIL'} {name}")

# Ecosystem detection — Solana Anchor
with tempfile.TemporaryDirectory() as d:
    open(f"{d}/Anchor.toml", "w").close()
    df = FrameworkDetector(d)
    dr = df.detect_framework()
    check("Solana Anchor detect", dr.framework == "anchor" and dr.ecosystem == "solana")
    dr2 = df.detect_ecosystem()
    check("Solana Anchor ecosystem", dr2.ecosystem == "solana")

# Ecosystem detection — Move Aptos
with tempfile.TemporaryDirectory() as d:
    open(f"{d}/Aptos.toml", "w").close()
    df = FrameworkDetector(d)
    dr = df.detect_framework()
    check("Move Aptos detect", dr.framework == "aptos" and dr.ecosystem == "move")
    dr2 = df.detect_ecosystem()
    check("Move Aptos ecosystem", dr2.ecosystem == "move")

# Ecosystem detection — Move Sui
with tempfile.TemporaryDirectory() as d:
    open(f"{d}/sui.yaml", "w").close()
    df = FrameworkDetector(d)
    dr = df.detect_framework()
    check("Move Sui detect", dr.framework == "sui" and dr.ecosystem == "move")

# Ecosystem detection — .move fallback
with tempfile.TemporaryDirectory() as d:
    open(f"{d}/MyModule.move", "w").close()
    df = FrameworkDetector(d)
    dr = df.detect_framework()
    check("Move no framework fallback", dr.framework == "unknown" and dr.ecosystem == "move")
    check("Move fallback confidence", dr.confidence == 0.3)

# Ecosystem detection — Solana Cargo.toml
with tempfile.TemporaryDirectory() as d:
    open(f"{d}/Cargo.toml", "w").write("[dependencies]\nsolana-program = \"1.18\"")
    open(f"{d}/src", "w").close()  # make src exist
    df = FrameworkDetector(d)
    dr = df.detect_framework()
    check("Solana native detect", dr.framework == "solana_native" and dr.ecosystem == "solana")

# Solana adapters — graceful degradation for unimplemented tools
a = AnchorAdapter("/tmp")
check("Anchor deps", not a.check_dependencies())  # anchor CLI not installed
check("Anchor version", a.get_version() == "")
check("Anchor cmd build", "anchor build" in " ".join(a.build_command("/tmp")))

s = SolanaCLIAdapter("/tmp")
check("Solana CLI deps", s.check_dependencies())  # solana CLI IS installed
check("Solana CLI version", s.get_version() != "")
check("Solana CLI cmd", "solana program" in " ".join(s.build_command("/tmp")))
check("Solana no findings", len(s.parse_output("", "", [])) == 0)

t = TridentAdapter("/tmp")
check("Trident deps", not t.check_dependencies())  # trident not installed
check("Trident version", t.get_version() == "unknown")

# Move adapters — graceful degradation
a2 = AptosAdapter("/tmp")
check("Aptos deps", not a2.check_dependencies())
check("Aptos cmd build", "aptos move compile" in " ".join(a2.build_command("/tmp")))
check("Aptos output parse", len(a2.parse_output("error: compilation failed\nwarning: unused import", "", [])) == 2)

s2 = SuiAdapter("/tmp")
check("Sui deps", not s2.check_dependencies())
check("Sui cmd build", "sui move build" in " ".join(s2.build_command("/tmp")))

mp = MoveProverAdapter("/tmp")
check("MoveProver deps", not mp.check_dependencies())
check("MoveProver version", mp.get_version() == "")
check("MoveProver cmd", "move prover" in " ".join(mp.build_command("/tmp")))

print(f"\nNon-EVM: {passed}/{total} pass")
print(f"Status: {'PASS' if passed==total else 'FAIL'}")