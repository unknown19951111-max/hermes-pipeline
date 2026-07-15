"""
Echidna adapter — property-based fuzzer for differential coverage vs Medusa.
"""

import json
import os
import re
import subprocess
import uuid
from pathlib import Path
from typing import Optional

from ..adapters.base_adapter import ToolAdapter, AdapterResult


class EchidnaAdapter(ToolAdapter):
    """Adapter for running Echidna property-based fuzzing."""

    ADAPTER_VERSION = "0.1.0"

    def check_dependencies(self) -> bool:
        try:
            result = subprocess.run(
                ["echidna", "--version"],
                capture_output=True, text=True, timeout=10,
            )
            return result.returncode == 0
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return False

    def get_version(self) -> str:
        try:
            result = subprocess.run(
                ["echidna", "--version"],
                capture_output=True, text=True, timeout=10,
            )
            return result.stdout.strip()
        except Exception:
            return "unknown"

    def build_command(self, target_dir: str, **kwargs) -> list[str]:
        """Build the Echidna command."""
        cmd = ["echidna"]
        
        # Config file
        config = kwargs.get("config")
        if config:
            cmd.extend(["--config", config])
        
        # Test limit
        test_limit = kwargs.get("test_limit")
        if test_limit:
            cmd.extend(["--test-limit", str(test_limit)])
        
        # Sequence length
        seq_len = kwargs.get("sequence_length")
        if seq_len:
            cmd.extend(["--seq-len", str(seq_len)])
        
        # Corpus directory
        corpus_dir = kwargs.get("corpus_dir")
        if corpus_dir:
            cmd.extend(["--corpus-dir", corpus_dir])
        
        # Contract to test
        contract = kwargs.get("contract")
        if contract:
            cmd.append(contract)
        
        # Target file
        cmd.append(target_dir)
        
        return cmd

    def parse_output(self, stdout: str, stderr: str, output_paths: list[str]) -> list[dict]:
        """Parse Echidna output for failing properties."""
        findings = []
        
        lines = stdout.split("\n")
        current_failure = ""
        failure_steps = []
        in_failure = False
        
        for line in lines:
            ls = line.strip()
            
            # Check for failure
            if "FAILED" in ls or "failed" in ls.lower():
                # Extract property name
                prop_match = re.match(r'^.*?(?:FAILED|failed)\s*:?\s*(.+?:)', ls)
                if prop_match:
                    current_failure = prop_match.group(1).strip()
                else:
                    current_failure = ls[:80]
                in_failure = True
                failure_steps = []
            
            # Collect failure steps
            if in_failure and ls:
                if ls.startswith("Call sequence") or ls.startswith("  ") or ls.startswith("->"):
                    failure_steps.append(ls)
            
            # Check for end of failure
            if in_failure and ("PASSED" in ls or "Unique" in ls or "Test limit" in ls):
                if current_failure and failure_steps:
                    findings.append({
                        "finding_id": str(uuid.uuid4()),
                        "classification": "invariant_violation",
                        "severity": "high",
                        "confidence": {"level": 3, "evidence_level": "executable_failure",
                                       "evidence_sources": ["echidna"]},
                        "tool": {"name": "echidna", "version": self.get_version(),
                                 "rule_id": "property-failure"},
                        "location": {"file": "", "start_line": 0},
                        "vulnerability_category": "other",
                        "title": f"Echidna: {current_failure}",
                        "description": "Failing sequence:\n" + "\n".join(failure_steps[-15:]),
                        "deduplication_group": f"echidna-fail-{current_failure[:50]}",
                        "reproduction": {"status": "none"},
                        "schema_version": "1.0.0",
                    })
                current_failure = ""
                failure_steps = []
                in_failure = False
        
        return findings