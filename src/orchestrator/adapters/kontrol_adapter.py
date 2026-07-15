"""
Kontrol adapter — KEVM formal verification bridge.
"""

import json
import subprocess
import uuid
from pathlib import Path

from ..adapters.base_adapter import ToolAdapter, AdapterResult


class KontrolAdapter(ToolAdapter):
    """
    Adapter for Kontrol — the KEVM formal verification bridge.
    
    Kontrol requires significant setup (KEVM, K Framework) and is typically
    only available in containerized or CI environments. This adapter provides
    graceful degradation when Kontrol is absent.
    """

    ADAPTER_VERSION = "0.1.0"

    def check_dependencies(self) -> bool:
        try:
            r = subprocess.run(["kontrol", "--version"], capture_output=True, text=True, timeout=15)
            return r.returncode == 0
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return False

    def get_version(self) -> str:
        try:
            r = subprocess.run(["kontrol", "--version"], capture_output=True, text=True, timeout=15)
            return r.stdout.strip()
        except Exception:
            return "unknown"

    def is_supported_version(self) -> bool:
        return False  # Kontrol is not available in this environment

    def build_command(self, target_dir: str, **kwargs) -> list[str]:
        cmd = ["kontrol"]
        if kwargs.get("command") == "prove":
            cmd.append("prove")
            cmd.extend(["--root", target_dir])
            if kwargs.get("match"):
                cmd.extend(["--match-test", kwargs["match"]])
            if kwargs.get("workers"):
                cmd.extend(["--workers", str(kwargs["workers"])])
            if kwargs.get("max_depth"):
                cmd.extend(["--max-depth", str(kwargs["max_depth"])])
        elif kwargs.get("command") == "build":
            cmd.append("build")
            cmd.extend(["--root", target_dir])
        else:
            cmd.extend([kwargs.get("command", "help")])
        return cmd

    def parse_output(self, stdout: str, stderr: str, output_paths: list[str]) -> list[dict]:
        findings = []
        for line in stdout.split("\n"):
            ls = line.strip()
            if "FAILED" in ls or "failed" in ls.lower():
                test_part = ls.replace("FAILED", "").replace("failed", "").strip().split()[0] if ls.split() else ""
                findings.append({
                    "finding_id": str(uuid.uuid4()),
                    "classification": "confirmed_vulnerability",
                    "severity": "high",
                    "confidence": {"level": 4, "evidence_level": "formal_verification_counterexample",
                                   "evidence_sources": ["kontrol"]},
                    "tool": {"name": "kontrol", "rule_id": "proof-failure"},
                    "location": {}, "vulnerability_category": "logic_error",
                    "title": f"Kontrol: proof failed — {test_part}",
                    "deduplication_group": f"kontrol-fail-{test_part}",
                    "reproduction": {"status": "counterexample"},
                    "schema_version": "1.0.0",
                })
        return findings