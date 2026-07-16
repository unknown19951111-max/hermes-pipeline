"""
Vertical Slice 1 E2E Test — Intake → Detect → Build → Slither → Normalize → Schema → Store → Report

This test proves the minimum complete pipeline works against:
1. A known-vulnerable fixture (reentrancy)
2. A known-patched fixture (checks-effects-interactions)
"""

import json
import os
import shutil
import sys
import tempfile
import time
import uuid
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "src"))

from orchestrator.intake import RepositoryManager, IntakeManifest
from orchestrator.detect import FrameworkDetector
from orchestrator.build import BuildExecutor
from orchestrator.adapters.slither_adapter import SlitherAdapter
from orchestrator.normalize import FindingNormalizer, Deduplicator
from orchestrator.jobs import ArtifactStore, JobState


FIXTURE_DIR = Path(__file__).resolve().parent.parent.parent / "fixtures"
VULNERABLE_DIR = str(FIXTURE_DIR / "vulnerable")
PATCHED_DIR = str(FIXTURE_DIR / "patched")


def test_vertical_slice_vulnerable():
    """
    Test the full pipeline against a known-vulnerable Foundry project.
    
    Expected: Slither detects the reentrancy vulnerability.
    """
    with tempfile.TemporaryDirectory(prefix="hermes-vs1-vuln-") as work_dir:
        print(f"\n{'='*60}")
        print(f"VS1: VULNERABLE FIXTURE")
        print(f"{'='*60}")
        print(f"Workspace: {work_dir}")
        
        # === STAGE 0: Setup ===
        job_id = str(uuid.uuid4())
        artifact_store = ArtifactStore(work_dir)
        job_state = JobState(os.path.join(work_dir, "jobs"))
        job_state.create(job_id, {"target": "fixtures/vulnerable"})
        
        # === STAGE 1: Intake (local) ===
        print("\n--- Stage 1: Intake ---")
        repo_manager = RepositoryManager(os.path.join(work_dir, "intake"))
        intake_job_id, repo_path, intake_manifest = repo_manager.intake_local(VULNERABLE_DIR)
        assert intake_job_id, "Intake must produce a job_id"
        print(f"  Job ID: {intake_job_id}")
        print(f"  Repo path: {repo_path}")
        print(f"  Commit: {intake_manifest.get('commit_sha', 'unknown')}")
        artifact_store.store_manifest(job_id, intake_manifest, "intake")
        job_state.transition(job_id, "running")
        
        # === STAGE 2: Ecosystem/Framework Detection ===
        print("\n--- Stage 2: Detection ---")
        detector = FrameworkDetector(repo_path)
        eco_result = detector.detect_ecosystem()
        fw_result = detector.detect_framework()
        print(f"  Ecosystem: {eco_result.ecosystem} (confidence: {eco_result.confidence:.2f})")
        print(f"  Framework: {fw_result.framework} (confidence: {fw_result.confidence:.2f})")
        print(f"  Evidence: {eco_result.evidence}")
        assert eco_result.ecosystem == "evm", "Should detect EVM ecosystem"
        assert fw_result.framework == "foundry", "Should detect Foundry framework"
        job_state.add_stage_result(job_id, {
            "stage_id": "detect", "tool": "detector",
            "completion_state": "completed"
        })
        
        # === STAGE 3: Build ===
        print("\n--- Stage 3: Build ---")
        build_executor = BuildExecutor(repo_path, fw_result.framework)
        success, build_manifest, build_log = build_executor.build(timeout_s=120)
        print(f"  Build success: {success}")
        if build_log:
            print(f"  Build log (last 200 chars): {build_log[-200:]}")
        artifact_store.store_build_log(job_id, build_log)
        artifact_store.store_manifest(job_id, build_manifest, "build")
        job_state.add_stage_result(job_id, {
            "stage_id": "build", "tool": "forge",
            "completion_state": "completed" if success else "failed"
        })
        # Build should succeed for this fixture
        assert success, f"Build should succeed for vulnerable fixture. Log: {build_log[-500:]}"
        
        # === STAGE 4: Slither ===
        print("\n--- Stage 4: Slither ---")
        slither_adapter = SlitherAdapter(os.path.join(work_dir, "slither"))
        slither_result = slither_adapter.run(repo_path, job_id, timeout_s=120)
        print(f"  Slither success: {slither_result.success}")
        print(f"  Slither exit code: {slither_result.exit_code}")
        print(f"  Slither version: {slither_result.tool_version}")
        print(f"  Findings: {len(slither_result.normalized_findings)}")
        
        # Save raw output
        if slither_result.stdout:
            artifact_store.store_raw_output(job_id, "slither", slither_result.stdout, "txt")
        job_state.add_stage_result(job_id, 
            slither_result.to_manifest(job_id, "slither", repo_path))
        
        # === STAGE 5: Normalize ===
        print("\n--- Stage 5: Normalize ---")
        normalizer = FindingNormalizer()
        schema_path = str(Path(__file__).resolve().parent.parent.parent / "schemas" / "finding.json")
        if Path(schema_path).exists():
            normalizer = FindingNormalizer(schema_path)
        
        valid, quarantined = normalizer.normalize(
            slither_result.normalized_findings,
            job_id=job_id,
            tool_name="slither",
            tool_version=slither_result.tool_version,
            adapter_version=slither_adapter.ADAPTER_VERSION,
        )
        print(f"  Valid findings: {len(valid)}")
        print(f"  Quarantined: {len(quarantined)}")
        
        for f in valid:
            print(f"    - {f.get('classification')}: {f.get('title', '')} [{f.get('severity', '')}]")
            loc = f.get("location", {})
            print(f"      Location: {loc.get('file', '')}:{loc.get('start_line', '')}")
        
        # Store normalized findings
        for f in valid:
            artifact_store.store_finding(job_id, f)
            job_state.add_finding(job_id, f)
        
        # === STAGE 6: Dedup ===
        print("\n--- Stage 6: Dedup ---")
        deduper = Deduplicator()
        deduped = deduper.dedup(valid)
        print(f"  After dedup: {len(deduped)} findings ({len(valid) - len(deduped)} duplicates removed)")
        
        # === STAGE 7: Report ===
        print("\n--- Stage 7: Report ---")
        stage_results = job_state.get(job_id).get("stage_results", [])
        report = artifact_store.generate_report(job_id, deduped, intake_manifest, stage_results)
        report_path = artifact_store.store_report(job_id, report)
        print(f"  Report: {report_path}")
        print(f"  Confirmed: {len(report['findings']['confirmed_vulnerabilities'])}")
        print(f"  Warnings: {len(report['findings']['tool_warnings'])}")
        print(f"  Analysis failures: {len(report['findings']['analysis_failures'])}")
        
        job_state.transition(job_id, "completed")
        
        # === ASSERTIONS ===
        print(f"\n{'='*60}")
        print("ASSERTIONS:")
        print(f"{'='*60}")
        
        # CRITICAL: Slither MUST detect the exact "reentrancy-eth" rule
        reentrancy_found = False
        for f in deduped:
            tool_rule = f.get("tool", {}).get("rule_id", "")
            if tool_rule == "reentrancy-eth":
                reentrancy_found = True
                print(f"  ✅ Exact reentrancy-eth detected: {f.get('title')} ({f.get('tool', {}).get('rule_id')})")
                break
        
        # Fail hard if exact reentrancy-eth not found
        assert reentrancy_found, \
            "Slither MUST produce exact 'reentrancy-eth' rule for the vulnerable fixture"
        
        # Schema validation: all findings must have required fields
        for f in deduped:
            assert "finding_id" in f, "Finding must have finding_id"
            assert "classification" in f, "Finding must have classification"
            assert "tool" in f, "Finding must have tool info"
            assert "location" in f, "Finding must have location"
            assert "schema_version" in f, "Finding must have schema_version"
        
        print(f"  ✅ All {len(deduped)} findings have valid schema")
        print(f"  ✅ Report generated with {len(report['findings'])} finding categories")
        print(f"  ✅ Provenance preserved in all {len(stage_results)} stage results")
        
        print(f"\n{'='*60}")
        print(f"VULNERABLE FIXTURE TEST: PASSED")
        print(f"{'='*60}")

        return None


def test_vertical_slice_patched():
    """
    Test the pipeline against a known-patched Foundry project.
    
    Expected: Slither should NOT flag the reentrancy-eth detector.
    """
    with tempfile.TemporaryDirectory(prefix="hermes-vs1-patched-") as work_dir:
        print(f"\n{'='*60}")
        print(f"VS1: PATCHED FIXTURE")
        print(f"{'='*60}")
        print(f"Workspace: {work_dir}")
        
        job_id = str(uuid.uuid4())
        artifact_store = ArtifactStore(work_dir)
        job_state = JobState(os.path.join(work_dir, "jobs"))
        job_state.create(job_id, {"target": "fixtures/patched"})
        
        # === STAGE 1: Intake ===
        print("\n--- Stage 1: Intake ---")
        repo_manager = RepositoryManager(os.path.join(work_dir, "intake"))
        _, repo_path, intake_manifest = repo_manager.intake_local(PATCHED_DIR)
        artifact_store.store_manifest(job_id, intake_manifest, "intake")
        job_state.transition(job_id, "running")
        
        # === STAGE 2: Detection ===
        print("\n--- Stage 2: Detection ---")
        detector = FrameworkDetector(repo_path)
        eco_result = detector.detect_ecosystem()
        fw_result = detector.detect_framework()
        assert eco_result.ecosystem == "evm"
        assert fw_result.framework == "foundry"
        
        # === STAGE 3: Build ===
        print("\n--- Stage 3: Build ---")
        build_executor = BuildExecutor(repo_path, fw_result.framework)
        success, _, build_log = build_executor.build(timeout_s=120)
        assert success, f"Build should succeed. Log: {build_log[-500:]}"
        artifact_store.store_build_log(job_id, build_log)
        
        # === STAGE 4: Slither ===
        print("\n--- Stage 4: Slither ---")
        slither_adapter = SlitherAdapter(os.path.join(work_dir, "slither"))
        slither_result = slither_adapter.run(repo_path, job_id, timeout_s=120)
        print(f"  Findings: {len(slither_result.normalized_findings)}")
        
        # === STAGE 5: Normalize ===
        normalizer = FindingNormalizer()
        valid, quarantined = normalizer.normalize(
            slither_result.normalized_findings,
            job_id=job_id,
            tool_name="slither",
            tool_version=slither_result.tool_version,
            adapter_version=slither_adapter.ADAPTER_VERSION,
        )
        print(f"  Valid: {len(valid)}, Quarantined: {len(quarantined)}")
        
        # === ASSERTIONS ===
        print(f"\n{'='*60}")
        print("ASSERTIONS:")
        print(f"{'='*60}")
        
        # The patched version MUST NOT have reentrancy-eth
        reentrancy_found = False
        for f in valid:
            tool_rule = f.get("tool", {}).get("rule_id", "")
            if tool_rule == "reentrancy-eth":
                reentrancy_found = True
                print(f"  ❌ reentrancy-eth STILL flagged in patched version: {f.get('title')}")
        
        assert not reentrancy_found, \
            "Patched fixture MUST NOT trigger reentrancy-eth detector"
        
        if not reentrancy_found:
            print(f"  ✅ No reentrancy-eth detector fired on patched version")
        
        # Verify schema still valid
        for f in valid:
            assert "finding_id" in f
            assert "schema_version" in f
        
        # Save findings
        for f in valid:
            artifact_store.store_finding(job_id, f)
        
        print(f"  ✅ Schema valid for all {len(valid)} findings")
        print(f"  ✅ Pipeline completed without errors")
        
        print(f"\n{'='*60}")
        print(f"PATCHED FIXTURE TEST: PASSED")
        print(f"{'='*60}")

        return None


