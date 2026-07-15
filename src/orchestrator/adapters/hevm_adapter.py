"""
hevm adapter — symbolic execution and equivalence checking.
"""

import json
import os
import subprocess
import uuid
from pathlib import Path

from ..adapters.base_adapter import ToolAdapter, AdapterResult


class HevmAdapter(ToolAdapter):
    """Adapter for hevm symbolic execution engine."""

    ADAPTER_VERSION = "0.1.0"

    def check_dependencies(self) -> bool:
        try:
            r = subprocess.run(["hevm", "version"], capture_output=True, text=True, timeout=10)
            return r.returncode == 0
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return False

    def get_version(self) -> str:
        try:
            r = subprocess.run(["hevm", "version"], capture_output=True, text=True, timeout=10)
            return r.stdout.strip()
        except Exception:
            return "unknown"

    def build_command(self, target_dir: str, **kwargs) -> list[str]:
        mode = kwargs.get("mode", "test")
        cmd = ["hevm"]

        if mode == "test":
            cmd.append("test")
            cmd.extend(["--root", target_dir])
            if kwargs.get("match"):
                cmd.extend(["--match", kwargs["match"]])
            if kwargs.get("number"):
                cmd.extend(["--number", str(kwargs["number"])])
        elif mode == "equivalence":
            cmd.append("equivalence")
            cmd.extend(["--root", target_dir])
        elif mode == "symbolic":
            cmd.append("symbolic")
            cmd.extend(["--root", target_dir])

        if kwargs.get("verbose"):
            cmd.append("--verbose")
        if kwargs.get("timeout"):
            cmd.extend(["--smt-timeout", str(kwargs["timeout"])])
        if kwargs.get("early_abort"):
            cmd.append("--early-abort")

        return cmd

    def parse_output(self, stdout: str, stderr: str, output_paths: list[str]) -> list[dict]:
        findings = []
        found_counterexample = False
        current_cex = []

        for line in stdout.split("\n"):
            stripped = line.strip()
            if "Counterexample" in stripped or "found" in stripped.lower() and "counterexample" in stripped.lower():
                found_counterexample = True
            if found_counterexample:
                current_cex.append(stripped)
            if "All tests passed" in stripped and found_counterexample:
                found_counterexample = False

        if found_counterexample or current_cex:
            cex_text = "\n".join(current_cex[-30:])
            findings.append({
                "finding_id": str(uuid.uuid4()),
                "classification": "confirmed_vulnerability",
                "severity": "high",
                "confidence": {"level": 4, "evidence_level": "executable_counterexample",
                               "evidence_sources": ["hevm"]},
                "tool": {"name": "hevm", "rule_id": "counterexample"},
                "location": {}, "vulnerability_category": "logic_error",
                "title": "hevm: Counterexample found",
                "description": cex_text[:1000],
                "deduplication_group": "hevm-counterexample",
                "reproduction": {"status": "counterexample"},
                "schema_version": "1.0.0",
            })

        return findings

    def run_equivalence(self, target_a: str, target_b: str, **kwargs) -> list[dict]:
        """Run equivalence check between two contract versions."""
        cmd = ["hevm", "equivalence", "--root", os.path.dirname(target_a),
               "--code-a", target_a, "--code-b", target_b]
        try:
            r = subprocess.run(cmd, capture_output=True, text=True, timeout=kwargs.get("timeout", 120))
            return self.parse_output(r.stdout, r.stderr, [])
        except subprocess.TimeoutExpired:
            return [{"finding_id": str(uuid.uuid4()), "classification": "analysis_failure",
                     "severity": "low", "tool": {"name": "hevm", "rule_id": "timeout"},
                     "location": {}, "vulnerability_category": "other",
                     "title": "hevm: Equivalence check timed out",
                     "description": f"Timeout after {kwargs.get('timeout', 120)}s",
                     "deduplication_group": "hevm-equiv-timeout",
                     "reproduction": {"status": "none"}, "schema_version": "1.0.0"}]