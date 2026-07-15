"""
Aderyn adapter — runs Aderyn Rust static analysis and parses JSON output.
"""

import json
import os
import re
import subprocess
import uuid
from pathlib import Path
from typing import Optional

from ..adapters.base_adapter import ToolAdapter, AdapterResult


class AderynAdapter(ToolAdapter):
    """Adapter for running Aderyn static analysis and parsing its JSON output."""

    ADAPTER_VERSION = "0.1.0"
    SUPPORTED_MIN_VERSION = "0.6.0"

    def check_dependencies(self) -> bool:
        """Check if aderyn is available."""
        try:
            result = subprocess.run(
                ["aderyn", "--version"],
                capture_output=True, text=True, timeout=10,
            )
            return result.returncode == 0
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return False

    def get_version(self) -> str:
        """Get installed Aderyn version."""
        try:
            result = subprocess.run(
                ["aderyn", "--version"],
                capture_output=True, text=True, timeout=10,
            )
            return result.stdout.strip()
        except Exception:
            return "unknown"

    def is_supported_version(self) -> bool:
        """Check if version meets minimum requirements."""
        version = self.get_version()
        try:
            parts = version.split(".")
            major, minor = int(parts[0]), int(parts[1])
            return major >= 0 and minor >= 6
        except Exception:
            return False

    def build_command(self, target_dir: str, **kwargs) -> list[str]:
        """Build the Aderyn command.
        
        Aderyn uses -o with .json extension for JSON output.
        """
        json_path = str(self.work_dir / "aderyn-report.json")
        cmd = ["aderyn", "-o", json_path, target_dir]
        
        # Only high severity if specified
        if kwargs.get("highs_only"):
            cmd.append("--highs-only")
        
        return cmd

    def parse_output(self, stdout: str, stderr: str, output_paths: list[str]) -> list[dict]:
        """Parse Aderyn JSON output into normalized finding records."""
        findings = []
        
        json_path = self.work_dir / "aderyn-report.json"
        if json_path.exists():
            try:
                raw = json.loads(json_path.read_text())
                findings = self._parse_json_output(raw)
            except (json.JSONDecodeError, Exception) as e:
                # Try to find the report from the output path
                pass
        
        # Fall back to parsing text output
        if not findings:
            findings = self._parse_text_output(stdout)
        
        return findings

    def _parse_json_output(self, data: dict) -> list[dict]:
        """Parse Aderyn's JSON output format."""
        findings = []
        
        # Aderyn format: { high_issues: { issues: [...] }, low_issues: { issues: [...] } }
        severity_map = {"high_issues": "high", "low_issues": "low"}
        
        for section, severity in severity_map.items():
            section_data = data.get(section, {})
            if isinstance(section_data, dict):
                issues = section_data.get("issues", [])
            elif isinstance(section_data, list):
                issues = section_data
            else:
                continue
            
            for issue in issues:
                if not isinstance(issue, dict):
                    continue
                
                detector_name = issue.get("detector_name", "unknown")
                title = issue.get("title", "")
                description = issue.get("description", "")
                instances = issue.get("instances", [])
                
                if not instances:
                    # Create a finding without location
                    findings.append({
                        "finding_id": str(uuid.uuid4()),
                        "classification": "tool_generated_warning",
                        "severity": severity,
                        "confidence": {"level": 1, "evidence_level": "single_tool",
                                       "evidence_sources": ["aderyn"]},
                        "tool": {"name": "aderyn", "version": self.get_version(),
                                 "rule_id": detector_name},
                        "location": {"file": "", "start_line": 0},
                        "vulnerability_category": self._categorize_vulnerability(detector_name, title),
                        "title": f"Aderyn: {title}",
                        "description": description,
                        "deduplication_group": f"aderyn-{detector_name}",
                        "reproduction": {"status": "none"},
                        "schema_version": "1.0.0",
                    })
                else:
                    for inst in instances:
                        contract_path = inst.get("contract_path", "")
                        line_no = inst.get("line_no", 0)
                        hint = inst.get("hint", "")
                        
                        findings.append({
                            "finding_id": str(uuid.uuid4()),
                            "classification": "tool_generated_warning",
                            "severity": severity,
                            "confidence": {"level": 1, "evidence_level": "single_tool",
                                           "evidence_sources": ["aderyn"]},
                            "tool": {"name": "aderyn", "version": self.get_version(),
                                     "rule_id": detector_name},
                            "location": {
                                "file": contract_path,
                                "start_line": line_no,
                                "end_line": line_no,
                            },
                            "vulnerability_category": self._categorize_vulnerability(detector_name, title),
                            "title": f"Aderyn: {title}",
                            "description": f"{description} {hint}".strip(),
                            "deduplication_group": f"aderyn-{detector_name}-{contract_path}:{line_no}",
                            "reproduction": {"status": "none"},
                            "schema_version": "1.0.0",
                        })
        
        return findings

    def _categorize_vulnerability(self, detector_name: str, title: str) -> str:
        """Map Aderyn detector names to vulnerability categories."""
        combined = (detector_name + " " + title).lower()
        
        if any(w in combined for w in ["reentrancy", "re-entrancy"]):
            return "reentrancy"
        elif any(w in combined for w in ["arithmetic", "overflow", "underflow"]):
            return "arithmetic"
        elif any(w in combined for w in ["access", "acl", "permission", "owner"]):
            return "access_control"
        elif any(w in combined for w in ["unchecked", "unused"]):
            return "logic_error"
        elif any(w in combined for w in ["gas", "opcode"]):
            return "gas"
        elif any(w in combined for w in ["pragma", "version", "naming", "solidity"]):
            return "informational"
        elif any(w in combined for w in ["flash", "loan"]):
            return "flash_loan"
        elif any(w in combined for w in ["oracle", "price"]):
            return "oracle_manipulation"
        else:
            return "other"

    def _parse_text_output(self, stdout: str) -> list[dict]:
        """Parse Aderyn text output as fallback."""
        findings = []
        
        # Look for issue patterns in text output
        for line in stdout.split("\n"):
            line = line.strip()
            if not line:
                continue
            
            # Try to extract issue info
            match = re.match(r'\[(High|Low|Medium|Info)\]\s+(.+?)(?:\s*\((?:\w+:\d+)\))?$', line)
            if match:
                severity = match.group(1).lower()
                desc = match.group(2)
                findings.append({
                    "finding_id": str(uuid.uuid4()),
                    "classification": "tool_generated_warning",
                    "severity": severity,
                    "tool": {"name": "aderyn", "version": self.get_version(), "rule_id": "text-parsed"},
                    "location": {"file": "", "start_line": 0},
                    "vulnerability_category": "other",
                    "title": f"Aderyn: {desc[:80]}",
                    "description": desc,
                    "deduplication_group": f"aderyn-text-{desc[:50]}",
                    "reproduction": {"status": "none"},
                    "schema_version": "1.0.0",
                })
        
        return findings