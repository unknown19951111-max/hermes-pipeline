"""
Move adapter — Aptos, Sui, and Move Prover CLI integration.
"""

import json
import os
import re
import subprocess
import uuid
from pathlib import Path
from typing import Optional

from ..adapters.base_adapter import ToolAdapter, AdapterResult


class MoveDetector:
    """Detect Move ecosystem tools."""

    @staticmethod
    def check_aptos_cli() -> tuple[bool, str]:
        try:
            r = subprocess.run(["aptos", "--version"], capture_output=True, text=True, timeout=10)
            if r.returncode == 0:
                return True, r.stdout.strip()
        except (FileNotFoundError, subprocess.TimeoutExpired):
            pass
        return False, ""

    @staticmethod
    def check_sui_cli() -> tuple[bool, str]:
        try:
            r = subprocess.run(["sui", "--version"], capture_output=True, text=True, timeout=10)
            if r.returncode == 0:
                return True, r.stdout.strip()
        except (FileNotFoundError, subprocess.TimeoutExpired):
            pass
        return False, ""

    @staticmethod
    def check_move_prover() -> tuple[bool, str]:
        try:
            r = subprocess.run(["move", "prover", "--version"], capture_output=True, text=True, timeout=15)
            if r.returncode == 0:
                return True, r.stdout.strip()
        except (FileNotFoundError, subprocess.TimeoutExpired):
            pass
        return False, ""


class AptosAdapter(ToolAdapter):
    """Adapter for Aptos CLI (Move blockchain)."""

    ADAPTER_VERSION = "0.1.0"

    def check_dependencies(self) -> bool:
        return MoveDetector.check_aptos_cli()[0]

    def get_version(self) -> str:
        return MoveDetector.check_aptos_cli()[1]

    def build_command(self, target_dir: str, **kwargs) -> list[str]:
        cmd = ["aptos"]
        subcommand = kwargs.get("subcommand", "move")
        cmd.append(subcommand)
        if subcommand == "move":
            action = kwargs.get("action", "compile")
            cmd.append(action)
            if kwargs.get("package_dir"):
                cmd.extend(["--package-dir", kwargs["package_dir"]])
            if kwargs.get("named_addresses"):
                cmd.extend(["--named-addresses", kwargs["named_addresses"]])
        return cmd

    def parse_output(self, stdout: str, stderr: str, output_paths: list[str]) -> list[dict]:
        findings = []
        for line in stdout.split("\n"):
            ls = line.strip()
            if "error" in ls.lower() or "warning" in ls.lower():
                findings.append({
                    "finding_id": str(uuid.uuid4()),
                    "classification": "tool_generated_warning",
                    "severity": "low" if "warning" in ls.lower() else "high",
                    "tool": {"name": "aptos", "rule_id": "move-issue"},
                    "location": {},
                    "vulnerability_category": "other",
                    "title": f"Aptos: {ls[:100]}",
                    "deduplication_group": f"aptos-{ls[:40]}",
                    "reproduction": {"status": "none"},
                    "schema_version": "1.0.0",
                })
        return findings


class SuiAdapter(ToolAdapter):
    """Adapter for Sui CLI (Move blockchain)."""

    ADAPTER_VERSION = "0.1.0"

    def check_dependencies(self) -> bool:
        return MoveDetector.check_sui_cli()[0]

    def get_version(self) -> str:
        return MoveDetector.check_sui_cli()[1]

    def build_command(self, target_dir: str, **kwargs) -> list[str]:
        cmd = ["sui"]
        subcommand = kwargs.get("subcommand", "move")
        cmd.append(subcommand)
        if subcommand == "move":
            action = kwargs.get("action", "build")
            cmd.append(action)
            if kwargs.get("path"):
                cmd.extend(["--path", kwargs["path"]])
        return cmd

    def parse_output(self, stdout: str, stderr: str, output_paths: list[str]) -> list[dict]:
        findings = []
        for line in stdout.split("\n"):
            ls = line.strip()
            if "error" in ls.lower() or "warning" in ls.lower():
                findings.append({
                    "finding_id": str(uuid.uuid4()),
                    "classification": "tool_generated_warning",
                    "severity": "low" if "warning" in ls.lower() else "high",
                    "tool": {"name": "sui", "rule_id": "move-issue"},
                    "location": {},
                    "vulnerability_category": "other",
                    "title": f"Sui: {ls[:100]}",
                    "deduplication_group": f"sui-{ls[:40]}",
                    "reproduction": {"status": "none"},
                    "schema_version": "1.0.0",
                })
        return findings


class MoveProverAdapter(ToolAdapter):
    """Adapter for Move Prover — formal verification for Move smart contracts."""

    ADAPTER_VERSION = "0.1.0"

    def check_dependencies(self) -> bool:
        return MoveDetector.check_move_prover()[0]

    def get_version(self) -> str:
        return MoveDetector.check_move_prover()[1]

    def build_command(self, target_dir: str, **kwargs) -> list[str]:
        cmd = ["move", "prover"]
        if kwargs.get("package_path"):
            cmd.extend(["--package-path", kwargs["package_path"]])
        if kwargs.get("verify_modules"):
            cmd.extend(["--verify-modules", kwargs["verify_modules"]])
        if kwargs.get("trace"):
            cmd.append("--trace")
        return cmd

    def parse_output(self, stdout: str, stderr: str, output_paths: list[str]) -> list[dict]:
        findings = []
        for line in stdout.split("\n"):
            ls = line.strip()
            if "FAILED" in ls or "counterexample" in ls.lower() or "verification" in ls.lower() and "failed" in ls.lower():
                findings.append({
                    "finding_id": str(uuid.uuid4()),
                    "classification": "confirmed_vulnerability",
                    "severity": "high",
                    "confidence": {"level": 4, "evidence_level": "formal_verification_counterexample",
                                   "evidence_sources": ["move-prover"]},
                    "tool": {"name": "move-prover", "rule_id": "proof-failure"},
                    "location": {},
                    "vulnerability_category": "logic_error",
                    "title": f"Move Prover: {ls[:100]}",
                    "deduplication_group": f"move-prover-{ls[:40]}",
                    "reproduction": {"status": "counterexample"},
                    "schema_version": "1.0.0",
                })
        return findings