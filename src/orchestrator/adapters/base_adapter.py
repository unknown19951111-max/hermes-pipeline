"""
Base adapter class for all pipeline tool adapters.
"""

import json
import os
import shlex
import subprocess
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, TYPE_CHECKING


if TYPE_CHECKING:
    from orchestrator.jobs.sandbox import SandboxManager


# Minimal environment for subprocess execution — strips host secrets
_SECURE_ENV = {
    "PATH": os.environ.get("PATH", "/usr/bin:/bin"),
    "HOME": os.environ.get("HOME", "/tmp"),
    "USER": os.environ.get("USER", "nobody"),
}


@dataclass
class AdapterResult:
    """Standard result from any tool adapter."""
    success: bool
    tool: str
    tool_version: str
    adapter_version: str
    command: str
    exit_code: int
    timed_out: bool
    stdout: str
    stderr: str
    raw_output_paths: list[str]
    normalized_findings: list[dict] = field(default_factory=list)
    execution_manifest: dict = field(default_factory=dict)
    coverage_limitations: list[str] = field(default_factory=list)
    start_time: str = ""
    end_time: str = ""
    duration_seconds: float = 0.0
    error: Optional[str] = None

    def to_manifest(self, job_id: str, stage_id: str, work_dir: str) -> dict:
        return {
            "job_id": job_id,
            "stage_id": stage_id,
            "tool": self.tool,
            "tool_version": self.tool_version,
            "adapter_version": self.adapter_version,
            "schema_version": "1.0.0",
            "command": self.command,
            "arguments": [],
            "working_directory": work_dir,
            "environment_allowlist": [],
            "start_time": self.start_time or datetime.now(timezone.utc).isoformat(),
            "end_time": self.end_time or datetime.now(timezone.utc).isoformat(),
            "duration_seconds": self.duration_seconds,
            "exit_code": self.exit_code,
            "timeout": self.timed_out,
            "resources": {},
            "output_hashes": {},
            "artifact_paths": self.raw_output_paths,
            "target_commit": "",
            "compiler_version": "",
            "container_image_digest": "",
            "fork_chain": "",
            "fork_block": 0,
            "retry_count": 0,
            "error_classification": (
                "timeout" if self.timed_out
                else "deterministic" if self.exit_code != 0
                else "unknown"
            ),
            "completion_state": (
                "completed" if self.success
                else "timed_out" if self.timed_out
                else "failed"
            ),
            "coverage_limitations": self.coverage_limitations,
        }


class ToolAdapter(ABC):
    """Base class for all tool adapters."""

    ADAPTER_VERSION = "0.1.0"

    def __init__(self, work_dir: str):
        self.work_dir = Path(work_dir)
        self.work_dir.mkdir(parents=True, exist_ok=True)

    @abstractmethod
    def check_dependencies(self) -> bool:
        """Check if the tool binary is available."""
        pass

    @abstractmethod
    def get_version(self) -> str:
        """Get the installed tool version."""
        pass

    @abstractmethod
    def build_command(self, target_dir: str, **kwargs) -> list[str]:
        """Build the command to run the tool."""
        pass

    @abstractmethod
    def parse_output(self, stdout: str, stderr: str, output_paths: list[str]) -> list[dict]:
        """Parse raw output into normalized findings."""
        pass

    def run(self, target_dir: str, job_id: str, timeout_s: int = 120,
            sandbox: Optional["SandboxManager"] = None,
            env: Optional[dict] = None,
            **kwargs) -> AdapterResult:
        """Run the tool adapter — dependency check, execution, parsing.

        Args:
            target_dir: Directory containing the target project.
            job_id: Unique job identifier.
            timeout_s: Max execution time in seconds.
            sandbox: Optional SandboxManager for container-isolated execution.
            env: Optional extra environment variables (merged into secure default).
            **kwargs: Tool-specific arguments passed to build_command().
        """
        # Check dependencies
        if not self.check_dependencies():
            return AdapterResult(
                success=False, tool=self.__class__.__name__,
                tool_version="", adapter_version=self.ADAPTER_VERSION,
                command="", exit_code=-1, timed_out=False,
                stdout="", stderr="", raw_output_paths=[],
                error=f"Tool {self.__class__.__name__} not found in PATH",
            )

        tool_version = self.get_version()

        # Build the command
        cmd = self.build_command(target_dir, **kwargs)
        cmd_str = shlex.join(str(c) for c in cmd)

        # Build a minimal environment — strip host secrets (F-016)
        run_env = dict(_SECURE_ENV)
        if env:
            run_env.update(env)
        # Allow PATH updates from kwargs (e.g. custom tool path)
        extra_path = kwargs.get("extra_path", "")
        if extra_path:
            run_env["PATH"] = f"{extra_path}:{run_env['PATH']}"

        _start = time.time()
        timed_out = False
        stdout = ""
        stderr = ""
        exit_code = -1

        if sandbox and sandbox.use_sandbox:
            # Route through sandbox container (F-015)
            try:
                exit_code, stdout, stderr = sandbox.run_in_sandbox(
                    job_id=job_id,
                    command=cmd,
                    work_dir=target_dir,
                    timeout_s=timeout_s,
                )
            except Exception as e:
                stderr = f"Sandbox execution failed: {e}"
                exit_code = -1
        else:
            # Direct execution with stripped environment
            try:
                result = subprocess.run(
                    cmd, cwd=target_dir,
                    capture_output=True, text=True,
                    timeout=timeout_s,
                    env=run_env,
                )
                stdout = result.stdout
                stderr = result.stderr
                exit_code = result.returncode
            except subprocess.TimeoutExpired:
                timed_out = True
                stderr = f"TIMEOUT after {timeout_s}s"
                exit_code = -1

        _end = time.time()

        # Save raw output
        output_paths = []
        if stdout:
            out_path = str(self.work_dir / f"{job_id}_stdout.txt")
            Path(out_path).write_text(stdout)
            output_paths.append(out_path)
        if stderr:
            err_path = str(self.work_dir / f"{job_id}_stderr.txt")
            Path(err_path).write_text(stderr)
            output_paths.append(err_path)

        # Parse output
        normalized = []
        if stdout:
            try:
                normalized = self.parse_output(stdout, stderr, output_paths)
            except Exception as e:
                # Malformed output → quarantine, don't crash
                normalized = [{
                    "finding_id": f"{job_id}-parse-error",
                    "classification": "analysis_failure",
                    "tool": {"name": self.__class__.__name__, "version": tool_version, "rule_id": "parse-error"},
                    "title": f"Failed to parse {self.__class__.__name__} output",
                    "description": str(e),
                    "raw_output_saved": output_paths[-1] if output_paths else "",
                }]

        # Track three independent success flags (F-004 fix)
        process_success = exit_code == 0
        parse_success = len(normalized) == 0 or not any(
            f.get("classification") == "analysis_failure"
            and "parse" in f.get("tool", {}).get("rule_id", "")
            for f in normalized
        )
        # Determine success — ONLY process_success matters for tool success
        success = process_success

        return AdapterResult(
            success=success,
            tool=self.__class__.__name__,
            tool_version=tool_version,
            adapter_version=self.ADAPTER_VERSION,
            command=cmd_str,
            exit_code=exit_code,
            timed_out=timed_out,
            stdout=stdout,
            stderr=stderr,
            raw_output_paths=output_paths,
            normalized_findings=normalized,
            error=None if success else stderr[:500] if stderr else "Unknown error",
            start_time=datetime.fromtimestamp(_start, tz=timezone.utc).isoformat(),
            end_time=datetime.fromtimestamp(_end, tz=timezone.utc).isoformat(),
            duration_seconds=_end - _start,
        )