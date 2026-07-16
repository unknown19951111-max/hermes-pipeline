"""
Adapter tests for Aderyn and Echidna.
"""

import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "src"))

from orchestrator.adapters.slither_adapter import SlitherAdapter
from orchestrator.adapters.aderyn_adapter import AderynAdapter
from orchestrator.adapters.medusa_adapter import MedusaAdapter
from orchestrator.adapters.echidna_adapter import EchidnaAdapter


FIXTURE_DIR = Path(__file__).resolve().parent.parent.parent / "fixtures"
VULNERABLE_DIR = str(FIXTURE_DIR / "vulnerable")


def test_slither_adapter_dependency_check():
    """Test that SlitherAdapter detects binary."""
    adapter = SlitherAdapter("/tmp")
    assert adapter.check_dependencies(), "Slither should be available"
    version = adapter.get_version()
    assert version, "Should get a version string"
    print(f"  ✅ Slither v{version}")


def test_slither_adapter_parse_vulnerable():
    """Test Slither output parsing against vulnerable fixture."""
    adapter = SlitherAdapter("/tmp")
    result = adapter.run(VULNERABLE_DIR, "test-slither-vuln", timeout_s=120)
    assert result.success or result.exit_code == 255, \
        f"Slither should run (exit={result.exit_code})"
    assert len(result.normalized_findings) > 0, \
        "Should parse findings from vulnerable fixture"
    
    # Check for reentrancy detector
    has_reentrancy = any(
        "reentrancy" in f.get("tool", {}).get("rule_id", "").lower()
        or "reentrancy" in f.get("title", "").lower()
        for f in result.normalized_findings
    )
    assert has_reentrancy, "Should detect reentrancy in vulnerable fixture"
    print(f"  ✅ Slither: {len(result.normalized_findings)} findings, reentrancy detected")


def test_aderyn_adapter_dependency_check():
    """Test that AderynAdapter detects binary."""
    adapter = AderynAdapter("/tmp")
    assert adapter.check_dependencies(), "Aderyn should be available"
    version = adapter.get_version()
    assert version, "Should get a version string"
    print(f"  ✅ Aderyn v{version}")


def test_aderyn_adapter_parse_vulnerable():
    """Test Aderyn output parsing against vulnerable fixture."""
    adapter = AderynAdapter("/tmp")
    result = adapter.run(VULNERABLE_DIR, "test-aderyn-vuln", timeout_s=60)
    assert result.success, f"Aderyn should run successfully (exit={result.exit_code})"
    assert len(result.normalized_findings) > 0, \
        "Should parse findings from vulnerable fixture"
    
    # Check for reentrancy detector
    has_reentrancy = any(
        "reentrancy" in f.get("tool", {}).get("rule_id", "").lower()
        or "reentrancy" in f.get("title", "").lower()
        for f in result.normalized_findings
    )
    assert has_reentrancy, "Should detect reentrancy in vulnerable fixture"
    print(f"  ✅ Aderyn: {len(result.normalized_findings)} findings, reentrancy detected")


def test_echidna_adapter_dependency_check():
    """Test that EchidnaAdapter detects binary."""
    adapter = EchidnaAdapter("/tmp")
    assert adapter.check_dependencies(), "Echidna should be available"
    version = adapter.get_version()
    assert version, "Should get a version string"
    print(f"  ✅ Echidna v{version}")


def test_medusa_adapter_dependency_check():
    """Test that MedusaAdapter detects binary."""
    adapter = MedusaAdapter("/tmp")
    assert adapter.check_dependencies(), "Medusa should be available"
    version = adapter.get_version()
    assert version, "Should get a version string"
    print(f"  ✅ Medusa v{version}")


def test_schema_normalization():
    """Test that adapter outputs normalize correctly."""
    from orchestrator.normalize import FindingNormalizer
    
    adapter = SlitherAdapter("/tmp")
    result = adapter.run(VULNERABLE_DIR, "test-schema", timeout_s=120)
    
    normalizer = FindingNormalizer()
    valid, quarantined = normalizer.normalize(
        result.normalized_findings,
        job_id="test-job",
        tool_name="slither",
        tool_version=result.tool_version,
        adapter_version=adapter.ADAPTER_VERSION,
    )
    
    assert len(valid) > 0, "Should have valid normalized findings"
    assert len(quarantined) == 0, "Should have no quarantined findings"
    
    # Verify schema compliance
    for f in valid:
        assert "finding_id" in f, "Missing finding_id"
        assert "classification" in f, "Missing classification"
        assert "tool" in f, "Missing tool"
        assert "tool" in f and "name" in f["tool"], "Missing tool.name"
        assert "location" in f, "Missing location"
        assert "provenance" in f, "Missing provenance"
        assert "schema_version" in f, "Missing schema_version"
    
    print(f"  ✅ Schema: {len(valid)} valid, {len(quarantined)} quarantined")


def test_schema_normalization_from_fixture():
    """Test normalizer logic with saved Slither output — no binary required."""
    from orchestrator.normalize import FindingNormalizer

    fixture_path = FIXTURE_DIR / "slither_output_vulnerable.json"
    assert fixture_path.exists(), f"Fixture not found: {fixture_path}"

    with open(fixture_path) as f:
        findings = json.load(f)

    assert len(findings) > 0, "Fixture should contain findings"
    normalizer = FindingNormalizer()

    valid, quarantined = normalizer.normalize(
        findings,
        job_id="fixture-test",
        tool_name="slither",
        tool_version="0.11.4",
        adapter_version="0.1.0",
    )

    assert len(valid) > 0, "Should have valid normalized findings"
    assert len(quarantined) == 0, "Should have no quarantined findings"

    for f in valid:
        assert "finding_id" in f, "Missing finding_id"
        assert "classification" in f, "Missing classification"
        assert "tool" in f, "Missing tool"
        assert "tool" in f and "name" in f["tool"], "Missing tool.name"
        assert "location" in f, "Missing location"
        assert "provenance" in f, "Missing provenance"
        assert "schema_version" in f, "Missing schema_version"

    print(f"  ✅ Fixture-driven schema: {len(valid)} valid, {len(quarantined)} quarantined")


if __name__ == "__main__":
    print("=" * 60)
    print("ADAPTER TESTS")
    print("=" * 60)

    test_slither_adapter_dependency_check()
    test_slither_adapter_parse_vulnerable()
    test_aderyn_adapter_dependency_check()
    test_aderyn_adapter_parse_vulnerable()
    test_echidna_adapter_dependency_check()
    test_medusa_adapter_dependency_check()
    test_schema_normalization()
    test_schema_normalization_from_fixture()

    print(f"\n{'='*60}")
    print("ALL ADAPTER TESTS PASSED")
    print(f"{'='*60}")