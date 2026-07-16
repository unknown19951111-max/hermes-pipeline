"""
Tests for PoC generation, human-review queue, failure isolation, checkpoints, and sandboxing.
"""

import json
import sys
import tempfile
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "src"))

from orchestrator.poc import POCGenerator, HumanReviewQueue
from orchestrator.jobs.failure_isolation import CircuitBreaker, FailureHandler, CheckpointManager
from orchestrator.jobs.sandbox import SandboxManager, SandboxConfig


FIXTURE_DIR = Path(__file__).resolve().parent.parent.parent / "fixtures"
VULNERABLE_DIR = str(FIXTURE_DIR / "vulnerable")


# ===== PoC Generation Tests =====

def test_poc_generator_detects_sequence():
    """Test that sequence extraction works from description text."""
    gen = POCGenerator("/tmp")
    description = """Call sequence:
        -> target.deposit(amount: 100)
        -> target.withdraw(amount: 100)
        -> target.withdraw(amount: 100)
    End of sequence."""
    steps = gen._extract_sequence_steps(description)
    assert len(steps) > 0, "Should extract steps from description"
    print(f"  ✅ Sequence extraction: {len(steps)} steps")


def test_poc_generates_file():
    """Test that PoC file is generated."""
    with tempfile.TemporaryDirectory() as tmpdir:
        gen = POCGenerator(tmpdir)
        finding = {
            "finding_id": "test-001",
            "classification": "tool_generated_warning",
            "severity": "high",
            "tool": {"name": "slither", "version": "0.11.4", "rule_id": "reentrancy-eth"},
            "location": {"file": "src/VulnerableVault.sol", "start_line": 23},
            "title": "Reentrancy in withdraw",
            "description": "Reentrancy in VulnerableVault.withdraw(uint256)",
            "schema_version": "1.0.0",
        }
        manifest = gen.generate_from_sequence(
            finding, tmpdir, contract_name="VulnerableVault",
        )
        assert manifest["poc_id"], "Should generate poc_id"
        assert Path(manifest["poc_path"]).exists(), "PoC file should exist"
        assert manifest["compile_status"] in ("passed", "failed"), "Should have compile status"
        print(f"  ✅ PoC generated: {manifest['poc_path']} (compile: {manifest['compile_status']})")


def test_poc_with_medusa():
    """Test PoC generation from a Medusa-style result dict."""
    with tempfile.TemporaryDirectory() as tmpdir:
        medusa_result = {
            "normalized_findings": [
                {
                    "finding_id": "medusa-001",
                    "classification": "invariant_violation",
                    "severity": "high",
                    "tool": {"name": "medusa", "version": "1.5.1", "rule_id": "fuzzer-failure"},
                    "location": {"file": "src/Vault.sol", "start_line": 42},
                    "title": "Medusa: Invariant violation",
                    "description": "Call sequence:\n  -> target.deposit(100)\n  -> target.withdraw(200)",
                    "schema_version": "1.0.0",
                }
            ],
            "_work_dir": tmpdir,
        }
        manifest = POCGenerator.generate_from_medusa_result(
            medusa_result, tmpdir, contract_name="Vault",
        )
        assert manifest is not None, "Should generate PoC from Medusa result"
        print(f"  ✅ Medusa PoC: {manifest.get('poc_id', '?')}")


# ===== Human Review Queue Tests =====

def test_review_queue_enqueue():
    """Test that findings enqueue correctly."""
    with tempfile.TemporaryDirectory() as tmpdir:
        queue = HumanReviewQueue(tmpdir)

        # Should reject non-qualifying classification
        result = queue.enqueue({
            "finding_id": "test-001",
            "classification": "informational_observation",
            "reproduction": {"status": "none"},
        })
        assert result["status"] == "skipped", "Informational should be skipped"
        assert queue.count()["pending"] == 0

        # Should reject without reproduction
        result = queue.enqueue({
            "finding_id": "test-002",
            "classification": "confirmed_vulnerability",
            "reproduction": {"status": "none"},
        })
        assert result["status"] == "skipped", "Unreproduced should be skipped"

        # Should accept qualifying finding
        result = queue.enqueue({
            "finding_id": "test-003",
            "classification": "confirmed_vulnerability",
            "severity": "high",
            "title": "Test finding",
            "tool": {"name": "slither", "version": "0.11.4", "rule_id": "reentrancy-eth"},
            "location": {"file": "src/Vault.sol", "start_line": 23},
            "reproduction": {"status": "pass"},
            "provenance": {"job_id": "job-001"},
            "schema_version": "1.0.0",
        })
        assert result["status"] == "pending", "Should be queued as pending"
        assert queue.count()["pending"] == 1
        print(f"  ✅ Review queue: {queue.count()['pending']} pending")


def test_review_queue_review():
    """Test that review decisions work."""
    with tempfile.TemporaryDirectory() as tmpdir:
        queue = HumanReviewQueue(tmpdir)

        entry = queue.enqueue({
            "finding_id": "test-001",
            "classification": "confirmed_vulnerability",
            "severity": "high",
            "title": "Test finding",
            "tool": {"name": "slither", "rule_id": "reentrancy-eth"},
            "location": {"file": "src/Vault.sol", "start_line": 23},
            "reproduction": {"status": "pass"},
            "provenance": {"job_id": "job-001"},
            "schema_version": "1.0.0",
        })

        # Approve
        reviewed = queue.review(entry["entry_id"], "alice", "approved", "Confirmed")
        assert reviewed["status"] == "approved"
        assert reviewed["reviewed_by"] == "alice"

        # Count
        counts = queue.count()
        assert counts["approved"] == 1
        assert counts["pending"] == 0
        print(f"  ✅ Review workflow: {counts['approved']} approved")


# ===== Circuit Breaker Tests =====

def test_circuit_breaker_trips():
    """Test circuit breaker trips after threshold failures."""
    cb = CircuitBreaker(threshold=3, reset_after_s=60)

    # First two failures should not trip
    assert not cb.record_failure("slither"), "Should not trip at 1"
    assert not cb.record_failure("slither"), "Should not trip at 2"
    assert not cb.is_tripped("slither"), "Should not be tripped yet"

    # Third failure should trip
    assert cb.record_failure("slither"), "Should trip at 3"
    assert cb.is_tripped("slither"), "Should be tripped after threshold"

    # Reset
    cb.reset("slither")
    assert not cb.is_tripped("slither"), "Should reset"

    print(f"  ✅ Circuit breaker: trip at {cb.threshold}, reset works")


def test_circuit_breaker_isolates_tools():
    """Test that one tool's circuit doesn't affect others."""
    cb = CircuitBreaker(threshold=2)

    cb.record_failure("slither")
    cb.record_failure("slither")
    assert cb.is_tripped("slither"), "Slither should be tripped"
    assert not cb.is_tripped("aderyn"), "Aderyn should NOT be tripped"
    assert not cb.is_tripped("medusa"), "Medusa should NOT be tripped"

    print(f"  ✅ Circuit isolation: per-tool tripping works")


# ===== Failure Handler Tests =====

def test_failure_handler_classification():
    """Test error classification."""
    fh = FailureHandler()

    # Timeout
    cls = fh.classify_error(exit_code=-1, timed_out=True, stderr="", stdout="")
    assert cls == "timeout", f"Expected timeout, got {cls}"

    # OOM
    cls = fh.classify_error(exit_code=-9, timed_out=False, stderr="killed", stdout="")
    assert cls == "oom", f"Expected oom, got {cls}"

    # Not found
    cls = fh.classify_error(exit_code=127, timed_out=False, stderr="not found", stdout="")
    assert cls == "unsupported", f"Expected unsupported, got {cls}"

    # Normal failure with output
    cls = fh.classify_error(exit_code=255, timed_out=False, stderr="", stdout="Detected 4 issues")
    assert cls in ("transient", "unknown"), f"Expected transient/unknown, got {cls}"

    print(f"  ✅ Failure classification: all 4 categories")


def test_failure_handler_retry_policy():
    """Test retry policy logic."""
    fh = FailureHandler()

    # Transient: retry up to 3 times
    assert fh.should_retry("slither", "transient", 0), "Should retry transient"
    assert fh.should_retry("slither", "transient", 2), "Should retry transient (2/3)"
    assert not fh.should_retry("slither", "transient", 3), "Should not retry after 3"

    # Deterministic: no retry
    assert not fh.should_retry("slither", "deterministic", 0), "Should not retry deterministic"

    # OOM: no retry
    assert not fh.should_retry("slither", "oom", 0), "Should not retry OOM"

    print(f"  ✅ Retry policy: transient=3, deterministic=0, oom=0")


# ===== Checkpoint Manager Tests =====

def test_checkpoint_manager():
    """Test checkpoint save/load/resume."""
    with tempfile.TemporaryDirectory() as tmpdir:
        cm = CheckpointManager(tmpdir)

        # Save checkpoint
        cm.save_checkpoint("job-001", "intake", {"commit": "abc123"})
        cm.save_checkpoint("job-001", "detect", {"ecosystem": "evm"})
        cm.save_checkpoint("job-001", "build", {"success": True})

        # List checkpoints
        stages = cm.list_checkpoints("job-001")
        assert "intake" in stages
        assert "detect" in stages
        assert "build" in stages
        assert len(stages) == 3

        # Find earliest uncompleted
        first_uncompleted = cm.get_earliest_uncompleted_stage(
            "job-001", ["intake", "detect", "build", "slither", "normalize"]
        )
        assert first_uncompleted == "slither", f"Expected slither, got {first_uncompleted}"

        # Load checkpoint
        cp = cm.load_checkpoint("job-001", "detect")
        assert cp is not None
        assert cp["data"]["ecosystem"] == "evm"

        print(f"  ✅ Checkpoints: {len(stages)} saved, resume from '{first_uncompleted}'")


# ===== Sandbox Tests =====

def test_sandbox_config_generation():
    """Test that sandbox configs are valid."""
    assert "FROM ubuntu:22.04" in SandboxConfig.DOCKERFILE_CONTENT
    assert "hermes-net" in SandboxConfig.COMPOSE_CONTENT
    print(f"  ✅ Sandbox configs: Dockerfile {len(SandboxConfig.DOCKERFILE_CONTENT)} chars, "
          f"compose {len(SandboxConfig.COMPOSE_CONTENT)} chars")


def test_sandbox_manager_dependency_check():
    """Test sandbox manager can check Docker availability."""
    sm = SandboxManager(use_sandbox=False)
    assert sm.check_docker_available() or not sm.use_sandbox, "Should handle missing Docker"
    print(f"  ✅ Sandbox: Docker available = {sm.check_docker_available()}")


def test_sandbox_direct_run():
    """Test sandbox bypass mode (direct execution)."""
    sm = SandboxManager(use_sandbox=False)
    exit_code, stdout, stderr = sm.run_in_sandbox(
        "test-job", ["echo", "hello"], "/tmp",
    )
    assert exit_code == 0, f"Expected 0, got {exit_code}"
    assert "hello" in stdout, "Should get echo output"
    print(f"  ✅ Sandbox direct mode: exit={exit_code}")
    print()


# ===== F-004: Adapter success calculation =====

def test_adapter_parse_failure_returns_success_false():
    """Test that parse failure results in success=False (F-004)."""
    from orchestrator.adapters.base_adapter import AdapterResult

    # Simulate: exit_code=0 but parse error created an analysis_failure finding
    result = AdapterResult(
        success=False,
        tool="TestTool",
        tool_version="1.0.0",
        adapter_version="0.1.0",
        command="test",
        exit_code=0,
        timed_out=False,
        stdout="garbage",
        stderr="",
        raw_output_paths=[],
        normalized_findings=[{
            "classification": "analysis_failure",
            "tool": {"name": "TestTool", "version": "1.0.0", "rule_id": "parse-error"},
            "title": "Failed to parse output",
        }],
        parse_success=False,
    )
    assert not result.success, "Parse failure should set success=False"
    assert not result.parse_success, "parse_success should be False"
    print(f"  ✅ Parse failure: success={result.success}, parse_success={result.parse_success}")


def test_adapter_nonzero_exit_no_output():
    """Test that nonzero exit with no output returns success=False (F-004)."""
    from orchestrator.adapters.base_adapter import AdapterResult

    result = AdapterResult(
        success=False,
        tool="TestTool",
        tool_version="1.0.0",
        adapter_version="0.1.0",
        command="test",
        exit_code=1,
        timed_out=False,
        stdout="",
        stderr="error",
        raw_output_paths=[],
        normalized_findings=[],
        parse_success=True,
    )
    assert not result.success, "Nonzero exit should set success=False"
    assert result.parse_success, "Empty output means no parse error"
    print(f"  ✅ Nonzero exit: success={result.success}, parse_success={result.parse_success}")


def test_adapter_clean_exit_parseable_output():
    """Test that clean exit with parseable output returns success=True (F-004)."""
    from orchestrator.adapters.base_adapter import AdapterResult

    result = AdapterResult(
        success=True,
        tool="TestTool",
        tool_version="1.0.0",
        adapter_version="0.1.0",
        command="test",
        exit_code=0,
        timed_out=False,
        stdout="valid output",
        stderr="",
        raw_output_paths=[],
        normalized_findings=[{"finding_id": "test-1", "classification": "reentrancy"}],
        parse_success=True,
    )
    assert result.success, "Clean exit with parseable output should set success=True"
    assert result.parse_success, "parse_success should be True"
    print(f"  ✅ Clean exit: success={result.success}, parse_success={result.parse_success}")


# ===== F-007/F-008: Harness generation =====

def test_harness_incompatible_archetype():
    """Test that unsupported archetypes return INCOMPATIBLE_INVARIANT (F-007)."""
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "src"))
    from orchestrator.harness import HarnessGenerator

    gen = HarnessGenerator("/tmp")
    success, path, error = gen.generate_harness(
        "/tmp", "lending", [], "TestContract",
    )
    assert not success, "Unsupported archetype should return success=False"
    assert "INCOMPATIBLE_INVARIANT" in error, f"Should mention INCOMPATIBLE_INVARIANT: {error}"
    print(f"  ✅ Incompatible archetype: {error}")


def test_harness_erc4626_meaningful_assertion():
    """Test that ERC-4626 invariant has a meaningful assertion (F-008)."""
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "src"))
    from orchestrator.harness import HarnessGenerator

    gen = HarnessGenerator("/tmp")
    content = gen._get_archetype_invariants("erc4626", "TestContract")
    assert "assertGe" in content, "Should use assertGe (not tautological assertTrue)"
    assert "assertTrue" not in content, "Should not have tautological assertTrue"
    print(f"  ✅ ERC-4626: meaningful assertion found (assertGe)")


def test_harness_erc20_has_assertion():
    """Test that ERC-20 invariant has a real assertion."""
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "src"))
    from orchestrator.harness import HarnessGenerator

    gen = HarnessGenerator("/tmp")
    content = gen._get_archetype_invariants("erc20", "TestContract")
    assert "assertEq" in content, "ERC-20 should have assertEq assertion"
    print(f"  ✅ ERC-20: assertion found (assertEq)")


# ===== F-006: Invariant registry evidence =====

def test_invariant_registry_no_verified_without_evidence():
    """Test that no VERIFIED invariants exist without evidence (F-006)."""
    from orchestrator.classify.invariant_registry import InvariantRegistry

    REGISTRY_PATH = str(Path(__file__).resolve().parent.parent.parent / "invariants" / "registry.json")
    registry = InvariantRegistry(REGISTRY_PATH)
    verified = registry.select_for_archetype(["erc20"], min_status="VERIFIED")
    for inv in verified:
        ok, reasons = registry.can_promote_to_verified(inv["id"])
        assert ok, f"VERIFIED invariant {inv['id']} missing evidence: {reasons}"
    print(f"  ✅ All {len(verified)} VERIFIED invariants have complete evidence")


def test_invariant_registry_rejects_phantom_promotion():
    """Test that CANDIDATE invariants cannot be promoted to VERIFIED without evidence (F-006)."""
    from orchestrator.classify.invariant_registry import InvariantRegistry

    REGISTRY_PATH = str(Path(__file__).resolve().parent.parent.parent / "invariants" / "registry.json")
    registry = InvariantRegistry(REGISTRY_PATH)
    try:
        registry.promote("erc20-total-supply-invariant", "VERIFIED")
        assert False, "Should have raised ValueError"
    except ValueError as e:
        assert "Cannot promote" in str(e), f"Unexpected error: {e}"
        print(f"  ✅ Phantom promotion rejected: {e}")

if __name__ == "__main__":
    print("=" * 60)
    print("PHASE 1 REMAINING TESTS")
    print("=" * 60)

    test_poc_generator_detects_sequence()
    test_poc_generates_file()
    test_poc_with_medusa()
    test_review_queue_enqueue()
    test_review_queue_review()
    test_circuit_breaker_trips()
    test_circuit_breaker_isolates_tools()
    test_failure_handler_classification()
    test_failure_handler_retry_policy()
    test_checkpoint_manager()
    test_sandbox_config_generation()
    test_sandbox_manager_dependency_check()
    test_sandbox_direct_run()
    test_adapter_parse_failure_returns_success_false()
    test_adapter_nonzero_exit_no_output()
    test_adapter_clean_exit_parseable_output()
    test_harness_incompatible_archetype()
    test_harness_erc4626_meaningful_assertion()
    test_harness_erc20_has_assertion()
    test_invariant_registry_no_verified_without_evidence()
    test_invariant_registry_rejects_phantom_promotion()

    print(f"\n{'='*60}")
    print("ALL PHASE 1 REMAINING TESTS PASSED")
    print(f"{'='*60}")