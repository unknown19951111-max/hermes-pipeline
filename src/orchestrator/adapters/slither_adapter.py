"""
Slither adapter — runs Slither static analysis and parses JSON output.
"""

import json
import os
import re
import subprocess
import uuid
from pathlib import Path
from typing import Optional

from ..adapters.base_adapter import ToolAdapter, AdapterResult


class SlitherAdapter(ToolAdapter):
    """Adapter for running Slither static analysis and parsing its JSON output."""

    ADAPTER_VERSION = "0.1.0"
    SUPPORTED_MIN_VERSION = "0.10.0"

    def check_dependencies(self) -> bool:
        """Check if slither is available."""
        try:
            result = subprocess.run(
                ["slither", "--version"],
                capture_output=True, text=True, timeout=10,
            )
            return result.returncode == 0
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return False

    def get_version(self) -> str:
        """Get installed Slither version."""
        try:
            result = subprocess.run(
                ["slither", "--version"],
                capture_output=True, text=True, timeout=10,
            )
            return result.stdout.strip()
        except Exception:
            return "unknown"

    def is_supported_version(self) -> bool:
        """Check if the version meets minimum requirements."""
        version = self.get_version()
        try:
            major, minor, _ = version.split(".")
            return int(major) >= 0 and int(minor) >= 10
        except Exception:
            return False

    def build_command(self, target_dir: str, **kwargs) -> list[str]:
        """Build the Slither command.
        
        Uses --json flag for machine-readable output.
        """
        cmd = ["slither", "."]
        
        # Add JSON output
        json_path = str(self.work_dir / "slither-report.json")
        cmd.extend(["--json", json_path])
        
        # Use checklist mode for human-readable output
        cmd.append("--checklist")
        
        # Filter by detectors if specified
        detectors = kwargs.get("detectors")
        if detectors:
            cmd.extend(["--detectors", ",".join(detectors)])
        
        # Exclude detectors if specified
        exclude = kwargs.get("exclude_detectors")
        if exclude:
            cmd.extend(["--exclude", ",".join(exclude)])
        
        # Include only specific detectors
        include = kwargs.get("include_detectors")
        if include:
            cmd.extend(["--include", ",".join(include)])
        
        return cmd

    def parse_output(self, stdout: str, stderr: str, output_paths: list[str]) -> list[dict]:
        """Parse Slither JSON output into normalized finding records."""
        findings = []
        
        # Try to find and parse the JSON report
        json_path = self.work_dir / "slither-report.json"
        if json_path.exists():
            try:
                raw = json.loads(json_path.read_text())
                findings = self._parse_json_output(raw)
            except (json.JSONDecodeError, Exception) as e:
                # Fall back to parsing stdout for findings
                pass
        
        # If no JSON findings, try parsing text output
        if not findings:
            findings = self._parse_text_output(stdout)
        
        return findings

    def _parse_json_output(self, data: dict) -> list[dict]:
        """Parse Slither's JSON output format."""
        findings = []
        
        # Slither JSON typically has a 'results' key with 'detectors' and 'printers'
        results = data.get("results", data)
        detectors = results.get("detectors", data.get("detectors", []))
        
        if not detectors and isinstance(data, dict):
            # Try alternative structure: list of results
            for key in ["detectors", "results", "issues", "findings"]:
                if key in data and isinstance(data[key], list):
                    detectors = data[key]
                    break
        
        for det in detectors:
            finding = self._detector_to_finding(det)
            if finding:
                findings.append(finding)
        
        return findings

    def _detector_to_finding(self, det: dict) -> Optional[dict]:
        """Convert a single Slither detector output to normalized finding."""
        if not isinstance(det, dict):
            return None
        
        elements = det.get("elements", det.get("element", det.get("elements", [])))
        if isinstance(elements, dict):
            elements = [elements]
        elif not isinstance(elements, list):
            elements = []
        
        # Get location from first element
        location = {"file": "", "start_line": 0, "end_line": 0}
        if elements:
            first = elements[0] if isinstance(elements, list) and len(elements) > 0 else elements
            if isinstance(first, dict):
                source_mapping = first.get("source_mapping", first)
                if isinstance(source_mapping, dict):
                    location["file"] = source_mapping.get("filename_relative", "")
                    location["start_line"] = source_mapping.get("lines", [0, 0])[0] if isinstance(source_mapping.get("lines"), list) else source_mapping.get("line", 0)
                    location["end_line"] = source_mapping.get("lines", [0, 0])[-1] if isinstance(source_mapping.get("lines"), list) else location["start_line"]
        
        # Get check/rule info
        check = det.get("check", det.get("id", det.get("detector_id", "")))
        description = det.get("description", det.get("message", det.get("desc", "")))
        impact = det.get("impact", det.get("severity", det.get("impact", "Medium")))
        confidence = det.get("confidence", det.get("confidence", "Medium"))
        
        # Map severity
        severity_map = {
            "High": "high", "Medium": "medium", "Low": "low", 
            "Informational": "informational", "Optimization": "informational"
        }
        
        # Map confidence to evidence level
        conf_map = {
            "High": "single_tool",
            "Medium": "single_tool",
            "Low": "single_tool",
        }
        
        return {
            "finding_id": str(uuid.uuid4()),
            "classification": "tool_generated_warning",
            "severity": severity_map.get(impact.title() if impact else "Medium", "medium"),
            "confidence": {
                "level": 1,
                "evidence_level": "single_tool",
                "evidence_sources": ["slither"]
            },
            "tool": {
                "name": "slither",
                "version": self.get_version(),
                "rule_id": str(check),
            },
            "location": location,
            "vulnerability_category": self._categorize_vulnerability(str(check), str(description)),
            "title": f"Slither: {check}",
            "description": str(description),
            "deduplication_group": f"slither-{check}-{location.get('file', '')}:{location.get('start_line', 0)}",
            "reproduction": {"status": "none"},
            "schema_version": "1.0.0",
        }

    def _categorize_vulnerability(self, check: str, description: str) -> str:
        """Map Slither check names to vulnerability categories."""
        check_lower = check.lower()
        desc_lower = description.lower()
        
        if any(w in check_lower or w in desc_lower for w in ["reentrancy", "re-entrancy"]):
            return "reentrancy"
        elif any(w in check_lower or w in desc_lower for w in ["arithmetic", "overflow", "underflow"]):
            return "arithmetic"
        elif any(w in check_lower or w in desc_lower for w in ["access", "controlled", "permission", "owner", "acl"]):
            return "access_control"
        elif any(w in check_lower or w in desc_lower for w in ["tx.origin", "txorigin"]):
            return "access_control"
        elif any(w in check_lower or w in desc_lower for w in ["unchecked", "unused-return", "unused"]):
            return "logic_error"
        elif any(w in check_lower or w in desc_lower for w in ["gas", "cost"]):
            return "gas"
        elif any(w in check_lower or w in desc_lower for w in ["shadow", "naming", "solc", "pragma", "version"]):
            return "informational"
        else:
            return "other"

    def _parse_text_output(self, stdout: str) -> list[dict]:
        """Parse Slither text output for findings when JSON is unavailable."""
        findings = []
        
        # Pattern for Slither text output: "ContractName.function (file.sol#L42-L55) has finding"
        pattern = re.compile(
            r'(?:(\w+)\.)?(\w+)\s*\(([^)]+)\)\s*(?:\|\s*)?(High|Medium|Low|Informational)\s*'
            r'(?:-\s*)?(.+?)(?=\n\s*\w|\Z)',
            re.DOTALL
        )
        
        for match in pattern.finditer(stdout):
            contract = match.group(1) or ""
            func = match.group(2)
            location_str = match.group(3)
            severity = match.group(4)
            desc = match.group(5).strip()
            
            # Try to extract file and line from location_str
            file_match = re.search(r'([\w/.-]+\.sol)', location_str)
            line_match = re.search(r'L(\d+)', location_str)
            
            location = {"file": file_match.group(1) if file_match else "", "start_line": int(line_match.group(1)) if line_match else 0}
            
            findings.append({
                "finding_id": str(uuid.uuid4()),
                "classification": "tool_generated_warning",
                "severity": severity.lower(),
                "tool": {"name": "slither", "version": self.get_version(), "rule_id": "text-parsed"},
                "location": location,
                "vulnerability_category": "other",
                "title": f"Slither: {desc[:80]}",
                "description": desc,
                "deduplication_group": f"slither-text-{location.get('file', '')}:{location.get('start_line', 0)}",
                "reproduction": {"status": "none"},
                "schema_version": "1.0.0",
            })
        
        return findings