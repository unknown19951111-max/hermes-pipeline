"""Build executor — compiles smart contracts using the detected framework."""

import json
import os
import subprocess
import time
from pathlib import Path
from typing import Optional


class BuildError(Exception):
    pass


class BuildExecutor:
    """Compiles smart contracts using the detected framework's build system."""

    def __init__(self, repo_path: str, framework: str):
        self.repo_path = Path(repo_path)
        self.framework = framework

    def build(self, timeout_s: int = 120, env: Optional[dict] = None) -> tuple[bool, dict, str]:
        """
        Build the project using the detected framework.
        
        Returns:
            (success, manifest, build_log)
        """
        start = time.time()
        build_env = {**os.environ, **(env or {})}

        if self.framework == "foundry":
            return self._build_foundry(timeout_s, build_env)
        elif self.framework == "hardhat":
            return self._build_hardhat(timeout_s, build_env)
        elif self.framework == "anchor":
            return self._build_anchor(timeout_s, build_env)
        else:
            raise BuildError(f"Unsupported framework: {self.framework}")

    def _build_foundry(self, timeout_s: int, env: dict) -> tuple[bool, dict, str]:
        """Build with Foundry."""
        _start = time.time()
        try:
            r = subprocess.run(
                ["forge", "build", "--via-ir"],
                cwd=str(self.repo_path),
                capture_output=True, text=True,
                timeout=timeout_s,
            )
            log = r.stdout + r.stderr
            manifest = {
                "tool": "forge",
                "framework": "foundry",
                "success": r.returncode == 0,
                "exit_code": r.returncode,
                "duration_seconds": time.time() - _start,
                "compiler_version": self._extract_solc_version(log),
            }
            return r.returncode == 0, manifest, log
        except subprocess.TimeoutExpired:
            raise BuildError("Foundry build timed out")
        except FileNotFoundError:
            raise BuildError("forge binary not found in PATH")

    def _build_hardhat(self, timeout_s: int, env: dict) -> tuple[bool, dict, str]:
        """Build with Hardhat."""
        _start = time.time()
        try:
            r = subprocess.run(
                ["npx", "hardhat", "compile"],
                cwd=str(self.repo_path),
                capture_output=True, text=True,
                timeout=timeout_s,
            )
            log = r.stdout + r.stderr
            manifest = {
                "tool": "hardhat",
                "framework": "hardhat",
                "success": r.returncode == 0,
                "exit_code": r.returncode,
                "duration_seconds": time.time() - _start,
                "compiler_version": "",
            }
            return r.returncode == 0, manifest, log
        except subprocess.TimeoutExpired:
            raise BuildError("Hardhat build timed out")
        except FileNotFoundError:
            raise BuildError("npx not found in PATH")

    def _build_anchor(self, timeout_s: int, env: dict) -> tuple[bool, dict, str]:
        """Build with Anchor (Solana)."""
        _start = time.time()
        try:
            r = subprocess.run(
                ["anchor", "build"],
                cwd=str(self.repo_path),
                capture_output=True, text=True,
                timeout=timeout_s,
            )
            log = r.stdout + r.stderr
            manifest = {
                "tool": "anchor",
                "framework": "anchor",
                "success": r.returncode == 0,
                "exit_code": r.returncode,
                "duration_seconds": time.time() - _start,
                "compiler_version": "",
            }
            return r.returncode == 0, manifest, log
        except subprocess.TimeoutExpired:
            raise BuildError("Anchor build timed out")
        except FileNotFoundError:
            raise BuildError("anchor binary not found in PATH")

    @staticmethod
    def _extract_solc_version(log: str) -> str:
        """Extract Solidity compiler version from build log."""
        for line in log.split("\n"):
            if "solc" in line.lower() and ("version" in line.lower() or "0." in line):
                parts = line.split()
                for p in parts:
                    if p.startswith("0."):
                        return p
        return ""