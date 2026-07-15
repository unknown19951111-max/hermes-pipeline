"""
Solana adapter — Anchor and Solana-native toolchain CLI.
"""

import json
import os
import re
import subprocess
import uuid
from pathlib import Path
from typing import Optional

from ..adapters.base_adapter import ToolAdapter, AdapterResult


class SolanaDetector:
    """Detect Solana CLI and Anchor availability."""

    @staticmethod
    def check_solana_cli() -> tuple[bool, str]:
        try:
            r = subprocess.run(["solana", "--version"], capture_output=True, text=True, timeout=10)
            if r.returncode == 0:
                return True, r.stdout.strip()
        except (FileNotFoundError, subprocess.TimeoutExpired):
            pass
        return False, ""

    @staticmethod
    def check_anchor_cli() -> tuple[bool, str]:
        try:
            r = subprocess.run(["anchor", "--version"], capture_output=True, text=True, timeout=10)
            if r.returncode == 0:
                return True, r.stdout.strip()
        except (FileNotFoundError, subprocess.TimeoutExpired):
            pass
        return False, ""


class AnchorAdapter(ToolAdapter):
    """Adapter for Anchor framework CLI (build, test, deploy on Solana)."""

    ADAPTER_VERSION = "0.1.0"

    def check_dependencies(self) -> bool:
        return SolanaDetector.check_anchor_cli()[0]

    def get_version(self) -> str:
        return SolanaDetector.check_anchor_cli()[1]

    def build_command(self, target_dir: str, **kwargs) -> list[str]:
        cmd = ["anchor"]
        subcommand = kwargs.get("subcommand", "build")
        cmd.append(subcommand)
        if subcommand == "test":
            if kwargs.get("skip_local_validator"):
                cmd.append("--skip-local-validator")
            if kwargs.get("detach"):
                cmd.append("--detach")
        return cmd

    def parse_output(self, stdout: str, stderr: str, output_paths: list[str]) -> list[dict]:
        findings = []
        for line in stdout.split("\n"):
            ls = line.strip()
            if "error" in ls.lower() or "warning" in ls.lower() and "Error" in ls:
                findings.append({
                    "finding_id": str(uuid.uuid4()),
                    "classification": "tool_generated_warning",
                    "severity": "low" if "warning" in ls.lower() else "high",
                    "tool": {"name": "anchor", "rule_id": "compilation-issue"},
                    "location": {},
                    "vulnerability_category": "other",
                    "title": f"Anchor: {ls[:100]}",
                    "deduplication_group": f"anchor-{ls[:40]}",
                    "reproduction": {"status": "none"},
                    "schema_version": "1.0.0",
                })
        return findings


class SolanaCLIAdapter(ToolAdapter):
    """Adapter for Solana CLI (program deploy, verify, account inspection)."""

    ADAPTER_VERSION = "0.1.0"

    def check_dependencies(self) -> bool:
        return SolanaDetector.check_solana_cli()[0]

    def get_version(self) -> str:
        return SolanaDetector.check_solana_cli()[1]

    def build_command(self, target_dir: str, **kwargs) -> list[str]:
        cmd = ["solana"]
        subcommand = kwargs.get("subcommand", "program")
        cmd.append(subcommand)
        if subcommand == "program":
            action = kwargs.get("action", "show")
            cmd.append(action)
            if kwargs.get("program_id"):
                cmd.append(kwargs["program_id"])
        elif subcommand == "cluster":
            cmd.append(kwargs.get("cluster_action", "version"))
        elif subcommand == "config":
            cmd.append("get")
        return cmd

    def parse_output(self, stdout: str, stderr: str, output_paths: list[str]) -> list[dict]:
        return []  # Solana CLI is informational — no security findings directly


class TridentAdapter(ToolAdapter):
    """Adapter for Trident Solana fuzzer (cargo-based)."""

    ADAPTER_VERSION = "0.1.0"

    def check_dependencies(self) -> bool:
        try:
            r = subprocess.run(["trident", "--version"], capture_output=True, text=True, timeout=15)
            return r.returncode == 0
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return False

    def get_version(self) -> str:
        try:
            r = subprocess.run(["trident", "--version"], capture_output=True, text=True, timeout=15)
            return r.stdout.strip()
        except Exception:
            return "unknown"

    def build_command(self, target_dir: str, **kwargs) -> list[str]:
        cmd = ["trident"]
        subcommand = kwargs.get("subcommand", "fuzz")
        cmd.append(subcommand)
        if subcommand == "fuzz":
            if kwargs.get("target"):
                cmd.extend(["--target", kwargs["target"]])
            if kwargs.get("number_of_cores"):
                cmd.extend(["--number-of-cores", str(kwargs["number_of_cores"])])
        return cmd

    def parse_output(self, stdout: str, stderr: str, output_paths: list[str]) -> list[dict]:
        findings = []
        for line in stdout.split("\n"):
            ls = line.strip()
            if "FAILED" in ls or "Invariant" in ls and "violated" in ls.lower():
                findings.append({
                    "finding_id": str(uuid.uuid4()),
                    "classification": "invariant_violation",
                    "severity": "high",
                    "confidence": {"level": 3, "evidence_level": "executable_failure",
                                   "evidence_sources": ["trident"]},
                    "tool": {"name": "trident", "rule_id": "fuzzer-failure"},
                    "location": {},
                    "vulnerability_category": "logic_error",
                    "title": f"Trident: {ls[:100]}",
                    "deduplication_group": f"trident-{ls[:40]}",
                    "reproduction": {"status": "counterexample"},
                    "schema_version": "1.0.0",
                })
        return findings