"""
Heimdall-rs adapter — decompilation, storage analysis, and bytecode-level insights.
"""

import json
import subprocess
import uuid
from pathlib import Path

from ..adapters.base_adapter import ToolAdapter, AdapterResult


class HeimdallAdapter(ToolAdapter):
    """Adapter for Heimdall-rs bytecode analysis toolkit."""

    ADAPTER_VERSION = "0.1.0"
    SUPPORTED_SUBCOMMANDS = ["decompile", "storage", "trace", "selectors", "approve"]

    def check_dependencies(self) -> bool:
        try:
            r = subprocess.run(["heimdall", "--version"], capture_output=True, text=True, timeout=10)
            return r.returncode == 0
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return False

    def get_version(self) -> str:
        try:
            r = subprocess.run(["heimdall", "--version"], capture_output=True, text=True, timeout=10)
            return r.stdout.strip()
        except Exception:
            return "unknown"

    def build_command(self, target_dir: str, **kwargs) -> list[str]:
        subcommand = kwargs.get("subcommand", "selectors")
        output = str(self.work_dir / f"heimdall-{subcommand}.json")
        cmd = ["heimdall", subcommand]

        if subcommand == "decompile":
            if kwargs.get("bytecode"):
                cmd.extend(["--bytecode", kwargs["bytecode"]])
            elif kwargs.get("contract"):
                cmd.extend(["--contract", kwargs["contract"]])
        elif subcommand == "storage":
            if kwargs.get("bytecode"):
                cmd.extend(["--bytecode", kwargs["bytecode"]])
            if kwargs.get("rpc_url"):
                cmd.extend(["--rpc-url", kwargs["rpc_url"]])
            if kwargs.get("slot"):
                cmd.extend(["--slot", kwargs["slot"]])
        elif subcommand == "selectors":
            if kwargs.get("bytecode"):
                cmd.extend(["--bytecode", kwargs["bytecode"]])
            elif kwargs.get("contract"):
                cmd.extend(["--contract", kwargs["contract"]])

        if kwargs.get("output"):
            cmd.extend(["--output", kwargs["output"]])
        else:
            cmd.extend(["--output", output])

        return cmd

    def parse_output(self, stdout: str, stderr: str, output_paths: list[str]) -> list[dict]:
        findings = []

        # Look for selectors output
        for line in stdout.split("\n"):
            stripped = line.strip()
            if "Function" in stripped and "(" in stripped:
                findings.append({
                    "finding_id": str(uuid.uuid4()),
                    "classification": "information_gathering",
                    "severity": "informational",
                    "tool": {"name": "heimdall", "rule_id": "function-selector"},
                    "location": {}, "vulnerability_category": "other",
                    "title": f"Heimdall: {stripped}",
                    "deduplication_group": f"heimdall-selector-{stripped[:40]}",
                    "reproduction": {"status": "none"},
                    "schema_version": "1.0.0",
                })

        return findings