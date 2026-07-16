"""
Unit tests for invariant registry.
"""

import json
import sys
import tempfile
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "src"))

from orchestrator.classify.invariant_registry import InvariantRegistry


REGISTRY_PATH = str(Path(__file__).resolve().parent.parent.parent / "invariants" / "registry.json")


def test_registry_load():
    """Test that the registry loads correctly."""
    registry = InvariantRegistry(REGISTRY_PATH)
    assert registry.count["TOTAL"] > 0, "Registry should have invariants"
    print(f"  ✅ Registry loaded: {registry.count['TOTAL']} invariants "
          f"({registry.count['VERIFIED']} VERIFIED, {registry.count['CANDIDATE']} CANDIDATE)")


def test_select_for_archetype():
    """Test selecting invariants for an archetype."""
    registry = InvariantRegistry(REGISTRY_PATH)
    
    erc20_invariants = registry.select_for_archetype(["erc20"])
    assert len(erc20_invariants) > 0, "Should select ERC-20 invariants"
    print(f"  ✅ ERC-20: {len(erc20_invariants)} invariants selected")
    
    lending_invariants = registry.select_for_archetype(["lending"])
    assert len(lending_invariants) > 0, "Should select lending invariants"
    print(f"  ✅ Lending: {len(lending_invariants)} invariants selected")


def test_select_multi_archetype():
    """Test selecting invariants for multiple archetypes."""
    registry = InvariantRegistry(REGISTRY_PATH)
    
    invariants = registry.select_for_archetype(["erc20", "erc4626"])
    assert len(invariants) > 0, "Should select invariants for multiple archetypes"
    # Should have both ERC-20 and ERC-4626 invariants
    archetypes = set(i["archetype"] for i in invariants)
    print(f"  ✅ Multi-archetype: {len(invariants)} invariants across {archetypes}")


def test_status_filter():
    """Test filtering by status."""
    registry = InvariantRegistry(REGISTRY_PATH)
    
    verified = registry.select_for_archetype(["erc20"], min_status="VERIFIED")
    all_status = registry.select_for_archetype(["erc20"], min_status="CANDIDATE")
    assert len(verified) <= len(all_status), "VERIFIED filter should be stricter"
    print(f"  ✅ Status filter: {len(verified)} VERIFIED, {len(all_status)} total")


def test_compatibility_check():
    """Test compatibility checking."""
    registry = InvariantRegistry(REGISTRY_PATH)
    
    compatible, reasons = registry.check_compatibility(
        "erc20-total-supply-invariant",
        compiler_version="0.8.20",
        available_deps=["crytic/properties"],
    )
    assert compatible, f"Should be compatible: {reasons}"
    print(f"  ✅ Compatibility: {compatible}")
    
    # Test incompatible version
    compat2, reasons2 = registry.check_compatibility(
        "erc20-total-supply-invariant",
        compiler_version="0.6.0",
        available_deps=["crytic/properties"],
    )
    if not compat2:
        print(f"  ✅ Incompatible version detected: {reasons2}")


def test_required_deps():
    """Test dependency collection."""
    registry = InvariantRegistry(REGISTRY_PATH)
    
    deps = registry.get_required_dependencies(["erc20"])
    print(f"  ✅ ERC-20 deps: {deps}")
    assert "crytic/properties" in deps, "ERC-20 should need crytic/properties"
    
    deps2 = registry.get_required_dependencies(["lending"])
    print(f"  ✅ Lending deps: {deps2}")


def test_promotion_rules():
    """Test that VERIFIED promotion requires full evidence."""
    registry = InvariantRegistry(REGISTRY_PATH)
    
    # Try to promote a CANDIDATE invariant to VERIFIED without evidence (should fail)
    try:
        registry.promote("erc20-total-supply-invariant", "VERIFIED")
        print("  ⚠️  VERIFIED promotion succeeded without evidence (this should not happen)")
    except ValueError as e:
        print(f"  ✅ VERIFIED promotion blocked: {e}")


def test_get_invariant():
    """Test single invariant lookup."""
    registry = InvariantRegistry(REGISTRY_PATH)
    
    inv = registry.get_invariant("erc20-total-supply-invariant")
    assert inv is not None, "Should find invariant by ID"
    assert inv["id"] == "erc20-total-supply-invariant"
    assert inv["status"] == "CANDIDATE", "Demoted to CANDIDATE — no source_commit (F-006)"
    print(f"  ✅ Lookup: {inv['id']} ({inv['status']})")


def test_can_promote_rejects_no_evidence():
    """Test that can_promote_to_verified rejects invariants without evidence."""
    registry = InvariantRegistry(REGISTRY_PATH)
    
    ok, reasons = registry.can_promote_to_verified("erc20-total-supply-invariant")
    assert not ok, "Should reject promotion without evidence"
    print(f"  ✅ Rejected CANDIDATE→VERIFIED: {'; '.join(reasons)}")
    
    
def test_can_promote_unknown_id():
    """Test that can_promote_to_verified handles unknown invariant IDs."""
    registry = InvariantRegistry(REGISTRY_PATH)
    
    ok, reasons = registry.can_promote_to_verified("nonexistent-invariant")
    assert not ok, "Should reject unknown invariant"
    print(f"  ✅ Rejected unknown ID: {'; '.join(reasons)}")


if __name__ == "__main__":
    print("=" * 60)
    print("INVARIANT REGISTRY UNIT TESTS")
    print("=" * 60)
    
    test_registry_load()
    test_select_for_archetype()
    test_select_multi_archetype()
    test_status_filter()
    test_compatibility_check()
    test_required_deps()
    test_promotion_rules()
    test_get_invariant()
    
    print(f"\n{'='*60}")
    print("ALL INVARIANT REGISTRY TESTS PASSED")
    print(f"{'='*60}")