"""
CI importability test — ensures all critical pipeline modules can be imported.

This prevents the F-005 false-green scenario where a missing dependency
(such as jsonschema) causes test files to silently fail to load.
"""
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "src"))


def test_import_jsonschema():
    """jsonschema must be importable — required by FindingNormalizer."""
    import jsonschema
    import importlib.metadata
    ver = importlib.metadata.version("jsonschema")
    assert ver, "jsonschema must have a version"


def test_import_normalizer():
    """orchestrator.normalize must be importable — required by all pipeline stages."""
    from orchestrator.normalize import FindingNormalizer, Deduplicator
    assert FindingNormalizer is not None
    assert Deduplicator is not None


def test_import_intake():
    """orchestrator.intake must be importable."""
    from orchestrator.intake import RepositoryManager, IntakeManifest, IntakeError
    assert RepositoryManager is not None
    assert IntakeManifest is not None


def test_import_build():
    """orchestrator.build must be importable."""
    from orchestrator.build import BuildExecutor, BuildError
    assert BuildExecutor is not None


def test_import_adapters():
    """All tool adapters must be importable."""
    from orchestrator.adapters.slither_adapter import SlitherAdapter
    from orchestrator.adapters.aderyn_adapter import AderynAdapter
    from orchestrator.adapters.medusa_adapter import MedusaAdapter
    from orchestrator.adapters.echidna_adapter import EchidnaAdapter
    assert SlitherAdapter is not None
    assert AderynAdapter is not None
    assert MedusaAdapter is not None
    assert EchidnaAdapter is not None


def test_import_jobs():
    """orchestrator.jobs must be importable."""
    from orchestrator.jobs import ArtifactStore, JobState
    from orchestrator.jobs.sandbox import SandboxManager, SandboxConfig
    from orchestrator.jobs.failure_isolation import CircuitBreaker, FailureHandler, CheckpointManager
    assert ArtifactStore is not None
    assert JobState is not None
    assert SandboxManager is not None


def test_import_poc():
    """orchestrator.poc must be importable."""
    from orchestrator.poc import POCGenerator, HumanReviewQueue
    assert POCGenerator is not None
    assert HumanReviewQueue is not None


def test_import_harness():
    """orchestrator.harness must be importable."""
    from orchestrator.harness import HarnessGenerator
    assert HarnessGenerator is not None


def test_import_classify():
    """orchestrator.classify must be importable."""
    from orchestrator.classify.invariant_registry import InvariantRegistry
    assert InvariantRegistry is not None


def test_import_eligibility():
    """orchestrator.eligibility must be importable."""
    from orchestrator.eligibility import EligibilitySnapshot, EligibilityGate
    assert EligibilitySnapshot is not None
    assert EligibilityGate is not None


def test_import_detect():
    """orchestrator.detect must be importable."""
    from orchestrator.detect import FrameworkDetector
    assert FrameworkDetector is not None


def test_import_schema():
    """JSON Schema files must exist and be loadable."""
    import json
    schemas = ["finding.json", "intake-manifest.json", "execution-manifest.json", "report.json"]
    base = Path(__file__).resolve().parent.parent.parent / "schemas"
    for name in schemas:
        path = base / name
        assert path.exists(), f"Schema file missing: {path}"
        data = json.loads(path.read_text())
        assert "$schema" in data, f"Schema {name} missing $schema field"
        assert "properties" in data, f"Schema {name} missing properties"
    print(f"  ✅ All {len(schemas)} schemas valid")


if __name__ == "__main__":
    print("=" * 60)
    print("CI IMPORTABILITY TESTS")
    print("=" * 60)
    test_import_jsonschema()
    print("  ✅ jsonschema importable")
    test_import_normalizer()
    print("  ✅ normalizer importable")
    test_import_intake()
    print("  ✅ intake importable")
    test_import_build()
    print("  ✅ build importable")
    test_import_adapters()
    print("  ✅ adapters importable")
    test_import_jobs()
    print("  ✅ jobs importable")
    test_import_poc()
    print("  ✅ poc importable")
    test_import_harness()
    print("  ✅ harness importable")
    test_import_classify()
    print("  ✅ classify importable")
    test_import_detect()
    print("  ✅ detect importable")
    test_import_schema()
    print("  ✅ schemas valid")
    print(f"\n{'='*60}")
    print("ALL CI IMPORTABILITY TESTS PASSED")
    print(f"{'='*60}")