"""
Halmos adapter — symbolic bounded model checker for EVM smart contracts.
"""

import json
import subprocess
import uuid
from pathlib import Path

from ..adapters.base_adapter import ToolAdapter, AdapterResult


class HalmosAdapter(ToolAdapter):
    """Adapter for Halmos symbolic execution engine."""

    ADAPTER_VERSION = "0.1.0"

    def check_dependencies(self) -> bool:
        try:
            r = subprocess.run(["halmos", "--version"], capture_output=True, text=True, timeout=10)
            return r.returncode == 0
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return False

    def get_version(self) -> str:
        try:
            r = subprocess.run(["halmos", "--version"], capture_output=True, text=True, timeout=10)
            return r.stdout.strip()
        except Exception:
            return "unknown"

    def build_command(self, target_dir: str, **kwargs) -> list[str]:
        cmd = ["halmos"]
        out = str(self.work_dir / "halmos-out.json")
        cmd.extend(["--json-output", out])

        if kwargs.get("function"):
            cmd.extend(["--function", kwargs["function"]])
        if kwargs.get("match_test"):
            cmd.extend(["--match-test", kwargs["match_test"]])
        if kwargs.get("number_of_cores"):
            cmd.extend(["--number-of-cores", str(kwargs["number_of_cores"])])
        if kwargs.get("solver_timeout_assertion"):
            cmd.extend(["--solver-timeout-assertion", str(kwargs["solver_timeout_assertion"])])
        if kwargs.get("loop"):
            cmd.extend(["--loop", str(kwargs["loop"])])
        if kwargs.get("depth"):
            cmd.extend(["--depth", str(kwargs["depth"])])
        if kwargs.get("width"):
            cmd.extend(["--width", str(kwargs["width"])])

        cmd.append(target_dir)
        return cmd

    def parse_output(self, stdout: str, stderr: str, output_paths: list[str]) -> list[dict]:
        findings = []
        json_path = self.work_dir / "halmos-out.json"
        if json_path.exists():
            try:
                data = json.loads(json_path.read_text())
                findings = self._parse_json(data)
            except (json.JSONDecodeError, Exception):
                pass
        if not findings:
            findings = self._parse_text(stdout)
        return findings

    def _parse_json(self, data: dict) -> list[dict]:
        findings = []
        tr = data.get("test_results", {})
        for entry_name, entry in tr.items():
            if not isinstance(entry, dict):
                continue
            contract_file = entry.get("contract", entry_name)
            for test_name, test in entry.items():
                if not isinstance(test, dict):
                    continue
                result = test.get("result", {})
                status = result.get("status", "")
                if status in ("failed", "error"):
                    counterexample = result.get("counterexample", {})
                    findings.append({
                        "finding_id": str(uuid.uuid4()),
                        "classification": "confirmed_vulnerability" if status == "failed" else "analysis_failure",
                        "severity": "high",
                        "confidence": {"level": 3, "evidence_level": "executable_failure",
                                       "evidence_sources": ["halmos"]},
                        "tool": {"name": "halmos", "rule_id": "symbolic-failure"},
                        "location": {"file": contract_file},
                        "vulnerability_category": "logic_error",
                        "title": f"Halmos: {test_name} ({status})",
                        "description": json.dumps(counterexample, indent=2)[:1000],
                        "deduplication_group": f"halmos-{test_name}",
                        "reproduction": {"status": "counterexample" if counterexample else "none"},
                        "schema_version": "1.0.0",
                    })
            break  # Only first contract
        return findings

    def _parse_text(self, stdout: str) -> list[dict]:
        findings = []
        for line in stdout.split("\n"):
            if "[FAIL]" in line:
                test = line.split("[FAIL]")[-1].strip()
                findings.append({
                    "finding_id": str(uuid.uuid4()),
                    "classification": "confirmed_vulnerability",
                    "severity": "high", "tool": {"name": "halmos", "rule_id": "text-fail"},
                    "location": {}, "vulnerability_category": "other",
                    "title": f"Halmos: {test}", "deduplication_group": f"halmos-{test}",
                    "reproduction": {"status": "counterexample"}, "schema_version": "1.0.0",
                })
        return findings