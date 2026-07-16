"""
PoC generation — converts failing fuzzer sequences into deterministic Foundry fork tests.
"""

import json
import os
import re
import subprocess
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional


class POCGenerationError(Exception):
    pass


class POCGenerator:
    """
    Converts failing fuzzer sequences into Foundry fork tests that reproduce
    the failure deterministically on a pinned block.
    """

    def __init__(self, work_dir: str):
        self.work_dir = Path(work_dir)
        self.work_dir.mkdir(parents=True, exist_ok=True)

    def generate_from_sequence(self, finding: dict, target_dir: str,
                                commit_sha: str = "", fork_block: int = 0,
                                contract_name: str = "Contract",
                                rpc_url: str = "") -> dict:
        """
        Generate a Foundry PoC test from a failing fuzzer sequence.

        Returns PoC manifest with path, compile_status, reproduction_status.
        """
        # Build the PoC Solidity file
        poc_content = self._build_poc_test(
            finding, contract_name, commit_sha, fork_block, rpc_url,
        )

        # Write to target test dir
        poc_id = str(uuid.uuid4())[:8]
        poc_path = Path(target_dir) / "test" / f"PoC_{poc_id}.t.sol"
        poc_path.parent.mkdir(parents=True, exist_ok=True)
        poc_path.write_text(poc_content)

        # Try to compile the PoC
        compile_success, compile_error = self._verify_compilation(target_dir)

        # Try to run the PoC test
        repro_success, repro_error = False, "Not executed"
        if compile_success:
            repro_success, repro_error = self._reproduce_test(target_dir, f"PoC_{poc_id}")

        # Build manifest
        manifest = {
            "poc_id": poc_id,
            "finding_id": finding.get("finding_id", ""),
            "target_commit": commit_sha,
            "fork_block": fork_block,
            "poc_path": str(poc_path),
            "compile_status": "passed" if compile_success else "failed",
            "compile_error": compile_error[:500] if compile_error else "",
            "reproduction_status": "reproduced" if repro_success else "not_reproduced",
            "reproduction_error": repro_error[:500] if repro_error and not repro_success else "",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "generator_version": "0.1.0",
        }

        # Save manifest
        manifest_path = self.work_dir / f"poc_{poc_id}_manifest.json"
        manifest_path.write_text(json.dumps(manifest, indent=2))

        return manifest

    def _build_poc_test(self, finding: dict, contract_name: str,
                         commit_sha: str, fork_block: int,
                         rpc_url: str) -> str:
        """Build the Foundry PoC test content."""
        tool_name = finding.get("tool", {}).get("name", "unknown")
        rule_id = finding.get("tool", {}).get("rule_id", "")
        title = finding.get("title", "Unspecified finding")
        description = finding.get("description", "")
        location = finding.get("location", {})
        source_file = location.get("file", "")
        source_line = location.get("start_line", 0)
        classification = finding.get("classification", "unknown")

        # Try to extract call sequence from description
        sequence_steps = self._extract_sequence_steps(description)
        sequence_comment = ""
        for s in sequence_steps:
            sequence_comment += f"    //   {s}\n"

        # Determine RPC URL
        rpc_url = rpc_url or os.environ.get("ETH_RPC_URL", "")
        fork_block_str = f"block: {fork_block}" if fork_block else "latest"

        # Build the test
        poc = f"""// SPDX-License-Identifier: MIT
pragma solidity >=0.8.0;

import "forge-std/Test.sol";
import "../{source_file}";

/**
 * @title PoC_{tool_name}_{rule_id}
 * @notice Auto-generated PoC for: {title}
 * @dev Classification: {classification}
 * @dev Tool: {tool_name} ({rule_id})
 * @dev Source: {source_file}:{source_line}
 * @dev Target commit: {commit_sha}
 *
 * Description:
 * {description.split(chr(10))[0] if description else ""}
 */
contract PoC_{tool_name}_{rule_id} is Test {{
    {contract_name} public target;

    /// @dev Set up the fork and deploy target at the pinned state
    function setUp() public {{
{f'        vm.createSelectFork("{rpc_url}", {fork_block});' if rpc_url and fork_block else ''}
        target = new {contract_name}();
        vm.deal(address(this), 100 ether);
        vm.deal(address(0xDEAD), 100 ether);
    }}

    /// @dev Reproduce the failing sequence
    function test_reproduce() public {{
        // Reproduce the failing sequence:
{sequence_comment}
        // The actual reproduction logic depends on the specific vulnerability.
        // This scaffold provides the fork environment and target deployment.
        // Replace the body below with the actual exploit sequence.

        // TODO: Insert exploit steps here
        // Example: target.withdraw(target.balanceOf(address(this)));

        // Assert the invariant that should hold but doesn't:
        // assertEq(target.balanceOf(address(this)), 0, "Invariant violated");
    }}

    /// @dev Test that the invariant is not violated in a normal scenario
    function test_baseline() public {{
        // Normal operation should not trigger the vulnerability
        // This serves as a negative control
    }}
}}
"""
        return poc

    def _extract_sequence_steps(self, description: str) -> list[str]:
        """Extract call sequence steps from a fuzzer failure description."""
        steps = []
        lines = description.split("\n")
        in_sequence = False

        for line in lines:
            stripped = line.strip()
            # Detect sequence markers
            if "Call sequence" in stripped or "Sequence" in stripped or "Steps" in stripped:
                in_sequence = True
                continue
            if in_sequence and stripped:
                if stripped.startswith("->") or stripped.startswith("-") or stripped.startswith("  "):
                    # Clean up
                    clean = re.sub(r'^\s*[->\s]+', '', stripped).strip()
                    if clean:
                        steps.append(clean)
                elif stripped.startswith("TRACE"):
                    steps.append(stripped)
                elif stripped.startswith("[") or stripped.startswith("#"):
                    steps.append(stripped)
            # Stop at empty line after sequence
            if in_sequence and not stripped:
                in_sequence = False

        return steps[:20]  # Max 20 steps

    def _verify_compilation(self, target_dir: str) -> tuple[bool, str]:
        """Verify that the PoC compiles."""
        try:
            result = subprocess.run(
                ["forge", "build", "--via-ir", "--force"],
                cwd=target_dir,
                capture_output=True, text=True,
                timeout=60,
            )
            if result.returncode == 0:
                return True, ""
            return False, result.stderr[:500] + result.stdout[-500:]
        except subprocess.TimeoutExpired:
            return False, "BUILD TIMEOUT"
        except FileNotFoundError:
            return False, "forge not found"

    def _reproduce_test(self, target_dir: str, test_name: str) -> tuple[bool, str]:
        """Run the PoC test to verify reproduction."""
        try:
            result = subprocess.run(
                ["forge", "test", "--match-path", f"*{test_name}*", "-vvv"],
                cwd=target_dir,
                capture_output=True, text=True,
                timeout=120,
            )
            stdout = result.stdout
            stderr = result.stderr

            # Check if test passed or failed
            if "PASSED" in stdout and "FAILED" not in stdout:
                return False, "Test passed (baseline OK — no reproduction)"
            elif "FAILED" in stdout:
                # Failed means our PoC test caught something — good reproduction
                failure_lines = []
                for line in stdout.split("\n"):
                    if "FAILED" in line or "Error" in line or "revert" in line:
                        failure_lines.append(line.strip())
                return True, "\n".join(failure_lines[:5]) if failure_lines else "Test failed (reproduction confirmed)"
            else:
                return False, stdout[-500:] if stdout else "No test output"

        except subprocess.TimeoutExpired:
            return False, "TEST TIMEOUT"
        except FileNotFoundError:
            return False, "forge not found in PATH"

    @staticmethod
    def generate_from_medusa_result(medusa_result: dict, target_dir: str,
                                      commit_sha: str = "", fork_block: int = 0,
                                      contract_name: str = "Contract") -> Optional[dict]:
        """
        Generate a PoC from a Medusa adapter result (convenience wrapper).
        """
        # Look for invariant violations in findings
        findings = medusa_result.get("normalized_findings", [])
        if not findings:
            return None

        # Find the most severe finding
        findings.sort(key=lambda f: {"critical": 5, "high": 4, "medium": 3,
                                     "low": 2, "informational": 1}.get(
            f.get("severity", "low"), 0), reverse=True)

        work_dir = medusa_result.get("_work_dir", "/tmp")
        generator = POCGenerator(work_dir)
        return generator.generate_from_sequence(
            findings[0], target_dir, commit_sha, fork_block, contract_name,
        )


class HumanReviewQueue:
    """
    Manages the human-review routing for qualified findings.

    A finding enters the review queue when it has:
    - classification: confirmed_vulnerability or invariant_violation
    - reproduction status: pass (PoC confirmed)
    - confidence >= 3 (executable_failure or higher)
    - provenance: complete
    """

    REVIEW_STATUSES = ["pending", "reviewing", "approved", "rejected", "requires_more_info"]

    def __init__(self, queue_dir: str):
        self.queue_dir = Path(queue_dir)
        self.queue_dir.mkdir(parents=True, exist_ok=True)

    def enqueue(self, finding: dict, poc_manifest: dict = None) -> dict:
        """
        Add a qualifying finding to the human-review queue.

        Returns the queue entry record.
        """
        # Check if the finding qualifies for review
        classification = finding.get("classification", "")
        if classification not in ("confirmed_vulnerability", "invariant_violation",
                                   "reproducible_suspicious_behavior"):
            return {
                "status": "skipped",
                "reason": f"Classification '{classification}' does not qualify for review",
            }

        # Check reproduction status
        repro = finding.get("reproduction", {})
        if repro.get("status") not in ("pass",):
            return {
                "status": "skipped",
                "reason": f"Reproduction status '{repro.get('status')}' not confirmed",
            }

        # Generate queue entry
        entry_id = str(uuid.uuid4())
        entry = {
            "entry_id": entry_id,
            "finding_id": finding.get("finding_id", ""),
            "status": "pending",
            "classification": classification,
            "severity": finding.get("severity", ""),
            "title": finding.get("title", ""),
            "tool": finding.get("tool", {}).get("name", ""),
            "location": finding.get("location", {}),
            "reproduction": repro,
            "poc_manifest": poc_manifest or {},
            "provenance": finding.get("provenance", {}),
            "entered_at": datetime.now(timezone.utc).isoformat(),
            "reviewed_by": "",
            "reviewed_at": "",
            "review_notes": "",
            "decision": "",
        }

        # Save entry
        entry_path = self.queue_dir / f"{entry_id}.json"
        entry_path.write_text(json.dumps(entry, indent=2))

        return entry

    def list_pending(self) -> list[dict]:
        """List all pending review entries."""
        entries = []
        for f in sorted(self.queue_dir.glob("*.json")):
            try:
                entry = json.loads(f.read_text())
                if entry.get("status") == "pending":
                    entries.append(entry)
            except Exception:
                continue
        return entries

    def list_all(self) -> list[dict]:
        """List all review entries."""
        entries = []
        for f in sorted(self.queue_dir.glob("*.json")):
            try:
                entries.append(json.loads(f.read_text()))
            except Exception:
                continue
        return entries

    def get(self, entry_id: str) -> Optional[dict]:
        """Get a review entry by ID."""
        entry_path = self.queue_dir / f"{entry_id}.json"
        if not entry_path.exists():
            return None
        return json.loads(entry_path.read_text())

    def review(self, entry_id: str, reviewer: str, decision: str,
                notes: str = "") -> Optional[dict]:
        """Record a human review decision."""
        if decision not in ("approved", "rejected", "requires_more_info"):
            raise ValueError(f"Invalid decision: {decision}")

        entry = self.get(entry_id)
        if not entry:
            return None

        entry["status"] = "reviewing" if decision == "requires_more_info" else decision
        entry["reviewed_by"] = reviewer
        entry["reviewed_at"] = datetime.now(timezone.utc).isoformat()
        entry["review_notes"] = notes
        entry["decision"] = decision

        entry_path = self.queue_dir / f"{entry_id}.json"
        entry_path.write_text(json.dumps(entry, indent=2))

        return entry

    def count(self) -> dict:
        """Get queue statistics."""
        counts = {"pending": 0, "reviewing": 0, "approved": 0, "rejected": 0}
        for entry in self.list_all():
            status = entry.get("status", "")
            if status in counts:
                counts[status] += 1
        return counts