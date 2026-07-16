"""Build executor — compiles smart contracts using the detected framework."""

import json
import os
import subprocess
import time
from pathlib import Path
from typing import Optional, TYPE_CHECKING


if TYPE_CHECKING:
    from orchestrator.jobs.sandbox import SandboxManager


class BuildError(Exception):
    pass


# Minimal environment for subprocess execution — strips host secrets (F-015/F-016)
_SECURE_ENV = {
    "PATH": os.environ.get("PATH", "/usr/bin:/bin"),
    "HOME": os.environ.get("HOME", "/tmp"),
    "USER": os.environ.get("USER", "nobody"),
}


class BuildExecutor:
    """Compiles smart contracts using the detected framework's build system."""

    def __init__(self, repo_path: str, framework: str,
                 sandbox: Optional["SandboxManager"] = None):
        self.repo_path = Path(repo_path)
        self.framework = framework
        self.sandbox = sandbox

    def build(self, timeout_s: int = 120, env: Optional[dict] = None) -> tuple[bool, dict, str]:
        """
        Build the project using the detected framework.
        
        Returns:
            (success, manifest, build_log)
        """
        start = time.time()
        build_env = dict(_SECURE_ENV)
        if env:
            build_env.update(env)

        if self.sandbox and self.sandbox.use_sandbox:
            return self._build_in_sandbox(timeout_s, build_env)
        elif self.framework == "foundry":
            return self._build_foundry(timeout_s, build_env)
        elif self.framework == "hardhat":
            return self._build_hardhat(timeout_s, build_env)
        elif self.framework == "anchor":
            return self._build_anchor(timeout_s, build_env)
        else:
            raise BuildError(f"Unsupported framework: {self.framework}")

    def _build_in_sandbox(self, timeout_s: int, env: dict) -> tuple[bool, dict, str]:
        """Build inside a sandbox container."""
        _start = time.time()
        try:
            exit_code, stdout, stderr = self.sandbox.run_in_sandbox(
                job_id=f"build-{self.framework}",
                command=["forge", "build"],
                work_dir=str(self.repo_path),
                timeout_s=timeout_s,
            )
            log = stdout + stderr
            manifest = {
                "tool": "forge",
                "framework": "foundry",
                "success": exit_code == 0,
                "exit_code": exit_code,
                "duration_seconds": time.time() - _start,
                "compiler_version": self._extract_solc_version(log),
                "sandboxed": True,
            }
            return exit_code == 0, manifest, log
        except Exception as e:
            raise BuildError(f"Sandbox build failed: {e}")

    def _build_foundry(self, timeout_s: int, env: dict) -> tuple[bool, dict, str]:
        """Build with Foundry."""
        _start = time.time()
        try:
            r = subprocess.run(
                ["forge", "build"],
                cwd=str(self.repo_path),
                capture_output=True, text=True,
                timeout=timeout_s,
                env=env,
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
                env=env,
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
                env=env,
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