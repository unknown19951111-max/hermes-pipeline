"""
Wake adapter — Python-based Solidity static analysis and fuzzing framework.
"""

import json
import subprocess
import uuid
from pathlib import Path

from ..adapters.base_adapter import ToolAdapter, AdapterResult


class WakeAdapter(ToolAdapter):
    """Adapter for Wake static analysis framework."""

    ADAPTER_VERSION = "0.1.0"

    DETECTOR_IMPACT_MAP = {
        "high": "high", "medium": "medium", "low": "low", "info": "informational",
        "warning": "low",
    }

    def check_dependencies(self) -> bool:
        try:
            r = subprocess.run(["wake", "--version"], capture_output=True, text=True, timeout=10)
            return r.returncode == 0
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return False

    def get_version(self) -> str:
        try:
            r = subprocess.run(["wake", "--version"], capture_output=True, text=True, timeout=10)
            return r.stdout.strip()
        except Exception:
            return "unknown"

    def build_command(self, target_dir: str, **kwargs) -> list[str]:
        cmd = ["wake", "detect", "all"]
        if kwargs.get("min_impact"):
            cmd.extend(["--min-impact", kwargs["min_impact"]])
        if kwargs.get("min_confidence"):
            cmd.extend(["--min-confidence", kwargs["min_confidence"]])
        if kwargs.get("exclude"):
            for ex in (kwargs["exclude"] if isinstance(kwargs["exclude"], list) else [kwargs["exclude"]]):
                cmd.extend(["--exclude", ex])
        if kwargs.get("only"):
            for o in (kwargs["only"] if isinstance(kwargs["only"], list) else [kwargs["only"]]):
                cmd.extend(["--only", o])
        if kwargs.get("target_paths"):
            cmd.extend(kwargs["target_paths"] if isinstance(kwargs["target_paths"], list) else [kwargs["target_paths"]])
        return cmd

    def parse_output(self, stdout: str, stderr: str, output_paths: list[str]) -> list[dict]:
        findings = []
        lines = stdout.split("\n")

        # Wake outputs findings in a structured text format with impact and detector name
        # Pattern: "  reentrancy                           External call vulnerable to reentrancy"
        current_detector = ""
        current_level = "low"

        for line in lines:
            stripped = line.strip()
            if not stripped:
                continue

            # Detect heading lines that indicate impact level
            if "│" in stripped:
                # Parse the tree-view output
                parts = [p.strip() for p in stripped.split("│") if p.strip()]
                for p in parts:
                    # Detector names are usually lowercase-with-hyphens
                    if p and " " not in p and "-" in p and not p.startswith("─"):
                        current_detector = p
                    elif "Impact" in p or "impact" in p:
                        current_level = p.lower().replace("impact", "").strip()

            # Look for reentrancy or other vulnerability detector hits in the output
            for detector_name in self._get_known_detectors():
                if detector_name in stripped.lower() and "external" not in detector_name:
                    # Extract description
                    desc = stripped.replace(detector_name, "", 1).strip()
                    # Determine severity from context
                    severity = self._infer_severity(detector_name, desc)

                    findings.append({
                        "finding_id": str(uuid.uuid4()),
                        "classification": "tool_generated_warning",
                        "severity": self.DETECTOR_IMPACT_MAP.get(severity, "low"),
                        "confidence": {"level": 1, "evidence_level": "single_tool",
                                       "evidence_sources": ["wake"]},
                        "tool": {"name": "wake", "version": self.get_version(),
                                 "rule_id": detector_name},
                        "location": {"file": ""},
                        "vulnerability_category": self._categorize(detector_name),
                        "title": f"Wake: {detector_name}",
                        "description": desc[:500] if desc else detector_name,
                        "deduplication_group": f"wake-{detector_name}",
                        "reproduction": {"status": "none"},
                        "schema_version": "1.0.0",
                    })

        return findings

    def _get_known_detectors(self) -> list[str]:
        return [
            "reentrancy", "unchecked-return-value", "tx-origin", "msg-value-nonpayable-function",
            "unsafe-delegatecall", "unprotected-selfdestruct", "incorrect-interface",
            "complex-struct-getter", "missing-return", "balance-relied-on",
            "calldata-tuple-reencoding-head-overflow-bug", "empty-byte-array-copy-bug",
            "chainlink-deprecated-function", "array-delete-nullification",
            "abi-encode-with-signature", "call-options-not-called",
            "invalid-memory-safe-assembly", "struct-mapping-deletion",
            "unsafe-erc20-call", "axelar-proxy-contract-id",
            "unused-contract", "unused-function", "unused-import", "unused-event",
            "unused-error", "unused-modifier",
        ]

    def _infer_severity(self, detector: str, desc: str) -> str:
        high_impact = {"reentrancy", "unprotected-selfdestruct", "unsafe-delegatecall",
                        "tx-origin", "msg-value-nonpayable-function"}
        medium_impact = {"unchecked-return-value", "chainlink-deprecated-function",
                          "balance-relied-on", "unsafe-erc20-call"}
        if detector in high_impact:
            return "high"
        if detector in medium_impact:
            return "medium"
        return "info"

    def _categorize(self, detector_name: str) -> str:
        name = detector_name.lower()
        if "reentrancy" in name:
            return "reentrancy"
        if "delegatecall" in name or "selfdestruct" in name:
            return "access_control"
        if "unchecked" in name:
            return "logic_error"
        if "tx.origin" in name or "msg.value" in name:
            return "best_practices"
        if "abi" in name or "encoding" in name:
            return "logic_error"
        return "other"